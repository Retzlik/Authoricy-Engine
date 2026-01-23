"""
Database-Integrated Analysis Pipeline

Wraps the existing pipeline with:
1. Database storage for all collected data
2. Data quality validation before AI analysis
3. Quality gate to prevent garbage-in-garbage-out
4. Agent output logging for learning

Usage:
    from src.database.pipeline import run_analysis_with_db

    result = await run_analysis_with_db(
        domain="example.com",
        email="user@example.com",
        market="Sweden",
        language="Swedish",
    )
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from dataclasses import asdict

from src.collector import (
    DataForSEOClient,
    DataCollectionOrchestrator,
    CollectionConfig,
    CollectionResult,
    compile_analysis_data,
)
from src.analyzer import AnalysisEngine

from .repository import (
    create_analysis_run,
    update_run_status,
    complete_run,
    fail_run,
    # Core storage
    store_keywords,
    store_competitors,
    store_backlinks,
    store_technical_metrics,
    store_agent_output,
    store_report,
    get_run_data,
    # Intelligence storage (NEW)
    store_serp_features,
    store_keyword_gaps,
    store_referring_domains,
    store_ranking_history,
    store_content_clusters,
    store_ai_visibility,
    store_local_rankings,
    store_serp_competitors,
)
from .validation import validate_run_data, QualityGate, DataQualityReport
from .models import AnalysisStatus, DataQualityLevel
from .session import get_db_context

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Quality gate: minimum 35% quality to proceed with AI analysis
QUALITY_GATE = QualityGate(min_score=35.0, allow_warnings=True)

# Cost threshold: don't run AI if data is too sparse (waste of money)
MIN_KEYWORDS_FOR_AI = 5
MIN_COMPETITORS_FOR_AI = 1


# =============================================================================
# DATA EXTRACTION HELPERS
# =============================================================================

def _safe_get(item, key, default=None):
    """Safely get a value from an item that should be a dict."""
    if isinstance(item, dict):
        return item.get(key, default)
    return default


def extract_keywords_from_result(result: CollectionResult) -> list:
    """Extract all keywords from collection result for DB storage."""
    keywords = []

    # Ranked keywords (primary source)
    for kw in result.ranked_keywords or []:
        if not isinstance(kw, dict):
            continue
        keywords.append({
            "keyword": _safe_get(kw, "keyword"),
            "search_volume": _safe_get(kw, "search_volume"),
            "cpc": _safe_get(kw, "cpc"),
            "competition": _safe_get(kw, "competition"),
            "position": _safe_get(kw, "position") or _safe_get(kw, "rank_absolute"),
            "url": _safe_get(kw, "url") or _safe_get(kw, "page"),
            "etv": _safe_get(kw, "etv"),
            "intent": _safe_get(kw, "intent"),
            "keyword_difficulty": _safe_get(kw, "keyword_difficulty"),
        })

    # Keyword universe (additional opportunities)
    for kw in result.keyword_universe or []:
        if not isinstance(kw, dict):
            continue
        kw_name = _safe_get(kw, "keyword")
        # Avoid duplicates
        if not any(_safe_get(k, "keyword") == kw_name for k in keywords):
            keywords.append({
                "keyword": kw_name,
                "search_volume": _safe_get(kw, "search_volume"),
                "cpc": _safe_get(kw, "cpc"),
                "competition": _safe_get(kw, "competition"),
                "keyword_difficulty": _safe_get(kw, "keyword_difficulty"),
            })

    # Keyword gaps (competitor keywords we don't rank for)
    for kw in result.keyword_gaps or []:
        if not isinstance(kw, dict):
            continue
        kw_name = _safe_get(kw, "keyword")
        if not any(_safe_get(k, "keyword") == kw_name for k in keywords):
            keywords.append({
                "keyword": kw_name,
                "search_volume": _safe_get(kw, "search_volume"),
                "cpc": _safe_get(kw, "cpc"),
                "source": "gap",
            })

    return keywords


def extract_competitors_from_result(result: CollectionResult) -> list:
    """Extract competitors from collection result for DB storage."""
    competitors = []

    for comp in result.competitors or []:
        if not isinstance(comp, dict):
            continue
        competitors.append({
            "domain": _safe_get(comp, "domain"),
            "competitor_type": _safe_get(comp, "competitor_type", "unknown"),
            "common_keywords": _safe_get(comp, "common_keywords") or _safe_get(comp, "se_keywords"),
            "organic_traffic": _safe_get(comp, "etv") or _safe_get(comp, "organic_traffic"),
            "domain_rating": _safe_get(comp, "rank") or _safe_get(comp, "domain_rating"),
            "detection_method": "organic_competitors",
            "confidence": _safe_get(comp, "confidence", 0.5),
        })

    # Also from competitor analysis (Phase 3)
    for comp in result.competitor_analysis or []:
        if not isinstance(comp, dict):
            continue
        comp_domain = _safe_get(comp, "domain")
        if not any(_safe_get(c, "domain") == comp_domain for c in competitors):
            competitors.append({
                "domain": comp_domain,
                "competitor_type": _safe_get(comp, "competitor_type", "unknown"),
                "organic_traffic": _safe_get(comp, "organic_traffic"),
                "organic_keywords": _safe_get(comp, "organic_keywords"),
                "detection_method": "serp_analysis",
            })

    return competitors


def extract_backlinks_from_result(result: CollectionResult) -> list:
    """Extract backlinks from collection result for DB storage."""
    backlinks = []

    for bl in result.backlinks or []:
        if not isinstance(bl, dict):
            continue
        backlinks.append({
            "url_from": _safe_get(bl, "url_from"),
            "domain_from": _safe_get(bl, "domain_from"),
            "url_to": _safe_get(bl, "url_to"),
            "anchor": _safe_get(bl, "anchor"),
            "dofollow": _safe_get(bl, "dofollow"),
            "domain_from_rank": _safe_get(bl, "domain_from_rank"),
            "first_seen": _safe_get(bl, "first_seen"),
            "last_seen": _safe_get(bl, "last_seen"),
        })

    # Also from top_backlinks
    for bl in result.top_backlinks or []:
        if not isinstance(bl, dict):
            continue
        url_from = _safe_get(bl, "url_from")
        if not any(_safe_get(b, "url_from") == url_from for b in backlinks):
            backlinks.append({
                "url_from": url_from,
                "domain_from": _safe_get(bl, "domain_from"),
                "anchor": _safe_get(bl, "anchor"),
                "dofollow": _safe_get(bl, "dofollow"),
                "domain_from_rank": _safe_get(bl, "rank") or _safe_get(bl, "domain_from_rank"),
            })

    return backlinks


def extract_technical_from_result(result: CollectionResult) -> dict:
    """Extract technical metrics from collection result."""
    # Handle technical_audit (dict) or technical_audits (list)
    technical_raw = result.technical_audit or result.technical_audits or {}
    baseline = result.technical_baseline or {}

    # If technical_audits is a list, aggregate issues from all audits
    if isinstance(technical_raw, list):
        critical_issues = []
        warnings = []
        all_issues = []
        for audit in technical_raw:
            if isinstance(audit, dict):
                critical_issues.extend(audit.get("critical_issues") or [])
                warnings.extend(audit.get("warnings") or [])
                all_issues.extend(audit.get("issues") or [])
        technical = {
            "critical_issues": critical_issues,
            "warnings": warnings,
            "issues": all_issues,
        }
    elif isinstance(technical_raw, dict):
        technical = technical_raw
    else:
        technical = {}

    return {
        "performance_score": baseline.get("performance_score"),
        "accessibility_score": baseline.get("accessibility_score"),
        "best_practices_score": baseline.get("best_practices_score"),
        "seo_score": baseline.get("seo_score"),
        "lcp": baseline.get("lcp"),
        "fid": baseline.get("fid"),
        "cls": baseline.get("cls"),
        "inp": baseline.get("inp"),
        "critical_issues": technical.get("critical_issues"),
        "warnings": technical.get("warnings"),
        "issues": technical.get("issues"),
        "technologies": result.technologies,
    }


# =============================================================================
# INTELLIGENCE DATA EXTRACTION
# =============================================================================

def extract_serp_features_from_result(result: CollectionResult) -> list:
    """Extract SERP features for storage."""
    serp_data = []

    # From serp_elements (Phase 2)
    for item in getattr(result, 'serp_elements', []) or []:
        serp_data.append(item)

    # From live_serp_data (Phase 4)
    for item in getattr(result, 'live_serp_data', []) or []:
        serp_data.append(item)

    return serp_data


def extract_keyword_gaps_from_result(result: CollectionResult) -> tuple:
    """Extract keyword gaps and overlaps for storage."""
    gaps = getattr(result, 'keyword_gaps', []) or []
    overlaps = getattr(result, 'keyword_overlaps', []) or []
    return gaps, overlaps


def extract_referring_domains_from_result(result: CollectionResult) -> tuple:
    """Extract referring domains data for storage."""
    ref_domains = getattr(result, 'referring_domains', []) or []
    backlinks = getattr(result, 'backlinks', []) or []
    anchor_dist = getattr(result, 'anchor_distribution', []) or []
    return ref_domains, backlinks, anchor_dist


def extract_content_clusters_from_result(result: CollectionResult) -> list:
    """Extract content clusters for storage."""
    return getattr(result, 'keyword_clusters', []) or []


def extract_ai_visibility_from_result(result: CollectionResult) -> tuple:
    """Extract AI visibility data for storage."""
    llm_mentions = getattr(result, 'llm_mentions', {}) or {}
    brand_mentions = getattr(result, 'brand_mentions', []) or []
    return llm_mentions, brand_mentions


def extract_local_data_from_result(result: CollectionResult) -> tuple:
    """Extract local ranking data for storage."""
    local_data = []

    # Extract from live_serp_data if local pack present
    for item in getattr(result, 'live_serp_data', []) or []:
        if isinstance(item, dict) and (_safe_get(item, 'local_pack') or _safe_get(item, 'local_pack_position')):
            local_data.append(item)

    # GBP data if available
    gbp_data = None
    domain_overview = getattr(result, 'domain_overview', None) or {}
    if isinstance(domain_overview, dict) and domain_overview.get('google_business_profile'):
        gbp_data = domain_overview['google_business_profile']

    return local_data, gbp_data


def extract_serp_competitors_from_result(result: CollectionResult) -> tuple:
    """Extract per-keyword SERP competitors for storage."""
    serp_data = getattr(result, 'serp_elements', []) or []

    # Build competitor metrics lookup
    comp_metrics = {}
    for comp in getattr(result, 'competitor_analysis', []) or []:
        if not isinstance(comp, dict):
            continue
        domain = _safe_get(comp, 'domain', '')
        if domain:
            comp_metrics[domain] = comp

    return serp_data, comp_metrics


def prepare_validation_data(result: CollectionResult) -> dict:
    """Prepare data structure for validation."""
    domain_overview = result.domain_overview if isinstance(result.domain_overview, dict) else {}
    backlink_summary = result.backlink_summary if isinstance(result.backlink_summary, dict) else {}

    return {
        "keywords": extract_keywords_from_result(result),
        "competitors": extract_competitors_from_result(result),
        "backlinks": extract_backlinks_from_result(result),
        "domain_info": {
            "domain_rating": domain_overview.get("domain_rank") or backlink_summary.get("domain_rank"),
            "organic_traffic": domain_overview.get("organic_traffic"),
            "organic_keywords": domain_overview.get("organic_keywords"),
            "referring_domains": backlink_summary.get("referring_domains"),
            "technologies": result.technologies,
        },
        "technical": extract_technical_from_result(result),
    }


# =============================================================================
# MAIN PIPELINE FUNCTION
# =============================================================================

async def run_analysis_with_db(
    domain: str,
    email: str,
    company_name: Optional[str] = None,
    market: str = "Sweden",
    language: str = "Swedish",
    skip_ai_analysis: bool = False,
    dataforseo_login: str = None,
    dataforseo_password: str = None,
    anthropic_key: str = None,
) -> Dict[str, Any]:
    """
    Run full analysis pipeline with database integration.

    This wraps the standard pipeline with:
    1. Creates analysis run in DB
    2. Stores all collected data
    3. Validates data quality
    4. Applies quality gate before AI
    5. Logs AI outputs for learning

    Returns:
        Dict with run_id, quality_report, analysis_result, etc.
    """
    import os

    # Get credentials from params or environment
    dataforseo_login = dataforseo_login or os.getenv("DATAFORSEO_LOGIN")
    dataforseo_password = dataforseo_password or os.getenv("DATAFORSEO_PASSWORD")
    anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")

    if not dataforseo_login or not dataforseo_password:
        raise ValueError("Missing DataForSEO credentials")

    # =========================================================================
    # STEP 1: Create analysis run in database
    # =========================================================================
    run_id = create_analysis_run(
        domain=domain,
        config={
            "market": market,
            "language": language,
            "email": email,
            "company_name": company_name,
        },
        client_email=email,
    )
    logger.info(f"Created analysis run {run_id} for {domain}")

    try:
        update_run_status(run_id, AnalysisStatus.COLLECTING, phase="data_collection")

        # =====================================================================
        # STEP 2: Collect data from DataForSEO
        # =====================================================================
        async with DataForSEOClient(
            login=dataforseo_login,
            password=dataforseo_password
        ) as client:

            orchestrator = DataCollectionOrchestrator(client)

            result = await orchestrator.collect(CollectionConfig(
                domain=domain,
                market=market,
                language=language,
                brand_name=company_name or domain.split(".")[0],
                skip_ai_analysis=skip_ai_analysis,
            ))

            if not result.success:
                fail_run(run_id, f"Collection failed: {', '.join(result.errors)}")
                return {
                    "run_id": str(run_id),
                    "success": False,
                    "error": "Data collection failed",
                    "errors": result.errors,
                }

            logger.info(f"Data collection complete for {domain}")

        # =====================================================================
        # STEP 3: Store collected data in database
        # =====================================================================
        update_run_status(run_id, AnalysisStatus.COLLECTING, phase="storing_data", progress=50)

        # Get domain_id from run
        with get_db_context() as db:
            from .models import AnalysisRun
            run = db.query(AnalysisRun).get(run_id)
            domain_id = run.domain_id

        # Store all entities - CORE TABLES
        keywords = extract_keywords_from_result(result)
        competitors = extract_competitors_from_result(result)
        backlinks = extract_backlinks_from_result(result)
        technical = extract_technical_from_result(result)

        keywords_count = store_keywords(run_id, domain_id, keywords, source="collected")
        competitors_count = store_competitors(run_id, domain_id, competitors)
        backlinks_count = store_backlinks(run_id, domain_id, backlinks)

        if technical:
            store_technical_metrics(run_id, domain_id, technical)

        logger.info(
            f"Stored core: {keywords_count} keywords, {competitors_count} competitors, "
            f"{backlinks_count} backlinks"
        )

        # Store all entities - INTELLIGENCE TABLES (NEW)
        update_run_status(run_id, AnalysisStatus.COLLECTING, phase="storing_intelligence", progress=55)

        # 1. SERP Features
        serp_features_data = extract_serp_features_from_result(result)
        serp_features_count = store_serp_features(
            run_id, domain_id, serp_features_data, ranked_keywords=result.ranked_keywords
        )

        # 2. Keyword Gaps
        gaps_data, overlaps_data = extract_keyword_gaps_from_result(result)
        keyword_gaps_count = store_keyword_gaps(run_id, domain_id, gaps_data, overlaps_data)

        # 3. Referring Domains
        ref_domains, bl_data, anchor_data = extract_referring_domains_from_result(result)
        ref_domains_count = store_referring_domains(run_id, domain_id, ref_domains, bl_data, anchor_data)

        # 4. Ranking History (snapshot current rankings for trend tracking)
        ranking_history_count = store_ranking_history(
            run_id, domain_id, result.ranked_keywords, timestamp=result.timestamp
        )

        # 5. Content Clusters
        clusters_data = extract_content_clusters_from_result(result)
        clusters_count = store_content_clusters(
            run_id, domain_id, clusters_data, ranked_keywords=result.ranked_keywords
        )

        # 6. AI Visibility (GEO)
        llm_mentions, brand_mentions = extract_ai_visibility_from_result(result)
        ai_visibility_count = store_ai_visibility(
            run_id, domain_id, result.domain, llm_mentions, brand_mentions
        )

        # 7. Local Rankings
        local_data, gbp_data = extract_local_data_from_result(result)
        local_count = store_local_rankings(run_id, domain_id, local_data, gbp_data)

        # 8. SERP Competitors
        serp_comp_data, comp_metrics = extract_serp_competitors_from_result(result)
        serp_competitors_count = store_serp_competitors(run_id, domain_id, serp_comp_data, comp_metrics)

        logger.info(
            f"Stored intelligence: {serp_features_count} SERP features, "
            f"{keyword_gaps_count} keyword gaps, {ref_domains_count} referring domains, "
            f"{ranking_history_count} rankings, {clusters_count} clusters, "
            f"{ai_visibility_count} AI visibility, {local_count} local, "
            f"{serp_competitors_count} SERP competitors"
        )

        # =====================================================================
        # STEP 4: Validate data quality
        # =====================================================================
        update_run_status(run_id, AnalysisStatus.VALIDATING, phase="quality_check", progress=60)

        validation_data = prepare_validation_data(result)
        quality_report = validate_run_data(validation_data)

        logger.info(
            f"Data quality: {quality_report.quality_level.value} "
            f"({quality_report.quality_score:.1f}%), "
            f"critical={quality_report.critical_count}, warnings={quality_report.warning_count}"
        )

        # =====================================================================
        # STEP 5: Quality Gate - decide if AI analysis should proceed
        # =====================================================================
        passed_gate, gate_reason = QUALITY_GATE.check(quality_report)

        # Additional checks
        if len(keywords) < MIN_KEYWORDS_FOR_AI:
            passed_gate = False
            gate_reason = f"Only {len(keywords)} keywords found (need {MIN_KEYWORDS_FOR_AI})"

        if len(competitors) < MIN_COMPETITORS_FOR_AI:
            passed_gate = False
            gate_reason = f"Only {len(competitors)} competitors found (need {MIN_COMPETITORS_FOR_AI})"

        if not passed_gate:
            logger.warning(f"Quality gate FAILED: {gate_reason}")
            complete_run(
                run_id,
                quality_level=quality_report.quality_level,
                quality_score=quality_report.quality_score,
                quality_issues=[i.__dict__ for i in quality_report.issues],
            )
            return {
                "run_id": str(run_id),
                "success": True,  # Collection succeeded
                "ai_skipped": True,
                "ai_skip_reason": gate_reason,
                "quality_report": quality_report.to_dict(),
                "data_stats": {
                    "keywords": keywords_count,
                    "competitors": competitors_count,
                    "backlinks": backlinks_count,
                },
            }

        logger.info(f"Quality gate PASSED: {gate_reason}")

        # =====================================================================
        # STEP 6: Run AI Analysis (if not skipped)
        # =====================================================================
        analysis_result = None

        if not skip_ai_analysis and anthropic_key:
            update_run_status(run_id, AnalysisStatus.ANALYZING, phase="ai_analysis", progress=70)

            try:
                # Compile data for AI
                analysis_data = compile_analysis_data(result)

                # Run analysis engine
                engine = AnalysisEngine(api_key=anthropic_key)
                analysis_result = await engine.analyze(
                    analysis_data,
                    skip_enrichment=False,
                )

                logger.info(
                    f"AI analysis complete: quality={analysis_result.quality_score}/10, "
                    f"cost=${analysis_result.total_cost:.2f}"
                )

                # Store agent outputs for learning
                store_agent_output(
                    run_id=run_id,
                    agent_name="loop1_interpreter",
                    input_summary={"phase": "data_interpretation"},
                    output_raw=analysis_result.loop1_findings,
                    quality_score=analysis_result.quality_score,
                    cost_usd=analysis_result.total_cost / 4,  # Approximate per-loop
                )

                store_agent_output(
                    run_id=run_id,
                    agent_name="loop2_synthesizer",
                    input_summary={"phase": "strategic_synthesis"},
                    output_raw=analysis_result.loop2_strategy,
                    quality_score=analysis_result.quality_score,
                    cost_usd=analysis_result.total_cost / 4,
                )

                store_agent_output(
                    run_id=run_id,
                    agent_name="loop3_enricher",
                    input_summary={"phase": "serp_enrichment"},
                    output_raw=analysis_result.loop3_enrichment,
                    quality_score=analysis_result.quality_score,
                    cost_usd=analysis_result.total_cost / 4,
                )

                store_agent_output(
                    run_id=run_id,
                    agent_name="loop4_reviewer",
                    input_summary={"phase": "quality_review"},
                    output_raw=analysis_result.executive_summary,
                    output_parsed=analysis_result.quality_checks,
                    quality_score=analysis_result.quality_score,
                    passed_quality_gate=analysis_result.passed_quality_gate,
                    cost_usd=analysis_result.total_cost / 4,
                )

            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                analysis_result = None

        # =====================================================================
        # STEP 7: Complete the run
        # =====================================================================
        complete_run(
            run_id,
            quality_level=quality_report.quality_level,
            quality_score=quality_report.quality_score,
            quality_issues=[i.__dict__ for i in quality_report.issues],
        )

        return {
            "run_id": str(run_id),
            "success": True,
            "quality_report": quality_report.to_dict(),
            "quality_gate_passed": passed_gate,
            "data_stats": {
                "keywords": keywords_count,
                "competitors": competitors_count,
                "backlinks": backlinks_count,
            },
            "analysis_result": {
                "quality_score": analysis_result.quality_score if analysis_result else None,
                "passed_quality_gate": analysis_result.passed_quality_gate if analysis_result else None,
                "total_cost": analysis_result.total_cost if analysis_result else None,
                "executive_summary": analysis_result.executive_summary if analysis_result else None,
            } if analysis_result else None,
            "collection_result": result,  # For report generation
        }

    except Exception as e:
        logger.exception(f"Analysis pipeline failed: {e}")
        fail_run(run_id, str(e))
        return {
            "run_id": str(run_id),
            "success": False,
            "error": str(e),
        }


# =============================================================================
# HELPER FOR EXISTING PIPELINE
# =============================================================================

def get_quality_summary(result: CollectionResult) -> dict:
    """
    Quick quality check without storing to database.

    Use this for quick validation in existing code.
    """
    validation_data = prepare_validation_data(result)
    report = validate_run_data(validation_data)

    return {
        "quality_level": report.quality_level.value,
        "quality_score": report.quality_score,
        "is_sufficient": report.is_sufficient_for_analysis,
        "critical_issues": report.critical_count,
        "warnings": report.warning_count,
        "recommendations": report.recommendations[:3],  # Top 3
    }

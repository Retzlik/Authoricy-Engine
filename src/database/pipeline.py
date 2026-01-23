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
    store_keywords,
    store_competitors,
    store_backlinks,
    store_technical_metrics,
    store_agent_output,
    store_report,
    get_run_data,
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

def extract_keywords_from_result(result: CollectionResult) -> list:
    """Extract all keywords from collection result for DB storage."""
    keywords = []

    # Ranked keywords (primary source)
    for kw in result.ranked_keywords:
        keywords.append({
            "keyword": kw.get("keyword"),
            "search_volume": kw.get("search_volume"),
            "cpc": kw.get("cpc"),
            "competition": kw.get("competition"),
            "position": kw.get("position") or kw.get("rank_absolute"),
            "url": kw.get("url") or kw.get("page"),
            "etv": kw.get("etv"),
            "intent": kw.get("intent"),
            "keyword_difficulty": kw.get("keyword_difficulty"),
        })

    # Keyword universe (additional opportunities)
    for kw in result.keyword_universe:
        # Avoid duplicates
        if not any(k.get("keyword") == kw.get("keyword") for k in keywords):
            keywords.append({
                "keyword": kw.get("keyword"),
                "search_volume": kw.get("search_volume"),
                "cpc": kw.get("cpc"),
                "competition": kw.get("competition"),
                "keyword_difficulty": kw.get("keyword_difficulty"),
            })

    # Keyword gaps (competitor keywords we don't rank for)
    for kw in result.keyword_gaps:
        if not any(k.get("keyword") == kw.get("keyword") for k in keywords):
            keywords.append({
                "keyword": kw.get("keyword"),
                "search_volume": kw.get("search_volume"),
                "cpc": kw.get("cpc"),
                "source": "gap",
            })

    return keywords


def extract_competitors_from_result(result: CollectionResult) -> list:
    """Extract competitors from collection result for DB storage."""
    competitors = []

    for comp in result.competitors:
        competitors.append({
            "domain": comp.get("domain"),
            "competitor_type": comp.get("competitor_type", "unknown"),
            "common_keywords": comp.get("common_keywords") or comp.get("se_keywords"),
            "organic_traffic": comp.get("etv") or comp.get("organic_traffic"),
            "domain_rating": comp.get("rank") or comp.get("domain_rating"),
            "detection_method": "organic_competitors",
            "confidence": comp.get("confidence", 0.5),
        })

    # Also from competitor analysis (Phase 3)
    for comp in result.competitor_analysis:
        if not any(c.get("domain") == comp.get("domain") for c in competitors):
            competitors.append({
                "domain": comp.get("domain"),
                "competitor_type": comp.get("competitor_type", "unknown"),
                "organic_traffic": comp.get("organic_traffic"),
                "organic_keywords": comp.get("organic_keywords"),
                "detection_method": "serp_analysis",
            })

    return competitors


def extract_backlinks_from_result(result: CollectionResult) -> list:
    """Extract backlinks from collection result for DB storage."""
    backlinks = []

    for bl in result.backlinks:
        backlinks.append({
            "url_from": bl.get("url_from"),
            "domain_from": bl.get("domain_from"),
            "url_to": bl.get("url_to"),
            "anchor": bl.get("anchor"),
            "dofollow": bl.get("dofollow"),
            "domain_from_rank": bl.get("domain_from_rank"),
            "first_seen": bl.get("first_seen"),
            "last_seen": bl.get("last_seen"),
        })

    # Also from top_backlinks
    for bl in result.top_backlinks:
        if not any(b.get("url_from") == bl.get("url_from") for b in backlinks):
            backlinks.append({
                "url_from": bl.get("url_from"),
                "domain_from": bl.get("domain_from"),
                "anchor": bl.get("anchor"),
                "dofollow": bl.get("dofollow"),
                "domain_from_rank": bl.get("rank") or bl.get("domain_from_rank"),
            })

    return backlinks


def extract_technical_from_result(result: CollectionResult) -> dict:
    """Extract technical metrics from collection result."""
    technical = result.technical_audit or result.technical_audits or {}
    baseline = result.technical_baseline or {}

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


def prepare_validation_data(result: CollectionResult) -> dict:
    """Prepare data structure for validation."""
    return {
        "keywords": extract_keywords_from_result(result),
        "competitors": extract_competitors_from_result(result),
        "backlinks": extract_backlinks_from_result(result),
        "domain_info": {
            "domain_rating": result.domain_overview.get("domain_rank") or result.backlink_summary.get("domain_rank"),
            "organic_traffic": result.domain_overview.get("organic_traffic"),
            "organic_keywords": result.domain_overview.get("organic_keywords"),
            "referring_domains": result.backlink_summary.get("referring_domains"),
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

        # Store all entities
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
            f"Stored: {keywords_count} keywords, {competitors_count} competitors, "
            f"{backlinks_count} backlinks"
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

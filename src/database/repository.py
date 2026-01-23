"""
Repository Layer - Clean Interface for Data Operations

Provides simple functions to store and retrieve data.
Handles all SQLAlchemy complexity internally.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_

from .models import (
    Client, Domain, AnalysisRun, APICall, Keyword, Competitor,
    Backlink, Page, TechnicalMetrics, AgentOutput, Report,
    DomainMetricsHistory, CompetitorType, AnalysisStatus, DataQualityLevel,
    SearchIntent,
    # New intelligence tables
    SERPFeature, SERPFeatureType,
    KeywordGap,
    ReferringDomain,
    RankingHistory,
    ContentCluster,
    AIVisibility, AIVisibilitySource,
    LocalRanking,
    SERPCompetitor,
)
from .session import get_db_context, get_db_session

logger = logging.getLogger(__name__)


# =============================================================================
# ANALYSIS RUN MANAGEMENT
# =============================================================================

def create_analysis_run(
    domain: str,
    config: Dict[str, Any] = None,
    client_email: Optional[str] = None,
) -> UUID:
    """
    Create a new analysis run.

    This is the entry point for every analysis job.

    Returns:
        UUID of the created analysis run
    """
    with get_db_context() as db:
        # Find or create domain
        domain_obj = db.query(Domain).filter(Domain.domain == domain).first()
        if not domain_obj:
            domain_obj = Domain(domain=domain)
            db.add(domain_obj)
            db.flush()

        # Create analysis run
        run = AnalysisRun(
            domain_id=domain_obj.id,
            status=AnalysisStatus.PENDING,
            config=config or {},
            started_at=datetime.utcnow(),
        )
        db.add(run)
        db.flush()

        run_id = run.id
        logger.info(f"Created analysis run {run_id} for {domain}")

        return run_id


def update_run_status(
    run_id: UUID,
    status: AnalysisStatus,
    phase: Optional[str] = None,
    progress: Optional[int] = None,
    error_message: Optional[str] = None,
):
    """Update analysis run status"""
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(run_id)
        if run:
            run.status = status
            if phase:
                run.current_phase = phase
            if progress is not None:
                run.progress_percent = progress
            if error_message:
                run.error_message = error_message
            if status == AnalysisStatus.COMPLETED:
                run.completed_at = datetime.utcnow()
                if run.started_at:
                    run.duration_seconds = int((run.completed_at - run.started_at).total_seconds())


def complete_run(
    run_id: UUID,
    quality_level: DataQualityLevel,
    quality_score: float,
    quality_issues: List[Dict] = None,
):
    """Mark analysis run as complete with quality assessment"""
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(run_id)
        if run:
            run.status = AnalysisStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.data_quality = quality_level
            run.data_quality_score = quality_score
            run.quality_issues = quality_issues or []
            if run.started_at:
                run.duration_seconds = int((run.completed_at - run.started_at).total_seconds())
            logger.info(f"Run {run_id} completed: {quality_level.value} ({quality_score:.1f}%)")


def fail_run(run_id: UUID, error_message: str, errors: List[Dict] = None):
    """Mark analysis run as failed"""
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(run_id)
        if run:
            run.status = AnalysisStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = error_message
            run.errors = errors or []
            logger.error(f"Run {run_id} failed: {error_message}")


# =============================================================================
# API CALL LOGGING
# =============================================================================

def log_api_call(
    run_id: UUID,
    endpoint: str,
    phase: str,
    request_payload: Dict,
    response_payload: Dict,
    http_status: int,
    response_time_ms: int,
    cost_usd: float = 0.0,
) -> UUID:
    """
    Log an API call for debugging and cost tracking.

    Every DataForSEO call should go through here.
    """
    with get_db_context() as db:
        # Calculate data completeness
        data_completeness = _calculate_completeness(response_payload)

        api_call = APICall(
            analysis_run_id=run_id,
            endpoint=endpoint,
            phase=phase,
            request_payload=request_payload,
            response_payload=response_payload,
            http_status=http_status,
            response_time_ms=response_time_ms,
            cost_usd=cost_usd,
            is_valid=http_status == 200,
            data_completeness=data_completeness,
        )
        db.add(api_call)

        # Update run totals
        run = db.query(AnalysisRun).get(run_id)
        if run:
            run.api_calls_count = (run.api_calls_count or 0) + 1
            run.api_cost_usd = (run.api_cost_usd or 0) + cost_usd

        db.flush()
        return api_call.id


def _calculate_completeness(response: Dict) -> float:
    """Estimate data completeness of API response"""
    if not response:
        return 0.0

    # Check for common success indicators
    if response.get("status_code") == 20000:  # DataForSEO success
        tasks = response.get("tasks", [])
        if tasks and tasks[0].get("result"):
            result = tasks[0]["result"]
            if isinstance(result, list) and len(result) > 0:
                return 100.0
            elif isinstance(result, dict):
                return 80.0
        return 50.0  # Success but sparse data

    return 0.0


# =============================================================================
# KEYWORD STORAGE
# =============================================================================

def store_keywords(
    run_id: UUID,
    domain_id: UUID,
    keywords: List[Dict[str, Any]],
    source: str = "collected",
) -> int:
    """
    Store keywords from collection.

    Args:
        run_id: Analysis run ID
        domain_id: Domain ID
        keywords: List of keyword dicts from collector
        source: Where keywords came from (ranked, universe, related, gap)

    Returns:
        Number of keywords stored
    """
    if not keywords:
        return 0

    with get_db_context() as db:
        count = 0
        for kw_data in keywords:
            keyword = Keyword(
                analysis_run_id=run_id,
                domain_id=domain_id,
                keyword=kw_data.get("keyword", ""),
                keyword_normalized=kw_data.get("keyword", "").lower().strip(),
                source=source,
                # Search metrics
                search_volume=kw_data.get("search_volume"),
                cpc=kw_data.get("cpc"),
                competition=kw_data.get("competition"),
                competition_level=kw_data.get("competition_level"),
                keyword_difficulty=kw_data.get("keyword_difficulty"),
                # Position data
                current_position=kw_data.get("position") or kw_data.get("current_position"),
                ranking_url=kw_data.get("url") or kw_data.get("ranking_url"),
                # Traffic
                estimated_traffic=kw_data.get("etv") or kw_data.get("estimated_traffic"),
                traffic_cost=kw_data.get("traffic_cost"),
                # Intent
                search_intent=_map_intent(kw_data.get("intent")),
                # Historical
                monthly_searches=kw_data.get("monthly_searches"),
            )
            db.add(keyword)
            count += 1

        logger.info(f"Stored {count} keywords for run {run_id}")
        return count


def _map_intent(intent_str: Optional[str]) -> Optional[SearchIntent]:
    """Map intent string to enum"""
    if not intent_str:
        return None
    mapping = {
        "informational": SearchIntent.INFORMATIONAL,
        "navigational": SearchIntent.NAVIGATIONAL,
        "transactional": SearchIntent.TRANSACTIONAL,
        "commercial": SearchIntent.COMMERCIAL,
        "commercial_investigation": SearchIntent.COMMERCIAL,
    }
    return mapping.get(intent_str.lower())


# =============================================================================
# COMPETITOR STORAGE
# =============================================================================

def store_competitors(
    run_id: UUID,
    domain_id: UUID,
    competitors: List[Dict[str, Any]],
) -> int:
    """
    Store competitors with proper classification.

    THIS SOLVES THE FACEBOOK PROBLEM - we classify each competitor.

    Returns:
        Number of competitors stored
    """
    if not competitors:
        return 0

    with get_db_context() as db:
        count = 0
        for comp_data in competitors:
            # Get or map competitor type
            comp_type = _map_competitor_type(comp_data.get("competitor_type"))

            competitor = Competitor(
                analysis_run_id=run_id,
                domain_id=domain_id,
                competitor_domain=comp_data.get("domain") or comp_data.get("competitor_domain", ""),
                # Classification
                competitor_type=comp_type,
                detection_method=comp_data.get("detection_method", "unknown"),
                detection_confidence=comp_data.get("confidence", 0.5),
                # Relationship
                keyword_overlap_count=comp_data.get("common_keywords") or comp_data.get("keyword_overlap_count"),
                keyword_overlap_percent=comp_data.get("overlap_percent"),
                shared_backlinks_count=comp_data.get("shared_backlinks"),
                # Metrics
                organic_traffic=comp_data.get("organic_traffic") or comp_data.get("etv"),
                organic_keywords=comp_data.get("keywords_count") or comp_data.get("organic_keywords"),
                domain_rating=comp_data.get("domain_rating") or comp_data.get("rank"),
                referring_domains=comp_data.get("referring_domains"),
                avg_position=comp_data.get("avg_position"),
            )
            db.add(competitor)
            count += 1

        logger.info(f"Stored {count} competitors for run {run_id}")
        return count


def _map_competitor_type(type_str: Optional[str]) -> CompetitorType:
    """Map competitor type string to enum"""
    if not type_str:
        return CompetitorType.UNKNOWN
    mapping = {
        "true_competitor": CompetitorType.TRUE_COMPETITOR,
        "affiliate": CompetitorType.AFFILIATE,
        "media": CompetitorType.MEDIA,
        "government": CompetitorType.GOVERNMENT,
        "platform": CompetitorType.PLATFORM,
    }
    return mapping.get(type_str.lower(), CompetitorType.UNKNOWN)


# =============================================================================
# BACKLINK STORAGE
# =============================================================================

def store_backlinks(
    run_id: UUID,
    domain_id: UUID,
    backlinks: List[Dict[str, Any]],
) -> int:
    """Store backlinks from collection"""
    if not backlinks:
        return 0

    with get_db_context() as db:
        count = 0
        for bl_data in backlinks:
            backlink = Backlink(
                analysis_run_id=run_id,
                domain_id=domain_id,
                source_url=bl_data.get("url_from") or bl_data.get("source_url", ""),
                source_domain=bl_data.get("domain_from") or bl_data.get("source_domain", ""),
                target_url=bl_data.get("url_to") or bl_data.get("target_url"),
                # Attributes
                anchor_text=bl_data.get("anchor"),
                link_type=bl_data.get("link_type"),
                is_dofollow=bl_data.get("dofollow"),
                is_sponsored=bl_data.get("is_sponsored"),
                is_ugc=bl_data.get("is_ugc"),
                # Metrics
                source_domain_rating=bl_data.get("domain_from_rank") or bl_data.get("source_domain_rating"),
                source_page_rating=bl_data.get("page_from_rank"),
                source_traffic=bl_data.get("page_from_external_links"),
                # Temporal
                first_seen=_parse_datetime(bl_data.get("first_seen")),
                last_seen=_parse_datetime(bl_data.get("last_seen")),
            )
            db.add(backlink)
            count += 1

        logger.info(f"Stored {count} backlinks for run {run_id}")
        return count


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except:
        return None


# =============================================================================
# TECHNICAL METRICS STORAGE
# =============================================================================

def store_technical_metrics(
    run_id: UUID,
    domain_id: UUID,
    metrics: Dict[str, Any],
) -> UUID:
    """Store technical metrics from Lighthouse/CWV"""
    with get_db_context() as db:
        tech = TechnicalMetrics(
            analysis_run_id=run_id,
            domain_id=domain_id,
            # Lighthouse
            performance_score=metrics.get("performance_score"),
            accessibility_score=metrics.get("accessibility_score"),
            best_practices_score=metrics.get("best_practices_score"),
            seo_score=metrics.get("seo_score"),
            # CWV
            lcp_ms=metrics.get("lcp"),
            fid_ms=metrics.get("fid"),
            cls=metrics.get("cls"),
            inp_ms=metrics.get("inp"),
            # Issues
            critical_issues=metrics.get("critical_issues"),
            warnings=metrics.get("warnings"),
            issues_detail=metrics.get("issues"),
            # Technologies
            technologies=metrics.get("technologies"),
        )
        db.add(tech)
        db.flush()

        logger.info(f"Stored technical metrics for run {run_id}")
        return tech.id


# =============================================================================
# AGENT OUTPUT STORAGE
# =============================================================================

def store_agent_output(
    run_id: UUID,
    agent_name: str,
    input_summary: Dict[str, Any],
    output_raw: str,
    output_parsed: Dict[str, Any] = None,
    quality_score: float = None,
    passed_quality_gate: bool = None,
    model_used: str = None,
    cost_usd: float = None,
    latency_ms: int = None,
) -> UUID:
    """
    Store agent output for learning and debugging.

    Every AI agent call should store its output here.
    """
    with get_db_context() as db:
        agent_output = AgentOutput(
            analysis_run_id=run_id,
            agent_name=agent_name,
            input_summary=input_summary,
            output_raw=output_raw,
            output_parsed=output_parsed,
            quality_score=quality_score,
            passed_quality_gate=passed_quality_gate,
            model_used=model_used,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
        db.add(agent_output)

        # Update run AI cost
        run = db.query(AnalysisRun).get(run_id)
        if run and cost_usd:
            run.ai_cost_usd = (run.ai_cost_usd or 0) + cost_usd

        db.flush()
        logger.info(f"Stored {agent_name} output for run {run_id}")
        return agent_output.id


# =============================================================================
# REPORT STORAGE
# =============================================================================

def store_report(
    run_id: UUID,
    domain_id: UUID,
    title: str,
    executive_summary: str,
    content: Dict[str, Any],
    pdf_path: str = None,
    overall_quality_score: float = None,
) -> UUID:
    """Store generated report"""
    with get_db_context() as db:
        report = Report(
            analysis_run_id=run_id,
            domain_id=domain_id,
            title=title,
            executive_summary=executive_summary,
            content=content,
            pdf_path=pdf_path,
            pdf_generated_at=datetime.utcnow() if pdf_path else None,
            overall_quality_score=overall_quality_score,
        )
        db.add(report)
        db.flush()

        logger.info(f"Stored report for run {run_id}")
        return report.id


def mark_report_delivered(report_id: UUID, email: str):
    """Mark report as delivered"""
    with get_db_context() as db:
        report = db.query(Report).get(report_id)
        if report:
            report.delivered_to = email
            report.delivered_at = datetime.utcnow()


# =============================================================================
# DATA RETRIEVAL
# =============================================================================

def get_run_data(run_id: UUID) -> Dict[str, Any]:
    """
    Get all data for an analysis run.

    Used to feed data to AI agents.
    """
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(run_id)
        if not run:
            return {}

        domain = db.query(Domain).get(run.domain_id)

        keywords = db.query(Keyword).filter(Keyword.analysis_run_id == run_id).all()
        competitors = db.query(Competitor).filter(Competitor.analysis_run_id == run_id).all()
        backlinks = db.query(Backlink).filter(Backlink.analysis_run_id == run_id).all()
        pages = db.query(Page).filter(Page.analysis_run_id == run_id).all()
        tech = db.query(TechnicalMetrics).filter(TechnicalMetrics.analysis_run_id == run_id).first()

        return {
            "run_id": str(run_id),
            "domain": domain.domain if domain else None,
            "domain_info": {
                "industry": domain.industry if domain else None,
                "business_type": domain.business_type if domain else None,
                "target_market": domain.target_market if domain else None,
            } if domain else {},
            "keywords": [_keyword_to_dict(k) for k in keywords],
            "competitors": [_competitor_to_dict(c) for c in competitors],
            "backlinks": [_backlink_to_dict(b) for b in backlinks],
            "pages": [_page_to_dict(p) for p in pages],
            "technical": _tech_to_dict(tech) if tech else {},
        }


def _keyword_to_dict(k: Keyword) -> Dict:
    return {
        "keyword": k.keyword,
        "search_volume": k.search_volume,
        "cpc": k.cpc,
        "competition": k.competition,
        "keyword_difficulty": k.keyword_difficulty,
        "current_position": k.current_position,
        "ranking_url": k.ranking_url,
        "estimated_traffic": k.estimated_traffic,
        "search_intent": k.search_intent.value if k.search_intent else None,
        "opportunity_score": k.opportunity_score,
    }


def _competitor_to_dict(c: Competitor) -> Dict:
    return {
        "competitor_domain": c.competitor_domain,
        "competitor_type": c.competitor_type.value if c.competitor_type else None,
        "keyword_overlap_count": c.keyword_overlap_count,
        "organic_traffic": c.organic_traffic,
        "organic_keywords": c.organic_keywords,
        "domain_rating": c.domain_rating,
        "threat_level": c.threat_level,
    }


def _backlink_to_dict(b: Backlink) -> Dict:
    return {
        "source_url": b.source_url,
        "source_domain": b.source_domain,
        "anchor_text": b.anchor_text,
        "is_dofollow": b.is_dofollow,
        "source_domain_rating": b.source_domain_rating,
        "link_quality_score": b.link_quality_score,
    }


def _page_to_dict(p: Page) -> Dict:
    return {
        "url": p.url,
        "title": p.title,
        "organic_traffic": p.organic_traffic,
        "organic_keywords": p.organic_keywords,
        "content_score": p.content_score,
        "kuck_recommendation": p.kuck_recommendation,
    }


def _tech_to_dict(t: TechnicalMetrics) -> Dict:
    return {
        "performance_score": t.performance_score,
        "accessibility_score": t.accessibility_score,
        "seo_score": t.seo_score,
        "lcp": t.lcp_ms,
        "fid": t.fid_ms,
        "cls": t.cls,
        "technologies": t.technologies,
    }


# =============================================================================
# STATISTICS
# =============================================================================

def get_run_stats(run_id: UUID) -> Dict[str, int]:
    """Get statistics for a run"""
    with get_db_context() as db:
        return {
            "keywords_count": db.query(Keyword).filter(Keyword.analysis_run_id == run_id).count(),
            "competitors_count": db.query(Competitor).filter(Competitor.analysis_run_id == run_id).count(),
            "backlinks_count": db.query(Backlink).filter(Backlink.analysis_run_id == run_id).count(),
            "pages_count": db.query(Page).filter(Page.analysis_run_id == run_id).count(),
            "api_calls_count": db.query(APICall).filter(APICall.analysis_run_id == run_id).count(),
            "agent_outputs_count": db.query(AgentOutput).filter(AgentOutput.analysis_run_id == run_id).count(),
            # New intelligence tables
            "serp_features_count": db.query(SERPFeature).filter(SERPFeature.analysis_run_id == run_id).count(),
            "keyword_gaps_count": db.query(KeywordGap).filter(KeywordGap.analysis_run_id == run_id).count(),
            "referring_domains_count": db.query(ReferringDomain).filter(ReferringDomain.analysis_run_id == run_id).count(),
            "content_clusters_count": db.query(ContentCluster).filter(ContentCluster.analysis_run_id == run_id).count(),
            "ai_visibility_count": db.query(AIVisibility).filter(AIVisibility.analysis_run_id == run_id).count(),
            "local_rankings_count": db.query(LocalRanking).filter(LocalRanking.analysis_run_id == run_id).count(),
            "serp_competitors_count": db.query(SERPCompetitor).filter(SERPCompetitor.analysis_run_id == run_id).count(),
        }


# =============================================================================
# SERP FEATURES STORAGE
# =============================================================================

def store_serp_features(
    run_id: UUID,
    domain_id: UUID,
    serp_data: List[Dict[str, Any]],
    ranked_keywords: List[Dict[str, Any]] = None,
) -> int:
    """
    Store SERP features (featured snippets, PAA, local packs, etc.)

    Maps from: phase2_keywords.serp_elements + phase4_ai_technical.live_serp_data
    """
    ranked_kw_set = {kw.get("keyword", "").lower() for kw in (ranked_keywords or [])}

    with get_db_context() as db:
        count = 0
        for item in serp_data:
            keyword = item.get("keyword", "")

            # Extract features from SERP data
            features_to_store = []

            # Featured snippets
            if item.get("featured_snippets_count", 0) > 0:
                features_to_store.append({
                    "type": SERPFeatureType.FEATURED_SNIPPET,
                    "data": item.get("featured_snippet_data", {}),
                })

            # People Also Ask
            if item.get("people_also_ask_count", 0) > 0:
                features_to_store.append({
                    "type": SERPFeatureType.PEOPLE_ALSO_ASK,
                    "data": {"questions": item.get("paa_questions", [])},
                })

            # Local Pack
            if item.get("local_pack_count", 0) > 0:
                features_to_store.append({
                    "type": SERPFeatureType.LOCAL_PACK,
                    "data": item.get("local_pack_data", {}),
                })

            # AI Overview
            if item.get("ai_overview", False) or item.get("has_ai_overview", False):
                features_to_store.append({
                    "type": SERPFeatureType.AI_OVERVIEW,
                    "data": item.get("ai_overview_data", {}),
                })

            # Knowledge Panel
            if item.get("knowledge_graph_count", 0) > 0:
                features_to_store.append({
                    "type": SERPFeatureType.KNOWLEDGE_PANEL,
                    "data": item.get("knowledge_panel_data", {}),
                })

            # Image Pack
            if item.get("image_pack", False):
                features_to_store.append({
                    "type": SERPFeatureType.IMAGE_PACK,
                    "data": {},
                })

            # Video Carousel
            if item.get("video_carousel", False):
                features_to_store.append({
                    "type": SERPFeatureType.VIDEO_CAROUSEL,
                    "data": {},
                })

            # Store each feature
            for feature_info in features_to_store:
                owned_by_target = keyword.lower() in ranked_kw_set

                serp_feature = SERPFeature(
                    analysis_run_id=run_id,
                    domain_id=domain_id,
                    keyword=keyword,
                    feature_type=feature_info["type"],
                    position=item.get("position", 1),
                    owned_by_target=owned_by_target,
                    owned_by_domain=item.get("owned_by"),
                    feature_data=feature_info["data"],
                    can_target=True,
                    opportunity_score=item.get("opportunity_score"),
                )
                db.add(serp_feature)
                count += 1

        logger.info(f"Stored {count} SERP features for run {run_id}")
        return count


# =============================================================================
# KEYWORD GAPS STORAGE
# =============================================================================

def store_keyword_gaps(
    run_id: UUID,
    domain_id: UUID,
    gaps_data: List[Dict[str, Any]],
    overlaps_data: List[Dict[str, Any]] = None,
) -> int:
    """
    Store keyword gaps - where competitors rank but target doesn't.

    Maps from: phase2_keywords.keyword_gaps + phase3_competitive.keyword_overlaps
    """
    # Build competitor positions from overlaps
    competitor_map = {}
    for overlap in (overlaps_data or []):
        competitor = overlap.get("competitor")
        for opp_kw in overlap.get("opportunity_keywords", []):
            kw = opp_kw.get("keyword", "").lower()
            if kw not in competitor_map:
                competitor_map[kw] = {}
            competitor_map[kw][competitor] = opp_kw.get("position")

    with get_db_context() as db:
        count = 0
        for gap in gaps_data:
            keyword = gap.get("keyword", "")
            keyword_lower = keyword.lower()

            # Get competitor positions for this keyword
            comp_positions = competitor_map.get(keyword_lower, {})
            best_comp = None
            best_pos = None
            if comp_positions:
                best_comp = min(comp_positions.keys(), key=lambda k: comp_positions[k] or 999)
                best_pos = comp_positions.get(best_comp)

            # Calculate priority based on volume and difficulty
            volume = gap.get("search_volume", 0) or 0
            difficulty = gap.get("difficulty", gap.get("keyword_difficulty", 50)) or 50
            if volume > 5000 and difficulty < 50:
                priority = "high"
            elif volume > 1000 or difficulty < 40:
                priority = "medium"
            else:
                priority = "low"

            keyword_gap = KeywordGap(
                analysis_run_id=run_id,
                domain_id=domain_id,
                keyword=keyword,
                keyword_normalized=keyword_lower,
                search_volume=volume,
                keyword_difficulty=difficulty,
                cpc=gap.get("cpc"),
                target_position=gap.get("target_position"),
                target_url=gap.get("target_url"),
                competitor_positions=comp_positions,
                best_competitor=best_comp,
                best_competitor_position=best_pos,
                competitor_count=gap.get("competitor_count", len(comp_positions)),
                avg_competitor_position=gap.get("avg_competitor_position"),
                opportunity_score=gap.get("opportunity_score"),
                priority=priority,
                estimated_traffic_potential=gap.get("traffic_potential"),
                suggested_content_type=gap.get("suggested_content_type"),
            )
            db.add(keyword_gap)
            count += 1

        logger.info(f"Stored {count} keyword gaps for run {run_id}")
        return count


# =============================================================================
# REFERRING DOMAINS STORAGE
# =============================================================================

def store_referring_domains(
    run_id: UUID,
    domain_id: UUID,
    ref_domains_data: List[Dict[str, Any]],
    backlinks_data: List[Dict[str, Any]] = None,
    anchor_data: List[Dict[str, Any]] = None,
) -> int:
    """
    Store referring domains with aggregate backlink analysis.

    Maps from: phase3_competitive.referring_domains + backlinks + anchor_distribution
    """
    # Build backlink aggregates per domain
    domain_backlinks = {}
    for bl in (backlinks_data or []):
        source = bl.get("source_domain") or bl.get("domain_from", "")
        if not source:
            continue
        if source not in domain_backlinks:
            domain_backlinks[source] = {
                "count": 0, "dofollow": 0, "nofollow": 0,
                "text": 0, "image": 0, "pages": set(), "anchors": {}
            }
        domain_backlinks[source]["count"] += 1
        if bl.get("dofollow") or bl.get("is_dofollow"):
            domain_backlinks[source]["dofollow"] += 1
        else:
            domain_backlinks[source]["nofollow"] += 1
        if bl.get("link_type") == "text":
            domain_backlinks[source]["text"] += 1
        elif bl.get("link_type") == "image":
            domain_backlinks[source]["image"] += 1
        target = bl.get("target_url", "")
        if target:
            domain_backlinks[source]["pages"].add(target)
        anchor = bl.get("anchor", "")
        if anchor:
            domain_backlinks[source]["anchors"][anchor] = domain_backlinks[source]["anchors"].get(anchor, 0) + 1

    with get_db_context() as db:
        count = 0
        for ref_dom in ref_domains_data:
            referring_domain = ref_dom.get("domain", "")
            if not referring_domain:
                continue

            # Get aggregate data from backlinks
            bl_agg = domain_backlinks.get(referring_domain, {})
            linked_pages = list(bl_agg.get("pages", set()))[:100]  # Limit to 100
            anchors = bl_agg.get("anchors", {})
            primary_anchor = max(anchors.keys(), key=lambda k: anchors[k]) if anchors else None

            ref_domain_obj = ReferringDomain(
                analysis_run_id=run_id,
                domain_id=domain_id,
                referring_domain=referring_domain,
                domain_rating=ref_dom.get("domain_rank") or ref_dom.get("domain_rating"),
                organic_traffic=ref_dom.get("organic_traffic"),
                organic_keywords=ref_dom.get("organic_keywords"),
                backlink_count=ref_dom.get("backlinks") or bl_agg.get("count", 0),
                dofollow_count=bl_agg.get("dofollow", 0),
                nofollow_count=bl_agg.get("nofollow", 0),
                text_links=bl_agg.get("text", 0),
                image_links=bl_agg.get("image", 0),
                linked_pages=linked_pages,
                unique_pages_linked=len(linked_pages),
                anchor_distribution=anchors,
                primary_anchor=primary_anchor,
                quality_score=ref_dom.get("quality_score"),
                spam_score=ref_dom.get("spam_score"),
                domain_type=ref_dom.get("domain_type"),
                first_seen=_parse_datetime(ref_dom.get("first_seen")),
                last_seen=_parse_datetime(ref_dom.get("last_seen")),
                is_lost=ref_dom.get("is_broken", False),
            )
            db.add(ref_domain_obj)
            count += 1

        logger.info(f"Stored {count} referring domains for run {run_id}")
        return count


# =============================================================================
# RANKING HISTORY STORAGE
# =============================================================================

def store_ranking_history(
    run_id: UUID,
    domain_id: UUID,
    ranked_keywords: List[Dict[str, Any]],
    timestamp: datetime = None,
) -> int:
    """
    Store ranking history snapshot for trend tracking.

    Maps from: phase2_keywords.ranked_keywords
    """
    timestamp = timestamp or datetime.utcnow()

    with get_db_context() as db:
        count = 0
        for kw in ranked_keywords:
            keyword = kw.get("keyword", "")
            if not keyword:
                continue

            current_pos = kw.get("position") or kw.get("rank_absolute")
            previous_pos = kw.get("previous_position")
            pos_change = None
            if current_pos and previous_pos:
                pos_change = previous_pos - current_pos  # Positive = improved

            ranking = RankingHistory(
                domain_id=domain_id,
                analysis_run_id=run_id,
                keyword=keyword,
                keyword_normalized=keyword.lower(),
                position=current_pos,
                previous_position=previous_pos,
                position_change=pos_change,
                ranking_url=kw.get("url") or kw.get("ranking_url"),
                previous_url=kw.get("previous_url"),
                estimated_traffic=kw.get("traffic") or kw.get("etv"),
                recorded_at=timestamp,
            )
            db.add(ranking)
            count += 1

        logger.info(f"Stored {count} ranking history records for run {run_id}")
        return count


# =============================================================================
# CONTENT CLUSTERS STORAGE
# =============================================================================

def store_content_clusters(
    run_id: UUID,
    domain_id: UUID,
    clusters_data: List[Dict[str, Any]],
    ranked_keywords: List[Dict[str, Any]] = None,
) -> int:
    """
    Store content clusters for topic authority analysis.

    Maps from: phase2_keywords.keyword_clusters
    """
    # Build ranking lookup
    ranking_map = {}
    for kw in (ranked_keywords or []):
        keyword_lower = kw.get("keyword", "").lower()
        ranking_map[keyword_lower] = {
            "position": kw.get("position") or kw.get("rank_absolute"),
            "url": kw.get("url") or kw.get("ranking_url"),
            "traffic": kw.get("traffic") or kw.get("etv", 0),
        }

    with get_db_context() as db:
        count = 0
        for cluster in clusters_data:
            seed = cluster.get("seed_keyword", "")
            if not seed:
                continue

            # Get cluster keywords
            cluster_keywords = cluster.get("keywords", [])
            if isinstance(cluster_keywords, list) and len(cluster_keywords) > 0:
                if isinstance(cluster_keywords[0], str):
                    # Convert simple list to dict format
                    cluster_keywords = [{"keyword": kw} for kw in cluster_keywords]

            # Calculate cluster metrics
            total_kw = len(cluster_keywords)
            ranking_kw = 0
            total_volume = 0
            total_traffic = 0
            positions = []
            missing_subtopics = []

            for kw_item in cluster_keywords:
                kw = kw_item.get("keyword", "") if isinstance(kw_item, dict) else kw_item
                kw_lower = kw.lower()
                vol = kw_item.get("volume", 0) if isinstance(kw_item, dict) else 0
                total_volume += vol or 0

                ranking_info = ranking_map.get(kw_lower)
                if ranking_info and ranking_info.get("position"):
                    ranking_kw += 1
                    positions.append(ranking_info["position"])
                    total_traffic += ranking_info.get("traffic", 0) or 0
                else:
                    missing_subtopics.append({"keyword": kw, "volume": vol})

            avg_position = sum(positions) / len(positions) if positions else None
            content_completeness = (ranking_kw / total_kw * 100) if total_kw > 0 else 0

            # Priority based on volume and completeness
            if total_volume > 50000 and content_completeness < 50:
                priority = "high"
            elif total_volume > 10000:
                priority = "medium"
            else:
                priority = "low"

            # Check pillar
            pillar_info = ranking_map.get(seed.lower(), {})

            cluster_obj = ContentCluster(
                analysis_run_id=run_id,
                domain_id=domain_id,
                cluster_name=seed,
                cluster_slug=seed.lower().replace(" ", "-"),
                pillar_keyword=seed,
                pillar_url=pillar_info.get("url"),
                pillar_position=pillar_info.get("position"),
                total_keywords=total_kw,
                ranking_keywords=ranking_kw,
                avg_position=avg_position,
                total_search_volume=cluster.get("total_volume") or total_volume,
                total_traffic=total_traffic,
                keywords=cluster_keywords[:100],  # Limit to 100
                missing_subtopics=missing_subtopics[:50],  # Limit to 50
                content_gap_count=len(missing_subtopics),
                cluster_difficulty=cluster.get("avg_difficulty"),
                topical_authority_score=content_completeness,
                content_completeness=content_completeness,
                priority=priority,
            )
            db.add(cluster_obj)
            count += 1

        logger.info(f"Stored {count} content clusters for run {run_id}")
        return count


# =============================================================================
# AI VISIBILITY STORAGE
# =============================================================================

def store_ai_visibility(
    run_id: UUID,
    domain_id: UUID,
    target_domain: str,
    llm_mentions: Dict[str, Any] = None,
    brand_mentions: List[Dict[str, Any]] = None,
) -> int:
    """
    Store AI visibility data (GEO tracking).

    Maps from: phase4_ai_technical.llm_mentions + brand_mentions
    """
    with get_db_context() as db:
        count = 0

        # Process LLM mentions (ChatGPT, Google AI)
        if llm_mentions:
            for platform, data in llm_mentions.items():
                if not isinstance(data, dict):
                    continue

                # Map platform to source enum
                source_map = {
                    "chatgpt": AIVisibilitySource.CHATGPT,
                    "google_ai": AIVisibilitySource.GOOGLE_AI_OVERVIEW,
                    "perplexity": AIVisibilitySource.PERPLEXITY,
                    "claude": AIVisibilitySource.CLAUDE,
                    "bing_copilot": AIVisibilitySource.BING_COPILOT,
                }
                ai_source = source_map.get(platform.lower(), AIVisibilitySource.CHATGPT)

                items = data.get("items", [])
                for item in items:
                    query = item.get("query") or item.get("keyword", "")
                    if not query:
                        continue

                    # Check if target domain is mentioned/cited
                    mentioned_domains = item.get("mentioned_domains", [])
                    cited_urls = item.get("cited_urls", [])

                    is_mentioned = target_domain.lower() in str(mentioned_domains).lower()
                    is_cited = target_domain.lower() in str(cited_urls).lower()

                    # Find citation URL if cited
                    citation_url = None
                    citation_position = None
                    for i, url in enumerate(cited_urls):
                        if target_domain.lower() in url.lower():
                            citation_url = url
                            citation_position = i + 1
                            break

                    # Get competitors mentioned
                    competitors = [d for d in mentioned_domains if d.lower() != target_domain.lower()]

                    ai_viz = AIVisibility(
                        analysis_run_id=run_id,
                        domain_id=domain_id,
                        query=query,
                        topic_category=item.get("category"),
                        ai_source=ai_source,
                        is_mentioned=is_mentioned,
                        is_cited=is_cited,
                        is_recommended=item.get("is_recommended", False),
                        citation_url=citation_url,
                        citation_context=item.get("context"),
                        citation_position=citation_position,
                        competitors_mentioned=competitors[:10],
                        total_citations=len(cited_urls),
                        sentiment=item.get("sentiment"),
                        authority_signal=item.get("authority_signal", False),
                    )
                    db.add(ai_viz)
                    count += 1

        # Process brand mentions (web mentions with sentiment)
        for mention in (brand_mentions or []):
            url = mention.get("url", "")
            if not url:
                continue

            ai_viz = AIVisibility(
                analysis_run_id=run_id,
                domain_id=domain_id,
                query=mention.get("title", "Brand mention"),
                ai_source=AIVisibilitySource.GOOGLE_AI_OVERVIEW,  # Default for web mentions
                is_mentioned=True,
                is_cited=True,
                citation_url=url,
                citation_context=mention.get("snippet"),
                cited_content_type=mention.get("content_type"),
                sentiment=mention.get("sentiment"),
            )
            db.add(ai_viz)
            count += 1

        logger.info(f"Stored {count} AI visibility records for run {run_id}")
        return count


# =============================================================================
# LOCAL RANKINGS STORAGE
# =============================================================================

def store_local_rankings(
    run_id: UUID,
    domain_id: UUID,
    local_data: List[Dict[str, Any]],
    gbp_data: Dict[str, Any] = None,
) -> int:
    """
    Store local rankings (Google Business Profile, local pack).

    Maps from: phase4_ai_technical.live_serp_data (local features)
    """
    gbp = gbp_data or {}

    with get_db_context() as db:
        count = 0
        for item in local_data:
            keyword = item.get("keyword", "")
            if not keyword:
                continue

            local_pack = item.get("local_pack", {})
            if not local_pack and not item.get("local_pack_position"):
                continue

            local_ranking = LocalRanking(
                analysis_run_id=run_id,
                domain_id=domain_id,
                location_name=gbp.get("name"),
                address=gbp.get("address"),
                city=item.get("city") or gbp.get("city"),
                region=item.get("region") or gbp.get("region"),
                country=item.get("country") or gbp.get("country"),
                postal_code=gbp.get("postal_code"),
                latitude=gbp.get("latitude"),
                longitude=gbp.get("longitude"),
                gbp_name=gbp.get("name"),
                gbp_category=gbp.get("category"),
                gbp_rating=gbp.get("rating"),
                gbp_review_count=gbp.get("review_count"),
                gbp_url=gbp.get("url"),
                keyword=keyword,
                search_volume=item.get("search_volume"),
                local_pack_position=item.get("local_pack_position"),
                organic_position=item.get("organic_position"),
                maps_position=item.get("maps_position"),
                local_pack_competitors=local_pack.get("competitors", [])[:10],
                prominence_score=item.get("prominence_score"),
            )
            db.add(local_ranking)
            count += 1

        logger.info(f"Stored {count} local rankings for run {run_id}")
        return count


# =============================================================================
# SERP COMPETITORS STORAGE
# =============================================================================

def store_serp_competitors(
    run_id: UUID,
    domain_id: UUID,
    serp_data: List[Dict[str, Any]],
    competitor_metrics: Dict[str, Dict] = None,
) -> int:
    """
    Store per-keyword SERP competitors.

    Maps from: phase2_keywords.serp_elements + phase3_competitive.competitor_analysis
    """
    comp_metrics = competitor_metrics or {}

    with get_db_context() as db:
        count = 0
        for item in serp_data:
            keyword = item.get("keyword", "")
            if not keyword:
                continue

            # Get top 10 competitors for this keyword
            serp_results = item.get("serp_results", item.get("organic_results", []))
            for result in serp_results[:10]:
                competitor_domain = result.get("domain", "")
                if not competitor_domain:
                    continue

                # Get metrics for this competitor if available
                metrics = comp_metrics.get(competitor_domain, {})

                serp_comp = SERPCompetitor(
                    analysis_run_id=run_id,
                    domain_id=domain_id,
                    keyword=keyword,
                    competitor_domain=competitor_domain,
                    competitor_url=result.get("url"),
                    position=result.get("position", result.get("rank_absolute")),
                    page_title=result.get("title"),
                    page_backlinks=result.get("backlinks") or metrics.get("backlinks"),
                    page_referring_domains=result.get("referring_domains"),
                    page_domain_rating=metrics.get("domain_rank") or metrics.get("domain_rating"),
                    content_type=result.get("content_type"),
                    word_count=result.get("word_count"),
                    has_schema=result.get("has_schema", False),
                    schema_types=result.get("schema_types", []),
                    serp_features_owned=result.get("serp_features", []),
                    is_beatable=result.get("is_beatable"),
                    difficulty_to_outrank=result.get("difficulty"),
                )
                db.add(serp_comp)
                count += 1

        logger.info(f"Stored {count} SERP competitors for run {run_id}")
        return count

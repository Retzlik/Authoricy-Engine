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
    SearchIntent
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
        }

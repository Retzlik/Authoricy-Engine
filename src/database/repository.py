"""
Repository Layer - Clean Interface for Data Operations

Provides simple functions to store and retrieve data.
Handles all SQLAlchemy complexity internally.

Includes cache integration:
- Triggers cache precomputation on analysis completion
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
    # Greenfield intelligence tables
    AnalysisMode,
    CompetitorPurpose,
    GreenfieldAnalysis,
    CompetitorIntelligenceSession,
    GreenfieldCompetitor,
)
from .session import get_db_context, get_db_session

logger = logging.getLogger(__name__)


# =============================================================================
# CACHE INTEGRATION HELPERS
# =============================================================================

def _trigger_cache_operations(run_id: UUID, domain_id: UUID, db: Session):
    """
    Trigger cache precomputation after analysis completion.

    Uses a background thread to avoid blocking the main request.
    Cache operations are non-critical - failures are logged but don't fail the operation.
    """
    import threading

    def _run_in_thread():
        """Run cache operations in a separate thread with its own db session."""
        try:
            # Import here to avoid circular imports
            from src.cache.precomputation import trigger_precomputation

            # Trigger precomputation with a new db session
            with get_db_context() as new_db:
                result = trigger_precomputation(run_id, new_db)
                logger.info(
                    f"Precomputation complete for {run_id}: "
                    f"{result['components_computed']} components in {result['duration_seconds']:.2f}s"
                )

        except ImportError as e:
            # Cache module not available - that's OK, caching is optional
            logger.debug(f"Cache module not available: {e}")
        except Exception as e:
            # Log but don't fail - cache operations are non-critical
            logger.warning(f"Cache operations failed for {run_id}: {e}")

    # Start background thread (non-blocking)
    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
    logger.debug(f"Started cache precomputation thread for {run_id}")


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
    trigger_cache: bool = True,
):
    """
    Mark analysis run as complete with quality assessment.

    Args:
        run_id: The analysis run ID
        quality_level: Data quality level (EXCELLENT, GOOD, FAIR, POOR, INVALID)
        quality_score: Numeric quality score (0-100)
        quality_issues: List of quality issues found
        trigger_cache: Whether to trigger cache invalidation and precomputation
    """
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

            # Trigger cache operations in background (non-blocking)
            if trigger_cache:
                _trigger_cache_operations(run_id, run.domain_id, db)


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
                # Scoring - calculated opportunity score from collection
                opportunity_score=kw_data.get("opportunity_score"),
                # Clustering - parent_topic from DataForSEO for semantic grouping
                parent_topic=kw_data.get("parent_topic"),
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


# =============================================================================
# CONTEXT INTELLIGENCE STORAGE
# =============================================================================

def store_context_intelligence(
    run_id: UUID,
    domain_id: UUID,
    context_result: "ContextIntelligenceResult",
) -> UUID:
    """
    Store Context Intelligence results.

    This persists the pre-collection intelligence for:
    - Reuse in future analyses
    - Learning and improvement
    - Audit trail

    Args:
        run_id: Analysis run ID
        domain_id: Domain ID
        context_result: ContextIntelligenceResult from orchestrator

    Returns:
        ID of created ContextIntelligence record
    """
    from .models import (
        ContextIntelligence,
        ValidatedCompetitorRecord,
        MarketOpportunityRecord,
        ValidatedCompetitorType,
    )

    def _convert_competitor_type(type_value: Optional[str]) -> ValidatedCompetitorType:
        """Convert string competitor type to enum, with safe fallback."""
        if not type_value:
            return ValidatedCompetitorType.DIRECT
        type_upper = type_value.upper()
        try:
            return ValidatedCompetitorType[type_upper]
        except KeyError:
            # Map common variations
            mapping = {
                "SEO_COMPETITOR": ValidatedCompetitorType.SEO,
                "CONTENT_COMPETITOR": ValidatedCompetitorType.CONTENT,
                "BUSINESS": ValidatedCompetitorType.DIRECT,
                "UNKNOWN": ValidatedCompetitorType.SEO,  # Default to SEO for unknowns
            }
            return mapping.get(type_upper, ValidatedCompetitorType.SEO)

    with get_db_context() as db:
        # Clean up existing market opportunities for this domain to avoid duplicate key errors
        # (unique constraint on domain_id, region, language)
        db.query(MarketOpportunityRecord).filter(
            MarketOpportunityRecord.domain_id == domain_id
        ).delete(synchronize_session=False)
        # Create main context intelligence record
        context_record = ContextIntelligence(
            domain_id=domain_id,
            analysis_run_id=run_id,
            # User inputs
            declared_market=context_result.market_validation.declared_primary if context_result.market_validation else None,
            declared_language=context_result.market_validation.declared_language if context_result.market_validation else None,
            declared_goal=context_result.business_context.primary_goal.value if context_result.business_context and context_result.business_context.primary_goal else None,
            user_provided_competitors=context_result.competitor_validation.user_provided if context_result.competitor_validation else [],
            # Resolved market (Phase 2 - single source of truth)
            resolved_market_code=context_result.resolved_market.code if context_result.resolved_market else None,
            resolved_market_name=context_result.resolved_market.name if context_result.resolved_market else None,
            resolved_location_code=context_result.resolved_market.location_code if context_result.resolved_market else None,
            resolved_language_code=context_result.resolved_market.language_code if context_result.resolved_market else None,
            resolved_language_name=context_result.resolved_market.language_name if context_result.resolved_market else None,
            resolved_market_source=context_result.resolved_market.source.value if context_result.resolved_market else None,
            resolved_market_confidence=context_result.resolved_market.confidence.value if context_result.resolved_market else None,
            resolved_detection_confidence=context_result.resolved_market.detection_confidence if context_result.resolved_market else None,
            resolved_has_conflict=context_result.resolved_market.has_conflict if context_result.resolved_market else False,
            resolved_conflict_details=context_result.resolved_market.conflict_details if context_result.resolved_market else None,
            # Website analysis
            detected_business_model=context_result.website_analysis.business_model.value if context_result.website_analysis and context_result.website_analysis.business_model else None,
            detected_company_stage=context_result.website_analysis.company_stage.value if context_result.website_analysis and context_result.website_analysis.company_stage else None,
            detected_languages=context_result.website_analysis.detected_languages if context_result.website_analysis else [],
            detected_offerings=[o.name for o in context_result.website_analysis.offerings] if context_result.website_analysis else [],
            has_blog=context_result.website_analysis.has_blog if context_result.website_analysis else False,
            has_pricing_page=context_result.website_analysis.has_pricing_page if context_result.website_analysis else False,
            has_demo_form=context_result.website_analysis.has_demo_form if context_result.website_analysis else False,
            has_contact_form=context_result.website_analysis.has_contact_form if context_result.website_analysis else False,
            has_ecommerce=context_result.website_analysis.has_ecommerce if context_result.website_analysis else False,
            # Goal validation
            goal_fits_business=context_result.business_context.goal_validation.goal_fits_business if context_result.business_context and context_result.business_context.goal_validation else True,
            suggested_goal=context_result.business_context.goal_validation.suggested_goal.value if context_result.business_context and context_result.business_context.goal_validation and context_result.business_context.goal_validation.suggested_goal else None,
            goal_suggestion_reason=context_result.business_context.goal_validation.suggestion_reason if context_result.business_context and context_result.business_context.goal_validation else None,
            # Market validation
            primary_market_validated=context_result.market_validation.primary_validated if context_result.market_validation else False,
            should_adjust_market=context_result.market_validation.should_adjust_primary if context_result.market_validation else False,
            suggested_market=context_result.market_validation.suggested_primary if context_result.market_validation else None,
            language_mismatch=context_result.market_validation.language_mismatch if context_result.market_validation else False,
            # Competitor summary
            direct_competitors_count=context_result.competitor_validation.total_direct_competitors if context_result.competitor_validation else 0,
            seo_competitors_count=context_result.competitor_validation.total_seo_competitors if context_result.competitor_validation else 0,
            emerging_threats_count=context_result.competitor_validation.emerging_threats if context_result.competitor_validation else 0,
            # Business context
            buyer_journey_type=context_result.business_context.buyer_journey.journey_type.value if context_result.business_context and context_result.business_context.buyer_journey and context_result.business_context.buyer_journey.journey_type else None,
            seo_fit=context_result.business_context.seo_fit if context_result.business_context else None,
            recommended_focus_areas=context_result.business_context.recommended_focus if context_result.business_context else [],
            # Confidence
            overall_confidence=context_result.overall_confidence,
            website_analysis_confidence=context_result.website_analysis.analysis_confidence if context_result.website_analysis else 0.0,
            context_confidence=context_result.business_context.context_confidence if context_result.business_context else 0.0,
            # Execution metadata
            execution_time_seconds=context_result.execution_time_seconds,
            errors=context_result.errors,
            warnings=context_result.warnings,
        )
        db.add(context_record)
        db.flush()  # Get the ID

        context_id = context_record.id

        # Store validated competitors
        if context_result.competitor_validation:
            all_competitors = (
                context_result.competitor_validation.confirmed +
                context_result.competitor_validation.discovered +
                context_result.competitor_validation.reclassified
            )

            for comp in all_competitors:
                # Convert competitor type string to enum
                comp_type_str = comp.competitor_type.value if comp.competitor_type else "direct"
                comp_type_enum = _convert_competitor_type(comp_type_str)

                comp_record = ValidatedCompetitorRecord(
                    domain_id=domain_id,
                    context_intelligence_id=context_id,
                    competitor_domain=comp.domain,
                    competitor_name=comp.name,
                    competitor_type=comp_type_enum,
                    threat_level=comp.threat_level.value if comp.threat_level else "medium",
                    discovery_method=comp.discovery_method.value if comp.discovery_method else "dataforseo_suggested",
                    user_provided=comp.user_provided,
                    validation_status=comp.validation_status.value if comp.validation_status else "unvalidated",
                    validation_notes=comp.validation_notes,
                    strengths=comp.strengths,
                    weaknesses=comp.weaknesses,
                    organic_traffic=comp.organic_traffic,
                    organic_keywords=comp.organic_keywords,
                    domain_rating=comp.domain_rating,
                    confidence_score=comp.confidence_score,
                )
                db.add(comp_record)

            # Also store rejected competitors with reason
            for rejected in context_result.competitor_validation.rejected:
                comp_record = ValidatedCompetitorRecord(
                    domain_id=domain_id,
                    context_intelligence_id=context_id,
                    competitor_domain=rejected.get("domain", ""),
                    competitor_type=ValidatedCompetitorType.NOT_COMPETITOR,
                    threat_level="none",
                    discovery_method="user_provided",
                    user_provided=True,
                    validation_status="rejected",
                    validation_notes=rejected.get("reason", "Not a real competitor"),
                    confidence_score=0.8,
                )
                db.add(comp_record)

        # Store market opportunities
        if context_result.market_validation:
            all_markets = (
                context_result.market_validation.validated_markets +
                context_result.market_validation.discovered_opportunities
            )

            for market in all_markets:
                from src.context.market_validator import MARKET_CONFIG
                market_config = MARKET_CONFIG.get(market.region, {})

                market_record = MarketOpportunityRecord(
                    domain_id=domain_id,
                    context_intelligence_id=context_id,
                    region=market.region,
                    language=market.language,
                    region_name=market_config.get("name", market.region),
                    opportunity_score=market.opportunity_score,
                    competition_level=market.competition_level,
                    search_volume_potential=market.search_volume_potential,
                    keyword_count_estimate=market.keyword_count_estimate,
                    our_current_visibility=market.our_current_visibility,
                    is_primary=market.is_primary,
                    is_recommended=market.is_recommended,
                    priority_rank=market.priority_rank,
                    recommendation_reason=market.recommendation_reason,
                    discovery_method=market.discovery_method.value if market.discovery_method else "serp_analysis",
                )
                db.add(market_record)

        logger.info(
            f"Stored context intelligence for run {run_id}: "
            f"{context_result.competitor_validation.total_direct_competitors if context_result.competitor_validation else 0} competitors, "
            f"{len(context_result.market_validation.discovered_opportunities) if context_result.market_validation else 0} market opportunities"
        )

        return context_id


def get_context_intelligence(domain: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent context intelligence for a domain.

    Useful for reusing context in subsequent analyses.

    Args:
        domain: Domain name

    Returns:
        Dict with context data, or None if not found
    """
    from .models import Domain, ContextIntelligence

    with get_db_context() as db:
        # Find domain
        domain_record = db.query(Domain).filter(Domain.domain == domain).first()
        if not domain_record:
            return None

        # Get most recent context intelligence
        context = (
            db.query(ContextIntelligence)
            .filter(ContextIntelligence.domain_id == domain_record.id)
            .order_by(ContextIntelligence.created_at.desc())
            .first()
        )

        if not context:
            return None

        return {
            "id": str(context.id),
            "domain_id": str(context.domain_id),
            "declared_market": context.declared_market,
            "declared_language": context.declared_language,
            "declared_goal": context.declared_goal,
            "detected_business_model": context.detected_business_model,
            "detected_company_stage": context.detected_company_stage,
            "goal_fits_business": context.goal_fits_business,
            "suggested_goal": context.suggested_goal,
            "primary_market_validated": context.primary_market_validated,
            "direct_competitors_count": context.direct_competitors_count,
            "seo_competitors_count": context.seo_competitors_count,
            "overall_confidence": context.overall_confidence,
            "created_at": context.created_at.isoformat() if context.created_at else None,
            # Resolved market (Phase 2)
            "resolved_market": {
                "code": context.resolved_market_code,
                "name": context.resolved_market_name,
                "location_code": context.resolved_location_code,
                "language_code": context.resolved_language_code,
                "language_name": context.resolved_language_name,
                "source": context.resolved_market_source,
                "confidence": context.resolved_market_confidence,
                "detection_confidence": context.resolved_detection_confidence,
                "has_conflict": context.resolved_has_conflict,
                "conflict_details": context.resolved_conflict_details,
            } if context.resolved_market_code else None,
        }


# =============================================================================
# GREENFIELD INTELLIGENCE - Competitor Sessions & Analysis
# =============================================================================

def create_greenfield_analysis_run(
    domain: str,
    greenfield_context: Dict[str, Any],
    config: Dict[str, Any] = None,
    user_id: UUID = None,
) -> UUID:
    """
    Create an analysis run configured for greenfield mode.

    Args:
        domain: Domain to analyze
        greenfield_context: User-provided business context
        config: Additional collection configuration

    Returns:
        UUID of the created analysis run
    """
    from .models import AnalysisMode
    from .session import ensure_greenfield_columns_exist

    # Ensure the analysis_mode column exists before inserting
    # This is a safety check in case the startup migration failed
    if not ensure_greenfield_columns_exist():
        raise RuntimeError(
            "Cannot create greenfield analysis run: the analysis_mode column "
            "does not exist in the database. Please check database migrations."
        )

    with get_db_context() as db:
        # Find or create domain
        domain_obj = db.query(Domain).filter(Domain.domain == domain).first()
        if not domain_obj:
            domain_obj = Domain(domain=domain, user_id=user_id)
            db.add(domain_obj)
            db.flush()
        elif user_id and not domain_obj.user_id:
            # Assign ownership if domain exists but has no owner
            domain_obj.user_id = user_id
            db.flush()

        # Create analysis run with greenfield mode
        run = AnalysisRun(
            domain_id=domain_obj.id,
            status=AnalysisStatus.PENDING,
            analysis_mode=AnalysisMode.GREENFIELD,
            domain_maturity_at_analysis="greenfield",
            greenfield_context=greenfield_context,
            config=config or {},
            started_at=datetime.utcnow(),
        )
        db.add(run)
        db.flush()

        run_id = run.id
        logger.info(f"Created greenfield analysis run {run_id} for {domain}")

        return run_id


def create_competitor_intelligence_session(
    analysis_run_id: UUID,
    domain_id: UUID,
    user_provided_competitors: List[str] = None,
) -> UUID:
    """
    Create a competitor intelligence session for curation workflow.

    Args:
        analysis_run_id: Parent analysis run
        domain_id: Domain being analyzed
        user_provided_competitors: User-provided competitor domains

    Returns:
        UUID of the created session
    """
    from .models import CompetitorIntelligenceSession

    with get_db_context() as db:
        session = CompetitorIntelligenceSession(
            analysis_run_id=analysis_run_id,
            domain_id=domain_id,
            status="pending",
            user_provided_competitors=user_provided_competitors or [],
        )
        db.add(session)
        db.flush()

        session_id = session.id
        logger.info(f"Created competitor intelligence session {session_id}")

        return session_id


def get_competitor_session(session_id: UUID) -> Optional[Dict[str, Any]]:
    """Get competitor intelligence session by ID."""
    from .models import CompetitorIntelligenceSession

    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).get(session_id)
        if not session:
            return None

        # Extract tiered results if available
        ai_data = session.ai_discovered_competitors or {}
        if isinstance(ai_data, list):
            ai_data = {"competitors": ai_data}
        tiered_results = ai_data.get("tiered_results", {})

        return {
            "id": str(session.id),
            "analysis_run_id": str(session.analysis_run_id),
            "domain_id": str(session.domain_id),
            "status": session.status,
            "candidate_competitors": session.candidate_competitors or [],
            "removed_competitors": session.removed_competitors or [],
            "added_competitors": session.added_competitors or [],
            "final_competitors": session.final_competitors or [],
            # Tiered data for smart curation UI
            "tiered_results": tiered_results,
            "benchmarks": tiered_results.get("benchmarks", []),
            "keyword_sources": tiered_results.get("keyword_sources", []),
            "market_intel": tiered_results.get("market_intel", []),
            "rejected": tiered_results.get("rejected", []),
            "target_dr": tiered_results.get("target_dr", 0),
            # Timestamps
            "candidates_generated_at": session.candidates_generated_at.isoformat() if session.candidates_generated_at else None,
            "curation_started_at": session.curation_started_at.isoformat() if session.curation_started_at else None,
            "curation_completed_at": session.curation_completed_at.isoformat() if session.curation_completed_at else None,
            "finalized_at": session.finalized_at.isoformat() if session.finalized_at else None,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }


def update_session_candidates(
    session_id: UUID,
    candidates: List[Dict[str, Any]],
    website_context: Optional[Dict[str, Any]] = None,
    tiered_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Update session with discovered competitor candidates.

    Args:
        session_id: Session to update
        candidates: List of competitor candidates (sorted by tier)
        website_context: Optional scraped website context from Firecrawl
        tiered_data: Optional tiered competitor data with scoring
    """
    from .models import CompetitorIntelligenceSession

    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).get(session_id)
        if not session:
            return False

        session.candidate_competitors = candidates
        session.candidates_generated_at = datetime.utcnow()
        session.status = "awaiting_curation"

        # Store website context if provided (from Firecrawl scraping)
        if website_context:
            session.website_context = website_context

        # Store tiered data for UI display
        # This includes: benchmarks, keyword_sources, market_intel, rejected
        # Each with scores and explanations
        if tiered_data:
            # Store in the ai_discovered_competitors field which is JSONB
            # and designed for discovery results
            existing_ai_data = session.ai_discovered_competitors or {}
            if isinstance(existing_ai_data, list):
                existing_ai_data = {"competitors": existing_ai_data}
            existing_ai_data["tiered_results"] = tiered_data
            session.ai_discovered_competitors = existing_ai_data

        return True


def submit_curation(
    session_id: UUID,
    removals: List[Dict[str, Any]],
    additions: List[Dict[str, Any]],
    purpose_overrides: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Submit user curation decisions and finalize competitor set.

    Args:
        session_id: Session to update
        removals: List of {domain, reason, note}
        additions: List of {domain, purpose}
        purpose_overrides: List of {domain, new_purpose}

    Returns:
        Updated session data or None if not found
    """
    from .models import CompetitorIntelligenceSession, GreenfieldCompetitor, CompetitorPurpose

    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).get(session_id)
        if not session:
            return None

        # Get current candidates
        candidates = session.candidate_competitors or []
        removed_domains = {r["domain"] for r in removals}

        # Build final set
        final_competitors = []
        priority = 1

        for candidate in candidates:
            domain = candidate.get("domain", "")

            if domain in removed_domains:
                continue

            # Check for purpose override
            purpose = candidate.get("suggested_purpose", "keyword_source")
            for override in purpose_overrides:
                if override.get("domain") == domain:
                    purpose = override.get("new_purpose", purpose)
                    break

            final_competitors.append({
                "domain": domain,
                "purpose": purpose,
                "priority": priority,
                "domain_rating": candidate.get("domain_rating", 0),
                "organic_traffic": candidate.get("organic_traffic", 0),
                "organic_keywords": candidate.get("organic_keywords", 0),
                "keyword_overlap": candidate.get("keyword_overlap", 0),
                "is_user_provided": candidate.get("discovery_source") == "user_provided",
                "is_user_curated": True,
            })
            priority += 1

        # Add user-added competitors
        for addition in additions:
            final_competitors.append({
                "domain": addition.get("domain", ""),
                "purpose": addition.get("purpose", "keyword_source"),
                "priority": priority,
                "domain_rating": 0,
                "organic_traffic": 0,
                "organic_keywords": 0,
                "keyword_overlap": 0,
                "is_user_provided": True,
                "is_user_curated": True,
            })
            priority += 1

        # Update session
        session.removed_competitors = removals
        session.added_competitors = additions
        session.final_competitors = final_competitors
        session.curation_completed_at = datetime.utcnow()
        session.finalized_at = datetime.utcnow()
        session.status = "curated"

        # Delete any existing GreenfieldCompetitor records for this session
        # (handles re-curation after partial failure or user re-submitting)
        db.query(GreenfieldCompetitor).filter(
            GreenfieldCompetitor.session_id == session.id
        ).delete()

        # Create GreenfieldCompetitor records
        for comp in final_competitors:
            purpose_str = comp.get("purpose", "keyword_source")
            try:
                purpose_enum = CompetitorPurpose(purpose_str)
            except ValueError:
                purpose_enum = CompetitorPurpose.KEYWORD_SOURCE

            gf_comp = GreenfieldCompetitor(
                session_id=session.id,
                analysis_run_id=session.analysis_run_id,
                domain=comp.get("domain", ""),
                purpose=purpose_enum,
                priority=comp.get("priority", 1),
                domain_rating=comp.get("domain_rating", 0),
                organic_traffic=comp.get("organic_traffic", 0),
                organic_keywords=comp.get("organic_keywords", 0),
                is_user_provided=comp.get("is_user_provided", False),
                is_validated=True,
            )
            db.add(gf_comp)

        db.flush()

        return {
            "session_id": str(session.id),
            "status": session.status,
            "final_competitors": final_competitors,
            "competitor_count": len(final_competitors),
            "removed_count": len(removals),
            "added_count": len(additions),
            "finalized_at": session.finalized_at.isoformat(),
        }


def update_competitors_post_curation(
    session_id: UUID,
    removals: List[Dict[str, Any]] = None,
    additions: List[Dict[str, Any]] = None,
    purpose_overrides: List[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update competitors after initial curation (post-finalization edits).
    """
    from .models import CompetitorIntelligenceSession, GreenfieldCompetitor, CompetitorPurpose

    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).get(session_id)
        if not session:
            return None

        final_competitors = session.final_competitors or []

        # Apply removals
        if removals:
            removed_domains = {r["domain"] for r in removals}
            final_competitors = [c for c in final_competitors if c.get("domain") not in removed_domains]

            # Mark as removed in database
            for removal in removals:
                comp = (
                    db.query(GreenfieldCompetitor)
                    .filter(
                        GreenfieldCompetitor.session_id == session_id,
                        GreenfieldCompetitor.domain == removal["domain"]
                    )
                    .first()
                )
                if comp:
                    comp.is_removed = True
                    comp.removal_reason = removal.get("reason", "other")
                    comp.removal_note = removal.get("note", "")

        # Apply purpose overrides
        if purpose_overrides:
            for override in purpose_overrides:
                domain = override.get("domain")
                new_purpose = override.get("new_purpose")

                for comp in final_competitors:
                    if comp.get("domain") == domain:
                        comp["purpose"] = new_purpose

                # Update database
                comp = (
                    db.query(GreenfieldCompetitor)
                    .filter(
                        GreenfieldCompetitor.session_id == session_id,
                        GreenfieldCompetitor.domain == domain
                    )
                    .first()
                )
                if comp:
                    try:
                        comp.purpose_override = CompetitorPurpose(new_purpose)
                    except ValueError:
                        pass

        # Apply additions
        if additions:
            max_priority = max((c.get("priority", 0) for c in final_competitors), default=0)
            for addition in additions:
                max_priority += 1
                new_comp = {
                    "domain": addition.get("domain", ""),
                    "purpose": addition.get("purpose", "keyword_source"),
                    "priority": max_priority,
                    "domain_rating": 0,
                    "organic_traffic": 0,
                    "organic_keywords": 0,
                    "is_user_provided": True,
                    "is_user_curated": True,
                }
                final_competitors.append(new_comp)

                # Add to database
                purpose_str = addition.get("purpose", "keyword_source")
                try:
                    purpose_enum = CompetitorPurpose(purpose_str)
                except ValueError:
                    purpose_enum = CompetitorPurpose.KEYWORD_SOURCE

                gf_comp = GreenfieldCompetitor(
                    session_id=session.id,
                    analysis_run_id=session.analysis_run_id,
                    domain=addition.get("domain", ""),
                    purpose=purpose_enum,
                    priority=max_priority,
                    is_user_provided=True,
                    is_validated=False,
                )
                db.add(gf_comp)

        session.final_competitors = final_competitors
        session.updated_at = datetime.utcnow()
        db.flush()

        return {
            "session_id": str(session.id),
            "status": session.status,
            "final_competitors": final_competitors,
            "competitor_count": len(final_competitors),
        }


def save_greenfield_analysis(
    analysis_run_id: UUID,
    domain_id: UUID,
    market_opportunity: Dict[str, Any],
    beachhead_summary: Dict[str, Any],
    projections: Dict[str, Any],
    growth_roadmap: List[Dict[str, Any]],
) -> UUID:
    """
    Save greenfield analysis results.

    Args:
        analysis_run_id: Parent analysis run
        domain_id: Domain analyzed
        market_opportunity: TAM/SAM/SOM data
        beachhead_summary: Beachhead keyword summary
        projections: Three-scenario traffic projections
        growth_roadmap: Phased growth plan

    Returns:
        UUID of the created greenfield analysis
    """
    from .models import GreenfieldAnalysis

    with get_db_context() as db:
        analysis = GreenfieldAnalysis(
            analysis_run_id=analysis_run_id,
            domain_id=domain_id,

            # Market opportunity
            total_addressable_market=market_opportunity.get("tam_volume", 0),
            serviceable_addressable_market=market_opportunity.get("sam_volume", 0),
            serviceable_obtainable_market=market_opportunity.get("som_volume", 0),
            tam_keyword_count=market_opportunity.get("tam_keywords", 0),
            sam_keyword_count=market_opportunity.get("sam_keywords", 0),
            som_keyword_count=market_opportunity.get("som_keywords", 0),
            market_opportunity_score=market_opportunity.get("opportunity_score", 0),
            competition_intensity=market_opportunity.get("competition_intensity", 0),

            # Beachhead summary
            beachhead_keyword_count=beachhead_summary.get("count", 0),
            total_beachhead_volume=beachhead_summary.get("total_volume", 0),
            avg_beachhead_winnability=beachhead_summary.get("avg_winnability", 0),
            beachhead_keywords=beachhead_summary.get("keywords", []),

            # Projections
            projection_conservative=projections.get("conservative", {}),
            projection_expected=projections.get("expected", {}),
            projection_aggressive=projections.get("aggressive", {}),

            # Growth roadmap
            growth_roadmap=growth_roadmap,

            data_completeness_score=market_opportunity.get("completeness", 0),
        )
        db.add(analysis)
        db.flush()

        analysis_id = analysis.id
        logger.info(f"Saved greenfield analysis {analysis_id}")

        return analysis_id


def get_greenfield_dashboard(analysis_run_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Get complete greenfield dashboard data.

    Returns all data needed for the greenfield dashboard UI.
    """
    from .models import (
        GreenfieldAnalysis,
        CompetitorIntelligenceSession,
        GreenfieldCompetitor,
    )

    with get_db_context() as db:
        # Get analysis run
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            return None

        # Get greenfield analysis
        gf_analysis = (
            db.query(GreenfieldAnalysis)
            .filter(GreenfieldAnalysis.analysis_run_id == analysis_run_id)
            .first()
        )

        # Get competitor session
        ci_session = (
            db.query(CompetitorIntelligenceSession)
            .filter(CompetitorIntelligenceSession.analysis_run_id == analysis_run_id)
            .first()
        )

        # Get beachhead keywords
        beachhead_keywords = (
            db.query(Keyword)
            .filter(
                Keyword.analysis_run_id == analysis_run_id,
                Keyword.is_beachhead == True
            )
            .order_by(Keyword.beachhead_priority.asc())
            .all()
        )

        # Get domain
        domain = db.query(Domain).get(run.domain_id)

        result = {
            "domain": domain.domain if domain else "",
            "analysis_run_id": str(analysis_run_id),
            "maturity": run.domain_maturity_at_analysis or "greenfield",

            # Competitors
            "competitors": ci_session.final_competitors if ci_session else [],
            "competitor_count": len(ci_session.final_competitors) if ci_session else 0,

            # Beachheads
            "beachhead_keywords": [
                {
                    "keyword": kw.keyword,
                    "search_volume": kw.search_volume or 0,
                    "winnability_score": kw.winnability_score or 0,
                    "personalized_difficulty": kw.personalized_difficulty or 0,
                    "keyword_difficulty": kw.keyword_difficulty or 0,
                    "beachhead_priority": kw.beachhead_priority or 0,
                    "growth_phase": kw.growth_phase or 1,
                    "has_ai_overview": kw.has_ai_overview or False,
                }
                for kw in beachhead_keywords
            ],
            "beachhead_count": len(beachhead_keywords),
            "total_beachhead_volume": sum(kw.search_volume or 0 for kw in beachhead_keywords),
            "avg_winnability": (
                sum(kw.winnability_score or 0 for kw in beachhead_keywords) / len(beachhead_keywords)
                if beachhead_keywords else 0
            ),

            "created_at": run.created_at.isoformat() if run.created_at else None,
            "last_updated": run.completed_at.isoformat() if run.completed_at else run.created_at.isoformat() if run.created_at else None,
        }

        # Add analysis data if available
        if gf_analysis:
            result["market_opportunity"] = {
                "total_addressable_market": gf_analysis.total_addressable_market or 0,
                "serviceable_addressable_market": gf_analysis.serviceable_addressable_market or 0,
                "serviceable_obtainable_market": gf_analysis.serviceable_obtainable_market or 0,
                "tam_keyword_count": gf_analysis.tam_keyword_count or 0,
                "sam_keyword_count": gf_analysis.sam_keyword_count or 0,
                "som_keyword_count": gf_analysis.som_keyword_count or 0,
                "market_opportunity_score": gf_analysis.market_opportunity_score or 0,
                "competition_intensity": gf_analysis.competition_intensity or 0,
            }

            result["traffic_projections"] = {
                "conservative": gf_analysis.projection_conservative or {},
                "expected": gf_analysis.projection_expected or {},
                "aggressive": gf_analysis.projection_aggressive or {},
            }

            result["growth_roadmap"] = gf_analysis.growth_roadmap or []

        return result


def get_beachhead_keywords(
    analysis_run_id: UUID,
    phase: Optional[int] = None,
    min_winnability: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Get beachhead keywords with optional filters."""
    with get_db_context() as db:
        query = (
            db.query(Keyword)
            .filter(
                Keyword.analysis_run_id == analysis_run_id,
                Keyword.is_beachhead == True
            )
        )

        if phase is not None:
            query = query.filter(Keyword.growth_phase == phase)

        if min_winnability is not None:
            query = query.filter(Keyword.winnability_score >= min_winnability)

        keywords = query.order_by(Keyword.beachhead_priority.asc()).all()

        return [
            {
                "id": str(kw.id),
                "keyword": kw.keyword,
                "search_volume": kw.search_volume or 0,
                "winnability_score": kw.winnability_score or 0,
                "personalized_difficulty": kw.personalized_difficulty or 0,
                "keyword_difficulty": kw.keyword_difficulty or 0,
                "beachhead_priority": kw.beachhead_priority or 0,
                "growth_phase": kw.growth_phase or 1,
                "has_ai_overview": kw.has_ai_overview or False,
                "source_competitor": kw.source_competitor or "",
            }
            for kw in keywords
        ]


def update_keyword_phase(keyword_id: UUID, phase: int) -> bool:
    """Update a keyword's growth phase assignment."""
    with get_db_context() as db:
        keyword = db.query(Keyword).get(keyword_id)
        if not keyword:
            return False

        keyword.growth_phase = phase
        return True


def save_beachhead_keywords(
    analysis_run_id: UUID,
    beachhead_keywords: List[Dict[str, Any]],
) -> int:
    """
    Save or update beachhead keywords.

    Returns number of keywords updated.
    """
    with get_db_context() as db:
        count = 0
        for bh in beachhead_keywords:
            keyword_text = bh.get("keyword", "")

            # Find existing keyword
            keyword = (
                db.query(Keyword)
                .filter(
                    Keyword.analysis_run_id == analysis_run_id,
                    Keyword.keyword == keyword_text
                )
                .first()
            )

            if keyword:
                keyword.is_beachhead = True
                keyword.beachhead_priority = bh.get("beachhead_priority", 0)
                keyword.beachhead_score = bh.get("beachhead_score", 0)
                keyword.winnability_score = bh.get("winnability_score", 0)
                keyword.personalized_difficulty = bh.get("personalized_difficulty", 0)
                keyword.growth_phase = bh.get("growth_phase", 1)
                keyword.serp_avg_dr = bh.get("avg_serp_dr", 0)
                keyword.has_ai_overview = bh.get("has_ai_overview", False)
                count += 1

        return count

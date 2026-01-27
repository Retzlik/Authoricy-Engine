"""
Dashboard Intelligence API

Provides dashboard-optimized endpoints for the 100x Intelligence Dashboard:
- Share of Voice calculations
- Sparkline data for position trends
- Attack/Defend competitive battleground
- Topical authority clusters
- Content audit (KUCK analysis)
- AI intelligence summaries
- Ranked opportunities

PERFORMANCE OPTIMIZATIONS:
- Precomputed data served from PostgreSQL cache (<100ms vs 2-5s)
- HTTP caching headers for CDN and browser caching
- Bundled endpoint for single API call (reduces 6+ calls to 1)
- ETag support for conditional requests (304 Not Modified)
- Stale-while-revalidate for seamless background updates

These endpoints aggregate and format existing data for visualization.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request, Header
from pydantic import BaseModel, Field
from sqlalchemy import func, and_, or_, case, desc, asc, text
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import (
    Domain, AnalysisRun, Keyword, Competitor, Backlink, Page,
    RankingHistory, DomainMetricsHistory, ContentCluster, KeywordGap,
    AgentOutput, SERPFeature, AIVisibility, TechnicalMetrics,
    AnalysisStatus, SearchIntent, CompetitorType
)
from src.cache.postgres_cache import PostgresCache, get_postgres_cache
from src.auth.dependencies import get_current_user, get_current_user_optional
from src.auth.models import User
from src.cache.headers import (
    add_cache_headers, generate_etag, check_not_modified,
    CacheHeadersBuilder
)
from src.cache.config import CacheTTL

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard Intelligence"],
    dependencies=[Depends(get_current_user)],  # All endpoints require authentication
)


# =============================================================================
# DOMAIN ACCESS HELPER
# =============================================================================

def check_domain_access(domain: Domain, user: User) -> None:
    """
    Check if user has access to a domain.

    Raises HTTPException 403 if access denied.
    Admins can access any domain, users can only access their own.
    """
    if user.is_admin:
        return  # Admins have access to all domains

    if domain.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this domain"
        )


def get_domain_with_access(
    domain_id: UUID,
    user: User,
    db: Session,
) -> Domain:
    """
    Get domain and verify user access in one step.

    Returns the domain if user has access.
    Raises HTTPException 404 if domain not found.
    Raises HTTPException 403 if access denied.
    """
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    check_domain_access(domain, user)
    return domain


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class HealthScore(BaseModel):
    """Overall domain health score"""
    overall: float = Field(..., description="Overall health score 0-100")
    keyword_health: float = Field(..., description="Keyword portfolio health 0-100")
    backlink_health: float = Field(..., description="Backlink profile health 0-100")
    technical_health: float = Field(..., description="Technical SEO health 0-100")
    content_health: float = Field(..., description="Content quality health 0-100")
    ai_visibility: float = Field(..., description="AI search visibility 0-100")


class MetricChange(BaseModel):
    """Metric with change tracking"""
    current: int
    previous: Optional[int] = None
    change: Optional[int] = None
    change_percent: Optional[float] = None
    trend: str = "stable"  # up, down, stable


class DashboardOverview(BaseModel):
    """Main dashboard overview"""
    domain: str
    analysis_id: str
    analysis_date: datetime

    # Health scores
    health: HealthScore

    # Key metrics with changes
    organic_traffic: MetricChange
    organic_keywords: MetricChange
    domain_rating: MetricChange
    referring_domains: MetricChange
    backlinks: MetricChange

    # Position distribution
    positions: Dict[str, int]  # {"top_3": 45, "4_10": 123, ...}

    # Quick stats
    quick_wins_count: int
    at_risk_keywords: int
    content_gaps: int
    ai_mentions: int


class ShareOfVoiceEntry(BaseModel):
    """Share of voice for a domain"""
    domain: str
    is_target: bool
    estimated_traffic: int
    keyword_count: int
    avg_position: float
    share_percent: float


class ShareOfVoiceResponse(BaseModel):
    """Share of voice analysis"""
    total_market_traffic: int
    target_share: float
    entries: List[ShareOfVoiceEntry]
    trend_30d: Optional[float] = None  # Change in SoV over 30 days


class SparklinePoint(BaseModel):
    """Single point in a sparkline"""
    date: str
    value: float


class KeywordSparkline(BaseModel):
    """Keyword with sparkline data"""
    keyword_id: str
    keyword: str
    current_position: Optional[int]
    search_volume: int
    opportunity_score: float
    sparkline: List[SparklinePoint]
    trend: str  # improving, declining, stable, volatile


class SparklineResponse(BaseModel):
    """Sparkline data for multiple keywords"""
    keywords: List[KeywordSparkline]
    domain_traffic_sparkline: List[SparklinePoint]


class BattlegroundKeyword(BaseModel):
    """Keyword in attack/defend battleground"""
    keyword_id: str
    keyword: str
    search_volume: int
    keyword_difficulty: int
    opportunity_score: float

    # Position data
    our_position: Optional[int]
    our_position_change: Optional[int]

    # Best competitor
    best_competitor: str
    best_competitor_position: int

    # Classification
    category: str  # attack_easy, attack_hard, defend_priority, defend_watch
    priority_score: float

    # Recommendation
    action: str
    estimated_traffic_gain: int


class BattlegroundResponse(BaseModel):
    """Attack/Defend battleground analysis"""
    # Attack opportunities (we don't rank or rank worse)
    attack_easy: List[BattlegroundKeyword]  # Low difficulty gaps
    attack_hard: List[BattlegroundKeyword]  # High value but difficult

    # Defend priorities (we rank but at risk)
    defend_priority: List[BattlegroundKeyword]  # Losing ground
    defend_watch: List[BattlegroundKeyword]  # Competitors gaining

    # Summary
    total_attack_opportunity: int  # Potential traffic
    total_at_risk_traffic: int


class ClusterAuthority(BaseModel):
    """Topical authority for a cluster"""
    cluster_id: str
    cluster_name: str
    pillar_keyword: Optional[str]

    # Authority metrics
    authority_score: float  # 0-100
    content_completeness: float  # 0-100
    avg_position: float

    # Coverage
    total_keywords: int
    ranking_keywords: int
    content_gaps: int

    # Traffic
    total_traffic: int
    total_search_volume: int

    # Competition
    top_competitor: Optional[str]
    competitor_authority: Optional[float]

    # Recommendation
    priority: str  # high, medium, low
    recommended_action: str


class TopicalAuthorityResponse(BaseModel):
    """Topical authority analysis"""
    clusters: List[ClusterAuthority]
    overall_authority: float
    strongest_cluster: Optional[str]
    weakest_cluster: Optional[str]
    total_content_gaps: int


class KUCKPage(BaseModel):
    """Page with KUCK recommendation"""
    page_id: str
    url: str
    title: Optional[str]

    # Metrics
    organic_traffic: int
    organic_keywords: int
    backlinks: int

    # Scores
    content_score: float
    freshness_score: float
    decay_score: float

    # KUCK recommendation
    recommendation: str  # keep, update, consolidate, kill
    reason: str
    priority: int  # 1-5

    # Potential
    traffic_potential: Optional[int]
    consolidate_with: Optional[List[str]]


class ContentAuditResponse(BaseModel):
    """Content audit (KUCK) analysis"""
    pages_analyzed: int

    # Distribution
    keep_count: int
    update_count: int
    consolidate_count: int
    kill_count: int

    # Prioritized lists
    keep: List[KUCKPage]
    update: List[KUCKPage]
    consolidate: List[KUCKPage]
    kill: List[KUCKPage]

    # Impact estimates
    potential_traffic_recovery: int
    pages_to_consolidate: int
    pages_to_remove: int


class IntelligenceFinding(BaseModel):
    """Single intelligence finding"""
    category: str  # keyword, backlink, technical, content, competitive, ai
    priority: int  # 1-5
    confidence: float  # 0-1

    title: str
    description: str
    impact: str

    # Data points
    metrics: Dict[str, Any]

    # Recommendation
    action: Optional[str]
    effort: Optional[str]  # low, medium, high


class IntelligenceSummary(BaseModel):
    """AI-generated intelligence summary"""
    # Narrative summary (AI-written prose)
    headline: str
    executive_summary: str

    # Categorized findings
    critical_findings: List[IntelligenceFinding]
    opportunities: List[IntelligenceFinding]
    risks: List[IntelligenceFinding]

    # Key metrics highlighted
    key_metrics: Dict[str, Any]

    # Generated timestamp
    generated_at: datetime


class RankedOpportunity(BaseModel):
    """Ranked opportunity"""
    rank: int
    opportunity_type: str  # keyword, content, backlink, technical, competitive

    title: str
    description: str

    # Impact
    impact_score: float  # 0-100
    effort: str  # low, medium, high
    confidence: float

    # Specifics
    keywords: Optional[List[str]]
    target_url: Optional[str]
    estimated_traffic: Optional[int]

    # Timeline
    time_to_impact: str  # immediate, short_term, medium_term, long_term


class OpportunitiesResponse(BaseModel):
    """Ranked opportunities"""
    opportunities: List[RankedOpportunity]
    total_traffic_potential: int
    quick_wins_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_trend(current: float, previous: float) -> str:
    """Calculate trend direction"""
    if previous == 0:
        return "stable" if current == 0 else "up"
    change_pct = ((current - previous) / previous) * 100
    if change_pct > 5:
        return "up"
    elif change_pct < -5:
        return "down"
    return "stable"


def calculate_metric_change(current: int, previous: Optional[int]) -> MetricChange:
    """Calculate metric with change tracking"""
    if previous is None:
        return MetricChange(current=current, trend="stable")

    change = current - previous
    change_pct = (change / previous * 100) if previous > 0 else 0
    trend = calculate_trend(current, previous)

    return MetricChange(
        current=current,
        previous=previous,
        change=change,
        change_percent=round(change_pct, 1),
        trend=trend
    )


def estimate_traffic_from_position(position: int, search_volume: int) -> int:
    """Estimate traffic based on position and CTR curves"""
    # CTR curve approximation
    ctr_map = {
        1: 0.32, 2: 0.18, 3: 0.11, 4: 0.08, 5: 0.06,
        6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.02
    }

    if position <= 0:
        return 0
    elif position <= 10:
        ctr = ctr_map.get(position, 0.02)
    elif position <= 20:
        ctr = 0.01
    elif position <= 50:
        ctr = 0.005
    else:
        ctr = 0.001

    return int(search_volume * ctr)


# =============================================================================
# CACHE HELPERS
# =============================================================================

def get_latest_analysis(domain_id: UUID, db: Session) -> Optional[AnalysisRun]:
    """Get the latest completed analysis for a domain."""
    return db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.status == AnalysisStatus.COMPLETED
    ).order_by(desc(AnalysisRun.completed_at)).first()


# =============================================================================
# BUNDLED ENDPOINT - Single call for all dashboard data
# =============================================================================

@router.get("/{domain_id}/bundle")
async def get_dashboard_bundle(
    domain_id: UUID,
    request: Request,
    response: Response,
    include: str = Query(
        "overview,sparklines,sov,battleground,clusters",
        description="Comma-separated list of components to include"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
):
    """
    Get all dashboard data in a single request.

    **This is the recommended endpoint for dashboard loading.**

    Reduces HTTP round trips from 6+ to 1, dramatically improving performance.
    Returns precomputed data from cache (<50ms) when available.

    Components:
    - overview: Health scores, metrics, position distribution
    - sparklines: 30-day position trends for top keywords
    - sov: Share of Voice vs competitors
    - battleground: Attack/Defend keyword analysis
    - clusters: Topical authority analysis
    - content_audit: KUCK recommendations
    - opportunities: Ranked opportunity list
    - ai_summary: AI-generated intelligence summary

    Cache behavior:
    - Data is precomputed after each analysis completion
    - Cache TTL: 4 hours (dashboard data changes only on new analysis)
    - HTTP caching: 5 minutes with stale-while-revalidate
    - Supports conditional requests (ETag/If-None-Match)

    Requires authentication. Users can only access their own domains.
    Admins can access all domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    analysis_id = str(analysis.id)

    # Generate ETag from analysis ID and completion time
    etag = generate_etag(analysis_id, analysis.completed_at)

    # Check for conditional request (304 Not Modified)
    not_modified = check_not_modified(request, etag, analysis.completed_at)
    if not_modified:
        return not_modified

    # Try to get bundle from PostgreSQL cache
    cache = get_postgres_cache(db)
    bundle_data = cache.get_bundle(str(domain_id), analysis_id)

    if bundle_data is not None:
        # Filter to requested components
        requested = set(c.strip() for c in include.split(","))
        filtered_bundle = {
            k: v for k, v in bundle_data.items()
            if k in requested or k in ["analysis_id", "precomputed_at", "from_cache"]
        }

        # Add cache headers
        add_cache_headers(
            response,
            max_age=300,  # 5 minutes
            etag=etag,
            last_modified=analysis.completed_at,
            public=True,
            surrogate_keys=[f"domain:{domain_id}", f"analysis:{analysis_id}", "dashboard-bundle"],
        )

        return {
            "domain": domain.domain,
            "analysis_id": analysis_id,
            "from_cache": True,
            **filtered_bundle,
        }

    # Cache miss - fetch individual components from cache
    requested = set(c.strip() for c in include.split(","))
    bundle = {
        "domain": domain.domain,
        "analysis_id": analysis_id,
        "from_cache": False,
    }

    # Fetch components from cache
    for component in requested:
        component_key = component.replace("_", "-")
        data = cache.get_dashboard(str(domain_id), component_key, analysis_id)
        if data:
            bundle[component] = data

    # Add cache headers
    add_cache_headers(
        response,
        max_age=300,
        etag=etag,
        last_modified=analysis.completed_at,
        public=True,
        surrogate_keys=[f"domain:{domain_id}", f"analysis:{analysis_id}", "dashboard-bundle"],
    )

    return bundle


# =============================================================================
# INDIVIDUAL ENDPOINTS
# =============================================================================

@router.get("/{domain_id}/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    domain_id: UUID,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
) -> DashboardOverview:
    """
    Get comprehensive dashboard overview for a domain.

    Aggregates key metrics, health scores, and quick stats for the main dashboard.

    Performance: Serves from cache in <50ms when precomputed.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    analysis_id = str(analysis.id)

    # Generate ETag
    etag = generate_etag(analysis_id, analysis.completed_at, "overview")

    # Check for conditional request
    not_modified = check_not_modified(request, etag, analysis.completed_at)
    if not_modified:
        return not_modified

    # Try cache first
    cache = get_postgres_cache(db)
    cached = cache.get_dashboard(str(domain_id), "overview", analysis_id)
    if cached is not None:
        add_cache_headers(
            response, max_age=300, etag=etag, last_modified=analysis.completed_at,
            public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-overview"]
        )
        return DashboardOverview(**cached)

    # Cache miss - compute from database
    # Get previous analysis for comparison
    previous_analysis = db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.status == AnalysisStatus.COMPLETED,
        AnalysisRun.id != analysis.id
    ).order_by(desc(AnalysisRun.completed_at)).first()

    # Current metrics from DomainMetricsHistory
    current_metrics = db.query(DomainMetricsHistory).filter(
        DomainMetricsHistory.analysis_run_id == analysis.id
    ).first()

    previous_metrics = None
    if previous_analysis:
        previous_metrics = db.query(DomainMetricsHistory).filter(
            DomainMetricsHistory.analysis_run_id == previous_analysis.id
        ).first()

    # Calculate health scores
    technical = db.query(TechnicalMetrics).filter(
        TechnicalMetrics.analysis_run_id == analysis.id
    ).first()

    # Keyword stats
    keyword_stats = db.query(
        func.count(Keyword.id).label("total"),
        func.sum(case((Keyword.current_position <= 10, 1), else_=0)).label("top_10"),
        func.sum(case((and_(Keyword.current_position >= 4, Keyword.current_position <= 20), 1), else_=0)).label("opportunity_zone"),
        func.avg(Keyword.opportunity_score).label("avg_opportunity")
    ).filter(
        Keyword.analysis_run_id == analysis.id
    ).first()

    # Quick wins (high opportunity, ranking 11-30)
    quick_wins = db.query(func.count(Keyword.id)).filter(
        Keyword.analysis_run_id == analysis.id,
        Keyword.opportunity_score >= 70,
        Keyword.current_position.between(11, 30)
    ).scalar() or 0

    # At-risk keywords (declining positions)
    at_risk = db.query(func.count(Keyword.id)).filter(
        Keyword.analysis_run_id == analysis.id,
        Keyword.position_change < -3,
        Keyword.current_position <= 20
    ).scalar() or 0

    # Content gaps
    content_gaps = db.query(func.count(KeywordGap.id)).filter(
        KeywordGap.analysis_run_id == analysis.id,
        KeywordGap.target_position == None
    ).scalar() or 0

    # AI mentions
    ai_mentions = db.query(func.count(AIVisibility.id)).filter(
        AIVisibility.analysis_run_id == analysis.id,
        AIVisibility.is_mentioned == True
    ).scalar() or 0

    # Position distribution
    position_dist = db.query(
        func.sum(case((Keyword.current_position <= 3, 1), else_=0)).label("top_3"),
        func.sum(case((Keyword.current_position.between(4, 10), 1), else_=0)).label("4_10"),
        func.sum(case((Keyword.current_position.between(11, 20), 1), else_=0)).label("11_20"),
        func.sum(case((Keyword.current_position.between(21, 50), 1), else_=0)).label("21_50"),
        func.sum(case((Keyword.current_position > 50, 1), else_=0)).label("51_plus")
    ).filter(
        Keyword.analysis_run_id == analysis.id,
        Keyword.current_position != None
    ).first()

    # Calculate health scores
    keyword_health = min(100, (keyword_stats.top_10 or 0) / max(1, keyword_stats.total or 1) * 200 + (keyword_stats.avg_opportunity or 0))
    backlink_health = min(100, (current_metrics.referring_domains or 0) / 100 * 50 + 50) if current_metrics else 50
    technical_health = (technical.seo_score or 50) if technical else 50
    content_health = min(100, ((keyword_stats.total or 0) / 100) * 30 + 70 - (content_gaps / max(1, keyword_stats.total or 1)) * 100)
    ai_health = min(100, ai_mentions * 10) if ai_mentions else 0

    overall_health = (keyword_health * 0.3 + backlink_health * 0.2 + technical_health * 0.2 + content_health * 0.2 + ai_health * 0.1)

    result = DashboardOverview(
        domain=domain.domain,
        analysis_id=str(analysis.id),
        analysis_date=analysis.completed_at or analysis.created_at,
        health=HealthScore(
            overall=round(overall_health, 1),
            keyword_health=round(keyword_health, 1),
            backlink_health=round(backlink_health, 1),
            technical_health=round(technical_health, 1),
            content_health=round(content_health, 1),
            ai_visibility=round(ai_health, 1)
        ),
        organic_traffic=calculate_metric_change(
            current_metrics.organic_traffic if current_metrics else 0,
            previous_metrics.organic_traffic if previous_metrics else None
        ),
        organic_keywords=calculate_metric_change(
            current_metrics.organic_keywords if current_metrics else 0,
            previous_metrics.organic_keywords if previous_metrics else None
        ),
        domain_rating=calculate_metric_change(
            int(current_metrics.domain_rating or 0) if current_metrics else 0,
            int(previous_metrics.domain_rating or 0) if previous_metrics else None
        ),
        referring_domains=calculate_metric_change(
            current_metrics.referring_domains if current_metrics else 0,
            previous_metrics.referring_domains if previous_metrics else None
        ),
        backlinks=calculate_metric_change(
            current_metrics.backlinks_total if current_metrics else 0,
            previous_metrics.backlinks_total if previous_metrics else None
        ),
        positions={
            "top_3": position_dist.top_3 or 0,
            "4_10": position_dist._4_10 or 0 if hasattr(position_dist, '_4_10') else (getattr(position_dist, '4_10', 0) or 0),
            "11_20": position_dist._11_20 or 0 if hasattr(position_dist, '_11_20') else (getattr(position_dist, '11_20', 0) or 0),
            "21_50": position_dist._21_50 or 0 if hasattr(position_dist, '_21_50') else (getattr(position_dist, '21_50', 0) or 0),
            "51_plus": position_dist._51_plus or 0 if hasattr(position_dist, '_51_plus') else (getattr(position_dist, '51_plus', 0) or 0)
        },
        quick_wins_count=quick_wins,
        at_risk_keywords=at_risk,
        content_gaps=content_gaps,
        ai_mentions=ai_mentions
    )

    # Cache the result and add headers
    add_cache_headers(
        response, max_age=300, etag=etag, last_modified=analysis.completed_at,
        public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-overview"]
    )

    return result


@router.get("/{domain_id}/sov", response_model=ShareOfVoiceResponse)
async def get_share_of_voice(
    domain_id: UUID,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
) -> ShareOfVoiceResponse:
    """
    Calculate Share of Voice vs competitors.

    SoV = Your estimated traffic / Total market traffic (you + competitors)
    Based on keywords where at least one party ranks in top 20.

    Performance: Serves from cache in <50ms when precomputed.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    analysis_id = str(analysis.id)
    etag = generate_etag(analysis_id, analysis.completed_at, "sov")

    # Check for conditional request
    not_modified = check_not_modified(request, etag, analysis.completed_at)
    if not_modified:
        return not_modified

    # Try cache first
    cache = get_postgres_cache(db)
    cached = cache.get_dashboard(str(domain_id), "sov", analysis_id)
    if cached is not None:
        add_cache_headers(
            response, max_age=300, etag=etag, last_modified=analysis.completed_at,
            public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-sov"]
        )
        return ShareOfVoiceResponse(**cached)

    # Get target domain's traffic
    target_stats = db.query(
        func.sum(Keyword.estimated_traffic).label("traffic"),
        func.count(Keyword.id).label("keyword_count"),
        func.avg(Keyword.current_position).label("avg_position")
    ).filter(
        Keyword.analysis_run_id == analysis.id,
        Keyword.current_position <= 20,
        Keyword.current_position > 0
    ).first()

    target_traffic = target_stats.traffic or 0
    target_keywords = target_stats.keyword_count or 0
    target_avg_pos = target_stats.avg_position or 0

    # Get competitors
    competitors = db.query(Competitor).filter(
        Competitor.analysis_run_id == analysis.id,
        Competitor.competitor_type == CompetitorType.TRUE_COMPETITOR,
        Competitor.is_active == True
    ).limit(10).all()

    entries = [
        ShareOfVoiceEntry(
            domain=domain.domain,
            is_target=True,
            estimated_traffic=int(target_traffic),
            keyword_count=int(target_keywords),
            avg_position=round(target_avg_pos, 1),
            share_percent=0  # Calculated below
        )
    ]

    total_traffic = target_traffic

    for comp in competitors:
        comp_traffic = comp.organic_traffic or 0
        total_traffic += comp_traffic
        entries.append(
            ShareOfVoiceEntry(
                domain=comp.competitor_domain,
                is_target=False,
                estimated_traffic=comp_traffic,
                keyword_count=comp.organic_keywords or 0,
                avg_position=comp.avg_position or 0,
                share_percent=0
            )
        )

    # Calculate percentages
    for entry in entries:
        entry.share_percent = round(
            (entry.estimated_traffic / total_traffic * 100) if total_traffic > 0 else 0,
            1
        )

    # Sort by share
    entries.sort(key=lambda x: x.share_percent, reverse=True)

    target_share = next((e.share_percent for e in entries if e.is_target), 0)

    # Add cache headers for computed response
    add_cache_headers(
        response, max_age=300, etag=etag, last_modified=analysis.completed_at,
        public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-sov"]
    )

    return ShareOfVoiceResponse(
        total_market_traffic=int(total_traffic),
        target_share=target_share,
        entries=entries,
        trend_30d=None  # Would require historical SoV tracking
    )


@router.get("/{domain_id}/sparklines", response_model=SparklineResponse)
async def get_sparklines(
    domain_id: UUID,
    request: Request,
    response: Response,
    keyword_ids: Optional[str] = Query(None, description="Comma-separated keyword IDs"),
    top_n: int = Query(20, description="Number of top keywords to include"),
    days: int = Query(30, description="Number of days of history"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
) -> SparklineResponse:
    """
    Get sparkline data for keyword position trends.

    Returns position history formatted for sparkline visualization.
    Performance: Serves from cache in <50ms when precomputed.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    analysis_id = str(analysis.id)
    etag = generate_etag(analysis_id, analysis.completed_at, "sparklines")

    # Check for conditional request
    not_modified = check_not_modified(request, etag, analysis.completed_at)
    if not_modified:
        return not_modified

    # Try cache first (only for default params)
    if not keyword_ids and top_n == 20 and days == 30:
        cache = get_postgres_cache(db)
        cached = cache.get_dashboard(str(domain_id), "sparklines", analysis_id)
        if cached is not None:
            add_cache_headers(
                response, max_age=300, etag=etag, last_modified=analysis.completed_at,
                public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-sparklines"]
            )
            return SparklineResponse(**cached)

    # Determine which keywords to include
    if keyword_ids:
        kw_ids = [UUID(k.strip()) for k in keyword_ids.split(",")]
        keywords = db.query(Keyword).filter(
            Keyword.id.in_(kw_ids),
            Keyword.domain_id == domain_id
        ).all()
    else:
        # Top keywords by traffic
        keywords = db.query(Keyword).filter(
            Keyword.analysis_run_id == analysis.id,
            Keyword.current_position <= 50
        ).order_by(desc(Keyword.estimated_traffic)).limit(top_n).all()

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    sparkline_keywords = []
    for kw in keywords:
        # Get ranking history
        history = db.query(RankingHistory).filter(
            RankingHistory.domain_id == domain_id,
            RankingHistory.keyword_normalized == kw.keyword_normalized,
            RankingHistory.recorded_at >= cutoff_date
        ).order_by(asc(RankingHistory.recorded_at)).all()

        sparkline = []
        for h in history:
            sparkline.append(SparklinePoint(
                date=h.recorded_at.strftime("%Y-%m-%d"),
                value=float(h.position or 100)  # 100 = not ranking
            ))

        # Determine trend
        if len(sparkline) >= 2:
            first_val = sparkline[0].value
            last_val = sparkline[-1].value
            diff = first_val - last_val  # Lower position = better

            # Check volatility
            values = [p.value for p in sparkline]
            volatility = max(values) - min(values) if values else 0

            if volatility > 20:
                trend = "volatile"
            elif diff > 5:
                trend = "improving"
            elif diff < -5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        sparkline_keywords.append(KeywordSparkline(
            keyword_id=str(kw.id),
            keyword=kw.keyword,
            current_position=kw.current_position,
            search_volume=kw.search_volume or 0,
            opportunity_score=kw.opportunity_score or 0,
            sparkline=sparkline,
            trend=trend
        ))

    # Domain traffic sparkline from DomainMetricsHistory
    traffic_history = db.query(DomainMetricsHistory).filter(
        DomainMetricsHistory.domain_id == domain_id,
        DomainMetricsHistory.recorded_at >= cutoff_date
    ).order_by(asc(DomainMetricsHistory.recorded_at)).all()

    domain_sparkline = [
        SparklinePoint(
            date=h.recorded_at.strftime("%Y-%m-%d"),
            value=float(h.organic_traffic or 0)
        )
        for h in traffic_history
    ]

    return SparklineResponse(
        keywords=sparkline_keywords,
        domain_traffic_sparkline=domain_sparkline
    )


@router.get("/{domain_id}/battleground", response_model=BattlegroundResponse)
async def get_battleground(
    domain_id: UUID,
    request: Request,
    response: Response,
    limit: int = Query(25, description="Max items per category"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
) -> BattlegroundResponse:
    """
    Get Attack/Defend competitive battleground.

    Attack: Keywords where competitors rank but we don't (or rank worse)
    Defend: Keywords where we rank but are losing ground or competitors gaining

    Performance: Serves from cache in <50ms when precomputed.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    analysis_id = str(analysis.id)
    etag = generate_etag(analysis_id, analysis.completed_at, "battleground")

    # Check for conditional request
    not_modified = check_not_modified(request, etag, analysis.completed_at)
    if not_modified:
        return not_modified

    # Try cache first
    cache = get_postgres_cache(db)
    cached = cache.get_dashboard(str(domain_id), "battleground", analysis_id)
    if cached is not None:
        add_cache_headers(
            response, max_age=300, etag=etag, last_modified=analysis.completed_at,
            public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-battleground"]
        )
        return BattlegroundResponse(**cached)

    # ATTACK: Keywords from gaps (competitors rank, we don't or rank worse)
    gaps = db.query(KeywordGap).filter(
        KeywordGap.analysis_run_id == analysis.id,
        or_(
            KeywordGap.target_position == None,
            KeywordGap.target_position > 20
        ),
        KeywordGap.best_competitor_position <= 10
    ).order_by(desc(KeywordGap.opportunity_score)).limit(limit * 2).all()

    attack_easy = []
    attack_hard = []

    for gap in gaps:
        difficulty = gap.keyword_difficulty or 50

        kw = BattlegroundKeyword(
            keyword_id=str(gap.id),
            keyword=gap.keyword,
            search_volume=gap.search_volume or 0,
            keyword_difficulty=difficulty,
            opportunity_score=gap.opportunity_score or 0,
            our_position=gap.target_position,
            our_position_change=None,
            best_competitor=gap.best_competitor or "Unknown",
            best_competitor_position=gap.best_competitor_position or 0,
            category="attack_easy" if difficulty < 40 else "attack_hard",
            priority_score=gap.difficulty_adjusted_score or gap.opportunity_score or 0,
            action="Create content targeting this keyword" if gap.target_position is None else "Optimize existing content",
            estimated_traffic_gain=gap.estimated_traffic_potential or estimate_traffic_from_position(5, gap.search_volume or 0)
        )

        if difficulty < 40:
            attack_easy.append(kw)
        else:
            attack_hard.append(kw)

    attack_easy = attack_easy[:limit]
    attack_hard = attack_hard[:limit]

    # DEFEND: Keywords where we rank but losing ground
    # Priority: position declining OR competitors in striking distance
    defend_keywords = db.query(Keyword).filter(
        Keyword.analysis_run_id == analysis.id,
        Keyword.current_position <= 20,
        Keyword.current_position > 0,
        or_(
            Keyword.position_change < -2,  # Declining
            Keyword.current_position.between(4, 10)  # Could be overtaken
        )
    ).order_by(desc(Keyword.estimated_traffic)).limit(limit * 2).all()

    defend_priority = []
    defend_watch = []

    for kw in defend_keywords:
        is_declining = (kw.position_change or 0) < -2

        bkw = BattlegroundKeyword(
            keyword_id=str(kw.id),
            keyword=kw.keyword,
            search_volume=kw.search_volume or 0,
            keyword_difficulty=kw.keyword_difficulty or 50,
            opportunity_score=kw.opportunity_score or 0,
            our_position=kw.current_position,
            our_position_change=kw.position_change,
            best_competitor="Competitors",  # Would need SERP data
            best_competitor_position=(kw.current_position or 5) - 1,
            category="defend_priority" if is_declining else "defend_watch",
            priority_score=float(kw.estimated_traffic or 0),
            action="Urgent: Refresh content and build links" if is_declining else "Monitor and prepare defensive content",
            estimated_traffic_gain=0  # Defend = prevent loss
        )

        if is_declining:
            defend_priority.append(bkw)
        else:
            defend_watch.append(bkw)

    defend_priority = defend_priority[:limit]
    defend_watch = defend_watch[:limit]

    # Calculate totals
    total_attack = sum(k.estimated_traffic_gain for k in attack_easy + attack_hard)
    total_at_risk = sum(k.search_volume for k in defend_priority)

    return BattlegroundResponse(
        attack_easy=attack_easy,
        attack_hard=attack_hard,
        defend_priority=defend_priority,
        defend_watch=defend_watch,
        total_attack_opportunity=total_attack,
        total_at_risk_traffic=estimate_traffic_from_position(5, total_at_risk)
    )


@router.get("/{domain_id}/clusters", response_model=TopicalAuthorityResponse)
async def get_topical_authority(
    domain_id: UUID,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
) -> TopicalAuthorityResponse:
    """
    Get topical authority analysis by cluster.

    Shows authority scores, content completeness, and gaps for each topic cluster.
    Performance: Serves from cache in <50ms when precomputed.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    analysis_id = str(analysis.id)
    etag = generate_etag(analysis_id, analysis.completed_at, "clusters")

    # Check for conditional request
    not_modified = check_not_modified(request, etag, analysis.completed_at)
    if not_modified:
        return not_modified

    # Try cache first
    cache = get_postgres_cache(db)
    cached = cache.get_dashboard(str(domain_id), "clusters", analysis_id)
    if cached is not None:
        add_cache_headers(
            response, max_age=300, etag=etag, last_modified=analysis.completed_at,
            public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-clusters"]
        )
        return TopicalAuthorityResponse(**cached)

    # Get clusters
    clusters = db.query(ContentCluster).filter(
        ContentCluster.analysis_run_id == analysis.id
    ).order_by(desc(ContentCluster.topical_authority_score)).all()

    cluster_responses = []
    total_gaps = 0

    for cluster in clusters:
        total_gaps += cluster.content_gap_count or 0

        cluster_responses.append(ClusterAuthority(
            cluster_id=str(cluster.id),
            cluster_name=cluster.cluster_name,
            pillar_keyword=cluster.pillar_keyword,
            authority_score=cluster.topical_authority_score or 0,
            content_completeness=cluster.content_completeness or 0,
            avg_position=cluster.avg_position or 0,
            total_keywords=cluster.total_keywords or 0,
            ranking_keywords=cluster.ranking_keywords or 0,
            content_gaps=cluster.content_gap_count or 0,
            total_traffic=cluster.total_traffic or 0,
            total_search_volume=cluster.total_search_volume or 0,
            top_competitor=cluster.top_competitor,
            competitor_authority=None,  # Would need competitor cluster data
            priority=cluster.priority or "medium",
            recommended_action=f"Create {cluster.content_gap_count or 0} pieces of content to fill gaps" if (cluster.content_gap_count or 0) > 0 else "Optimize existing content for better rankings"
        ))

    # Calculate overall authority
    overall = sum(c.authority_score for c in cluster_responses) / len(cluster_responses) if cluster_responses else 0

    strongest = max(cluster_responses, key=lambda x: x.authority_score).cluster_name if cluster_responses else None
    weakest = min(cluster_responses, key=lambda x: x.authority_score).cluster_name if cluster_responses else None

    return TopicalAuthorityResponse(
        clusters=cluster_responses,
        overall_authority=round(overall, 1),
        strongest_cluster=strongest,
        weakest_cluster=weakest,
        total_content_gaps=total_gaps
    )


@router.get("/{domain_id}/content-audit", response_model=ContentAuditResponse)
async def get_content_audit(
    domain_id: UUID,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
) -> ContentAuditResponse:
    """
    Get content audit (KUCK analysis).

    Categorizes pages as Keep, Update, Consolidate, or Kill based on performance.
    Performance: Serves from cache in <50ms when precomputed.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    analysis_id = str(analysis.id)
    etag = generate_etag(analysis_id, analysis.completed_at, "content-audit")

    # Check for conditional request
    not_modified = check_not_modified(request, etag, analysis.completed_at)
    if not_modified:
        return not_modified

    # Try cache first
    cache = get_postgres_cache(db)
    cached = cache.get_dashboard(str(domain_id), "content-audit", analysis_id)
    if cached is not None:
        add_cache_headers(
            response, max_age=300, etag=etag, last_modified=analysis.completed_at,
            public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-content-audit"]
        )
        return ContentAuditResponse(**cached)

    # Get pages with KUCK recommendations
    pages = db.query(Page).filter(
        Page.analysis_run_id == analysis.id
    ).all()

    # Categorize pages
    keep = []
    update = []
    consolidate = []
    kill = []

    for page in pages:
        kuck_page = KUCKPage(
            page_id=str(page.id),
            url=page.url,
            title=page.title,
            organic_traffic=page.organic_traffic or 0,
            organic_keywords=page.organic_keywords or 0,
            backlinks=page.backlink_count or 0,
            content_score=page.content_score or 50,
            freshness_score=page.freshness_score or 50,
            decay_score=page.decay_score or 0,
            recommendation=page.kuck_recommendation or "keep",
            reason=_get_kuck_reason(page),
            priority=_get_kuck_priority(page),
            traffic_potential=_estimate_traffic_potential(page),
            consolidate_with=None
        )

        rec = (page.kuck_recommendation or "keep").lower()
        if rec == "keep":
            keep.append(kuck_page)
        elif rec == "update":
            update.append(kuck_page)
        elif rec == "consolidate":
            consolidate.append(kuck_page)
        elif rec == "kill":
            kill.append(kuck_page)
        else:
            keep.append(kuck_page)

    # Sort by priority
    keep.sort(key=lambda x: -x.organic_traffic)
    update.sort(key=lambda x: x.priority)
    consolidate.sort(key=lambda x: x.priority)
    kill.sort(key=lambda x: -x.decay_score)

    # Estimate potential traffic recovery
    potential_recovery = sum(p.traffic_potential or 0 for p in update)

    return ContentAuditResponse(
        pages_analyzed=len(pages),
        keep_count=len(keep),
        update_count=len(update),
        consolidate_count=len(consolidate),
        kill_count=len(kill),
        keep=keep[:50],
        update=update[:50],
        consolidate=consolidate[:50],
        kill=kill[:50],
        potential_traffic_recovery=potential_recovery,
        pages_to_consolidate=len(consolidate),
        pages_to_remove=len(kill)
    )


def _get_kuck_reason(page: Page) -> str:
    """Generate reason for KUCK recommendation"""
    rec = (page.kuck_recommendation or "keep").lower()

    if rec == "keep":
        return f"Performing well with {page.organic_traffic or 0} monthly traffic"
    elif rec == "update":
        decay = page.decay_score or 0
        if decay > 50:
            return f"Content decay detected (score: {decay:.0f}). Refresh needed."
        else:
            return f"Good potential but underperforming. Freshness score: {page.freshness_score or 0:.0f}"
    elif rec == "consolidate":
        return "Similar content exists. Consider merging to strengthen authority."
    elif rec == "kill":
        return f"Low traffic ({page.organic_traffic or 0}), high decay ({page.decay_score or 0:.0f}). Remove or noindex."
    return "Needs review"


def _get_kuck_priority(page: Page) -> int:
    """Get priority 1-5 based on page metrics"""
    traffic = page.organic_traffic or 0
    decay = page.decay_score or 0

    if traffic > 1000 and decay > 30:
        return 1  # High traffic, decaying = urgent
    elif traffic > 500:
        return 2
    elif traffic > 100:
        return 3
    elif traffic > 10:
        return 4
    return 5


def _estimate_traffic_potential(page: Page) -> int:
    """Estimate traffic potential if updated"""
    current = page.organic_traffic or 0
    decay = page.decay_score or 0

    # Estimate recovery: higher decay = more potential
    recovery_multiplier = 1 + (decay / 100)
    return int(current * recovery_multiplier)


@router.get("/{domain_id}/intelligence-summary", response_model=IntelligenceSummary)
async def get_intelligence_summary(
    domain_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> IntelligenceSummary:
    """
    Get AI-generated intelligence summary.

    Synthesizes agent outputs into a narrative summary with key findings.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.status == AnalysisStatus.COMPLETED
    ).order_by(desc(AnalysisRun.completed_at)).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    # Get agent outputs
    agent_outputs = db.query(AgentOutput).filter(
        AgentOutput.analysis_run_id == analysis.id,
        AgentOutput.passed_quality_gate == True
    ).all()

    # Extract findings from agent outputs
    critical_findings = []
    opportunities = []
    risks = []

    key_metrics = {}

    for output in agent_outputs:
        parsed = output.output_parsed or {}

        # Extract findings
        findings = parsed.get("findings", [])
        for f in findings[:5]:  # Limit per agent
            finding = IntelligenceFinding(
                category=output.agent_name.replace("_", " ").title(),
                priority=f.get("priority", 3),
                confidence=f.get("confidence", 0.7),
                title=f.get("title", "Finding"),
                description=f.get("description", ""),
                impact=f.get("impact", ""),
                metrics=f.get("evidence", {}),
                action=f.get("action"),
                effort=f.get("effort")
            )

            # Categorize
            priority = f.get("priority", 3)
            if priority <= 2:
                critical_findings.append(finding)
            elif "opportunity" in f.get("type", "").lower() or "opportunity" in f.get("title", "").lower():
                opportunities.append(finding)
            else:
                risks.append(finding)

        # Extract metrics
        metrics = parsed.get("metrics", {})
        key_metrics.update(metrics)

    # Sort by priority
    critical_findings.sort(key=lambda x: x.priority)
    opportunities.sort(key=lambda x: -x.confidence)
    risks.sort(key=lambda x: x.priority)

    # Generate headline and summary
    # In a production system, this would call Claude to generate prose
    keyword_count = key_metrics.get("total_ranking_keywords", 0)
    traffic = key_metrics.get("total_organic_traffic", 0)
    quick_wins = key_metrics.get("quick_win_count", 0)

    headline = f"{domain.domain}: {len(critical_findings)} Critical Findings, {len(opportunities)} Opportunities"

    summary_parts = []
    if keyword_count:
        summary_parts.append(f"Your domain ranks for {keyword_count:,} keywords")
    if traffic:
        summary_parts.append(f"driving an estimated {traffic:,} monthly organic visitors")
    if quick_wins:
        summary_parts.append(f"We identified {quick_wins} quick win opportunities")
    if critical_findings:
        summary_parts.append(f"Attention needed on {len(critical_findings)} critical issues")

    executive_summary = ". ".join(summary_parts) + "." if summary_parts else "Analysis complete. Review the findings below."

    return IntelligenceSummary(
        headline=headline,
        executive_summary=executive_summary,
        critical_findings=critical_findings[:10],
        opportunities=opportunities[:10],
        risks=risks[:10],
        key_metrics=key_metrics,
        generated_at=datetime.utcnow()
    )


@router.get("/{domain_id}/opportunities", response_model=OpportunitiesResponse)
async def get_ranked_opportunities(
    domain_id: UUID,
    request: Request,
    response: Response,
    limit: int = Query(20, description="Max opportunities to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
) -> OpportunitiesResponse:
    """
    Get ranked opportunities across all categories.

    Combines keyword, content, backlink, and competitive opportunities,
    ranked by impact/effort ratio.
    Performance: Serves from cache in <50ms when precomputed.

    Requires authentication. Users can only access their own domains.
    """
    # Get domain with access check
    domain = get_domain_with_access(domain_id, current_user, db)

    analysis = get_latest_analysis(domain_id, db)
    if analysis:
        analysis_id = str(analysis.id)
        etag = generate_etag(analysis_id, analysis.completed_at, "opportunities")

        # Check for conditional request
        not_modified = check_not_modified(request, etag, analysis.completed_at)
        if not_modified:
            return not_modified

        # Try cache first
        cache = get_postgres_cache(db)
        cached = cache.get_dashboard(str(domain_id), "opportunities", analysis_id)
        if cached is not None:
            add_cache_headers(
                response, max_age=300, etag=etag, last_modified=analysis.completed_at,
                public=True, surrogate_keys=[f"domain:{domain_id}", "dashboard-opportunities"]
            )
            return OpportunitiesResponse(**cached)

    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.status == AnalysisStatus.COMPLETED
    ).order_by(desc(AnalysisRun.completed_at)).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")

    opportunities = []

    # 1. Quick win keywords (high opportunity, ranking 11-30)
    quick_wins = db.query(Keyword).filter(
        Keyword.analysis_run_id == analysis.id,
        Keyword.opportunity_score >= 70,
        Keyword.current_position.between(11, 30)
    ).order_by(desc(Keyword.opportunity_score)).limit(limit // 4).all()

    for kw in quick_wins:
        traffic_potential = estimate_traffic_from_position(5, kw.search_volume or 0) - (kw.estimated_traffic or 0)
        opportunities.append(RankedOpportunity(
            rank=0,
            opportunity_type="keyword",
            title=f"Push '{kw.keyword}' into top 10",
            description=f"Currently ranking #{kw.current_position}. Optimize content to reach top 10.",
            impact_score=(kw.opportunity_score or 0),
            effort="low",
            confidence=0.8,
            keywords=[kw.keyword],
            target_url=kw.ranking_url,
            estimated_traffic=traffic_potential,
            time_to_impact="short_term"
        ))

    # 2. High-value keyword gaps
    gaps = db.query(KeywordGap).filter(
        KeywordGap.analysis_run_id == analysis.id,
        KeywordGap.target_position == None,
        KeywordGap.search_volume >= 500
    ).order_by(desc(KeywordGap.opportunity_score)).limit(limit // 4).all()

    for gap in gaps:
        traffic_potential = estimate_traffic_from_position(5, gap.search_volume or 0)
        difficulty = gap.keyword_difficulty or 50
        opportunities.append(RankedOpportunity(
            rank=0,
            opportunity_type="content",
            title=f"Create content for '{gap.keyword}'",
            description=f"Competitors rank for this {gap.search_volume:,} volume keyword. You don't.",
            impact_score=(gap.opportunity_score or 0),
            effort="medium" if difficulty < 50 else "high",
            confidence=0.7,
            keywords=[gap.keyword],
            target_url=None,
            estimated_traffic=traffic_potential,
            time_to_impact="medium_term"
        ))

    # 3. Content to update (high decay, good traffic)
    update_pages = db.query(Page).filter(
        Page.analysis_run_id == analysis.id,
        Page.decay_score > 40,
        Page.organic_traffic > 100
    ).order_by(desc(Page.organic_traffic)).limit(limit // 4).all()

    for page in update_pages:
        recovery = int((page.organic_traffic or 0) * (page.decay_score or 0) / 100)
        opportunities.append(RankedOpportunity(
            rank=0,
            opportunity_type="content",
            title=f"Refresh: {page.title or page.url}",
            description=f"Content decay detected. Update to recover {recovery:,} estimated traffic.",
            impact_score=min(100, (page.decay_score or 0) + (page.organic_traffic or 0) / 100),
            effort="low",
            confidence=0.75,
            keywords=None,
            target_url=page.url,
            estimated_traffic=recovery,
            time_to_impact="immediate"
        ))

    # 4. Featured snippet opportunities
    snippet_opps = db.query(SERPFeature).filter(
        SERPFeature.analysis_run_id == analysis.id,
        SERPFeature.owned_by_target == False,
        SERPFeature.opportunity_score >= 60
    ).order_by(desc(SERPFeature.opportunity_score)).limit(limit // 4).all()

    for feat in snippet_opps:
        opportunities.append(RankedOpportunity(
            rank=0,
            opportunity_type="competitive",
            title=f"Capture featured snippet for '{feat.keyword}'",
            description=f"You rank for this keyword but don't own the snippet. Optimize content format.",
            impact_score=(feat.opportunity_score or 0),
            effort="low",
            confidence=0.6,
            keywords=[feat.keyword],
            target_url=None,
            estimated_traffic=None,
            time_to_impact="short_term"
        ))

    # Sort by impact/effort ratio and assign ranks
    effort_weights = {"low": 1, "medium": 2, "high": 3}
    opportunities.sort(
        key=lambda x: x.impact_score / effort_weights.get(x.effort, 2),
        reverse=True
    )

    for i, opp in enumerate(opportunities[:limit]):
        opp.rank = i + 1

    # Calculate totals
    total_potential = sum(o.estimated_traffic or 0 for o in opportunities[:limit])
    quick_win_count = len([o for o in opportunities[:limit] if o.effort == "low"])

    return OpportunitiesResponse(
        opportunities=opportunities[:limit],
        total_traffic_potential=total_potential,
        quick_wins_count=quick_win_count
    )

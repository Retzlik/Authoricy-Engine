"""
API Endpoints for Greenfield Intelligence

Handles:
1. Competitor Intelligence Sessions (discovery, curation, finalization)
2. Greenfield Dashboard data
3. Beachhead keyword management
4. Traffic projections

These endpoints implement the flows described in:
- COMPETITOR_INTELLIGENCE_ARCHITECTURE.md
- LOVABLE_BUILD_SPEC.md (Sections 3 and 5)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.database import get_session
from src.database.models import (
    AnalysisRun,
    AnalysisMode,
    CompetitorPurpose,
    CompetitorIntelligenceSession,
    GreenfieldAnalysis,
    GreenfieldCompetitor,
    Keyword,
)
from src.scoring.greenfield import (
    DomainMaturity,
    classify_domain_maturity,
    DomainMetrics,
)
from src.services.greenfield import GreenfieldService
from src.database.models import Domain
from src.auth.dependencies import get_current_user
from src.auth.models import User

logger = logging.getLogger(__name__)

# Router with authentication required for ALL endpoints
# The maturity check is public (no auth needed) so we'll override for that endpoint
router = APIRouter(
    prefix="/api/greenfield",
    tags=["greenfield"],
    dependencies=[Depends(get_current_user)],  # All endpoints require authentication
)


# =============================================================================
# AUTH HELPERS
# =============================================================================

def check_domain_access_greenfield(domain: Domain, user: User) -> None:
    """Check if user has access to a domain for greenfield operations."""
    if user.is_admin:
        return
    if domain.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this domain"
        )


def check_analysis_access(analysis: AnalysisRun, user: User, db) -> None:
    """Check if user has access to an analysis."""
    if user.is_admin:
        return
    domain = db.query(Domain).filter(Domain.id == analysis.domain_id).first()
    if domain and domain.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this analysis"
        )


def check_session_access(session: CompetitorIntelligenceSession, user: User, db) -> None:
    """Check if user has access to a competitor intelligence session."""
    if user.is_admin:
        return
    analysis = db.query(AnalysisRun).filter(AnalysisRun.id == session.analysis_run_id).first()
    if analysis:
        check_analysis_access(analysis, user, db)

# Service instance (will be initialized with client in production)
greenfield_service = GreenfieldService()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DomainMaturityResponse(BaseModel):
    """Response for domain maturity check."""
    domain: str
    maturity: str  # greenfield, emerging, established
    domain_rating: int
    organic_keywords: int
    organic_traffic: int
    requires_greenfield: bool
    message: str


class CompetitorCandidate(BaseModel):
    """Competitor candidate during discovery."""
    domain: str
    discovery_source: str  # perplexity, serp, traffic_share, user_provided
    domain_rating: int = 0
    organic_traffic: int = 0
    organic_keywords: int = 0
    relevance_score: float = 0.0
    suggested_purpose: str = "keyword_source"
    discovery_reason: str = ""


class CurationSession(BaseModel):
    """Competitor intelligence session for curation."""
    session_id: UUID
    analysis_run_id: UUID
    status: str
    candidates: List[CompetitorCandidate]
    candidates_count: int
    required_removals: int
    min_final_count: int
    max_final_count: int
    created_at: datetime


class RemovalInput(BaseModel):
    """Input for removing a competitor."""
    domain: str
    reason: Literal["not_relevant", "too_large", "too_small", "different_market", "other"]
    note: Optional[str] = None


class AddCompetitorInput(BaseModel):
    """Input for adding a competitor."""
    domain: str
    purpose: Optional[str] = None


class PurposeOverrideInput(BaseModel):
    """Input for changing competitor purpose."""
    domain: str
    new_purpose: Literal["benchmark_peer", "keyword_source", "link_source", "content_model", "aspirational"]


class CurationInput(BaseModel):
    """Input for submitting curation decisions."""
    removals: List[RemovalInput] = []
    additions: List[AddCompetitorInput] = []
    purpose_overrides: List[PurposeOverrideInput] = []


class FinalCompetitor(BaseModel):
    """Finalized competitor with purpose."""
    domain: str
    display_name: Optional[str] = None
    purpose: str
    priority: int
    domain_rating: int
    organic_traffic: int
    organic_keywords: int
    keyword_overlap: int = 0
    is_user_provided: bool = False
    is_user_curated: bool = False


class FinalCompetitorSetResponse(BaseModel):
    """Response after curation with final competitor set."""
    session_id: UUID
    status: str
    final_competitors: List[FinalCompetitor]
    competitor_count: int
    removed_count: int
    added_count: int
    finalized_at: Optional[datetime] = None


class CompetitorUpdateInput(BaseModel):
    """Input for post-finalization competitor updates."""
    removals: Optional[List[RemovalInput]] = None
    additions: Optional[List[AddCompetitorInput]] = None
    purpose_overrides: Optional[List[PurposeOverrideInput]] = None


# Beachhead models
class BeachheadKeyword(BaseModel):
    """Beachhead keyword for display."""
    keyword: str
    search_volume: int
    winnability_score: float
    personalized_difficulty: float
    keyword_difficulty: int
    beachhead_priority: int
    growth_phase: int
    has_ai_overview: bool = False
    estimated_traffic: int = 0
    recommended_content_type: str = ""


class MarketOpportunityResponse(BaseModel):
    """Market opportunity sizing."""
    total_addressable_market: int  # TAM volume
    serviceable_addressable_market: int  # SAM volume
    serviceable_obtainable_market: int  # SOM volume
    tam_keyword_count: int
    sam_keyword_count: int
    som_keyword_count: int
    market_opportunity_score: float
    competition_intensity: float


class TrafficProjectionScenario(BaseModel):
    """Single traffic projection scenario."""
    scenario: str  # conservative, expected, aggressive
    confidence: float
    month_3: int = 0
    month_6: int = 0
    month_12: int = 0
    month_18: int = 0
    month_24: int = 0


class TrafficProjectionsResponse(BaseModel):
    """Three-scenario traffic projections."""
    conservative: TrafficProjectionScenario
    expected: TrafficProjectionScenario
    aggressive: TrafficProjectionScenario


class GrowthPhase(BaseModel):
    """Growth roadmap phase."""
    phase: str
    phase_number: int
    months: str
    focus: str
    strategy: str
    keyword_count: int
    total_volume: int
    expected_traffic: int


class GreenfieldDashboardResponse(BaseModel):
    """Complete greenfield dashboard data."""
    domain: str
    analysis_run_id: UUID
    maturity: str

    # Competitors
    competitors: List[FinalCompetitor]
    competitor_count: int

    # Market opportunity
    market_opportunity: Optional[MarketOpportunityResponse] = None

    # Beachheads
    beachhead_keywords: List[BeachheadKeyword]
    beachhead_count: int
    total_beachhead_volume: int
    avg_winnability: float

    # Projections
    traffic_projections: Optional[TrafficProjectionsResponse] = None

    # Growth roadmap
    growth_roadmap: List[GrowthPhase]

    # Metadata
    created_at: datetime
    last_updated: datetime


# =============================================================================
# DOMAIN MATURITY ENDPOINTS
# =============================================================================

@router.get("/maturity/{domain}", response_model=DomainMaturityResponse, dependencies=[])
async def check_domain_maturity(domain: str) -> DomainMaturityResponse:
    """
    Check domain maturity to determine analysis mode.

    Returns whether the domain should use greenfield analysis.

    Note: This is a public endpoint (no auth required) for preliminary checks.
    """
    result = await greenfield_service.check_domain_maturity(domain)

    return DomainMaturityResponse(
        domain=result["domain"],
        maturity=result["maturity"],
        domain_rating=result["domain_rating"],
        organic_keywords=result["organic_keywords"],
        organic_traffic=result["organic_traffic"],
        requires_greenfield=result["requires_greenfield"],
        message=result["message"],
    )


# =============================================================================
# COMPETITOR INTELLIGENCE SESSION ENDPOINTS
# =============================================================================

@router.post("/sessions")
async def create_competitor_session(
    analysis_run_id: UUID,
    current_user: User = Depends(get_current_user),
    seed_keywords: List[str] = [],
    known_competitors: List[str] = [],
) -> Dict[str, Any]:
    """
    Create a new competitor intelligence session.

    Triggers the competitor discovery pipeline and returns
    a session for user curation.
    """
    from src.database import repository
    from src.database.session import get_db_context

    # Get analysis run to find domain_id and check access
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis run not found")
        check_analysis_access(run, current_user, db)
        domain_id = run.domain_id

    # Create session
    session_id = repository.create_competitor_intelligence_session(
        analysis_run_id=analysis_run_id,
        domain_id=domain_id,
        user_provided_competitors=known_competitors,
    )

    # Trigger discovery
    result = await greenfield_service.discover_competitors(
        session_id=session_id,
        seed_keywords=seed_keywords,
        known_competitors=known_competitors,
    )

    return {
        "session_id": str(session_id),
        "analysis_run_id": str(analysis_run_id),
        "status": result.get("status", "awaiting_curation"),
        "candidates": result.get("candidates", []),
        "candidates_count": result.get("candidates_count", 0),
        "required_removals": result.get("required_removals", 0),
        "min_final_count": 8,
        "max_final_count": 10,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.get("/sessions/{session_id}")
async def get_competitor_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current state of a competitor intelligence session.
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.id == session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        check_session_access(session, current_user, db)

    session_data = greenfield_service.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    return session_data


@router.post("/sessions/{session_id}/curate")
async def submit_curation(
    session_id: UUID,
    curation: CurationInput,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Submit user's curation decisions.

    Validates that:
    - Required number of competitors removed
    - Final count is within limits (8-10)
    - Purpose overrides are valid

    Returns the finalized competitor set.
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.id == session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        check_session_access(session, current_user, db)
    try:
        result = greenfield_service.submit_curation(
            session_id=session_id,
            removals=[r.model_dump() for r in curation.removals],
            additions=[a.model_dump() for a in curation.additions],
            purpose_overrides=[p.model_dump() for p in curation.purpose_overrides],
        )

        if not result:
            raise HTTPException(status_code=404, detail="Session not found")

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/sessions/{session_id}/competitors")
async def update_competitors(
    session_id: UUID,
    updates: CompetitorUpdateInput,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Update competitors after finalization.

    Allows users to:
    - Remove competitors from the final set
    - Add new competitors
    - Change competitor purposes

    Note: Significant changes may trigger reanalysis.
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.id == session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        check_session_access(session, current_user, db)

    result = greenfield_service.update_competitors(
        session_id=session_id,
        removals=[r.model_dump() for r in updates.removals] if updates.removals else None,
        additions=[a.model_dump() for a in updates.additions] if updates.additions else None,
        purpose_overrides=[p.model_dump() for p in updates.purpose_overrides] if updates.purpose_overrides else None,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return result


# =============================================================================
# GREENFIELD DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/dashboard/{analysis_run_id}")
async def get_greenfield_dashboard(
    analysis_run_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get complete greenfield dashboard data.

    Returns:
    - Curated competitors with purposes
    - Market opportunity (TAM/SAM/SOM)
    - Beachhead keywords
    - Traffic projections
    - Growth roadmap
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")
        check_analysis_access(run, current_user, db)

    result = greenfield_service.get_dashboard(analysis_run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return result


@router.get("/dashboard/{analysis_run_id}/beachheads")
async def get_beachhead_keywords(
    analysis_run_id: UUID,
    current_user: User = Depends(get_current_user),
    phase: Optional[int] = None,
    min_winnability: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Get beachhead keywords for greenfield analysis.

    Optionally filter by:
    - Growth phase (1=Foundation, 2=Traction, 3=Authority)
    - Minimum winnability score
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")
        check_analysis_access(run, current_user, db)

    keywords = greenfield_service.get_beachheads(
        analysis_run_id=analysis_run_id,
        phase=phase,
        min_winnability=min_winnability,
    )
    return keywords


@router.get("/dashboard/{analysis_run_id}/market-map")
async def get_market_map(
    analysis_run_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get market map data for visualization.

    Returns competitor positioning data for the market map component.
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")
        check_analysis_access(run, current_user, db)

    dashboard = greenfield_service.get_dashboard(analysis_run_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Extract market map data from competitors
    competitors = dashboard.get("competitors", [])

    return {
        "analysis_run_id": str(analysis_run_id),
        "competitors": [
            {
                "domain": c.get("domain", ""),
                "domain_rating": c.get("domain_rating", 0),
                "organic_traffic": c.get("organic_traffic", 0),
                "purpose": c.get("purpose", "keyword_source"),
                "priority": c.get("priority", 0),
            }
            for c in competitors
        ],
        "market_opportunity": dashboard.get("market_opportunity", {}),
    }


@router.get("/dashboard/{analysis_run_id}/projections")
async def get_traffic_projections(
    analysis_run_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get traffic projections for greenfield domain.

    Returns three scenarios: conservative, expected, aggressive
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")
        check_analysis_access(run, current_user, db)

    dashboard = greenfield_service.get_dashboard(analysis_run_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Analysis not found")

    projections = dashboard.get("traffic_projections", {})
    return projections


@router.get("/dashboard/{analysis_run_id}/roadmap")
async def get_growth_roadmap(
    analysis_run_id: UUID,
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Get growth roadmap for greenfield domain.

    Returns phased keyword targeting strategy:
    - Phase 1: Foundation (months 1-3)
    - Phase 2: Traction (months 4-6)
    - Phase 3: Authority (months 7-12)
    """
    from src.database.session import get_db_context

    # Check access
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")
        check_analysis_access(run, current_user, db)

    dashboard = greenfield_service.get_dashboard(analysis_run_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Analysis not found")

    roadmap = dashboard.get("growth_roadmap", [])
    return roadmap


# =============================================================================
# KEYWORD PHASE ASSIGNMENT
# =============================================================================

@router.patch("/keywords/{keyword_id}/phase")
async def assign_keyword_phase(
    keyword_id: UUID,
    phase: int,  # 1, 2, or 3
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Assign a keyword to a growth phase.

    Phases:
    - 1: Foundation (high winnability, early targeting)
    - 2: Traction (medium difficulty, expansion)
    - 3: Authority (competitive, later targeting)
    """
    from src.database.session import get_db_context

    # Check access via keyword -> analysis -> domain
    with get_db_context() as db:
        keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword:
            raise HTTPException(status_code=404, detail="Keyword not found")
        if keyword.analysis_run_id:
            run = db.query(AnalysisRun).filter(AnalysisRun.id == keyword.analysis_run_id).first()
            if run:
                check_analysis_access(run, current_user, db)

    try:
        success = greenfield_service.update_keyword_phase(keyword_id, phase)
        if not success:
            raise HTTPException(status_code=404, detail="Keyword not found")
        return {"keyword_id": str(keyword_id), "phase": phase, "updated": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# TRIGGER ANALYSIS
# =============================================================================

class GreenfieldAnalysisRequest(BaseModel):
    """Request to start greenfield analysis."""
    domain: str
    business_name: str
    business_description: str
    primary_offering: str
    target_market: str = "United States"
    industry_vertical: str = "saas"
    seed_keywords: List[str] = Field(..., min_items=5)
    known_competitors: List[str] = Field(..., min_items=3)
    target_audience: Optional[str] = None
    email: Optional[str] = None


@router.post("/analyze")
async def start_greenfield_analysis(
    request: GreenfieldAnalysisRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Start a greenfield analysis.

    Creates an analysis run with greenfield context and triggers
    the competitor discovery pipeline.

    Returns:
    - analysis_run_id: UUID of the created analysis
    - session_id: UUID of the competitor intelligence session
    - status: Current status (discovering)

    The domain will be associated with the current user.
    """
    greenfield_context = {
        "business_name": request.business_name,
        "business_description": request.business_description,
        "primary_offering": request.primary_offering,
        "target_market": request.target_market,
        "industry_vertical": request.industry_vertical,
        "seed_keywords": request.seed_keywords,
        "known_competitors": request.known_competitors,
        "target_audience": request.target_audience,
    }

    try:
        analysis_run_id, session_id = greenfield_service.start_greenfield_analysis(
            domain=request.domain,
            greenfield_context=greenfield_context,
            user_id=current_user.id,
        )

        # Trigger competitor discovery
        await greenfield_service.discover_competitors(
            session_id=session_id,
            seed_keywords=request.seed_keywords,
            known_competitors=request.known_competitors,
            market=request.target_market.lower().replace(" ", "_")[:2] if request.target_market else "us",
        )

        return {
            "analysis_run_id": str(analysis_run_id),
            "session_id": str(session_id),
            "status": "awaiting_curation",
            "message": "Greenfield analysis started. Competitor discovery complete. Proceed to curation.",
            "next_step": f"/api/greenfield/sessions/{session_id}",
        }

    except Exception as e:
        logger.error(f"Failed to start greenfield analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

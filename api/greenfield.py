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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/greenfield", tags=["greenfield"])


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

@router.get("/maturity/{domain}", response_model=DomainMaturityResponse)
async def check_domain_maturity(domain: str) -> DomainMaturityResponse:
    """
    Check domain maturity to determine analysis mode.

    Returns whether the domain should use greenfield analysis.
    """
    # In production, this would call DataForSEO to get metrics
    # For now, return mock data structure

    # TODO: Implement actual DataForSEO call
    metrics = DomainMetrics(
        domain_rating=15,  # Example: low DR
        organic_keywords=30,  # Example: few keywords
        organic_traffic=100,
        referring_domains=10,
    )

    maturity = classify_domain_maturity(metrics)

    return DomainMaturityResponse(
        domain=domain,
        maturity=maturity.value,
        domain_rating=metrics.domain_rating,
        organic_keywords=metrics.organic_keywords,
        organic_traffic=metrics.organic_traffic,
        requires_greenfield=maturity == DomainMaturity.GREENFIELD,
        message=_get_maturity_message(maturity),
    )


def _get_maturity_message(maturity: DomainMaturity) -> str:
    """Get user-friendly message for maturity level."""
    if maturity == DomainMaturity.GREENFIELD:
        return (
            "Your domain has limited SEO data. We'll use competitor-first analysis "
            "to identify market opportunities and beachhead keywords."
        )
    elif maturity == DomainMaturity.EMERGING:
        return (
            "Your domain has some SEO data. We'll combine your existing data "
            "with competitor analysis for a comprehensive view."
        )
    else:
        return (
            "Your domain has established SEO data. We'll perform standard "
            "analysis with competitive benchmarking."
        )


# =============================================================================
# COMPETITOR INTELLIGENCE SESSION ENDPOINTS
# =============================================================================

@router.post("/sessions", response_model=CurationSession)
async def create_competitor_session(
    analysis_run_id: UUID,
    seed_keywords: List[str] = [],
    known_competitors: List[str] = [],
) -> CurationSession:
    """
    Create a new competitor intelligence session.

    Triggers the competitor discovery pipeline and returns
    a session for user curation.
    """
    session_id = uuid4()

    # TODO: Trigger actual competitor discovery pipeline
    # For now, return mock session structure

    mock_candidates = [
        CompetitorCandidate(
            domain="competitor1.com",
            discovery_source="serp",
            domain_rating=45,
            organic_traffic=50000,
            organic_keywords=2500,
            relevance_score=0.85,
            suggested_purpose="keyword_source",
            discovery_reason="Ranks for 8 of your seed keywords",
        ),
        # Add more mock candidates...
    ]

    return CurationSession(
        session_id=session_id,
        analysis_run_id=analysis_run_id,
        status="awaiting_curation",
        candidates=mock_candidates,
        candidates_count=len(mock_candidates),
        required_removals=max(0, len(mock_candidates) - 10),
        min_final_count=8,
        max_final_count=10,
        created_at=datetime.utcnow(),
    )


@router.get("/sessions/{session_id}", response_model=CurationSession)
async def get_competitor_session(session_id: UUID) -> CurationSession:
    """
    Get current state of a competitor intelligence session.
    """
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/sessions/{session_id}/curate", response_model=FinalCompetitorSetResponse)
async def submit_curation(
    session_id: UUID,
    curation: CurationInput,
) -> FinalCompetitorSetResponse:
    """
    Submit user's curation decisions.

    Validates that:
    - Required number of competitors removed
    - Final count is within limits (8-10)
    - Purpose overrides are valid

    Returns the finalized competitor set.
    """
    # Validate curation
    if len(curation.removals) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Must remove at least 5 competitors (removed {len(curation.removals)})"
        )

    # TODO: Apply curation to session and finalize

    # Mock response
    final_competitors = [
        FinalCompetitor(
            domain="competitor1.com",
            display_name="Competitor 1",
            purpose="keyword_source",
            priority=1,
            domain_rating=45,
            organic_traffic=50000,
            organic_keywords=2500,
            keyword_overlap=234,
            is_user_provided=False,
            is_user_curated=True,
        ),
    ]

    return FinalCompetitorSetResponse(
        session_id=session_id,
        status="curated",
        final_competitors=final_competitors,
        competitor_count=len(final_competitors),
        removed_count=len(curation.removals),
        added_count=len(curation.additions),
        finalized_at=datetime.utcnow(),
    )


@router.patch("/sessions/{session_id}/competitors", response_model=FinalCompetitorSetResponse)
async def update_competitors(
    session_id: UUID,
    updates: CompetitorUpdateInput,
) -> FinalCompetitorSetResponse:
    """
    Update competitors after finalization.

    Allows users to:
    - Remove competitors from the final set
    - Add new competitors
    - Change competitor purposes

    Note: Significant changes may trigger reanalysis.
    """
    # TODO: Implement post-finalization updates
    raise HTTPException(status_code=501, detail="Not implemented")


# =============================================================================
# GREENFIELD DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/dashboard/{analysis_run_id}", response_model=GreenfieldDashboardResponse)
async def get_greenfield_dashboard(analysis_run_id: UUID) -> GreenfieldDashboardResponse:
    """
    Get complete greenfield dashboard data.

    Returns:
    - Curated competitors with purposes
    - Market opportunity (TAM/SAM/SOM)
    - Beachhead keywords
    - Traffic projections
    - Growth roadmap
    """
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="Analysis not found")


@router.get("/dashboard/{analysis_run_id}/beachheads", response_model=List[BeachheadKeyword])
async def get_beachhead_keywords(
    analysis_run_id: UUID,
    phase: Optional[int] = None,
    min_winnability: Optional[float] = None,
) -> List[BeachheadKeyword]:
    """
    Get beachhead keywords for greenfield analysis.

    Optionally filter by:
    - Growth phase (1=Foundation, 2=Traction, 3=Authority)
    - Minimum winnability score
    """
    # TODO: Fetch from database with filters
    raise HTTPException(status_code=404, detail="Analysis not found")


@router.get("/dashboard/{analysis_run_id}/market-map")
async def get_market_map(analysis_run_id: UUID) -> Dict[str, Any]:
    """
    Get market map data for visualization.

    Returns competitor positioning data for the market map component.
    """
    # TODO: Implement market map data
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/dashboard/{analysis_run_id}/projections", response_model=TrafficProjectionsResponse)
async def get_traffic_projections(analysis_run_id: UUID) -> TrafficProjectionsResponse:
    """
    Get traffic projections for greenfield domain.

    Returns three scenarios: conservative, expected, aggressive
    """
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="Analysis not found")


@router.get("/dashboard/{analysis_run_id}/roadmap", response_model=List[GrowthPhase])
async def get_growth_roadmap(analysis_run_id: UUID) -> List[GrowthPhase]:
    """
    Get growth roadmap for greenfield domain.

    Returns phased keyword targeting strategy:
    - Phase 1: Foundation (months 1-3)
    - Phase 2: Traction (months 4-6)
    - Phase 3: Authority (months 7-12)
    """
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="Analysis not found")


# =============================================================================
# KEYWORD PHASE ASSIGNMENT
# =============================================================================

@router.patch("/keywords/{keyword_id}/phase")
async def assign_keyword_phase(
    keyword_id: UUID,
    phase: int,  # 1, 2, or 3
) -> Dict[str, Any]:
    """
    Assign a keyword to a growth phase.

    Phases:
    - 1: Foundation (high winnability, early targeting)
    - 2: Traction (medium difficulty, expansion)
    - 3: Authority (competitive, later targeting)
    """
    if phase not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Phase must be 1, 2, or 3")

    # TODO: Update keyword phase in database
    return {"keyword_id": str(keyword_id), "phase": phase, "updated": True}


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
) -> Dict[str, Any]:
    """
    Start a greenfield analysis.

    Creates an analysis run with greenfield context and triggers
    the competitor discovery pipeline.

    Returns:
    - analysis_run_id: UUID of the created analysis
    - session_id: UUID of the competitor intelligence session
    - status: Current status (discovering)
    """
    # TODO: Implement full greenfield analysis trigger

    analysis_run_id = uuid4()
    session_id = uuid4()

    return {
        "analysis_run_id": str(analysis_run_id),
        "session_id": str(session_id),
        "status": "discovering",
        "message": "Greenfield analysis started. Competitor discovery in progress.",
        "next_step": f"/api/greenfield/sessions/{session_id}",
    }

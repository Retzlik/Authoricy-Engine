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

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from src.database.models import (
    AnalysisRun,
    AnalysisMode,
    AnalysisStatus,
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
from src.collector.client import DataForSEOClient
from src.integrations import ExternalAPIClients, ExternalAPIConfig

logger = logging.getLogger(__name__)

# Authenticated router - requires login for all endpoints
router = APIRouter(
    prefix="/api/greenfield",
    tags=["greenfield"],
    dependencies=[Depends(get_current_user)],
)

# Public router - no authentication required
# Used for endpoints that should be accessible without login (e.g., maturity check)
public_router = APIRouter(
    prefix="/api/greenfield",
    tags=["greenfield"],
)


# =============================================================================
# DEBUG ENDPOINT (for testing routing)
# =============================================================================

@public_router.get("/debug/ping")
async def debug_ping():
    """
    Simple ping endpoint to verify greenfield routing works.
    No auth required. Use this to test if requests reach the server.
    """
    logger.info("[DEBUG] Ping endpoint called - routing is working!")
    return {
        "status": "ok",
        "message": "Greenfield API is reachable",
        "endpoints": {
            "analyze": "POST /api/greenfield/analyze",
            "get_session": "GET /api/greenfield/sessions/{session_id}",
            "curate": "POST /api/greenfield/sessions/{session_id}/curate",
            "dashboard": "GET /api/greenfield/dashboard/{analysis_run_id}",
        }
    }


@public_router.post("/debug/sessions/{session_id}/test-curate")
async def debug_curate_route(session_id: str):
    """
    Debug endpoint to test if POST to /sessions/{id}/xxx pattern works.
    No auth required. This helps diagnose routing issues.
    """
    logger.info(f"[DEBUG] Test curate route called with session_id={session_id}")
    return {
        "status": "ok",
        "message": "POST route pattern is working",
        "session_id_received": session_id,
        "route_pattern": "/sessions/{session_id}/test-curate",
    }


@public_router.post("/sessions/{session_id}/curate-test")
async def debug_curate_exact_pattern(session_id: str, request: Request):
    """
    Debug endpoint with EXACT same path pattern as real /curate (but different suffix).
    No auth required. Tests if the sessions/{id}/curate-xxx pattern works.

    Also logs all request details to help debug.
    """
    headers = dict(request.headers)
    logger.info(f"[DEBUG-CURATE-TEST] session_id={session_id}")
    logger.info(f"[DEBUG-CURATE-TEST] method={request.method}")
    logger.info(f"[DEBUG-CURATE-TEST] headers={headers}")

    body = None
    try:
        body = await request.json()
    except:
        body = "Could not parse JSON body"

    logger.info(f"[DEBUG-CURATE-TEST] body={body}")

    return {
        "status": "ok",
        "message": "curate-test pattern reached successfully",
        "session_id": session_id,
        "method": request.method,
        "content_type": headers.get("content-type"),
        "origin": headers.get("origin"),
        "body_received": body is not None and body != "Could not parse JSON body",
    }


@public_router.get("/debug/sessions/{session_id}/check")
async def debug_session_check(session_id: str):
    """
    Debug endpoint to check if a session exists in the database.
    No auth required. Helps diagnose session lookup issues.
    """
    from src.database.session import get_db_context
    from src.database.models import CompetitorIntelligenceSession
    from uuid import UUID

    logger.info(f"[DEBUG] Session check called for session_id={session_id}")

    try:
        session_uuid = UUID(session_id)
    except ValueError:
        return {
            "status": "error",
            "message": "Invalid UUID format",
            "session_id": session_id,
        }

    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.id == session_uuid
        ).first()

        if session:
            return {
                "status": "ok",
                "message": "Session found",
                "session_id": str(session.id),
                "session_status": session.status,
                "has_candidates": bool(session.candidate_competitors),
                "candidate_count": len(session.candidate_competitors or []),
            }
        else:
            return {
                "status": "not_found",
                "message": "Session does not exist in database",
                "session_id": session_id,
            }


@public_router.get("/debug/domain/{domain_name}")
async def debug_domain_check(domain_name: str):
    """
    Debug endpoint to check domain ownership and analysis data.
    No auth required. Helps diagnose why domains don't appear in selector.
    """
    from src.database.session import get_db_context

    logger.info(f"[DEBUG] Domain check called for domain={domain_name}")

    with get_db_context() as db:
        domain_obj = db.query(Domain).filter(Domain.domain == domain_name).first()

        if not domain_obj:
            return {
                "status": "not_found",
                "message": f"Domain {domain_name} does not exist in database",
            }

        # Get analysis runs for this domain
        runs = db.query(AnalysisRun).filter(
            AnalysisRun.domain_id == domain_obj.id
        ).order_by(AnalysisRun.created_at.desc()).limit(5).all()

        return {
            "status": "found",
            "domain": {
                "id": str(domain_obj.id),
                "domain": domain_obj.domain,
                "user_id": str(domain_obj.user_id) if domain_obj.user_id else None,
                "is_active": domain_obj.is_active,
                "analysis_count": domain_obj.analysis_count,
                "created_at": domain_obj.created_at.isoformat() if domain_obj.created_at else None,
            },
            "recent_analysis_runs": [
                {
                    "id": str(run.id),
                    "status": str(run.status.value) if run.status else None,
                    "analysis_mode": str(run.analysis_mode.value) if run.analysis_mode else None,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                }
                for run in runs
            ],
        }


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


def resolve_greenfield_analysis(id_param: UUID, user: User, db) -> AnalysisRun:
    """
    Resolve an ID to a greenfield analysis run.

    The ID can be either:
    - An analysis_run_id (direct lookup)
    - A domain_id (finds the latest completed greenfield analysis for that domain)

    This allows frontend to use either ID type and get the expected result.

    Returns the AnalysisRun or raises HTTPException(404) if not found.
    """
    # First, try as analysis_run_id
    run = db.query(AnalysisRun).get(id_param)
    if run:
        check_analysis_access(run, user, db)
        return run

    # If not found, try as domain_id - find latest greenfield analysis
    domain = db.query(Domain).get(id_param)
    if domain:
        check_domain_access_greenfield(domain, user)
        run = db.query(AnalysisRun).filter(
            AnalysisRun.domain_id == id_param,
            AnalysisRun.analysis_mode == AnalysisMode.GREENFIELD,
            AnalysisRun.status == AnalysisStatus.COMPLETED
        ).order_by(AnalysisRun.completed_at.desc()).first()

        if run:
            return run

    # Neither worked - not found
    raise HTTPException(
        status_code=404,
        detail="Analysis not found. The ID must be a valid analysis_run_id or domain_id with a completed greenfield analysis."
    )


# Service instance (will be initialized with client in production)
greenfield_service = GreenfieldService()


# =============================================================================
# BACKGROUND TASK FOR DEEP ANALYSIS
# =============================================================================

async def run_deep_analysis_background(
    session_id: UUID,
    analysis_run_id: UUID,
    domain_id: UUID,
    domain: str,
    final_competitors: List[Dict],
    greenfield_context: Dict,
    market: str,
):
    """
    Run deep analysis (G2-G5) as a background task.

    This is triggered after curation is saved and runs independently
    of the HTTP request, so the frontend doesn't timeout.
    """
    from src.database.session import get_db_context
    from src.database import repository
    from src.database.models import AnalysisStatus

    logger.info(f"[BACKGROUND] Starting deep analysis for session {session_id}")

    # Get DataForSEO credentials
    dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
    dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

    if not dataforseo_login or not dataforseo_password:
        logger.error(f"[BACKGROUND] DataForSEO credentials not configured for session {session_id}")
        with get_db_context() as db:
            session = db.query(CompetitorIntelligenceSession).filter(
                CompetitorIntelligenceSession.id == session_id
            ).first()
            if session:
                session.status = "failed"
                db.commit()
        return

    try:
        # Update status to ANALYZING
        repository.update_run_status(
            analysis_run_id,
            AnalysisStatus.ANALYZING,
            phase="deep_analysis",
            progress=10,
        )

        # Run deep analysis
        async with DataForSEOClient(
            login=dataforseo_login,
            password=dataforseo_password
        ) as dataforseo_client:
            service_with_client = GreenfieldService(
                dataforseo_client=dataforseo_client,
            )

            result = await service_with_client.run_deep_analysis(
                session_id=session_id,
                analysis_run_id=analysis_run_id,
                domain_id=domain_id,
                domain=domain,
                final_competitors=final_competitors,
                greenfield_context=greenfield_context,
                market=market,
            )

        # Update session status based on result
        with get_db_context() as db:
            session = db.query(CompetitorIntelligenceSession).filter(
                CompetitorIntelligenceSession.id == session_id
            ).first()
            if session:
                if result.get("success"):
                    session.status = "completed"
                    logger.info(f"[BACKGROUND] Deep analysis completed for session {session_id}")
                else:
                    session.status = "failed"
                    logger.error(f"[BACKGROUND] Deep analysis failed for session {session_id}: {result.get('error')}")
                db.commit()

    except Exception as e:
        logger.error(f"[BACKGROUND] Deep analysis error for session {session_id}: {e}")
        # Mark as failed
        try:
            repository.fail_run(analysis_run_id, error_message=str(e))
            with get_db_context() as db:
                session = db.query(CompetitorIntelligenceSession).filter(
                    CompetitorIntelligenceSession.id == session_id
                ).first()
                if session:
                    session.status = "failed"
                    db.commit()
        except Exception as inner_e:
            logger.error(f"[BACKGROUND] Failed to update failure status: {inner_e}")


def start_background_analysis(
    session_id: UUID,
    analysis_run_id: UUID,
    domain_id: UUID,
    domain: str,
    final_competitors: List[Dict],
    greenfield_context: Dict,
    market: str,
):
    """
    Start the background analysis task.

    Uses asyncio.create_task to run the analysis independently of the request.
    """
    asyncio.create_task(
        run_deep_analysis_background(
            session_id=session_id,
            analysis_run_id=analysis_run_id,
            domain_id=domain_id,
            domain=domain,
            final_competitors=final_competitors,
            greenfield_context=greenfield_context,
            market=market,
        )
    )


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

@public_router.get("/maturity/{domain}", response_model=DomainMaturityResponse)
async def check_domain_maturity(domain: str) -> DomainMaturityResponse:
    """
    Check domain maturity to determine analysis mode.

    Returns whether the domain should use greenfield analysis.

    Note: This is a PUBLIC endpoint (no auth required) for preliminary checks.
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


@router.options("/sessions/{session_id}/curate")
async def curate_options(session_id: UUID):
    """
    Handle OPTIONS preflight for /curate endpoint.
    FastAPI's CORSMiddleware should handle this, but adding explicit handler for debugging.
    """
    logger.info(f"[CURATE-OPTIONS] Preflight request for session {session_id}")
    return {"status": "ok"}


@router.post("/sessions/{session_id}/curate")
async def submit_curation(
    session_id: UUID,
    curation: CurationInput,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Submit user's curation decisions and trigger deep analysis asynchronously.

    This endpoint:
    1. Validates and saves the curation decisions
    2. Starts deep analysis (G2-G5) as a BACKGROUND task
    3. Returns IMMEDIATELY with status "analyzing"

    The frontend should poll GET /sessions/{session_id} to check when
    status changes from "analyzing" to "completed" or "failed".

    Validates that:
    - Final count is within limits (3-15 competitors)
    - Purpose overrides are valid

    Returns immediately with status "analyzing" so the browser doesn't timeout.
    """
    logger.info(
        f"[CURATE] *** REQUEST REACHED HANDLER *** session={session_id} "
        f"user={current_user.email if current_user else 'unknown'}"
    )
    logger.info(
        f"[CURATE] Curation input: removals={len(curation.removals)}, "
        f"additions={len(curation.additions)}, overrides={len(curation.purpose_overrides)}"
    )

    from src.database.session import get_db_context
    from src.database import repository
    from src.database.models import AnalysisStatus

    # Check access and get session data
    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.id == session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        check_session_access(session, current_user, db)

        # Get analysis run info for later
        analysis_run_id = session.analysis_run_id
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis run not found")

        domain_id = run.domain_id
        domain_obj = db.query(Domain).get(domain_id)
        domain = domain_obj.domain if domain_obj else None
        greenfield_context = run.greenfield_context or {}

    # Step 1: Submit curation (fast - just database write)
    try:
        curation_result = greenfield_service.submit_curation(
            session_id=session_id,
            removals=[r.model_dump() for r in curation.removals],
            additions=[a.model_dump() for a in curation.additions],
            purpose_overrides=[p.model_dump() for p in curation.purpose_overrides],
        )

        if not curation_result:
            raise HTTPException(status_code=404, detail="Session not found")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Step 2: Get finalized competitors
    final_competitors = curation_result.get("final_competitors", [])

    if not final_competitors:
        raise HTTPException(
            status_code=400,
            detail="No finalized competitors. Curation may have failed."
        )

    # Step 3: Check credentials
    dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
    dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

    if not dataforseo_login or not dataforseo_password:
        return {
            **curation_result,
            "status": "failed",
            "analysis_status": "failed",
            "analysis_message": "DataForSEO credentials not configured.",
        }

    # Step 4: Update session status to "analyzing" and start background task
    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.id == session_id
        ).first()
        if session:
            session.status = "analyzing"
            db.commit()

    # Step 5: Start background analysis task (non-blocking)
    logger.info(f"[CURATE] Starting background analysis for session {session_id}")
    start_background_analysis(
        session_id=session_id,
        analysis_run_id=analysis_run_id,
        domain_id=domain_id,
        domain=domain,
        final_competitors=final_competitors,
        greenfield_context=greenfield_context,
        market=greenfield_context.get("target_market", "United States"),
    )

    # Step 6: Return immediately with "analyzing" status
    return {
        **curation_result,
        "status": "analyzing",
        "analysis_status": "analyzing",
        "analysis_message": "Deep analysis started. Poll GET /sessions/{session_id} for status updates.",
        "poll_endpoint": f"/api/greenfield/sessions/{session_id}",
        "expected_duration_seconds": 300,  # ~5 minutes typical
    }


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


@router.post("/sessions/{session_id}/continue")
async def continue_analysis(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Continue analysis after competitor curation.

    NOTE: This endpoint is DEPRECATED. The /curate endpoint now handles
    everything automatically. You do NOT need to call this endpoint.

    If you see this error, the frontend should be calling /curate instead.

    This triggers the deep analysis pipeline (G2-G5):
    - G2: Keyword Universe Construction (mining competitor keywords)
    - G3: SERP Analysis & Winnability Scoring
    - G4: Market Sizing (TAM/SAM/SOM)
    - G5: Beachhead Selection & Growth Roadmap

    Prerequisites:
    - Session must be in "curated" status (competitors confirmed)

    Returns:
    - analysis_run_id: UUID of the analysis
    - status: "completed" or "failed"
    - keywords_count: Number of keywords discovered
    - beachheads_count: Number of beachhead keywords selected
    - market_opportunity: TAM/SAM/SOM summary
    """
    # DEBUG: Log that this deprecated endpoint was called
    logger.warning(
        f"[CONTINUE] DEPRECATED endpoint called for session {session_id}. "
        f"Frontend should use /curate instead. User: {current_user.email if current_user else 'unknown'}"
    )

    from src.database.session import get_db_context
    from src.database import repository
    from src.database.models import AnalysisStatus

    # Check access and get session
    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.id == session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        check_session_access(session, current_user, db)

        # Verify session is curated
        if session.status != "curated":
            raise HTTPException(
                status_code=400,
                detail=f"Session must be curated before continuing. Current status: {session.status}"
            )

        # Get analysis run
        analysis_run_id = session.analysis_run_id
        run = db.query(AnalysisRun).get(analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis run not found")

        domain_id = run.domain_id
        domain_obj = db.query(Domain).get(domain_id)
        domain = domain_obj.domain if domain_obj else None
        greenfield_context = run.greenfield_context or {}

        # Get finalized competitors
        final_competitors = session.final_competitors or []

    if not final_competitors:
        raise HTTPException(
            status_code=400,
            detail="No finalized competitors found. Please complete curation first."
        )

    # Get DataForSEO credentials
    dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
    dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

    if not dataforseo_login or not dataforseo_password:
        raise HTTPException(
            status_code=500,
            detail="DataForSEO credentials not configured. Cannot run deep analysis."
        )

    try:
        # Update status to ANALYZING
        repository.update_run_status(
            analysis_run_id,
            AnalysisStatus.ANALYZING,
            phase="deep_analysis",
            progress=10,
        )

        # Run deep analysis
        async with DataForSEOClient(
            login=dataforseo_login,
            password=dataforseo_password
        ) as dataforseo_client:
            # Create service with client
            service_with_client = GreenfieldService(
                dataforseo_client=dataforseo_client,
            )

            result = await service_with_client.run_deep_analysis(
                session_id=session_id,
                analysis_run_id=analysis_run_id,
                domain_id=domain_id,
                domain=domain,
                final_competitors=final_competitors,
                greenfield_context=greenfield_context,
                market=greenfield_context.get("target_market", "United States"),
            )

        if result.get("success"):
            return {
                "analysis_run_id": str(analysis_run_id),
                "session_id": str(session_id),
                "status": "completed",
                "message": "Deep analysis completed successfully. Dashboard is now ready.",
                "keywords_count": result.get("keywords_count", 0),
                "beachheads_count": result.get("beachheads_count", 0),
                "market_opportunity": result.get("market_opportunity", {}),
                "next_step": f"/api/greenfield/dashboard/{analysis_run_id}",
            }
        else:
            return {
                "analysis_run_id": str(analysis_run_id),
                "session_id": str(session_id),
                "status": "failed",
                "message": result.get("error", "Deep analysis failed"),
                "errors": result.get("errors", []),
            }

    except Exception as e:
        logger.error(f"Deep analysis failed for session {session_id}: {e}")
        # Mark as failed
        repository.fail_run(
            analysis_run_id,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


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

    The analysis_run_id parameter can be either:
    - An actual analysis_run_id
    - A domain_id (will find the latest completed greenfield analysis)

    Returns:
    - Curated competitors with purposes
    - Market opportunity (TAM/SAM/SOM)
    - Beachhead keywords
    - Traffic projections
    - Growth roadmap
    """
    from src.database.session import get_db_context

    # Resolve the ID (could be analysis_run_id or domain_id)
    with get_db_context() as db:
        run = resolve_greenfield_analysis(analysis_run_id, current_user, db)
        actual_analysis_id = run.id

    result = greenfield_service.get_dashboard(actual_analysis_id)
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

    The analysis_run_id parameter can be either:
    - An actual analysis_run_id
    - A domain_id (will find the latest completed greenfield analysis)

    Optionally filter by:
    - Growth phase (1=Foundation, 2=Traction, 3=Authority)
    - Minimum winnability score
    """
    from src.database.session import get_db_context

    # Resolve the ID (could be analysis_run_id or domain_id)
    with get_db_context() as db:
        run = resolve_greenfield_analysis(analysis_run_id, current_user, db)
        actual_analysis_id = run.id

    keywords = greenfield_service.get_beachheads(
        analysis_run_id=actual_analysis_id,
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

    The analysis_run_id parameter can be either:
    - An actual analysis_run_id
    - A domain_id (will find the latest completed greenfield analysis)

    Returns competitor positioning data for the market map component.
    """
    from src.database.session import get_db_context

    # Resolve the ID (could be analysis_run_id or domain_id)
    with get_db_context() as db:
        run = resolve_greenfield_analysis(analysis_run_id, current_user, db)
        actual_analysis_id = run.id

    dashboard = greenfield_service.get_dashboard(actual_analysis_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Extract market map data from competitors
    competitors = dashboard.get("competitors", [])

    return {
        "analysis_run_id": str(actual_analysis_id),
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

    The analysis_run_id parameter can be either:
    - An actual analysis_run_id
    - A domain_id (will find the latest completed greenfield analysis)

    Returns three scenarios: conservative, expected, aggressive
    """
    from src.database.session import get_db_context

    # Resolve the ID (could be analysis_run_id or domain_id)
    with get_db_context() as db:
        run = resolve_greenfield_analysis(analysis_run_id, current_user, db)
        actual_analysis_id = run.id

    dashboard = greenfield_service.get_dashboard(actual_analysis_id)
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

    The analysis_run_id parameter can be either:
    - An actual analysis_run_id
    - A domain_id (will find the latest completed greenfield analysis)

    Returns phased keyword targeting strategy:
    - Phase 1: Foundation (months 1-3)
    - Phase 2: Traction (months 4-6)
    - Phase 3: Authority (months 7-12)
    """
    from src.database.session import get_db_context

    # Resolve the ID (could be analysis_run_id or domain_id)
    with get_db_context() as db:
        run = resolve_greenfield_analysis(analysis_run_id, current_user, db)
        actual_analysis_id = run.id

    dashboard = greenfield_service.get_dashboard(actual_analysis_id)
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

    # Get DataForSEO credentials
    dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
    dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

    try:
        # Use the global service for creating the analysis run (no client needed)
        analysis_run_id, session_id = greenfield_service.start_greenfield_analysis(
            domain=request.domain,
            greenfield_context=greenfield_context,
            user_id=current_user.id,
        )

        # Initialize API clients for competitor discovery
        external_clients = None
        dataforseo_client = None

        try:
            # Initialize external API clients (Perplexity, Firecrawl)
            external_clients = ExternalAPIClients()
            logger.info(
                f"External API clients initialized: "
                f"perplexity={external_clients.perplexity is not None}, "
                f"firecrawl={external_clients.firecrawl is not None}"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize external API clients: {e}")

        # Trigger competitor discovery with clients
        if dataforseo_login and dataforseo_password:
            logger.info(
                "DataForSEO credentials configured - SERP discovery and metric enrichment ENABLED"
            )
            async with DataForSEOClient(
                login=dataforseo_login,
                password=dataforseo_password
            ) as dataforseo_client:
                # Create service with clients
                service_with_clients = GreenfieldService(
                    dataforseo_client=dataforseo_client,
                    external_api_clients=external_clients,
                )

                await service_with_clients.discover_competitors(
                    session_id=session_id,
                    seed_keywords=request.seed_keywords,
                    known_competitors=request.known_competitors,
                    market=request.target_market or "United States",  # FIXED: pass full name, not broken [:2]
                    business_context=greenfield_context,
                    target_domain=request.domain,  # Enable Firecrawl website scraping
                )
        else:
            # No DataForSEO credentials - use service with just external clients
            logger.error(
                "DataForSEO credentials NOT configured! "
                "SERP discovery DISABLED. Metric enrichment (DR, Traffic, Keywords) DISABLED. "
                "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD environment variables to enable."
            )
            service_with_clients = GreenfieldService(
                external_api_clients=external_clients,
            )

            await service_with_clients.discover_competitors(
                session_id=session_id,
                seed_keywords=request.seed_keywords,
                known_competitors=request.known_competitors,
                market=request.target_market or "United States",  # FIXED: pass full name, not broken [:2]
                business_context=greenfield_context,
                target_domain=request.domain,  # Enable Firecrawl website scraping
            )

        # Cleanup external clients
        if external_clients:
            try:
                await external_clients.close()
            except Exception:
                pass

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

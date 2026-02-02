"""
Unified Analysis API - Single Entry Point

This module implements the superior unified analysis architecture where:
- One endpoint accepts any domain
- System auto-detects maturity (greenfield/hybrid/established)
- Progressive disclosure asks only for what's needed
- Backend drives the UX, frontend just renders

Flow:
1. POST /api/v2/analyze {domain} → Returns mode + next_action
2. POST /api/v2/analyze/{id}/context {business_context} → For greenfield/hybrid
3. POST /api/v2/analyze/{id}/curate {curation} → For competitor curation
4. GET /api/v2/analyze/{id}/status → Poll for progress
5. GET /api/v2/dashboard/{id} → Unified dashboard for all modes
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

from src.database.models import (
    AnalysisRun,
    AnalysisMode,
    AnalysisStatus,
    Domain,
    CompetitorIntelligenceSession,
    GreenfieldAnalysis,
    Keyword,
)
from src.database.session import get_db_context
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.scoring.greenfield import (
    DomainMaturity,
    classify_domain_maturity,
    DomainMetrics,
)
from src.services.greenfield import GreenfieldService
from src.collector.client import DataForSEOClient

logger = logging.getLogger(__name__)

# Router with v2 prefix for new unified API
router = APIRouter(
    prefix="/api/v2",
    tags=["Unified Analysis"],
    dependencies=[Depends(get_current_user)],
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FormField(BaseModel):
    """Dynamic form field definition - frontend renders based on this."""
    field_name: str
    label: str
    field_type: Literal["text", "textarea", "tags", "select", "email"]
    required: bool
    placeholder: Optional[str] = None
    min_items: Optional[int] = None  # For tags/arrays
    max_items: Optional[int] = None
    options: Optional[List[str]] = None  # For select
    help_text: Optional[str] = None


class MaturityMetrics(BaseModel):
    """Domain maturity metrics shown to user for transparency."""
    domain_rating: int
    organic_keywords: int
    organic_traffic: int
    classification: Literal["greenfield", "emerging", "established"]
    explanation: str


class CompetitorCandidate(BaseModel):
    """Competitor discovered during analysis."""
    domain: str
    domain_rating: int = 0
    organic_traffic: int = 0
    organic_keywords: int = 0
    discovery_source: str  # perplexity, serp, traffic_share, user_provided
    relevance_score: float = 0.0
    suggested_purpose: str = "keyword_source"
    discovery_reason: str = ""


class AnalysisProgress(BaseModel):
    """Progress tracking for async analysis."""
    phase: str
    phase_number: int
    total_phases: int
    progress_percent: int
    message: str
    started_at: datetime
    estimated_completion: Optional[datetime] = None


class NextAction(BaseModel):
    """Tells frontend exactly what to do next."""
    action: Literal[
        "provide_context",     # Need business context (greenfield/hybrid)
        "curate_competitors",  # User reviews competitor list
        "poll_status",         # Analysis in progress
        "view_dashboard"       # Complete - show results
    ]

    # For provide_context action
    required_fields: Optional[List[FormField]] = None
    optional_fields: Optional[List[FormField]] = None

    # For curate_competitors action
    competitors: Optional[List[CompetitorCandidate]] = None
    min_competitors: Optional[int] = None
    max_competitors: Optional[int] = None

    # For poll_status action
    progress: Optional[AnalysisProgress] = None
    poll_interval_seconds: Optional[int] = None

    # For view_dashboard action
    dashboard_url: Optional[str] = None


class UnifiedAnalysisRequest(BaseModel):
    """The only request needed to start analysis - just the domain."""
    domain: str = Field(..., description="Domain to analyze (e.g., example.com)")


class UnifiedAnalysisResponse(BaseModel):
    """Smart response that tells frontend what to do next."""
    analysis_id: UUID
    domain: str
    detected_mode: Literal["greenfield", "hybrid", "established"]
    maturity: MaturityMetrics
    status: str
    message: str
    next_action: NextAction

    # Endpoints for subsequent actions
    context_endpoint: Optional[str] = None
    curate_endpoint: Optional[str] = None
    status_endpoint: Optional[str] = None
    dashboard_endpoint: Optional[str] = None


class BusinessContext(BaseModel):
    """Business context for greenfield/hybrid analysis."""
    company_name: str = Field(..., min_length=1)
    business_description: str = Field(..., min_length=10)
    primary_offering: str = Field(..., min_length=1)
    target_market: str = "United States"
    industry_vertical: str = "saas"
    seed_keywords: List[str] = Field(default_factory=list)
    known_competitors: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    email: Optional[EmailStr] = None


class ContextSubmission(BaseModel):
    """Submit business context for greenfield/hybrid."""
    business_context: BusinessContext


class CurationSubmission(BaseModel):
    """Submit competitor curation decisions."""
    removals: List[str] = Field(default_factory=list, description="Domains to remove")
    additions: List[str] = Field(default_factory=list, description="Domains to add")
    purpose_overrides: Dict[str, str] = Field(default_factory=dict, description="Domain -> purpose mapping")


# =============================================================================
# FORM FIELD DEFINITIONS
# =============================================================================

GREENFIELD_REQUIRED_FIELDS = [
    FormField(
        field_name="company_name",
        label="Company Name",
        field_type="text",
        required=True,
        placeholder="e.g., Acme Inc.",
    ),
    FormField(
        field_name="business_description",
        label="What does your company do?",
        field_type="textarea",
        required=True,
        placeholder="Describe your business in 2-3 sentences...",
        help_text="This helps us find the right competitors and keywords.",
    ),
    FormField(
        field_name="primary_offering",
        label="Main Product or Service",
        field_type="text",
        required=True,
        placeholder="e.g., Invoice software, Dog food, Marketing agency",
    ),
    FormField(
        field_name="seed_keywords",
        label="Keywords You Want to Rank For",
        field_type="tags",
        required=True,
        min_items=5,
        max_items=20,
        placeholder="Enter keywords and press Enter",
        help_text="Add at least 5 keywords that describe what you want to be found for.",
    ),
    FormField(
        field_name="known_competitors",
        label="Your Competitors",
        field_type="tags",
        required=True,
        min_items=3,
        max_items=10,
        placeholder="competitor.com",
        help_text="Add at least 3 competitor domains. We'll discover more automatically.",
    ),
]

GREENFIELD_OPTIONAL_FIELDS = [
    FormField(
        field_name="target_market",
        label="Target Market",
        field_type="select",
        required=False,
        options=["United States", "United Kingdom", "Germany", "France", "Canada", "Australia"],
    ),
    FormField(
        field_name="industry_vertical",
        label="Industry",
        field_type="select",
        required=False,
        options=["saas", "ecommerce", "agency", "media", "fintech", "healthcare", "education", "other"],
    ),
    FormField(
        field_name="target_audience",
        label="Target Audience",
        field_type="textarea",
        required=False,
        placeholder="Describe your ideal customer...",
    ),
    FormField(
        field_name="email",
        label="Email (for notifications)",
        field_type="email",
        required=False,
        placeholder="you@company.com",
    ),
]

HYBRID_REQUIRED_FIELDS = [
    FormField(
        field_name="company_name",
        label="Company Name",
        field_type="text",
        required=True,
        placeholder="e.g., Acme Inc.",
    ),
    FormField(
        field_name="business_description",
        label="What does your company do?",
        field_type="textarea",
        required=True,
        placeholder="Describe your business...",
    ),
    FormField(
        field_name="primary_offering",
        label="Main Product or Service",
        field_type="text",
        required=True,
        placeholder="e.g., Invoice software",
    ),
]

HYBRID_OPTIONAL_FIELDS = [
    FormField(
        field_name="seed_keywords",
        label="Additional Keywords (optional)",
        field_type="tags",
        required=False,
        min_items=0,
        max_items=10,
        placeholder="Enter keywords to focus on",
        help_text="We'll analyze your existing keywords plus these.",
    ),
    FormField(
        field_name="known_competitors",
        label="Additional Competitors (optional)",
        field_type="tags",
        required=False,
        min_items=0,
        max_items=5,
        placeholder="competitor.com",
        help_text="We'll auto-detect competitors from your keywords plus these.",
    ),
]

ESTABLISHED_OPTIONAL_FIELDS = [
    FormField(
        field_name="email",
        label="Email (for report delivery)",
        field_type="email",
        required=False,
        placeholder="you@company.com",
        help_text="We'll email you when the analysis is complete.",
    ),
    FormField(
        field_name="company_name",
        label="Company Name (optional)",
        field_type="text",
        required=False,
        placeholder="For personalized reports",
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_maturity_explanation(maturity: DomainMaturity, metrics: DomainMetrics) -> str:
    """Generate human-readable explanation of domain maturity."""
    if maturity == DomainMaturity.GREENFIELD:
        return (
            f"Your domain is new with limited online presence "
            f"(DR: {metrics.domain_rating}, Keywords: {metrics.organic_keywords}). "
            f"We'll help you find keywords you can rank for based on competitor analysis."
        )
    elif maturity == DomainMaturity.EMERGING:
        return (
            f"Your domain is growing "
            f"(DR: {metrics.domain_rating}, Keywords: {metrics.organic_keywords}). "
            f"We'll analyze your current performance and find opportunities to accelerate growth."
        )
    else:
        return (
            f"Your domain has established authority "
            f"(DR: {metrics.domain_rating}, Keywords: {metrics.organic_keywords}). "
            f"We'll perform a comprehensive audit to optimize your competitive position."
        )


async def detect_domain_maturity(domain: str) -> tuple[DomainMaturity, DomainMetrics]:
    """
    Detect domain maturity using DataForSEO.
    Returns (maturity_level, metrics).
    """
    dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
    dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

    if not dataforseo_login or not dataforseo_password:
        # Default to greenfield if no credentials
        logger.warning("DataForSEO credentials not configured, defaulting to greenfield")
        return DomainMaturity.GREENFIELD, DomainMetrics(
            domain_rating=0,
            organic_keywords=0,
            organic_traffic=0,
        )

    try:
        async with DataForSEOClient(
            login=dataforseo_login,
            password=dataforseo_password
        ) as client:
            # Get domain overview
            overview = await client.get_domain_overview(domain)

            # Get backlink summary for DR
            backlinks = await client.get_backlinks_summary(domain)

            metrics = DomainMetrics(
                domain_rating=backlinks.get("rank", 0) if backlinks else 0,
                organic_keywords=overview.get("organic_keywords", 0) if overview else 0,
                organic_traffic=overview.get("organic_traffic", 0) if overview else 0,
            )

            maturity = classify_domain_maturity(metrics)
            return maturity, metrics

    except Exception as e:
        logger.error(f"Failed to detect domain maturity: {e}")
        # Default to greenfield on error
        return DomainMaturity.GREENFIELD, DomainMetrics(
            domain_rating=0,
            organic_keywords=0,
            organic_traffic=0,
        )


def create_analysis_run(
    domain: str,
    user_id: UUID,
    mode: AnalysisMode,
    maturity: str,
    metrics: DomainMetrics,
) -> tuple[UUID, UUID]:
    """
    Create AnalysisRun and Domain records.
    Returns (analysis_run_id, domain_id).
    """
    from src.database import repository

    with get_db_context() as db:
        # Get or create domain
        domain_obj = db.query(Domain).filter(Domain.domain == domain).first()
        if not domain_obj:
            domain_obj = Domain(
                domain=domain,
                user_id=user_id,
                is_active=True,
            )
            db.add(domain_obj)
            db.flush()
        elif domain_obj.user_id != user_id:
            # Update ownership if needed
            domain_obj.user_id = user_id

        # Create analysis run
        analysis_run = AnalysisRun(
            domain_id=domain_obj.id,
            analysis_mode=mode,
            status=AnalysisStatus.PENDING,
            domain_maturity_at_analysis=maturity,
            domain_rating_at_analysis=metrics.domain_rating,
            organic_keywords_at_analysis=metrics.organic_keywords,
            organic_traffic_at_analysis=metrics.organic_traffic,
        )
        db.add(analysis_run)
        db.commit()

        return analysis_run.id, domain_obj.id


# =============================================================================
# MAIN ENDPOINTS
# =============================================================================

@router.post("/analyze", response_model=UnifiedAnalysisResponse)
async def start_unified_analysis(
    request: UnifiedAnalysisRequest,
    current_user: User = Depends(get_current_user),
) -> UnifiedAnalysisResponse:
    """
    Start analysis for any domain.

    This is the single entry point for all analysis types.
    The system auto-detects domain maturity and tells the frontend
    exactly what to do next.

    Flow:
    1. Detects domain maturity (greenfield/hybrid/established)
    2. Creates analysis run in PENDING state
    3. Returns next_action telling frontend what's needed

    For GREENFIELD/HYBRID: next_action = "provide_context"
    For ESTABLISHED: next_action = "poll_status" (analysis starts immediately)
    """
    domain = request.domain.lower().strip()

    # Remove protocol if present
    if domain.startswith("http://"):
        domain = domain[7:]
    elif domain.startswith("https://"):
        domain = domain[8:]

    # Remove trailing slash and www
    domain = domain.rstrip("/")
    if domain.startswith("www."):
        domain = domain[4:]

    logger.info(f"[UNIFIED] Starting analysis for domain: {domain}, user: {current_user.email}")

    # Step 1: Detect maturity
    maturity, metrics = await detect_domain_maturity(domain)

    # Map maturity to mode
    mode_map = {
        DomainMaturity.GREENFIELD: AnalysisMode.GREENFIELD,
        DomainMaturity.EMERGING: AnalysisMode.HYBRID,
        DomainMaturity.ESTABLISHED: AnalysisMode.STANDARD,
    }
    mode = mode_map[maturity]
    maturity_str = maturity.value.lower()

    logger.info(f"[UNIFIED] Detected maturity: {maturity_str} (DR={metrics.domain_rating}, KW={metrics.organic_keywords})")

    # Step 2: Create analysis run
    analysis_id, domain_id = create_analysis_run(
        domain=domain,
        user_id=current_user.id,
        mode=mode,
        maturity=maturity_str,
        metrics=metrics,
    )

    # Step 3: Build response based on mode
    maturity_response = MaturityMetrics(
        domain_rating=metrics.domain_rating,
        organic_keywords=metrics.organic_keywords,
        organic_traffic=metrics.organic_traffic,
        classification=maturity_str,
        explanation=get_maturity_explanation(maturity, metrics),
    )

    # Common endpoints
    base_response = {
        "analysis_id": analysis_id,
        "domain": domain,
        "detected_mode": maturity_str,
        "maturity": maturity_response,
        "context_endpoint": f"/api/v2/analyze/{analysis_id}/context",
        "curate_endpoint": f"/api/v2/analyze/{analysis_id}/curate",
        "status_endpoint": f"/api/v2/analyze/{analysis_id}/status",
        "dashboard_endpoint": f"/api/v2/dashboard/{analysis_id}",
    }

    if maturity == DomainMaturity.GREENFIELD:
        return UnifiedAnalysisResponse(
            **base_response,
            status="needs_context",
            message="Your domain is new. Tell us about your business so we can find the right opportunities.",
            next_action=NextAction(
                action="provide_context",
                required_fields=GREENFIELD_REQUIRED_FIELDS,
                optional_fields=GREENFIELD_OPTIONAL_FIELDS,
            ),
        )

    elif maturity == DomainMaturity.EMERGING:
        return UnifiedAnalysisResponse(
            **base_response,
            status="needs_context",
            message="Your domain is growing. Tell us about your business so we can accelerate your growth.",
            next_action=NextAction(
                action="provide_context",
                required_fields=HYBRID_REQUIRED_FIELDS,
                optional_fields=HYBRID_OPTIONAL_FIELDS,
            ),
        )

    else:  # ESTABLISHED
        # For established domains, we can start immediately (optionally collect email)
        return UnifiedAnalysisResponse(
            **base_response,
            status="ready_to_start",
            message="Your domain has strong authority. We can start the comprehensive analysis now.",
            next_action=NextAction(
                action="provide_context",  # Optional context, but show form
                required_fields=[],  # No required fields
                optional_fields=ESTABLISHED_OPTIONAL_FIELDS,
            ),
        )


@router.post("/analyze/{analysis_id}/context")
async def submit_context(
    analysis_id: UUID,
    submission: ContextSubmission,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> UnifiedAnalysisResponse:
    """
    Submit business context and start appropriate analysis flow.

    For GREENFIELD: Starts competitor discovery, returns "curate_competitors"
    For HYBRID: Starts hybrid analysis flow
    For ESTABLISHED: Starts full analysis
    """
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Verify ownership
        domain = db.query(Domain).get(run.domain_id)
        if domain.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        # Store context
        ctx = submission.business_context
        run.greenfield_context = {
            "company_name": ctx.company_name,
            "business_description": ctx.business_description,
            "primary_offering": ctx.primary_offering,
            "target_market": ctx.target_market,
            "industry_vertical": ctx.industry_vertical,
            "seed_keywords": ctx.seed_keywords,
            "known_competitors": ctx.known_competitors,
            "target_audience": ctx.target_audience,
        }

        mode = run.analysis_mode
        domain_name = domain.domain
        db.commit()

    logger.info(f"[UNIFIED] Context submitted for {analysis_id}, mode: {mode}")

    # Build base response
    base_response = {
        "analysis_id": analysis_id,
        "domain": domain_name,
        "detected_mode": run.domain_maturity_at_analysis,
        "maturity": MaturityMetrics(
            domain_rating=run.domain_rating_at_analysis or 0,
            organic_keywords=run.organic_keywords_at_analysis or 0,
            organic_traffic=run.organic_traffic_at_analysis or 0,
            classification=run.domain_maturity_at_analysis or "greenfield",
            explanation="",
        ),
        "context_endpoint": f"/api/v2/analyze/{analysis_id}/context",
        "curate_endpoint": f"/api/v2/analyze/{analysis_id}/curate",
        "status_endpoint": f"/api/v2/analyze/{analysis_id}/status",
        "dashboard_endpoint": f"/api/v2/dashboard/{analysis_id}",
    }

    if mode == AnalysisMode.GREENFIELD:
        # Start competitor discovery
        await start_competitor_discovery(
            analysis_id=analysis_id,
            domain=domain_name,
            context=submission.business_context,
        )

        # Get discovered competitors
        competitors = await get_competitor_candidates(analysis_id)

        return UnifiedAnalysisResponse(
            **base_response,
            status="awaiting_curation",
            message=f"Found {len(competitors)} potential competitors. Review and curate the list.",
            next_action=NextAction(
                action="curate_competitors",
                competitors=competitors,
                min_competitors=3,
                max_competitors=15,
            ),
        )

    elif mode == AnalysisMode.HYBRID:
        # Discover competitors from SERP overlap (for curation)
        await start_hybrid_competitor_discovery(
            analysis_id=analysis_id,
            domain=domain_name,
            context=submission.business_context,
        )

        # Get discovered competitors for curation
        competitors = await get_competitor_candidates(analysis_id)

        return UnifiedAnalysisResponse(
            **base_response,
            status="awaiting_curation",
            message=f"Found {len(competitors)} competitors based on your SERP overlap. Review and curate the list.",
            next_action=NextAction(
                action="curate_competitors",
                competitors=competitors,
                min_competitors=3,
                max_competitors=10,
            ),
        )

    else:  # ESTABLISHED
        # Discover competitors from SERP overlap (for curation)
        await start_standard_competitor_discovery(
            analysis_id=analysis_id,
            domain=domain_name,
            context=submission.business_context,
        )

        # Get discovered competitors for curation
        competitors = await get_competitor_candidates(analysis_id)

        return UnifiedAnalysisResponse(
            **base_response,
            status="awaiting_curation",
            message=f"Found {len(competitors)} competitors. Review and curate - focus only on truly relevant competitors.",
            next_action=NextAction(
                action="curate_competitors",
                competitors=competitors,
                min_competitors=3,
                max_competitors=8,  # Standard needs fewer, more focused competitors
            ),
        )


@router.post("/analyze/{analysis_id}/curate")
async def submit_curation(
    analysis_id: UUID,
    submission: CurationSubmission,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> UnifiedAnalysisResponse:
    """
    Submit competitor curation decisions and start deep analysis.

    This is called after the user reviews competitor candidates.
    Handles ALL modes: greenfield, hybrid, and standard.

    The curation impact varies by mode:
    - GREENFIELD: Competitors are the primary source for keyword mining
    - HYBRID: Competitors help identify expansion opportunities
    - STANDARD: Competitors used for gap analysis, but less weight
    """
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Verify ownership
        domain = db.query(Domain).get(run.domain_id)
        if domain.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        domain_name = domain.domain
        mode = run.analysis_mode
        maturity_str = run.domain_maturity_at_analysis or "greenfield"

        # Store curation metrics for instrumentation
        run.curation_metrics = {
            "removals_count": len(submission.removals),
            "additions_count": len(submission.additions),
            "purpose_overrides_count": len(submission.purpose_overrides),
            "curated_at": datetime.utcnow().isoformat(),
            "mode": mode.value if mode else "greenfield",
        }
        db.commit()

    logger.info(f"[UNIFIED] Curation submitted for {analysis_id}, mode: {mode}")

    # Apply curation to competitor session
    await apply_curation(
        analysis_id=analysis_id,
        removals=submission.removals,
        additions=submission.additions,
        purpose_overrides=submission.purpose_overrides,
    )

    # Build base response
    base_response = {
        "analysis_id": analysis_id,
        "domain": domain_name,
        "detected_mode": maturity_str,
        "maturity": MaturityMetrics(
            domain_rating=run.domain_rating_at_analysis or 0,
            organic_keywords=run.organic_keywords_at_analysis or 0,
            organic_traffic=run.organic_traffic_at_analysis or 0,
            classification=maturity_str,
            explanation="",
        ),
        "context_endpoint": f"/api/v2/analyze/{analysis_id}/context",
        "curate_endpoint": f"/api/v2/analyze/{analysis_id}/curate",
        "status_endpoint": f"/api/v2/analyze/{analysis_id}/status",
        "dashboard_endpoint": f"/api/v2/dashboard/{analysis_id}",
    }

    # Start appropriate analysis based on mode
    if mode == AnalysisMode.GREENFIELD:
        background_tasks.add_task(
            run_greenfield_deep_analysis_background,
            analysis_id=analysis_id,
        )
        return UnifiedAnalysisResponse(
            **base_response,
            status="analyzing",
            message="Starting deep analysis. Mining keywords, analyzing SERPs, and building your roadmap.",
            next_action=NextAction(
                action="poll_status",
                poll_interval_seconds=5,
                progress=AnalysisProgress(
                    phase="Mining Keywords",
                    phase_number=1,
                    total_phases=5,
                    progress_percent=10,
                    message="Mining keywords from curated competitors...",
                    started_at=datetime.utcnow(),
                ),
            ),
        )

    elif mode == AnalysisMode.HYBRID:
        background_tasks.add_task(
            run_hybrid_analysis_background,
            analysis_id=analysis_id,
            context=BusinessContext(**run.greenfield_context) if run.greenfield_context else None,
        )
        return UnifiedAnalysisResponse(
            **base_response,
            status="analyzing",
            message="Starting hybrid analysis. Analyzing your existing rankings and finding growth opportunities.",
            next_action=NextAction(
                action="poll_status",
                poll_interval_seconds=5,
                progress=AnalysisProgress(
                    phase="Collecting Existing Data",
                    phase_number=1,
                    total_phases=6,
                    progress_percent=10,
                    message="Collecting your existing keyword rankings...",
                    started_at=datetime.utcnow(),
                ),
            ),
        )

    else:  # STANDARD
        background_tasks.add_task(
            run_standard_analysis_background,
            analysis_id=analysis_id,
            context=BusinessContext(**run.greenfield_context) if run.greenfield_context else None,
        )
        return UnifiedAnalysisResponse(
            **base_response,
            status="analyzing",
            message="Starting comprehensive analysis. Full SEO audit with competitor benchmarking.",
            next_action=NextAction(
                action="poll_status",
                poll_interval_seconds=30,
                progress=AnalysisProgress(
                    phase="Collecting Data",
                    phase_number=1,
                    total_phases=5,
                    progress_percent=5,
                    message="Starting comprehensive data collection...",
                    started_at=datetime.utcnow(),
                ),
            ),
        )


@router.get("/analyze/{analysis_id}/status")
async def get_analysis_status(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
) -> UnifiedAnalysisResponse:
    """
    Get current analysis status for polling.

    Returns progress information and next_action based on current state.
    """
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Verify ownership
        domain = db.query(Domain).get(run.domain_id)
        if domain.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        domain_name = domain.domain
        status = run.status
        mode = run.analysis_mode
        progress = run.progress_percent or 0
        phase = run.current_phase or "Processing"

    base_response = {
        "analysis_id": analysis_id,
        "domain": domain_name,
        "detected_mode": run.domain_maturity_at_analysis or "greenfield",
        "maturity": MaturityMetrics(
            domain_rating=run.domain_rating_at_analysis or 0,
            organic_keywords=run.organic_keywords_at_analysis or 0,
            organic_traffic=run.organic_traffic_at_analysis or 0,
            classification=run.domain_maturity_at_analysis or "greenfield",
            explanation="",
        ),
        "context_endpoint": f"/api/v2/analyze/{analysis_id}/context",
        "curate_endpoint": f"/api/v2/analyze/{analysis_id}/curate",
        "status_endpoint": f"/api/v2/analyze/{analysis_id}/status",
        "dashboard_endpoint": f"/api/v2/dashboard/{analysis_id}",
    }

    if status == AnalysisStatus.COMPLETED:
        return UnifiedAnalysisResponse(
            **base_response,
            status="completed",
            message="Analysis complete! View your dashboard.",
            next_action=NextAction(
                action="view_dashboard",
                dashboard_url=f"/api/v2/dashboard/{analysis_id}",
            ),
        )

    elif status == AnalysisStatus.FAILED:
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again or contact support."
        )

    else:
        # Still in progress
        phase_map = {
            "collecting": ("Collecting Data", 1, 5),
            "validating": ("Validating Data", 2, 5),
            "analyzing": ("Analyzing", 3, 5),
            "generating": ("Generating Results", 4, 5),
            "deep_analysis": ("Deep Analysis", 2, 5),
            "keyword_mining": ("Mining Keywords", 1, 5),
            "serp_analysis": ("Analyzing SERPs", 2, 5),
            "market_sizing": ("Sizing Market", 3, 5),
            "beachhead_selection": ("Selecting Beachheads", 4, 5),
        }

        phase_info = phase_map.get(phase.lower(), (phase, 1, 5))

        return UnifiedAnalysisResponse(
            **base_response,
            status="analyzing",
            message=f"{phase_info[0]}...",
            next_action=NextAction(
                action="poll_status",
                poll_interval_seconds=5,
                progress=AnalysisProgress(
                    phase=phase_info[0],
                    phase_number=phase_info[1],
                    total_phases=phase_info[2],
                    progress_percent=progress,
                    message=f"{phase_info[0]}...",
                    started_at=run.created_at,
                ),
            ),
        )


# =============================================================================
# BACKGROUND TASKS (Stubs - implement with actual logic)
# =============================================================================

async def start_competitor_discovery(
    analysis_id: UUID,
    domain: str,
    context: BusinessContext,
) -> None:
    """Start competitor discovery for greenfield analysis."""
    from src.services.greenfield import GreenfieldService

    greenfield_service = GreenfieldService()

    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)

        # Create competitor intelligence session
        session = CompetitorIntelligenceSession(
            analysis_run_id=analysis_id,
            domain_id=run.domain_id,
            status="discovering",
            user_provided_competitors=context.known_competitors,
        )
        db.add(session)
        db.commit()
        session_id = session.id

    # Run discovery
    try:
        await greenfield_service.discover_competitors(
            session_id=session_id,
            seed_keywords=context.seed_keywords,
            known_competitors=context.known_competitors,
            market=context.target_market,
            business_context={
                "business_name": context.company_name,
                "business_description": context.business_description,
                "primary_offering": context.primary_offering,
            },
        )
    except Exception as e:
        logger.error(f"Competitor discovery failed: {e}")


async def get_competitor_candidates(analysis_id: UUID) -> List[CompetitorCandidate]:
    """Get competitor candidates for curation."""
    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.analysis_run_id == analysis_id
        ).first()

        if not session or not session.candidate_competitors:
            return []

        return [
            CompetitorCandidate(
                domain=c.get("domain", ""),
                domain_rating=c.get("domain_rating", 0),
                organic_traffic=c.get("organic_traffic", 0),
                organic_keywords=c.get("organic_keywords", 0),
                discovery_source=c.get("discovery_source", "unknown"),
                relevance_score=c.get("relevance_score", 0),
                suggested_purpose=c.get("suggested_purpose", "keyword_source"),
                discovery_reason=c.get("discovery_reason", ""),
            )
            for c in session.candidate_competitors
        ]


async def start_hybrid_competitor_discovery(
    analysis_id: UUID,
    domain: str,
    context: BusinessContext,
) -> None:
    """
    Discover competitors for HYBRID mode analysis using SERP overlap.

    For emerging domains, we find competitors by:
    1. Getting domains that rank for similar keywords (SERP overlap)
    2. Adding any user-provided competitors
    3. Filtering out false competitors (aggregators, directories, etc.)
    """
    import os
    from src.collector.client import DataForSEOClient

    logger.info(f"[HYBRID] Starting competitor discovery for {domain}")

    dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
    dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)

        # Create competitor intelligence session
        session = CompetitorIntelligenceSession(
            analysis_run_id=analysis_id,
            domain_id=run.domain_id,
            status="discovering",
            user_provided_competitors=context.known_competitors if context else [],
        )
        db.add(session)
        db.commit()
        session_id = session.id

    candidates = []

    try:
        if dataforseo_login and dataforseo_password:
            async with DataForSEOClient(
                login=dataforseo_login,
                password=dataforseo_password
            ) as client:
                # Get competitors from SERP overlap
                serp_competitors = await client.get_domain_competitors(
                    domain=domain,
                    limit=15,
                )

                for comp in (serp_competitors or []):
                    comp_domain = comp.get("domain", "")
                    if comp_domain and not _is_false_competitor(comp_domain):
                        candidates.append({
                            "domain": comp_domain,
                            "domain_rating": comp.get("domain_rating", 0),
                            "organic_traffic": comp.get("organic_traffic", 0),
                            "organic_keywords": comp.get("organic_keywords", 0),
                            "discovery_source": "serp_overlap",
                            "relevance_score": comp.get("common_keywords", 0) / 100,
                            "suggested_purpose": "gap_analysis",
                            "discovery_reason": f"Ranks for {comp.get('common_keywords', 0)} keywords you're targeting",
                        })

        # Add user-provided competitors
        if context and context.known_competitors:
            for user_comp in context.known_competitors:
                if user_comp and not any(c["domain"] == user_comp for c in candidates):
                    candidates.append({
                        "domain": user_comp,
                        "domain_rating": 0,
                        "organic_traffic": 0,
                        "organic_keywords": 0,
                        "discovery_source": "user_provided",
                        "relevance_score": 1.0,
                        "suggested_purpose": "benchmark",
                        "discovery_reason": "You identified this as a competitor",
                    })

        # Sort by relevance
        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Update session with candidates
        with get_db_context() as db:
            session = db.query(CompetitorIntelligenceSession).get(session_id)
            session.candidate_competitors = candidates[:15]
            session.status = "awaiting_curation"
            db.commit()

        logger.info(f"[HYBRID] Found {len(candidates)} competitors for curation")

    except Exception as e:
        logger.error(f"[HYBRID] Competitor discovery failed: {e}")
        # Still allow curation with user-provided competitors
        if context and context.known_competitors:
            with get_db_context() as db:
                session = db.query(CompetitorIntelligenceSession).get(session_id)
                session.candidate_competitors = [
                    {
                        "domain": c,
                        "domain_rating": 0,
                        "organic_traffic": 0,
                        "organic_keywords": 0,
                        "discovery_source": "user_provided",
                        "relevance_score": 1.0,
                        "suggested_purpose": "benchmark",
                        "discovery_reason": "You identified this as a competitor",
                    }
                    for c in context.known_competitors
                ]
                session.status = "awaiting_curation"
                db.commit()


async def start_standard_competitor_discovery(
    analysis_id: UUID,
    domain: str,
    context: BusinessContext,
) -> None:
    """
    Discover competitors for STANDARD mode analysis.

    For established domains, we find competitors by:
    1. Traffic share analysis (who competes for our traffic)
    2. SERP overlap analysis (who ranks for our keywords)
    3. Filtering for true competitors (similar DR, not aggregators)
    """
    import os
    from src.collector.client import DataForSEOClient

    logger.info(f"[STANDARD] Starting competitor discovery for {domain}")

    dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
    dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)
        our_dr = run.domain_rating_at_analysis or 0

        # Create competitor intelligence session
        session = CompetitorIntelligenceSession(
            analysis_run_id=analysis_id,
            domain_id=run.domain_id,
            status="discovering",
            user_provided_competitors=context.known_competitors if context else [],
        )
        db.add(session)
        db.commit()
        session_id = session.id

    candidates = []

    try:
        if dataforseo_login and dataforseo_password:
            async with DataForSEOClient(
                login=dataforseo_login,
                password=dataforseo_password
            ) as client:
                # Get competitors from SERP overlap
                serp_competitors = await client.get_domain_competitors(
                    domain=domain,
                    limit=20,
                )

                for comp in (serp_competitors or []):
                    comp_domain = comp.get("domain", "")
                    comp_dr = comp.get("domain_rating", 0)

                    if not comp_domain or _is_false_competitor(comp_domain):
                        continue

                    # For standard mode, prefer competitors within 20 DR points
                    dr_diff = abs(comp_dr - our_dr)
                    is_tier_match = dr_diff <= 20

                    candidates.append({
                        "domain": comp_domain,
                        "domain_rating": comp_dr,
                        "organic_traffic": comp.get("organic_traffic", 0),
                        "organic_keywords": comp.get("organic_keywords", 0),
                        "discovery_source": "serp_overlap",
                        "relevance_score": 1.0 if is_tier_match else 0.5,
                        "suggested_purpose": "true_competitor" if is_tier_match else "aspiration",
                        "discovery_reason": (
                            f"Similar authority (DR {comp_dr}) with {comp.get('common_keywords', 0)} keyword overlap"
                            if is_tier_match
                            else f"Higher authority target (DR {comp_dr})"
                        ),
                    })

        # Add user-provided competitors
        if context and context.known_competitors:
            for user_comp in context.known_competitors:
                if user_comp and not any(c["domain"] == user_comp for c in candidates):
                    candidates.append({
                        "domain": user_comp,
                        "domain_rating": 0,
                        "organic_traffic": 0,
                        "organic_keywords": 0,
                        "discovery_source": "user_provided",
                        "relevance_score": 1.0,
                        "suggested_purpose": "business_competitor",
                        "discovery_reason": "You identified this as a competitor",
                    })

        # Sort by relevance, then by overlap
        candidates.sort(key=lambda x: (x["relevance_score"], x.get("organic_keywords", 0)), reverse=True)

        # Update session with candidates
        with get_db_context() as db:
            session = db.query(CompetitorIntelligenceSession).get(session_id)
            session.candidate_competitors = candidates[:12]  # Fewer for standard
            session.status = "awaiting_curation"
            db.commit()

        logger.info(f"[STANDARD] Found {len(candidates)} competitors for curation")

    except Exception as e:
        logger.error(f"[STANDARD] Competitor discovery failed: {e}")
        if context and context.known_competitors:
            with get_db_context() as db:
                session = db.query(CompetitorIntelligenceSession).get(session_id)
                session.candidate_competitors = [
                    {
                        "domain": c,
                        "domain_rating": 0,
                        "organic_traffic": 0,
                        "organic_keywords": 0,
                        "discovery_source": "user_provided",
                        "relevance_score": 1.0,
                        "suggested_purpose": "business_competitor",
                        "discovery_reason": "You identified this as a competitor",
                    }
                    for c in context.known_competitors
                ]
                session.status = "awaiting_curation"
                db.commit()


def _is_false_competitor(domain: str) -> bool:
    """
    Check if a domain is a false competitor (aggregator, directory, etc.).

    This is a simple exclusion list - can be expanded based on instrumentation data.
    """
    # Common false competitor patterns
    false_competitor_domains = {
        # Review/aggregator sites
        "g2.com", "capterra.com", "trustradius.com", "getapp.com",
        "softwareadvice.com", "trustpilot.com", "yelp.com",
        # Directories
        "linkedin.com", "crunchbase.com", "glassdoor.com", "indeed.com",
        "yellowpages.com", "bbb.org",
        # News/media
        "forbes.com", "techcrunch.com", "bloomberg.com", "reuters.com",
        "wsj.com", "nytimes.com", "cnn.com",
        # Social/platforms
        "facebook.com", "twitter.com", "instagram.com", "youtube.com",
        "reddit.com", "quora.com", "medium.com",
        # Generic resources
        "wikipedia.org", "wikihow.com", "investopedia.com",
        # E-commerce giants
        "amazon.com", "ebay.com", "walmart.com", "target.com",
        # Government/edu
        "gov", ".edu",
    }

    domain_lower = domain.lower()

    # Check exact matches
    if domain_lower in false_competitor_domains:
        return True

    # Check if domain ends with any pattern
    for pattern in false_competitor_domains:
        if pattern.startswith(".") and domain_lower.endswith(pattern):
            return True

    return False


async def apply_curation(
    analysis_id: UUID,
    removals: List[str],
    additions: List[str],
    purpose_overrides: Dict[str, str],
) -> None:
    """Apply curation decisions to competitor session."""
    from src.services.greenfield import GreenfieldService

    greenfield_service = GreenfieldService()

    with get_db_context() as db:
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.analysis_run_id == analysis_id
        ).first()

        if session:
            greenfield_service.submit_curation(
                session_id=session.id,
                removals=[{"domain": d, "reason": "user_removed"} for d in removals],
                additions=[{"domain": d} for d in additions],
                purpose_overrides=[
                    {"domain": d, "new_purpose": p}
                    for d, p in purpose_overrides.items()
                ],
            )


async def run_greenfield_deep_analysis_background(analysis_id: UUID) -> None:
    """Run greenfield deep analysis (G2-G5) in background."""
    # This calls the existing greenfield deep analysis logic
    from api.greenfield import run_deep_analysis_background

    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)
        session = db.query(CompetitorIntelligenceSession).filter(
            CompetitorIntelligenceSession.analysis_run_id == analysis_id
        ).first()
        domain = db.query(Domain).get(run.domain_id)

        if run and session and domain:
            await run_deep_analysis_background(
                session_id=session.id,
                analysis_run_id=analysis_id,
                domain_id=run.domain_id,
                domain=domain.domain,
                final_competitors=session.final_competitors or [],
                greenfield_context=run.greenfield_context or {},
                market=run.greenfield_context.get("target_market", "United States") if run.greenfield_context else "United States",
            )


async def run_hybrid_analysis_background(
    analysis_id: UUID,
    context: BusinessContext,
) -> None:
    """
    Run hybrid analysis in background.

    HYBRID combines:
    1. Domain's existing (limited) data from DataForSEO
    2. Competitor discovery from SERP overlap
    3. Gap analysis within existing topic clusters (consolidation)
    4. Gap analysis for adjacent clusters (expansion)
    5. Beachhead selection for quick wins

    This is for "emerging" domains that have some data but need strategic growth.
    """
    import os
    from src.collector.client import DataForSEOClient
    from src.database.models import KeywordGap

    logger.info(f"[HYBRID] Starting hybrid analysis for {analysis_id}")

    try:
        # Phase 1: Initialize
        with get_db_context() as db:
            run = db.query(AnalysisRun).get(analysis_id)
            domain = db.query(Domain).get(run.domain_id)
            domain_name = domain.domain
            run.status = AnalysisStatus.ANALYZING
            run.current_phase = "collecting"
            run.progress_percent = 10
            db.commit()

        logger.info(f"[HYBRID] Phase 1: Collecting existing data for {domain_name}")

        # Get DataForSEO credentials
        dataforseo_login = os.environ.get("DATAFORSEO_LOGIN")
        dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD")

        if not dataforseo_login or not dataforseo_password:
            raise ValueError("DataForSEO credentials not configured")

        async with DataForSEOClient(
            login=dataforseo_login,
            password=dataforseo_password
        ) as client:
            # Phase 2: Collect existing ranked keywords
            with get_db_context() as db:
                run = db.query(AnalysisRun).get(analysis_id)
                run.current_phase = "collecting_keywords"
                run.progress_percent = 20
                db.commit()

            logger.info(f"[HYBRID] Phase 2: Getting ranked keywords for {domain_name}")

            # Get domain's existing keywords
            ranked_keywords = await client.get_domain_ranked_keywords(
                domain=domain_name,
                limit=500,  # Limited for hybrid
            )

            # Store keywords
            with get_db_context() as db:
                domain_obj = db.query(Domain).filter(Domain.domain == domain_name).first()

                for kw_data in (ranked_keywords or []):
                    keyword = Keyword(
                        domain_id=domain_obj.id,
                        analysis_run_id=analysis_id,
                        keyword=kw_data.get("keyword", ""),
                        keyword_normalized=kw_data.get("keyword", "").lower().strip(),
                        search_volume=kw_data.get("search_volume", 0),
                        keyword_difficulty=kw_data.get("keyword_difficulty", 0),
                        current_position=kw_data.get("position", None),
                        estimated_traffic=kw_data.get("etv", 0),
                    )
                    db.add(keyword)

                run = db.query(AnalysisRun).get(analysis_id)
                run.current_phase = "discovering_competitors"
                run.progress_percent = 35
                db.commit()

            logger.info(f"[HYBRID] Stored {len(ranked_keywords or [])} existing keywords")

            # Phase 3: Discover competitors from SERP overlap
            logger.info(f"[HYBRID] Phase 3: Discovering competitors for {domain_name}")

            competitors_data = await client.get_domain_competitors(
                domain=domain_name,
                limit=10,
            )

            # Store competitors
            with get_db_context() as db:
                from src.database.models import Competitor, CompetitorType

                for comp_data in (competitors_data or []):
                    competitor = Competitor(
                        analysis_run_id=analysis_id,
                        competitor_domain=comp_data.get("domain", ""),
                        competitor_type=CompetitorType.SEO_COMPETITOR,
                        organic_traffic=comp_data.get("organic_traffic", 0),
                        organic_keywords=comp_data.get("organic_keywords", 0),
                        overlap_keywords=comp_data.get("common_keywords", 0),
                        domain_rating=comp_data.get("domain_rating", 0),
                        is_active=True,
                    )
                    db.add(competitor)

                run = db.query(AnalysisRun).get(analysis_id)
                run.current_phase = "analyzing_gaps"
                run.progress_percent = 50
                db.commit()

            logger.info(f"[HYBRID] Found {len(competitors_data or [])} competitors")

            # Phase 4: Analyze gaps (keywords competitors rank for, we don't)
            logger.info(f"[HYBRID] Phase 4: Analyzing keyword gaps")

            # Get gaps from top competitors
            all_gaps = []
            for comp_data in (competitors_data or [])[:5]:  # Top 5 competitors
                comp_domain = comp_data.get("domain", "")
                if comp_domain:
                    gaps = await client.get_keyword_gaps(
                        target_domain=domain_name,
                        competitor_domains=[comp_domain],
                        limit=100,
                    )
                    for gap in (gaps or []):
                        gap["best_competitor"] = comp_domain
                    all_gaps.extend(gaps or [])

            # Deduplicate and store gaps
            seen_keywords = set()
            with get_db_context() as db:
                for gap_data in all_gaps:
                    kw = gap_data.get("keyword", "").lower().strip()
                    if kw and kw not in seen_keywords:
                        seen_keywords.add(kw)

                        keyword_gap = KeywordGap(
                            analysis_run_id=analysis_id,
                            keyword=gap_data.get("keyword", ""),
                            search_volume=gap_data.get("search_volume", 0),
                            keyword_difficulty=gap_data.get("keyword_difficulty", 0),
                            best_competitor=gap_data.get("best_competitor", ""),
                            best_competitor_position=gap_data.get("competitor_position", 0),
                            target_position=None,  # We don't rank
                            opportunity_score=_calculate_gap_opportunity_score(gap_data),
                        )
                        db.add(keyword_gap)

                run = db.query(AnalysisRun).get(analysis_id)
                run.current_phase = "selecting_beachheads"
                run.progress_percent = 70
                db.commit()

            logger.info(f"[HYBRID] Stored {len(seen_keywords)} unique keyword gaps")

            # Phase 5: Select beachheads (quick wins)
            logger.info(f"[HYBRID] Phase 5: Selecting beachhead keywords")

            with get_db_context() as db:
                # Mark existing keywords in striking distance as beachheads
                striking_distance = db.query(Keyword).filter(
                    Keyword.analysis_run_id == analysis_id,
                    Keyword.current_position != None,
                    Keyword.current_position.between(11, 30),  # Page 2-3
                ).order_by(Keyword.estimated_traffic.desc()).limit(20).all()

                for i, kw in enumerate(striking_distance):
                    kw.is_beachhead = True
                    kw.beachhead_priority = i + 1
                    kw.winnability_score = _calculate_winnability_existing(kw)
                    kw.growth_phase = 1  # Quick wins = Phase 1

                # Mark low-difficulty gaps as expansion beachheads
                expansion_beachheads = db.query(KeywordGap).filter(
                    KeywordGap.analysis_run_id == analysis_id,
                    KeywordGap.keyword_difficulty < 40,
                    KeywordGap.search_volume >= 100,
                ).order_by(KeywordGap.opportunity_score.desc()).limit(15).all()

                # Convert to Keywords and mark as beachheads
                domain_obj = db.query(Domain).filter(Domain.domain == domain_name).first()
                for i, gap in enumerate(expansion_beachheads):
                    # Check if keyword already exists
                    existing = db.query(Keyword).filter(
                        Keyword.analysis_run_id == analysis_id,
                        Keyword.keyword_normalized == gap.keyword.lower().strip(),
                    ).first()

                    if not existing:
                        keyword = Keyword(
                            domain_id=domain_obj.id,
                            analysis_run_id=analysis_id,
                            keyword=gap.keyword,
                            keyword_normalized=gap.keyword.lower().strip(),
                            search_volume=gap.search_volume,
                            keyword_difficulty=gap.keyword_difficulty,
                            current_position=None,  # We don't rank
                            is_beachhead=True,
                            beachhead_priority=20 + i + 1,  # After consolidation
                            winnability_score=_calculate_winnability_gap(gap),
                            growth_phase=2,  # Expansion = Phase 2
                        )
                        db.add(keyword)

                run = db.query(AnalysisRun).get(analysis_id)
                run.current_phase = "finalizing"
                run.progress_percent = 90
                db.commit()

            logger.info(f"[HYBRID] Selected {len(striking_distance)} consolidation and {len(expansion_beachheads)} expansion beachheads")

        # Phase 6: Complete
        with get_db_context() as db:
            run = db.query(AnalysisRun).get(analysis_id)
            run.status = AnalysisStatus.COMPLETED
            run.current_phase = "completed"
            run.progress_percent = 100
            run.completed_at = datetime.utcnow()
            db.commit()

        logger.info(f"[HYBRID] Analysis completed for {analysis_id}")

    except Exception as e:
        logger.error(f"[HYBRID] Analysis failed for {analysis_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        with get_db_context() as db:
            run = db.query(AnalysisRun).get(analysis_id)
            run.status = AnalysisStatus.FAILED
            run.error_message = str(e)
            db.commit()


def _calculate_gap_opportunity_score(gap_data: dict) -> float:
    """Calculate opportunity score for a keyword gap."""
    volume = gap_data.get("search_volume", 0)
    difficulty = gap_data.get("keyword_difficulty", 50)
    comp_position = gap_data.get("competitor_position", 10)

    # Higher volume = better
    volume_score = min(100, (volume / 1000) * 50) if volume else 0

    # Lower difficulty = better
    difficulty_score = max(0, 100 - difficulty)

    # Competitor in top 5 = high opportunity
    position_score = 100 if comp_position <= 5 else (50 if comp_position <= 10 else 25)

    return (volume_score * 0.4 + difficulty_score * 0.4 + position_score * 0.2)


def _calculate_winnability_existing(keyword: Keyword) -> float:
    """Calculate winnability for an existing ranked keyword."""
    position = keyword.current_position or 100
    difficulty = keyword.keyword_difficulty or 50

    # Already on page 2-3 = high winnability
    position_score = 100 if position <= 15 else (75 if position <= 20 else 50)

    # Lower difficulty = higher winnability
    difficulty_score = max(0, 100 - difficulty)

    return (position_score * 0.6 + difficulty_score * 0.4)


def _calculate_winnability_gap(gap) -> float:
    """Calculate winnability for a keyword gap."""
    difficulty = gap.keyword_difficulty or 50
    volume = gap.search_volume or 0

    # Low difficulty = high winnability
    difficulty_score = max(0, 100 - difficulty)

    # Minimum volume threshold met = viable
    volume_score = 50 if volume >= 100 else 25

    return (difficulty_score * 0.7 + volume_score * 0.3)


# =============================================================================
# UNIFIED DASHBOARD ENDPOINT
# =============================================================================

@router.get("/dashboard/{analysis_id}")
async def get_unified_dashboard(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Unified dashboard endpoint that returns mode-appropriate data.

    This endpoint detects the analysis mode and returns:
    - GREENFIELD: Beachheads, market map, roadmap, competitors
    - HYBRID: Quick wins, existing strengths, expansion opportunities
    - ESTABLISHED: Full SEO dashboard with SoV, battleground, clusters

    The frontend can render a single dashboard component that adapts
    based on the returned mode field.
    """
    with get_db_context() as db:
        run = db.query(AnalysisRun).get(analysis_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Verify ownership
        domain = db.query(Domain).get(run.domain_id)
        if domain.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        mode = run.analysis_mode
        domain_name = domain.domain
        domain_id = domain.id
        status = run.status

        if status != AnalysisStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Analysis not complete. Current status: {status.value}"
            )

        # Base response
        response = {
            "analysis_id": str(analysis_id),
            "domain": domain_name,
            "mode": mode.value if mode else "standard",
            "status": status.value,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "maturity": {
                "domain_rating": run.domain_rating_at_analysis or 0,
                "organic_keywords": run.organic_keywords_at_analysis or 0,
                "organic_traffic": run.organic_traffic_at_analysis or 0,
                "classification": run.domain_maturity_at_analysis or "unknown",
            },
        }

        if mode == AnalysisMode.GREENFIELD:
            response["dashboard"] = await _get_greenfield_dashboard_data(db, run, domain)

        elif mode == AnalysisMode.HYBRID:
            response["dashboard"] = await _get_hybrid_dashboard_data(db, run, domain)

        else:  # STANDARD
            response["dashboard"] = await _get_standard_dashboard_data(db, run, domain)

        return response


async def _get_greenfield_dashboard_data(db, run: AnalysisRun, domain: Domain) -> Dict[str, Any]:
    """Get greenfield-specific dashboard data."""
    from sqlalchemy import func

    # Get greenfield analysis
    gf_analysis = db.query(GreenfieldAnalysis).filter(
        GreenfieldAnalysis.analysis_run_id == run.id
    ).first()

    # Get competitor session
    ci_session = db.query(CompetitorIntelligenceSession).filter(
        CompetitorIntelligenceSession.analysis_run_id == run.id
    ).first()

    # Get beachhead keywords
    beachheads = db.query(Keyword).filter(
        Keyword.analysis_run_id == run.id,
        Keyword.is_beachhead == True
    ).order_by(Keyword.beachhead_priority.asc()).limit(50).all()

    # Get competitors
    competitors = []
    if ci_session:
        from src.database.models import GreenfieldCompetitor
        greenfield_comps = db.query(GreenfieldCompetitor).filter(
            GreenfieldCompetitor.session_id == ci_session.id
        ).order_by(GreenfieldCompetitor.priority.asc()).all()

        competitors = [
            {
                "domain": comp.domain,
                "display_name": comp.display_name,
                "purpose": comp.purpose.value if comp.purpose else "keyword_source",
                "domain_rating": comp.domain_rating or 0,
                "organic_traffic": comp.organic_traffic or 0,
            }
            for comp in greenfield_comps
        ]

    # Get roadmap phases
    phase_data = db.query(
        Keyword.growth_phase,
        func.count(Keyword.id).label("keyword_count"),
        func.sum(Keyword.search_volume).label("total_volume"),
    ).filter(
        Keyword.analysis_run_id == run.id,
        Keyword.is_beachhead == True,
        Keyword.growth_phase != None
    ).group_by(Keyword.growth_phase).all()

    roadmap = []
    phase_info = {
        1: {"name": "Foundation", "months": "1-3"},
        2: {"name": "Traction", "months": "4-6"},
        3: {"name": "Authority", "months": "7-12"},
    }
    for phase in phase_data:
        phase_num = phase.growth_phase or 1
        info = phase_info.get(phase_num, phase_info[1])
        roadmap.append({
            "phase": info["name"],
            "phase_number": phase_num,
            "months": info["months"],
            "keyword_count": phase.keyword_count or 0,
            "total_volume": phase.total_volume or 0,
        })
    roadmap.sort(key=lambda x: x["phase_number"])

    return {
        "type": "greenfield",
        "market_opportunity": {
            "tam_volume": gf_analysis.tam_volume if gf_analysis else 0,
            "sam_volume": gf_analysis.sam_volume if gf_analysis else 0,
            "som_volume": gf_analysis.som_volume if gf_analysis else 0,
            "market_opportunity_score": gf_analysis.market_opportunity_score if gf_analysis else 0,
        },
        "beachheads": [
            {
                "keyword": kw.keyword,
                "search_volume": kw.search_volume or 0,
                "winnability_score": kw.winnability_score or 0,
                "personalized_difficulty": kw.personalized_difficulty or 0,
                "growth_phase": kw.growth_phase or 1,
            }
            for kw in beachheads
        ],
        "beachhead_summary": {
            "count": len(beachheads),
            "total_volume": sum(kw.search_volume or 0 for kw in beachheads),
            "avg_winnability": (
                sum(kw.winnability_score or 0 for kw in beachheads) / len(beachheads)
                if beachheads else 0
            ),
        },
        "competitors": competitors,
        "roadmap": roadmap,
    }


async def _get_hybrid_dashboard_data(db, run: AnalysisRun, domain: Domain) -> Dict[str, Any]:
    """
    Get hybrid-mode dashboard data.

    HYBRID mode combines:
    - Domain's existing ranked keywords (consolidation opportunities)
    - Competitor gap analysis (expansion opportunities)
    - Beachhead selection from both
    """
    from sqlalchemy import func

    # Get existing ranked keywords (quick wins in current clusters)
    existing_keywords = db.query(Keyword).filter(
        Keyword.analysis_run_id == run.id,
        Keyword.current_position != None,
        Keyword.current_position <= 50,
    ).order_by(Keyword.opportunity_score.desc()).limit(30).all()

    # Group by clusters if available
    consolidation_opportunities = []
    for kw in existing_keywords:
        if kw.current_position and kw.current_position > 10:
            consolidation_opportunities.append({
                "keyword": kw.keyword,
                "current_position": kw.current_position,
                "search_volume": kw.search_volume or 0,
                "opportunity_score": kw.opportunity_score or 0,
                "action": "optimize" if kw.current_position <= 20 else "create_supporting",
            })

    # Get expansion opportunities (gaps)
    from src.database.models import KeywordGap
    expansion_keywords = db.query(KeywordGap).filter(
        KeywordGap.analysis_run_id == run.id,
        KeywordGap.target_position == None,
        KeywordGap.search_volume >= 100,
    ).order_by(KeywordGap.opportunity_score.desc()).limit(20).all()

    expansion_opportunities = [
        {
            "keyword": gap.keyword,
            "search_volume": gap.search_volume or 0,
            "keyword_difficulty": gap.keyword_difficulty or 0,
            "best_competitor": gap.best_competitor,
            "opportunity_score": gap.opportunity_score or 0,
        }
        for gap in expansion_keywords
    ]

    # Summary stats
    total_existing = db.query(func.count(Keyword.id)).filter(
        Keyword.analysis_run_id == run.id,
        Keyword.current_position != None,
    ).scalar() or 0

    total_gaps = db.query(func.count(KeywordGap.id)).filter(
        KeywordGap.analysis_run_id == run.id,
    ).scalar() or 0

    return {
        "type": "hybrid",
        "summary": {
            "existing_rankings": total_existing,
            "content_gaps": total_gaps,
            "consolidation_count": len(consolidation_opportunities),
            "expansion_count": len(expansion_opportunities),
        },
        "consolidation_opportunities": consolidation_opportunities[:15],
        "expansion_opportunities": expansion_opportunities[:15],
        "recommended_strategy": (
            "Focus on consolidation first - strengthen your existing rankings "
            "before pursuing new topics. This builds authority faster."
            if total_existing > total_gaps
            else "Mix of consolidation and expansion - you have room to grow in "
            "both existing and new topic areas."
        ),
    }


async def _get_standard_dashboard_data(db, run: AnalysisRun, domain: Domain) -> Dict[str, Any]:
    """Get standard (established domain) dashboard data."""
    from sqlalchemy import func
    from src.database.models import (
        DomainMetricsHistory, ContentCluster, KeywordGap,
        Competitor, CompetitorType
    )

    # Get latest metrics
    metrics = db.query(DomainMetricsHistory).filter(
        DomainMetricsHistory.analysis_run_id == run.id
    ).first()

    # Get keyword stats
    keyword_stats = db.query(
        func.count(Keyword.id).label("total"),
        func.sum(Keyword.estimated_traffic).label("total_traffic"),
    ).filter(
        Keyword.analysis_run_id == run.id,
    ).first()

    # Get position distribution
    position_dist = db.query(
        func.sum(func.cast(Keyword.current_position <= 3, db.bind.dialect.name == 'postgresql' and 'INTEGER' or 'INT')).label("top_3"),
        func.sum(func.cast(Keyword.current_position.between(4, 10), db.bind.dialect.name == 'postgresql' and 'INTEGER' or 'INT')).label("p4_10"),
        func.sum(func.cast(Keyword.current_position.between(11, 20), db.bind.dialect.name == 'postgresql' and 'INTEGER' or 'INT')).label("p11_20"),
    ).filter(
        Keyword.analysis_run_id == run.id,
        Keyword.current_position != None,
    ).first()

    # Get top competitors
    competitors = db.query(Competitor).filter(
        Competitor.analysis_run_id == run.id,
        Competitor.competitor_type == CompetitorType.TRUE_COMPETITOR,
    ).order_by(Competitor.organic_traffic.desc()).limit(5).all()

    # Get content clusters
    clusters = db.query(ContentCluster).filter(
        ContentCluster.analysis_run_id == run.id
    ).order_by(ContentCluster.topical_authority_score.desc()).limit(10).all()

    # Get quick wins
    quick_wins = db.query(Keyword).filter(
        Keyword.analysis_run_id == run.id,
        Keyword.opportunity_score >= 70,
        Keyword.current_position.between(11, 30)
    ).order_by(Keyword.opportunity_score.desc()).limit(10).all()

    return {
        "type": "standard",
        "overview": {
            "organic_traffic": metrics.organic_traffic if metrics else 0,
            "organic_keywords": metrics.organic_keywords if metrics else 0,
            "domain_rating": metrics.domain_rating if metrics else 0,
            "referring_domains": metrics.referring_domains if metrics else 0,
        },
        "position_distribution": {
            "top_3": position_dist.top_3 or 0 if position_dist else 0,
            "4_10": position_dist.p4_10 or 0 if position_dist else 0,
            "11_20": position_dist.p11_20 or 0 if position_dist else 0,
        },
        "competitors": [
            {
                "domain": c.competitor_domain,
                "organic_traffic": c.organic_traffic or 0,
                "overlap_keywords": c.overlap_keywords or 0,
            }
            for c in competitors
        ],
        "clusters": [
            {
                "name": c.cluster_name,
                "authority_score": c.topical_authority_score or 0,
                "keyword_count": c.total_keywords or 0,
            }
            for c in clusters
        ],
        "quick_wins": [
            {
                "keyword": kw.keyword,
                "current_position": kw.current_position,
                "search_volume": kw.search_volume or 0,
                "opportunity_score": kw.opportunity_score or 0,
            }
            for kw in quick_wins
        ],
    }


async def run_standard_analysis_background(
    analysis_id: UUID,
    context: BusinessContext,
) -> None:
    """
    Run standard (established domain) analysis in background.

    This calls the existing standard analysis pipeline.
    """
    # TODO: Integrate with existing /api/analyze logic
    # For now, this is a placeholder

    logger.info(f"[STANDARD] Starting standard analysis for {analysis_id}")

    try:
        with get_db_context() as db:
            run = db.query(AnalysisRun).get(analysis_id)
            run.status = AnalysisStatus.ANALYZING
            run.current_phase = "collecting"
            db.commit()

        # TODO: Call existing standard analysis pipeline
        logger.warning(f"[STANDARD] Standard mode needs integration with existing pipeline for {analysis_id}")

        # Mark as completed for now
        with get_db_context() as db:
            run = db.query(AnalysisRun).get(analysis_id)
            run.status = AnalysisStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        logger.error(f"[STANDARD] Analysis failed for {analysis_id}: {e}")
        with get_db_context() as db:
            run = db.query(AnalysisRun).get(analysis_id)
            run.status = AnalysisStatus.FAILED
            db.commit()

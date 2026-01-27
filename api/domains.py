"""
API Endpoints for Domain Management

Handles:
1. List user's domains
2. Get single domain details
3. Create domain (manual, without analysis)
4. Update domain settings
5. Delete domain
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.database.models import Domain, AnalysisRun, AnalysisStatus
from src.database.session import get_db_context
from src.auth.dependencies import get_current_user
from src.auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/domains",
    tags=["Domains"],
    dependencies=[Depends(get_current_user)],
)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class DomainResponse(BaseModel):
    """Single domain response."""
    id: str
    domain: str
    display_name: Optional[str] = None
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_market: Optional[str] = None
    primary_language: Optional[str] = None
    brand_name: Optional[str] = None
    business_description: Optional[str] = None
    is_active: bool
    analysis_count: int
    first_analyzed_at: Optional[datetime] = None
    last_analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Latest analysis info
    latest_analysis_id: Optional[str] = None
    latest_analysis_status: Optional[str] = None

    class Config:
        from_attributes = True


class DomainListResponse(BaseModel):
    """List of domains response."""
    domains: List[DomainResponse]
    total: int


class CreateDomainRequest(BaseModel):
    """Request to create a domain manually."""
    domain: str = Field(..., min_length=3, max_length=255)
    display_name: Optional[str] = None
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_market: Optional[str] = None
    primary_language: Optional[str] = None
    brand_name: Optional[str] = None
    business_description: Optional[str] = None


class UpdateDomainRequest(BaseModel):
    """Request to update domain settings."""
    display_name: Optional[str] = None
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_market: Optional[str] = None
    primary_language: Optional[str] = None
    brand_name: Optional[str] = None
    business_description: Optional[str] = None
    is_active: Optional[bool] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_domain_access(domain: Domain, user: User) -> None:
    """Check if user has access to a domain."""
    if user.is_admin:
        return
    if domain.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this domain"
        )


def domain_to_response(domain: Domain, latest_run: Optional[AnalysisRun] = None) -> DomainResponse:
    """Convert Domain model to response."""
    return DomainResponse(
        id=str(domain.id),
        domain=domain.domain,
        display_name=domain.display_name,
        industry=domain.industry,
        business_type=domain.business_type,
        target_market=domain.target_market,
        primary_language=domain.primary_language,
        brand_name=domain.brand_name,
        business_description=domain.business_description,
        is_active=domain.is_active,
        analysis_count=domain.analysis_count or 0,
        first_analyzed_at=domain.first_analyzed_at,
        last_analyzed_at=domain.last_analyzed_at,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        latest_analysis_id=str(latest_run.id) if latest_run else None,
        latest_analysis_status=latest_run.status.value if latest_run else None,
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=DomainListResponse)
async def list_domains(
    current_user: User = Depends(get_current_user),
    include_inactive: bool = Query(False, description="Include inactive domains"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List all domains for the current user.

    Admins can see all domains. Regular users only see their own.

    Returns domains sorted by last_analyzed_at (most recent first),
    with analysis count and latest analysis status.
    """
    with get_db_context() as db:
        # Base query
        query = db.query(Domain)

        # Filter by user unless admin
        if not current_user.is_admin:
            query = query.filter(Domain.user_id == current_user.id)

        # Filter inactive
        if not include_inactive:
            query = query.filter(Domain.is_active == True)

        # Get total count
        total = query.count()

        # Order by last analyzed (most recent first), then created_at
        query = query.order_by(
            Domain.last_analyzed_at.desc().nullsfirst(),
            Domain.created_at.desc()
        )

        # Pagination
        domains = query.offset(offset).limit(limit).all()

        # Get latest analysis for each domain
        domain_responses = []
        for domain in domains:
            latest_run = db.query(AnalysisRun).filter(
                AnalysisRun.domain_id == domain.id
            ).order_by(AnalysisRun.created_at.desc()).first()

            domain_responses.append(domain_to_response(domain, latest_run))

        return DomainListResponse(
            domains=domain_responses,
            total=total
        )


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get a single domain by ID.

    Includes latest analysis information.
    """
    with get_db_context() as db:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()

        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        check_domain_access(domain, current_user)

        # Get latest analysis
        latest_run = db.query(AnalysisRun).filter(
            AnalysisRun.domain_id == domain.id
        ).order_by(AnalysisRun.created_at.desc()).first()

        return domain_to_response(domain, latest_run)


@router.post("", response_model=DomainResponse, status_code=201)
async def create_domain(
    request: CreateDomainRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a domain manually (without triggering analysis).

    Useful for pre-registering domains before analysis.
    The domain is normalized (lowercase, no protocol/www).
    """
    # Normalize domain
    normalized = request.domain.lower().strip()
    normalized = normalized.replace("https://", "").replace("http://", "")
    normalized = normalized.replace("www.", "").rstrip("/")

    with get_db_context() as db:
        # Check if domain already exists for this user
        existing = db.query(Domain).filter(
            Domain.user_id == current_user.id,
            Domain.domain == normalized
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Domain '{normalized}' already exists"
            )

        # Create domain
        domain = Domain(
            user_id=current_user.id,
            domain=normalized,
            display_name=request.display_name or normalized,
            industry=request.industry,
            business_type=request.business_type,
            target_market=request.target_market,
            primary_language=request.primary_language,
            brand_name=request.brand_name,
            business_description=request.business_description,
            is_active=True,
            analysis_count=0,
        )

        db.add(domain)
        db.commit()
        db.refresh(domain)

        logger.info(f"Domain created: {normalized} for user {current_user.id}")

        return domain_to_response(domain)


@router.patch("/{domain_id}", response_model=DomainResponse)
async def update_domain(
    domain_id: UUID,
    request: UpdateDomainRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update domain settings.

    Only updates fields that are provided (non-null).
    """
    with get_db_context() as db:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()

        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        check_domain_access(domain, current_user)

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(domain, field, value)

        domain.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(domain)

        # Get latest analysis
        latest_run = db.query(AnalysisRun).filter(
            AnalysisRun.domain_id == domain.id
        ).order_by(AnalysisRun.created_at.desc()).first()

        logger.info(f"Domain updated: {domain.domain}")

        return domain_to_response(domain, latest_run)


@router.delete("/{domain_id}", status_code=204)
async def delete_domain(
    domain_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a domain and all its associated data.

    WARNING: This permanently deletes all analyses, keywords, competitors, etc.
    Consider using PATCH to set is_active=false instead for soft delete.
    """
    with get_db_context() as db:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()

        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        check_domain_access(domain, current_user)

        domain_name = domain.domain
        db.delete(domain)
        db.commit()

        logger.info(f"Domain deleted: {domain_name} by user {current_user.id}")

        return None

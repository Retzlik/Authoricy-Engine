"""
Cache Management API

Provides endpoints for cache monitoring and manual operations.

Endpoints:
- Health check for monitoring/alerting
- Statistics for dashboard insights
- Manual invalidation for debugging
- Precomputation trigger for testing
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import AnalysisRun, Domain, AnalysisStatus
from src.cache.postgres_cache import PostgresCache, get_postgres_cache
from src.cache.precomputation import trigger_precomputation


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cache", tags=["Cache Management"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class CacheHealthResponse(BaseModel):
    """Cache health check response."""
    status: str = Field(..., description="healthy or unhealthy")
    backend: str = Field(default="postgresql", description="Cache backend type")
    cached_entries: int = Field(..., description="Number of cached entries")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    enabled: bool
    backend: str
    hits: int
    misses: int
    writes: int
    hit_rate_percent: float


class InvalidationResponse(BaseModel):
    """Cache invalidation response."""
    success: bool
    keys_invalidated: int
    duration_ms: float
    errors: List[str] = []


class PrecomputeResponse(BaseModel):
    """Precomputation response."""
    success: bool
    analysis_id: str
    domain_id: str
    components_computed: int
    duration_seconds: float
    errors: List[str] = []


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/health", response_model=CacheHealthResponse)
def cache_health_check(db: Session = Depends(get_db)):
    """
    Check cache infrastructure health.

    Use this endpoint for monitoring and alerting systems.
    With PostgreSQL caching, this simply verifies database connectivity.
    """
    cache = get_postgres_cache(db)
    health = cache.health_check()

    return CacheHealthResponse(
        status="healthy" if health["healthy"] else "unhealthy",
        backend=health["backend"],
        cached_entries=health.get("cached_entries", 0),
        timestamp=datetime.utcnow(),
    )


@router.get("/stats", response_model=CacheStatsResponse)
def get_cache_stats(db: Session = Depends(get_db)):
    """
    Get current cache statistics.

    Useful for monitoring cache performance over time.
    Note: Stats are reset on application restart.
    """
    cache = get_postgres_cache(db)
    stats = cache.get_stats()
    return CacheStatsResponse(**stats)


@router.post("/invalidate/domain/{domain_id}", response_model=InvalidationResponse)
def invalidate_domain_cache(domain_id: UUID, db: Session = Depends(get_db)):
    """
    Invalidate all cache for a specific domain.

    Use this when you need to force-refresh all cached data for a domain,
    for example after manual data corrections or during debugging.
    """
    start = datetime.utcnow()

    cache = get_postgres_cache(db)
    count = cache.invalidate_domain(str(domain_id))

    elapsed = (datetime.utcnow() - start).total_seconds() * 1000

    return InvalidationResponse(
        success=True,
        keys_invalidated=count,
        duration_ms=elapsed,
        errors=[],
    )


@router.post("/invalidate/analysis/{analysis_id}", response_model=InvalidationResponse)
def invalidate_analysis_cache(analysis_id: UUID, db: Session = Depends(get_db)):
    """
    Invalidate all cache for a specific analysis.
    """
    start = datetime.utcnow()

    cache = get_postgres_cache(db)
    count = cache.invalidate_analysis(str(analysis_id))

    elapsed = (datetime.utcnow() - start).total_seconds() * 1000

    return InvalidationResponse(
        success=True,
        keys_invalidated=count,
        duration_ms=elapsed,
        errors=[],
    )


@router.post("/invalidate/all", response_model=InvalidationResponse)
def invalidate_all_cache(db: Session = Depends(get_db)):
    """
    Invalidate ALL cache data.

    CAUTION: This clears the entire cache and will temporarily
    degrade performance until caches are repopulated.

    Use only in emergencies or during debugging.
    """
    from src.database.models import PrecomputedDashboard

    start = datetime.utcnow()

    try:
        result = db.query(PrecomputedDashboard).update({"is_current": False})
        db.commit()
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000

        return InvalidationResponse(
            success=True,
            keys_invalidated=result,
            duration_ms=elapsed,
            errors=[],
        )
    except Exception as e:
        logger.error(f"Failed to invalidate all cache: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/precompute/{analysis_id}", response_model=PrecomputeResponse)
def trigger_precompute(
    analysis_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Manually trigger precomputation for an analysis.

    This is normally done automatically when an analysis completes.
    Use this endpoint to:
    - Re-run precomputation after data corrections
    - Debug precomputation issues
    - Force cache population

    Note: This is a synchronous operation and may take 10-30 seconds.
    """
    from src.database.models import AnalysisRun

    analysis = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        result = trigger_precomputation(analysis_id, db)

        return PrecomputeResponse(
            success=len(result.get("errors", [])) == 0,
            analysis_id=result["analysis_id"],
            domain_id=result["domain_id"],
            components_computed=result["components_computed"],
            duration_seconds=result["duration_seconds"],
            errors=result.get("errors", []),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to trigger precomputation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warm/domain/{domain_id}")
def warm_domain_cache(
    domain_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Warm cache for a specific domain.

    Triggers precomputation for the domain's latest analysis.
    """
    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.status == AnalysisStatus.COMPLETED,
    ).order_by(AnalysisRun.completed_at.desc()).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for domain")

    def warm_task():
        try:
            trigger_precomputation(analysis.id, db)
        except Exception as e:
            logger.error(f"Failed to warm cache for domain {domain_id}: {e}")

    background_tasks.add_task(warm_task)

    return {
        "status": "warming_started",
        "domain_id": str(domain_id),
        "analysis_id": str(analysis.id),
    }

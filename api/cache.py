"""
Cache Management API

Provides endpoints for cache monitoring, health checks, and manual operations.

Endpoints:
- Health check for monitoring/alerting
- Statistics for dashboard insights
- Manual invalidation for debugging
- Precomputation trigger for testing
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import AnalysisRun, Domain
from src.cache.redis_cache import get_redis_cache
from src.cache.monitoring import get_cache_monitor, HealthStatus, run_health_check
from src.cache.invalidation import get_cache_invalidator, CacheEvent
from src.cache.precomputation import trigger_precomputation
from src.cache.warming import CacheWarmer


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cache", tags=["Cache Management"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class CacheHealthResponse(BaseModel):
    """Cache health check response."""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    latency_ms: float = Field(..., description="Health check latency in ms")
    checks: Dict[str, bool] = Field(..., description="Individual check results")
    issues: List[Dict[str, Any]] = Field(default=[], description="List of issues found")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    enabled: bool
    initialized: bool
    hits: int
    misses: int
    hit_rate_percent: float
    avg_latency_ms: float
    bytes_written: int
    bytes_read: int
    bytes_saved_compression: int
    errors: int
    circuit_breaker_open: bool


class CacheSummaryResponse(BaseModel):
    """Cache performance summary."""
    health: Dict[str, Any]
    performance: Dict[str, Any]
    storage: Dict[str, Any]
    reliability: Dict[str, Any]
    timestamp: datetime


class InvalidationResponse(BaseModel):
    """Cache invalidation response."""
    success: bool
    keys_invalidated: int
    cdn_purged: bool
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
async def cache_health_check():
    """
    Check cache infrastructure health.

    Use this endpoint for monitoring and alerting systems.

    Returns:
    - status: overall health (healthy/degraded/unhealthy)
    - latency_ms: how long the check took
    - checks: individual check results (connectivity, latency, hit_rate, memory)
    - issues: list of problems found with severity and recommended actions

    Health thresholds:
    - Latency: <50ms = healthy
    - Hit rate: >80% = healthy
    - Memory: <1GB = healthy
    """
    result = await run_health_check()

    return CacheHealthResponse(
        status=result.status.value,
        latency_ms=result.latency_ms,
        checks=result.checks,
        issues=result.issues,
        timestamp=result.timestamp,
    )


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get current cache statistics.

    Useful for monitoring cache performance over time.
    """
    try:
        cache = await get_redis_cache()
        stats = cache.get_stats()
        return CacheStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=CacheSummaryResponse)
async def get_cache_summary():
    """
    Get comprehensive cache performance summary.

    Includes health status, performance metrics, storage stats, and trends.
    """
    try:
        monitor = await get_cache_monitor()
        summary = await monitor.get_summary()

        return CacheSummaryResponse(
            health=summary["health"],
            performance=summary["performance"],
            storage=summary["storage"],
            reliability=summary["reliability"],
            timestamp=datetime.fromisoformat(summary["timestamp"]),
        )
    except Exception as e:
        logger.error(f"Failed to get cache summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/redis-info")
async def get_redis_info():
    """
    Get Redis server information.

    Returns detailed Redis server metrics including memory, connections,
    and keyspace statistics.
    """
    try:
        cache = await get_redis_cache()
        info = await cache.get_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get Redis info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate/domain/{domain_id}", response_model=InvalidationResponse)
async def invalidate_domain_cache(domain_id: UUID):
    """
    Invalidate all cache for a specific domain.

    Use this when you need to force-refresh all cached data for a domain,
    for example after manual data corrections or during debugging.
    """
    try:
        invalidator = await get_cache_invalidator()
        result = await invalidator.handle_event(
            CacheEvent.MANUAL_INVALIDATE_DOMAIN,
            domain_id=str(domain_id),
        )

        return InvalidationResponse(
            success=result.success,
            keys_invalidated=result.keys_invalidated,
            cdn_purged=result.cdn_purged,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )
    except Exception as e:
        logger.error(f"Failed to invalidate domain cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate/analysis/{analysis_id}", response_model=InvalidationResponse)
async def invalidate_analysis_cache(analysis_id: UUID):
    """
    Invalidate all cache for a specific analysis.
    """
    try:
        cache = await get_redis_cache()
        count = await cache.invalidate_analysis(str(analysis_id))

        return InvalidationResponse(
            success=True,
            keys_invalidated=count,
            cdn_purged=False,
            duration_ms=0,
            errors=[],
        )
    except Exception as e:
        logger.error(f"Failed to invalidate analysis cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate/all", response_model=InvalidationResponse)
async def invalidate_all_cache():
    """
    Invalidate ALL cache data.

    ⚠️ CAUTION: This clears the entire cache and will temporarily
    degrade performance until caches are repopulated.

    Use only in emergencies or during debugging.
    """
    try:
        invalidator = await get_cache_invalidator()
        result = await invalidator.handle_event(CacheEvent.MANUAL_INVALIDATE_ALL)

        return InvalidationResponse(
            success=result.success,
            keys_invalidated=result.keys_invalidated,
            cdn_purged=result.cdn_purged,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )
    except Exception as e:
        logger.error(f"Failed to invalidate all cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/precompute/{analysis_id}", response_model=PrecomputeResponse)
async def trigger_precompute(
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
    try:
        result = await trigger_precomputation(analysis_id, db)

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
async def warm_domain_cache(
    domain_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Warm cache for a specific domain.

    Runs in background and returns immediately.
    """
    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
    ).order_by(AnalysisRun.completed_at.desc()).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for domain")

    async def warm_task():
        warmer = CacheWarmer(db)
        await warmer.warm_domain(str(domain_id), str(analysis.id))

    background_tasks.add_task(warm_task)

    return {
        "status": "warming_started",
        "domain_id": str(domain_id),
        "analysis_id": str(analysis.id),
    }


@router.post("/warm/active")
async def warm_active_domains(
    limit: int = Query(20, ge=1, le=100),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Warm cache for recently active domains.

    Runs in background and returns immediately.
    Warms up to `limit` most recently analyzed domains.
    """
    async def warm_task():
        warmer = CacheWarmer(db)
        await warmer.warm_active_domains(limit=limit)

    background_tasks.add_task(warm_task)

    return {
        "status": "warming_started",
        "limit": limit,
    }

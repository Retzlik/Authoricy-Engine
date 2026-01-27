"""
Authoricy Caching Layer

Multi-layer caching strategy for high-performance dashboard delivery:
- Layer 1: Browser Cache (React Query - handled by frontend)
- Layer 2: Edge Cache (CDN with HTTP Cache-Control headers)
- Layer 3: Application Cache (Redis for hot data)
- Layer 4: Precomputed Cache (PostgreSQL + Redis for expensive aggregations)
- Layer 5: Database (PostgreSQL - source of truth)

Key components:
- RedisCache: Type-safe Redis operations with compression
- PrecomputationPipeline: Background computation after analysis completion
- CacheInvalidator: Event-driven cache invalidation
- CacheHeaders: HTTP cache header management
- CacheMonitor: Health checks and metrics
- CacheWarmer: Proactive cache warming

Target performance:
- Dashboard load: <500ms (from 2-5s)
- Keywords table: <300ms (from 1-3s)
- API calls per view: 1-2 (from 6-8)
- Cache hit rate: >90%

Usage:
    # Get cached data or compute
    cache = await get_redis_cache()
    data = await cache.get_dashboard(domain_id, "overview", analysis_id)

    # Invalidate on changes
    invalidator = await get_cache_invalidator()
    await invalidator.handle_event(CacheEvent.ANALYSIS_COMPLETED, domain_id=...)

    # Precompute after analysis
    await trigger_precomputation(analysis_id, db)

    # Add HTTP cache headers
    add_cache_headers(response, max_age=300, etag=etag)
"""

from src.cache.config import CacheConfig, CacheTTL, get_cache_config
from src.cache.redis_cache import RedisCache, get_redis_cache, close_redis_cache
from src.cache.precomputation import PrecomputationPipeline, trigger_precomputation
from src.cache.invalidation import (
    CacheInvalidator,
    CacheEvent,
    get_cache_invalidator,
    invalidate_on_analysis_complete,
)
from src.cache.headers import (
    cache_headers,
    generate_etag,
    add_cache_headers,
    check_not_modified,
    CacheHeadersBuilder,
)
from src.cache.monitoring import (
    CacheMonitor,
    CacheMetrics,
    get_cache_monitor,
    run_health_check,
)
from src.cache.warming import CacheWarmer, warm_after_analysis

__all__ = [
    # Config
    "CacheConfig",
    "CacheTTL",
    "get_cache_config",
    # Redis
    "RedisCache",
    "get_redis_cache",
    "close_redis_cache",
    # Precomputation
    "PrecomputationPipeline",
    "trigger_precomputation",
    # Invalidation
    "CacheInvalidator",
    "CacheEvent",
    "get_cache_invalidator",
    "invalidate_on_analysis_complete",
    # Headers
    "cache_headers",
    "generate_etag",
    "add_cache_headers",
    "check_not_modified",
    "CacheHeadersBuilder",
    # Monitoring
    "CacheMonitor",
    "CacheMetrics",
    "get_cache_monitor",
    "run_health_check",
    # Warming
    "CacheWarmer",
    "warm_after_analysis",
]

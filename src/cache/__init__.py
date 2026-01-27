"""
Authoricy Cache Module

Simple PostgreSQL-based caching for precomputed dashboard data.

No Redis required - all caching uses the same PostgreSQL database
as the application, stored in the precomputed_dashboard table.

Key insight: Dashboard data only changes when new analysis completes.
Pre-computing and storing in PostgreSQL gives us:
- Sub-100ms reads (simple indexed query)
- No additional infrastructure
- ACID guarantees
- Automatic backup with database

Target performance:
- Dashboard load: <500ms (from 2-5s)
- Keywords table: <300ms (from 1-3s)
- API calls per view: 1-2 (from 6-8)
- Cache hit rate: >90%

Usage:
    # Get cached data
    cache = get_postgres_cache(db)
    data = cache.get_dashboard(domain_id, "overview", analysis_id)

    # Precompute after analysis
    trigger_precomputation(analysis_id, db)

    # Add HTTP cache headers
    add_cache_headers(response, max_age=300, etag=etag)
"""

from src.cache.config import CacheConfig, CacheTTL, get_cache_config
from src.cache.postgres_cache import PostgresCache, get_postgres_cache
from src.cache.precomputation import PrecomputationPipeline, trigger_precomputation
from src.cache.headers import (
    generate_etag,
    add_cache_headers,
    check_not_modified,
    CacheHeadersBuilder,
)

__all__ = [
    # Config
    "CacheConfig",
    "CacheTTL",
    "get_cache_config",
    # PostgreSQL cache
    "PostgresCache",
    "get_postgres_cache",
    # Precomputation
    "PrecomputationPipeline",
    "trigger_precomputation",
    # HTTP headers
    "generate_etag",
    "add_cache_headers",
    "check_not_modified",
    "CacheHeadersBuilder",
]

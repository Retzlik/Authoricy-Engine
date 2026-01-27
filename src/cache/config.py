"""
Cache Configuration

Centralized configuration for all caching layers.
TTLs are carefully tuned based on data change frequency.
"""

import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional
from functools import lru_cache


@dataclass(frozen=True)
class CacheTTL:
    """
    Cache TTL configuration by data type.

    Key insight: Most dashboard data only changes when a new analysis runs.
    This happens weekly or monthly. We're re-computing data that hasn't
    changed on every page load - that's the waste we're eliminating.
    """

    # Dashboard data (stable after analysis completion)
    DASHBOARD_OVERVIEW: timedelta = timedelta(hours=4)
    DASHBOARD_SPARKLINES: timedelta = timedelta(hours=6)
    DASHBOARD_SOV: timedelta = timedelta(hours=8)
    DASHBOARD_BATTLEGROUND: timedelta = timedelta(hours=8)
    DASHBOARD_CLUSTERS: timedelta = timedelta(hours=12)
    DASHBOARD_CONTENT_AUDIT: timedelta = timedelta(hours=12)
    DASHBOARD_AI_SUMMARY: timedelta = timedelta(hours=24)
    DASHBOARD_OPPORTUNITIES: timedelta = timedelta(hours=8)
    DASHBOARD_BUNDLE: timedelta = timedelta(hours=4)

    # Keywords data (large datasets, cache longer)
    KEYWORDS_PAGE: timedelta = timedelta(hours=4)
    KEYWORDS_FULL: timedelta = timedelta(hours=12)

    # Precomputed data (until new analysis invalidates)
    PRECOMPUTED: timedelta = timedelta(days=30)

    # Strategy data (user edits, shorter cache)
    STRATEGY: timedelta = timedelta(minutes=10)
    STRATEGY_THREADS: timedelta = timedelta(minutes=10)
    STRATEGY_KEYWORDS: timedelta = timedelta(minutes=5)

    # Greenfield data
    GREENFIELD_ANALYSIS: timedelta = timedelta(hours=24)
    COMPETITOR_INTELLIGENCE: timedelta = timedelta(hours=24)

    # Analysis status (real-time polling)
    ANALYSIS_STATUS: timedelta = timedelta(seconds=5)

    # Domain list (stable, user rarely adds domains)
    DOMAINS_LIST: timedelta = timedelta(minutes=30)

    @classmethod
    def for_endpoint(cls, endpoint: str) -> timedelta:
        """Get TTL for an endpoint name."""
        mapping = {
            "overview": cls.DASHBOARD_OVERVIEW,
            "sparklines": cls.DASHBOARD_SPARKLINES,
            "sov": cls.DASHBOARD_SOV,
            "battleground": cls.DASHBOARD_BATTLEGROUND,
            "clusters": cls.DASHBOARD_CLUSTERS,
            "content-audit": cls.DASHBOARD_CONTENT_AUDIT,
            "intelligence-summary": cls.DASHBOARD_AI_SUMMARY,
            "opportunities": cls.DASHBOARD_OPPORTUNITIES,
            "bundle": cls.DASHBOARD_BUNDLE,
            "keywords": cls.KEYWORDS_PAGE,
        }
        return mapping.get(endpoint, cls.DASHBOARD_OVERVIEW)


@dataclass
class CacheConfig:
    """
    Main cache configuration.

    All settings can be overridden via environment variables:
    - REDIS_URL: Redis connection URL
    - CACHE_ENABLED: Enable/disable caching globally
    - CACHE_COMPRESSION_ENABLED: Enable LZ4 compression
    - CACHE_COMPRESSION_THRESHOLD: Min size for compression
    """

    # Redis connection
    redis_url: str = field(default_factory=lambda: os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    ))
    redis_max_connections: int = field(default_factory=lambda: int(
        os.getenv("REDIS_MAX_CONNECTIONS", "50")
    ))
    redis_socket_timeout: float = field(default_factory=lambda: float(
        os.getenv("REDIS_SOCKET_TIMEOUT", "5.0")
    ))
    redis_connect_timeout: float = field(default_factory=lambda: float(
        os.getenv("REDIS_CONNECT_TIMEOUT", "2.0")
    ))

    # Cache namespace (for multi-tenant isolation)
    namespace: str = field(default_factory=lambda: os.getenv(
        "CACHE_NAMESPACE",
        "authoricy"
    ))

    # Global cache toggle
    enabled: bool = field(default_factory=lambda: os.getenv(
        "CACHE_ENABLED",
        "true"
    ).lower() == "true")

    # Compression settings
    compression_enabled: bool = field(default_factory=lambda: os.getenv(
        "CACHE_COMPRESSION_ENABLED",
        "true"
    ).lower() == "true")
    compression_threshold: int = field(default_factory=lambda: int(
        os.getenv("CACHE_COMPRESSION_THRESHOLD", "1024")
    ))  # Only compress if > 1KB

    # Precomputation settings
    precomputation_enabled: bool = field(default_factory=lambda: os.getenv(
        "CACHE_PRECOMPUTATION_ENABLED",
        "true"
    ).lower() == "true")
    precomputation_batch_size: int = field(default_factory=lambda: int(
        os.getenv("CACHE_PRECOMPUTATION_BATCH_SIZE", "100")
    ))

    # Cache warming settings
    warming_enabled: bool = field(default_factory=lambda: os.getenv(
        "CACHE_WARMING_ENABLED",
        "true"
    ).lower() == "true")
    warming_interval_seconds: int = field(default_factory=lambda: int(
        os.getenv("CACHE_WARMING_INTERVAL", "300")
    ))  # 5 minutes

    # HTTP cache settings
    http_cache_enabled: bool = field(default_factory=lambda: os.getenv(
        "HTTP_CACHE_ENABLED",
        "true"
    ).lower() == "true")

    # CDN purge settings
    cdn_purge_enabled: bool = field(default_factory=lambda: os.getenv(
        "CDN_PURGE_ENABLED",
        "false"
    ).lower() == "true")
    cloudflare_zone_id: Optional[str] = field(default_factory=lambda: os.getenv(
        "CLOUDFLARE_ZONE_ID"
    ))
    cloudflare_api_token: Optional[str] = field(default_factory=lambda: os.getenv(
        "CLOUDFLARE_API_TOKEN"
    ))

    # Monitoring thresholds
    min_hit_rate: float = field(default_factory=lambda: float(
        os.getenv("CACHE_MIN_HIT_RATE", "0.8")
    ))  # Alert if < 80%
    max_latency_ms: float = field(default_factory=lambda: float(
        os.getenv("CACHE_MAX_LATENCY_MS", "50")
    ))  # Alert if > 50ms
    max_memory_mb: int = field(default_factory=lambda: int(
        os.getenv("CACHE_MAX_MEMORY_MB", "1024")
    ))  # Alert if > 1GB

    # Circuit breaker settings
    circuit_breaker_enabled: bool = field(default_factory=lambda: os.getenv(
        "CACHE_CIRCUIT_BREAKER_ENABLED",
        "true"
    ).lower() == "true")
    circuit_breaker_threshold: int = field(default_factory=lambda: int(
        os.getenv("CACHE_CIRCUIT_BREAKER_THRESHOLD", "5")
    ))  # Failures before opening
    circuit_breaker_timeout: int = field(default_factory=lambda: int(
        os.getenv("CACHE_CIRCUIT_BREAKER_TIMEOUT", "60")
    ))  # Seconds before retry


@lru_cache(maxsize=1)
def get_cache_config() -> CacheConfig:
    """Get singleton cache configuration."""
    return CacheConfig()


# HTTP Cache-Control presets for different data types
HTTP_CACHE_PRESETS = {
    "stable": {
        # Data that rarely changes (precomputed aggregations)
        "max_age": 3600,  # 1 hour
        "stale_while_revalidate": 7200,  # 2 hours
        "public": True,
    },
    "moderate": {
        # Data that changes occasionally (dashboard components)
        "max_age": 300,  # 5 minutes
        "stale_while_revalidate": 600,  # 10 minutes
        "public": True,
    },
    "volatile": {
        # Data that changes frequently (strategy edits)
        "max_age": 60,  # 1 minute
        "stale_while_revalidate": 120,  # 2 minutes
        "public": False,  # Private, user-specific
    },
    "realtime": {
        # Data that must be fresh (analysis status)
        "max_age": 0,
        "no_store": True,
    },
}

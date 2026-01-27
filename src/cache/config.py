"""
Cache Configuration

Centralized configuration for caching layer.
TTLs define HTTP cache header durations.

Note: Application cache uses PostgreSQL (precomputed_dashboard table).
No Redis required.
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

    These values are used for:
    - HTTP Cache-Control headers (browser/CDN caching)
    - Determining when to refresh precomputed data
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

    Settings can be overridden via environment variables:
    - CACHE_ENABLED: Enable/disable caching globally
    - HTTP_CACHE_ENABLED: Enable HTTP cache headers
    """

    # Cache namespace (for key prefixes)
    namespace: str = field(default_factory=lambda: os.getenv(
        "CACHE_NAMESPACE",
        "authoricy"
    ))

    # Global cache toggle
    enabled: bool = field(default_factory=lambda: os.getenv(
        "CACHE_ENABLED",
        "true"
    ).lower() == "true")

    # Precomputation settings
    precomputation_enabled: bool = field(default_factory=lambda: os.getenv(
        "CACHE_PRECOMPUTATION_ENABLED",
        "true"
    ).lower() == "true")

    # HTTP cache settings
    http_cache_enabled: bool = field(default_factory=lambda: os.getenv(
        "HTTP_CACHE_ENABLED",
        "true"
    ).lower() == "true")

    # CDN purge settings (optional - for Cloudflare integration)
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

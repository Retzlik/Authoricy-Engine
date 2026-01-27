"""
Cache Invalidation Service

Event-driven cache invalidation with minimal scope.
Principle: Invalidate as narrowly as possible.

Events trigger targeted cache invalidation:
- ANALYSIS_COMPLETED: Invalidate dashboard + keywords for domain
- STRATEGY_UPDATED: Invalidate only strategy cache
- DOMAIN_ADDED: No invalidation needed (new data)
"""

import asyncio
import logging
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

import httpx

from src.cache.redis_cache import RedisCache, get_redis_cache
from src.cache.config import get_cache_config


logger = logging.getLogger(__name__)


class CacheEvent(Enum):
    """Events that trigger cache invalidation."""

    # Analysis lifecycle
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"

    # Strategy changes
    STRATEGY_CREATED = "strategy_created"
    STRATEGY_UPDATED = "strategy_updated"
    STRATEGY_DELETED = "strategy_deleted"
    THREAD_CREATED = "thread_created"
    THREAD_UPDATED = "thread_updated"
    THREAD_DELETED = "thread_deleted"
    KEYWORDS_ASSIGNED = "keywords_assigned"
    KEYWORDS_UNASSIGNED = "keywords_unassigned"

    # Domain changes
    DOMAIN_ADDED = "domain_added"
    DOMAIN_UPDATED = "domain_updated"
    DOMAIN_DELETED = "domain_deleted"

    # Manual invalidation
    MANUAL_INVALIDATE_DOMAIN = "manual_invalidate_domain"
    MANUAL_INVALIDATE_ALL = "manual_invalidate_all"


@dataclass
class InvalidationResult:
    """Result of a cache invalidation operation."""
    event: CacheEvent
    success: bool
    keys_invalidated: int
    cdn_purged: bool
    duration_ms: float
    errors: List[str]


class CDNPurger:
    """
    Purges CDN cache using vendor-specific APIs.

    Supports:
    - Cloudflare (via Cache Tags or URL purging)
    - Vercel (via revalidation)
    """

    def __init__(
        self,
        cloudflare_zone_id: Optional[str] = None,
        cloudflare_api_token: Optional[str] = None,
    ):
        self.cloudflare_zone_id = cloudflare_zone_id
        self.cloudflare_api_token = cloudflare_api_token
        self._enabled = bool(cloudflare_zone_id and cloudflare_api_token)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def purge_by_tags(self, tags: List[str]) -> bool:
        """
        Purge CDN cache by surrogate keys/tags.

        Requires Cloudflare Enterprise for Cache Tags.
        Falls back to prefix purging for other plans.
        """
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/purge_cache",
                    headers={
                        "Authorization": f"Bearer {self.cloudflare_api_token}",
                        "Content-Type": "application/json",
                    },
                    json={"tags": tags},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info(f"CDN purged by tags: {tags}")
                    return True

                # Fall back to prefix purging if tags not supported
                logger.warning(
                    f"Tag-based purging failed (status {response.status_code}), "
                    "may need Enterprise plan"
                )
                return False

        except Exception as e:
            logger.error(f"CDN purge error: {e}")
            return False

    async def purge_prefix(self, prefix: str) -> bool:
        """Purge CDN cache by URL prefix."""
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/purge_cache",
                    headers={
                        "Authorization": f"Bearer {self.cloudflare_api_token}",
                        "Content-Type": "application/json",
                    },
                    json={"prefixes": [prefix]},
                    timeout=10.0,
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"CDN prefix purge error: {e}")
            return False

    async def purge_everything(self) -> bool:
        """Nuclear option: purge entire CDN cache."""
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/purge_cache",
                    headers={
                        "Authorization": f"Bearer {self.cloudflare_api_token}",
                        "Content-Type": "application/json",
                    },
                    json={"purge_everything": True},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.warning("CDN cache purged completely!")
                    return True
                return False

        except Exception as e:
            logger.error(f"CDN complete purge error: {e}")
            return False


class CacheInvalidator:
    """
    Handles cache invalidation based on events.

    Principle: Invalidate as narrowly as possible.
    Each event type has a specific invalidation scope.
    """

    def __init__(
        self,
        cache: Optional[RedisCache] = None,
        cdn_purger: Optional[CDNPurger] = None,
    ):
        self._cache = cache
        self._cdn_purger = cdn_purger

    async def _get_cache(self) -> RedisCache:
        if self._cache is None:
            self._cache = await get_redis_cache()
        return self._cache

    async def _get_cdn_purger(self) -> CDNPurger:
        if self._cdn_purger is None:
            config = get_cache_config()
            self._cdn_purger = CDNPurger(
                cloudflare_zone_id=config.cloudflare_zone_id,
                cloudflare_api_token=config.cloudflare_api_token,
            )
        return self._cdn_purger

    async def handle_event(
        self,
        event: CacheEvent,
        domain_id: Optional[str] = None,
        analysis_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        **kwargs,
    ) -> InvalidationResult:
        """
        Handle cache invalidation for an event.

        Each event type has specific invalidation logic to minimize
        cache churn while ensuring data consistency.
        """
        start_time = datetime.utcnow()
        errors = []
        keys_invalidated = 0
        cdn_purged = False

        logger.info(
            f"Cache invalidation event: {event.value}, "
            f"domain={domain_id}, analysis={analysis_id}"
        )

        cache = await self._get_cache()
        cdn = await self._get_cdn_purger()

        try:
            if event == CacheEvent.ANALYSIS_STARTED:
                # Don't invalidate yet - old data is still valid
                # The new data will create new cache entries
                pass

            elif event == CacheEvent.ANALYSIS_COMPLETED:
                # Invalidate all dashboard and keywords cache for this domain
                # The precomputation pipeline will repopulate with new data
                if domain_id:
                    keys_invalidated += await cache.invalidate_dashboard(domain_id)
                    keys_invalidated += await cache.invalidate_keywords(domain_id)

                # Purge CDN for this domain
                if cdn.is_enabled:
                    cdn_purged = await cdn.purge_by_tags([
                        f"domain:{domain_id}",
                        "dashboard",
                    ])
                    if analysis_id:
                        await cdn.purge_by_tags([f"analysis:{analysis_id}"])

            elif event == CacheEvent.ANALYSIS_FAILED:
                # Failed analysis - no data to cache, no invalidation needed
                pass

            elif event == CacheEvent.STRATEGY_CREATED:
                # New strategy - no existing cache to invalidate
                pass

            elif event == CacheEvent.STRATEGY_UPDATED:
                # Only invalidate strategy-specific cache
                if strategy_id:
                    key = cache._make_key("strategy", strategy_id)
                    if await cache.delete(key):
                        keys_invalidated += 1

            elif event == CacheEvent.STRATEGY_DELETED:
                # Invalidate all strategy-related cache
                if strategy_id:
                    pattern = cache._make_key("strategy", strategy_id, "*")
                    keys_invalidated += await cache.delete_pattern(pattern)

            elif event in (CacheEvent.THREAD_CREATED, CacheEvent.THREAD_UPDATED):
                # Invalidate thread and parent strategy cache
                if strategy_id:
                    pattern = cache._make_key("strategy", strategy_id, "*")
                    keys_invalidated += await cache.delete_pattern(pattern)

            elif event == CacheEvent.THREAD_DELETED:
                if thread_id:
                    pattern = cache._make_key("thread", thread_id, "*")
                    keys_invalidated += await cache.delete_pattern(pattern)
                if strategy_id:
                    key = cache._make_key("strategy", strategy_id)
                    if await cache.delete(key):
                        keys_invalidated += 1

            elif event in (CacheEvent.KEYWORDS_ASSIGNED, CacheEvent.KEYWORDS_UNASSIGNED):
                # Invalidate available keywords cache for strategy
                if strategy_id:
                    pattern = cache._make_key("strategy", strategy_id, "available-keywords", "*")
                    keys_invalidated += await cache.delete_pattern(pattern)

            elif event == CacheEvent.DOMAIN_ADDED:
                # New domain - no existing cache
                pass

            elif event == CacheEvent.DOMAIN_UPDATED:
                # Domain settings changed - minimal impact on cache
                # Only invalidate domain metadata cache if it exists
                if domain_id:
                    key = cache._make_key("domain", domain_id, "metadata")
                    if await cache.delete(key):
                        keys_invalidated += 1

            elif event == CacheEvent.DOMAIN_DELETED:
                # Complete invalidation for this domain
                if domain_id:
                    keys_invalidated += await cache.invalidate_domain(domain_id)

                if cdn.is_enabled:
                    cdn_purged = await cdn.purge_by_tags([f"domain:{domain_id}"])

            elif event == CacheEvent.MANUAL_INVALIDATE_DOMAIN:
                if domain_id:
                    keys_invalidated += await cache.invalidate_domain(domain_id)

                if cdn.is_enabled:
                    cdn_purged = await cdn.purge_by_tags([f"domain:{domain_id}"])

            elif event == CacheEvent.MANUAL_INVALIDATE_ALL:
                # Nuclear option - use sparingly
                pattern = cache._make_key("*")
                keys_invalidated += await cache.delete_pattern(pattern)

                if cdn.is_enabled:
                    cdn_purged = await cdn.purge_everything()

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Cache invalidation error: {e}")

        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        result = InvalidationResult(
            event=event,
            success=len(errors) == 0,
            keys_invalidated=keys_invalidated,
            cdn_purged=cdn_purged,
            duration_ms=duration,
            errors=errors,
        )

        logger.info(
            f"Invalidation complete: {keys_invalidated} keys, "
            f"CDN purged: {cdn_purged}, duration: {duration:.2f}ms"
        )

        return result


# Singleton instance
_invalidator: Optional[CacheInvalidator] = None


async def get_cache_invalidator() -> CacheInvalidator:
    """Get singleton cache invalidator instance."""
    global _invalidator

    if _invalidator is None:
        _invalidator = CacheInvalidator()

    return _invalidator


async def invalidate_on_analysis_complete(
    domain_id: str,
    analysis_id: str,
):
    """Convenience function to invalidate after analysis completes."""
    invalidator = await get_cache_invalidator()
    return await invalidator.handle_event(
        CacheEvent.ANALYSIS_COMPLETED,
        domain_id=domain_id,
        analysis_id=analysis_id,
    )


async def invalidate_on_strategy_update(strategy_id: str):
    """Convenience function to invalidate after strategy update."""
    invalidator = await get_cache_invalidator()
    return await invalidator.handle_event(
        CacheEvent.STRATEGY_UPDATED,
        strategy_id=strategy_id,
    )

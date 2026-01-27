"""
Cache Warming Service

Proactively warms caches to ensure fast first-load experience.
Runs in background to maintain hot cache for active domains.

Strategies:
1. Post-analysis warming: After analysis completes, warm all dashboard views
2. Predictive warming: Warm caches for domains likely to be accessed
3. Periodic warming: Refresh expiring cache entries before they expire
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.cache.redis_cache import RedisCache, get_redis_cache
from src.cache.precomputation import PrecomputationPipeline
from src.cache.config import get_cache_config, CacheTTL


logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    Proactive cache warming to ensure fast first-load experience.

    Features:
    - Post-analysis warming (triggered after analysis completion)
    - Predictive warming (based on access patterns)
    - Periodic refresh (before cache expiry)
    """

    def __init__(
        self,
        db: Session,
        cache: Optional[RedisCache] = None,
    ):
        self.db = db
        self._cache = cache
        self._config = get_cache_config()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def _get_cache(self) -> RedisCache:
        if self._cache is None:
            self._cache = await get_redis_cache()
        return self._cache

    async def warm_domain(
        self,
        domain_id: str,
        analysis_id: str,
        components: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        Warm cache for a specific domain and analysis.

        Args:
            domain_id: Domain to warm cache for
            analysis_id: Analysis to use for data
            components: Specific components to warm (default: all)

        Returns:
            Dict of component -> success status
        """
        logger.info(f"Warming cache for domain {domain_id}, analysis {analysis_id}")

        if components is None:
            components = [
                "overview", "sparklines", "sov", "battleground",
                "clusters", "content-audit", "opportunities", "keywords"
            ]

        pipeline = PrecomputationPipeline(self.db, await self._get_cache())

        results = {}
        for component in components:
            try:
                method_name = f"_precompute_{component.replace('-', '_')}"
                if hasattr(pipeline, method_name):
                    cache = await self._get_cache()
                    method = getattr(pipeline, method_name)

                    if component == "keywords":
                        await method(domain_id, analysis_id, cache)
                    elif component in ["overview"]:
                        # Get analysis object
                        from src.database.models import AnalysisRun
                        analysis = self.db.query(AnalysisRun).filter(
                            AnalysisRun.id == analysis_id
                        ).first()
                        await method(domain_id, analysis_id, analysis, cache)
                    else:
                        await method(domain_id, analysis_id, cache)

                    results[component] = True
                    logger.debug(f"Warmed {component} for domain {domain_id}")
                else:
                    results[component] = False
            except Exception as e:
                logger.error(f"Failed to warm {component} for {domain_id}: {e}")
                results[component] = False

        # Create bundle
        try:
            await pipeline._precompute_bundle(domain_id, analysis_id, await self._get_cache())
            results["bundle"] = True
        except Exception as e:
            logger.error(f"Failed to create bundle for {domain_id}: {e}")
            results["bundle"] = False

        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"Cache warming complete for {domain_id}: "
            f"{success_count}/{len(results)} components"
        )

        return results

    async def warm_active_domains(
        self,
        limit: int = 50,
    ) -> Dict[str, Dict[str, bool]]:
        """
        Warm cache for recently active domains.

        Prioritizes:
        1. Domains with recent analysis completion
        2. Domains with recent dashboard access (if tracking available)
        """
        from src.database.models import Domain, AnalysisRun, AnalysisStatus

        # Get domains with recent completed analyses
        cutoff = datetime.utcnow() - timedelta(days=7)

        analyses = (
            self.db.query(AnalysisRun)
            .filter(
                AnalysisRun.status == AnalysisStatus.COMPLETED,
                AnalysisRun.completed_at >= cutoff,
            )
            .order_by(desc(AnalysisRun.completed_at))
            .limit(limit)
            .all()
        )

        results = {}
        for analysis in analyses:
            domain_id = str(analysis.domain_id)
            analysis_id = str(analysis.id)

            try:
                results[domain_id] = await self.warm_domain(
                    domain_id, analysis_id
                )
            except Exception as e:
                logger.error(f"Failed to warm domain {domain_id}: {e}")
                results[domain_id] = {"error": str(e)}

        return results

    async def warm_expiring_entries(
        self,
        threshold_minutes: int = 30,
    ) -> int:
        """
        Refresh cache entries that are close to expiring.

        This prevents cache misses due to expiration during peak hours.
        """
        from src.database.models import AnalysisRun, AnalysisStatus

        cache = await self._get_cache()
        warmed_count = 0

        # Get recent analyses
        analyses = (
            self.db.query(AnalysisRun)
            .filter(AnalysisRun.status == AnalysisStatus.COMPLETED)
            .order_by(desc(AnalysisRun.completed_at))
            .limit(100)
            .all()
        )

        for analysis in analyses:
            domain_id = str(analysis.domain_id)
            analysis_id = str(analysis.id)

            # Check each component's TTL
            for component in ["overview", "sparklines", "sov"]:
                key = cache.dashboard_key(domain_id, component, analysis_id)
                ttl = await cache.ttl(key)

                # If TTL is less than threshold, refresh
                if 0 < ttl < threshold_minutes * 60:
                    try:
                        await self.warm_domain(
                            domain_id, analysis_id, components=[component]
                        )
                        warmed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to refresh {component} for {domain_id}: {e}")

        logger.info(f"Refreshed {warmed_count} expiring cache entries")
        return warmed_count

    async def start_background_warmer(
        self,
        interval_seconds: Optional[int] = None,
    ):
        """
        Start background warming task.

        Runs periodically to:
        1. Warm cache for active domains
        2. Refresh expiring entries
        """
        if self._running:
            logger.warning("Background warmer already running")
            return

        interval = interval_seconds or self._config.warming_interval_seconds
        self._running = True

        async def warming_loop():
            while self._running:
                try:
                    logger.info("Running background cache warming...")

                    # Warm active domains
                    await self.warm_active_domains(limit=20)

                    # Refresh expiring entries
                    await self.warm_expiring_entries(threshold_minutes=30)

                    logger.info(f"Background warming complete, sleeping for {interval}s")

                except Exception as e:
                    logger.error(f"Background warming error: {e}")

                await asyncio.sleep(interval)

        self._task = asyncio.create_task(warming_loop())
        logger.info(f"Background cache warmer started (interval: {interval}s)")

    async def stop_background_warmer(self):
        """Stop background warming task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Background cache warmer stopped")


async def warm_after_analysis(
    analysis_id: UUID,
    db: Session,
):
    """
    Convenience function to warm cache after analysis completes.

    Should be called from the analysis pipeline when transitioning
    to COMPLETED status.
    """
    from src.database.models import AnalysisRun

    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.id == analysis_id
    ).first()

    if not analysis:
        logger.error(f"Analysis not found for warming: {analysis_id}")
        return

    warmer = CacheWarmer(db)
    return await warmer.warm_domain(
        str(analysis.domain_id),
        str(analysis_id),
    )

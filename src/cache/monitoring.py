"""
Cache Monitoring

Health checks, metrics collection, and alerting for cache infrastructure.
Provides visibility into cache performance and helps identify issues.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from src.cache.redis_cache import RedisCache, get_redis_cache
from src.cache.config import get_cache_config, CacheConfig


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    timestamp: datetime

    # Hit/miss statistics
    hits: int
    misses: int
    hit_rate: float

    # Latency
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

    # Memory
    memory_used_mb: float
    memory_peak_mb: float

    # Throughput
    bytes_read: int
    bytes_written: int
    bytes_saved_compression: int

    # Errors
    errors: int
    error_rate: float

    # Circuit breaker
    circuit_breaker_open: bool

    # Connection pool
    active_connections: int
    max_connections: int


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    status: HealthStatus
    latency_ms: float
    checks: Dict[str, bool]
    issues: List[Dict[str, Any]]
    metrics: Optional[CacheMetrics] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CacheMonitor:
    """
    Monitors cache health and performance.

    Provides:
    - Health checks (connectivity, latency, memory)
    - Performance metrics (hit rate, latency percentiles)
    - Alerting thresholds
    - Trend analysis
    """

    def __init__(
        self,
        cache: Optional[RedisCache] = None,
        config: Optional[CacheConfig] = None,
    ):
        self._cache = cache
        self._config = config or get_cache_config()
        self._metrics_history: List[CacheMetrics] = []
        self._max_history = 1000  # Keep last 1000 samples

    async def _get_cache(self) -> RedisCache:
        if self._cache is None:
            self._cache = await get_redis_cache()
        return self._cache

    async def health_check(self) -> HealthCheckResult:
        """
        Perform comprehensive health check.

        Returns:
            HealthCheckResult with status, latency, and issues
        """
        start_time = time.time()
        checks = {}
        issues = []

        try:
            cache = await self._get_cache()

            # Check 1: Connectivity
            try:
                info = await cache.get_info()
                checks["connectivity"] = info.get("connected", False)
                if not checks["connectivity"]:
                    issues.append({
                        "type": "connectivity",
                        "severity": "critical",
                        "message": "Redis connection failed",
                        "action": "Check Redis server status and network connectivity",
                    })
            except Exception as e:
                checks["connectivity"] = False
                issues.append({
                    "type": "connectivity",
                    "severity": "critical",
                    "message": f"Redis connection error: {str(e)}",
                    "action": "Check Redis server and connection settings",
                })

            # Check 2: Latency
            latency_ms = 0.0
            if checks.get("connectivity"):
                latency_samples = []
                for _ in range(5):
                    ping_start = time.time()
                    await cache._redis.ping()
                    latency_samples.append((time.time() - ping_start) * 1000)

                latency_ms = sum(latency_samples) / len(latency_samples)
                checks["latency"] = latency_ms < self._config.max_latency_ms

                if not checks["latency"]:
                    issues.append({
                        "type": "latency",
                        "severity": "warning",
                        "message": f"High cache latency: {latency_ms:.2f}ms",
                        "threshold": self._config.max_latency_ms,
                        "action": "Check Redis server load and network conditions",
                    })

            # Check 3: Hit rate
            stats = cache.get_stats()
            hit_rate = stats.get("hit_rate_percent", 0) / 100
            checks["hit_rate"] = hit_rate >= self._config.min_hit_rate

            if not checks["hit_rate"] and (stats["hits"] + stats["misses"]) > 100:
                issues.append({
                    "type": "hit_rate",
                    "severity": "warning",
                    "message": f"Low cache hit rate: {hit_rate*100:.1f}%",
                    "threshold": self._config.min_hit_rate * 100,
                    "action": "Review cache TTLs and precomputation coverage",
                })

            # Check 4: Memory usage
            if checks.get("connectivity"):
                memory_mb = info.get("used_memory_mb", 0)
                checks["memory"] = memory_mb < self._config.max_memory_mb

                if not checks["memory"]:
                    issues.append({
                        "type": "memory",
                        "severity": "warning",
                        "message": f"High memory usage: {memory_mb:.1f}MB",
                        "threshold": self._config.max_memory_mb,
                        "action": "Review cache eviction policy and TTLs",
                    })

            # Check 5: Circuit breaker
            circuit_breaker_open = stats.get("circuit_breaker_open", False)
            checks["circuit_breaker"] = not circuit_breaker_open

            if circuit_breaker_open:
                issues.append({
                    "type": "circuit_breaker",
                    "severity": "critical",
                    "message": "Circuit breaker is open (cache failing over to bypass)",
                    "action": "Investigate Redis connectivity issues",
                })

            # Determine overall status
            if not checks.get("connectivity") or circuit_breaker_open:
                status = HealthStatus.UNHEALTHY
            elif not all([checks.get("latency", True), checks.get("hit_rate", True), checks.get("memory", True)]):
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            # Collect metrics
            metrics = await self._collect_metrics(cache, info if checks.get("connectivity") else {})

        except Exception as e:
            logger.error(f"Health check error: {e}")
            status = HealthStatus.UNHEALTHY
            latency_ms = (time.time() - start_time) * 1000
            checks["connectivity"] = False
            issues.append({
                "type": "error",
                "severity": "critical",
                "message": str(e),
                "action": "Check cache infrastructure",
            })
            metrics = None

        total_latency = (time.time() - start_time) * 1000

        return HealthCheckResult(
            status=status,
            latency_ms=total_latency,
            checks=checks,
            issues=issues,
            metrics=metrics,
        )

    async def _collect_metrics(
        self,
        cache: RedisCache,
        redis_info: Dict,
    ) -> CacheMetrics:
        """Collect detailed metrics."""
        stats = cache.get_stats()

        # Calculate latency percentiles from samples
        latency_samples = cache._stats.latency_samples[-100:]
        p95 = 0.0
        p99 = 0.0
        if latency_samples:
            sorted_samples = sorted(latency_samples)
            p95 = sorted_samples[int(len(sorted_samples) * 0.95)] * 1000
            p99 = sorted_samples[int(len(sorted_samples) * 0.99)] * 1000

        total = stats["hits"] + stats["misses"]
        error_rate = stats["errors"] / max(1, total + stats["errors"])

        metrics = CacheMetrics(
            timestamp=datetime.utcnow(),
            hits=stats["hits"],
            misses=stats["misses"],
            hit_rate=stats["hit_rate_percent"] / 100,
            avg_latency_ms=stats["avg_latency_ms"],
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            memory_used_mb=redis_info.get("used_memory_mb", 0),
            memory_peak_mb=redis_info.get("used_memory_peak_mb", 0),
            bytes_read=stats["bytes_read"],
            bytes_written=stats["bytes_written"],
            bytes_saved_compression=stats["bytes_saved_compression"],
            errors=stats["errors"],
            error_rate=error_rate,
            circuit_breaker_open=stats["circuit_breaker_open"],
            active_connections=redis_info.get("connected_clients", 0),
            max_connections=cache.config.redis_max_connections,
        )

        # Store in history
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]

        return metrics

    async def get_metrics(self) -> CacheMetrics:
        """Get current metrics."""
        cache = await self._get_cache()
        info = await cache.get_info()
        return await self._collect_metrics(cache, info)

    def get_metrics_history(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[CacheMetrics]:
        """Get metrics history."""
        history = self._metrics_history

        if since:
            history = [m for m in history if m.timestamp >= since]

        return history[-limit:]

    async def get_summary(self) -> Dict[str, Any]:
        """Get summary of cache performance."""
        health = await self.health_check()
        cache = await self._get_cache()
        stats = cache.get_stats()

        # Calculate trends from history
        recent = self.get_metrics_history(
            since=datetime.utcnow() - timedelta(hours=1),
            limit=60,
        )

        hit_rate_trend = "stable"
        latency_trend = "stable"

        if len(recent) >= 10:
            first_half = recent[:len(recent)//2]
            second_half = recent[len(recent)//2:]

            # Hit rate trend
            first_hit_rate = sum(m.hit_rate for m in first_half) / len(first_half)
            second_hit_rate = sum(m.hit_rate for m in second_half) / len(second_half)
            if second_hit_rate > first_hit_rate + 0.05:
                hit_rate_trend = "improving"
            elif second_hit_rate < first_hit_rate - 0.05:
                hit_rate_trend = "degrading"

            # Latency trend
            first_latency = sum(m.avg_latency_ms for m in first_half) / len(first_half)
            second_latency = sum(m.avg_latency_ms for m in second_half) / len(second_half)
            if second_latency < first_latency - 5:
                latency_trend = "improving"
            elif second_latency > first_latency + 5:
                latency_trend = "degrading"

        return {
            "health": {
                "status": health.status.value,
                "issues_count": len(health.issues),
                "critical_issues": len([i for i in health.issues if i.get("severity") == "critical"]),
            },
            "performance": {
                "hit_rate_percent": stats["hit_rate_percent"],
                "hit_rate_trend": hit_rate_trend,
                "avg_latency_ms": stats["avg_latency_ms"],
                "latency_trend": latency_trend,
            },
            "storage": {
                "bytes_written": stats["bytes_written"],
                "bytes_read": stats["bytes_read"],
                "bytes_saved_compression": stats["bytes_saved_compression"],
                "compression_ratio": (
                    stats["bytes_saved_compression"] / max(1, stats["bytes_written"])
                    if stats["bytes_written"] > 0 else 0
                ),
            },
            "reliability": {
                "errors": stats["errors"],
                "circuit_breaker_open": stats["circuit_breaker_open"],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


# Singleton instance
_monitor: Optional[CacheMonitor] = None


async def get_cache_monitor() -> CacheMonitor:
    """Get singleton cache monitor instance."""
    global _monitor

    if _monitor is None:
        _monitor = CacheMonitor()

    return _monitor


async def run_health_check() -> HealthCheckResult:
    """Convenience function to run health check."""
    monitor = await get_cache_monitor()
    return await monitor.health_check()

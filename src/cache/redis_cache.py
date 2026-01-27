"""
Redis Cache Implementation

Type-safe Redis cache with:
- Automatic compression for large values
- Circuit breaker for resilience
- Namespace isolation for multi-tenant support
- Async operations throughout
- Comprehensive statistics tracking
"""

import asyncio
import hashlib
import logging
import time
from datetime import timedelta
from typing import Any, Optional, TypeVar, Generic, List, Dict, Callable
from dataclasses import dataclass, field
from functools import wraps
from contextlib import asynccontextmanager

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.cache.config import CacheConfig, CacheTTL, get_cache_config
from src.cache.compression import (
    CacheCompressor,
    serialize_value,
    deserialize_value,
)


logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheStats:
    """Cache operation statistics."""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    bytes_written: int = 0
    bytes_read: int = 0
    bytes_saved_compression: int = 0
    latency_samples: List[float] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples[-100:]) / len(self.latency_samples[-100:]) * 1000

    def record_latency(self, seconds: float):
        """Record a latency sample."""
        self.latency_samples.append(seconds)
        # Keep only last 1000 samples
        if len(self.latency_samples) > 1000:
            self.latency_samples = self.latency_samples[-1000:]


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""
    failures: int = 0
    last_failure: float = 0.0
    is_open: bool = False
    opened_at: float = 0.0


class CircuitBreaker:
    """
    Circuit breaker pattern for Redis connection.

    Prevents thundering herd when Redis is down by failing fast
    after threshold failures, then gradually recovering.
    """

    def __init__(
        self,
        threshold: int = 5,
        timeout: int = 60,
    ):
        self.threshold = threshold
        self.timeout = timeout
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    async def is_available(self) -> bool:
        """Check if circuit allows requests."""
        if not self.state.is_open:
            return True

        # Check if timeout has passed
        if time.time() - self.state.opened_at >= self.timeout:
            async with self._lock:
                # Half-open state - allow one request through
                self.state.is_open = False
                self.state.failures = 0
                logger.info("Circuit breaker closed, allowing requests")
            return True

        return False

    async def record_success(self):
        """Record successful operation."""
        async with self._lock:
            self.state.failures = 0
            self.state.is_open = False

    async def record_failure(self):
        """Record failed operation."""
        async with self._lock:
            self.state.failures += 1
            self.state.last_failure = time.time()

            if self.state.failures >= self.threshold:
                self.state.is_open = True
                self.state.opened_at = time.time()
                logger.warning(
                    f"Circuit breaker opened after {self.state.failures} failures. "
                    f"Will retry in {self.timeout} seconds."
                )


class RedisCache:
    """
    High-performance Redis cache with type-safe operations.

    Features:
    - Automatic LZ4/ZSTD compression for large values
    - Circuit breaker for resilience
    - Namespace isolation
    - Comprehensive statistics
    - Graceful degradation (returns None on errors)
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
    ):
        self.config = config or get_cache_config()
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._compressor = CacheCompressor(
            enabled=self.config.compression_enabled,
            threshold=self.config.compression_threshold,
        )
        self._circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout,
        ) if self.config.circuit_breaker_enabled else None
        self._stats = CacheStats()
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize Redis connection pool."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                self._pool = ConnectionPool.from_url(
                    self.config.redis_url,
                    max_connections=self.config.redis_max_connections,
                    socket_timeout=self.config.redis_socket_timeout,
                    socket_connect_timeout=self.config.redis_connect_timeout,
                    decode_responses=False,  # We handle bytes directly
                )
                self._redis = Redis(connection_pool=self._pool)

                # Test connection
                await self._redis.ping()
                self._initialized = True
                logger.info(f"Redis cache initialized: {self.config.redis_url}")

            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                self._initialized = False
                raise

    async def close(self):
        """Close Redis connection pool."""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
        self._initialized = False
        logger.info("Redis cache closed")

    @asynccontextmanager
    async def _with_circuit_breaker(self):
        """Context manager for circuit breaker pattern."""
        if self._circuit_breaker and not await self._circuit_breaker.is_available():
            raise RedisConnectionError("Circuit breaker is open")

        try:
            yield
            if self._circuit_breaker:
                await self._circuit_breaker.record_success()
        except (RedisError, RedisConnectionError) as e:
            if self._circuit_breaker:
                await self._circuit_breaker.record_failure()
            raise

    def _make_key(self, *parts: str) -> str:
        """Create namespaced cache key."""
        return f"{self.config.namespace}:{':'.join(str(p) for p in parts)}"

    def _hash_params(self, params: Dict) -> str:
        """Create hash of parameters for cache key."""
        import json
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]

    # =========================================================================
    # Core Operations
    # =========================================================================

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Returns None if:
        - Key doesn't exist
        - Cache is disabled
        - Redis is unavailable
        - Deserialization fails
        """
        if not self.config.enabled:
            return None

        if not self._initialized:
            await self.initialize()

        start_time = time.time()

        try:
            async with self._with_circuit_breaker():
                data = await self._redis.get(key)

            elapsed = time.time() - start_time
            self._stats.record_latency(elapsed)

            if data is None:
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            self._stats.bytes_read += len(data)

            # Decompress and deserialize
            decompressed = self._compressor.decompress(data)
            return deserialize_value(decompressed)

        except RedisConnectionError:
            self._stats.errors += 1
            logger.warning("Redis unavailable, returning None")
            return None
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache get error for {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """
        Set value in cache with optional TTL.

        Returns True on success, False on failure.
        """
        if not self.config.enabled:
            return False

        if not self._initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Serialize
            serialized = serialize_value(value)
            original_size = len(serialized)

            # Compress
            compressed, stats = self._compressor.compress(serialized)

            if stats:
                self._stats.bytes_saved_compression += (
                    stats.original_size - stats.compressed_size
                )

            async with self._with_circuit_breaker():
                if ttl:
                    await self._redis.setex(key, ttl, compressed)
                else:
                    await self._redis.set(key, compressed)

            elapsed = time.time() - start_time
            self._stats.record_latency(elapsed)
            self._stats.bytes_written += len(compressed)

            return True

        except RedisConnectionError:
            self._stats.errors += 1
            logger.warning("Redis unavailable, cache set failed")
            return False
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self.config.enabled or not self._initialized:
            return False

        try:
            async with self._with_circuit_breaker():
                await self._redis.delete(key)
            return True
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns count deleted."""
        if not self.config.enabled or not self._initialized:
            return 0

        try:
            async with self._with_circuit_breaker():
                keys = []
                async for key in self._redis.scan_iter(match=pattern, count=100):
                    keys.append(key)

                if keys:
                    deleted = await self._redis.delete(*keys)
                    logger.info(f"Deleted {deleted} keys matching {pattern}")
                    return deleted

            return 0

        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.config.enabled or not self._initialized:
            return False

        try:
            async with self._with_circuit_breaker():
                return await self._redis.exists(key) > 0
        except Exception:
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL in seconds for a key. Returns -1 if no TTL, -2 if not exists."""
        if not self.config.enabled or not self._initialized:
            return -2

        try:
            async with self._with_circuit_breaker():
                return await self._redis.ttl(key)
        except Exception:
            return -2

    # =========================================================================
    # Dashboard Cache Operations
    # =========================================================================

    def dashboard_key(
        self,
        domain_id: str,
        endpoint: str,
        analysis_id: Optional[str] = None,
    ) -> str:
        """Generate dashboard cache key."""
        parts = ["dashboard", domain_id, endpoint]
        if analysis_id:
            parts.append(analysis_id)
        return self._make_key(*parts)

    async def get_dashboard(
        self,
        domain_id: str,
        endpoint: str,
        analysis_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Get cached dashboard data."""
        key = self.dashboard_key(domain_id, endpoint, analysis_id)
        return await self.get(key)

    async def set_dashboard(
        self,
        domain_id: str,
        endpoint: str,
        data: Dict,
        analysis_id: Optional[str] = None,
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """Set dashboard data in cache."""
        key = self.dashboard_key(domain_id, endpoint, analysis_id)
        if ttl is None:
            ttl = CacheTTL.for_endpoint(endpoint)
        return await self.set(key, data, ttl)

    async def get_dashboard_bundle(
        self,
        domain_id: str,
        analysis_id: str,
    ) -> Optional[Dict]:
        """Get cached dashboard bundle (all components)."""
        key = self.dashboard_key(domain_id, "bundle", analysis_id)
        return await self.get(key)

    async def set_dashboard_bundle(
        self,
        domain_id: str,
        analysis_id: str,
        data: Dict,
    ) -> bool:
        """Set dashboard bundle in cache."""
        key = self.dashboard_key(domain_id, "bundle", analysis_id)
        return await self.set(key, data, CacheTTL.DASHBOARD_BUNDLE)

    # =========================================================================
    # Keywords Cache Operations
    # =========================================================================

    def keywords_key(
        self,
        domain_id: str,
        analysis_id: str,
        cursor: Optional[str] = None,
        filters: Optional[Dict] = None,
    ) -> str:
        """Generate keywords cache key."""
        parts = ["keywords", domain_id, analysis_id]
        if cursor:
            parts.append(f"cursor:{cursor}")
        if filters:
            parts.append(f"filters:{self._hash_params(filters)}")
        return self._make_key(*parts)

    async def get_keywords_page(
        self,
        domain_id: str,
        analysis_id: str,
        cursor: Optional[str] = None,
        filters: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Get cached keywords page."""
        key = self.keywords_key(domain_id, analysis_id, cursor, filters)
        return await self.get(key)

    async def set_keywords_page(
        self,
        domain_id: str,
        analysis_id: str,
        data: Dict,
        cursor: Optional[str] = None,
        filters: Optional[Dict] = None,
    ) -> bool:
        """Set keywords page in cache."""
        key = self.keywords_key(domain_id, analysis_id, cursor, filters)
        return await self.set(key, data, CacheTTL.KEYWORDS_PAGE)

    # =========================================================================
    # Cache Invalidation
    # =========================================================================

    async def invalidate_domain(self, domain_id: str) -> int:
        """Invalidate all cache for a domain."""
        pattern = self._make_key("*", domain_id, "*")
        count = await self.delete_pattern(pattern)
        logger.info(f"Invalidated {count} cache entries for domain: {domain_id}")
        return count

    async def invalidate_analysis(self, analysis_id: str) -> int:
        """Invalidate all cache for an analysis."""
        pattern = self._make_key("*", "*", analysis_id, "*")
        count = await self.delete_pattern(pattern)
        logger.info(f"Invalidated {count} cache entries for analysis: {analysis_id}")
        return count

    async def invalidate_dashboard(self, domain_id: str) -> int:
        """Invalidate dashboard cache for a domain."""
        pattern = self._make_key("dashboard", domain_id, "*")
        count = await self.delete_pattern(pattern)
        logger.info(f"Invalidated {count} dashboard cache entries for domain: {domain_id}")
        return count

    async def invalidate_keywords(self, domain_id: str) -> int:
        """Invalidate keywords cache for a domain."""
        pattern = self._make_key("keywords", domain_id, "*")
        count = await self.delete_pattern(pattern)
        logger.info(f"Invalidated {count} keywords cache entries for domain: {domain_id}")
        return count

    # =========================================================================
    # Statistics and Health
    # =========================================================================

    async def get_info(self) -> Dict:
        """Get Redis server info."""
        if not self._initialized:
            return {}

        try:
            async with self._with_circuit_breaker():
                info = await self._redis.info()
                memory = await self._redis.info("memory")
                return {
                    "connected": True,
                    "redis_version": info.get("redis_version"),
                    "used_memory_mb": memory.get("used_memory", 0) / 1024 / 1024,
                    "used_memory_peak_mb": memory.get("used_memory_peak", 0) / 1024 / 1024,
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "enabled": self.config.enabled,
            "initialized": self._initialized,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "errors": self._stats.errors,
            "hit_rate_percent": round(self._stats.hit_rate * 100, 2),
            "avg_latency_ms": round(self._stats.avg_latency_ms, 2),
            "bytes_written": self._stats.bytes_written,
            "bytes_read": self._stats.bytes_read,
            "bytes_saved_compression": self._stats.bytes_saved_compression,
            "circuit_breaker_open": (
                self._circuit_breaker.state.is_open
                if self._circuit_breaker else False
            ),
        }

    async def health_check(self) -> Dict:
        """Perform health check."""
        if not self.config.enabled:
            return {"healthy": True, "status": "disabled"}

        try:
            if not self._initialized:
                await self.initialize()

            start = time.time()
            async with self._with_circuit_breaker():
                await self._redis.ping()
            latency_ms = (time.time() - start) * 1000

            return {
                "healthy": True,
                "status": "connected",
                "latency_ms": round(latency_ms, 2),
                "stats": self.get_stats(),
            }

        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "stats": self.get_stats(),
            }


# Singleton instance
_redis_cache: Optional[RedisCache] = None
_redis_cache_lock = asyncio.Lock()


async def get_redis_cache() -> RedisCache:
    """Get singleton Redis cache instance."""
    global _redis_cache

    if _redis_cache is not None:
        return _redis_cache

    async with _redis_cache_lock:
        if _redis_cache is not None:
            return _redis_cache

        _redis_cache = RedisCache()
        await _redis_cache.initialize()
        return _redis_cache


async def close_redis_cache():
    """Close singleton Redis cache instance."""
    global _redis_cache

    if _redis_cache:
        await _redis_cache.close()
        _redis_cache = None

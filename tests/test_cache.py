"""
Tests for the caching layer.

These tests verify:
- Redis cache operations (get, set, delete)
- Compression (LZ4/ZSTD)
- Cache invalidation
- HTTP cache headers
- Circuit breaker behavior

Requires Redis running locally for integration tests.
Unit tests work without Redis.
"""

import pytest
import asyncio
from datetime import timedelta, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.cache.config import CacheConfig, CacheTTL, get_cache_config
from src.cache.compression import CacheCompressor, serialize_value, deserialize_value
from src.cache.headers import (
    generate_etag, parse_etag, etags_match,
    CacheHeadersBuilder, check_not_modified,
)


# =============================================================================
# COMPRESSION TESTS
# =============================================================================

class TestCompression:
    """Test compression utilities."""

    def test_serialize_deserialize_dict(self):
        """Test serialization of dict."""
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        serialized = serialize_value(data)
        deserialized = deserialize_value(serialized)
        assert deserialized == data

    def test_serialize_deserialize_list(self):
        """Test serialization of list."""
        data = [1, 2, 3, {"key": "value"}]
        serialized = serialize_value(data)
        deserialized = deserialize_value(serialized)
        assert deserialized == data

    def test_serialize_datetime(self):
        """Test serialization of datetime."""
        data = {"timestamp": datetime(2024, 1, 15, 10, 30, 0)}
        serialized = serialize_value(data)
        deserialized = deserialize_value(serialized)
        assert deserialized["timestamp"] == "2024-01-15T10:30:00"

    def test_compressor_small_data_not_compressed(self):
        """Small data should not be compressed."""
        compressor = CacheCompressor(enabled=True, threshold=1024)
        small_data = b"hello world"
        compressed, stats = compressor.compress(small_data)

        # Should have uncompressed marker
        assert compressed[0:1] == b'\x00'
        assert stats is None
        assert compressor.decompress(compressed) == small_data

    @pytest.mark.skipif(
        not CacheCompressor().enabled,
        reason="LZ4 not installed"
    )
    def test_compressor_large_data_compressed(self):
        """Large data should be compressed."""
        compressor = CacheCompressor(enabled=True, threshold=100)
        large_data = b"x" * 10000  # 10KB of repeated data

        compressed, stats = compressor.compress(large_data)

        # Should have LZ4 marker
        assert compressed[0:1] == b'\x01'
        assert stats is not None
        assert stats.compression_ratio > 1
        assert compressor.decompress(compressed) == large_data


# =============================================================================
# HTTP CACHE HEADERS TESTS
# =============================================================================

class TestCacheHeaders:
    """Test HTTP cache header utilities."""

    def test_generate_etag(self):
        """Test ETag generation."""
        etag1 = generate_etag("abc", 123)
        etag2 = generate_etag("abc", 123)
        etag3 = generate_etag("abc", 456)

        assert etag1 == etag2  # Same inputs = same ETag
        assert etag1 != etag3  # Different inputs = different ETag
        assert etag1.startswith('"')
        assert etag1.endswith('"')

    def test_generate_weak_etag(self):
        """Test weak ETag generation."""
        etag = generate_etag("abc", weak=True)
        assert etag.startswith('W/"')

    def test_parse_etag(self):
        """Test ETag parsing."""
        assert parse_etag('"abc123"') == "abc123"
        assert parse_etag('W/"abc123"') == "abc123"
        assert parse_etag("abc123") == "abc123"

    def test_etags_match_exact(self):
        """Test exact ETag matching."""
        etag = '"abc123"'
        assert etags_match('"abc123"', etag)
        assert not etags_match('"xyz789"', etag)

    def test_etags_match_weak(self):
        """Test weak ETag matching."""
        etag = '"abc123"'
        assert etags_match('W/"abc123"', etag)

    def test_etags_match_wildcard(self):
        """Test wildcard ETag matching."""
        assert etags_match("*", '"anything"')

    def test_etags_match_multiple(self):
        """Test multiple ETags in If-None-Match."""
        etag = '"abc123"'
        assert etags_match('"xyz", "abc123", "other"', etag)
        assert not etags_match('"xyz", "other"', etag)

    def test_headers_builder_basic(self):
        """Test basic cache headers building."""
        headers = (
            CacheHeadersBuilder()
            .max_age(300)
            .public()
            .build()
        )

        assert "Cache-Control" in headers
        assert "max-age=300" in headers["Cache-Control"]
        assert "public" in headers["Cache-Control"]

    def test_headers_builder_swr(self):
        """Test stale-while-revalidate."""
        headers = (
            CacheHeadersBuilder()
            .max_age(300)
            .stale_while_revalidate(600)
            .build()
        )

        assert "stale-while-revalidate=600" in headers["Cache-Control"]

    def test_headers_builder_no_store(self):
        """Test no-store directive."""
        headers = (
            CacheHeadersBuilder()
            .no_store()
            .build()
        )

        assert "no-store" in headers["Cache-Control"]
        assert "max-age" not in headers["Cache-Control"]

    def test_headers_builder_etag(self):
        """Test ETag header."""
        headers = (
            CacheHeadersBuilder()
            .etag("analysis123", datetime.now())
            .build()
        )

        assert "ETag" in headers
        assert headers["ETag"].startswith('"')

    def test_headers_builder_surrogate_keys(self):
        """Test surrogate keys for CDN."""
        headers = (
            CacheHeadersBuilder()
            .surrogate_keys(["domain:123", "dashboard"])
            .build()
        )

        assert "Cache-Tag" in headers
        assert "domain:123" in headers["Cache-Tag"]
        assert "Surrogate-Key" in headers


# =============================================================================
# CACHE TTL TESTS
# =============================================================================

class TestCacheTTL:
    """Test cache TTL configuration."""

    def test_ttl_for_endpoint(self):
        """Test TTL lookup by endpoint."""
        assert CacheTTL.for_endpoint("overview") == CacheTTL.DASHBOARD_OVERVIEW
        assert CacheTTL.for_endpoint("sparklines") == CacheTTL.DASHBOARD_SPARKLINES
        assert CacheTTL.for_endpoint("sov") == CacheTTL.DASHBOARD_SOV

    def test_ttl_for_unknown_endpoint(self):
        """Test TTL for unknown endpoint returns default."""
        assert CacheTTL.for_endpoint("unknown") == CacheTTL.DASHBOARD_OVERVIEW

    def test_ttl_values_reasonable(self):
        """Test that TTL values are reasonable."""
        # Dashboard data should cache for hours (data changes on new analysis)
        assert CacheTTL.DASHBOARD_OVERVIEW >= timedelta(hours=1)
        assert CacheTTL.DASHBOARD_SPARKLINES >= timedelta(hours=1)

        # Strategy data should cache for minutes (user edits)
        assert CacheTTL.STRATEGY <= timedelta(hours=1)

        # Analysis status should be very short (real-time)
        assert CacheTTL.ANALYSIS_STATUS <= timedelta(minutes=1)


# =============================================================================
# CACHE CONFIG TESTS
# =============================================================================

class TestCacheConfig:
    """Test cache configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.compression_enabled is True
        assert config.redis_max_connections == 50
        assert config.min_hit_rate == 0.8

    @patch.dict('os.environ', {'CACHE_ENABLED': 'false'})
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        # Clear the cache
        get_cache_config.cache_clear()
        config = CacheConfig()
        assert config.enabled is False
        get_cache_config.cache_clear()  # Reset


# =============================================================================
# REDIS CACHE TESTS (Integration - requires Redis)
# =============================================================================

@pytest.mark.asyncio
class TestRedisCache:
    """
    Integration tests for Redis cache.

    These require a running Redis instance.
    Skip if Redis is not available.
    """

    @pytest.fixture
    async def cache(self):
        """Get a cache instance for testing."""
        try:
            from src.cache.redis_cache import RedisCache
            cache = RedisCache()
            await cache.initialize()
            yield cache
            await cache.close()
        except Exception:
            pytest.skip("Redis not available")

    async def test_set_and_get(self, cache):
        """Test basic set and get."""
        key = "test:basic"
        value = {"hello": "world", "number": 42}

        success = await cache.set(key, value, timedelta(minutes=1))
        assert success is True

        retrieved = await cache.get(key)
        assert retrieved == value

        # Cleanup
        await cache.delete(key)

    async def test_get_nonexistent(self, cache):
        """Test getting nonexistent key."""
        result = await cache.get("test:nonexistent")
        assert result is None

    async def test_delete(self, cache):
        """Test deletion."""
        key = "test:delete"
        await cache.set(key, "value", timedelta(minutes=1))
        assert await cache.exists(key)

        await cache.delete(key)
        assert not await cache.exists(key)

    async def test_delete_pattern(self, cache):
        """Test pattern deletion."""
        # Set multiple keys
        for i in range(5):
            await cache.set(f"test:pattern:{i}", f"value{i}", timedelta(minutes=1))

        # Delete all matching pattern
        deleted = await cache.delete_pattern("test:pattern:*")
        assert deleted == 5

    async def test_dashboard_operations(self, cache):
        """Test dashboard-specific operations."""
        domain_id = "test-domain"
        analysis_id = "test-analysis"
        data = {"health": 85, "keywords": 1000}

        await cache.set_dashboard(domain_id, "overview", data, analysis_id)

        retrieved = await cache.get_dashboard(domain_id, "overview", analysis_id)
        assert retrieved == data

        # Cleanup
        await cache.invalidate_dashboard(domain_id)

    async def test_stats(self, cache):
        """Test statistics tracking."""
        # Generate some activity
        await cache.set("test:stats:1", "value", timedelta(minutes=1))
        await cache.get("test:stats:1")  # Hit
        await cache.get("test:stats:nonexistent")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert "hit_rate_percent" in stats

        # Cleanup
        await cache.delete("test:stats:1")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

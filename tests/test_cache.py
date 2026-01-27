"""
Tests for the PostgreSQL caching layer.

These tests verify:
- PostgreSQL cache operations (get, set, delete)
- Cache invalidation
- HTTP cache headers
- Config and TTL settings

All tests use a mock database session.
"""

import pytest
from datetime import timedelta, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.cache.config import CacheConfig, CacheTTL, get_cache_config
from src.cache.headers import (
    generate_etag, parse_etag, etags_match,
    CacheHeadersBuilder, check_not_modified,
)


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
        assert config.precomputation_enabled is True
        assert config.http_cache_enabled is True

    @patch.dict('os.environ', {'CACHE_ENABLED': 'false'})
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        # Clear the cache
        get_cache_config.cache_clear()
        config = CacheConfig()
        assert config.enabled is False
        get_cache_config.cache_clear()  # Reset


# =============================================================================
# POSTGRES CACHE TESTS
# =============================================================================

class TestPostgresCache:
    """Test PostgreSQL cache operations."""

    def test_cache_stats(self):
        """Test cache statistics."""
        from src.cache.postgres_cache import PostgresCache

        # Create a mock session
        mock_db = MagicMock()
        cache = PostgresCache(mock_db)

        stats = cache.get_stats()
        assert stats["enabled"] is True
        assert stats["backend"] == "postgresql"
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate_percent" in stats

    def test_health_check_success(self):
        """Test health check with working database."""
        from src.cache.postgres_cache import PostgresCache

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 10

        cache = PostgresCache(mock_db)
        health = cache.health_check()

        assert health["healthy"] is True
        assert health["backend"] == "postgresql"
        assert health["cached_entries"] == 10

    def test_health_check_failure(self):
        """Test health check with database error."""
        from src.cache.postgres_cache import PostgresCache

        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database error")

        cache = PostgresCache(mock_db)
        health = cache.health_check()

        assert health["healthy"] is False
        assert "error" in health

    def test_get_dashboard_hit(self):
        """Test cache hit."""
        from src.cache.postgres_cache import PostgresCache
        from src.database.models import PrecomputedDashboard

        mock_db = MagicMock()
        mock_record = MagicMock()
        mock_record.data = {"health": 85, "keywords": 1000}
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_record

        cache = PostgresCache(mock_db)
        result = cache.get_dashboard("domain-123", "overview")

        assert result == {"health": 85, "keywords": 1000}
        assert cache._stats["hits"] == 1

    def test_get_dashboard_miss(self):
        """Test cache miss."""
        from src.cache.postgres_cache import PostgresCache

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        cache = PostgresCache(mock_db)
        result = cache.get_dashboard("domain-123", "overview")

        assert result is None
        assert cache._stats["misses"] == 1

    def test_set_dashboard(self):
        """Test cache set."""
        from src.cache.postgres_cache import PostgresCache

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        cache = PostgresCache(mock_db)
        success = cache.set_dashboard(
            "domain-123",
            "overview",
            {"health": 85},
            "analysis-456"
        )

        assert success is True
        assert cache._stats["writes"] == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_invalidate_domain(self):
        """Test domain invalidation."""
        from src.cache.postgres_cache import PostgresCache

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.update.return_value = 5

        cache = PostgresCache(mock_db)
        count = cache.invalidate_domain("domain-123")

        assert count == 5
        mock_db.commit.assert_called_once()


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

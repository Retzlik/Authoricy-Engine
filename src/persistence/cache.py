"""
Analysis Cache

Caches DataForSEO API responses to reduce costs and improve performance.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    data: Dict
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    cost_saved: float = 0.0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "hit_count": self.hit_count,
            "cost_saved": self.cost_saved,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            hit_count=data.get("hit_count", 0),
            cost_saved=data.get("cost_saved", 0.0),
        )


class AnalysisCache:
    """
    Cache for DataForSEO API responses.

    Reduces API costs by caching responses for a configurable duration.
    """

    # Default TTL by data type (hours)
    DEFAULT_TTLS = {
        "domain_overview": 24,      # Domain metrics change slowly
        "historical": 168,          # Historical data is stable
        "backlinks": 24,            # Backlinks change moderately
        "keywords": 12,             # Keywords more volatile
        "serp": 6,                  # SERP data changes faster
        "technical": 24,            # Technical audits fairly stable
        "trends": 12,               # Trends update regularly
        "default": 12,              # Default 12 hours
    }

    # Approximate costs per endpoint (USD)
    ENDPOINT_COSTS = {
        "domain_rank_overview": 0.05,
        "ranked_keywords": 0.15,
        "backlinks": 0.10,
        "serp": 0.02,
        "lighthouse": 0.10,
        "default": 0.05,
    }

    def __init__(
        self,
        cache_path: Optional[str] = None,
        enabled: bool = True,
        max_size_mb: int = 500
    ):
        """
        Initialize cache.

        Args:
            cache_path: Directory for cache files.
                       Defaults to ~/.authoricy/cache/
            enabled: Whether caching is enabled
            max_size_mb: Maximum cache size in MB
        """
        if cache_path is None:
            cache_path = os.getenv(
                "AUTHORICY_CACHE_PATH",
                str(Path.home() / ".authoricy" / "cache")
            )

        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self.max_size_mb = max_size_mb

        # Stats
        self._hits = 0
        self._misses = 0
        self._cost_saved = 0.0

        logger.info(f"AnalysisCache initialized at {self.cache_path} (enabled={enabled})")

    def _generate_key(
        self,
        endpoint: str,
        domain: str,
        market: str,
        language: str,
        params: Optional[Dict] = None
    ) -> str:
        """Generate cache key from request parameters."""
        key_parts = [endpoint, domain, market, language]

        if params:
            # Sort params for consistent keys
            param_str = json.dumps(params, sort_keys=True)
            key_parts.append(param_str)

        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def _get_ttl(self, endpoint: str) -> int:
        """Get TTL in hours for endpoint type."""
        for key, ttl in self.DEFAULT_TTLS.items():
            if key in endpoint.lower():
                return ttl
        return self.DEFAULT_TTLS["default"]

    def _get_cost(self, endpoint: str) -> float:
        """Get approximate cost for endpoint."""
        for key, cost in self.ENDPOINT_COSTS.items():
            if key in endpoint.lower():
                return cost
        return self.ENDPOINT_COSTS["default"]

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Use first 2 chars for subdirectory to avoid too many files in one dir
        subdir = key[:2]
        return self.cache_path / subdir / f"{key}.json"

    def get(
        self,
        endpoint: str,
        domain: str,
        market: str,
        language: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Get cached response.

        Args:
            endpoint: API endpoint
            domain: Target domain
            market: Location name
            language: Language code
            params: Additional parameters

        Returns:
            Cached data or None if not found/expired
        """
        if not self.enabled:
            return None

        key = self._generate_key(endpoint, domain, market, language, params)
        path = self._get_cache_path(key)

        if not path.exists():
            self._misses += 1
            return None

        try:
            with open(path, "r") as f:
                entry = CacheEntry.from_dict(json.load(f))

            if entry.is_expired():
                # Clean up expired entry
                path.unlink()
                self._misses += 1
                return None

            # Update hit count
            entry.hit_count += 1
            cost = self._get_cost(endpoint)
            entry.cost_saved += cost
            self._cost_saved += cost

            with open(path, "w") as f:
                json.dump(entry.to_dict(), f)

            self._hits += 1
            logger.debug(f"Cache HIT for {endpoint} ({domain})")
            return entry.data

        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            self._misses += 1
            return None

    def set(
        self,
        endpoint: str,
        domain: str,
        market: str,
        language: str,
        data: Dict,
        params: Optional[Dict] = None,
        ttl_hours: Optional[int] = None
    ):
        """
        Cache a response.

        Args:
            endpoint: API endpoint
            domain: Target domain
            market: Location name
            language: Language code
            data: Response data to cache
            params: Additional parameters
            ttl_hours: Custom TTL in hours (overrides default)
        """
        if not self.enabled:
            return

        key = self._generate_key(endpoint, domain, market, language, params)
        path = self._get_cache_path(key)

        ttl = ttl_hours or self._get_ttl(endpoint)

        entry = CacheEntry(
            key=key,
            data=data,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=ttl),
        )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(entry.to_dict(), f)

            logger.debug(f"Cached {endpoint} ({domain}) for {ttl}h")

        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def invalidate(
        self,
        endpoint: Optional[str] = None,
        domain: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            endpoint: Invalidate entries for this endpoint
            domain: Invalidate entries for this domain
        """
        if not endpoint and not domain:
            # Clear all
            for subdir in self.cache_path.iterdir():
                if subdir.is_dir():
                    for file in subdir.glob("*.json"):
                        file.unlink()
            logger.info("Cleared entire cache")
            return

        # Selective invalidation requires scanning files
        count = 0
        for subdir in self.cache_path.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.json"):
                    try:
                        with open(file, "r") as f:
                            entry = json.load(f)

                        # Check if should invalidate
                        should_invalidate = False
                        if endpoint and endpoint in entry.get("key", ""):
                            should_invalidate = True
                        # Note: domain matching would require storing domain in entry

                        if should_invalidate:
                            file.unlink()
                            count += 1

                    except Exception:
                        pass

        logger.info(f"Invalidated {count} cache entries")

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        count = 0
        for subdir in self.cache_path.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.json"):
                    try:
                        with open(file, "r") as f:
                            entry = CacheEntry.from_dict(json.load(f))

                        if entry.is_expired():
                            file.unlink()
                            count += 1

                    except Exception:
                        # Remove invalid files
                        file.unlink()
                        count += 1

        logger.info(f"Cleaned up {count} expired cache entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests else 0

        # Calculate cache size
        total_size = 0
        entry_count = 0
        for subdir in self.cache_path.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.json"):
                    total_size += file.stat().st_size
                    entry_count += 1

        return {
            "enabled": self.enabled,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 1),
            "cost_saved_usd": round(self._cost_saved, 2),
            "entry_count": entry_count,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.max_size_mb,
        }

    def enforce_size_limit(self):
        """
        Enforce maximum cache size by removing oldest entries.
        """
        # Calculate current size
        entries = []
        total_size = 0

        for subdir in self.cache_path.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.json"):
                    size = file.stat().st_size
                    mtime = file.stat().st_mtime
                    entries.append((file, size, mtime))
                    total_size += size

        max_bytes = self.max_size_mb * 1024 * 1024

        if total_size <= max_bytes:
            return

        # Sort by modification time (oldest first)
        entries.sort(key=lambda x: x[2])

        # Remove oldest until under limit
        removed = 0
        for file, size, _ in entries:
            if total_size <= max_bytes:
                break
            file.unlink()
            total_size -= size
            removed += 1

        logger.info(f"Removed {removed} cache entries to enforce size limit")

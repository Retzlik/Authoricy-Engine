# Authoricy Platform Caching Strategy

**Version:** 1.0
**Date:** January 2026
**Goal:** Sub-second dashboard loads, 60fps table scrolling, minimal API costs

---

## Executive Summary

The current approach of "compute everything on demand" will not scale. With 8,000+ keywords per domain, sparklines needing 30-day history, and AI summaries requiring expensive LLM calls, we need a multi-layered caching strategy that:

1. **Precomputes expensive data** after analysis completes
2. **Serves from edge** for global performance
3. **Invalidates intelligently** only when data actually changes
4. **Coordinates with frontend** via proper HTTP caching headers

**Target Metrics:**
| Metric | Current (Estimated) | Target |
|--------|---------------------|--------|
| Dashboard initial load | 2-5 seconds | <500ms |
| Keywords table load (8K rows) | 1-3 seconds | <300ms |
| Sparkline data | 500ms-2s | <100ms |
| AI Summary generation | 5-15 seconds | <200ms (cached) |
| API costs per dashboard view | ~$0.05 | ~$0.001 |

---

## 1. Data Analysis: What Changes When?

### Change Frequency Matrix

| Data Type | Changes When | Typical Frequency | Size | Compute Cost |
|-----------|--------------|-------------------|------|--------------|
| Domain metrics | New analysis | Weekly-Monthly | 1 KB | Low |
| Keywords list | New analysis | Weekly-Monthly | 500 KB - 2 MB | Low |
| Position history | New analysis | Weekly-Monthly | 2-10 MB | Medium |
| Sparklines | New analysis | Weekly-Monthly | 500 KB | Medium (aggregation) |
| Share of Voice | New analysis | Weekly-Monthly | 10 KB | Medium |
| Battleground | New analysis | Weekly-Monthly | 50 KB | High (computation) |
| Topical clusters | New analysis | Weekly-Monthly | 100 KB | High (AI) |
| Content audit | New analysis | Weekly-Monthly | 100 KB | High |
| AI Summary | New analysis | Weekly-Monthly | 5 KB | Very High (LLM) |
| Strategy data | User edits | Minutes-Hours | 50 KB | Low |

**Key Insight:** Most dashboard data only changes when a new analysis runs. This happens weekly or monthly. We're re-computing data that hasn't changed on every page load.

---

## 2. Multi-Layer Caching Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    USER BROWSER                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 1: Browser Cache (React Query)                                          │  │
│  │  • Stale-while-revalidate pattern                                             │  │
│  │  • Optimistic updates                                                          │  │
│  │  • Local persistence (IndexedDB for large datasets)                           │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    CDN EDGE                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 2: Edge Cache (Cloudflare/Vercel)                                       │  │
│  │  • Static data served from edge (50-200ms globally)                           │  │
│  │  • Cache-Control headers respected                                             │  │
│  │  • Surrogate keys for selective purging                                        │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  API SERVER                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 3: Application Cache (Redis)                                            │  │
│  │  • Hot data in memory (microsecond access)                                    │  │
│  │  • Precomputed aggregations                                                    │  │
│  │  • Session data                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 4: Precomputed Cache (PostgreSQL + Redis)                               │  │
│  │  • Materialized views for aggregations                                        │  │
│  │  • Denormalized dashboard tables                                               │  │
│  │  • AI summary storage                                                          │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  DATABASE                                            │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 5: Source of Truth                                                       │  │
│  │  • Raw analysis data                                                           │  │
│  │  • Full keyword records                                                         │  │
│  │  • Position history                                                             │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Implementation

### Layer 1: Browser Cache (React Query)

The frontend uses TanStack Query. Configure it properly:

```typescript
// src/lib/query-client.ts

import { QueryClient } from '@tanstack/react-query';
import { persistQueryClient } from '@tanstack/react-query-persist-client';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';
import { createIDBPersister } from './idb-persister';

// Different stale times based on data type
export const STALE_TIMES = {
  // Dashboard data - stable after analysis
  dashboardOverview: 5 * 60 * 1000,      // 5 minutes (then background refresh)
  keywords: 10 * 60 * 1000,               // 10 minutes
  sparklines: 15 * 60 * 1000,             // 15 minutes
  shareOfVoice: 30 * 60 * 1000,           // 30 minutes
  battleground: 30 * 60 * 1000,           // 30 minutes
  aiSummary: 60 * 60 * 1000,              // 1 hour (expensive to regenerate)

  // Strategy data - user edits, more volatile
  strategy: 1 * 60 * 1000,                // 1 minute
  threads: 1 * 60 * 1000,                 // 1 minute

  // Analysis status - real-time
  analysisStatus: 0,                       // Never stale, always refetch
};

// GC times - how long to keep in memory after unmount
export const GC_TIMES = {
  dashboardOverview: 30 * 60 * 1000,      // 30 minutes
  keywords: 60 * 60 * 1000,               // 1 hour (large, keep longer)
  sparklines: 60 * 60 * 1000,             // 1 hour
  default: 10 * 60 * 1000,                // 10 minutes
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,           // Default 5 minutes
      gcTime: 30 * 60 * 1000,             // Default 30 minutes GC
      refetchOnWindowFocus: false,         // Don't refetch on tab switch
      refetchOnReconnect: true,            // Refetch on reconnect
      retry: 3,                            // Retry failed requests
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

// Persist large datasets to IndexedDB
const idbPersister = createIDBPersister({
  dbName: 'authoricy-cache',
  storeName: 'query-cache',
});

persistQueryClient({
  queryClient,
  persister: idbPersister,
  maxAge: 24 * 60 * 60 * 1000,            // 24 hours max persistence
  dehydrateOptions: {
    shouldDehydrateQuery: (query) => {
      // Only persist dashboard and keyword data
      const key = query.queryKey[0] as string;
      return ['dashboard', 'keywords', 'sparklines'].some(k => key?.includes(k));
    },
  },
});


// Query key factory for consistent cache keys
export const queryKeys = {
  domains: {
    all: ['domains'] as const,
    detail: (id: string) => ['domains', id] as const,
  },
  dashboard: {
    overview: (domainId: string) => ['dashboard', domainId, 'overview'] as const,
    sparklines: (domainId: string) => ['dashboard', domainId, 'sparklines'] as const,
    sov: (domainId: string) => ['dashboard', domainId, 'sov'] as const,
    battleground: (domainId: string) => ['dashboard', domainId, 'battleground'] as const,
    clusters: (domainId: string) => ['dashboard', domainId, 'clusters'] as const,
    contentAudit: (domainId: string) => ['dashboard', domainId, 'content-audit'] as const,
    aiSummary: (domainId: string) => ['dashboard', domainId, 'ai-summary'] as const,
  },
  keywords: {
    list: (domainId: string, filters?: object) =>
      ['keywords', domainId, filters] as const,
    detail: (keywordId: string) => ['keywords', 'detail', keywordId] as const,
  },
  strategies: {
    detail: (id: string) => ['strategies', id] as const,
    availableKeywords: (id: string, cursor?: string) =>
      ['strategies', id, 'available-keywords', cursor] as const,
  },
  analysis: {
    status: (id: string) => ['analysis', id, 'status'] as const,
  },
};


// Custom hooks with proper caching
export function useDashboardOverview(domainId: string) {
  return useQuery({
    queryKey: queryKeys.dashboard.overview(domainId),
    queryFn: () => fetchDashboardOverview(domainId),
    staleTime: STALE_TIMES.dashboardOverview,
    gcTime: GC_TIMES.dashboardOverview,
  });
}

export function useKeywords(domainId: string, filters?: KeywordFilters) {
  return useInfiniteQuery({
    queryKey: queryKeys.keywords.list(domainId, filters),
    queryFn: ({ pageParam }) => fetchKeywords(domainId, pageParam, filters),
    getNextPageParam: (lastPage) => lastPage.pagination.next_cursor,
    staleTime: STALE_TIMES.keywords,
    gcTime: GC_TIMES.keywords,
  });
}

export function useAnalysisStatus(analysisId: string) {
  return useQuery({
    queryKey: queryKeys.analysis.status(analysisId),
    queryFn: () => fetchAnalysisStatus(analysisId),
    staleTime: STALE_TIMES.analysisStatus,
    refetchInterval: 3000,                // Poll every 3 seconds
    enabled: !!analysisId,
  });
}
```

#### IndexedDB Persister for Large Datasets

```typescript
// src/lib/idb-persister.ts

import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface CacheDB extends DBSchema {
  'query-cache': {
    key: string;
    value: {
      data: unknown;
      timestamp: number;
    };
  };
}

export function createIDBPersister(options: { dbName: string; storeName: string }) {
  let db: IDBPDatabase<CacheDB> | null = null;

  const getDB = async () => {
    if (!db) {
      db = await openDB<CacheDB>(options.dbName, 1, {
        upgrade(db) {
          db.createObjectStore(options.storeName);
        },
      });
    }
    return db;
  };

  return {
    persistClient: async (client: unknown) => {
      const db = await getDB();
      await db.put(options.storeName, {
        data: client,
        timestamp: Date.now(),
      }, 'tanstack-query');
    },
    restoreClient: async () => {
      const db = await getDB();
      const entry = await db.get(options.storeName, 'tanstack-query');
      return entry?.data;
    },
    removeClient: async () => {
      const db = await getDB();
      await db.delete(options.storeName, 'tanstack-query');
    },
  };
}
```

### Layer 2: Edge Cache (CDN)

Configure API responses with proper HTTP caching headers:

```python
# In api/dashboard.py - Add caching headers

from fastapi import Response
from datetime import datetime, timedelta


def add_cache_headers(
    response: Response,
    max_age: int,
    etag: str,
    last_modified: datetime,
    public: bool = True,
    surrogate_keys: list[str] = None,
):
    """
    Add comprehensive HTTP cache headers for CDN and browser caching.

    Args:
        response: FastAPI Response object
        max_age: Seconds the response can be cached
        etag: Entity tag for conditional requests
        last_modified: When the data was last changed
        public: Whether the response can be cached publicly
        surrogate_keys: Keys for selective cache purging (Cloudflare/Fastly)
    """
    cache_control = f"{'public' if public else 'private'}, max-age={max_age}"

    # Stale-while-revalidate: serve stale content while refreshing in background
    cache_control += f", stale-while-revalidate={max_age * 2}"

    response.headers["Cache-Control"] = cache_control
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Surrogate keys for CDN purging (Cloudflare, Fastly, Vercel)
    if surrogate_keys:
        response.headers["Surrogate-Key"] = " ".join(surrogate_keys)
        response.headers["Cache-Tag"] = ",".join(surrogate_keys)  # Cloudflare


def get_cache_config(endpoint: str, domain_id: str, analysis_id: str) -> dict:
    """
    Get cache configuration based on endpoint type.
    """
    configs = {
        "overview": {
            "max_age": 300,           # 5 minutes
            "surrogate_keys": [f"domain:{domain_id}", f"analysis:{analysis_id}", "dashboard"],
        },
        "sparklines": {
            "max_age": 900,           # 15 minutes
            "surrogate_keys": [f"domain:{domain_id}", f"analysis:{analysis_id}", "sparklines"],
        },
        "sov": {
            "max_age": 1800,          # 30 minutes
            "surrogate_keys": [f"domain:{domain_id}", f"analysis:{analysis_id}", "sov"],
        },
        "battleground": {
            "max_age": 1800,          # 30 minutes
            "surrogate_keys": [f"domain:{domain_id}", f"analysis:{analysis_id}", "battleground"],
        },
        "ai-summary": {
            "max_age": 3600,          # 1 hour
            "surrogate_keys": [f"domain:{domain_id}", f"analysis:{analysis_id}", "ai-summary"],
        },
        "keywords": {
            "max_age": 600,           # 10 minutes
            "surrogate_keys": [f"domain:{domain_id}", f"analysis:{analysis_id}", "keywords"],
        },
    }
    return configs.get(endpoint, {"max_age": 60, "surrogate_keys": []})


@router.get("/{domain_id}/overview")
async def get_dashboard_overview(
    domain_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
    if_none_match: Optional[str] = Header(None),
    if_modified_since: Optional[str] = Header(None),
):
    """Dashboard overview with proper caching."""

    # Get latest analysis
    analysis = get_latest_analysis(domain_id, db)
    if not analysis:
        raise HTTPException(404, "No analysis found")

    # Generate ETag from analysis ID and timestamp
    etag = f"{analysis.id}-{analysis.completed_at.timestamp()}"

    # Check if client has current version (304 Not Modified)
    if if_none_match and if_none_match.strip('"') == etag:
        response.status_code = 304
        return Response(status_code=304)

    # Get data (from precomputed cache if available)
    overview = await get_precomputed_overview(domain_id, analysis.id, db)

    # Add cache headers
    cache_config = get_cache_config("overview", str(domain_id), str(analysis.id))
    add_cache_headers(
        response=response,
        max_age=cache_config["max_age"],
        etag=etag,
        last_modified=analysis.completed_at,
        surrogate_keys=cache_config["surrogate_keys"],
    )

    return overview
```

### Layer 3: Application Cache (Redis)

```python
# src/cache/redis_cache.py

import json
import hashlib
from datetime import timedelta
from typing import Any, Optional, TypeVar, Generic
from redis.asyncio import Redis
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CacheConfig:
    """Cache TTL configuration by data type."""

    # Dashboard data (stable after analysis)
    DASHBOARD_OVERVIEW = timedelta(hours=1)
    DASHBOARD_SPARKLINES = timedelta(hours=2)
    DASHBOARD_SOV = timedelta(hours=4)
    DASHBOARD_BATTLEGROUND = timedelta(hours=4)
    DASHBOARD_CLUSTERS = timedelta(hours=6)
    DASHBOARD_CONTENT_AUDIT = timedelta(hours=6)
    DASHBOARD_AI_SUMMARY = timedelta(hours=12)

    # Keywords (large, cache longer)
    KEYWORDS_PAGE = timedelta(hours=2)
    KEYWORDS_FULL = timedelta(hours=6)

    # Precomputed data (until new analysis)
    PRECOMPUTED = timedelta(days=30)

    # Strategy data (user edits, shorter cache)
    STRATEGY = timedelta(minutes=5)

    # Greenfield SERP data
    SERP_RESULTS = timedelta(hours=24)
    COMPETITOR_KEYWORDS = timedelta(days=3)


class RedisCache:
    """
    Application-level Redis cache with type-safe serialization.
    """

    def __init__(self, redis: Redis, namespace: str = "authoricy"):
        self.redis = redis
        self.namespace = namespace

    def _make_key(self, *parts: str) -> str:
        """Create namespaced cache key."""
        return f"{self.namespace}:{':'.join(parts)}"

    def _hash_params(self, params: dict) -> str:
        """Create hash of parameters for cache key."""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:8]

    # =========================================================================
    # Generic Operations
    # =========================================================================

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta,
    ):
        """Set value in cache with TTL."""
        await self.redis.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str):
        """Delete key from cache."""
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)

    # =========================================================================
    # Dashboard Cache Operations
    # =========================================================================

    def _dashboard_key(self, domain_id: str, endpoint: str, analysis_id: str = None) -> str:
        if analysis_id:
            return self._make_key("dashboard", domain_id, analysis_id, endpoint)
        return self._make_key("dashboard", domain_id, endpoint)

    async def get_dashboard_overview(
        self,
        domain_id: str,
        analysis_id: str,
    ) -> Optional[dict]:
        key = self._dashboard_key(domain_id, "overview", analysis_id)
        return await self.get(key)

    async def set_dashboard_overview(
        self,
        domain_id: str,
        analysis_id: str,
        data: dict,
    ):
        key = self._dashboard_key(domain_id, "overview", analysis_id)
        await self.set(key, data, CacheConfig.DASHBOARD_OVERVIEW)

    async def get_sparklines(
        self,
        domain_id: str,
        analysis_id: str,
    ) -> Optional[dict]:
        key = self._dashboard_key(domain_id, "sparklines", analysis_id)
        return await self.get(key)

    async def set_sparklines(
        self,
        domain_id: str,
        analysis_id: str,
        data: dict,
    ):
        key = self._dashboard_key(domain_id, "sparklines", analysis_id)
        await self.set(key, data, CacheConfig.DASHBOARD_SPARKLINES)

    async def get_ai_summary(
        self,
        domain_id: str,
        analysis_id: str,
    ) -> Optional[dict]:
        key = self._dashboard_key(domain_id, "ai-summary", analysis_id)
        return await self.get(key)

    async def set_ai_summary(
        self,
        domain_id: str,
        analysis_id: str,
        data: dict,
    ):
        # AI summary is expensive, cache longer
        key = self._dashboard_key(domain_id, "ai-summary", analysis_id)
        await self.set(key, data, CacheConfig.DASHBOARD_AI_SUMMARY)

    # =========================================================================
    # Keywords Cache Operations
    # =========================================================================

    def _keywords_key(self, domain_id: str, analysis_id: str, cursor: str = None, filters: dict = None) -> str:
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
        cursor: str = None,
        filters: dict = None,
    ) -> Optional[dict]:
        key = self._keywords_key(domain_id, analysis_id, cursor, filters)
        return await self.get(key)

    async def set_keywords_page(
        self,
        domain_id: str,
        analysis_id: str,
        data: dict,
        cursor: str = None,
        filters: dict = None,
    ):
        key = self._keywords_key(domain_id, analysis_id, cursor, filters)
        await self.set(key, data, CacheConfig.KEYWORDS_PAGE)

    # =========================================================================
    # Cache Invalidation
    # =========================================================================

    async def invalidate_domain(self, domain_id: str):
        """Invalidate all cache for a domain."""
        pattern = self._make_key("*", domain_id, "*")
        await self.delete_pattern(pattern)
        logger.info(f"Invalidated cache for domain: {domain_id}")

    async def invalidate_analysis(self, analysis_id: str):
        """Invalidate all cache for an analysis."""
        pattern = self._make_key("*", "*", analysis_id, "*")
        await self.delete_pattern(pattern)
        logger.info(f"Invalidated cache for analysis: {analysis_id}")

    async def invalidate_dashboard(self, domain_id: str):
        """Invalidate dashboard cache for a domain."""
        pattern = self._make_key("dashboard", domain_id, "*")
        await self.delete_pattern(pattern)
        logger.info(f"Invalidated dashboard cache for domain: {domain_id}")

    # =========================================================================
    # Cache Statistics
    # =========================================================================

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        info = await self.redis.info("stats")
        memory = await self.redis.info("memory")

        return {
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
            "memory_used_mb": memory.get("used_memory", 0) / 1024 / 1024,
            "memory_peak_mb": memory.get("used_memory_peak", 0) / 1024 / 1024,
        }
```

### Layer 4: Precomputed Cache

The most important optimization: **precompute expensive aggregations after analysis completes**.

```python
# src/cache/precomputation.py

"""
Precomputation Pipeline

After an analysis completes, precompute all expensive dashboard data
and store it for instant retrieval.

This runs ONCE after analysis, not on every dashboard load.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.database.models import (
    AnalysisRun,
    PrecomputedDashboard,
    Keyword,
    KeywordPosition,
)
from src.cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class PrecomputationPipeline:
    """
    Precomputes all expensive dashboard data after analysis completion.

    Run this as a background job when analysis finishes.
    """

    def __init__(self, db: Session, cache: RedisCache):
        self.db = db
        self.cache = cache

    async def precompute_all(self, analysis_id: UUID):
        """
        Precompute all dashboard data for an analysis.

        This is the main entry point, called after analysis completes.
        """
        logger.info(f"Starting precomputation for analysis: {analysis_id}")
        start_time = datetime.utcnow()

        analysis = self.db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
        if not analysis:
            raise ValueError(f"Analysis not found: {analysis_id}")

        domain_id = str(analysis.domain_id)
        analysis_id_str = str(analysis_id)

        # Run all precomputations in parallel
        await asyncio.gather(
            self._precompute_overview(domain_id, analysis_id_str, analysis),
            self._precompute_sparklines(domain_id, analysis_id_str),
            self._precompute_sov(domain_id, analysis_id_str),
            self._precompute_battleground(domain_id, analysis_id_str),
            self._precompute_clusters(domain_id, analysis_id_str),
            self._precompute_content_audit(domain_id, analysis_id_str),
            self._precompute_ai_summary(domain_id, analysis_id_str, analysis),
            self._precompute_keywords_pages(domain_id, analysis_id_str),
        )

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Precomputation complete for {analysis_id} in {elapsed:.2f}s")

        # Mark precomputation complete
        analysis.precomputation_complete = True
        analysis.precomputation_time = elapsed
        self.db.commit()

    async def _precompute_overview(
        self,
        domain_id: str,
        analysis_id: str,
        analysis: AnalysisRun,
    ):
        """Precompute dashboard overview."""
        logger.info("Precomputing overview...")

        # Calculate all health scores
        keywords = self.db.query(Keyword).filter(
            Keyword.analysis_run_id == analysis_id
        ).all()

        # Position distribution
        positions = {"top_3": 0, "4_10": 0, "11_20": 0, "21_50": 0, "51_plus": 0}
        for kw in keywords:
            pos = kw.position or 100
            if pos <= 3:
                positions["top_3"] += 1
            elif pos <= 10:
                positions["4_10"] += 1
            elif pos <= 20:
                positions["11_20"] += 1
            elif pos <= 50:
                positions["21_50"] += 1
            else:
                positions["51_plus"] += 1

        # Health scores (calculate from data)
        keyword_health = self._calculate_keyword_health(keywords)
        # ... other health scores ...

        overview = {
            "domain": analysis.domain.domain,
            "analysis_id": str(analysis_id),
            "analysis_date": analysis.completed_at.isoformat(),
            "health": {
                "overall": keyword_health * 0.3 + 70,  # Simplified
                "keyword_health": keyword_health,
                # ... other scores
            },
            "organic_keywords": {
                "current": len(keywords),
                # ... trends
            },
            "positions": positions,
            "quick_wins_count": sum(1 for k in keywords if self._is_quick_win(k)),
            "at_risk_keywords": sum(1 for k in keywords if self._is_at_risk(k)),
        }

        # Store in Redis
        await self.cache.set_dashboard_overview(domain_id, analysis_id, overview)

        # Also store in PostgreSQL for persistence
        self._store_precomputed(analysis_id, "overview", overview)

    async def _precompute_sparklines(self, domain_id: str, analysis_id: str):
        """
        Precompute sparkline data for all keywords.

        This is expensive: we need position history for 8000+ keywords.
        """
        logger.info("Precomputing sparklines...")

        # Get all keywords with their position history
        keywords = self.db.query(Keyword).filter(
            Keyword.analysis_run_id == analysis_id
        ).all()

        sparklines = []
        for kw in keywords:
            # Get 30-day position history
            history = self.db.query(KeywordPosition).filter(
                KeywordPosition.keyword_id == kw.id
            ).order_by(KeywordPosition.date.desc()).limit(30).all()

            sparkline_data = [
                {"date": h.date.isoformat(), "value": h.position}
                for h in reversed(history)
            ]

            # Calculate trend
            if len(sparkline_data) >= 2:
                first_pos = sparkline_data[0]["value"]
                last_pos = sparkline_data[-1]["value"]
                trend = "improving" if last_pos < first_pos else "declining" if last_pos > first_pos else "stable"
            else:
                trend = "stable"

            sparklines.append({
                "keyword_id": str(kw.id),
                "keyword": kw.keyword,
                "current_position": kw.position,
                "search_volume": kw.search_volume,
                "sparkline": sparkline_data,
                "trend": trend,
            })

        # Store in Redis (chunked for large datasets)
        await self.cache.set_sparklines(domain_id, analysis_id, {"keywords": sparklines})

    async def _precompute_ai_summary(
        self,
        domain_id: str,
        analysis_id: str,
        analysis: AnalysisRun,
    ):
        """
        Precompute AI-generated summary.

        This is the most expensive operation (requires LLM call).
        Run ONCE and cache result.
        """
        logger.info("Precomputing AI summary...")

        # Only call LLM if summary doesn't exist
        existing = await self.cache.get_ai_summary(domain_id, analysis_id)
        if existing:
            logger.info("AI summary already cached, skipping")
            return

        # Generate summary using agent output or dedicated LLM call
        summary = await self._generate_ai_summary(analysis)

        await self.cache.set_ai_summary(domain_id, analysis_id, summary)

    async def _precompute_keywords_pages(self, domain_id: str, analysis_id: str):
        """
        Precompute first N pages of keywords in common sort orders.

        Users almost always view first 2-3 pages. Precompute these.
        """
        logger.info("Precomputing keywords pages...")

        sort_orders = [
            {"field": "search_volume", "direction": "desc"},
            {"field": "position", "direction": "asc"},
            {"field": "opportunity_score", "direction": "desc"},
        ]

        for sort in sort_orders:
            # Precompute first 3 pages (150 keywords)
            for page in range(3):
                cursor = None if page == 0 else f"page:{page}"
                keywords_page = await self._fetch_keywords_page(
                    analysis_id, cursor, sort, limit=50
                )
                await self.cache.set_keywords_page(
                    domain_id, analysis_id, keywords_page, cursor, sort
                )

    def _store_precomputed(self, analysis_id: str, data_type: str, data: dict):
        """Store precomputed data in PostgreSQL for persistence."""
        precomputed = PrecomputedDashboard(
            analysis_run_id=analysis_id,
            data_type=data_type,
            data=data,
        )
        self.db.merge(precomputed)
        self.db.commit()

    def _calculate_keyword_health(self, keywords) -> float:
        """Calculate keyword health score."""
        if not keywords:
            return 0

        top_10 = sum(1 for k in keywords if k.position and k.position <= 10)
        total = len(keywords)

        return (top_10 / total) * 100

    def _is_quick_win(self, keyword) -> bool:
        """Check if keyword is a quick win."""
        return (
            keyword.position and
            11 <= keyword.position <= 20 and
            keyword.keyword_difficulty and
            keyword.keyword_difficulty <= 40 and
            keyword.search_volume and
            keyword.search_volume >= 100
        )

    def _is_at_risk(self, keyword) -> bool:
        """Check if keyword position is declining."""
        # Would need position history analysis
        return False


# Integration with analysis completion
async def on_analysis_complete(analysis_id: UUID, db: Session, cache: RedisCache):
    """
    Called when analysis completes. Triggers precomputation.
    """
    pipeline = PrecomputationPipeline(db, cache)

    # Run precomputation in background
    asyncio.create_task(pipeline.precompute_all(analysis_id))
```

### Layer 5: Database Optimization

```sql
-- Create materialized view for dashboard overview
-- Refresh after each analysis

CREATE MATERIALIZED VIEW mv_dashboard_overview AS
SELECT
    d.id as domain_id,
    ar.id as analysis_run_id,
    ar.completed_at,
    COUNT(k.id) as total_keywords,
    SUM(CASE WHEN k.position <= 3 THEN 1 ELSE 0 END) as top_3,
    SUM(CASE WHEN k.position BETWEEN 4 AND 10 THEN 1 ELSE 0 END) as pos_4_10,
    SUM(CASE WHEN k.position BETWEEN 11 AND 20 THEN 1 ELSE 0 END) as pos_11_20,
    SUM(CASE WHEN k.position BETWEEN 21 AND 50 THEN 1 ELSE 0 END) as pos_21_50,
    SUM(CASE WHEN k.position > 50 THEN 1 ELSE 0 END) as pos_51_plus,
    SUM(k.search_volume) as total_volume,
    SUM(k.estimated_traffic) as total_traffic,
    AVG(k.opportunity_score) as avg_opportunity_score
FROM domains d
JOIN analysis_runs ar ON ar.domain_id = d.id AND ar.is_latest = true
LEFT JOIN keywords k ON k.analysis_run_id = ar.id
GROUP BY d.id, ar.id, ar.completed_at;

CREATE UNIQUE INDEX ON mv_dashboard_overview(domain_id);

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_dashboard_overview()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_overview;
END;
$$ LANGUAGE plpgsql;


-- Optimized keywords query with covering index
CREATE INDEX CONCURRENTLY idx_keywords_dashboard
ON keywords (analysis_run_id, search_volume DESC, position ASC)
INCLUDE (keyword, keyword_difficulty, intent, opportunity_score, estimated_traffic);

-- Position history for sparklines
CREATE INDEX CONCURRENTLY idx_position_history_sparkline
ON keyword_positions (keyword_id, date DESC)
INCLUDE (position);
```

---

## 4. Cache Invalidation Strategy

### Event-Driven Invalidation

```python
# src/cache/invalidation.py

from enum import Enum
from typing import List
import asyncio
import logging

from src.cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class CacheEvent(Enum):
    """Events that trigger cache invalidation."""
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    STRATEGY_CREATED = "strategy_created"
    STRATEGY_UPDATED = "strategy_updated"
    THREAD_UPDATED = "thread_updated"
    KEYWORDS_ASSIGNED = "keywords_assigned"


class CacheInvalidator:
    """
    Handles cache invalidation based on events.

    Principle: Invalidate as narrowly as possible.
    """

    def __init__(self, cache: RedisCache, cdn_purger: 'CDNPurger' = None):
        self.cache = cache
        self.cdn_purger = cdn_purger

    async def handle_event(
        self,
        event: CacheEvent,
        domain_id: str = None,
        analysis_id: str = None,
        strategy_id: str = None,
        **kwargs
    ):
        """Handle cache invalidation for an event."""

        logger.info(f"Cache invalidation event: {event.value}, domain={domain_id}")

        if event == CacheEvent.ANALYSIS_STARTED:
            # Don't invalidate yet - old data still valid
            pass

        elif event == CacheEvent.ANALYSIS_COMPLETED:
            # Invalidate all dashboard data for this domain
            await self.cache.invalidate_dashboard(domain_id)

            # Invalidate keywords cache
            await self.cache.invalidate_analysis(analysis_id)

            # Purge CDN
            if self.cdn_purger:
                await self.cdn_purger.purge_by_tags([
                    f"domain:{domain_id}",
                    f"analysis:{analysis_id}",
                    "dashboard",
                ])

        elif event == CacheEvent.STRATEGY_UPDATED:
            # Only invalidate strategy cache, not dashboard
            await self.cache.delete(f"strategy:{strategy_id}")

        elif event == CacheEvent.KEYWORDS_ASSIGNED:
            # Invalidate available keywords cache
            await self.cache.delete_pattern(f"*:strategy:{strategy_id}:available*")


class CDNPurger:
    """
    Purges CDN cache using vendor-specific APIs.
    """

    async def purge_by_tags(self, tags: List[str]):
        """Purge CDN cache by surrogate keys/tags."""
        # Cloudflare example
        # await self._purge_cloudflare(tags)
        pass

    async def purge_urls(self, urls: List[str]):
        """Purge specific URLs from CDN."""
        pass
```

### CDN Purging (Cloudflare Example)

```python
# src/cache/cdn.py

import httpx
from typing import List


class CloudflarePurger:
    """
    Purges Cloudflare cache using Cache Tags.

    Requires Enterprise plan for Cache Tags, or use URL purging for Pro.
    """

    def __init__(self, zone_id: str, api_token: str):
        self.zone_id = zone_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"

    async def purge_by_tags(self, tags: List[str]):
        """Purge by Cache-Tag (Enterprise only)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                json={"tags": tags},
            )
            response.raise_for_status()

    async def purge_by_prefix(self, prefix: str):
        """Purge by URL prefix (Enterprise only)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                json={"prefixes": [prefix]},
            )
            response.raise_for_status()

    async def purge_everything(self):
        """Nuclear option - purge entire zone."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                json={"purge_everything": True},
            )
            response.raise_for_status()
```

---

## 5. Request Optimization

### Parallel Data Loading

Frontend should load dashboard data in parallel:

```typescript
// src/pages/Dashboard.tsx

export function Dashboard({ domainId }: { domainId: string }) {
  // Load all dashboard data in parallel
  const results = useQueries({
    queries: [
      {
        queryKey: queryKeys.dashboard.overview(domainId),
        queryFn: () => fetchDashboardOverview(domainId),
        staleTime: STALE_TIMES.dashboardOverview,
      },
      {
        queryKey: queryKeys.dashboard.sparklines(domainId),
        queryFn: () => fetchSparklines(domainId),
        staleTime: STALE_TIMES.sparklines,
      },
      {
        queryKey: queryKeys.dashboard.sov(domainId),
        queryFn: () => fetchShareOfVoice(domainId),
        staleTime: STALE_TIMES.shareOfVoice,
      },
      {
        queryKey: queryKeys.dashboard.aiSummary(domainId),
        queryFn: () => fetchAISummary(domainId),
        staleTime: STALE_TIMES.aiSummary,
      },
    ],
  });

  const [overview, sparklines, sov, aiSummary] = results;

  // Show skeleton while loading
  if (overview.isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <DashboardLayout>
      <AISummary data={aiSummary.data} isLoading={aiSummary.isLoading} />
      <MetricCards overview={overview.data} />
      <PositionChart sparklines={sparklines.data} />
      <ShareOfVoiceChart sov={sov.data} />
    </DashboardLayout>
  );
}
```

### Batched API Endpoints

Create combined endpoints to reduce round trips:

```python
# In api/dashboard.py

@router.get("/{domain_id}/bundle")
async def get_dashboard_bundle(
    domain_id: UUID,
    include: str = Query("overview,sparklines,sov"),  # Comma-separated
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Bundled endpoint to fetch multiple dashboard components in one request.

    Reduces HTTP round trips from 6 to 1.
    """
    requested = set(include.split(","))

    bundle = {}

    # Fetch requested components in parallel
    tasks = []
    if "overview" in requested:
        tasks.append(("overview", get_precomputed_overview(domain_id, db)))
    if "sparklines" in requested:
        tasks.append(("sparklines", get_precomputed_sparklines(domain_id, db)))
    if "sov" in requested:
        tasks.append(("sov", get_precomputed_sov(domain_id, db)))
    if "battleground" in requested:
        tasks.append(("battleground", get_precomputed_battleground(domain_id, db)))
    if "ai-summary" in requested:
        tasks.append(("ai-summary", get_precomputed_ai_summary(domain_id, db)))

    results = await asyncio.gather(*[t[1] for t in tasks])

    for (key, _), result in zip(tasks, results):
        bundle[key] = result

    # Cache headers for the bundle
    add_cache_headers(
        response=response,
        max_age=300,  # 5 minutes
        etag=generate_bundle_etag(bundle),
        last_modified=datetime.utcnow(),
        surrogate_keys=[f"domain:{domain_id}", "dashboard-bundle"],
    )

    return bundle
```

### Conditional Requests

```typescript
// src/lib/api-client.ts

import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// Add ETag handling for conditional requests
apiClient.interceptors.request.use((config) => {
  const etag = localStorage.getItem(`etag:${config.url}`);
  if (etag && config.method === 'get') {
    config.headers['If-None-Match'] = etag;
  }
  return config;
});

apiClient.interceptors.response.use((response) => {
  // Store ETag for future requests
  const etag = response.headers['etag'];
  if (etag) {
    localStorage.setItem(`etag:${response.config.url}`, etag);
  }
  return response;
}, (error) => {
  // Handle 304 Not Modified
  if (error.response?.status === 304) {
    // Return cached data
    const cachedData = queryClient.getQueryData(/* query key */);
    if (cachedData) {
      return { data: cachedData, status: 304 };
    }
  }
  return Promise.reject(error);
});
```

---

## 6. Monitoring & Observability

```python
# src/cache/monitoring.py

from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Metrics for cache performance monitoring."""
    hits: int
    misses: int
    hit_rate: float
    avg_latency_ms: float
    memory_usage_mb: float


class CacheMonitor:
    """
    Monitors cache performance and alerts on issues.
    """

    def __init__(self, cache: 'RedisCache'):
        self.cache = cache
        self.thresholds = {
            "min_hit_rate": 0.8,        # Alert if hit rate drops below 80%
            "max_latency_ms": 50,        # Alert if latency exceeds 50ms
            "max_memory_mb": 1024,       # Alert if memory exceeds 1GB
        }

    async def collect_metrics(self) -> CacheMetrics:
        """Collect current cache metrics."""
        stats = await self.cache.get_stats()

        return CacheMetrics(
            hits=stats["hits"],
            misses=stats["misses"],
            hit_rate=stats["hit_rate"],
            avg_latency_ms=await self._measure_latency(),
            memory_usage_mb=stats["memory_used_mb"],
        )

    async def check_health(self) -> dict:
        """Check cache health and return issues."""
        metrics = await self.collect_metrics()
        issues = []

        if metrics.hit_rate < self.thresholds["min_hit_rate"]:
            issues.append({
                "type": "low_hit_rate",
                "value": metrics.hit_rate,
                "threshold": self.thresholds["min_hit_rate"],
                "action": "Review cache TTLs and precomputation coverage",
            })

        if metrics.avg_latency_ms > self.thresholds["max_latency_ms"]:
            issues.append({
                "type": "high_latency",
                "value": metrics.avg_latency_ms,
                "threshold": self.thresholds["max_latency_ms"],
                "action": "Check Redis connection and memory pressure",
            })

        if metrics.memory_usage_mb > self.thresholds["max_memory_mb"]:
            issues.append({
                "type": "high_memory",
                "value": metrics.memory_usage_mb,
                "threshold": self.thresholds["max_memory_mb"],
                "action": "Review cache eviction policy and TTLs",
            })

        return {
            "healthy": len(issues) == 0,
            "metrics": metrics.__dict__,
            "issues": issues,
        }

    async def _measure_latency(self) -> float:
        """Measure average cache latency."""
        import time
        latencies = []

        for _ in range(10):
            start = time.perf_counter()
            await self.cache.redis.ping()
            latencies.append((time.perf_counter() - start) * 1000)

        return sum(latencies) / len(latencies)
```

---

## 7. Implementation Checklist

### Phase 1: Foundation (Week 1)

- [ ] Set up Redis instance
- [ ] Implement `RedisCache` class with basic operations
- [ ] Add cache headers to all dashboard endpoints
- [ ] Configure React Query with proper stale times

### Phase 2: Precomputation (Week 2)

- [ ] Implement `PrecomputationPipeline`
- [ ] Add precomputation trigger on analysis completion
- [ ] Create materialized views in PostgreSQL
- [ ] Test precomputation with real analyses

### Phase 3: Frontend Integration (Week 3)

- [ ] Add IndexedDB persistence for large datasets
- [ ] Implement parallel data loading
- [ ] Add conditional request handling (ETags)
- [ ] Create loading skeletons for all components

### Phase 4: CDN & Monitoring (Week 4)

- [ ] Configure CDN caching rules
- [ ] Implement cache purging
- [ ] Set up monitoring dashboard
- [ ] Add alerting for cache issues

---

## 8. Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Dashboard load time | 2-5s | <500ms | 5-10x faster |
| Keywords table load | 1-3s | <300ms | 5-10x faster |
| API calls per dashboard view | 6-8 | 1-2 (bundled) | 4-6x fewer |
| LLM costs per view | $0.02-0.05 | $0 (cached) | 100% reduction |
| DataForSEO API costs | $0.05/view | $0.001/view | 50x reduction |
| Cache hit rate | 0% | >90% | ∞ |

---

## 9. Cost Analysis

### Current (No Caching)

```
Per dashboard view:
- 6 API calls to backend: $0
- Potential DataForSEO calls: $0.02-0.05
- LLM call for AI summary: $0.02-0.10

Daily cost (100 views/day): $2-15
Monthly cost: $60-450
```

### With Caching

```
Per dashboard view:
- Cache hit: $0
- LLM call: $0 (precomputed)

Per analysis completion:
- Precomputation: $0.10-0.20 (one-time LLM + compute)

Daily cost (100 views/day): ~$0.20 (from analysis runs)
Monthly cost: ~$6
```

**Savings: 90-98% reduction in operational costs**

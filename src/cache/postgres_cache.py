"""
PostgreSQL Cache Implementation

Simple, reliable caching using PostgreSQL's precomputed_dashboard table.
No Redis required - uses the same database as the application.

Key insight: Dashboard data only changes when new analysis completes.
Pre-computing and storing in PostgreSQL gives us:
- Sub-100ms reads (simple indexed query)
- No additional infrastructure
- ACID guarantees
- Automatic backup with database

Performance characteristics:
- Read latency: 5-20ms (single indexed query)
- Write latency: 10-50ms (single upsert)
- Perfect consistency with source data
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from src.database.models import PrecomputedDashboard, AnalysisRun, AnalysisStatus
from src.cache.config import CacheTTL


logger = logging.getLogger(__name__)


class PostgresCache:
    """
    PostgreSQL-based cache using the precomputed_dashboard table.

    Simple and reliable - no external dependencies.
    """

    def __init__(self, db: Session):
        self.db = db
        self._stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
        }

    def get_dashboard(
        self,
        domain_id: str,
        data_type: str,
        analysis_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Get cached dashboard data.

        Args:
            domain_id: Domain UUID string
            data_type: Type of data (overview, sparklines, sov, etc.)
            analysis_id: Specific analysis ID (optional, defaults to latest)

        Returns:
            Cached data dict or None if not found
        """
        try:
            query = self.db.query(PrecomputedDashboard).filter(
                PrecomputedDashboard.domain_id == domain_id,
                PrecomputedDashboard.data_type == data_type,
                PrecomputedDashboard.is_current == True,
            )

            if analysis_id:
                query = query.filter(PrecomputedDashboard.analysis_run_id == analysis_id)

            # Get most recent
            record = query.order_by(desc(PrecomputedDashboard.created_at)).first()

            if record:
                self._stats["hits"] += 1
                return record.data
            else:
                self._stats["misses"] += 1
                return None

        except Exception as e:
            logger.error(f"Cache get error for {data_type}: {e}")
            self._stats["misses"] += 1
            return None

    def set_dashboard(
        self,
        domain_id: str,
        data_type: str,
        data: Dict,
        analysis_id: str,
        etag: Optional[str] = None,
    ) -> bool:
        """
        Store dashboard data in cache.

        Uses upsert to handle both insert and update cases.

        Args:
            domain_id: Domain UUID string
            data_type: Type of data (overview, sparklines, sov, etc.)
            data: Data to cache
            analysis_id: Analysis ID this data belongs to
            etag: Optional ETag for HTTP caching

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if record exists
            existing = self.db.query(PrecomputedDashboard).filter(
                PrecomputedDashboard.analysis_run_id == analysis_id,
                PrecomputedDashboard.data_type == data_type,
            ).first()

            # Calculate size
            data_bytes = json.dumps(data).encode('utf-8')
            size_bytes = len(data_bytes)

            if existing:
                # Update existing record
                existing.data = data
                existing.etag = etag
                existing.size_bytes = size_bytes
                existing.is_current = True
                existing.created_at = datetime.utcnow()
            else:
                # Create new record
                record = PrecomputedDashboard(
                    domain_id=domain_id,
                    analysis_run_id=analysis_id,
                    data_type=data_type,
                    data=data,
                    etag=etag,
                    size_bytes=size_bytes,
                    is_current=True,
                )
                self.db.add(record)

            self.db.commit()
            self._stats["writes"] += 1
            logger.debug(f"Cached {data_type} for domain {domain_id} ({size_bytes} bytes)")
            return True

        except Exception as e:
            logger.error(f"Cache set error for {data_type}: {e}")
            self.db.rollback()
            return False

    def get_bundle(
        self,
        domain_id: str,
        analysis_id: str,
    ) -> Optional[Dict]:
        """
        Get all dashboard components as a bundle.

        Fetches all precomputed data for an analysis in one query.
        """
        try:
            records = self.db.query(PrecomputedDashboard).filter(
                PrecomputedDashboard.analysis_run_id == analysis_id,
                PrecomputedDashboard.is_current == True,
            ).all()

            if not records:
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1

            bundle = {}
            for record in records:
                # Convert data_type like "content-audit" to "content_audit"
                key = record.data_type.replace("-", "_")
                bundle[key] = record.data

            bundle["analysis_id"] = analysis_id
            bundle["from_cache"] = True

            return bundle

        except Exception as e:
            logger.error(f"Bundle cache error: {e}")
            self._stats["misses"] += 1
            return None

    def invalidate_domain(self, domain_id: str) -> int:
        """
        Invalidate all cache for a domain.

        Marks records as not current rather than deleting them.
        """
        try:
            result = self.db.query(PrecomputedDashboard).filter(
                PrecomputedDashboard.domain_id == domain_id,
                PrecomputedDashboard.is_current == True,
            ).update({"is_current": False})

            self.db.commit()
            logger.info(f"Invalidated {result} cache entries for domain {domain_id}")
            return result

        except Exception as e:
            logger.error(f"Invalidation error for domain {domain_id}: {e}")
            self.db.rollback()
            return 0

    def invalidate_analysis(self, analysis_id: str) -> int:
        """
        Invalidate all cache for an analysis.
        """
        try:
            result = self.db.query(PrecomputedDashboard).filter(
                PrecomputedDashboard.analysis_run_id == analysis_id,
            ).update({"is_current": False})

            self.db.commit()
            logger.info(f"Invalidated {result} cache entries for analysis {analysis_id}")
            return result

        except Exception as e:
            logger.error(f"Invalidation error for analysis {analysis_id}: {e}")
            self.db.rollback()
            return 0

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        return {
            "enabled": True,
            "backend": "postgresql",
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "writes": self._stats["writes"],
            "hit_rate_percent": round(hit_rate, 2),
        }

    def health_check(self) -> Dict:
        """
        Simple health check.

        Just verifies we can query the table.
        """
        try:
            count = self.db.query(PrecomputedDashboard).filter(
                PrecomputedDashboard.is_current == True
            ).count()

            return {
                "healthy": True,
                "status": "connected",
                "cached_entries": count,
                "backend": "postgresql",
            }

        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "backend": "postgresql",
            }


def get_postgres_cache(db: Session) -> PostgresCache:
    """
    Get a PostgresCache instance.

    Unlike Redis, this doesn't need a singleton - it uses the
    existing database session.
    """
    return PostgresCache(db)


def get_latest_analysis_for_domain(db: Session, domain_id: str) -> Optional[AnalysisRun]:
    """
    Helper to get the latest completed analysis for a domain.
    """
    return db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.status == AnalysisStatus.COMPLETED,
    ).order_by(desc(AnalysisRun.completed_at)).first()

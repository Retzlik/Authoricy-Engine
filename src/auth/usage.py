"""
Usage Tracking

Track API usage, costs, and analytics per API key.
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Single usage record."""
    timestamp: datetime
    api_key_id: str
    endpoint: str
    domain: str
    success: bool
    duration_ms: int
    tokens_used: int = 0
    api_cost: float = 0.0  # DataForSEO API cost
    ai_cost: float = 0.0   # Claude API cost
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def total_cost(self) -> float:
        """Calculate total cost."""
        return self.api_cost + self.ai_cost

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "UsageRecord":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class DailyUsageSummary:
    """Daily usage summary for a key."""
    date: date
    api_key_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: int = 0
    total_tokens: int = 0
    total_api_cost: float = 0.0
    total_ai_cost: float = 0.0
    unique_domains: int = 0
    endpoints_called: Dict[str, int] = field(default_factory=dict)

    def total_cost(self) -> float:
        """Calculate total cost."""
        return self.total_api_cost + self.total_ai_cost

    def avg_duration_ms(self) -> float:
        """Calculate average request duration."""
        if self.total_requests == 0:
            return 0
        return self.total_duration_ms / self.total_requests

    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100


class UsageTracker:
    """
    Tracks and persists API usage.

    Supports real-time tracking and historical reporting.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize usage tracker.

        Args:
            storage_path: Directory for usage data files.
                         Defaults to ~/.authoricy/usage/
        """
        if storage_path is None:
            storage_path = os.getenv(
                "AUTHORICY_USAGE_PATH",
                str(Path.home() / ".authoricy" / "usage")
            )

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory buffer for recent records (flushed periodically)
        self._buffer: List[UsageRecord] = []
        self._buffer_max_size = 100

        # Daily summaries cache
        self._daily_summaries: Dict[str, DailyUsageSummary] = {}

    def _get_daily_file(self, d: date) -> Path:
        """Get path for daily usage file."""
        return self.storage_path / f"usage_{d.isoformat()}.json"

    def record(
        self,
        api_key_id: str,
        endpoint: str,
        domain: str,
        success: bool,
        duration_ms: int,
        tokens_used: int = 0,
        api_cost: float = 0.0,
        ai_cost: float = 0.0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> UsageRecord:
        """
        Record a usage event.

        Args:
            api_key_id: ID of the API key used
            endpoint: API endpoint called
            domain: Domain analyzed
            success: Whether request succeeded
            duration_ms: Request duration in milliseconds
            tokens_used: AI tokens consumed
            api_cost: DataForSEO API cost
            ai_cost: Claude API cost
            error_message: Error message if failed
            metadata: Additional metadata

        Returns:
            The created UsageRecord
        """
        record = UsageRecord(
            timestamp=datetime.now(),
            api_key_id=api_key_id,
            endpoint=endpoint,
            domain=domain,
            success=success,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            api_cost=api_cost,
            ai_cost=ai_cost,
            error_message=error_message,
            metadata=metadata or {}
        )

        self._buffer.append(record)
        self._update_daily_summary(record)

        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_max_size:
            self._flush_buffer()

        return record

    def _update_daily_summary(self, record: UsageRecord):
        """Update daily summary with new record."""
        today = record.timestamp.date()
        key = f"{today.isoformat()}_{record.api_key_id}"

        if key not in self._daily_summaries:
            self._daily_summaries[key] = DailyUsageSummary(
                date=today,
                api_key_id=record.api_key_id
            )

        summary = self._daily_summaries[key]
        summary.total_requests += 1
        if record.success:
            summary.successful_requests += 1
        else:
            summary.failed_requests += 1
        summary.total_duration_ms += record.duration_ms
        summary.total_tokens += record.tokens_used
        summary.total_api_cost += record.api_cost
        summary.total_ai_cost += record.ai_cost

        # Track endpoints
        if record.endpoint not in summary.endpoints_called:
            summary.endpoints_called[record.endpoint] = 0
        summary.endpoints_called[record.endpoint] += 1

    def _flush_buffer(self):
        """Flush buffer to disk."""
        if not self._buffer:
            return

        # Group records by date
        by_date: Dict[date, List[UsageRecord]] = defaultdict(list)
        for record in self._buffer:
            by_date[record.timestamp.date()].append(record)

        # Append to daily files
        for d, records in by_date.items():
            file_path = self._get_daily_file(d)

            # Load existing records
            existing = []
            if file_path.exists():
                try:
                    with open(file_path, "r") as f:
                        existing = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load existing usage data: {e}")

            # Append new records
            existing.extend([r.to_dict() for r in records])

            # Save
            try:
                with open(file_path, "w") as f:
                    json.dump(existing, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save usage data: {e}")

        self._buffer.clear()
        logger.debug(f"Flushed {sum(len(r) for r in by_date.values())} usage records")

    def flush(self):
        """Force flush buffer to disk."""
        self._flush_buffer()

    def get_daily_summary(
        self,
        api_key_id: str,
        d: Optional[date] = None
    ) -> Optional[DailyUsageSummary]:
        """Get daily usage summary for a key."""
        if d is None:
            d = date.today()

        key = f"{d.isoformat()}_{api_key_id}"

        # Check cache
        if key in self._daily_summaries:
            return self._daily_summaries[key]

        # Load from disk
        file_path = self._get_daily_file(d)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                records = [UsageRecord.from_dict(r) for r in json.load(f)]

            # Filter and summarize
            key_records = [r for r in records if r.api_key_id == api_key_id]
            if not key_records:
                return None

            summary = DailyUsageSummary(date=d, api_key_id=api_key_id)
            unique_domains = set()

            for record in key_records:
                summary.total_requests += 1
                if record.success:
                    summary.successful_requests += 1
                else:
                    summary.failed_requests += 1
                summary.total_duration_ms += record.duration_ms
                summary.total_tokens += record.tokens_used
                summary.total_api_cost += record.api_cost
                summary.total_ai_cost += record.ai_cost
                unique_domains.add(record.domain)

                if record.endpoint not in summary.endpoints_called:
                    summary.endpoints_called[record.endpoint] = 0
                summary.endpoints_called[record.endpoint] += 1

            summary.unique_domains = len(unique_domains)
            return summary

        except Exception as e:
            logger.error(f"Failed to load daily summary: {e}")
            return None

    def get_usage_report(
        self,
        api_key_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Generate usage report for a date range.

        Args:
            api_key_id: API key ID
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)

        Returns:
            Usage report dictionary
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        summaries = []
        current = start_date

        while current <= end_date:
            summary = self.get_daily_summary(api_key_id, current)
            if summary:
                summaries.append(summary)
            current += timedelta(days=1)

        # Aggregate
        total_requests = sum(s.total_requests for s in summaries)
        total_successful = sum(s.successful_requests for s in summaries)
        total_failed = sum(s.failed_requests for s in summaries)
        total_api_cost = sum(s.total_api_cost for s in summaries)
        total_ai_cost = sum(s.total_ai_cost for s in summaries)
        total_tokens = sum(s.total_tokens for s in summaries)

        # Aggregate endpoints
        all_endpoints: Dict[str, int] = defaultdict(int)
        for s in summaries:
            for endpoint, count in s.endpoints_called.items():
                all_endpoints[endpoint] += count

        return {
            "api_key_id": api_key_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days + 1,
            },
            "totals": {
                "requests": total_requests,
                "successful": total_successful,
                "failed": total_failed,
                "success_rate": (total_successful / total_requests * 100) if total_requests else 0,
                "api_cost": round(total_api_cost, 2),
                "ai_cost": round(total_ai_cost, 2),
                "total_cost": round(total_api_cost + total_ai_cost, 2),
                "tokens": total_tokens,
            },
            "daily_breakdown": [
                {
                    "date": s.date.isoformat(),
                    "requests": s.total_requests,
                    "cost": round(s.total_cost(), 2),
                    "success_rate": round(s.success_rate(), 1),
                }
                for s in summaries
            ],
            "endpoints": dict(all_endpoints),
            "averages": {
                "requests_per_day": total_requests / max(len(summaries), 1),
                "cost_per_day": (total_api_cost + total_ai_cost) / max(len(summaries), 1),
                "cost_per_request": (total_api_cost + total_ai_cost) / max(total_requests, 1),
            }
        }

    def get_all_time_stats(self, api_key_id: str) -> Dict[str, Any]:
        """Get all-time statistics for a key."""
        # Scan all usage files
        total_requests = 0
        total_cost = 0.0
        first_used = None
        last_used = None

        for file_path in sorted(self.storage_path.glob("usage_*.json")):
            try:
                with open(file_path, "r") as f:
                    records = json.load(f)

                for record_data in records:
                    if record_data.get("api_key_id") == api_key_id:
                        total_requests += 1
                        total_cost += record_data.get("api_cost", 0) + record_data.get("ai_cost", 0)

                        timestamp = datetime.fromisoformat(record_data["timestamp"])
                        if first_used is None or timestamp < first_used:
                            first_used = timestamp
                        if last_used is None or timestamp > last_used:
                            last_used = timestamp

            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")

        return {
            "api_key_id": api_key_id,
            "total_requests": total_requests,
            "total_cost": round(total_cost, 2),
            "first_used": first_used.isoformat() if first_used else None,
            "last_used": last_used.isoformat() if last_used else None,
        }

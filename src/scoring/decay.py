"""
Content Decay Score Calculator

Identifies content that has lost traffic/rankings and needs refreshing.
Uses historical data to detect decline patterns.

Formula:
    Decay_Score = (
        (Peak_Traffic - Current_Traffic) / Peak_Traffic × 0.40 +
        (Current_Position - Peak_Position) / 10 × 0.30 +
        (Peak_CTR - Current_CTR) / Peak_CTR × 0.20 +
        Age_Factor × 0.10
    )

Thresholds:
    >0.5: Critical - Complete content refresh needed
    0.3-0.5: Major - Significant update recommended
    0.1-0.3: Light - Minor refresh
    <0.1: Monitor - No action needed
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .helpers import DecaySeverity, get_decay_severity, DECAY_ACTIONS

logger = logging.getLogger(__name__)


class DecayAction(Enum):
    """Recommended action based on decay severity (KUCK framework)."""
    KEEP = "keep"           # <0.1 decay - content performing well
    UPDATE = "update"       # 0.1-0.3 decay - light refresh
    CONSOLIDATE = "consolidate"  # Content can be merged with similar
    KILL = "kill"           # >0.5 decay + low potential - remove or noindex


@dataclass
class DecayAnalysis:
    """Complete decay analysis for a piece of content."""
    url: str
    decay_score: float
    severity: DecaySeverity
    recommended_action: DecayAction

    # Score components (0-1 each)
    traffic_decay: float
    position_decay: float
    ctr_decay: float
    age_factor: float

    # Raw metrics
    current_traffic: int
    peak_traffic: int
    traffic_decline_pct: float

    current_position: Optional[float]
    peak_position: Optional[float]
    position_decline: float

    months_since_update: int
    last_updated: Optional[str]

    # Actionable recommendation
    action_description: str
    estimated_recovery_potential: int  # Traffic that could be recovered


def calculate_decay_score(
    page: Dict[str, Any],
    historical_data: Optional[List[Dict[str, Any]]] = None
) -> DecayAnalysis:
    """
    Calculate Content Decay Score for a page.

    Args:
        page: Current page metrics with:
            - url: str
            - traffic: int (current monthly traffic)
            - position: float (average position for main keyword)
            - ctr: float (optional, click-through rate)
            - last_updated: str (optional, ISO date)
        historical_data: Optional list of historical snapshots with:
            - date: str (ISO date)
            - traffic: int
            - position: float
            - ctr: float

    Returns:
        DecayAnalysis with complete breakdown
    """
    url = page.get("url", "unknown")
    current_traffic = page.get("traffic", 0)
    current_position = page.get("position")
    current_ctr = page.get("ctr", 0.0)

    # Calculate peak metrics from history or current
    if historical_data and len(historical_data) > 0:
        peak_traffic = max(h.get("traffic", 0) for h in historical_data)
        peak_position = min(
            (h.get("position") for h in historical_data if h.get("position")),
            default=current_position
        )
        peak_ctr = max(h.get("ctr", 0) for h in historical_data)
    else:
        # No history - use current as baseline (no decay)
        peak_traffic = current_traffic
        peak_position = current_position
        peak_ctr = current_ctr

    # Ensure we have valid peaks
    peak_traffic = max(peak_traffic, current_traffic, 1)  # Avoid division by zero
    peak_ctr = max(peak_ctr, current_ctr, 0.01)

    # 1. Traffic Decay (0-1)
    traffic_decay = max(0, (peak_traffic - current_traffic) / peak_traffic)
    traffic_decline_pct = traffic_decay * 100

    # 2. Position Decay (0-1)
    if peak_position and current_position:
        position_decline = max(0, current_position - peak_position)
        position_decay = min(1.0, position_decline / 10)  # Cap at 10 position drop
    else:
        position_decline = 0
        position_decay = 0

    # 3. CTR Decay (0-1)
    if peak_ctr > 0 and current_ctr is not None:
        ctr_decay = max(0, (peak_ctr - current_ctr) / peak_ctr)
    else:
        ctr_decay = 0

    # 4. Age Factor (0-1)
    months_since_update = _calculate_months_since_update(page.get("last_updated"))
    age_factor = min(1.0, months_since_update / 24)  # Max at 24 months

    # Calculate weighted decay score
    decay_score = round(
        traffic_decay * 0.40 +
        position_decay * 0.30 +
        ctr_decay * 0.20 +
        age_factor * 0.10,
        3
    )

    # Determine severity and action
    severity = get_decay_severity(decay_score)
    recommended_action = _determine_action(
        decay_score, current_traffic, peak_traffic, months_since_update
    )

    # Calculate recovery potential
    recovery_potential = _estimate_recovery_potential(
        current_traffic, peak_traffic, decay_score
    )

    return DecayAnalysis(
        url=url,
        decay_score=decay_score,
        severity=severity,
        recommended_action=recommended_action,
        traffic_decay=round(traffic_decay, 3),
        position_decay=round(position_decay, 3),
        ctr_decay=round(ctr_decay, 3),
        age_factor=round(age_factor, 3),
        current_traffic=current_traffic,
        peak_traffic=peak_traffic,
        traffic_decline_pct=round(traffic_decline_pct, 1),
        current_position=current_position,
        peak_position=peak_position,
        position_decline=round(position_decline, 1),
        months_since_update=months_since_update,
        last_updated=page.get("last_updated"),
        action_description=DECAY_ACTIONS.get(severity.value, "Monitor"),
        estimated_recovery_potential=recovery_potential,
    )


def _calculate_months_since_update(last_updated: Optional[str]) -> int:
    """
    Calculate months since last content update.

    Args:
        last_updated: ISO date string or None

    Returns:
        Number of months since update (defaults to 12 if unknown)
    """
    if not last_updated:
        return 12  # Default assumption

    try:
        if isinstance(last_updated, str):
            # Try parsing ISO format
            update_date = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        else:
            update_date = last_updated

        days_since = (datetime.now(update_date.tzinfo) - update_date).days
        return max(0, days_since // 30)
    except Exception:
        return 12


def _determine_action(
    decay_score: float,
    current_traffic: int,
    peak_traffic: int,
    months_old: int
) -> DecayAction:
    """
    Determine recommended action using KUCK framework.

    KUCK = Keep, Update, Consolidate, Kill

    Args:
        decay_score: Calculated decay score
        current_traffic: Current monthly traffic
        peak_traffic: Historical peak traffic
        months_old: Months since last update

    Returns:
        DecayAction enum
    """
    # KEEP: Low decay, still performing
    if decay_score < 0.1:
        return DecayAction.KEEP

    # KILL: High decay + low absolute traffic + very old
    if decay_score > 0.5 and current_traffic < 50 and months_old > 18:
        return DecayAction.KILL

    # CONSOLIDATE: Medium-high decay but content might have value when merged
    if decay_score > 0.4 and current_traffic < 100 and peak_traffic < 500:
        return DecayAction.CONSOLIDATE

    # UPDATE: All other cases - content has value but needs refresh
    return DecayAction.UPDATE


def _estimate_recovery_potential(
    current_traffic: int,
    peak_traffic: int,
    decay_score: float
) -> int:
    """
    Estimate traffic that could be recovered with content refresh.

    Args:
        current_traffic: Current monthly traffic
        peak_traffic: Historical peak traffic
        decay_score: Calculated decay score

    Returns:
        Estimated recoverable monthly traffic
    """
    lost_traffic = peak_traffic - current_traffic

    # Recovery potential depends on decay level
    # Critical decay: 50% recovery expected
    # Major decay: 70% recovery expected
    # Light decay: 90% recovery expected
    if decay_score > 0.5:
        recovery_rate = 0.5
    elif decay_score > 0.3:
        recovery_rate = 0.7
    else:
        recovery_rate = 0.9

    return int(lost_traffic * recovery_rate)


def calculate_batch_decay(
    pages: List[Dict[str, Any]],
    historical_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> List[DecayAnalysis]:
    """
    Calculate decay scores for a batch of pages.

    Args:
        pages: List of page dictionaries
        historical_cache: Optional dict mapping URL -> historical data

    Returns:
        List of DecayAnalysis results, sorted by decay score descending
    """
    historical_cache = historical_cache or {}
    results = []

    for page in pages:
        url = page.get("url", "")
        historical = historical_cache.get(url, [])

        try:
            analysis = calculate_decay_score(page, historical)
            results.append(analysis)
        except Exception as e:
            logger.warning(f"Error calculating decay for '{url}': {e}")

    # Sort by decay score (highest decay first)
    results.sort(key=lambda x: x.decay_score, reverse=True)
    return results


def get_decay_summary(analyses: List[DecayAnalysis]) -> Dict[str, Any]:
    """
    Generate summary statistics from batch decay analysis.

    Args:
        analyses: List of DecayAnalysis results

    Returns:
        Summary dict with distributions and totals
    """
    if not analyses:
        return {
            "total_pages": 0,
            "avg_decay_score": 0,
            "total_lost_traffic": 0,
            "total_recovery_potential": 0,
            "severity_distribution": {},
            "action_distribution": {},
        }

    scores = [a.decay_score for a in analyses]
    lost_traffic = [a.peak_traffic - a.current_traffic for a in analyses]
    recovery = [a.estimated_recovery_potential for a in analyses]

    # Count by severity
    severity_counts = {}
    for sev in DecaySeverity:
        severity_counts[sev.value] = sum(
            1 for a in analyses if a.severity == sev
        )

    # Count by action
    action_counts = {}
    for action in DecayAction:
        action_counts[action.value] = sum(
            1 for a in analyses if a.recommended_action == action
        )

    return {
        "total_pages": len(analyses),
        "avg_decay_score": round(sum(scores) / len(scores), 3),
        "max_decay_score": round(max(scores), 3),
        "total_lost_traffic": sum(lost_traffic),
        "total_recovery_potential": sum(recovery),
        "severity_distribution": severity_counts,
        "action_distribution": action_counts,
        "critical_count": severity_counts.get("critical", 0),
        "update_needed_count": action_counts.get("update", 0),
        "pages_to_review": [
            {
                "url": a.url,
                "decay_score": a.decay_score,
                "severity": a.severity.value,
                "action": a.recommended_action.value,
                "traffic_decline_pct": a.traffic_decline_pct,
                "recovery_potential": a.estimated_recovery_potential,
            }
            for a in analyses[:20]  # Top 20 most decayed
        ],
    }


def get_critical_pages(
    analyses: List[DecayAnalysis],
    min_recovery_potential: int = 100
) -> List[DecayAnalysis]:
    """
    Get pages with critical decay that have recovery potential.

    Args:
        analyses: List of DecayAnalysis results
        min_recovery_potential: Minimum traffic recovery to consider

    Returns:
        List of critical pages worth refreshing
    """
    return [
        a for a in analyses
        if a.severity == DecaySeverity.CRITICAL
        and a.estimated_recovery_potential >= min_recovery_potential
        and a.recommended_action != DecayAction.KILL
    ]


def get_pages_to_kill(
    analyses: List[DecayAnalysis],
    min_decay: float = 0.5,
    max_current_traffic: int = 50
) -> List[DecayAnalysis]:
    """
    Get pages recommended for removal or noindex.

    Args:
        analyses: List of DecayAnalysis results
        min_decay: Minimum decay score
        max_current_traffic: Maximum current traffic

    Returns:
        List of pages to consider removing
    """
    return [
        a for a in analyses
        if a.recommended_action == DecayAction.KILL
        or (a.decay_score >= min_decay and a.current_traffic <= max_current_traffic)
    ]


def get_consolidation_candidates(
    analyses: List[DecayAnalysis]
) -> List[DecayAnalysis]:
    """
    Get pages that should be consolidated with others.

    Args:
        analyses: List of DecayAnalysis results

    Returns:
        List of pages to consider consolidating
    """
    return [
        a for a in analyses
        if a.recommended_action == DecayAction.CONSOLIDATE
    ]


def prioritize_by_recovery_roi(
    analyses: List[DecayAnalysis],
    limit: int = 20
) -> List[DecayAnalysis]:
    """
    Prioritize pages by recovery ROI (recovery potential / decay score).

    Higher ROI = easier to recover valuable traffic.

    Args:
        analyses: List of DecayAnalysis results
        limit: Maximum results to return

    Returns:
        List prioritized by recovery ROI
    """
    # Filter to updateable pages only
    updateable = [
        a for a in analyses
        if a.recommended_action == DecayAction.UPDATE
        and a.estimated_recovery_potential > 0
    ]

    # Calculate ROI score
    def recovery_roi(a: DecayAnalysis) -> float:
        # Inverse decay as "effort" proxy (higher decay = more work)
        effort = max(0.1, a.decay_score)
        return a.estimated_recovery_potential / effort

    sorted_analyses = sorted(updateable, key=recovery_roi, reverse=True)
    return sorted_analyses[:limit]

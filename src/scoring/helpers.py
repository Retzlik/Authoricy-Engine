"""
Scoring Helper Functions and Constants

Contains CTR curves, intent weights, thresholds, and utility functions
used across all scoring calculations.
"""

import math
from typing import Dict, Any, List, Optional
from enum import Enum


# ============================================================================
# CTR CURVE (Based on industry benchmarks - Backlinko/Sistrix 2024 studies)
# ============================================================================

CTR_CURVE: Dict[int, float] = {
    1: 0.317,   # 31.7% CTR for position 1
    2: 0.247,   # 24.7%
    3: 0.187,   # 18.7%
    4: 0.133,   # 13.3%
    5: 0.095,   # 9.5%
    6: 0.069,   # 6.9%
    7: 0.051,   # 5.1%
    8: 0.038,   # 3.8%
    9: 0.029,   # 2.9%
    10: 0.022,  # 2.2%
}

# Extended CTR for positions 11-100 (approximation)
def get_ctr_for_position(position: int) -> float:
    """
    Get estimated CTR for any position.

    Args:
        position: SERP position (1-100)

    Returns:
        Estimated CTR as decimal (0.0 - 1.0)
    """
    if position <= 0:
        return 0.0
    if position <= 10:
        return CTR_CURVE.get(position, 0.01)
    if position <= 20:
        # Page 2: ~0.5-2% CTR
        return 0.01 - (position - 10) * 0.0005
    if position <= 50:
        # Page 3-5: ~0.1-0.5% CTR
        return 0.005 - (position - 20) * 0.0001
    # Page 6+: negligible
    return 0.001


# ============================================================================
# INTENT WEIGHTS
# ============================================================================

class SearchIntent(Enum):
    """Search intent classification."""
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"


INTENT_WEIGHTS: Dict[str, int] = {
    "transactional": 100,   # Ready to buy
    "commercial": 75,       # Researching with intent to buy
    "informational": 50,    # Learning/researching
    "navigational": 25,     # Looking for specific site
}


def get_intent_weight(intent: Optional[str]) -> int:
    """
    Get business value weight for search intent.

    Args:
        intent: Intent string from DataForSEO

    Returns:
        Weight (25-100)
    """
    if not intent:
        return 50  # Default to informational
    return INTENT_WEIGHTS.get(intent.lower(), 50)


# ============================================================================
# VOLUME SCORING
# ============================================================================

def normalize_volume(volume: int, max_volume: int, method: str = "logarithmic") -> float:
    """
    Normalize search volume to 0-100 scale.

    Args:
        volume: Keyword search volume
        max_volume: Maximum volume in dataset (for normalization)
        method: "logarithmic" (default) or "linear"

    Returns:
        Normalized score (0-100)
    """
    if volume <= 0:
        return 0.0

    if max_volume <= 0:
        max_volume = volume

    if method == "logarithmic":
        # Logarithmic normalization - better for wide volume ranges
        return min(100, (math.log10(volume + 1) / math.log10(max_volume + 1)) * 100)
    else:
        # Linear normalization
        return min(100, (volume / max_volume) * 100)


# ============================================================================
# DIFFICULTY THRESHOLDS
# ============================================================================

class DifficultyTier(Enum):
    """Keyword difficulty tiers."""
    EASY = "easy"           # KD 0-30
    MODERATE = "moderate"   # KD 31-50
    HARD = "hard"           # KD 51-70
    VERY_HARD = "very_hard" # KD 71-85
    EXTREME = "extreme"     # KD 86-100


def get_difficulty_tier(kd: int) -> DifficultyTier:
    """
    Classify keyword difficulty into tiers.

    Args:
        kd: Keyword difficulty (0-100)

    Returns:
        DifficultyTier enum
    """
    if kd <= 30:
        return DifficultyTier.EASY
    elif kd <= 50:
        return DifficultyTier.MODERATE
    elif kd <= 70:
        return DifficultyTier.HARD
    elif kd <= 85:
        return DifficultyTier.VERY_HARD
    else:
        return DifficultyTier.EXTREME


# Estimated months to rank based on KD and DR gap
RANKING_TIME_MATRIX: Dict[str, Dict[str, int]] = {
    # DR advantage: months to rank by difficulty tier
    "high_advantage": {  # Site DR 20+ above SERP average
        "easy": 2,
        "moderate": 3,
        "hard": 5,
        "very_hard": 8,
        "extreme": 12,
    },
    "moderate_advantage": {  # Site DR 5-20 above SERP average
        "easy": 3,
        "moderate": 4,
        "hard": 6,
        "very_hard": 10,
        "extreme": 15,
    },
    "neutral": {  # Site DR within 5 of SERP average
        "easy": 4,
        "moderate": 6,
        "hard": 9,
        "very_hard": 14,
        "extreme": 18,
    },
    "disadvantage": {  # Site DR below SERP average
        "easy": 6,
        "moderate": 9,
        "hard": 14,
        "very_hard": 18,
        "extreme": 24,
    },
}


def estimate_ranking_time(kd: int, site_dr: int, serp_avg_dr: int) -> int:
    """
    Estimate months to achieve top-10 ranking.

    Args:
        kd: Keyword difficulty (0-100)
        site_dr: Site's Domain Rating
        serp_avg_dr: Average DR of current top-10 results

    Returns:
        Estimated months to rank
    """
    dr_gap = site_dr - serp_avg_dr

    if dr_gap >= 20:
        advantage = "high_advantage"
    elif dr_gap >= 5:
        advantage = "moderate_advantage"
    elif dr_gap >= -5:
        advantage = "neutral"
    else:
        advantage = "disadvantage"

    tier = get_difficulty_tier(kd)
    return RANKING_TIME_MATRIX[advantage][tier.value]


# ============================================================================
# CONTENT DECAY THRESHOLDS
# ============================================================================

class DecaySeverity(Enum):
    """Content decay severity levels."""
    CRITICAL = "critical"   # >0.5 decay score
    MAJOR = "major"         # 0.3-0.5
    LIGHT = "light"         # 0.1-0.3
    MONITOR = "monitor"     # <0.1


def get_decay_severity(decay_score: float) -> DecaySeverity:
    """
    Classify decay score into severity levels.

    Args:
        decay_score: Decay score (0.0-1.0)

    Returns:
        DecaySeverity enum
    """
    if decay_score > 0.5:
        return DecaySeverity.CRITICAL
    elif decay_score > 0.3:
        return DecaySeverity.MAJOR
    elif decay_score > 0.1:
        return DecaySeverity.LIGHT
    else:
        return DecaySeverity.MONITOR


# Recommended action by decay severity
DECAY_ACTIONS: Dict[str, str] = {
    "critical": "Complete content refresh - rewrite with updated information, new examples, and current data",
    "major": "Major update - add 30-50% new content, update statistics, refresh examples",
    "light": "Light refresh - update dates, statistics, add 1-2 new sections",
    "monitor": "Monitor only - check again in 3 months",
}


# ============================================================================
# OPPORTUNITY CLASSIFICATION
# ============================================================================

class OpportunityType(Enum):
    """Keyword opportunity classifications."""
    QUICK_WIN = "quick_win"         # High opportunity, low effort
    STRATEGIC = "strategic"         # High value, medium effort
    LONG_TERM = "long_term"         # High value, high effort
    MAINTAIN = "maintain"           # Already ranking well
    LOW_PRIORITY = "low_priority"   # Low opportunity score


def classify_opportunity(
    opportunity_score: float,
    current_position: Optional[int],
    personalized_kd: int
) -> OpportunityType:
    """
    Classify keyword into opportunity type.

    Args:
        opportunity_score: Calculated opportunity score (0-100)
        current_position: Current SERP position (None if not ranking)
        personalized_kd: Personalized keyword difficulty

    Returns:
        OpportunityType enum
    """
    # Already ranking top 3
    if current_position and current_position <= 3:
        return OpportunityType.MAINTAIN

    # High opportunity + low difficulty = Quick Win
    if opportunity_score >= 70 and personalized_kd <= 40:
        return OpportunityType.QUICK_WIN

    # High opportunity + medium difficulty = Strategic
    if opportunity_score >= 60 and personalized_kd <= 60:
        return OpportunityType.STRATEGIC

    # High opportunity + high difficulty = Long Term
    if opportunity_score >= 50:
        return OpportunityType.LONG_TERM

    return OpportunityType.LOW_PRIORITY


# ============================================================================
# TRAFFIC POTENTIAL ESTIMATION
# ============================================================================

def estimate_traffic_potential(
    volume: int,
    current_position: Optional[int],
    target_position: int = 3
) -> int:
    """
    Estimate monthly traffic gain from ranking improvement.

    Args:
        volume: Monthly search volume
        current_position: Current position (None if not ranking)
        target_position: Target position (default: 3)

    Returns:
        Estimated monthly traffic gain
    """
    target_ctr = get_ctr_for_position(target_position)
    current_ctr = get_ctr_for_position(current_position or 100)

    traffic_gain = volume * (target_ctr - current_ctr)
    return max(0, int(traffic_gain))


def estimate_traffic_value(
    traffic: int,
    cpc: float,
    conversion_rate: float = 0.02
) -> float:
    """
    Estimate traffic value (SEO equivalent of PPC cost).

    Args:
        traffic: Monthly organic traffic
        cpc: Cost per click (from DataForSEO)
        conversion_rate: Assumed conversion rate (default 2%)

    Returns:
        Monthly traffic value in currency units
    """
    return traffic * cpc


# ============================================================================
# AGGREGATION HELPERS
# ============================================================================

def calculate_weighted_average(
    items: List[Dict[str, Any]],
    value_key: str,
    weight_key: str
) -> float:
    """
    Calculate weighted average from list of items.

    Args:
        items: List of dictionaries
        value_key: Key for value to average
        weight_key: Key for weight

    Returns:
        Weighted average
    """
    if not items:
        return 0.0

    total_weight = sum(item.get(weight_key, 1) for item in items)
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(
        item.get(value_key, 0) * item.get(weight_key, 1)
        for item in items
    )

    return weighted_sum / total_weight


def percentile(values: List[float], p: float) -> float:
    """
    Calculate percentile value.

    Args:
        values: List of numeric values
        p: Percentile (0-100)

    Returns:
        Value at percentile
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return sorted_values[int(k)]

    return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)

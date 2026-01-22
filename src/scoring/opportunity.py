"""
Opportunity Score Calculator

Calculates a composite score (0-100) representing the overall opportunity
value of targeting a keyword, considering:

1. Search Volume (20%) - Demand potential
2. Personalized Difficulty Inverse (20%) - Rankability
3. Business Intent (20%) - Commercial value
4. Position Gap (20%) - Traffic potential from improvement
5. Topical Alignment (20%) - Relevance to domain expertise

Formula:
    Opportunity_Score = (
        Volume_Score × 0.20 +
        Difficulty_Inverse × 0.20 +
        Business_Intent × 0.20 +
        Position_Gap × 0.20 +
        Topical_Alignment × 0.20
    ) × Freshness_Modifier
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .helpers import (
    normalize_volume,
    get_intent_weight,
    get_ctr_for_position,
    estimate_traffic_potential,
    classify_opportunity,
    OpportunityType,
)
from .difficulty import calculate_personalized_difficulty, DifficultyAnalysis

logger = logging.getLogger(__name__)


@dataclass
class OpportunityAnalysis:
    """Complete opportunity analysis for a keyword."""
    keyword: str
    opportunity_score: int
    opportunity_type: OpportunityType

    # Score components (0-100 each)
    volume_score: float
    difficulty_score: float  # Inverse of personalized difficulty
    intent_score: float
    position_gap_score: float
    topical_score: float

    # Raw data
    search_volume: int
    current_position: Optional[int]
    personalized_difficulty: int
    intent: str

    # Business metrics
    estimated_traffic_gain: int
    estimated_monthly_value: float
    estimated_months_to_rank: int

    # Difficulty analysis (embedded)
    difficulty_analysis: DifficultyAnalysis


def calculate_opportunity_score(
    keyword: Dict[str, Any],
    domain_data: Dict[str, Any],
    max_volume: int = 10000,
    serp_data: Optional[Dict[str, Any]] = None,
    topical_alignment: float = 0.75
) -> OpportunityAnalysis:
    """
    Calculate comprehensive Opportunity Score for a keyword.

    Args:
        keyword: Keyword data with:
            - keyword: str
            - search_volume: int
            - keyword_difficulty: int
            - position: int (optional, current ranking position)
            - intent: str (transactional/commercial/informational/navigational)
            - cpc: float (optional, for value calculation)
        domain_data: Domain metrics with:
            - domain_rank: int
            - categories: List
        max_volume: Maximum volume for normalization (from dataset)
        serp_data: Optional SERP analysis data
        topical_alignment: Default topical alignment score if not calculable

    Returns:
        OpportunityAnalysis with full breakdown
    """
    keyword_str = keyword.get("keyword", "unknown")
    volume = keyword.get("search_volume", 0)
    current_pos = keyword.get("position")
    intent = keyword.get("intent", "informational")
    cpc = keyword.get("cpc", 1.0)

    # 1. Calculate Personalized Difficulty first
    difficulty_analysis = calculate_personalized_difficulty(
        keyword, domain_data, serp_data
    )
    personalized_kd = difficulty_analysis.personalized_difficulty

    # 2. Volume Score (0-100, logarithmic)
    volume_score = normalize_volume(volume, max_volume, method="logarithmic")

    # 3. Difficulty Score (inverse - higher is better)
    difficulty_score = 100 - personalized_kd

    # 4. Intent Score (business value)
    intent_score = float(get_intent_weight(intent))

    # 5. Position Gap Score (traffic improvement potential)
    position_gap_score = _calculate_position_gap_score(
        volume, current_pos
    )

    # 6. Topical Alignment Score
    # Can be enhanced with category matching, but default to provided value
    topical_score = _calculate_topical_alignment(
        keyword, domain_data
    ) or (topical_alignment * 100)

    # Calculate weighted opportunity score
    raw_score = (
        volume_score * 0.20 +
        difficulty_score * 0.20 +
        intent_score * 0.20 +
        position_gap_score * 0.20 +
        topical_score * 0.20
    )

    # Apply freshness modifier (if SERP data available)
    freshness_modifier = _get_freshness_modifier(serp_data)
    opportunity_score = round(raw_score * freshness_modifier)

    # Classify opportunity type
    opportunity_type = classify_opportunity(
        opportunity_score, current_pos, personalized_kd
    )

    # Calculate business metrics
    traffic_gain = estimate_traffic_potential(volume, current_pos, target_position=3)
    monthly_value = traffic_gain * cpc

    return OpportunityAnalysis(
        keyword=keyword_str,
        opportunity_score=min(100, max(0, opportunity_score)),
        opportunity_type=opportunity_type,
        volume_score=round(volume_score, 1),
        difficulty_score=round(difficulty_score, 1),
        intent_score=round(intent_score, 1),
        position_gap_score=round(position_gap_score, 1),
        topical_score=round(topical_score, 1),
        search_volume=volume,
        current_position=current_pos,
        personalized_difficulty=personalized_kd,
        intent=intent,
        estimated_traffic_gain=traffic_gain,
        estimated_monthly_value=round(monthly_value, 2),
        estimated_months_to_rank=difficulty_analysis.estimated_months_to_rank,
        difficulty_analysis=difficulty_analysis,
    )


def _calculate_position_gap_score(
    volume: int,
    current_position: Optional[int],
    target_position: int = 3
) -> float:
    """
    Calculate position gap score based on traffic improvement potential.

    Higher score = more traffic to gain from ranking improvement.

    Args:
        volume: Monthly search volume
        current_position: Current SERP position (None if not ranking)
        target_position: Target position (default 3)

    Returns:
        Position gap score (0-100)
    """
    if volume <= 0:
        return 0.0

    current_ctr = get_ctr_for_position(current_position or 100)
    target_ctr = get_ctr_for_position(target_position)

    # CTR improvement as percentage of max possible
    ctr_improvement = target_ctr - current_ctr
    max_ctr_improvement = target_ctr  # From position 100 to target

    if max_ctr_improvement <= 0:
        return 0.0

    # Score based on relative improvement potential
    return min(100, (ctr_improvement / max_ctr_improvement) * 100)


def _calculate_topical_alignment(
    keyword: Dict[str, Any],
    domain_data: Dict[str, Any]
) -> Optional[float]:
    """
    Calculate topical alignment score.

    Higher score = keyword is in a category where domain has authority.

    Args:
        keyword: Keyword with optional category
        domain_data: Domain data with categories

    Returns:
        Topical alignment score (0-100) or None if can't calculate
    """
    keyword_category = keyword.get("category")
    domain_categories = domain_data.get("categories", [])

    if not keyword_category or not domain_categories:
        return None

    # Find if domain ranks in this category
    for cat in domain_categories:
        cat_name = cat.get("name", "").lower()
        cat_code = cat.get("code", "").lower()

        if keyword_category.lower() in [cat_name, cat_code]:
            # Found match - score based on keyword count in category
            kw_count = cat.get("keyword_count", 0)
            # More keywords = higher alignment (capped at 100)
            return min(100, kw_count * 2)

        # Partial match
        if keyword_category.lower() in cat_name:
            kw_count = cat.get("keyword_count", 0)
            return min(80, kw_count * 1.5)  # Lower score for partial match

    return None


def _get_freshness_modifier(serp_data: Optional[Dict[str, Any]]) -> float:
    """
    Calculate freshness modifier based on SERP characteristics.

    Some SERPs favor fresh content, others favor established pages.

    Args:
        serp_data: SERP analysis data

    Returns:
        Freshness modifier (0.8 - 1.2)
    """
    if not serp_data:
        return 1.0

    # Check for news/freshness signals
    has_news_results = serp_data.get("has_news_results", False)
    avg_content_age_days = serp_data.get("avg_content_age_days", 365)

    if has_news_results or avg_content_age_days < 90:
        # Fresh content SERP - boost for sites that can publish quickly
        return 1.1

    if avg_content_age_days > 730:  # 2+ years
        # Evergreen SERP - established content wins
        return 0.95

    return 1.0


def calculate_batch_opportunities(
    keywords: List[Dict[str, Any]],
    domain_data: Dict[str, Any],
    serp_cache: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[OpportunityAnalysis]:
    """
    Calculate opportunity scores for a batch of keywords.

    Args:
        keywords: List of keyword dictionaries
        domain_data: Domain metrics
        serp_cache: Optional dict mapping keyword -> SERP data

    Returns:
        List of OpportunityAnalysis results, sorted by score descending
    """
    if not keywords:
        return []

    # Find max volume for normalization
    max_volume = max(kw.get("search_volume", 0) for kw in keywords)
    max_volume = max(max_volume, 100)  # Minimum baseline

    serp_cache = serp_cache or {}
    results = []

    for keyword in keywords:
        keyword_str = keyword.get("keyword", "")
        serp_data = serp_cache.get(keyword_str)

        try:
            analysis = calculate_opportunity_score(
                keyword, domain_data, max_volume, serp_data
            )
            results.append(analysis)
        except Exception as e:
            logger.warning(f"Error calculating opportunity for '{keyword_str}': {e}")

    # Sort by opportunity score (descending)
    results.sort(key=lambda x: x.opportunity_score, reverse=True)
    return results


def get_opportunity_summary(analyses: List[OpportunityAnalysis]) -> Dict[str, Any]:
    """
    Generate summary statistics from batch opportunity analysis.

    Args:
        analyses: List of OpportunityAnalysis results

    Returns:
        Summary dict with distributions and totals
    """
    if not analyses:
        return {
            "total_keywords": 0,
            "avg_opportunity_score": 0,
            "total_traffic_potential": 0,
            "total_monthly_value": 0,
            "type_distribution": {},
        }

    scores = [a.opportunity_score for a in analyses]
    traffic = [a.estimated_traffic_gain for a in analyses]
    values = [a.estimated_monthly_value for a in analyses]

    # Count by opportunity type
    type_counts = {}
    for op_type in OpportunityType:
        type_counts[op_type.value] = sum(
            1 for a in analyses if a.opportunity_type == op_type
        )

    # Top opportunities by type
    quick_wins = [a for a in analyses if a.opportunity_type == OpportunityType.QUICK_WIN]
    strategic = [a for a in analyses if a.opportunity_type == OpportunityType.STRATEGIC]

    return {
        "total_keywords": len(analyses),
        "avg_opportunity_score": round(sum(scores) / len(scores), 1),
        "max_opportunity_score": max(scores),
        "total_traffic_potential": sum(traffic),
        "total_monthly_value": round(sum(values), 2),
        "type_distribution": type_counts,
        "quick_win_count": len(quick_wins),
        "strategic_count": len(strategic),
        "top_10_keywords": [
            {
                "keyword": a.keyword,
                "score": a.opportunity_score,
                "volume": a.search_volume,
                "position": a.current_position,
                "type": a.opportunity_type.value,
            }
            for a in analyses[:10]
        ],
    }


def get_quick_wins(
    analyses: List[OpportunityAnalysis],
    min_score: int = 60,
    max_difficulty: int = 40,
    limit: int = 20
) -> List[OpportunityAnalysis]:
    """
    Extract quick win opportunities.

    Quick wins are high-opportunity, low-difficulty keywords.

    Args:
        analyses: List of OpportunityAnalysis results
        min_score: Minimum opportunity score
        max_difficulty: Maximum personalized difficulty
        limit: Maximum results to return

    Returns:
        Filtered list of quick wins
    """
    quick_wins = [
        a for a in analyses
        if a.opportunity_score >= min_score
        and a.personalized_difficulty <= max_difficulty
        and a.opportunity_type == OpportunityType.QUICK_WIN
    ]

    # Sort by opportunity score
    quick_wins.sort(key=lambda x: x.opportunity_score, reverse=True)
    return quick_wins[:limit]


def get_strategic_opportunities(
    analyses: List[OpportunityAnalysis],
    min_score: int = 50,
    min_volume: int = 1000,
    limit: int = 20
) -> List[OpportunityAnalysis]:
    """
    Extract strategic opportunities.

    Strategic opportunities are high-volume keywords worth long-term investment.

    Args:
        analyses: List of OpportunityAnalysis results
        min_score: Minimum opportunity score
        min_volume: Minimum search volume
        limit: Maximum results to return

    Returns:
        Filtered list of strategic opportunities
    """
    strategic = [
        a for a in analyses
        if a.opportunity_score >= min_score
        and a.search_volume >= min_volume
        and a.opportunity_type in [OpportunityType.STRATEGIC, OpportunityType.LONG_TERM]
    ]

    # Sort by potential value
    strategic.sort(key=lambda x: x.estimated_monthly_value, reverse=True)
    return strategic[:limit]


def prioritize_by_roi(
    analyses: List[OpportunityAnalysis],
    limit: int = 20
) -> List[OpportunityAnalysis]:
    """
    Prioritize keywords by ROI (value / months to rank).

    Args:
        analyses: List of OpportunityAnalysis results
        limit: Maximum results to return

    Returns:
        List prioritized by ROI
    """
    # Calculate ROI score (value per month of investment)
    def roi_score(a: OpportunityAnalysis) -> float:
        months = max(1, a.estimated_months_to_rank)
        return a.estimated_monthly_value / months

    sorted_analyses = sorted(analyses, key=roi_score, reverse=True)
    return sorted_analyses[:limit]

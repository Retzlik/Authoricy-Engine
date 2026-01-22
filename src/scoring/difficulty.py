"""
Personalized Keyword Difficulty Calculator

Implements the MarketMuse methodology for calculating personalized
keyword difficulty based on domain authority and topical expertise.

Formula:
    Personal_KD = Base_KD × (1 - Authority_Advantage)

    Authority_Advantage = min(0.5,
        (Site_DR - Avg_SERP_DR) / 100 +
        Topical_Authority_Bonus
    )

    Topical_Authority_Bonus = min(0.3,
        count(ranked_keywords in same category) / 100
    )
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .helpers import get_difficulty_tier, estimate_ranking_time, DifficultyTier

logger = logging.getLogger(__name__)


@dataclass
class DifficultyAnalysis:
    """Result of personalized difficulty calculation."""
    keyword: str
    base_difficulty: int
    personalized_difficulty: int
    authority_advantage: float
    dr_advantage: float
    topical_bonus: float
    difficulty_tier: DifficultyTier
    estimated_months_to_rank: int
    competitive_gap: str  # "advantage", "neutral", "disadvantage"


def calculate_personalized_difficulty(
    keyword: Dict[str, Any],
    domain_data: Dict[str, Any],
    serp_data: Optional[Dict[str, Any]] = None
) -> DifficultyAnalysis:
    """
    Calculate Personalized Keyword Difficulty.

    A lower personalized difficulty indicates an easier path to ranking
    based on your domain's authority and topical expertise.

    Args:
        keyword: Keyword data with at least:
            - keyword: str
            - keyword_difficulty: int (0-100)
            - category: str (optional)
        domain_data: Domain metrics with:
            - domain_rank: int (DR)
            - categories: List of category objects with keyword counts
        serp_data: Optional SERP analysis data:
            - avg_dr: Average DR of top 10 results
            - avg_backlinks: Average backlinks of top 10

    Returns:
        DifficultyAnalysis with personalized difficulty and breakdown
    """
    keyword_str = keyword.get("keyword", "unknown")
    base_kd = keyword.get("keyword_difficulty", 50)
    site_dr = domain_data.get("domain_rank", 30)

    # Get SERP average DR (from SERP data or estimate)
    if serp_data:
        avg_serp_dr = serp_data.get("avg_dr", 50)
    else:
        # Estimate based on keyword difficulty
        avg_serp_dr = _estimate_serp_dr(base_kd)

    # Calculate DR advantage component
    dr_advantage = max(-0.3, min(0.3, (site_dr - avg_serp_dr) / 100))

    # Calculate topical authority bonus
    topical_bonus = _calculate_topical_bonus(
        keyword.get("category"),
        domain_data.get("categories", [])
    )

    # Combined authority advantage (capped at 0.5)
    authority_advantage = min(0.5, max(0, dr_advantage + topical_bonus))

    # Calculate personalized difficulty
    personalized_kd = round(base_kd * (1 - authority_advantage))

    # Determine competitive gap description
    dr_gap = site_dr - avg_serp_dr
    if dr_gap >= 10:
        competitive_gap = "advantage"
    elif dr_gap >= -10:
        competitive_gap = "neutral"
    else:
        competitive_gap = "disadvantage"

    # Get difficulty tier and ranking time estimate
    difficulty_tier = get_difficulty_tier(personalized_kd)
    months_to_rank = estimate_ranking_time(personalized_kd, site_dr, avg_serp_dr)

    return DifficultyAnalysis(
        keyword=keyword_str,
        base_difficulty=base_kd,
        personalized_difficulty=personalized_kd,
        authority_advantage=round(authority_advantage, 3),
        dr_advantage=round(dr_advantage, 3),
        topical_bonus=round(topical_bonus, 3),
        difficulty_tier=difficulty_tier,
        estimated_months_to_rank=months_to_rank,
        competitive_gap=competitive_gap,
    )


def _calculate_topical_bonus(
    keyword_category: Optional[str],
    domain_categories: List[Dict[str, Any]]
) -> float:
    """
    Calculate topical authority bonus based on category keyword coverage.

    More keywords ranking in the same category = higher topical authority.

    Args:
        keyword_category: Category/topic of the target keyword
        domain_categories: List of categories the domain ranks for

    Returns:
        Topical bonus (0.0 - 0.3)
    """
    if not keyword_category or not domain_categories:
        return 0.0

    # Find matching category
    matching = None
    for category in domain_categories:
        cat_name = category.get("name", "").lower()
        cat_code = category.get("code", "").lower()

        if keyword_category.lower() in [cat_name, cat_code]:
            matching = category
            break

        # Partial match
        if keyword_category.lower() in cat_name or cat_name in keyword_category.lower():
            matching = category
            break

    if not matching:
        return 0.0

    # More keywords in category = higher authority
    category_keywords = matching.get("keyword_count", 0)

    # Scale: 100 keywords = 0.3 bonus (max)
    return min(0.3, category_keywords / 100 * 0.3)


def _estimate_serp_dr(keyword_difficulty: int) -> int:
    """
    Estimate average SERP DR based on keyword difficulty.

    Higher difficulty keywords tend to have higher DR competitors.

    Args:
        keyword_difficulty: Base keyword difficulty (0-100)

    Returns:
        Estimated average DR of top 10 results
    """
    # Rough correlation: KD roughly maps to SERP DR
    # KD 20 -> DR ~35
    # KD 50 -> DR ~55
    # KD 80 -> DR ~75
    return min(90, max(20, int(keyword_difficulty * 0.7 + 20)))


def calculate_batch_difficulty(
    keywords: List[Dict[str, Any]],
    domain_data: Dict[str, Any],
    serp_cache: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[DifficultyAnalysis]:
    """
    Calculate personalized difficulty for a batch of keywords.

    Args:
        keywords: List of keyword dictionaries
        domain_data: Domain metrics
        serp_cache: Optional dict mapping keyword -> SERP data

    Returns:
        List of DifficultyAnalysis results
    """
    results = []
    serp_cache = serp_cache or {}

    for keyword in keywords:
        keyword_str = keyword.get("keyword", "")
        serp_data = serp_cache.get(keyword_str)

        try:
            analysis = calculate_personalized_difficulty(
                keyword, domain_data, serp_data
            )
            results.append(analysis)
        except Exception as e:
            logger.warning(f"Error calculating difficulty for '{keyword_str}': {e}")
            # Return default analysis on error
            results.append(DifficultyAnalysis(
                keyword=keyword_str,
                base_difficulty=keyword.get("keyword_difficulty", 50),
                personalized_difficulty=keyword.get("keyword_difficulty", 50),
                authority_advantage=0.0,
                dr_advantage=0.0,
                topical_bonus=0.0,
                difficulty_tier=DifficultyTier.MODERATE,
                estimated_months_to_rank=6,
                competitive_gap="neutral",
            ))

    return results


def get_difficulty_summary(analyses: List[DifficultyAnalysis]) -> Dict[str, Any]:
    """
    Generate summary statistics from batch difficulty analysis.

    Args:
        analyses: List of DifficultyAnalysis results

    Returns:
        Summary dict with distributions and averages
    """
    if not analyses:
        return {
            "total_keywords": 0,
            "avg_base_difficulty": 0,
            "avg_personalized_difficulty": 0,
            "avg_authority_advantage": 0,
            "tier_distribution": {},
        }

    base_diffs = [a.base_difficulty for a in analyses]
    personal_diffs = [a.personalized_difficulty for a in analyses]
    advantages = [a.authority_advantage for a in analyses]

    # Count by tier
    tier_counts = {}
    for tier in DifficultyTier:
        tier_counts[tier.value] = sum(
            1 for a in analyses if a.difficulty_tier == tier
        )

    # Count by competitive gap
    gap_counts = {
        "advantage": sum(1 for a in analyses if a.competitive_gap == "advantage"),
        "neutral": sum(1 for a in analyses if a.competitive_gap == "neutral"),
        "disadvantage": sum(1 for a in analyses if a.competitive_gap == "disadvantage"),
    }

    return {
        "total_keywords": len(analyses),
        "avg_base_difficulty": round(sum(base_diffs) / len(base_diffs), 1),
        "avg_personalized_difficulty": round(sum(personal_diffs) / len(personal_diffs), 1),
        "difficulty_reduction": round(
            (sum(base_diffs) - sum(personal_diffs)) / len(base_diffs), 1
        ),
        "avg_authority_advantage": round(sum(advantages) / len(advantages), 3),
        "tier_distribution": tier_counts,
        "competitive_position": gap_counts,
        "keywords_with_advantage": sum(1 for a in analyses if a.authority_advantage > 0.1),
    }


def find_easy_wins(
    analyses: List[DifficultyAnalysis],
    max_personalized_kd: int = 35,
    min_advantage: float = 0.1
) -> List[DifficultyAnalysis]:
    """
    Find keywords where you have a significant advantage.

    Args:
        analyses: List of DifficultyAnalysis results
        max_personalized_kd: Maximum personalized KD threshold
        min_advantage: Minimum authority advantage required

    Returns:
        Filtered list of "easy win" keywords
    """
    return [
        a for a in analyses
        if a.personalized_difficulty <= max_personalized_kd
        and a.authority_advantage >= min_advantage
    ]


def find_difficult_keywords(
    analyses: List[DifficultyAnalysis],
    min_base_kd: int = 60
) -> List[DifficultyAnalysis]:
    """
    Find keywords that are difficult even with your advantages.

    Args:
        analyses: List of DifficultyAnalysis results
        min_base_kd: Minimum base difficulty threshold

    Returns:
        Keywords where you're at a disadvantage
    """
    return [
        a for a in analyses
        if a.base_difficulty >= min_base_kd
        and a.competitive_gap == "disadvantage"
    ]

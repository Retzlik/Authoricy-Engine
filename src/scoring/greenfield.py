"""
Greenfield Domain Scoring Module

Provides specialized scoring algorithms for domains with insufficient data.
Implements the Competitor-First methodology from the Greenfield Domain Brief.

Key algorithms:
1. Winnability Score - SERP-based assessment of ranking feasibility
2. Industry Coefficients - Vertical-specific adjustments
3. Beachhead Selection - Entry-point keyword identification
4. Traffic Projections - Three-scenario forecasting
"""

import logging
import statistics
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class DomainMaturity(Enum):
    """Domain maturity classification for routing analysis."""
    GREENFIELD = "greenfield"      # Competitor-first mode (DR <20, KW <50)
    EMERGING = "emerging"          # Hybrid mode (DR 20-35, KW 50-200)
    ESTABLISHED = "established"    # Standard mode (DR >35, KW >200)


class Industry(Enum):
    """Industry verticals with specific coefficient profiles."""
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    YMYL_HEALTH = "ymyl_health"
    YMYL_FINANCE = "ymyl_finance"
    LOCAL_SERVICES = "local_services"
    NEWS_MEDIA = "news_media"
    EDUCATION = "education"
    B2C_CONSUMER = "b2c_consumer"


# Industry-specific coefficients for winnability calculations
INDUSTRY_COEFFICIENTS: Dict[str, Dict[str, Any]] = {
    "saas": {
        "dr_weight": 1.0,
        "kd_multiplier": 1.0,
        "ai_overview_penalty": 20,
        "time_multiplier": 1.0,
        "content_bonus_max": 15,
        "low_dr_bonus": 15,
    },
    "ecommerce": {
        "dr_weight": 0.8,
        "kd_multiplier": 1.2,
        "ai_overview_penalty": 15,
        "time_multiplier": 0.8,
        "content_bonus_max": 10,
        "low_dr_bonus": 20,
    },
    "ymyl_health": {
        "dr_weight": 1.8,
        "kd_multiplier": 1.5,
        "ai_overview_penalty": 30,
        "time_multiplier": 1.5,
        "content_bonus_max": 20,
        "low_dr_bonus": 5,
        "eeat_required": True,
    },
    "ymyl_finance": {
        "dr_weight": 1.7,
        "kd_multiplier": 1.4,
        "ai_overview_penalty": 25,
        "time_multiplier": 1.4,
        "content_bonus_max": 18,
        "low_dr_bonus": 8,
        "eeat_required": True,
    },
    "local_services": {
        "dr_weight": 0.6,
        "kd_multiplier": 0.7,
        "ai_overview_penalty": 10,
        "time_multiplier": 0.6,
        "content_bonus_max": 12,
        "low_dr_bonus": 25,
        "geo_modifier_bonus": 20,
    },
    "news_media": {
        "dr_weight": 1.4,
        "kd_multiplier": 1.3,
        "ai_overview_penalty": 25,
        "time_multiplier": 0.5,
        "content_bonus_max": 20,
        "low_dr_bonus": 10,
        "freshness_critical": True,
    },
    "education": {
        "dr_weight": 1.2,
        "kd_multiplier": 1.1,
        "ai_overview_penalty": 20,
        "time_multiplier": 1.2,
        "content_bonus_max": 18,
        "low_dr_bonus": 12,
        "institutional_bonus": 15,
    },
    "b2c_consumer": {
        "dr_weight": 0.9,
        "kd_multiplier": 1.1,
        "ai_overview_penalty": 18,
        "time_multiplier": 0.9,
        "content_bonus_max": 15,
        "low_dr_bonus": 18,
    },
}


# CTR curves for traffic projections (post-AI Overview era)
CTR_CURVE: Dict[int, float] = {
    1: 0.19,
    2: 0.10,
    3: 0.07,
    4: 0.05,
    5: 0.04,
    6: 0.03,
    7: 0.025,
    8: 0.02,
    9: 0.018,
    10: 0.015,
}

# AI Overview CTR multiplier
AI_OVERVIEW_CTR_MULTIPLIER = 0.16  # Only 16% of normal CTR when AIO present

# Ranking probability by month for new domains
RANKING_PROBABILITY: Dict[int, float] = {
    3: 0.05,
    6: 0.15,
    9: 0.30,
    12: 0.50,
    18: 0.70,
    24: 0.85,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DomainMetrics:
    """Basic domain metrics for maturity classification."""
    domain_rating: int = 0
    organic_keywords: int = 0
    organic_traffic: int = 0
    referring_domains: int = 0


@dataclass
class WinnabilityAnalysis:
    """Complete winnability analysis for a keyword."""
    keyword: str
    winnability_score: float  # 0-100
    personalized_difficulty: float  # Adjusted KD

    # SERP composition
    avg_serp_dr: float
    min_serp_dr: float
    has_low_dr_rankings: bool
    low_dr_positions: List[int] = field(default_factory=list)

    # Content signals
    weak_content_signals: List[str] = field(default_factory=list)
    has_ai_overview: bool = False
    targetable_features: List[str] = field(default_factory=list)

    # Score components
    dr_gap_penalty: float = 0.0
    low_dr_bonus: float = 0.0
    content_bonus: float = 0.0
    ai_penalty: float = 0.0
    kd_penalty: float = 0.0

    # Beachhead classification
    is_beachhead_candidate: bool = False
    beachhead_score: float = 0.0
    estimated_time_to_rank_weeks: int = 0


@dataclass
class BeachheadKeyword:
    """A keyword selected as a beachhead entry point."""
    keyword: str
    search_volume: int
    keyword_difficulty: int
    personalized_difficulty: float
    winnability_score: float
    business_relevance: float

    # SERP insights
    avg_serp_dr: float
    has_ai_overview: bool

    # Recommendation metadata
    beachhead_score: float
    beachhead_priority: int  # 1-5
    recommended_content_type: str
    estimated_time_to_rank_weeks: int
    estimated_traffic_gain: int


@dataclass
class MarketOpportunity:
    """Market opportunity sizing from competitor analysis."""
    tam_volume: int  # Total addressable market
    tam_keywords: int
    sam_volume: int  # Serviceable addressable market
    sam_keywords: int
    som_volume: int  # Serviceable obtainable market
    som_keywords: int
    competitor_shares: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TrafficProjection:
    """Traffic projection for a single scenario."""
    scenario: str  # conservative, expected, aggressive
    confidence: float
    traffic_by_month: Dict[int, int] = field(default_factory=dict)


@dataclass
class TrafficProjections:
    """Three-scenario traffic projections."""
    conservative: TrafficProjection
    expected: TrafficProjection
    aggressive: TrafficProjection


# =============================================================================
# DOMAIN MATURITY CLASSIFICATION
# =============================================================================

def classify_domain_maturity(metrics: DomainMetrics) -> DomainMaturity:
    """
    Classify domain into maturity tier for analysis routing.

    Thresholds based on industry research:
    - DR < 20 with < 50 keywords = insufficient for domain-centric analysis
    - DR 20-35 or 50-200 keywords = partial data, needs supplementation
    - DR > 35 with > 200 keywords = sufficient for full analysis

    Args:
        metrics: Domain metrics object

    Returns:
        DomainMaturity enum value
    """
    dr = metrics.domain_rating or 0
    kw = metrics.organic_keywords or 0
    traffic = metrics.organic_traffic or 0

    # GREENFIELD: Truly new domains
    if (dr < 20 and kw < 50) or (traffic < 100 and kw < 30):
        return DomainMaturity.GREENFIELD

    # EMERGING: Has some data but not enough for full analysis
    if dr < 35 or kw < 200 or traffic < 1000:
        return DomainMaturity.EMERGING

    # ESTABLISHED: Full data available
    return DomainMaturity.ESTABLISHED


def is_greenfield(metrics: DomainMetrics) -> bool:
    """Check if domain should use greenfield analysis."""
    return classify_domain_maturity(metrics) == DomainMaturity.GREENFIELD


def is_emerging(metrics: DomainMetrics) -> bool:
    """Check if domain should use hybrid analysis."""
    return classify_domain_maturity(metrics) == DomainMaturity.EMERGING


# =============================================================================
# WINNABILITY SCORE CALCULATION
# =============================================================================

def calculate_winnability(
    target_dr: int,
    avg_serp_dr: float,
    min_serp_dr: float,
    has_low_dr_rankings: bool,
    weak_content_signals: List[str],
    has_ai_overview: bool,
    keyword_difficulty: int,
    industry: str = "saas",
    has_geo_modifier: bool = False,
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate winnability score (0-100) for a keyword.

    Winnability represents the likelihood of ranking based on SERP composition,
    not just keyword difficulty.

    Args:
        target_dr: Target domain's Domain Rating
        avg_serp_dr: Average DR of top 10 SERP results
        min_serp_dr: Minimum DR found in top 10
        has_low_dr_rankings: True if any DR <30 site ranks in top 10
        weak_content_signals: List of signals like "outdated_content", "thin_content"
        has_ai_overview: True if AI Overview present for this keyword
        keyword_difficulty: Base keyword difficulty (0-100)
        industry: Industry vertical for coefficient lookup
        has_geo_modifier: True if keyword contains geographic modifier

    Returns:
        Tuple of (winnability_score, component_breakdown)
    """
    coef = INDUSTRY_COEFFICIENTS.get(industry, INDUSTRY_COEFFICIENTS["saas"])
    score = 100.0
    components = {}

    # Factor 1: DR Gap (-40 points max)
    dr_gap = avg_serp_dr - target_dr
    if dr_gap > 0:
        # Penalize keywords where SERP DR is much higher
        penalty = min(40, dr_gap * 1.5 * coef["dr_weight"])
        score -= penalty
        components["dr_gap_penalty"] = -penalty
    else:
        # Bonus if our DR exceeds SERP average
        bonus = min(10, abs(dr_gap) * 0.5)
        score += bonus
        components["dr_gap_penalty"] = bonus

    # Factor 2: Low-DR Presence (industry-weighted bonus)
    if has_low_dr_rankings:
        low_dr_bonus = coef["low_dr_bonus"]
        score += low_dr_bonus
        # Extra bonus if low-DR site is in top positions
        if min_serp_dr < target_dr:
            score += 5
            low_dr_bonus += 5
        components["low_dr_bonus"] = low_dr_bonus
    else:
        components["low_dr_bonus"] = 0

    # Factor 3: Weak Content Signals (industry-weighted max)
    content_bonus = min(coef["content_bonus_max"], len(weak_content_signals) * 5)
    score += content_bonus
    components["content_bonus"] = content_bonus

    # Factor 4: AI Overview (industry-weighted penalty)
    if has_ai_overview:
        ai_penalty = coef["ai_overview_penalty"]
        score -= ai_penalty
        components["ai_penalty"] = -ai_penalty
    else:
        components["ai_penalty"] = 0

    # Factor 5: KD Adjustment (industry-weighted multiplier)
    if keyword_difficulty > 30:
        kd_penalty = (keyword_difficulty - 30) * 0.3 * coef["kd_multiplier"]
        score -= kd_penalty
        components["kd_penalty"] = -kd_penalty
    else:
        components["kd_penalty"] = 0

    # Factor 6: Geo modifier bonus (local services)
    if has_geo_modifier and "geo_modifier_bonus" in coef:
        geo_bonus = coef["geo_modifier_bonus"]
        score += geo_bonus
        components["geo_bonus"] = geo_bonus

    return max(0, min(100, score)), components


def calculate_winnability_full(
    keyword: Dict[str, Any],
    target_dr: int,
    serp_data: Dict[str, Any],
    industry: str = "saas",
) -> WinnabilityAnalysis:
    """
    Calculate complete winnability analysis for a keyword.

    Args:
        keyword: Keyword data with keyword, search_volume, keyword_difficulty
        target_dr: Target domain's Domain Rating
        serp_data: SERP analysis data with:
            - results: List of top 10 results with domain_rating, position
            - ai_overview: AI Overview presence
            - featured_snippet: Featured snippet data
            - people_also_ask: PAA questions
        industry: Industry vertical

    Returns:
        Complete WinnabilityAnalysis
    """
    keyword_str = keyword.get("keyword", "unknown")
    keyword_difficulty = keyword.get("keyword_difficulty", 50)

    # Extract SERP metrics
    results = serp_data.get("results", [])
    serp_drs = [r.get("domain_rating", 50) for r in results if r.get("domain_rating")]

    avg_serp_dr = statistics.mean(serp_drs) if serp_drs else 50.0
    min_serp_dr = min(serp_drs) if serp_drs else 50.0

    # Check for low-DR rankings
    low_dr_positions = [
        r.get("position", 0) for r in results
        if r.get("domain_rating") and r.get("domain_rating") < 30
    ]
    has_low_dr_rankings = len(low_dr_positions) > 0

    # Check for weak content signals
    weak_content_signals = []
    for r in results[:5]:
        if r.get("last_updated") and r.get("content_age_days", 0) > 365:
            weak_content_signals.append("outdated_content")
        if r.get("word_count") and r.get("word_count") < 1000:
            weak_content_signals.append("thin_content")
        if r.get("is_forum") or r.get("is_ugc"):
            weak_content_signals.append("ugc_content")

    # Check AI Overview
    has_ai_overview = serp_data.get("ai_overview") is not None

    # Check targetable features
    targetable_features = []
    if serp_data.get("featured_snippet"):
        targetable_features.append("featured_snippet")
    if serp_data.get("people_also_ask"):
        targetable_features.append("paa")
    if serp_data.get("video_carousel"):
        targetable_features.append("video")

    # Calculate winnability
    winnability_score, components = calculate_winnability(
        target_dr=target_dr,
        avg_serp_dr=avg_serp_dr,
        min_serp_dr=min_serp_dr,
        has_low_dr_rankings=has_low_dr_rankings,
        weak_content_signals=weak_content_signals,
        has_ai_overview=has_ai_overview,
        keyword_difficulty=keyword_difficulty,
        industry=industry,
    )

    # Calculate personalized difficulty
    personalized_difficulty = calculate_personalized_difficulty_greenfield(
        base_kd=keyword_difficulty,
        target_dr=target_dr,
        avg_serp_dr=avg_serp_dr,
    )

    # Estimate time to rank
    coef = INDUSTRY_COEFFICIENTS.get(industry, INDUSTRY_COEFFICIENTS["saas"])
    base_weeks = estimate_time_to_rank_base(personalized_difficulty, winnability_score)
    adjusted_weeks = int(base_weeks * coef["time_multiplier"])

    # Check beachhead eligibility
    is_beachhead = (
        winnability_score >= 70 and
        personalized_difficulty <= 30 and
        keyword.get("search_volume", 0) >= 100
    )

    beachhead_score = 0.0
    if is_beachhead:
        beachhead_score = calculate_beachhead_score(
            search_volume=keyword.get("search_volume", 0),
            business_relevance=keyword.get("business_relevance", 0.7),
            winnability_score=winnability_score,
            personalized_difficulty=personalized_difficulty,
        )

    return WinnabilityAnalysis(
        keyword=keyword_str,
        winnability_score=winnability_score,
        personalized_difficulty=personalized_difficulty,
        avg_serp_dr=avg_serp_dr,
        min_serp_dr=min_serp_dr,
        has_low_dr_rankings=has_low_dr_rankings,
        low_dr_positions=low_dr_positions,
        weak_content_signals=weak_content_signals,
        has_ai_overview=has_ai_overview,
        targetable_features=targetable_features,
        dr_gap_penalty=components.get("dr_gap_penalty", 0),
        low_dr_bonus=components.get("low_dr_bonus", 0),
        content_bonus=components.get("content_bonus", 0),
        ai_penalty=components.get("ai_penalty", 0),
        kd_penalty=components.get("kd_penalty", 0),
        is_beachhead_candidate=is_beachhead,
        beachhead_score=beachhead_score,
        estimated_time_to_rank_weeks=adjusted_weeks,
    )


def calculate_personalized_difficulty_greenfield(
    base_kd: int,
    target_dr: int,
    avg_serp_dr: float,
) -> float:
    """
    Calculate personalized keyword difficulty for greenfield domains.

    Formula:
    Personalized KD = Base KD × Authority Multiplier
    Where Authority Multiplier = 1 + (SERP_DR - Your_DR) / 100

    Args:
        base_kd: Base keyword difficulty (0-100)
        target_dr: Target domain's DR (often low for greenfield)
        avg_serp_dr: Average DR of SERP top 10

    Returns:
        Personalized difficulty (0-100)
    """
    authority_gap = avg_serp_dr - target_dr
    authority_multiplier = 1 + (authority_gap / 100)

    # Clamp multiplier between 0.5 and 2.0
    authority_multiplier = max(0.5, min(2.0, authority_multiplier))

    personalized_kd = base_kd * authority_multiplier
    return min(100, max(0, personalized_kd))


def estimate_time_to_rank_base(
    personalized_difficulty: float,
    winnability_score: float,
) -> int:
    """
    Estimate base weeks to achieve page 1 ranking.

    Args:
        personalized_difficulty: Personalized KD (0-100)
        winnability_score: Winnability score (0-100)

    Returns:
        Estimated weeks to rank
    """
    # Base time by difficulty tier
    if personalized_difficulty <= 20:
        base_weeks = 6
    elif personalized_difficulty <= 35:
        base_weeks = 10
    elif personalized_difficulty <= 50:
        base_weeks = 16
    elif personalized_difficulty <= 70:
        base_weeks = 26
    else:
        base_weeks = 40

    # Adjust by winnability (high winnability = faster)
    winnability_factor = 1 + ((50 - winnability_score) / 100)  # 50 is neutral
    adjusted_weeks = int(base_weeks * winnability_factor)

    return max(4, min(52, adjusted_weeks))


# =============================================================================
# BEACHHEAD KEYWORD SELECTION
# =============================================================================

def calculate_beachhead_score(
    search_volume: int,
    business_relevance: float,
    winnability_score: float,
    personalized_difficulty: float,
) -> float:
    """
    Calculate beachhead value score.

    Formula: (Volume × Business_Relevance × Winnability) / (Personalized_KD + 10)

    Higher score = better beachhead candidate.

    Args:
        search_volume: Monthly search volume
        business_relevance: Business relevance (0-1)
        winnability_score: Winnability score (0-100)
        personalized_difficulty: Personalized KD

    Returns:
        Beachhead score
    """
    numerator = search_volume * business_relevance * (winnability_score / 100)
    denominator = personalized_difficulty + 10
    return numerator / denominator


def select_beachhead_keywords(
    keywords: List[Dict[str, Any]],
    winnability_analyses: Dict[str, WinnabilityAnalysis],
    target_count: int = 20,
    max_kd: int = 30,
    min_volume: int = 100,
    min_winnability: float = 70.0,
    min_business_relevance: float = 0.7,
) -> List[BeachheadKeyword]:
    """
    Select beachhead keywords: narrow, winnable cluster to establish dominance.

    Beachhead Criteria:
    1. Winnability score >= 70
    2. Personalized KD <= 30
    3. Search volume >= 100 (practical traffic)
    4. High business relevance
    5. Topically clustered (enables authority building)

    Args:
        keywords: List of keyword dictionaries
        winnability_analyses: Dict mapping keyword -> WinnabilityAnalysis
        target_count: Number of beachhead keywords to select
        max_kd: Maximum personalized KD
        min_volume: Minimum search volume
        min_winnability: Minimum winnability score
        min_business_relevance: Minimum business relevance

    Returns:
        List of BeachheadKeyword objects, prioritized
    """
    candidates = []

    for kw in keywords:
        keyword_str = kw.get("keyword", "")
        analysis = winnability_analyses.get(keyword_str)

        if not analysis:
            continue

        # Apply filters
        if analysis.winnability_score < min_winnability:
            continue
        if analysis.personalized_difficulty > max_kd:
            continue
        if kw.get("search_volume", 0) < min_volume:
            continue
        if kw.get("business_relevance", 0) < min_business_relevance:
            continue

        # Calculate beachhead score
        beachhead_score = calculate_beachhead_score(
            search_volume=kw.get("search_volume", 0),
            business_relevance=kw.get("business_relevance", 0.7),
            winnability_score=analysis.winnability_score,
            personalized_difficulty=analysis.personalized_difficulty,
        )

        candidates.append({
            "keyword": kw,
            "analysis": analysis,
            "beachhead_score": beachhead_score,
        })

    # Sort by beachhead score
    candidates.sort(key=lambda x: x["beachhead_score"], reverse=True)

    # Select top candidates
    beachhead = []
    for i, candidate in enumerate(candidates[:target_count]):
        kw = candidate["keyword"]
        analysis = candidate["analysis"]

        # Determine content type recommendation
        content_type = _recommend_content_type(kw, analysis)

        # Estimate traffic gain (position 5 target for beachhead)
        search_volume = kw.get("search_volume", 0)
        estimated_traffic = int(search_volume * CTR_CURVE.get(5, 0.04))
        if analysis.has_ai_overview:
            estimated_traffic = int(estimated_traffic * AI_OVERVIEW_CTR_MULTIPLIER)

        beachhead.append(BeachheadKeyword(
            keyword=kw.get("keyword", ""),
            search_volume=search_volume,
            keyword_difficulty=kw.get("keyword_difficulty", 0),
            personalized_difficulty=analysis.personalized_difficulty,
            winnability_score=analysis.winnability_score,
            business_relevance=kw.get("business_relevance", 0.7),
            avg_serp_dr=analysis.avg_serp_dr,
            has_ai_overview=analysis.has_ai_overview,
            beachhead_score=candidate["beachhead_score"],
            beachhead_priority=_calculate_priority(i, len(candidates)),
            recommended_content_type=content_type,
            estimated_time_to_rank_weeks=analysis.estimated_time_to_rank_weeks,
            estimated_traffic_gain=estimated_traffic,
        ))

    return beachhead


def _recommend_content_type(
    keyword: Dict[str, Any],
    analysis: WinnabilityAnalysis,
) -> str:
    """Recommend content type based on keyword and SERP features."""
    intent = keyword.get("intent", "informational")
    features = analysis.targetable_features

    if "featured_snippet" in features:
        return "How-to guide with structured headings"
    if "video" in features:
        return "Video + written content"
    if "paa" in features:
        return "FAQ-style comprehensive guide"
    if intent == "transactional":
        return "Product/service page"
    if intent == "commercial":
        return "Comparison or buying guide"
    if intent == "informational":
        return "Educational long-form content"

    return "Comprehensive pillar content"


def _calculate_priority(index: int, total: int) -> int:
    """Calculate priority tier (1-5) based on position in sorted list."""
    if total == 0:
        return 3
    percentile = index / total
    if percentile < 0.1:
        return 1
    if percentile < 0.25:
        return 2
    if percentile < 0.5:
        return 3
    if percentile < 0.75:
        return 4
    return 5


# =============================================================================
# MARKET OPPORTUNITY SIZING
# =============================================================================

def calculate_market_opportunity(
    keywords: List[Dict[str, Any]],
    winnability_analyses: Dict[str, WinnabilityAnalysis],
    competitors: List[Dict[str, Any]],
    min_business_relevance: float = 0.6,
    min_winnability_for_som: float = 50.0,
) -> MarketOpportunity:
    """
    Calculate total market opportunity from competitor landscape.

    Metrics:
    1. TAM - Total search volume in universe
    2. SAM - Keywords matching our offering (business relevant)
    3. SOM - Realistically winnable keywords (winnability > 50)

    Args:
        keywords: List of keyword dictionaries with search_volume, business_relevance
        winnability_analyses: Dict mapping keyword -> WinnabilityAnalysis
        competitors: List of competitor data with traffic, keyword count
        min_business_relevance: Threshold for SAM inclusion
        min_winnability_for_som: Threshold for SOM inclusion

    Returns:
        MarketOpportunity with TAM/SAM/SOM breakdown
    """
    # TAM: Total search volume
    tam_volume = sum(kw.get("search_volume", 0) for kw in keywords)
    tam_keywords = len(keywords)

    # SAM: Business-relevant keywords
    sam_keywords = [
        kw for kw in keywords
        if kw.get("business_relevance", 0) >= min_business_relevance
    ]
    sam_volume = sum(kw.get("search_volume", 0) for kw in sam_keywords)

    # SOM: Winnable keywords
    som_keywords = []
    for kw in sam_keywords:
        keyword_str = kw.get("keyword", "")
        analysis = winnability_analyses.get(keyword_str)
        if analysis and analysis.winnability_score >= min_winnability_for_som:
            som_keywords.append(kw)
    som_volume = sum(kw.get("search_volume", 0) for kw in som_keywords)

    # Competitor market share
    total_traffic = sum(c.get("organic_traffic", 0) for c in competitors)
    competitor_shares = []
    for comp in competitors:
        traffic = comp.get("organic_traffic", 0)
        share = (traffic / total_traffic * 100) if total_traffic > 0 else 0
        competitor_shares.append({
            "domain": comp.get("domain", "unknown"),
            "traffic": traffic,
            "share_percent": round(share, 1),
            "keyword_count": comp.get("organic_keywords", 0),
        })

    competitor_shares.sort(key=lambda x: x["share_percent"], reverse=True)

    return MarketOpportunity(
        tam_volume=tam_volume,
        tam_keywords=tam_keywords,
        sam_volume=sam_volume,
        sam_keywords=len(sam_keywords),
        som_volume=som_volume,
        som_keywords=len(som_keywords),
        competitor_shares=competitor_shares,
    )


# =============================================================================
# TRAFFIC PROJECTIONS
# =============================================================================

def project_traffic_scenarios(
    beachhead_keywords: List[BeachheadKeyword],
    growth_keywords: List[Dict[str, Any]],
    winnability_analyses: Dict[str, WinnabilityAnalysis],
    domain_maturity: DomainMaturity = DomainMaturity.GREENFIELD,
) -> TrafficProjections:
    """
    Generate three-scenario traffic projections.

    Scenarios:
    - Conservative (75% confidence): Assumes headwinds, slower progress
    - Expected (50% confidence): Mid-range, standard timelines
    - Aggressive (25% confidence): Best case, everything goes well

    Based on:
    - Ahrefs data: Only 1.74% of new pages reach top 10 in year 1
    - AI Overview impact: 32% CTR reduction when present
    - Google Sandbox: 3-9 month trust-building period

    Args:
        beachhead_keywords: Selected beachhead keywords
        growth_keywords: Additional growth-phase keywords
        winnability_analyses: Winnability data for keywords
        domain_maturity: Domain classification

    Returns:
        TrafficProjections with three scenarios
    """
    scenarios = {}
    scenario_multipliers = [
        ("conservative", 0.6, 0.75),
        ("expected", 1.0, 0.50),
        ("aggressive", 1.5, 0.25),
    ]

    for scenario_name, multiplier, confidence in scenario_multipliers:
        monthly_traffic = {}

        for month in [3, 6, 9, 12, 18, 24]:
            ranking_prob = RANKING_PROBABILITY.get(month, 0.5) * multiplier

            # Beachhead keywords (easier, rank faster)
            beachhead_traffic = 0
            for bh in beachhead_keywords:
                expected_position = _estimate_position_at_month(
                    bh.winnability_score,
                    bh.personalized_difficulty,
                    month,
                )
                ctr = CTR_CURVE.get(expected_position, 0.01)

                if bh.has_ai_overview:
                    ctr *= AI_OVERVIEW_CTR_MULTIPLIER

                kw_traffic = bh.search_volume * ctr * ranking_prob
                beachhead_traffic += kw_traffic

            # Growth keywords (harder, rank slower)
            growth_traffic = 0
            growth_ranking_prob = ranking_prob * 0.5  # Harder keywords rank slower

            for kw in growth_keywords[:50]:
                keyword_str = kw.get("keyword", "")
                analysis = winnability_analyses.get(keyword_str)

                if not analysis:
                    continue

                expected_position = _estimate_position_at_month(
                    analysis.winnability_score,
                    analysis.personalized_difficulty,
                    month,
                ) + 5  # Worse positions for growth keywords

                ctr = CTR_CURVE.get(min(10, expected_position), 0.005)

                if analysis.has_ai_overview:
                    ctr *= AI_OVERVIEW_CTR_MULTIPLIER

                kw_traffic = kw.get("search_volume", 0) * ctr * growth_ranking_prob
                growth_traffic += kw_traffic

            monthly_traffic[month] = int(beachhead_traffic + growth_traffic)

        scenarios[scenario_name] = TrafficProjection(
            scenario=scenario_name,
            confidence=confidence,
            traffic_by_month=monthly_traffic,
        )

    return TrafficProjections(
        conservative=scenarios["conservative"],
        expected=scenarios["expected"],
        aggressive=scenarios["aggressive"],
    )


def _estimate_position_at_month(
    winnability_score: float,
    personalized_difficulty: float,
    month: int,
) -> int:
    """
    Estimate expected ranking position at a given month.

    Higher winnability and lower difficulty = better positions sooner.
    """
    # Base position starts at 100 (not ranking)
    # Improves over time based on winnability

    # Ranking progress factor (0-1)
    progress = RANKING_PROBABILITY.get(month, 0.5)

    # Winnability determines ultimate achievable position
    if winnability_score >= 85:
        target_position = 3
    elif winnability_score >= 70:
        target_position = 5
    elif winnability_score >= 55:
        target_position = 8
    elif winnability_score >= 40:
        target_position = 12
    else:
        target_position = 20

    # Calculate expected position (interpolate from 100 to target)
    expected_position = int(100 - (100 - target_position) * progress)

    # Adjust for difficulty (higher difficulty = slower progress)
    difficulty_factor = 1 + (personalized_difficulty - 30) / 100
    expected_position = int(expected_position * difficulty_factor)

    return max(1, min(100, expected_position))


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_industry_from_string(industry_str: str) -> str:
    """Normalize industry string to valid key."""
    industry_lower = industry_str.lower().replace(" ", "_").replace("-", "_")

    # Direct mappings
    mappings = {
        "saas": "saas",
        "software": "saas",
        "b2b_saas": "saas",
        "ecommerce": "ecommerce",
        "e_commerce": "ecommerce",
        "retail": "ecommerce",
        "health": "ymyl_health",
        "healthcare": "ymyl_health",
        "medical": "ymyl_health",
        "finance": "ymyl_finance",
        "financial": "ymyl_finance",
        "fintech": "ymyl_finance",
        "local": "local_services",
        "local_service": "local_services",
        "local_business": "local_services",
        "news": "news_media",
        "media": "news_media",
        "publishing": "news_media",
        "education": "education",
        "edtech": "education",
        "b2c": "b2c_consumer",
        "consumer": "b2c_consumer",
        "dtc": "b2c_consumer",
    }

    return mappings.get(industry_lower, "saas")


def requires_eeat_compliance(industry: str) -> bool:
    """Check if industry requires E-E-A-T compliance."""
    coef = INDUSTRY_COEFFICIENTS.get(industry, {})
    return coef.get("eeat_required", False)


def get_coefficient(industry: str, coefficient_name: str, default: Any = None) -> Any:
    """Get a specific coefficient for an industry."""
    coef = INDUSTRY_COEFFICIENTS.get(industry, INDUSTRY_COEFFICIENTS["saas"])
    return coef.get(coefficient_name, default)


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def calculate_batch_winnability(
    keywords: List[Dict[str, Any]],
    target_dr: int,
    serp_cache: Dict[str, Dict[str, Any]],
    industry: str = "saas",
) -> Dict[str, WinnabilityAnalysis]:
    """
    Calculate winnability for a batch of keywords.

    Args:
        keywords: List of keyword dictionaries
        target_dr: Target domain's DR
        serp_cache: Dict mapping keyword -> SERP data
        industry: Industry vertical

    Returns:
        Dict mapping keyword -> WinnabilityAnalysis
    """
    results = {}

    for kw in keywords:
        keyword_str = kw.get("keyword", "")
        serp_data = serp_cache.get(keyword_str, {})

        try:
            analysis = calculate_winnability_full(
                keyword=kw,
                target_dr=target_dr,
                serp_data=serp_data,
                industry=industry,
            )
            results[keyword_str] = analysis
        except Exception as e:
            logger.warning(f"Error calculating winnability for '{keyword_str}': {e}")

    return results


def get_winnability_summary(
    analyses: Dict[str, WinnabilityAnalysis]
) -> Dict[str, Any]:
    """
    Generate summary statistics from winnability analyses.

    Args:
        analyses: Dict mapping keyword -> WinnabilityAnalysis

    Returns:
        Summary dict with distributions and counts
    """
    if not analyses:
        return {
            "total_keywords": 0,
            "avg_winnability": 0,
            "beachhead_count": 0,
            "distribution": {},
        }

    values = list(analyses.values())
    scores = [a.winnability_score for a in values]

    # Distribution by tier
    distribution = {
        "excellent": sum(1 for s in scores if s >= 80),
        "good": sum(1 for s in scores if 65 <= s < 80),
        "moderate": sum(1 for s in scores if 50 <= s < 65),
        "challenging": sum(1 for s in scores if 35 <= s < 50),
        "difficult": sum(1 for s in scores if s < 35),
    }

    return {
        "total_keywords": len(values),
        "avg_winnability": round(statistics.mean(scores), 1),
        "max_winnability": max(scores),
        "min_winnability": min(scores),
        "beachhead_count": sum(1 for a in values if a.is_beachhead_candidate),
        "ai_overview_count": sum(1 for a in values if a.has_ai_overview),
        "low_dr_opportunity_count": sum(1 for a in values if a.has_low_dr_rankings),
        "distribution": distribution,
    }

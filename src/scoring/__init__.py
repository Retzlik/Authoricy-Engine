"""
Scoring Module for Authoricy Intelligence Engine

This module provides three core scoring calculations:

1. **Opportunity Score** (0-100)
   Composite score representing keyword targeting value.
   Components: Volume, Personalized Difficulty, Intent, Position Gap, Topical Alignment

2. **Personalized Difficulty** (0-100)
   Adjusted keyword difficulty based on domain authority and topical expertise.
   Uses MarketMuse methodology: Base_KD × (1 - Authority_Advantage)

3. **Content Decay Score** (0-1)
   Identifies content losing traffic/rankings that needs refresh.
   Components: Traffic Decay, Position Decay, CTR Decay, Age Factor

Example Usage:
    from src.scoring import (
        calculate_opportunity_score,
        calculate_personalized_difficulty,
        calculate_decay_score,
        OpportunityAnalysis,
        DifficultyAnalysis,
        DecayAnalysis,
    )

    # Calculate opportunity for a keyword
    keyword = {
        "keyword": "project management software",
        "search_volume": 2400,
        "keyword_difficulty": 52,
        "intent": "commercial",
        "position": 15,
    }

    domain_data = {
        "domain_rank": 45,
        "categories": [{"name": "Software", "keyword_count": 150}],
    }

    analysis = calculate_opportunity_score(keyword, domain_data)
    print(f"Opportunity Score: {analysis.opportunity_score}")
    print(f"Personalized KD: {analysis.personalized_difficulty}")
    print(f"Traffic Potential: {analysis.estimated_traffic_gain}")
"""

# Helper utilities and constants
from .helpers import (
    # CTR and volume
    CTR_CURVE,
    get_ctr_for_position,
    normalize_volume,

    # Intent
    INTENT_WEIGHTS,
    SearchIntent,
    get_intent_weight,

    # Difficulty helpers
    DifficultyTier,
    get_difficulty_tier,
    RANKING_TIME_MATRIX,
    estimate_ranking_time,

    # Decay helpers
    DecaySeverity,
    get_decay_severity,
    DECAY_ACTIONS,

    # Opportunity helpers
    OpportunityType,
    classify_opportunity,

    # Traffic estimation
    estimate_traffic_potential,
    estimate_traffic_value,

    # Aggregation
    calculate_weighted_average,
    percentile,
)

# Personalized Difficulty
from .difficulty import (
    DifficultyAnalysis,
    calculate_personalized_difficulty,
    calculate_batch_difficulty,
    get_difficulty_summary,
    find_easy_wins,
    find_difficult_keywords,
)

# Opportunity Score
from .opportunity import (
    OpportunityAnalysis,
    calculate_opportunity_score,
    calculate_batch_opportunities,
    get_opportunity_summary,
    get_quick_wins,
    get_strategic_opportunities,
    prioritize_by_roi,
)

# Content Decay Score
from .decay import (
    DecayAction,
    DecayAnalysis,
    calculate_decay_score,
    calculate_batch_decay,
    get_decay_summary,
    get_critical_pages,
    get_pages_to_kill,
    get_consolidation_candidates,
    prioritize_by_recovery_roi,
)

# Greenfield Domain Scoring
from .greenfield import (
    # Enums
    DomainMaturity,
    Industry,

    # Data classes
    DomainMetrics,
    WinnabilityAnalysis,
    BeachheadKeyword,
    MarketOpportunity,
    TrafficProjection,
    TrafficProjections,

    # Classification
    classify_domain_maturity,
    is_greenfield,
    is_emerging,

    # Winnability
    calculate_winnability,
    calculate_winnability_full,
    calculate_personalized_difficulty_greenfield,
    calculate_batch_winnability,
    get_winnability_summary,

    # Beachhead
    calculate_beachhead_score,
    select_beachhead_keywords,

    # Market opportunity
    calculate_market_opportunity,

    # Traffic projections
    project_traffic_scenarios,

    # Utilities
    get_industry_from_string,
    requires_eeat_compliance,
    get_coefficient,
    INDUSTRY_COEFFICIENTS,
)

__all__ = [
    # Helpers
    "CTR_CURVE",
    "get_ctr_for_position",
    "normalize_volume",
    "INTENT_WEIGHTS",
    "SearchIntent",
    "get_intent_weight",
    "DifficultyTier",
    "get_difficulty_tier",
    "RANKING_TIME_MATRIX",
    "estimate_ranking_time",
    "DecaySeverity",
    "get_decay_severity",
    "DECAY_ACTIONS",
    "OpportunityType",
    "classify_opportunity",
    "estimate_traffic_potential",
    "estimate_traffic_value",
    "calculate_weighted_average",
    "percentile",

    # Difficulty
    "DifficultyAnalysis",
    "calculate_personalized_difficulty",
    "calculate_batch_difficulty",
    "get_difficulty_summary",
    "find_easy_wins",
    "find_difficult_keywords",

    # Opportunity
    "OpportunityAnalysis",
    "calculate_opportunity_score",
    "calculate_batch_opportunities",
    "get_opportunity_summary",
    "get_quick_wins",
    "get_strategic_opportunities",
    "prioritize_by_roi",

    # Decay
    "DecayAction",
    "DecayAnalysis",
    "calculate_decay_score",
    "calculate_batch_decay",
    "get_decay_summary",
    "get_critical_pages",
    "get_pages_to_kill",
    "get_consolidation_candidates",
    "prioritize_by_recovery_roi",

    # Greenfield
    "DomainMaturity",
    "Industry",
    "DomainMetrics",
    "WinnabilityAnalysis",
    "BeachheadKeyword",
    "MarketOpportunity",
    "TrafficProjection",
    "TrafficProjections",
    "classify_domain_maturity",
    "is_greenfield",
    "is_emerging",
    "calculate_winnability",
    "calculate_winnability_full",
    "calculate_personalized_difficulty_greenfield",
    "calculate_batch_winnability",
    "get_winnability_summary",
    "calculate_beachhead_score",
    "select_beachhead_keywords",
    "calculate_market_opportunity",
    "project_traffic_scenarios",
    "get_industry_from_string",
    "requires_eeat_compliance",
    "get_coefficient",
    "INDUSTRY_COEFFICIENTS",
]

__version__ = "1.1.0"  # Added greenfield scoring

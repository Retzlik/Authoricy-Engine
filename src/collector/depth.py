"""
Collection Depth Configuration

Controls the thoroughness vs cost trade-off for data collection.
Higher depth = more data = better insights = higher API cost.

Presets:
- testing: Development/debugging (~$0.30)
- basic: Quick audits (~$1-2)
- balanced: Standard clients (~$3-5)
- comprehensive: Important clients (~$8-15)
- enterprise: Maximum depth (~$20-30)

Usage:
    from src.collector.depth import CollectionDepth

    # Use a preset
    depth = CollectionDepth.balanced()

    # Or customize
    depth = CollectionDepth.balanced()
    depth.max_seed_keywords = 40  # Override specific value

    # Or start from scratch
    depth = CollectionDepth(
        max_seed_keywords=30,
        keyword_universe_limit=1000,
        ...
    )
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)


# Valid preset names
DepthPreset = Literal["testing", "basic", "balanced", "comprehensive", "enterprise"]


@dataclass
class CollectionDepth:
    """
    Configuration for data collection depth.

    All limits are designed to scale proportionally:
    - More seeds = more keywords discovered
    - More keywords = more need for intent/difficulty/SERP analysis

    Attributes:
        name: Preset name for logging

        # Discovery - controls breadth of keyword exploration
        max_seed_keywords: Number of seed keywords for expansion
        keyword_universe_limit: Max keywords from keywords_for_site API
        keyword_gaps_limit: Max keyword gap opportunities to find
        expansion_limit_per_seed: Results per seed expansion call

        # Analysis - controls depth of keyword understanding
        intent_classification_limit: How many keywords get intent labels
        difficulty_scoring_limit: How many keywords get KD scores
        serp_analysis_limit: How many keywords get SERP feature analysis

        # Context - supporting data for strategy
        questions_limit: How many keywords to get PAA/questions for
        historical_volume_limit: How many keywords get trend data
        traffic_estimation_limit: How many keywords get traffic estimates
    """

    # Preset name (for logging)
    name: str = "custom"

    # Discovery
    max_seed_keywords: int = 5
    keyword_universe_limit: int = 500
    keyword_gaps_limit: int = 200
    expansion_limit_per_seed: int = 50

    # Analysis
    intent_classification_limit: int = 200
    difficulty_scoring_limit: int = 200
    serp_analysis_limit: int = 20

    # Context
    questions_limit: int = 5
    historical_volume_limit: int = 10
    traffic_estimation_limit: int = 50

    # Estimated cost (informational only)
    estimated_cost_usd: float = field(default=0.0, repr=False)

    def __post_init__(self):
        """Log the depth configuration."""
        logger.info(
            f"[DEPTH] Using '{self.name}' preset: "
            f"seeds={self.max_seed_keywords}, universe={self.keyword_universe_limit}, "
            f"gaps={self.keyword_gaps_limit}, intent={self.intent_classification_limit}, "
            f"serp={self.serp_analysis_limit}"
        )

    # =========================================================================
    # PRESETS
    # =========================================================================

    @classmethod
    def testing(cls) -> "CollectionDepth":
        """
        Minimal data for development and debugging.

        Use when:
        - Testing code changes
        - Debugging pipeline issues
        - Quick sanity checks

        Est. cost: ~$0.30-0.50
        """
        return cls(
            name="testing",
            # Discovery
            max_seed_keywords=5,
            keyword_universe_limit=200,
            keyword_gaps_limit=100,
            expansion_limit_per_seed=30,
            # Analysis
            intent_classification_limit=50,
            difficulty_scoring_limit=50,
            serp_analysis_limit=10,
            # Context
            questions_limit=3,
            historical_volume_limit=5,
            traffic_estimation_limit=20,
            # Cost
            estimated_cost_usd=0.40,
        )

    @classmethod
    def basic(cls) -> "CollectionDepth":
        """
        Quick analysis for small sites or audits.

        Use when:
        - Small business sites (<100 pages)
        - Quick competitive check
        - Budget-conscious clients

        Est. cost: ~$1-2
        """
        return cls(
            name="basic",
            # Discovery
            max_seed_keywords=10,
            keyword_universe_limit=500,
            keyword_gaps_limit=200,
            expansion_limit_per_seed=50,
            # Analysis
            intent_classification_limit=200,
            difficulty_scoring_limit=200,
            serp_analysis_limit=20,
            # Context
            questions_limit=5,
            historical_volume_limit=10,
            traffic_estimation_limit=50,
            # Cost
            estimated_cost_usd=1.50,
        )

    @classmethod
    def balanced(cls) -> "CollectionDepth":
        """
        Standard analysis for most clients.

        Use when:
        - Medium-sized sites (100-1000 pages)
        - Standard SEO audits
        - Monthly reporting

        Est. cost: ~$3-5
        """
        return cls(
            name="balanced",
            # Discovery
            max_seed_keywords=25,
            keyword_universe_limit=1000,
            keyword_gaps_limit=500,
            expansion_limit_per_seed=50,
            # Analysis
            intent_classification_limit=500,
            difficulty_scoring_limit=500,
            serp_analysis_limit=50,
            # Context
            questions_limit=15,
            historical_volume_limit=25,
            traffic_estimation_limit=100,
            # Cost
            estimated_cost_usd=4.00,
        )

    @classmethod
    def comprehensive(cls) -> "CollectionDepth":
        """
        Deep analysis for important clients.

        Use when:
        - Large sites (1000+ pages)
        - Strategic planning
        - Competitive deep-dives
        - Enterprise clients

        Est. cost: ~$8-15
        """
        return cls(
            name="comprehensive",
            # Discovery
            max_seed_keywords=50,
            keyword_universe_limit=2000,
            keyword_gaps_limit=1000,
            expansion_limit_per_seed=75,
            # Analysis
            intent_classification_limit=1000,
            difficulty_scoring_limit=1000,
            serp_analysis_limit=100,
            # Context
            questions_limit=30,
            historical_volume_limit=50,
            traffic_estimation_limit=200,
            # Cost
            estimated_cost_usd=12.00,
        )

    @classmethod
    def enterprise(cls) -> "CollectionDepth":
        """
        Maximum depth for large sites with big budgets.

        Use when:
        - Very large sites (10,000+ pages)
        - Agency white-label reports
        - Full market analysis
        - Quarterly strategic reviews

        Est. cost: ~$20-30
        """
        return cls(
            name="enterprise",
            # Discovery
            max_seed_keywords=100,
            keyword_universe_limit=5000,
            keyword_gaps_limit=2000,
            expansion_limit_per_seed=100,
            # Analysis
            intent_classification_limit=2000,
            difficulty_scoring_limit=2000,
            serp_analysis_limit=200,
            # Context
            questions_limit=50,
            historical_volume_limit=100,
            traffic_estimation_limit=500,
            # Cost
            estimated_cost_usd=25.00,
        )

    # =========================================================================
    # FACTORY
    # =========================================================================

    @classmethod
    def from_preset(cls, preset: str) -> "CollectionDepth":
        """
        Create a CollectionDepth from a preset name.

        Args:
            preset: One of "testing", "basic", "balanced", "comprehensive", "enterprise"

        Returns:
            CollectionDepth with preset values

        Raises:
            ValueError: If preset name is invalid
        """
        presets = {
            "testing": cls.testing,
            "basic": cls.basic,
            "balanced": cls.balanced,
            "comprehensive": cls.comprehensive,
            "enterprise": cls.enterprise,
        }

        preset_lower = preset.lower().strip()

        if preset_lower not in presets:
            valid = ", ".join(presets.keys())
            raise ValueError(f"Invalid preset '{preset}'. Valid presets: {valid}")

        return presets[preset_lower]()

    @classmethod
    def from_preset_with_overrides(
        cls,
        preset: str,
        **overrides
    ) -> "CollectionDepth":
        """
        Create a CollectionDepth from a preset with custom overrides.

        Args:
            preset: Base preset name
            **overrides: Any CollectionDepth field to override

        Returns:
            CollectionDepth with preset values + overrides

        Example:
            depth = CollectionDepth.from_preset_with_overrides(
                "balanced",
                max_seed_keywords=40,
                serp_analysis_limit=100
            )
        """
        depth = cls.from_preset(preset)

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(depth, key):
                setattr(depth, key, value)
                logger.info(f"[DEPTH] Override: {key}={value}")
            else:
                logger.warning(f"[DEPTH] Unknown override ignored: {key}")

        # Mark as customized
        if overrides:
            depth.name = f"{depth.name}+custom"

        return depth

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "name": self.name,
            "discovery": {
                "max_seed_keywords": self.max_seed_keywords,
                "keyword_universe_limit": self.keyword_universe_limit,
                "keyword_gaps_limit": self.keyword_gaps_limit,
                "expansion_limit_per_seed": self.expansion_limit_per_seed,
            },
            "analysis": {
                "intent_classification_limit": self.intent_classification_limit,
                "difficulty_scoring_limit": self.difficulty_scoring_limit,
                "serp_analysis_limit": self.serp_analysis_limit,
            },
            "context": {
                "questions_limit": self.questions_limit,
                "historical_volume_limit": self.historical_volume_limit,
                "traffic_estimation_limit": self.traffic_estimation_limit,
            },
            "estimated_cost_usd": self.estimated_cost_usd,
        }

    def summary(self) -> str:
        """Human-readable summary for logs."""
        return (
            f"CollectionDepth('{self.name}'): "
            f"{self.max_seed_keywords} seeds, "
            f"{self.keyword_universe_limit} universe, "
            f"{self.keyword_gaps_limit} gaps, "
            f"~${self.estimated_cost_usd:.2f}"
        )


# =============================================================================
# CONVENIENCE
# =============================================================================

def get_depth(preset: str = "balanced", **overrides) -> CollectionDepth:
    """
    Convenience function to get a CollectionDepth.

    Args:
        preset: Preset name (testing, basic, balanced, comprehensive, enterprise)
        **overrides: Optional field overrides

    Returns:
        CollectionDepth instance

    Example:
        depth = get_depth("balanced", max_seed_keywords=30)
    """
    if overrides:
        return CollectionDepth.from_preset_with_overrides(preset, **overrides)
    return CollectionDepth.from_preset(preset)

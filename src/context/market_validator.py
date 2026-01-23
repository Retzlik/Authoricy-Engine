"""
Market Validator Agent

Validates user's market selection and discovers opportunities:
- Validates primary market is appropriate
- Discovers secondary market opportunities
- Analyzes language alignment
- Compares opportunity scores across markets

Provides:
- Market validation (confirm/correct user's choice)
- Discovered opportunities (markets user didn't consider)
- Language insights (site vs. search language alignment)
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .models import (
    DiscoveryMethod,
    MarketOpportunity,
    MarketValidation,
    WebsiteAnalysis,
)

if TYPE_CHECKING:
    from src.analyzer.client import ClaudeClient
    from src.collector.client import DataForSEOClient

logger = logging.getLogger(__name__)


# =============================================================================
# MARKET DATA
# =============================================================================


# Market configurations with DataForSEO location codes
MARKET_CONFIG = {
    "us": {
        "name": "United States",
        "location_code": 2840,
        "language": "en",
        "language_name": "English",
        "search_multiplier": 1.0,  # Baseline
    },
    "uk": {
        "name": "United Kingdom",
        "location_code": 2826,
        "language": "en",
        "language_name": "English",
        "search_multiplier": 0.25,
    },
    "se": {
        "name": "Sweden",
        "location_code": 2752,
        "language": "sv",
        "language_name": "Swedish",
        "search_multiplier": 0.02,
    },
    "de": {
        "name": "Germany",
        "location_code": 2276,
        "language": "de",
        "language_name": "German",
        "search_multiplier": 0.35,
    },
    "fr": {
        "name": "France",
        "location_code": 2250,
        "language": "fr",
        "language_name": "French",
        "search_multiplier": 0.25,
    },
    "no": {
        "name": "Norway",
        "location_code": 2578,
        "language": "no",
        "language_name": "Norwegian",
        "search_multiplier": 0.015,
    },
    "dk": {
        "name": "Denmark",
        "location_code": 2208,
        "language": "da",
        "language_name": "Danish",
        "search_multiplier": 0.015,
    },
    "fi": {
        "name": "Finland",
        "location_code": 2246,
        "language": "fi",
        "language_name": "Finnish",
        "search_multiplier": 0.015,
    },
    "nl": {
        "name": "Netherlands",
        "location_code": 2528,
        "language": "nl",
        "language_name": "Dutch",
        "search_multiplier": 0.06,
    },
    "global": {
        "name": "Global (English)",
        "location_code": 2840,  # Use US as proxy
        "language": "en",
        "language_name": "English",
        "search_multiplier": 1.5,
    },
}

# Related markets for expansion suggestions
MARKET_RELATIONS = {
    "se": ["no", "dk", "fi", "de"],  # Nordic + German-speaking
    "no": ["se", "dk", "fi"],  # Nordic
    "dk": ["se", "no", "de"],  # Nordic + German
    "fi": ["se", "no"],  # Nordic
    "de": ["at", "ch", "nl"],  # German-speaking
    "uk": ["us", "ie", "au"],  # English-speaking
    "us": ["uk", "ca", "au"],  # English-speaking
    "fr": ["be", "ch", "ca"],  # French-speaking
    "nl": ["be", "de"],  # Dutch + German
}


# =============================================================================
# MARKET VALIDATOR
# =============================================================================


class MarketValidator:
    """
    Validates and discovers market opportunities.

    Uses DataForSEO to compare search volumes and competition
    across different markets to identify opportunities.
    """

    def __init__(
        self,
        claude_client: Optional["ClaudeClient"] = None,
        dataforseo_client: Optional["DataForSEOClient"] = None,
    ):
        self.claude_client = claude_client
        self.dataforseo_client = dataforseo_client

    async def validate_and_discover(
        self,
        domain: str,
        declared_market: str,
        declared_language: Optional[str] = None,
        secondary_markets: Optional[List[str]] = None,
        website_analysis: Optional[WebsiteAnalysis] = None,
        sample_keywords: Optional[List[str]] = None,
    ) -> MarketValidation:
        """
        Validate market selection and discover opportunities.

        Args:
            domain: Target domain
            declared_market: User's declared primary market
            declared_language: User's declared language
            secondary_markets: User's declared secondary markets
            website_analysis: Results from website analyzer
            sample_keywords: Sample keywords for volume comparison

        Returns:
            MarketValidation with validated markets and discoveries
        """
        logger.info(f"Validating market for {domain}: {declared_market}")

        # Normalize market code
        declared_market = declared_market.lower()
        if declared_market not in MARKET_CONFIG:
            declared_market = "us"  # Default fallback

        # Get language from market if not specified
        if not declared_language:
            declared_language = MARKET_CONFIG[declared_market]["language"]

        # Initialize result
        result = MarketValidation(
            declared_primary=declared_market,
            declared_language=declared_language,
            declared_secondary=secondary_markets or [],
        )

        # Get site languages from website analysis
        if website_analysis:
            result.site_languages = website_analysis.detected_languages

            # Check for language mismatch
            site_primary_lang = website_analysis.primary_language
            if site_primary_lang and site_primary_lang != declared_language:
                result.language_mismatch = True
                result.language_recommendation = (
                    f"Your site's primary language appears to be '{site_primary_lang}', "
                    f"but you selected '{declared_language}'. Consider aligning these."
                )

        # Validate primary market
        primary_opportunity = await self._assess_market_opportunity(
            market=declared_market,
            domain=domain,
            sample_keywords=sample_keywords,
        )
        primary_opportunity.is_primary = True
        result.validated_markets.append(primary_opportunity)

        # Always validate primary market as confirmed (user explicitly chose it)
        result.primary_validated = True
        result.primary_validation_notes = (
            f"Confirmed {MARKET_CONFIG[declared_market]['name']} as primary market. "
            f"Opportunity score: {primary_opportunity.opportunity_score:.0f}/100"
        )

        # Discover additional market opportunities
        related_markets = MARKET_RELATIONS.get(declared_market, [])

        # Also check markets based on site languages
        if website_analysis:
            for lang in website_analysis.detected_languages:
                for market, config in MARKET_CONFIG.items():
                    if config["language"] == lang and market not in related_markets:
                        if market != declared_market:
                            related_markets.append(market)

        # Assess related markets
        for market in related_markets[:5]:  # Limit to 5 markets
            if market not in MARKET_CONFIG:
                continue

            opportunity = await self._assess_market_opportunity(
                market=market,
                domain=domain,
                sample_keywords=sample_keywords,
            )

            # Mark as recommended if better than primary
            if opportunity.opportunity_score > primary_opportunity.opportunity_score * 0.8:
                opportunity.is_recommended = True
                opportunity.recommendation_reason = self._generate_recommendation(
                    opportunity, primary_opportunity, declared_market
                )

            result.discovered_opportunities.append(opportunity)

        # Sort discovered opportunities by score
        result.discovered_opportunities.sort(
            key=lambda x: x.opportunity_score, reverse=True
        )

        # Check if we should suggest adjusting primary
        if result.discovered_opportunities:
            best_discovered = result.discovered_opportunities[0]
            if best_discovered.opportunity_score > primary_opportunity.opportunity_score * 1.3:
                result.should_adjust_primary = True
                result.suggested_primary = best_discovered.region
                result.primary_validation_notes += (
                    f" However, {MARKET_CONFIG[best_discovered.region]['name']} "
                    f"shows 30%+ higher opportunity (score: {best_discovered.opportunity_score:.0f}/100)."
                )

        # Generate suggested secondary markets
        result.suggested_secondary = [
            m.region for m in result.discovered_opportunities[:3]
            if m.is_recommended and m.region != declared_market
        ]

        logger.info(
            f"Market validation complete: {len(result.discovered_opportunities)} "
            f"opportunities discovered, adjust_primary={result.should_adjust_primary}"
        )

        return result

    async def _assess_market_opportunity(
        self,
        market: str,
        domain: str,
        sample_keywords: Optional[List[str]] = None,
    ) -> MarketOpportunity:
        """Assess opportunity in a specific market."""
        config = MARKET_CONFIG.get(market, MARKET_CONFIG["us"])

        opportunity = MarketOpportunity(
            region=market,
            language=config["language"],
            discovery_method=DiscoveryMethod.SERP_ANALYSIS,
        )

        # If we have DataForSEO client and sample keywords, get real data
        if self.dataforseo_client and sample_keywords:
            try:
                volume_data = await self._get_market_volumes(
                    market=market,
                    keywords=sample_keywords[:10],  # Limit keywords
                )

                if volume_data:
                    opportunity.search_volume_potential = volume_data.get("total_volume", 0)
                    opportunity.keyword_count_estimate = volume_data.get("keyword_count", 0)

                    # Calculate opportunity score based on volume and competition
                    avg_competition = volume_data.get("avg_competition", 0.5)
                    opportunity.competition_level = self._competition_to_level(avg_competition)
                    opportunity.opportunity_score = self._calculate_opportunity_score(
                        volume=opportunity.search_volume_potential,
                        competition=avg_competition,
                        market_size=config["search_multiplier"],
                    )

                    return opportunity

            except Exception as e:
                logger.warning(f"Failed to get market data for {market}: {e}")

        # Fallback: Estimate based on market size multiplier
        base_volume = 10000  # Assume 10K base volume
        estimated_volume = int(base_volume * config["search_multiplier"])

        opportunity.search_volume_potential = estimated_volume
        opportunity.keyword_count_estimate = int(estimated_volume / 100)
        opportunity.competition_level = "medium"  # Assume medium competition
        opportunity.opportunity_score = self._calculate_opportunity_score(
            volume=estimated_volume,
            competition=0.5,
            market_size=config["search_multiplier"],
        )

        return opportunity

    async def _get_market_volumes(
        self,
        market: str,
        keywords: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Get search volume data for keywords in a market."""
        if not self.dataforseo_client:
            return None

        config = MARKET_CONFIG.get(market, MARKET_CONFIG["us"])

        try:
            # Use DataForSEO keywords data API (Labs API uses language_name)
            results = await self.dataforseo_client.get_keywords_data(
                keywords=keywords,
                location_code=config["location_code"],
                language_name=config["language_name"],
            )

            if results:
                total_volume = sum(
                    r.get("search_volume", 0) for r in results
                )
                avg_competition = sum(
                    r.get("competition", 0.5) for r in results
                ) / len(results) if results else 0.5

                return {
                    "total_volume": total_volume,
                    "keyword_count": len(results),
                    "avg_competition": avg_competition,
                }

        except Exception as e:
            logger.warning(f"DataForSEO market volume query failed: {e}")

        return None

    def _competition_to_level(self, competition: float) -> str:
        """Convert competition score to level string."""
        if competition < 0.25:
            return "low"
        elif competition < 0.5:
            return "medium"
        elif competition < 0.75:
            return "high"
        else:
            return "very_high"

    def _calculate_opportunity_score(
        self,
        volume: int,
        competition: float,
        market_size: float,
    ) -> float:
        """
        Calculate opportunity score (0-100).

        Higher volume, lower competition, larger market = higher score.
        """
        # Volume score (log scale, 0-40 points)
        import math
        volume_score = min(40, math.log10(max(volume, 1)) * 10)

        # Competition score (inverted, 0-30 points)
        competition_score = (1 - competition) * 30

        # Market size score (0-30 points)
        market_score = min(30, market_size * 20)

        return min(100, volume_score + competition_score + market_score)

    def _generate_recommendation(
        self,
        opportunity: MarketOpportunity,
        primary: MarketOpportunity,
        declared_market: str,
    ) -> str:
        """Generate recommendation text for a market opportunity."""
        config = MARKET_CONFIG.get(opportunity.region, {})
        market_name = config.get("name", opportunity.region)

        parts = [f"Consider {market_name} as a secondary market."]

        # Compare to primary
        if opportunity.search_volume_potential > primary.search_volume_potential:
            ratio = opportunity.search_volume_potential / max(primary.search_volume_potential, 1)
            parts.append(f"Search volume is {ratio:.1f}x higher than primary market.")

        if opportunity.competition_level in ["low", "medium"]:
            parts.append(f"Competition is {opportunity.competition_level}.")

        # Check language alignment
        if opportunity.language == primary.language:
            parts.append("Same language as primary market - easier expansion.")

        return " ".join(parts)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


async def validate_market(
    domain: str,
    declared_market: str,
    declared_language: Optional[str] = None,
    secondary_markets: Optional[List[str]] = None,
    website_analysis: Optional[WebsiteAnalysis] = None,
    sample_keywords: Optional[List[str]] = None,
    claude_client: Optional["ClaudeClient"] = None,
    dataforseo_client: Optional["DataForSEOClient"] = None,
) -> MarketValidation:
    """
    Convenience function to validate market and discover opportunities.

    Args:
        domain: Target domain
        declared_market: User's declared primary market
        declared_language: User's declared language
        secondary_markets: User's declared secondary markets
        website_analysis: Results from website analyzer
        sample_keywords: Sample keywords for volume comparison
        claude_client: Claude client (optional)
        dataforseo_client: DataForSEO client (optional)

    Returns:
        MarketValidation result
    """
    validator = MarketValidator(
        claude_client=claude_client,
        dataforseo_client=dataforseo_client,
    )

    return await validator.validate_and_discover(
        domain=domain,
        declared_market=declared_market,
        declared_language=declared_language,
        secondary_markets=secondary_markets,
        website_analysis=website_analysis,
        sample_keywords=sample_keywords,
    )

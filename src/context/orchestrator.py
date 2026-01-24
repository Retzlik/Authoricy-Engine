"""
Context Intelligence Orchestrator

Coordinates all context intelligence agents:
1. Website Analyzer - Understand the business
2. Competitor Discovery - Find and classify competitors
3. Market Validator - Validate and discover markets
4. Business Profiler - Synthesize into business context

Produces IntelligentCollectionConfig for focused data collection
and ContextIntelligenceResult for enhanced analysis.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .models import (
    CompetitorType,
    ContextIntelligenceResult,
    IntelligentCollectionConfig,
    PrimaryGoal,
)
from .market_detection import MarketDetector, MarketDetectionResult
from .website_analyzer import WebsiteAnalyzer
from .competitor_discovery import CompetitorDiscovery
from .market_validator import MarketValidator
from .business_profiler import BusinessProfiler

if TYPE_CHECKING:
    from src.analyzer.client import ClaudeClient
    from src.collector.client import DataForSEOClient

logger = logging.getLogger(__name__)


# =============================================================================
# ENHANCED REQUEST MODEL
# =============================================================================


class ContextIntelligenceRequest:
    """
    Enhanced analysis request with user inputs for Context Intelligence.

    This replaces the simple domain/market/language input with
    validated and enriched context.
    """

    def __init__(
        self,
        domain: str,
        primary_market: str,
        primary_goal: PrimaryGoal,
        primary_language: Optional[str] = None,
        secondary_markets: Optional[List[str]] = None,
        known_competitors: Optional[List[str]] = None,
        industry: Optional[str] = None,
    ):
        self.domain = domain
        self.primary_market = primary_market
        self.primary_goal = primary_goal
        self.primary_language = primary_language
        self.secondary_markets = secondary_markets or []
        self.known_competitors = known_competitors or []
        self.industry = industry

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "primary_market": self.primary_market,
            "primary_goal": self.primary_goal.value,
            "primary_language": self.primary_language,
            "secondary_markets": self.secondary_markets,
            "known_competitors": self.known_competitors,
            "industry": self.industry,
        }


# =============================================================================
# CONTEXT INTELLIGENCE ORCHESTRATOR
# =============================================================================


class ContextIntelligenceOrchestrator:
    """
    Orchestrates the Context Intelligence phase.

    Runs before data collection to:
    1. Understand the business
    2. Validate and discover competitors
    3. Validate and discover markets
    4. Create focused collection configuration

    This transforms generic SEO analysis into business-aligned intelligence.
    """

    def __init__(
        self,
        claude_client: Optional["ClaudeClient"] = None,
        dataforseo_client: Optional["DataForSEOClient"] = None,
    ):
        self.claude_client = claude_client
        self.dataforseo_client = dataforseo_client

        # Initialize agents
        self.market_detector = MarketDetector(timeout=10.0)
        self.website_analyzer = WebsiteAnalyzer(claude_client)
        self.competitor_discovery = CompetitorDiscovery(claude_client, dataforseo_client)
        self.market_validator = MarketValidator(claude_client, dataforseo_client)
        self.business_profiler = BusinessProfiler(claude_client)

    async def gather_context(
        self,
        request: ContextIntelligenceRequest,
        dataforseo_competitors: Optional[List[Dict[str, Any]]] = None,
        sample_keywords: Optional[List[str]] = None,
    ) -> ContextIntelligenceResult:
        """
        Gather comprehensive context before data collection.

        This is the main entry point for Context Intelligence.

        Args:
            request: Enhanced analysis request with user inputs
            dataforseo_competitors: Optional pre-fetched competitor data
            sample_keywords: Optional sample keywords for market analysis

        Returns:
            ContextIntelligenceResult with all gathered intelligence
        """
        start_time = time.time()

        logger.info(f"Starting Context Intelligence for: {request.domain}")
        logger.info(f"User inputs: market={request.primary_market}, goal={request.primary_goal.value}")

        result = ContextIntelligenceResult(domain=request.domain)

        # Resolve effective market (user input takes priority, then detection)
        effective_market = request.primary_market

        try:
            # Phase 0: Market Detection (NEW - detect market from website signals)
            logger.info("Phase 0: Detecting market from website signals...")
            result.market_detection = await self.market_detector.detect(request.domain)

            if result.market_detection:
                md = result.market_detection
                logger.info(
                    f"Market detection complete: {md.primary.code} ({md.primary.name}) "
                    f"confidence={md.primary.confidence:.0%}, "
                    f"needs_confirmation={md.needs_confirmation}, "
                    f"is_multi_market={md.is_multi_market_site}"
                )

                # Use detected market if:
                # 1. User didn't provide explicit market (still has default)
                # 2. Detection has high confidence
                if not request.primary_market or request.primary_market.lower() in ["", "auto", "detect"]:
                    if md.primary.confidence >= 0.6:
                        effective_market = md.primary.code
                        logger.info(f"Using detected market: {effective_market}")
                    else:
                        # Low confidence, default to US
                        effective_market = "us"
                        logger.info(f"Low confidence detection, defaulting to: {effective_market}")
                else:
                    # User explicitly provided market - validate against detection
                    if md.primary.code != request.primary_market.lower():
                        if md.primary.confidence > 0.8:
                            logger.warning(
                                f"User-provided market '{request.primary_market}' conflicts with "
                                f"detected market '{md.primary.code}' (confidence: {md.primary.confidence:.0%})"
                            )
                            result.warnings.append(
                                f"Detected market ({md.primary.name}) differs from selected market. "
                                f"Detection confidence: {md.primary.confidence:.0%}"
                            )
                    # Always respect user's explicit choice
                    effective_market = request.primary_market

            # Phase 1: Website Analysis (runs first, other phases depend on it)
            logger.info("Phase 1: Analyzing website...")
            result.website_analysis = await self.website_analyzer.analyze(request.domain)

            if result.website_analysis:
                logger.info(
                    f"Website analysis complete: model={result.website_analysis.business_model.value}, "
                    f"confidence={result.website_analysis.analysis_confidence:.2f}"
                )

            # Phase 2 & 3: Run competitor discovery and market validation in parallel
            logger.info("Phase 2 & 3: Discovering competitors and validating market (parallel)...")

            competitor_task = self.competitor_discovery.discover_and_validate(
                domain=request.domain,
                website_analysis=result.website_analysis,
                user_provided_competitors=request.known_competitors,
                dataforseo_competitors=dataforseo_competitors,
                market=effective_market,  # Use resolved market
            )

            market_task = self.market_validator.validate_and_discover(
                domain=request.domain,
                declared_market=effective_market,  # Use resolved market
                declared_language=request.primary_language,
                secondary_markets=request.secondary_markets,
                website_analysis=result.website_analysis,
                sample_keywords=sample_keywords,
            )

            # Run in parallel
            result.competitor_validation, result.market_validation = await asyncio.gather(
                competitor_task,
                market_task,
            )

            if result.competitor_validation:
                logger.info(
                    f"Competitor discovery complete: {result.competitor_validation.total_direct_competitors} direct, "
                    f"{len(result.competitor_validation.discovered)} discovered"
                )

            if result.market_validation:
                logger.info(
                    f"Market validation complete: primary_validated={result.market_validation.primary_validated}, "
                    f"opportunities={len(result.market_validation.discovered_opportunities)}"
                )

            # Phase 4: Business profiling (synthesizes all previous phases)
            logger.info("Phase 4: Profiling business context...")
            result.business_context = await self.business_profiler.profile(
                domain=request.domain,
                stated_goal=request.primary_goal,
                website_analysis=result.website_analysis,
                competitor_validation=result.competitor_validation,
                market_validation=result.market_validation,
            )

            if result.business_context:
                goal_fits = result.business_context.goal_validation.goal_fits_business if result.business_context.goal_validation else True
                logger.info(
                    f"Business profiling complete: goal_fits={goal_fits}, "
                    f"confidence={result.business_context.context_confidence:.2f}"
                )

            # Generate collection config
            result.collection_config = self._generate_collection_config(
                request=request,
                result=result,
                effective_market=effective_market,
            )

            logger.info(
                f"Collection config generated: market='{result.collection_config.primary_market}', "
                f"language='{result.collection_config.primary_language}'"
            )

            # Calculate overall confidence
            confidences = []
            if result.market_detection and result.market_detection.primary:
                confidences.append(result.market_detection.primary.confidence)
            if result.website_analysis:
                confidences.append(result.website_analysis.analysis_confidence)
            if result.business_context:
                confidences.append(result.business_context.context_confidence)

            result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        except Exception as e:
            logger.error(f"Context Intelligence failed: {e}")
            result.errors.append(str(e))

            # Create minimal fallback config
            result.collection_config = IntelligentCollectionConfig(
                domain=request.domain,
                primary_market=request.primary_market,
                primary_language=request.primary_language or "en",
                primary_goal=request.primary_goal,
                direct_competitors=request.known_competitors,
            )

        result.execution_time_seconds = time.time() - start_time

        logger.info(
            f"Context Intelligence complete in {result.execution_time_seconds:.1f}s. "
            f"Confidence: {result.overall_confidence:.2f}"
        )

        return result

    def _generate_collection_config(
        self,
        request: ContextIntelligenceRequest,
        result: ContextIntelligenceResult,
        effective_market: str = "",
    ) -> IntelligentCollectionConfig:
        """Generate the intelligent collection configuration."""
        # Use effective market (resolved from detection + user input)
        primary_market = effective_market or request.primary_market or "us"

        # Get language from market detection if available, otherwise derive from market
        if result.market_detection and result.market_detection.primary:
            default_language = result.market_detection.primary.language_code or "en"
        else:
            market_languages = {
                "se": "sv", "us": "en", "uk": "en", "de": "de",
                "no": "no", "dk": "da", "fi": "fi", "fr": "fr", "nl": "nl",
                "au": "en", "ca": "en", "ie": "en", "nz": "en",
            }
            default_language = market_languages.get(primary_market.lower(), "en")

        config = IntelligentCollectionConfig(
            domain=request.domain,
            primary_market=primary_market,
            primary_language=request.primary_language or default_language,
            primary_goal=request.primary_goal,
            business_context=result.business_context,
        )

        # Set languages based on market validation
        if result.market_validation:
            # Include site languages
            config.collect_languages = list(set(
                [config.primary_language] +
                result.market_validation.site_languages
            ))

            # Set secondary markets
            config.secondary_markets = [
                m.region for m in result.market_validation.discovered_opportunities
                if m.is_recommended
            ][:3]  # Limit to top 3

            # Determine if we should collect for secondary markets
            config.collect_secondary_markets = len(config.secondary_markets) > 0

        # Set competitors based on competitor validation
        if result.competitor_validation:
            # Direct competitors for deep analysis
            config.direct_competitors = [
                c.domain for c in result.competitor_validation.confirmed
                if c.competitor_type == CompetitorType.DIRECT
            ]

            # Add discovered direct competitors
            config.direct_competitors.extend([
                c.domain for c in result.competitor_validation.discovered
                if c.competitor_type == CompetitorType.DIRECT
            ])

            # SEO competitors (for content gap analysis)
            config.seo_competitors = [
                c.domain for c in (
                    result.competitor_validation.confirmed +
                    result.competitor_validation.discovered
                )
                if c.competitor_type == CompetitorType.SEO
            ]

            # Aspirational competitors (for learning)
            config.aspirational_competitors = [
                c.domain for c in result.competitor_validation.discovered
                if c.competitor_type == CompetitorType.ASPIRATIONAL
            ]

            # Domains to ignore
            config.ignore_domains = [
                r["domain"] for r in result.competitor_validation.rejected
            ]

        # Set collection focus based on goal
        if request.primary_goal == PrimaryGoal.LEADS:
            config.priority_intents = ["commercial", "transactional"]
            config.content_type_focus = ["comparison", "evaluation", "pricing"]
            config.skip_news_keywords = True
        elif request.primary_goal == PrimaryGoal.TRAFFIC:
            config.priority_intents = ["informational", "commercial"]
            config.content_type_focus = ["educational", "guide", "how-to"]
        elif request.primary_goal == PrimaryGoal.AUTHORITY:
            config.priority_intents = ["informational"]
            config.content_type_focus = ["research", "data", "linkable-assets"]
            config.enhance_competitor_analysis = True
        else:  # BALANCED
            config.priority_intents = ["commercial", "transactional", "informational"]
            config.content_type_focus = []  # No specific focus

        # Determine if local SEO is relevant
        if result.website_analysis:
            is_local = result.website_analysis.business_model.value == "local_service"
            config.skip_local_seo = not is_local

        return config


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


async def gather_context_intelligence(
    domain: str,
    primary_market: str,
    primary_goal: PrimaryGoal,
    primary_language: Optional[str] = None,
    secondary_markets: Optional[List[str]] = None,
    known_competitors: Optional[List[str]] = None,
    industry: Optional[str] = None,
    claude_client: Optional["ClaudeClient"] = None,
    dataforseo_client: Optional["DataForSEOClient"] = None,
    dataforseo_competitors: Optional[List[Dict[str, Any]]] = None,
    sample_keywords: Optional[List[str]] = None,
) -> ContextIntelligenceResult:
    """
    Convenience function to gather context intelligence.

    This is the main entry point for the Context Intelligence phase.

    Args:
        domain: Target domain
        primary_market: User's declared primary market
        primary_goal: User's declared primary goal
        primary_language: User's declared language (optional)
        secondary_markets: User's declared secondary markets (optional)
        known_competitors: User-provided competitors (optional)
        industry: User's industry (optional)
        claude_client: Claude client for AI analysis
        dataforseo_client: DataForSEO client for data
        dataforseo_competitors: Pre-fetched competitor data
        sample_keywords: Sample keywords for market analysis

    Returns:
        ContextIntelligenceResult with full context
    """
    request = ContextIntelligenceRequest(
        domain=domain,
        primary_market=primary_market,
        primary_goal=primary_goal,
        primary_language=primary_language,
        secondary_markets=secondary_markets,
        known_competitors=known_competitors,
        industry=industry,
    )

    orchestrator = ContextIntelligenceOrchestrator(
        claude_client=claude_client,
        dataforseo_client=dataforseo_client,
    )

    return await orchestrator.gather_context(
        request=request,
        dataforseo_competitors=dataforseo_competitors,
        sample_keywords=sample_keywords,
    )

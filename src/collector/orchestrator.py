"""
Data Collection Orchestrator

Coordinates the multi-phase data collection process.

Supports two modes:
1. Standard Mode: Traditional 4-phase analysis for established domains
2. Greenfield Mode: Competitor-first analysis for domains with minimal SEO data

FIXES APPLIED:
- Phase 3 call now uses correct argument order (named arguments)
- Phase 4 call now includes brand_name parameter
- Default language changed from "sv" to "Swedish" (full name)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .depth import CollectionDepth

# Greenfield context is imported at runtime in _collect_greenfield
# to avoid circular imports. Type hint uses string forward reference.

logger = logging.getLogger(__name__)


@dataclass
class CollectionConfig:
    """Configuration for data collection."""
    domain: str
    market: str = "United States"  # Default to US (English, most common)
    language: str = "English"  # Must be full name like "Swedish", "English" (not code like "sv", "en")
    brand_name: Optional[str] = None
    industry: str = "General"
    competitors: Optional[List[str]] = None

    # Collection depth (controls thoroughness vs cost)
    # If provided, overrides individual limits below
    depth: Optional["CollectionDepth"] = None

    # Legacy limits (used if depth is None)
    max_seed_keywords: int = 5
    max_competitors: int = 5
    max_backlinks: int = 500

    # Options
    skip_ai_analysis: bool = False
    skip_technical_audits: bool = False
    skip_phases: Optional[List[int]] = None
    early_termination_threshold: int = 10  # Min keywords to continue

    # Greenfield mode
    # When greenfield_context is provided, the orchestrator will use
    # competitor-first analysis for domains with minimal SEO data.
    # Set force_greenfield=True to always use greenfield mode regardless of metrics.
    # greenfield_context should be a GreenfieldContext instance from greenfield_pipeline
    greenfield_context: Optional[Any] = None  # GreenfieldContext from greenfield_pipeline
    force_greenfield: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate market is a full name, not a code
        if len(self.market) <= 3:
            logger.error(
                f"[CONFIG ERROR] Market '{self.market}' appears to be a code, not a full name! "
                f"DataForSEO requires full names like 'United Kingdom', 'United States'. "
                f"This WILL cause wrong data to be returned!"
            )

        # Validate language is a full name, not a code
        if len(self.language) <= 3:
            logger.error(
                f"[CONFIG ERROR] Language '{self.language}' appears to be a code, not a full name! "
                f"DataForSEO requires full names like 'English', 'Swedish'."
            )

        # If depth is provided, sync max_seed_keywords for backward compatibility
        if self.depth is not None:
            self.max_seed_keywords = self.depth.max_seed_keywords
            logger.info(f"[CONFIG] Using depth preset: {self.depth.name}")

    def get_depth(self) -> "CollectionDepth":
        """
        Get the CollectionDepth config, creating a default if needed.

        Returns:
            CollectionDepth instance (either provided or created from legacy limits)
        """
        if self.depth is not None:
            return self.depth

        # Create from legacy limits for backward compatibility
        from .depth import CollectionDepth
        return CollectionDepth(
            name="legacy",
            max_seed_keywords=self.max_seed_keywords,
            # Use basic preset values for other limits when using legacy config
            keyword_universe_limit=500,
            keyword_gaps_limit=200,
            expansion_limit_per_seed=50,
            intent_classification_limit=200,
            difficulty_scoring_limit=200,
            serp_analysis_limit=20,
            questions_limit=5,
            historical_volume_limit=10,
            traffic_estimation_limit=50,
        )


@dataclass
class CollectionResult:
    """Result of data collection."""
    domain: str
    timestamp: datetime
    market: str
    language: str
    industry: str = "General"

    # Status tracking
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    # Phase 1: Foundation (11 endpoints - removed domain_pages_summary)
    domain_overview: Dict[str, Any] = field(default_factory=dict)
    historical_data: List[Dict] = field(default_factory=list)
    subdomains: List[Dict] = field(default_factory=list)
    top_pages: List[Dict] = field(default_factory=list)
    competitors: List[Dict] = field(default_factory=list)
    backlink_summary: Dict[str, Any] = field(default_factory=dict)
    technical_baseline: Dict[str, Any] = field(default_factory=dict)
    technologies: List[Dict] = field(default_factory=list)
    whois_data: Dict[str, Any] = field(default_factory=dict)
    page_intersection: List[Dict] = field(default_factory=list)
    categories: List[Dict] = field(default_factory=list)

    # Phase 2: Keywords (18 endpoints)
    ranked_keywords: List[Dict] = field(default_factory=list)
    keyword_gaps: List[Dict] = field(default_factory=list)
    keyword_clusters: List[Dict] = field(default_factory=list)
    keyword_universe: List[Dict] = field(default_factory=list)
    intent_classification: Dict[str, Any] = field(default_factory=dict)
    difficulty_scores: Dict[str, float] = field(default_factory=dict)
    historical_volume: List[Dict] = field(default_factory=list)
    serp_elements: List[Dict] = field(default_factory=list)
    questions_data: List[Dict] = field(default_factory=list)
    top_searches: List[Dict] = field(default_factory=list)
    traffic_estimation: Dict[str, Any] = field(default_factory=dict)
    # Phase 2 summary metrics
    total_ranking_keywords: int = 0
    total_search_volume: int = 0
    position_distribution: Dict[str, int] = field(default_factory=dict)
    intent_distribution: Dict[str, int] = field(default_factory=dict)
    cluster_metrics: Dict[str, Any] = field(default_factory=dict)
    gap_metrics: Dict[str, Any] = field(default_factory=dict)

    # Phase 3: Competitive (15 endpoints)
    competitor_analysis: List[Dict] = field(default_factory=list)
    competitor_metrics: Dict[str, Any] = field(default_factory=dict)
    competitor_trajectories: Dict[str, List] = field(default_factory=dict)
    keyword_intersections: Dict[str, List] = field(default_factory=dict)
    keyword_overlaps: List[Dict] = field(default_factory=list)
    link_gaps: List[Dict] = field(default_factory=list)
    link_gap_targets: List[Dict] = field(default_factory=list)
    top_backlinks: List[Dict] = field(default_factory=list)
    backlinks: List[Dict] = field(default_factory=list)
    anchor_distribution: List[Dict] = field(default_factory=list)
    referring_domains: List[Dict] = field(default_factory=list)
    link_velocity: List[Dict] = field(default_factory=list)
    referring_networks: Dict[str, Any] = field(default_factory=dict)
    broken_backlinks: List[Dict] = field(default_factory=list)
    backlink_history: List[Dict] = field(default_factory=list)
    bulk_ref_domains: Dict[str, Any] = field(default_factory=dict)
    backlink_competitors: List[Dict] = field(default_factory=list)
    # Phase 3 summary metrics
    total_backlinks: int = 0
    total_referring_domains: int = 0
    dofollow_percentage: float = 0.0
    avg_competitor_traffic: int = 0

    # Phase 4: AI & Technical (15 endpoints)
    ai_visibility: Dict[str, Any] = field(default_factory=dict)
    ai_keyword_data: List[Dict] = field(default_factory=list)
    ai_mentions: Dict[str, Any] = field(default_factory=dict)
    llm_mentions: Dict[str, Any] = field(default_factory=dict)
    llm_responses: Dict[str, Any] = field(default_factory=dict)
    brand_mentions: List[Dict] = field(default_factory=list)
    sentiment_summary: Dict[str, Any] = field(default_factory=dict)
    trend_data: Dict[str, Any] = field(default_factory=dict)
    technical_audit: Dict[str, Any] = field(default_factory=dict)
    technical_audits: Dict[str, Any] = field(default_factory=dict)
    live_serp_data: List[Dict] = field(default_factory=list)
    schema_data: List[Dict] = field(default_factory=list)
    content_ratings: Dict[str, Any] = field(default_factory=dict)
    search_volume_live: List[Dict] = field(default_factory=list)
    duplicate_content: Dict[str, Any] = field(default_factory=dict)
    ai_visibility_score: float = 0.0
    brand_sentiment_score: float = 0.0
    technical_health_score: float = 0.0

    # Greenfield mode fields
    analysis_mode: str = "standard"  # standard, greenfield, hybrid
    greenfield_competitors: List[Dict] = field(default_factory=list)
    greenfield_keyword_universe: List[Dict] = field(default_factory=list)
    winnability_analyses: Dict[str, Any] = field(default_factory=dict)
    market_opportunity: Dict[str, Any] = field(default_factory=dict)
    beachhead_keywords: List[Dict] = field(default_factory=list)
    traffic_projections: Dict[str, Any] = field(default_factory=dict)
    growth_roadmap: List[Dict] = field(default_factory=list)
    data_completeness_score: float = 0.0


class DataCollectionOrchestrator:
    """
    Orchestrates the multi-phase data collection process.

    Phases:
    1. Foundation - Domain basics, competitors, backlinks overview
    2. Keywords - Rankings, gaps, clusters
    3. Competitive - Detailed competitor analysis, link gaps
    4. AI & Technical - AI visibility, deep technical audit
    """

    def __init__(self, client):
        """
        Initialize orchestrator with DataForSEO client.

        Args:
            client: DataForSEOClient instance
        """
        self.client = client

    async def collect_all(self, config: CollectionConfig) -> CollectionResult:
        """
        Execute full data collection across all phases.

        Args:
            config: CollectionConfig with domain and settings

        Returns:
            CollectionResult with all collected data
        """
        start_time = datetime.utcnow()
        skip = config.skip_phases or []
        errors = []
        warnings = []

        # Log market parameters prominently for debugging
        logger.info(
            f"[MARKET] Starting collection: domain={config.domain}, "
            f"market='{config.market}', language='{config.language}'"
        )

        # Add warning if market/language look like codes (should be full names)
        if len(config.market) <= 3 or len(config.language) <= 3:
            warning_msg = (
                f"CRITICAL: Market/language may be codes instead of full names! "
                f"market='{config.market}', language='{config.language}'. "
                f"DataForSEO expects 'United Kingdom' not 'uk', 'English' not 'en'."
            )
            logger.error(warning_msg)
            warnings.append(warning_msg)

        logger.info(f"Starting collection for {config.domain}")

        # Import phase collectors
        from src.collector.phase1 import collect_foundation_data

        # Phase 1: Foundation (always runs)
        logger.info("Phase 1: Collecting foundation data...")
        try:
            foundation = await collect_foundation_data(
                self.client,
                config.domain,
                config.market,
                config.language
            )
        except Exception as e:
            logger.error(f"Phase 1 critical failure: {e}")
            errors.append(f"Phase 1 failed: {str(e)}")
            foundation = {}

        # Check for minimal domain - route to greenfield if context provided
        if self._should_use_greenfield(foundation, config):
            domain_keywords = foundation.get("domain_overview", {}).get("organic_keywords", 0)
            domain_backlinks = foundation.get("backlink_summary", {}).get("total_backlinks", 0)

            if config.greenfield_context:
                # Route to greenfield pipeline
                logger.info(
                    f"Routing to greenfield pipeline. "
                    f"Keywords: {domain_keywords}, Backlinks: {domain_backlinks}."
                )
                return await self._collect_greenfield(
                    config=config,
                    foundation=foundation,
                    start_time=start_time,
                    errors=errors,
                    warnings=warnings,
                )
            else:
                # No greenfield context provided - abbreviated analysis
                logger.warning(
                    f"Domain has minimal data - abbreviated analysis. "
                    f"Keywords: {domain_keywords}, Backlinks: {domain_backlinks}. "
                    f"Provide greenfield_context for competitor-first analysis."
                )
                warnings.append(
                    f"Domain has minimal SEO data (keywords: {domain_keywords}, backlinks: {domain_backlinks}). "
                    f"Analysis was abbreviated. Provide greenfield_context for competitor-first analysis."
                )
                duration = (datetime.utcnow() - start_time).total_seconds()
                return CollectionResult(
                    domain=config.domain,
                    timestamp=start_time,
                    market=config.market,
                    language=config.language,
                    industry=config.industry,
                    success=True,
                    errors=errors,
                    warnings=warnings,
                    duration_seconds=duration,
                    **foundation
                )

        # Extract competitors for later phases
        detected_competitors = config.competitors or self._extract_top_competitors(
            foundation, limit=config.max_competitors
        )

        # Phase 2: Keywords (if not skipped)
        keywords_data = {}
        depth = config.get_depth()
        if 2 not in skip:
            try:
                from src.collector.phase2 import collect_keyword_data
                logger.info(
                    f"Phase 2: Collecting keyword data "
                    f"(depth={depth.name}, seeds={depth.max_seed_keywords}, "
                    f"universe={depth.keyword_universe_limit})..."
                )
                keywords_data = await collect_keyword_data(
                    self.client,
                    config.domain,
                    config.market,
                    config.language,
                    seed_keywords=self._extract_seed_keywords(foundation),
                    depth=depth,
                )
            except ImportError:
                warnings.append("Phase 2 module not available, skipping...")
                logger.warning("Phase 2 module not available, skipping...")
            except Exception as e:
                errors.append(f"Phase 2 failed: {str(e)}")
                logger.error(f"Phase 2 failed: {e}")

        # Phase 3: Competitive (if not skipped)
        competitive_data = {}
        if 3 not in skip:
            try:
                from src.collector.phase3 import collect_competitive_data
                logger.info("Phase 3: Collecting competitive data...")
                # FIXED: Use named arguments to ensure correct parameter mapping
                competitive_data = await collect_competitive_data(
                    client=self.client,
                    domain=config.domain,
                    market=config.market,
                    language=config.language,
                    competitors=detected_competitors,
                    top_keywords=self._extract_priority_keywords(keywords_data)
                )
            except ImportError:
                warnings.append("Phase 3 module not available, skipping...")
                logger.warning("Phase 3 module not available, skipping...")
            except Exception as e:
                errors.append(f"Phase 3 failed: {str(e)}")
                logger.error(f"Phase 3 failed: {e}")

        # Phase 4: AI & Technical (if not skipped)
        ai_tech_data = {}
        if 4 not in skip and not config.skip_ai_analysis:
            try:
                from src.collector.phase4 import collect_ai_technical_data
                logger.info("Phase 4: Collecting AI & technical data...")
                # FIXED: Include brand_name and optional parameters
                ai_tech_data = await collect_ai_technical_data(
                    client=self.client,
                    domain=config.domain,
                    brand_name=config.brand_name or config.domain.split('.')[0],  # Extract brand from domain if not provided
                    market=config.market,
                    language=config.language,
                    top_keywords=self._extract_priority_keywords(keywords_data) if keywords_data else None,
                    top_pages=[p.get("page") for p in foundation.get("top_pages", [])[:5]] if foundation.get("top_pages") else None
                )
            except ImportError:
                warnings.append("Phase 4 module not available, skipping...")
                logger.warning("Phase 4 module not available, skipping...")
            except Exception as e:
                errors.append(f"Phase 4 failed: {str(e)}")
                logger.error(f"Phase 4 failed: {e}")

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Collection complete in {duration:.1f}s")

        # Merge all data
        all_data = {**foundation, **keywords_data, **competitive_data, **ai_tech_data}

        # Determine success - we need at least SOME data to analyze
        # Success if we have domain_overview metrics OR ranked keywords OR backlinks
        has_overview = bool(foundation.get("domain_overview"))
        has_keywords = bool(keywords_data.get("ranked_keywords"))
        has_backlinks = bool(foundation.get("backlink_summary"))
        success = has_overview or has_keywords or has_backlinks

        if not success:
            logger.warning("No usable data collected - all sources empty")

        return CollectionResult(
            domain=config.domain,
            timestamp=start_time,
            market=config.market,
            language=config.language,
            industry=config.industry,
            success=success,
            errors=errors,
            warnings=warnings,
            duration_seconds=duration,
            **all_data
        )

    # Alias for backwards compatibility
    async def collect(self, config: CollectionConfig) -> CollectionResult:
        """Alias for collect_all()."""
        return await self.collect_all(config)

    async def _collect_greenfield(
        self,
        config: CollectionConfig,
        foundation: Dict[str, Any],
        start_time: datetime,
        errors: List[str],
        warnings: List[str],
    ) -> CollectionResult:
        """
        Execute greenfield collection pipeline for domains with minimal SEO data.

        Uses competitor-first analysis to build keyword universe and identify
        beachhead opportunities.
        """
        from .greenfield_pipeline import collect_greenfield_data, GreenfieldContext

        logger.info("Starting greenfield collection pipeline...")

        # Convert dict to GreenfieldContext if needed
        ctx = config.greenfield_context
        if isinstance(ctx, dict):
            try:
                config.greenfield_context = GreenfieldContext(
                    business_name=ctx.get("business_name", ""),
                    business_description=ctx.get("business_description", ""),
                    primary_offering=ctx.get("primary_offering", ""),
                    target_market=ctx.get("target_market", "United States"),
                    industry_vertical=ctx.get("industry_vertical", "saas"),
                    seed_keywords=ctx.get("seed_keywords", []),
                    known_competitors=ctx.get("known_competitors", []),
                    target_audience=ctx.get("target_audience"),
                    unique_value_prop=ctx.get("unique_value_prop"),
                    content_budget=ctx.get("content_budget"),
                )
            except Exception as e:
                logger.error(f"Failed to convert greenfield context: {e}")
                errors.append(f"Invalid greenfield context: {str(e)}")
                duration = (datetime.utcnow() - start_time).total_seconds()
                return CollectionResult(
                    domain=config.domain,
                    timestamp=start_time,
                    market=config.market,
                    language=config.language,
                    industry=config.industry,
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_seconds=duration,
                    analysis_mode="greenfield",
                    **foundation,
                )

        try:
            greenfield_result = await collect_greenfield_data(
                client=self.client,
                config=config,
                foundation=foundation,
                start_time=start_time,
            )

            # Merge greenfield results with foundation data
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Convert greenfield competitors to dict format
            gf_competitors = [
                {
                    "domain": comp.domain,
                    "discovery_source": comp.discovery_source,
                    "discovery_reason": comp.discovery_reason,
                    "domain_rating": comp.domain_rating,
                    "organic_traffic": comp.organic_traffic,
                    "organic_keywords": comp.organic_keywords,
                    "relevance_score": comp.relevance_score,
                    "suggested_purpose": comp.suggested_purpose,
                    "is_validated": comp.is_validated,
                }
                for comp in greenfield_result.competitors
            ]

            # Convert keyword universe to dict format
            gf_keywords = [
                {
                    "keyword": kw.keyword,
                    "search_volume": kw.search_volume,
                    "keyword_difficulty": kw.keyword_difficulty,
                    "cpc": kw.cpc,
                    "source_competitor": kw.source_competitor,
                    "search_intent": kw.search_intent,
                    "winnability_score": kw.winnability_score,
                    "personalized_difficulty": kw.personalized_difficulty,
                    "serp_analyzed": kw.serp_analyzed,
                }
                for kw in greenfield_result.keyword_universe
            ]

            # Convert beachhead keywords to dict format
            # Note: BeachheadKeyword uses beachhead_priority, not priority
            # growth_phase is assigned during roadmap building, not stored in BeachheadKeyword
            gf_beachheads = [
                {
                    "keyword": bh.keyword,
                    "search_volume": bh.search_volume,
                    "winnability_score": bh.winnability_score,
                    "personalized_difficulty": bh.personalized_difficulty,
                    "keyword_difficulty": bh.keyword_difficulty,
                    "beachhead_priority": bh.beachhead_priority,
                    "beachhead_score": bh.beachhead_score,
                    "avg_serp_dr": bh.avg_serp_dr,
                    "has_ai_overview": bh.has_ai_overview,
                    "recommended_content_type": bh.recommended_content_type,
                    "estimated_time_to_rank_weeks": bh.estimated_time_to_rank_weeks,
                    "estimated_traffic_gain": bh.estimated_traffic_gain,
                }
                for bh in greenfield_result.beachhead_keywords
            ]

            # Convert winnability analyses to dict format
            # Note: WinnabilityAnalysis uses avg_serp_dr (not serp_avg_dr), weak_content_signals (not weak_signals)
            gf_winnability = {
                kw: {
                    "winnability_score": analysis.winnability_score,
                    "personalized_difficulty": analysis.personalized_difficulty,
                    "avg_serp_dr": analysis.avg_serp_dr,
                    "min_serp_dr": analysis.min_serp_dr,
                    "has_low_dr_rankings": analysis.has_low_dr_rankings,
                    "weak_content_signals": analysis.weak_content_signals,
                    "has_ai_overview": analysis.has_ai_overview,
                    "is_beachhead_candidate": analysis.is_beachhead_candidate,
                    "beachhead_score": analysis.beachhead_score,
                }
                for kw, analysis in greenfield_result.winnability_analyses.items()
            }

            # Convert market opportunity to dict
            # Note: MarketOpportunity uses tam_keywords (not tam_keyword_count)
            gf_market = {}
            if greenfield_result.market_opportunity:
                mo = greenfield_result.market_opportunity
                gf_market = {
                    "tam_volume": mo.tam_volume,
                    "sam_volume": mo.sam_volume,
                    "som_volume": mo.som_volume,
                    "tam_keyword_count": mo.tam_keywords,
                    "sam_keyword_count": mo.sam_keywords,
                    "som_keyword_count": mo.som_keywords,
                    "competitor_shares": mo.competitor_shares,
                }

            # Convert traffic projections to dict
            # Note: TrafficProjection uses traffic_by_month dict, not individual month_X fields
            gf_projections = {}
            if greenfield_result.traffic_projections:
                tp = greenfield_result.traffic_projections

                def projection_to_dict(proj):
                    return {
                        "scenario": proj.scenario,
                        "confidence": proj.confidence,
                        "month_3": proj.traffic_by_month.get(3, 0),
                        "month_6": proj.traffic_by_month.get(6, 0),
                        "month_12": proj.traffic_by_month.get(12, 0),
                        "month_18": proj.traffic_by_month.get(18, 0),
                        "month_24": proj.traffic_by_month.get(24, 0),
                    }

                gf_projections = {
                    "conservative": projection_to_dict(tp.conservative),
                    "expected": projection_to_dict(tp.expected),
                    "aggressive": projection_to_dict(tp.aggressive),
                }

            # Merge errors and warnings
            all_errors = errors + greenfield_result.errors
            all_warnings = warnings + greenfield_result.warnings

            logger.info(
                f"Greenfield collection complete: {len(gf_competitors)} competitors, "
                f"{len(gf_keywords)} keywords, {len(gf_beachheads)} beachheads"
            )

            return CollectionResult(
                domain=config.domain,
                timestamp=start_time,
                market=config.market,
                language=config.language,
                industry=config.industry,
                success=True,
                errors=all_errors,
                warnings=all_warnings,
                duration_seconds=duration,
                # Foundation data
                **foundation,
                # Greenfield mode indicator
                analysis_mode="greenfield",
                # Greenfield-specific results
                greenfield_competitors=gf_competitors,
                greenfield_keyword_universe=gf_keywords,
                winnability_analyses=gf_winnability,
                market_opportunity=gf_market,
                beachhead_keywords=gf_beachheads,
                traffic_projections=gf_projections,
                growth_roadmap=greenfield_result.growth_roadmap,
                data_completeness_score=greenfield_result.data_completeness_score,
            )

        except Exception as e:
            logger.error(f"Greenfield pipeline failed: {e}")
            errors.append(f"Greenfield pipeline failed: {str(e)}")

            # Return abbreviated result
            duration = (datetime.utcnow() - start_time).total_seconds()
            return CollectionResult(
                domain=config.domain,
                timestamp=start_time,
                market=config.market,
                language=config.language,
                industry=config.industry,
                success=False,
                errors=errors,
                warnings=warnings,
                duration_seconds=duration,
                analysis_mode="greenfield",
                **foundation,
            )

    def _should_use_greenfield(self, foundation: Dict, config: CollectionConfig) -> bool:
        """
        Determine if greenfield mode should be used.

        Greenfield mode is used when:
        1. force_greenfield is True, OR
        2. Domain has minimal SEO data (< 50 keywords AND < 100 backlinks)

        Returns:
            True if greenfield mode should be used
        """
        if config.force_greenfield:
            return True

        keywords = foundation.get("domain_overview", {}).get("organic_keywords", 0)
        backlinks = foundation.get("backlink_summary", {}).get("total_backlinks", 0)

        # Use greenfield thresholds from scoring module
        return keywords < 50 and backlinks < 100

    def _should_abbreviate(self, foundation: Dict) -> bool:
        """Check if domain has enough data for full analysis (deprecated, use _should_use_greenfield)."""
        keywords = foundation.get("domain_overview", {}).get("organic_keywords", 0)
        backlinks = foundation.get("backlink_summary", {}).get("total_backlinks", 0)
        return keywords < 10 and backlinks < 50

    def _extract_top_competitors(self, foundation: Dict, limit: int = 5) -> List[str]:
        """Extract top competitor domains from foundation data."""
        competitors = foundation.get("competitors", [])
        return [c.get("domain") for c in competitors[:limit] if c.get("domain")]

    def _extract_seed_keywords(self, foundation: Dict) -> List[str]:
        """Extract seed keywords from top pages."""
        pages = foundation.get("top_pages", [])
        keywords = []
        for page in pages[:10]:
            if kw := page.get("main_keyword"):
                keywords.append(kw)
        return keywords[:5]

    def _extract_priority_keywords(self, keywords_data: Dict) -> List[str]:
        """Extract priority keywords for competitive analysis."""
        ranked = keywords_data.get("ranked_keywords", [])
        # Get keywords where we rank 4-20 (opportunity zone)
        priority = [
            kw.get("keyword")
            for kw in ranked
            if kw.get("keyword") and 4 <= kw.get("position", 100) <= 20
        ]
        return priority[:20]


def compile_analysis_data(result: CollectionResult) -> Dict[str, Any]:
    """
    Compile collection result into a structured format for AI analysis.

    This function transforms the raw CollectionResult into a format
    optimized for consumption by Claude's analysis loops.

    Args:
        result: CollectionResult from data collection

    Returns:
        Dict containing structured data ready for AI analysis
    """
    import json
    from dataclasses import asdict

    # Convert dataclass to dict
    data = asdict(result)

    # Convert datetime to ISO format
    if data.get("timestamp"):
        data["timestamp"] = data["timestamp"].isoformat()

    # Structure for AI analysis
    compiled = {
        "metadata": {
            "domain": result.domain,
            "market": result.market,
            "language": result.language,
            "industry": result.industry,
            "collection_timestamp": data["timestamp"],
            "duration_seconds": result.duration_seconds,
            "success": result.success,
            "errors": result.errors,
            "warnings": result.warnings,
            "analysis_mode": result.analysis_mode,
        },
        "phase1_foundation": {
            "domain_overview": result.domain_overview,
            "historical_data": result.historical_data,
            "subdomains": result.subdomains,
            "top_pages": result.top_pages,
            "competitors": result.competitors,
            "backlink_summary": result.backlink_summary,
            "technical_baseline": result.technical_baseline,
            "technologies": result.technologies,
        },
        "phase2_keywords": {
            "ranked_keywords": result.ranked_keywords,
            "keyword_universe": result.keyword_universe,
            "keyword_gaps": result.keyword_gaps,
            "keyword_clusters": result.keyword_clusters,
            "intent_classification": result.intent_classification,
            "difficulty_scores": result.difficulty_scores,
        },
        "phase3_competitive": {
            "competitor_analysis": result.competitor_analysis,
            "competitor_metrics": result.competitor_metrics,
            "competitor_trajectories": result.competitor_trajectories,
            "keyword_intersections": result.keyword_intersections,
            "top_backlinks": result.top_backlinks,
            "anchor_distribution": result.anchor_distribution,
            "referring_domains": result.referring_domains,
            "link_gaps": result.link_gaps,
            "link_velocity": result.link_velocity,
        },
        "phase4_ai_technical": {
            "ai_visibility": result.ai_visibility,
            "ai_mentions": result.ai_mentions,
            "llm_responses": result.llm_responses,
            "brand_mentions": result.brand_mentions,
            "trend_data": result.trend_data,
            "technical_audit": result.technical_audit,
            "technical_audits": result.technical_audits,
        },
        "summary": {
            "total_organic_keywords": result.domain_overview.get("organic_keywords", 0),
            "total_organic_traffic": result.domain_overview.get("organic_traffic", 0),
            "domain_rank": result.backlink_summary.get("domain_rank", 0),
            "total_backlinks": result.backlink_summary.get("total_backlinks", 0),
            "referring_domains_count": result.backlink_summary.get("referring_domains", 0),
            "competitor_count": len(result.competitors),
            "ranked_keywords_count": len(result.ranked_keywords),
            "keyword_gaps_count": len(result.keyword_gaps),
        },
    }

    # Add greenfield data if in greenfield mode
    if result.analysis_mode == "greenfield":
        compiled["greenfield"] = {
            "competitors": result.greenfield_competitors,
            "keyword_universe": result.greenfield_keyword_universe,
            "winnability_analyses": result.winnability_analyses,
            "market_opportunity": result.market_opportunity,
            "beachhead_keywords": result.beachhead_keywords,
            "traffic_projections": result.traffic_projections,
            "growth_roadmap": result.growth_roadmap,
            "data_completeness_score": result.data_completeness_score,
        }

        # Update summary for greenfield mode
        compiled["summary"].update({
            "analysis_mode": "greenfield",
            "greenfield_competitor_count": len(result.greenfield_competitors),
            "greenfield_keyword_count": len(result.greenfield_keyword_universe),
            "beachhead_count": len(result.beachhead_keywords),
            "data_completeness_score": result.data_completeness_score,
        })

        # Add market opportunity to summary if available
        if result.market_opportunity:
            compiled["summary"]["market_opportunity"] = {
                "tam_volume": result.market_opportunity.get("tam_volume", 0),
                "sam_volume": result.market_opportunity.get("sam_volume", 0),
                "som_volume": result.market_opportunity.get("som_volume", 0),
                "tam_keyword_count": result.market_opportunity.get("tam_keyword_count", 0),
                "sam_keyword_count": result.market_opportunity.get("sam_keyword_count", 0),
                "som_keyword_count": result.market_opportunity.get("som_keyword_count", 0),
            }

    return compiled


def get_analysis_json(result: CollectionResult, indent: int = 2) -> str:
    """
    Get analysis data as JSON string.

    Args:
        result: CollectionResult from data collection
        indent: JSON indentation level

    Returns:
        JSON string of compiled analysis data
    """
    import json

    compiled = compile_analysis_data(result)
    return json.dumps(compiled, indent=indent, default=str)

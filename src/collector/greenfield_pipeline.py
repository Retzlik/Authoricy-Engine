"""
Greenfield Collection Pipeline

Competitor-first data collection for domains with insufficient SEO data.
Implements the strategy from GREENFIELD_DOMAIN_BRIEF.md and COMPETITOR_INTELLIGENCE_ARCHITECTURE.md

Pipeline Phases:
G1: Competitor Discovery & Validation
G2: Keyword Universe Construction (from competitors)
G3: SERP Analysis & Winnability Scoring
G4: Market Sizing
G5: Beachhead Selection & Roadmap
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from src.scoring.greenfield import (
    DomainMaturity,
    Industry,
    DomainMetrics,
    WinnabilityAnalysis,
    BeachheadKeyword,
    MarketOpportunity,
    TrafficProjections,
    calculate_winnability_full,
    select_beachhead_keywords,
    calculate_market_opportunity,
    project_traffic_scenarios,
    get_industry_from_string,
    classify_domain_maturity,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GreenfieldContext:
    """User-provided context for greenfield analysis."""
    business_name: str
    business_description: str
    primary_offering: str
    target_market: str
    industry_vertical: str
    seed_keywords: List[str]          # Minimum 5
    known_competitors: List[str]      # Minimum 3

    # Optional
    target_audience: Optional[str] = None
    unique_value_prop: Optional[str] = None
    content_budget: Optional[str] = None  # low, medium, high


@dataclass
class GreenfieldCompetitorCandidate:
    """Competitor candidate during discovery phase."""
    domain: str
    discovery_source: str  # perplexity, serp, traffic_share, user_provided
    discovery_reason: str

    # Metrics (populated after validation)
    domain_rating: int = 0
    organic_traffic: int = 0
    organic_keywords: int = 0
    referring_domains: int = 0

    # Scoring
    relevance_score: float = 0.0
    suggested_purpose: str = "keyword_source"

    # Validation
    is_validated: bool = False
    validation_warnings: List[str] = field(default_factory=list)


@dataclass
class ValidatedCompetitorSet:
    """Final validated competitor set after curation."""
    competitors: List[GreenfieldCompetitorCandidate]
    removed_count: int = 0
    added_count: int = 0
    validation_warnings: List[str] = field(default_factory=list)


@dataclass
class GreenfieldKeyword:
    """Keyword with greenfield-specific attributes."""
    keyword: str
    search_volume: int
    keyword_difficulty: int
    cpc: float = 0.0

    # Source tracking
    source_competitor: str = ""
    competitor_position: int = 0

    # Intent
    search_intent: str = "informational"

    # Business relevance
    business_relevance: float = 0.7

    # Winnability (populated after SERP analysis)
    winnability_score: float = 0.0
    personalized_difficulty: float = 0.0
    serp_analyzed: bool = False


@dataclass
class GreenfieldCollectionResult:
    """Complete result from greenfield collection pipeline."""
    # Metadata
    domain: str
    analysis_mode: str = "greenfield"
    collected_at: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: int = 0

    # Domain context
    domain_metrics: Optional[DomainMetrics] = None
    greenfield_context: Optional[GreenfieldContext] = None

    # Phase G1: Competitors
    competitors: List[GreenfieldCompetitorCandidate] = field(default_factory=list)
    competitor_validation: Optional[ValidatedCompetitorSet] = None

    # Phase G2: Keywords
    keyword_universe: List[GreenfieldKeyword] = field(default_factory=list)

    # Phase G3: Winnability
    winnability_analyses: Dict[str, WinnabilityAnalysis] = field(default_factory=dict)

    # Phase G4: Market sizing
    market_opportunity: Optional[MarketOpportunity] = None

    # Phase G5: Beachheads and projections
    beachhead_keywords: List[BeachheadKeyword] = field(default_factory=list)
    traffic_projections: Optional[TrafficProjections] = None
    growth_roadmap: List[Dict[str, Any]] = field(default_factory=list)

    # Quality and errors
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data_completeness_score: float = 0.0


# =============================================================================
# MAIN PIPELINE FUNCTION
# =============================================================================

async def collect_greenfield_data(
    client,  # DataForSEOClient
    config,  # CollectionConfig
    foundation: Dict[str, Any],
    start_time: datetime,
    perplexity_client=None,  # Optional PerplexityClient for AI discovery
    firecrawl_client=None,  # Optional FirecrawlClient for context scraping
) -> GreenfieldCollectionResult:
    """
    Execute greenfield collection pipeline.

    Phases:
    G1: Competitor Discovery & Validation
    G2: Keyword Universe Construction (from competitors)
    G3: SERP Analysis & Winnability Scoring
    G4: Market Sizing
    G5: Beachhead Selection & Roadmap

    Args:
        client: DataForSEO client for API calls
        config: Collection configuration with greenfield_context
        foundation: Phase 1 foundation data (domain overview)
        start_time: Pipeline start time
        perplexity_client: Optional Perplexity client for AI-powered discovery
        firecrawl_client: Optional Firecrawl client for website scraping

    Returns:
        GreenfieldCollectionResult with all collected data
    """
    result = GreenfieldCollectionResult(domain=config.domain)

    # Extract greenfield context
    ctx = config.greenfield_context
    if not ctx:
        result.errors.append("Greenfield context is required")
        return result

    result.greenfield_context = ctx

    # Extract domain metrics from foundation
    overview = foundation.get("domain_overview", {})
    backlinks = foundation.get("backlink_summary", {})

    # Domain Rating (DR) comes from backlinks/summary API, NOT from domain_rank_overview
    # The domain_rank_overview "rank" field was incorrectly named - it was actually pos_1
    # (count of keywords in position 1), not Domain Rating
    result.domain_metrics = DomainMetrics(
        domain_rating=backlinks.get("domain_rank", 0),
        organic_keywords=overview.get("organic_keywords", 0),
        organic_traffic=overview.get("organic_traffic", 0),
        referring_domains=backlinks.get("referring_domains", 0),
    )

    target_dr = result.domain_metrics.domain_rating or 10  # Default to 10 for new domains
    industry = get_industry_from_string(ctx.industry_vertical)

    # Build business context dict for external APIs
    business_context = {
        "business_name": ctx.business_name,
        "business_description": ctx.business_description,
        "primary_offering": ctx.primary_offering,
        "target_market": ctx.target_market,
        "industry_vertical": ctx.industry_vertical,
        "target_audience": ctx.target_audience,
    }

    # =========================================================================
    # Phase G1: Competitor Discovery & Validation
    # =========================================================================
    logger.info("Phase G1: Discovering and validating competitors...")

    try:
        competitors = await _discover_competitors(
            client=client,
            seed_keywords=ctx.seed_keywords,
            known_competitors=ctx.known_competitors,
            market=config.market,
            language=config.language,
            perplexity_client=perplexity_client,
            business_context=business_context,
        )

        # Validate and enrich with metrics
        validated = await _validate_competitors(
            client=client,
            candidates=competitors,
            target_dr=target_dr,
            market=config.market,
        )

        result.competitors = validated.competitors
        result.competitor_validation = validated

        if validated.validation_warnings:
            result.warnings.extend(validated.validation_warnings)

    except Exception as e:
        logger.error(f"Phase G1 failed: {e}")
        result.errors.append(f"Competitor discovery failed: {str(e)}")
        # Use user-provided competitors as fallback
        result.competitors = [
            GreenfieldCompetitorCandidate(
                domain=comp,
                discovery_source="user_provided",
                discovery_reason="User-provided competitor",
            )
            for comp in ctx.known_competitors
        ]

    # =========================================================================
    # Phase G2: Keyword Universe Construction
    # =========================================================================
    logger.info("Phase G2: Building keyword universe from competitors...")

    try:
        keyword_universe = await _build_keyword_universe(
            client=client,
            competitors=result.competitors,
            seed_keywords=ctx.seed_keywords,
            market=config.market,
            language=config.language,
        )

        result.keyword_universe = keyword_universe
        logger.info(f"Built keyword universe with {len(keyword_universe)} keywords")

    except Exception as e:
        logger.error(f"Phase G2 failed: {e}")
        result.errors.append(f"Keyword universe construction failed: {str(e)}")

    # =========================================================================
    # Phase G3: SERP Analysis & Winnability Scoring
    # =========================================================================
    logger.info("Phase G3: Analyzing SERPs and calculating winnability...")

    try:
        # Analyze top 200 keywords by volume
        keywords_to_analyze = sorted(
            result.keyword_universe,
            key=lambda k: k.search_volume,
            reverse=True
        )[:200]

        winnability_analyses = await _analyze_serps_batch(
            client=client,
            keywords=keywords_to_analyze,
            target_dr=target_dr,
            market=config.market,
            language=config.language,
            industry=industry.value,
        )

        result.winnability_analyses = winnability_analyses

        # Update keywords with winnability scores
        for kw in result.keyword_universe:
            if kw.keyword in winnability_analyses:
                analysis = winnability_analyses[kw.keyword]
                kw.winnability_score = analysis.winnability_score
                kw.personalized_difficulty = analysis.personalized_difficulty
                kw.serp_analyzed = True

        logger.info(f"Analyzed winnability for {len(winnability_analyses)} keywords")

    except Exception as e:
        logger.error(f"Phase G3 failed: {e}")
        result.errors.append(f"SERP analysis failed: {str(e)}")

    # =========================================================================
    # Phase G4: Market Sizing
    # =========================================================================
    logger.info("Phase G4: Calculating market opportunity...")

    try:
        # Convert keywords to dict format for scoring functions
        keywords_for_scoring = [
            {
                "keyword": kw.keyword,
                "search_volume": kw.search_volume,
                "keyword_difficulty": kw.keyword_difficulty,
                "business_relevance": kw.business_relevance,
            }
            for kw in result.keyword_universe
        ]

        # Convert competitors to dict format
        competitors_for_scoring = [
            {
                "domain": comp.domain,
                "organic_traffic": comp.organic_traffic,
                "organic_keywords": comp.organic_keywords,
            }
            for comp in result.competitors
        ]

        result.market_opportunity = calculate_market_opportunity(
            keywords=keywords_for_scoring,
            winnability_analyses=result.winnability_analyses,
            competitors=competitors_for_scoring,
        )

        logger.info(
            f"Market opportunity: TAM={result.market_opportunity.tam_volume:,}, "
            f"SAM={result.market_opportunity.sam_volume:,}, "
            f"SOM={result.market_opportunity.som_volume:,}"
        )

    except Exception as e:
        logger.error(f"Phase G4 failed: {e}")
        result.errors.append(f"Market sizing failed: {str(e)}")

    # =========================================================================
    # Phase G5: Beachhead Selection & Roadmap
    # =========================================================================
    logger.info("Phase G5: Selecting beachhead keywords and building roadmap...")

    try:
        # Select beachhead keywords
        keywords_for_beachhead = [
            {
                "keyword": kw.keyword,
                "search_volume": kw.search_volume,
                "keyword_difficulty": kw.keyword_difficulty,
                "business_relevance": kw.business_relevance,
                "intent": kw.search_intent,
            }
            for kw in result.keyword_universe
            if kw.serp_analyzed
        ]

        result.beachhead_keywords = select_beachhead_keywords(
            keywords=keywords_for_beachhead,
            winnability_analyses=result.winnability_analyses,
            target_count=20,
            max_kd=30,
            min_volume=100,
            min_winnability=60.0,
        )

        logger.info(f"Selected {len(result.beachhead_keywords)} beachhead keywords")

        # Generate traffic projections
        growth_keywords = [
            kw_dict for kw_dict in keywords_for_beachhead
            if kw_dict["keyword"] not in [bh.keyword for bh in result.beachhead_keywords]
        ][:50]

        result.traffic_projections = project_traffic_scenarios(
            beachhead_keywords=result.beachhead_keywords,
            growth_keywords=growth_keywords,
            winnability_analyses=result.winnability_analyses,
            domain_maturity=DomainMaturity.GREENFIELD,
        )

        # Build growth roadmap
        result.growth_roadmap = _build_growth_roadmap(
            beachhead_keywords=result.beachhead_keywords,
            keyword_universe=result.keyword_universe,
            market_opportunity=result.market_opportunity,
        )

    except Exception as e:
        logger.error(f"Phase G5 failed: {e}")
        result.errors.append(f"Beachhead selection failed: {str(e)}")

    # Calculate duration and completeness
    result.duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
    result.data_completeness_score = _calculate_completeness(result)

    logger.info(
        f"Greenfield collection completed in {result.duration_seconds}s, "
        f"completeness: {result.data_completeness_score:.0f}%"
    )

    return result


# =============================================================================
# PHASE G1: COMPETITOR DISCOVERY
# =============================================================================

async def _discover_competitors(
    client,
    seed_keywords: List[str],
    known_competitors: List[str],
    market: str,
    language: str,
    perplexity_client=None,
    business_context: Optional[Dict[str, Any]] = None,
) -> List[GreenfieldCompetitorCandidate]:
    """
    Discover competitors through multiple sources.

    Sources:
    1. User-provided competitors
    2. Perplexity AI discovery (if client provided)
    3. SERP analysis for seed keywords
    4. Traffic share competitors
    """
    candidates = []
    seen_domains = set()

    # Source 1: User-provided competitors
    for domain in known_competitors:
        domain = domain.lower().strip()
        if domain and domain not in seen_domains:
            candidates.append(GreenfieldCompetitorCandidate(
                domain=domain,
                discovery_source="user_provided",
                discovery_reason="User-provided competitor",
                relevance_score=0.9,  # High relevance for user-provided
            ))
            seen_domains.add(domain)

    # Source 2: Perplexity AI discovery (intelligent search)
    if perplexity_client and business_context:
        try:
            perplexity_competitors = await _discover_from_perplexity(
                client=perplexity_client,
                business_context=business_context,
            )

            for comp in perplexity_competitors:
                if comp.domain and comp.domain not in seen_domains:
                    candidates.append(comp)
                    seen_domains.add(comp.domain)

            logger.info(f"Perplexity discovered {len(perplexity_competitors)} candidates")

        except Exception as e:
            logger.warning(f"Perplexity discovery failed: {e}")

    # Source 3: SERP analysis for seed keywords
    try:
        serp_competitors = await _discover_from_serps(
            client=client,
            seed_keywords=seed_keywords[:5],  # Top 5 seeds
            market=market,
            language=language,
        )

        for comp in serp_competitors:
            if comp.domain not in seen_domains:
                candidates.append(comp)
                seen_domains.add(comp.domain)

    except Exception as e:
        logger.warning(f"SERP discovery failed: {e}")

    # Source 4: Traffic share (if we have at least one competitor)
    if candidates:
        try:
            traffic_competitors = await _discover_from_traffic_share(
                client=client,
                reference_domains=[c.domain for c in candidates[:3]],
                market=market,
            )

            for comp in traffic_competitors:
                if comp.domain not in seen_domains:
                    candidates.append(comp)
                    seen_domains.add(comp.domain)

        except Exception as e:
            logger.warning(f"Traffic share discovery failed: {e}")

    logger.info(f"Discovered {len(candidates)} competitor candidates")
    return candidates


async def _discover_from_perplexity(
    client,  # PerplexityClient or PerplexityDiscovery
    business_context: Dict[str, Any],
) -> List[GreenfieldCompetitorCandidate]:
    """
    Discover competitors using Perplexity AI search.

    Perplexity provides intelligent, context-aware competitor discovery
    that can find competitors DataForSEO might miss.
    """
    from src.integrations.perplexity import PerplexityDiscovery

    # Create discovery instance if raw client provided
    if hasattr(client, 'discover_competitors'):
        discovery = client
    else:
        discovery = PerplexityDiscovery(client)

    # Extract context fields
    company_name = business_context.get("business_name", "the company")
    category = business_context.get("primary_offering", "software")
    offering = business_context.get("business_description", category)
    customer_type = business_context.get("target_audience", "businesses")

    # Run discovery
    discovered = await discovery.discover_competitors(
        company_name=company_name,
        category=category,
        offering=offering,
        customer_type=customer_type,
    )

    # Convert to GreenfieldCompetitorCandidate
    candidates = []
    for disc in discovered:
        if disc.domain:
            candidates.append(GreenfieldCompetitorCandidate(
                domain=disc.domain,
                discovery_source=disc.discovery_source,
                discovery_reason=disc.discovery_reason or f"AI discovery: {disc.name}",
                relevance_score=disc.confidence,
            ))

    return candidates


async def _discover_from_serps(
    client,
    seed_keywords: List[str],
    market: str,
    language: str,
) -> List[GreenfieldCompetitorCandidate]:
    """Discover competitors from SERP analysis of seed keywords."""
    competitors = []
    domain_counts = {}

    for keyword in seed_keywords:
        try:
            # Use DataForSEO SERP API
            serp_results = await client.get_serp_results(
                keyword=keyword,
                location=market,
                language=language,
                depth=10,
            )

            for result in serp_results.get("items", []):
                domain = result.get("domain", "")
                if not domain:
                    continue

                # Skip excluded domains (social media, platforms, etc.)
                from src.utils.domain_filter import is_excluded_domain
                if is_excluded_domain(domain):
                    continue

                domain_counts[domain] = domain_counts.get(domain, 0) + 1

        except Exception as e:
            logger.warning(f"SERP analysis for '{keyword}' failed: {e}")

    # Convert to candidates (domains appearing 2+ times)
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        if count >= 2:
            competitors.append(GreenfieldCompetitorCandidate(
                domain=domain,
                discovery_source="serp",
                discovery_reason=f"Ranks for {count} of your seed keywords",
                relevance_score=min(0.95, 0.5 + count * 0.1),
            ))

    return competitors[:15]  # Limit to top 15


async def _discover_from_traffic_share(
    client,
    reference_domains: List[str],
    market: str,
) -> List[GreenfieldCompetitorCandidate]:
    """Discover competitors from traffic share analysis."""
    competitors = []

    for ref_domain in reference_domains[:2]:
        try:
            # Use DataForSEO domain competitors endpoint
            traffic_share = await client.get_domain_competitors(
                domain=ref_domain,
                location=market,
            )

            for comp in traffic_share.get("items", [])[:5]:
                domain = comp.get("domain", "")
                if domain:
                    competitors.append(GreenfieldCompetitorCandidate(
                        domain=domain,
                        discovery_source="traffic_share",
                        discovery_reason=f"Competes with {ref_domain} for traffic",
                        relevance_score=comp.get("intersection_score", 0.5),
                    ))

        except Exception as e:
            logger.warning(f"Traffic share for {ref_domain} failed: {e}")

    return competitors


async def _validate_competitors(
    client,
    candidates: List[GreenfieldCompetitorCandidate],
    target_dr: int,
    market: str,
) -> ValidatedCompetitorSet:
    """Validate and enrich competitors with metrics."""
    validated = []
    warnings = []

    for candidate in candidates:
        try:
            # Get domain overview for organic metrics
            overview = await client.get_domain_overview(
                domain=candidate.domain,
                location=market,
            )

            # Get Domain Rating from backlinks summary, not domain overview
            # The domain_rank_overview API doesn't return DR - it must come from backlinks/summary
            backlink_summary = await client.get_backlink_summary(domain=candidate.domain)

            candidate.domain_rating = backlink_summary.get("domain_rank", 0) if backlink_summary else 0
            candidate.organic_traffic = overview.get("organic_traffic", 0)
            candidate.organic_keywords = overview.get("organic_keywords", 0)
            candidate.referring_domains = backlink_summary.get("referring_domains", 0) if backlink_summary else 0
            candidate.is_validated = True

            # Check for DR too far from target
            if candidate.domain_rating > target_dr + 50:
                candidate.validation_warnings.append(
                    f"DR {candidate.domain_rating} is much higher than target ({target_dr})"
                )
                candidate.suggested_purpose = "aspirational"
            elif candidate.domain_rating < target_dr:
                candidate.suggested_purpose = "benchmark_peer"
            else:
                candidate.suggested_purpose = "keyword_source"

            validated.append(candidate)

        except Exception as e:
            logger.warning(f"Validation failed for {candidate.domain}: {e}")
            # Keep the candidate but mark as not validated
            candidate.validation_warnings.append(f"Validation failed: {str(e)}")
            validated.append(candidate)

    # Sort by relevance and DR
    validated.sort(
        key=lambda c: (c.relevance_score, c.organic_traffic),
        reverse=True
    )

    return ValidatedCompetitorSet(
        competitors=validated[:15],  # Keep top 15
        validation_warnings=warnings,
    )


# =============================================================================
# PHASE G2: KEYWORD UNIVERSE CONSTRUCTION
# =============================================================================

async def _build_keyword_universe(
    client,
    competitors: List[GreenfieldCompetitorCandidate],
    seed_keywords: List[str],
    market: str,
    language: str,
) -> List[GreenfieldKeyword]:
    """Build keyword universe from competitors and seed keywords."""
    keywords = {}  # Use dict for deduplication

    # Source 1: Seed keywords and their expansions
    for seed in seed_keywords:
        try:
            related = await client.get_keyword_ideas(
                keyword=seed,
                location=market,
                language=language,
                limit=50,
            )

            for kw in related.get("items", []):
                keyword = kw.get("keyword", "").lower().strip()
                if keyword and keyword not in keywords:
                    keywords[keyword] = GreenfieldKeyword(
                        keyword=keyword,
                        search_volume=kw.get("search_volume", 0),
                        keyword_difficulty=kw.get("keyword_difficulty", 50),
                        cpc=kw.get("cpc", 0),
                        search_intent=kw.get("search_intent", {}).get("main", "informational"),
                        business_relevance=0.9,  # High relevance for seed expansions
                    )
        except Exception as e:
            logger.warning(f"Keyword ideas for '{seed}' failed: {e}")

    # Source 2: Competitor rankings
    for comp in competitors[:10]:  # Top 10 competitors
        if not comp.is_validated:
            continue

        try:
            rankings = await client.get_ranked_keywords(
                domain=comp.domain,
                location=market,
                language=language,
                limit=200,
            )

            for kw in rankings.get("items", []):
                keyword = kw.get("keyword", "").lower().strip()
                if keyword and keyword not in keywords:
                    keywords[keyword] = GreenfieldKeyword(
                        keyword=keyword,
                        search_volume=kw.get("search_volume", 0),
                        keyword_difficulty=kw.get("keyword_difficulty", 50),
                        cpc=kw.get("cpc", 0),
                        search_intent=kw.get("search_intent", {}).get("main", "informational"),
                        source_competitor=comp.domain,
                        competitor_position=kw.get("position", 0),
                        business_relevance=0.7,  # Medium relevance for competitor keywords
                    )
        except Exception as e:
            logger.warning(f"Ranked keywords for {comp.domain} failed: {e}")

    # Filter and sort
    universe = list(keywords.values())

    # Remove very low volume keywords
    universe = [kw for kw in universe if kw.search_volume >= 10]

    # Sort by business relevance × volume
    universe.sort(key=lambda k: k.business_relevance * k.search_volume, reverse=True)

    return universe[:1000]  # Cap at 1000 keywords


# =============================================================================
# PHASE G3: SERP ANALYSIS
# =============================================================================

async def _analyze_serps_batch(
    client,
    keywords: List[GreenfieldKeyword],
    target_dr: int,
    market: str,
    language: str,
    industry: str,
) -> Dict[str, WinnabilityAnalysis]:
    """Analyze SERPs in batches and calculate winnability."""
    analyses = {}

    # Process in batches of 10
    batch_size = 10
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]

        # Create tasks for parallel SERP fetching
        tasks = [
            _analyze_single_serp(client, kw, target_dr, market, language, industry)
            for kw in batch
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for kw, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.warning(f"SERP analysis for '{kw.keyword}' failed: {result}")
            elif result:
                analyses[kw.keyword] = result

        # Rate limiting
        await asyncio.sleep(0.5)

    return analyses


async def _analyze_single_serp(
    client,
    keyword: GreenfieldKeyword,
    target_dr: int,
    market: str,
    language: str,
    industry: str,
) -> Optional[WinnabilityAnalysis]:
    """Analyze a single SERP and calculate winnability."""
    try:
        serp_data = await client.get_serp_results(
            keyword=keyword.keyword,
            location=market,
            language=language,
            depth=10,
        )

        keyword_dict = {
            "keyword": keyword.keyword,
            "search_volume": keyword.search_volume,
            "keyword_difficulty": keyword.keyword_difficulty,
            "business_relevance": keyword.business_relevance,
        }

        return calculate_winnability_full(
            keyword=keyword_dict,
            target_dr=target_dr,
            serp_data=serp_data,
            industry=industry,
        )

    except Exception as e:
        logger.debug(f"SERP analysis failed for '{keyword.keyword}': {e}")
        return None


# =============================================================================
# PHASE G5: GROWTH ROADMAP
# =============================================================================

def _build_growth_roadmap(
    beachhead_keywords: List[BeachheadKeyword],
    keyword_universe: List[GreenfieldKeyword],
    market_opportunity: Optional[MarketOpportunity],
) -> List[Dict[str, Any]]:
    """Build growth roadmap with phased keyword targeting."""

    # Phase 1: Foundation (months 1-3) - Beachheads only
    phase1_keywords = [bh.keyword for bh in beachhead_keywords[:10]]
    phase1_volume = sum(bh.search_volume for bh in beachhead_keywords[:10])

    # Phase 2: Traction (months 4-6) - Remaining beachheads + medium difficulty
    phase2_keywords = [bh.keyword for bh in beachhead_keywords[10:]]
    medium_kws = [
        kw for kw in keyword_universe
        if kw.winnability_score >= 50 and kw.winnability_score < 70
        and kw.keyword not in phase1_keywords
    ][:15]
    phase2_keywords.extend([kw.keyword for kw in medium_kws])
    phase2_volume = sum(bh.search_volume for bh in beachhead_keywords[10:])
    phase2_volume += sum(kw.search_volume for kw in medium_kws)

    # Phase 3: Authority (months 7-12) - Competitive keywords
    phase3_keywords = [
        kw.keyword for kw in keyword_universe
        if kw.winnability_score >= 30 and kw.winnability_score < 50
        and kw.keyword not in phase1_keywords
        and kw.keyword not in phase2_keywords
    ][:25]
    phase3_volume = sum(
        kw.search_volume for kw in keyword_universe
        if kw.keyword in phase3_keywords
    )

    return [
        {
            "phase": "Foundation",
            "phase_number": 1,
            "months": "1-3",
            "focus": "Establish beachheads",
            "strategy": "Target high-winnability, low-competition keywords",
            "keyword_count": len(phase1_keywords),
            "total_volume": phase1_volume,
            "expected_traffic": int(phase1_volume * 0.05),  # Conservative 5% capture
            "keywords": phase1_keywords,
        },
        {
            "phase": "Traction",
            "phase_number": 2,
            "months": "4-6",
            "focus": "Expand keyword coverage",
            "strategy": "Build on beachhead success with medium-difficulty keywords",
            "keyword_count": len(phase2_keywords),
            "total_volume": phase2_volume,
            "expected_traffic": int(phase2_volume * 0.08),  # 8% capture
            "keywords": phase2_keywords,
        },
        {
            "phase": "Authority",
            "phase_number": 3,
            "months": "7-12",
            "focus": "Compete for valuable keywords",
            "strategy": "Leverage built authority to target competitive keywords",
            "keyword_count": len(phase3_keywords),
            "total_volume": phase3_volume,
            "expected_traffic": int(phase3_volume * 0.10),  # 10% capture
            "keywords": phase3_keywords,
        },
    ]


def _calculate_completeness(result: GreenfieldCollectionResult) -> float:
    """Calculate data completeness score (0-100)."""
    score = 0.0

    # Competitors (25 points)
    if result.competitors:
        validated_count = sum(1 for c in result.competitors if c.is_validated)
        score += min(25, (validated_count / 10) * 25)

    # Keywords (25 points)
    if result.keyword_universe:
        score += min(25, (len(result.keyword_universe) / 500) * 25)

    # Winnability (25 points)
    if result.winnability_analyses:
        score += min(25, (len(result.winnability_analyses) / 100) * 25)

    # Beachheads (15 points)
    if result.beachhead_keywords:
        score += min(15, (len(result.beachhead_keywords) / 20) * 15)

    # Market opportunity (10 points)
    if result.market_opportunity:
        score += 10

    return min(100, score)

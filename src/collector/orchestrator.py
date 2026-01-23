"""
Data Collection Orchestrator

Coordinates the multi-phase data collection process.

FIXES APPLIED:
- Phase 3 call now uses correct argument order (named arguments)
- Phase 4 call now includes brand_name parameter
- Default language changed from "sv" to "Swedish" (full name)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CollectionConfig:
    """Configuration for data collection."""
    domain: str
    market: str = "Sweden"
    language: str = "Swedish"  # FIXED: was "sv" - must be full name like "Swedish", "English"
    brand_name: Optional[str] = None
    industry: str = "General"
    competitors: Optional[List[str]] = None

    # Limits
    max_seed_keywords: int = 5
    max_competitors: int = 5
    max_backlinks: int = 500

    # Options
    skip_ai_analysis: bool = False
    skip_technical_audits: bool = False
    skip_phases: Optional[List[int]] = None
    early_termination_threshold: int = 10  # Min keywords to continue


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

        # Check for minimal domain
        if self._should_abbreviate(foundation):
            logger.info("Domain has minimal data - abbreviated analysis")
            warnings.append("Domain has minimal data - abbreviated analysis performed")
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
        if 2 not in skip:
            try:
                from src.collector.phase2 import collect_keyword_data
                logger.info("Phase 2: Collecting keyword data...")
                keywords_data = await collect_keyword_data(
                    self.client,
                    config.domain,
                    config.market,
                    config.language,
                    seed_keywords=self._extract_seed_keywords(foundation)
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

        # Determine success (critical failure if Phase 1 failed completely)
        success = bool(foundation.get("domain_overview"))

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

    def _should_abbreviate(self, foundation: Dict) -> bool:
        """Check if domain has enough data for full analysis."""
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


# =============================================================================
# DATA DICTIONARY - Comprehensive field documentation for AI agents
# =============================================================================

DATA_DICTIONARY = {
    "domain_overview": {
        "_description": "Core domain metrics from DataForSEO Domain Overview API",
        "_source": "DataForSEO /v3/dataforseo_labs/google/domain_metrics_by_categories/live",
        "_reliability": "HIGH - Direct Google index data",
        "organic_keywords": {
            "meaning": "Total keywords this domain ranks for in Google top 100",
            "interpretation": "Higher = broader visibility. <100 = minimal presence, 100-1000 = emerging, 1000-10000 = established, >10000 = dominant",
        },
        "organic_traffic": {
            "meaning": "Estimated monthly organic visitors based on keyword positions and CTR models",
            "interpretation": "Modeled estimate, not actual analytics. Typically 60-80% of real traffic due to long-tail not captured",
        },
        "organic_cost": {
            "meaning": "Equivalent Google Ads spend to buy this traffic at current CPCs",
            "interpretation": "Higher = more valuable traffic. Useful for ROI calculations",
        },
        "domain_rank": {
            "meaning": "DataForSEO's proprietary authority score (0-1000 scale)",
            "interpretation": "Combines backlink authority + traffic. <100 = low authority, 100-300 = moderate, >300 = strong",
        },
    },
    "ranked_keywords": {
        "_description": "Keywords where the domain currently ranks in Google top 100",
        "_source": "DataForSEO /v3/dataforseo_labs/google/ranked_keywords/live",
        "_reliability": "HIGH - Direct SERP position data",
        "_truncation_note": "May be truncated to 1000 keywords. Full data can have 10,000+",
        "keyword": {"meaning": "The search query text"},
        "position": {
            "meaning": "Current Google ranking position (1-100)",
            "interpretation": "1-3 = high CTR (20-30%), 4-10 = moderate CTR (5-10%), 11-20 = low CTR (1-3%), 21+ = minimal traffic",
        },
        "search_volume": {
            "meaning": "Average monthly searches in the target market",
            "interpretation": "Higher = more potential traffic. But consider competition",
        },
        "cpc": {
            "meaning": "Average cost-per-click in Google Ads for this keyword",
            "interpretation": "Higher CPC = higher commercial intent = more valuable traffic",
        },
        "keyword_difficulty": {
            "meaning": "DataForSEO's difficulty score (0-100)",
            "interpretation": "0-30 = easy (can rank with content alone), 30-60 = moderate (need links), 60+ = hard (need authority)",
        },
        "url": {"meaning": "The URL that ranks for this keyword"},
        "traffic": {
            "meaning": "Estimated monthly traffic from this keyword",
            "interpretation": "position × search_volume × CTR_model",
        },
        "traffic_cost": {"meaning": "Equivalent Google Ads cost for this keyword's traffic"},
        "competition_level": {
            "meaning": "Google Ads competition indicator",
            "interpretation": "'high' = advertisers pay for this = commercial intent",
        },
        "intent": {
            "meaning": "Search intent classification",
            "interpretation": "'informational' = research, 'commercial' = comparison, 'transactional' = buy, 'navigational' = brand",
        },
    },
    "keyword_gaps": {
        "_description": "Keywords competitors rank for but target domain does not",
        "_source": "DataForSEO /v3/dataforseo_labs/google/competitors_domain/live comparison",
        "_reliability": "HIGH - Direct comparison data",
        "_truncation_note": "May be truncated. Gaps can number in thousands",
        "keyword": {"meaning": "Search query competitor ranks for"},
        "search_volume": {"meaning": "Monthly search volume"},
        "competitor_positions": {
            "meaning": "Dict of competitor domain -> their ranking position",
            "interpretation": "Lower position number = they rank better. Use to identify who to target content against",
        },
        "opportunity_score": {
            "meaning": "Calculated as: search_volume × (1 - difficulty/100) × intent_multiplier",
            "interpretation": "Higher = better opportunity. Prioritize top scores for content creation",
            "formula": "search_volume * (1 - keyword_difficulty/100) * (1.5 if transactional else 1.2 if commercial else 1.0)",
        },
    },
    "competitors": {
        "_description": "Domains competing for similar keywords",
        "_source": "DataForSEO /v3/dataforseo_labs/google/competitors_domain/live",
        "_reliability": "HIGH - Based on keyword overlap analysis",
        "domain": {"meaning": "Competitor domain name"},
        "competitor_type": {
            "meaning": "Classification based on overlap and trajectory",
            "interpretation": "'direct' = same keywords, 'indirect' = adjacent keywords, 'emerging' = growing fast, 'declining' = losing ground",
            "classification_rules": {
                "direct": "Keyword overlap > 30% AND similar traffic range (0.5x-2x)",
                "indirect": "Keyword overlap 10-30% OR different traffic tier",
                "emerging": "Traffic growth > 20% month-over-month AND overlap > 10%",
                "declining": "Traffic decline > 15% month-over-month",
            },
        },
        "organic_keywords": {"meaning": "Their total ranking keywords"},
        "organic_traffic": {"meaning": "Their estimated monthly traffic"},
        "common_keywords": {
            "meaning": "Number of keywords both domains rank for",
            "interpretation": "Higher = more direct competition",
        },
    },
    "backlink_summary": {
        "_description": "Overview of domain's backlink profile",
        "_source": "DataForSEO /v3/backlinks/summary/live",
        "_reliability": "MEDIUM-HIGH - DataForSEO crawl may miss some links",
        "total_backlinks": {
            "meaning": "Total number of backlinks pointing to domain",
            "interpretation": "Raw count. Quality matters more than quantity",
        },
        "referring_domains": {
            "meaning": "Unique domains linking to the target",
            "interpretation": "More important than total links. 100+ RDs = established, 500+ = strong, 1000+ = authoritative",
        },
        "domain_rank": {
            "meaning": "DataForSEO's authority score combining link metrics",
            "interpretation": "0-100 scale. 30+ = credible, 50+ = strong, 70+ = highly authoritative",
        },
        "dofollow_percentage": {
            "meaning": "Percentage of links passing PageRank",
            "interpretation": "50-80% is healthy. <40% may indicate low-quality profile. >90% may indicate manipulation",
        },
    },
    "referring_domains": {
        "_description": "List of domains linking to target",
        "_source": "DataForSEO /v3/backlinks/referring_domains/live",
        "_reliability": "MEDIUM-HIGH",
        "_truncation_note": "Limited to top 500 by authority. Full list can be thousands",
        "domain": {"meaning": "The referring domain"},
        "domain_rank": {
            "meaning": "Authority score of the referring domain",
            "interpretation": "Higher = more valuable link. DR 50+ links are premium",
        },
        "backlinks": {"meaning": "Number of links from this domain to target"},
        "first_seen": {"meaning": "Date link was first discovered"},
    },
    "technical_audit": {
        "_description": "Site technical health assessment",
        "_source": "DataForSEO /v3/on_page/lighthouse/live",
        "_reliability": "HIGH - Based on actual page rendering",
        "performance_score": {
            "meaning": "Google Lighthouse performance score (0-100)",
            "interpretation": "90+ = excellent, 50-89 = needs improvement, <50 = poor (impacts rankings)",
        },
        "accessibility_score": {"meaning": "Lighthouse accessibility score (0-100)"},
        "best_practices_score": {"meaning": "Lighthouse best practices score (0-100)"},
        "seo_score": {
            "meaning": "Lighthouse SEO score (0-100)",
            "interpretation": "Basic on-page SEO health. 90+ expected for modern sites",
        },
    },
    "ai_visibility": {
        "_description": "Brand presence in AI-generated responses",
        "_source": "DataForSEO AI Overview and custom LLM queries",
        "_reliability": "MEDIUM - AI responses vary by session/time",
        "mentioned": {
            "meaning": "Whether brand appears in AI overviews for target keywords",
            "interpretation": "Boolean. Presence in AI = future traffic source",
        },
        "cited": {
            "meaning": "Whether brand is cited as a source in AI responses",
            "interpretation": "Citations = authority recognition by AI systems",
        },
    },
    "_scoring_formulas": {
        "opportunity_score": "search_volume × (1 - difficulty/100) × intent_multiplier. intent_multiplier: transactional=1.5, commercial=1.2, informational=1.0",
        "personalized_difficulty": "base_difficulty × (competitor_authority / our_authority). Harder if competitors stronger",
        "traffic_value": "estimated_traffic × CPC. Dollar value of organic traffic",
        "content_decay_risk": "traffic_change_90d < -20% = HIGH, -10 to -20% = MEDIUM, stable = LOW",
        "link_quality_score": "Average DR of referring domains × dofollow_percentage",
    },
    "_data_limitations": {
        "traffic_estimates": "Modeled from CTR curves, typically 60-80% of actual. Use for relative comparison, not absolute numbers",
        "keyword_coverage": "DataForSEO may miss long-tail queries. Total universe could be 2-5x larger",
        "backlink_freshness": "Crawl data may be 1-4 weeks old. Recent link changes not reflected",
        "competitor_classification": "Algorithmic. May misclassify niche competitors or new entrants",
        "ai_visibility": "AI responses are non-deterministic. Results represent a snapshot, not consistent behavior",
    },
}


def _calculate_data_quality(result: CollectionResult) -> Dict[str, Any]:
    """
    Calculate comprehensive data quality metrics for AI context.

    Returns quality scores, completeness indicators, and specific warnings
    to help agents understand data reliability.
    """
    quality = {
        "overall_score": 0.0,
        "phase_scores": {},
        "completeness": {},
        "truncation_warnings": [],
        "missing_data": [],
        "reliability_notes": [],
        "confidence_indicators": {},
    }

    # Phase 1 completeness
    phase1_fields = [
        ("domain_overview", result.domain_overview, "Critical for analysis"),
        ("competitors", result.competitors, "Needed for competitive analysis"),
        ("backlink_summary", result.backlink_summary, "Authority assessment"),
        ("top_pages", result.top_pages, "Content performance"),
        ("technical_baseline", result.technical_baseline, "Technical health"),
    ]
    phase1_complete = sum(1 for _, v, _ in phase1_fields if v) / len(phase1_fields)
    quality["phase_scores"]["phase1_foundation"] = phase1_complete
    for name, value, purpose in phase1_fields:
        if not value:
            quality["missing_data"].append(f"{name}: {purpose}")

    # Phase 2 completeness
    phase2_fields = [
        ("ranked_keywords", result.ranked_keywords, "Current rankings"),
        ("keyword_gaps", result.keyword_gaps, "Opportunity identification"),
        ("keyword_clusters", result.keyword_clusters, "Topical authority"),
    ]
    phase2_complete = sum(1 for _, v, _ in phase2_fields if v) / len(phase2_fields)
    quality["phase_scores"]["phase2_keywords"] = phase2_complete
    for name, value, purpose in phase2_fields:
        if not value:
            quality["missing_data"].append(f"{name}: {purpose}")

    # Phase 3 completeness
    phase3_fields = [
        ("competitor_metrics", result.competitor_metrics, "Competitor benchmarking"),
        ("referring_domains", result.referring_domains, "Link profile analysis"),
        ("link_gaps", result.link_gaps, "Link building targets"),
    ]
    phase3_complete = sum(1 for _, v, _ in phase3_fields if v) / len(phase3_fields)
    quality["phase_scores"]["phase3_competitive"] = phase3_complete
    for name, value, purpose in phase3_fields:
        if not value:
            quality["missing_data"].append(f"{name}: {purpose}")

    # Phase 4 completeness
    phase4_fields = [
        ("technical_audit", result.technical_audit, "Technical assessment"),
        ("ai_visibility", result.ai_visibility, "AI presence"),
        ("brand_mentions", result.brand_mentions, "Brand awareness"),
    ]
    phase4_complete = sum(1 for _, v, _ in phase4_fields if v) / len(phase4_fields)
    quality["phase_scores"]["phase4_ai_technical"] = phase4_complete
    for name, value, purpose in phase4_fields:
        if not value:
            quality["missing_data"].append(f"{name}: {purpose}")

    # Truncation warnings - help agents understand they're seeing a sample
    truncation_thresholds = [
        ("ranked_keywords", result.ranked_keywords, 1000, "May have 10,000+ keywords"),
        ("keyword_gaps", result.keyword_gaps, 500, "May have thousands of gaps"),
        ("referring_domains", result.referring_domains, 500, "May have thousands of RDs"),
        ("backlinks", result.backlinks, 500, "May have millions of backlinks"),
        ("competitors", result.competitors, 20, "May have hundreds of competitors"),
    ]
    for name, data, threshold, note in truncation_thresholds:
        if isinstance(data, list) and len(data) >= threshold * 0.9:
            quality["truncation_warnings"].append({
                "field": name,
                "shown": len(data),
                "threshold": threshold,
                "note": f"Data likely truncated. {note}",
            })

    # Overall quality score
    phase_weights = {"phase1_foundation": 0.3, "phase2_keywords": 0.3, "phase3_competitive": 0.2, "phase4_ai_technical": 0.2}
    quality["overall_score"] = sum(
        quality["phase_scores"].get(phase, 0) * weight
        for phase, weight in phase_weights.items()
    ) * 100

    # Confidence indicators for key metrics
    quality["confidence_indicators"] = {
        "traffic_estimates": "MEDIUM - Modeled from CTR curves, use for relative comparison",
        "keyword_positions": "HIGH - Direct SERP data from DataForSEO",
        "backlink_counts": "MEDIUM-HIGH - Crawl-based, may miss recent changes",
        "competitor_classification": "MEDIUM - Algorithmic classification based on overlap",
        "ai_visibility": "LOW-MEDIUM - AI responses are non-deterministic",
        "technical_scores": "HIGH - Direct Lighthouse measurements",
    }

    # Add reliability notes based on data state
    if result.errors:
        quality["reliability_notes"].append(f"Collection had {len(result.errors)} error(s): data may be incomplete")
    if result.warnings:
        quality["reliability_notes"].append(f"Collection had {len(result.warnings)} warning(s)")
    if not result.domain_overview.get("organic_keywords"):
        quality["reliability_notes"].append("Domain appears to have minimal organic presence - limited data available")

    return quality


def compile_analysis_data(result: CollectionResult) -> Dict[str, Any]:
    """
    Compile collection result into a structured format for AI analysis.

    This function transforms the raw CollectionResult into a format
    optimized for consumption by Claude's analysis loops, including:
    - Comprehensive data dictionary explaining field meanings
    - Data quality metrics and completeness scores
    - Truncation warnings and confidence indicators

    Args:
        result: CollectionResult from data collection

    Returns:
        Dict containing structured data ready for AI analysis with full context
    """
    from dataclasses import asdict

    # Convert dataclass to dict
    data = asdict(result)

    # Convert datetime to ISO format
    if data.get("timestamp"):
        data["timestamp"] = data["timestamp"].isoformat()

    # Calculate data quality metrics
    data_quality = _calculate_data_quality(result)

    # Structure for AI analysis with comprehensive context
    compiled = {
        # =====================================================================
        # DATA DICTIONARY - Explains what each field means
        # =====================================================================
        "data_dictionary": DATA_DICTIONARY,

        # =====================================================================
        # DATA QUALITY - Helps agents understand data reliability
        # =====================================================================
        "data_quality": data_quality,

        # =====================================================================
        # METADATA - Collection context
        # =====================================================================
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
            "data_freshness": "Data collected at timestamp above. Backlink data may be 1-4 weeks old.",
        },

        # =====================================================================
        # PHASE 1: FOUNDATION DATA
        # =====================================================================
        "phase1_foundation": {
            "domain_overview": result.domain_overview,
            "historical_data": result.historical_data,
            "subdomains": result.subdomains,
            "top_pages": result.top_pages,
            "competitors": result.competitors,
            "backlink_summary": result.backlink_summary,
            "technical_baseline": result.technical_baseline,
            "technologies": result.technologies,
            "_field_counts": {
                "competitors_shown": len(result.competitors),
                "top_pages_shown": len(result.top_pages),
                "subdomains_shown": len(result.subdomains),
            },
        },

        # =====================================================================
        # PHASE 2: KEYWORD INTELLIGENCE
        # =====================================================================
        "phase2_keywords": {
            "ranked_keywords": result.ranked_keywords,
            "keyword_universe": result.keyword_universe,
            "keyword_gaps": result.keyword_gaps,
            "keyword_clusters": result.keyword_clusters,
            "intent_classification": result.intent_classification,
            "difficulty_scores": result.difficulty_scores,
            "_field_counts": {
                "ranked_keywords_shown": len(result.ranked_keywords),
                "keyword_gaps_shown": len(result.keyword_gaps),
                "keyword_clusters_shown": len(result.keyword_clusters),
                "total_claimed_keywords": result.domain_overview.get("organic_keywords", 0),
                "note": "ranked_keywords may be truncated. Use total_claimed_keywords for accurate count.",
            },
        },

        # =====================================================================
        # PHASE 3: COMPETITIVE & BACKLINK DATA
        # =====================================================================
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
            "_field_counts": {
                "referring_domains_shown": len(result.referring_domains),
                "backlinks_shown": len(result.backlinks),
                "total_claimed_backlinks": result.backlink_summary.get("total_backlinks", 0),
                "total_claimed_referring_domains": result.backlink_summary.get("referring_domains", 0),
                "note": "Backlink lists truncated to top 500 by authority. Full profile may have millions.",
            },
        },

        # =====================================================================
        # PHASE 4: AI VISIBILITY & TECHNICAL
        # =====================================================================
        "phase4_ai_technical": {
            "ai_visibility": result.ai_visibility,
            "ai_mentions": result.ai_mentions,
            "llm_responses": result.llm_responses,
            "brand_mentions": result.brand_mentions,
            "trend_data": result.trend_data,
            "technical_audit": result.technical_audit,
            "technical_audits": result.technical_audits,
            "_reliability_note": "AI visibility data is non-deterministic. Results represent a snapshot.",
        },

        # =====================================================================
        # SUMMARY METRICS - Quick reference
        # =====================================================================
        "summary": {
            "total_organic_keywords": result.domain_overview.get("organic_keywords", 0),
            "total_organic_traffic": result.domain_overview.get("organic_traffic", 0),
            "domain_rank": result.backlink_summary.get("domain_rank", 0),
            "total_backlinks": result.backlink_summary.get("total_backlinks", 0),
            "referring_domains_count": result.backlink_summary.get("referring_domains", 0),
            "competitor_count": len(result.competitors),
            "ranked_keywords_count": len(result.ranked_keywords),
            "keyword_gaps_count": len(result.keyword_gaps),
            "_interpretation_guide": {
                "traffic_reliability": "Estimated, typically 60-80% of actual. Use for relative comparisons.",
                "keyword_count_note": "ranked_keywords_count is sample size. total_organic_keywords is true count.",
                "domain_rank_scale": "0-1000. <100=low, 100-300=moderate, 300+=strong authority.",
            },
        },
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

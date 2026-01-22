"""
Phase 3: Competitive Intelligence & Backlinks

This module collects competitive and backlink data:
- Competitor domain metrics
- Keyword overlaps with competitors
- SERP-level competition
- Backlink profile (top links, anchors, referring domains)
- Link gap analysis
- Link velocity (new/lost over time)
- Referring networks (subnets, IPs)
- Broken backlinks for recovery opportunities
- New and lost backlinks tracking
- Page-level backlink intersection

Endpoints used:
1. dataforseo_labs/google/domain_rank_overview (x5 competitors)
2. dataforseo_labs/google/domain_intersection (x3 competitors)
3. dataforseo_labs/google/serp_competitors
4. backlinks/backlinks
5. backlinks/anchors
6. backlinks/referring_domains
7. backlinks/domain_intersection (link gap)
8. backlinks/timeseries_new_lost_summary
9. backlinks/referring_networks
10. backlinks/bulk_backlinks
11. backlinks/page_intersection
12. backlinks/history
13. backlinks/bulk_referring_domains
14. backlinks/competitors

Total: 15-18 API calls
Expected time: 8-12 seconds (with parallelization)

Note: All endpoints use language_name (e.g., "English") not language_code (e.g., "en")
Note: backlinks/domain_intersection requires targets as dict, not array
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# NON-COMPETITOR DOMAIN LISTS
# =============================================================================

# Domains that should NEVER be considered competitors - platforms and social media
NON_COMPETITOR_DOMAINS = {
    # Social Media
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "twitter.com", "www.twitter.com", "x.com",
    "instagram.com", "www.instagram.com",
    "linkedin.com", "www.linkedin.com",
    "tiktok.com", "www.tiktok.com",
    "pinterest.com", "www.pinterest.com",
    "reddit.com", "www.reddit.com",
    "tumblr.com", "www.tumblr.com",
    "snapchat.com", "www.snapchat.com",
    "whatsapp.com", "www.whatsapp.com",
    "telegram.org", "www.telegram.org",
    "discord.com", "www.discord.com",

    # Search Engines
    "google.com", "www.google.com", "google.se", "google.co.uk",
    "bing.com", "www.bing.com",
    "yahoo.com", "www.yahoo.com",
    "duckduckgo.com", "www.duckduckgo.com",
    "baidu.com", "www.baidu.com",
    "yandex.com", "www.yandex.com",

    # E-commerce Platforms
    "amazon.com", "www.amazon.com", "amazon.se", "amazon.co.uk", "amazon.de",
    "ebay.com", "www.ebay.com", "ebay.se", "ebay.co.uk",
    "etsy.com", "www.etsy.com",
    "aliexpress.com", "www.aliexpress.com",
    "alibaba.com", "www.alibaba.com",
    "wish.com", "www.wish.com",

    # Reference/Encyclopedia
    "wikipedia.org", "www.wikipedia.org", "en.wikipedia.org", "sv.wikipedia.org",
    "wikimedia.org", "www.wikimedia.org",
    "britannica.com", "www.britannica.com",
    "quora.com", "www.quora.com",
    "medium.com", "www.medium.com",

    # Developer/Tech Platforms
    "github.com", "www.github.com",
    "stackoverflow.com", "www.stackoverflow.com",
    "stackexchange.com", "www.stackexchange.com",
    "npmjs.com", "www.npmjs.com",
    "pypi.org", "www.pypi.org",

    # Cloud/Infrastructure
    "cloudflare.com", "www.cloudflare.com",
    "aws.amazon.com",
    "azure.microsoft.com",
    "cloud.google.com",

    # App Stores
    "play.google.com",
    "apps.apple.com", "itunes.apple.com",

    # Job Sites
    "indeed.com", "www.indeed.com",
    "glassdoor.com", "www.glassdoor.com",
    "monster.com", "www.monster.com",

    # Review Sites (generic)
    "trustpilot.com", "www.trustpilot.com",
    "yelp.com", "www.yelp.com",
    "tripadvisor.com", "www.tripadvisor.com",

    # Maps
    "maps.google.com",
    "maps.apple.com",
}

# Government and official domains - NOT competitors
GOVERNMENT_DOMAINS = {
    # Swedish government
    "krisinformation.se", "www.krisinformation.se",  # Crisis info
    "msb.se", "www.msb.se",  # Civil contingencies agency
    "folkhalsomyndigheten.se", "www.folkhalsomyndigheten.se",
    "regeringen.se", "www.regeringen.se",
    "riksdagen.se", "www.riksdagen.se",
    "polisen.se", "www.polisen.se",
    "forsakringskassan.se", "www.forsakringskassan.se",
    "skatteverket.se", "www.skatteverket.se",
    "1177.se", "www.1177.se",

    # International government
    "gov.uk", "www.gov.uk",
    "usa.gov", "www.usa.gov",
    "cdc.gov", "www.cdc.gov",
    "fema.gov", "www.fema.gov",
    "ready.gov", "www.ready.gov",
}

# Media and news organizations - NOT business competitors
MEDIA_DOMAINS = {
    # Swedish media
    "sverigesradio.se", "www.sverigesradio.se",  # Public radio
    "svt.se", "www.svt.se",  # Public TV
    "dn.se", "www.dn.se",  # Dagens Nyheter
    "expressen.se", "www.expressen.se",
    "aftonbladet.se", "www.aftonbladet.se",
    "gp.se", "www.gp.se",
    "sydsvenskan.se", "www.sydsvenskan.se",
    "tv4.se", "www.tv4.se",

    # International media
    "news.google.com", "news.yahoo.com",
    "msn.com", "www.msn.com",
    "cnn.com", "www.cnn.com",
    "bbc.com", "www.bbc.com", "bbc.co.uk",
    "nytimes.com", "www.nytimes.com",
    "theguardian.com", "www.theguardian.com",
    "forbes.com", "www.forbes.com",
    "businessinsider.com", "www.businessinsider.com",
    "reuters.com", "www.reuters.com",
    "apnews.com", "www.apnews.com",
}

# Patterns that indicate non-competitor domains
GOVERNMENT_PATTERNS = [".gov", ".gov.", ".myndighet", ".kommun."]
MEDIA_PATTERNS = ["radio", "tv", "news", "nyheter", "tidning", "media"]


def _get_root_domain(domain: str) -> str:
    """Extract root domain from a full domain string."""
    domain = domain.lower().strip()
    parts = domain.split(".")
    if len(parts) >= 2:
        return parts[-2] + "." + parts[-1]
    return domain


def _is_government_domain(domain: str) -> bool:
    """Check if domain is a government/official site."""
    domain_lower = domain.lower()
    root = _get_root_domain(domain_lower)

    # Check explicit list
    if domain_lower in GOVERNMENT_DOMAINS or root in GOVERNMENT_DOMAINS:
        return True

    # Check patterns
    for pattern in GOVERNMENT_PATTERNS:
        if pattern in domain_lower:
            return True

    return False


def _is_media_domain(domain: str) -> bool:
    """Check if domain is a media/news organization."""
    domain_lower = domain.lower()
    root = _get_root_domain(domain_lower)

    # Check explicit list
    if domain_lower in MEDIA_DOMAINS or root in MEDIA_DOMAINS:
        return True

    # Check patterns in domain name
    domain_name = root.split(".")[0]
    for pattern in MEDIA_PATTERNS:
        if pattern in domain_name:
            return True

    return False


def _is_real_competitor(domain: str, target_domain: str = None) -> bool:
    """
    Check if a domain is a real business competitor.

    Filters out:
    - Social media platforms
    - Search engines
    - Generic platforms (Amazon, eBay, Wikipedia, etc.)
    - Government and official sites
    - Media and news organizations
    - The target domain itself (if provided)
    - Subdomains of non-competitor domains

    Args:
        domain: The potential competitor domain
        target_domain: The domain being analyzed (optional)

    Returns:
        True if this is a real competitor, False otherwise
    """
    if not domain:
        return False

    domain_lower = domain.lower().strip()
    root_domain = _get_root_domain(domain_lower)

    # Filter out the target domain itself
    if target_domain:
        target_lower = target_domain.lower().strip()
        if domain_lower == target_lower or domain_lower.endswith(f".{target_lower}"):
            return False

    # Check against known non-competitor domains (platforms)
    if domain_lower in NON_COMPETITOR_DOMAINS or root_domain in NON_COMPETITOR_DOMAINS:
        return False

    # Check for government domains
    if _is_government_domain(domain_lower):
        logger.debug(f"Filtered government domain: {domain}")
        return False

    # Check for media domains
    if _is_media_domain(domain_lower):
        logger.debug(f"Filtered media domain: {domain}")
        return False

    # Check if it's a subdomain of a non-competitor
    for non_competitor in NON_COMPETITOR_DOMAINS:
        if domain_lower.endswith(f".{non_competitor}"):
            return False

    return True


def _safe_get_items(result: Dict, get_first: bool = True) -> List[Dict]:
    """
    Safely extract items from DataForSEO API response.
    Handles cases where result or nested values are None.

    Args:
        result: API response dict
        get_first: If True, gets items from result[0], else returns result list

    Returns:
        List of items or empty list
    """
    tasks = result.get("tasks") or [{}]
    task_result = tasks[0].get("result")

    if task_result is None:
        return []

    if get_first:
        if isinstance(task_result, list) and len(task_result) > 0:
            first_result = task_result[0]
            if isinstance(first_result, dict):
                return first_result.get("items") or []
        return []
    else:
        # Return the result list directly (for endpoints that return list at result level)
        return task_result if isinstance(task_result, list) else []


def _safe_get_first_result(result: Dict) -> Dict:
    """
    Safely get the first result object from DataForSEO API response.

    Returns:
        First result dict or empty dict
    """
    tasks = result.get("tasks") or [{}]
    task_result = tasks[0].get("result")

    if task_result is None:
        return {}

    if isinstance(task_result, list) and len(task_result) > 0:
        first = task_result[0]
        return first if isinstance(first, dict) else {}

    return {}


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class CompetitorMetrics:
    """Metrics for a competitor domain."""
    domain: str
    organic_traffic: int
    organic_keywords: int
    paid_traffic: int
    paid_keywords: int
    domain_rank: int
    backlinks: int
    referring_domains: int


@dataclass
class KeywordOverlap:
    """Keyword overlap between target and competitor."""
    competitor: str
    shared_keywords: int
    unique_to_target: int
    unique_to_competitor: int
    overlap_percentage: float
    opportunity_keywords: List[Dict[str, Any]]  # Keywords competitor ranks for, we don't


@dataclass
class Backlink:
    """A single backlink to the domain."""
    source_url: str
    source_domain: str
    target_url: str
    anchor: str
    domain_rank: int
    page_rank: int
    is_dofollow: bool
    first_seen: str
    link_type: str  # text, image, redirect, etc.


@dataclass
class AnchorDistribution:
    """Anchor text distribution."""
    anchor: str
    backlinks: int
    referring_domains: int
    percentage: float


@dataclass
class ReferringDomain:
    """A domain linking to the target."""
    domain: str
    backlinks: int
    domain_rank: int
    first_seen: str
    is_broken: bool


@dataclass
class LinkGapTarget:
    """A domain that links to competitors but not to us."""
    domain: str
    domain_rank: int
    links_to_competitors: int
    competitors_linked: List[str]


@dataclass
class Phase3Data:
    """Complete Phase 3 data container."""
    competitor_metrics: List[CompetitorMetrics] = field(default_factory=list)
    keyword_overlaps: List[KeywordOverlap] = field(default_factory=list)
    serp_competitors: List[Dict[str, Any]] = field(default_factory=list)
    backlinks: List[Backlink] = field(default_factory=list)
    anchor_distribution: List[AnchorDistribution] = field(default_factory=list)
    referring_domains: List[ReferringDomain] = field(default_factory=list)
    link_gap_targets: List[LinkGapTarget] = field(default_factory=list)
    link_velocity: Dict[str, Any] = field(default_factory=dict)

    # Aggregated metrics
    total_backlinks: int = 0
    total_referring_domains: int = 0
    dofollow_percentage: float = 0
    avg_competitor_traffic: int = 0


# ============================================================================
# MAIN COLLECTION FUNCTION
# ============================================================================

async def collect_competitive_data(
    client,  # DataForSEOClient
    domain: str,
    market: str,
    language: str,
    competitors: Optional[List[str]] = None,
    top_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Collect Phase 3: Competitive Intelligence & Backlinks data.

    Flow:
    1. If no competitors provided, identify them from SERP competitors
    2. Fetch competitor metrics in parallel
    3. Analyze keyword overlaps with top competitors
    4. Fetch backlink profile (links, anchors, referring domains) in parallel
    5. Identify link gap targets
    6. Get link velocity data

    Args:
        client: DataForSEO API client
        domain: Target domain
        market: Location name (e.g., "United States", "Sweden")
        language: Language name (e.g., "English", "Swedish") - NOT code!
        competitors: Optional list of competitor domains (from Phase 1)
        top_keywords: Optional list of top keywords (from Phase 2)

    Returns:
        Dictionary with all Phase 3 data
    """

    logger.info(f"Phase 3: Starting competitive intelligence for {domain}")

    # -------------------------------------------------------------------------
    # Step 1: Identify or validate competitors
    # -------------------------------------------------------------------------

    if not competitors:
        logger.info("Phase 3.1: Identifying competitors from SERP data...")
        serp_competitors_data = await fetch_serp_competitors(
            client, top_keywords or [domain], market, language,
            target_domain=domain  # Pass target domain for filtering
        )
        if not isinstance(serp_competitors_data, Exception):
            competitors = [c["domain"] for c in serp_competitors_data[:5]]
        else:
            logger.warning(f"Failed to fetch SERP competitors: {serp_competitors_data}")
            competitors = []

    # Apply real competitor filter to any pre-provided competitors as well
    competitors = [c for c in competitors if c != domain and _is_real_competitor(c, domain)][:5]

    logger.info(f"Phase 3.1: Analyzing {len(competitors)} competitors: {competitors}")

    # -------------------------------------------------------------------------
    # Step 2: Fetch competitor metrics (parallel)
    # -------------------------------------------------------------------------

    logger.info("Phase 3.2: Fetching competitor metrics...")

    competitor_metrics = []
    if competitors:
        metric_tasks = [
            fetch_domain_rank_overview(client, comp, market, language)
            for comp in competitors
        ]
        metric_results = await asyncio.gather(*metric_tasks, return_exceptions=True)

        for comp, result in zip(competitors, metric_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch metrics for {comp}: {result}")
            else:
                competitor_metrics.append(result)

    logger.info(f"Phase 3.2: Got metrics for {len(competitor_metrics)} competitors")

    # -------------------------------------------------------------------------
    # Step 3: Analyze keyword overlaps (parallel, top 3 competitors)
    # -------------------------------------------------------------------------

    logger.info("Phase 3.3: Analyzing keyword overlaps...")

    keyword_overlaps = []
    top_competitors = competitors[:3]

    if top_competitors:
        overlap_tasks = [
            fetch_domain_intersection(client, domain, comp, market, language)
            for comp in top_competitors
        ]
        overlap_results = await asyncio.gather(*overlap_tasks, return_exceptions=True)

        for comp, result in zip(top_competitors, overlap_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to analyze overlap with {comp}: {result}")
            else:
                keyword_overlaps.append(result)

    logger.info(f"Phase 3.3: Analyzed {len(keyword_overlaps)} competitor overlaps")

    # -------------------------------------------------------------------------
    # Step 4: Fetch backlink profile (parallel)
    # -------------------------------------------------------------------------

    logger.info("Phase 3.4: Fetching backlink profile...")

    backlink_tasks = [
        fetch_backlinks(client, domain, limit=500),
        fetch_anchors(client, domain, limit=100),
        fetch_referring_domains(client, domain, limit=200),
    ]

    backlink_results = await asyncio.gather(*backlink_tasks, return_exceptions=True)

    backlinks = backlink_results[0] if not isinstance(backlink_results[0], Exception) else []
    anchors = backlink_results[1] if not isinstance(backlink_results[1], Exception) else []
    referring_domains = backlink_results[2] if not isinstance(backlink_results[2], Exception) else []

    if isinstance(backlink_results[0], Exception):
        logger.warning(f"Failed to fetch backlinks: {backlink_results[0]}")
    if isinstance(backlink_results[1], Exception):
        logger.warning(f"Failed to fetch anchors: {backlink_results[1]}")
    if isinstance(backlink_results[2], Exception):
        logger.warning(f"Failed to fetch referring domains: {backlink_results[2]}")

    logger.info(f"Phase 3.4: Found {len(backlinks)} backlinks, {len(anchors)} anchors, "
                f"{len(referring_domains)} referring domains")

    # -------------------------------------------------------------------------
    # Step 5: Link gap analysis
    # -------------------------------------------------------------------------

    logger.info("Phase 3.5: Identifying link gap targets...")

    link_gap_targets = []
    if competitors:
        # Get domains linking to competitors but not to us
        targets_to_analyze = [domain] + competitors[:3]
        try:
            link_gap_result = await fetch_backlink_domain_intersection(
                client, targets_to_analyze
            )
            if not isinstance(link_gap_result, Exception):
                link_gap_targets = link_gap_result
            else:
                logger.warning(f"Failed to analyze link gaps: {link_gap_result}")
        except Exception as e:
            # Link gap is non-critical - continue without it
            logger.warning(f"Link gap analysis failed (non-critical): {e}")

    logger.info(f"Phase 3.5: Found {len(link_gap_targets)} link gap targets")

    # -------------------------------------------------------------------------
    # Step 6: Link velocity
    # -------------------------------------------------------------------------

    logger.info("Phase 3.6: Fetching link velocity...")

    link_velocity = await fetch_link_velocity(client, domain)

    if isinstance(link_velocity, Exception):
        logger.warning(f"Failed to fetch link velocity: {link_velocity}")
        link_velocity = {}

    # -------------------------------------------------------------------------
    # Step 7: Additional backlink intelligence (parallel)
    # -------------------------------------------------------------------------

    logger.info("Phase 3.7: Fetching additional backlink intelligence...")

    additional_tasks = [
        fetch_referring_networks(client, domain),
        fetch_broken_backlinks(client, domain, limit=100),
        fetch_backlink_history(client, domain),
        fetch_bulk_referring_domains(client, [domain] + competitors[:3]),
        fetch_backlink_competitors(client, domain),
    ]

    additional_results = await asyncio.gather(*additional_tasks, return_exceptions=True)

    referring_networks = additional_results[0] if not isinstance(additional_results[0], Exception) else {}
    broken_backlinks = additional_results[1] if not isinstance(additional_results[1], Exception) else []
    backlink_history = additional_results[2] if not isinstance(additional_results[2], Exception) else []
    bulk_ref_domains = additional_results[3] if not isinstance(additional_results[3], Exception) else {}
    backlink_competitors = additional_results[4] if not isinstance(additional_results[4], Exception) else []

    for i, name in enumerate(["referring_networks", "broken_backlinks", "backlink_history", "bulk_ref_domains", "backlink_competitors"]):
        if isinstance(additional_results[i], Exception):
            logger.warning(f"Failed to fetch {name}: {additional_results[i]}")

    # -------------------------------------------------------------------------
    # Step 7: Calculate aggregated metrics
    # -------------------------------------------------------------------------

    total_backlinks = len(backlinks)
    total_referring_domains = len(referring_domains)

    dofollow_count = sum(1 for bl in backlinks if bl.get("is_dofollow", False))
    dofollow_percentage = (dofollow_count / total_backlinks * 100) if total_backlinks else 0

    avg_competitor_traffic = (
        sum(m.organic_traffic for m in competitor_metrics) / len(competitor_metrics)
        if competitor_metrics else 0
    )

    # -------------------------------------------------------------------------
    # Return complete Phase 3 data
    # -------------------------------------------------------------------------

    return {
        "competitor_metrics": [
            {
                "domain": m.domain,
                "organic_traffic": m.organic_traffic,
                "organic_keywords": m.organic_keywords,
                "paid_traffic": m.paid_traffic,
                "paid_keywords": m.paid_keywords,
                "domain_rank": m.domain_rank,
                "backlinks": m.backlinks,
                "referring_domains": m.referring_domains,
            }
            for m in competitor_metrics
        ],
        "keyword_overlaps": [
            {
                "competitor": o.competitor,
                "shared_keywords": o.shared_keywords,
                "unique_to_target": o.unique_to_target,
                "unique_to_competitor": o.unique_to_competitor,
                "overlap_percentage": o.overlap_percentage,
                "opportunity_keywords": o.opportunity_keywords[:50],  # Top 50
            }
            for o in keyword_overlaps
        ],
        "backlinks": backlinks[:500],
        "anchor_distribution": anchors,
        "referring_domains": referring_domains,
        "link_gap_targets": link_gap_targets[:100],
        "link_velocity": link_velocity,
        "referring_networks": referring_networks,
        "broken_backlinks": broken_backlinks,
        "backlink_history": backlink_history,
        "bulk_ref_domains": bulk_ref_domains,
        "backlink_competitors": backlink_competitors,
        "total_backlinks": total_backlinks,
        "total_referring_domains": total_referring_domains,
        "dofollow_percentage": round(dofollow_percentage, 1),
        "avg_competitor_traffic": int(avg_competitor_traffic),
    }


# ============================================================================
# INDIVIDUAL ENDPOINT FUNCTIONS
# ============================================================================

async def fetch_domain_rank_overview(
    client,
    domain: str,
    market: str,
    language: str
) -> CompetitorMetrics:
    """
    Fetch comprehensive metrics for a domain.
    Returns traffic, keywords, rank, and backlink counts.
    """
    result = await client.post(
        "dataforseo_labs/google/domain_rank_overview/live",
        [{
            "target": domain,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
        }]
    )

    data = _safe_get_first_result(result)

    return CompetitorMetrics(
        domain=domain,
        organic_traffic=data.get("metrics", {}).get("organic", {}).get("etv", 0),
        organic_keywords=data.get("metrics", {}).get("organic", {}).get("count", 0),
        paid_traffic=data.get("metrics", {}).get("paid", {}).get("etv", 0),
        paid_keywords=data.get("metrics", {}).get("paid", {}).get("count", 0),
        domain_rank=data.get("rank", 0),
        backlinks=data.get("backlinks_info", {}).get("backlinks", 0),
        referring_domains=data.get("backlinks_info", {}).get("referring_domains", 0),
    )


async def fetch_domain_intersection(
    client,
    target: str,
    competitor: str,
    market: str,
    language: str,
    limit: int = 100
) -> KeywordOverlap:
    """
    Analyze keyword overlap between target and competitor.
    Returns shared keywords and opportunities (competitor ranks, we don't).
    """
    result = await client.post(
        "dataforseo_labs/google/domain_intersection/live",
        [{
            "target1": target,
            "target2": competitor,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
            "limit": limit,
            "intersections": True,  # Get shared keywords
        }]
    )

    task_result = _safe_get_first_result(result)
    items = task_result.get("items") or []

    shared = 0
    opportunities = []

    for item in items:
        kw_data = item.get("keyword_data", {})
        kw_info = kw_data.get("keyword_info", {})
        first_serp = item.get("first_domain_serp_element", {})
        second_serp = item.get("second_domain_serp_element", {})

        # Both ranking = shared
        if first_serp and second_serp:
            shared += 1
        # Competitor ranks, we don't = opportunity
        elif not first_serp and second_serp:
            opportunities.append({
                "keyword": kw_data.get("keyword", ""),
                "search_volume": kw_info.get("search_volume", 0),
                "competitor_position": second_serp.get("serp_item", {}).get("rank_group", 0),
            })

    # Get totals from task result
    total_count = task_result.get("total_count", 0)

    return KeywordOverlap(
        competitor=competitor,
        shared_keywords=shared,
        unique_to_target=0,  # Would need separate call
        unique_to_competitor=len(opportunities),
        overlap_percentage=(shared / total_count * 100) if total_count else 0,
        opportunity_keywords=opportunities,
    )


async def fetch_serp_competitors(
    client,
    keywords: List[str],
    market: str,
    language: str,
    target_domain: str = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Identify competitors from SERP data.
    Finds domains that rank for similar keywords.

    IMPORTANT: Filters out non-competitors like social media, platforms,
    government sites, and media organizations.
    Only returns actual business competitors.
    """
    result = await client.post(
        "dataforseo_labs/google/serp_competitors/live",
        [{
            "keywords": keywords[:200],  # Max 200 keywords
            "location_name": market,
            "language_name": language,
            "limit": 100,  # Fetch more to allow for thorough filtering
        }]
    )

    items = _safe_get_items(result)

    # Track filtering stats
    filtered_stats = {
        "platform": 0,
        "government": 0,
        "media": 0,
        "low_overlap": 0,
        "accepted": 0,
    }

    competitors = []
    for item in items:
        competitor_domain = item.get("domain", "")
        keywords_count = item.get("keywords_count", 0) or 0

        # Check domain type
        if competitor_domain in NON_COMPETITOR_DOMAINS or _get_root_domain(competitor_domain) in NON_COMPETITOR_DOMAINS:
            filtered_stats["platform"] += 1
            continue

        if _is_government_domain(competitor_domain):
            filtered_stats["government"] += 1
            logger.debug(f"Filtered government from SERP: {competitor_domain}")
            continue

        if _is_media_domain(competitor_domain):
            filtered_stats["media"] += 1
            logger.debug(f"Filtered media from SERP: {competitor_domain}")
            continue

        # Filter out target domain
        if target_domain:
            target_lower = target_domain.lower().strip()
            if competitor_domain.lower() == target_lower:
                continue

        # Very permissive keyword overlap threshold for niche sites
        min_keywords = 1  # Accept any overlap
        if keywords_count < min_keywords:
            filtered_stats["low_overlap"] += 1
            continue

        filtered_stats["accepted"] += 1
        competitors.append({
            "domain": competitor_domain,
            "visibility": item.get("visibility", 0),
            "relevant_serp_items": item.get("relevant_serp_items", 0),
            "keywords_count": keywords_count,
            "avg_position": item.get("avg_position", 0),
        })

        # Stop after getting enough real competitors
        if len(competitors) >= limit:
            break

    logger.info(f"SERP competitor filtering: {filtered_stats}")
    logger.info(f"Found {len(competitors)} real SERP competitors (filtered from {len(items)} raw results)")

    # Log warning if too few competitors found
    if len(competitors) < 3 and len(items) > 10:
        raw_domains = [item.get("domain", "")[:30] for item in items[:10]]
        logger.warning(f"Very few SERP competitors found. Top raw domains: {raw_domains}")

    return competitors


async def fetch_backlinks(
    client,
    domain: str,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Fetch backlinks to the domain.
    Returns link source, anchor, ranks, and attributes.
    """
    result = await client.post(
        "backlinks/backlinks/live",
        [{
            "target": domain,
            "limit": limit,
            "order_by": ["rank,desc"],  # Best links first
            "mode": "as_is",  # All links, not one per domain
        }]
    )

    items = _safe_get_items(result)

    backlinks = []
    for item in items:
        backlinks.append({
            "source_url": item.get("url_from", ""),
            "source_domain": item.get("domain_from", ""),
            "target_url": item.get("url_to", ""),
            "anchor": item.get("anchor", ""),
            "domain_rank": item.get("domain_from_rank", 0),
            "page_rank": item.get("page_from_rank", 0),
            "is_dofollow": item.get("dofollow", False),
            "first_seen": item.get("first_seen", ""),
            "link_type": item.get("type", ""),
            "is_broken": item.get("is_broken", False),
        })

    return backlinks


async def fetch_anchors(
    client,
    domain: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch anchor text distribution.
    Returns anchors with backlink counts.
    """
    result = await client.post(
        "backlinks/anchors/live",
        [{
            "target": domain,
            "limit": limit,
            "order_by": ["backlinks,desc"],
        }]
    )

    first_result = _safe_get_first_result(result)
    items = first_result.get("items") or []
    total_backlinks = first_result.get("total_count", 1) or 1

    anchors = []
    for item in items:
        bl_count = item.get("backlinks", 0)
        anchors.append({
            "anchor": item.get("anchor", ""),
            "backlinks": bl_count,
            "referring_domains": item.get("referring_domains", 0),
            "percentage": round(bl_count / total_backlinks * 100, 2) if total_backlinks else 0,
        })

    return anchors


async def fetch_referring_domains(
    client,
    domain: str,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """
    Fetch referring domains.
    Returns domains linking to target with metrics.
    """
    result = await client.post(
        "backlinks/referring_domains/live",
        [{
            "target": domain,
            "limit": limit,
            "order_by": ["rank,desc"],  # Best domains first
        }]
    )

    items = _safe_get_items(result)

    domains = []
    for item in items:
        domains.append({
            "domain": item.get("domain", ""),
            "backlinks": item.get("backlinks", 0),
            "domain_rank": item.get("rank", 0),
            "first_seen": item.get("first_seen", ""),
            "is_broken": item.get("broken_backlinks", 0) > 0,
        })

    return domains


def _clean_domain(domain: str) -> str:
    """Clean domain by removing protocol and trailing slashes."""
    domain = domain.strip()
    # Remove protocol
    if domain.startswith("https://"):
        domain = domain[8:]
    elif domain.startswith("http://"):
        domain = domain[7:]
    # Remove trailing slash
    domain = domain.rstrip("/")
    # Remove www. prefix for consistency
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


async def fetch_backlink_domain_intersection(
    client,
    targets: List[str],
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Find domains linking to competitors but not to us (link gap).
    targets[0] = our domain, targets[1:] = competitors

    FIXED: targets must be a dict with numbered keys, not an array
    FIXED: Clean domains and handle API errors gracefully
    """
    # Validate and clean targets
    if not targets or len(targets) < 2:
        logger.warning("Link gap analysis requires at least 2 targets (domain + 1 competitor)")
        return []

    # Clean all domains
    cleaned_targets = [_clean_domain(t) for t in targets if t]
    cleaned_targets = [t for t in cleaned_targets if t]  # Remove empty strings

    if len(cleaned_targets) < 2:
        logger.warning("Not enough valid targets for link gap analysis")
        return []

    # Limit to max 5 targets (API limitation)
    cleaned_targets = cleaned_targets[:5]

    # Convert array to dict format required by API
    targets_dict = {str(i+1): target for i, target in enumerate(cleaned_targets)}

    try:
        result = await client.post(
            "backlinks/domain_intersection/live",
            [{
                "targets": targets_dict,
                "limit": limit,
                "order_by": ["rank,desc"],  # FIXED: Use simple field name, not "1.rank"
            }]
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "500" in error_msg or "internal server error" in error_msg:
            logger.warning(f"Link gap API returned 500 error - this may be a temporary DataForSEO issue")
            # Try with fewer targets as fallback
            if len(cleaned_targets) > 2:
                logger.info("Retrying link gap with fewer targets...")
                targets_dict_reduced = {str(i+1): target for i, target in enumerate(cleaned_targets[:2])}
                try:
                    result = await client.post(
                        "backlinks/domain_intersection/live",
                        [{
                            "targets": targets_dict_reduced,
                            "limit": limit,
                            "order_by": ["rank,desc"],
                        }]
                    )
                except Exception as retry_e:
                    logger.warning(f"Link gap retry also failed: {retry_e}")
                    return []
            else:
                return []
        else:
            raise

    items = _safe_get_items(result)

    if not items:
        logger.info("Link gap analysis returned no results")
        return []

    # Filter: domains that link to at least one competitor but not to us
    link_gaps = []

    for item in items:
        if not isinstance(item, dict):
            continue

        target_data = item.get("1", {})  # Our domain's data

        # If target_data is empty/null, this domain doesn't link to us = opportunity
        if not target_data or target_data.get("backlinks", 0) == 0:
            competitors_linked = []
            total_competitor_links = 0

            # Check each competitor (positions 2, 3, 4...)
            for i, target in enumerate(cleaned_targets[1:], start=2):
                comp_data = item.get(str(i), {})
                if comp_data and comp_data.get("backlinks", 0) > 0:
                    competitors_linked.append(target)
                    total_competitor_links += comp_data.get("backlinks", 0)

            if competitors_linked:
                link_gaps.append({
                    "domain": item.get("domain", ""),
                    "domain_rank": item.get("rank", 0),
                    "links_to_competitors": total_competitor_links,
                    "competitors_linked": competitors_linked,
                })

    # Sort by number of competitors linked (more = better target)
    link_gaps.sort(key=lambda x: (len(x["competitors_linked"]), x["domain_rank"]), reverse=True)

    logger.info(f"Link gap analysis found {len(link_gaps)} opportunities")
    return link_gaps


async def fetch_link_velocity(
    client,
    domain: str,
    months: int = 6
) -> Dict[str, Any]:
    """
    Fetch link velocity (new/lost backlinks over time).
    Returns monthly data for the past N months.
    """
    # Calculate date range
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")

    result = await client.post(
        "backlinks/timeseries_new_lost_summary/live",
        [{
            "target": domain,
            "date_from": date_from,
            "date_to": date_to,
            "group_range": "month",
        }]
    )

    items = _safe_get_items(result)

    velocity_data = {
        "months": [],
        "total_new": 0,
        "total_lost": 0,
        "net_growth": 0,
        "avg_monthly_new": 0,
        "avg_monthly_lost": 0,
    }

    for item in items:
        month_data = {
            "date": item.get("date", ""),
            "new_backlinks": item.get("new_backlinks", 0),
            "lost_backlinks": item.get("lost_backlinks", 0),
            "new_referring_domains": item.get("new_referring_domains", 0),
            "lost_referring_domains": item.get("lost_referring_domains", 0),
        }
        velocity_data["months"].append(month_data)
        velocity_data["total_new"] += item.get("new_backlinks", 0)
        velocity_data["total_lost"] += item.get("lost_backlinks", 0)

    num_months = len(items) or 1
    velocity_data["net_growth"] = velocity_data["total_new"] - velocity_data["total_lost"]
    velocity_data["avg_monthly_new"] = velocity_data["total_new"] // num_months
    velocity_data["avg_monthly_lost"] = velocity_data["total_lost"] // num_months

    return velocity_data


async def fetch_referring_networks(
    client,
    domain: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Fetch referring network data (IP blocks, subnets).
    Useful for identifying link network patterns.
    """
    result = await client.post(
        "backlinks/referring_networks/live",
        [{
            "target": domain,
            "limit": limit,
            "network_type": "subnet",
            "order_by": ["backlinks,desc"],
        }]
    )

    items = _safe_get_items(result)

    networks = [
        {
            "network": item.get("network_address", ""),
            "backlinks": item.get("backlinks", 0),
            "referring_domains": item.get("referring_domains", 0),
            "referring_ips": item.get("referring_ips", 0),
        }
        for item in items
    ]

    # Summary stats
    total_networks = len(networks)
    unique_subnets = len(set(n["network"] for n in networks))

    return {
        "networks": networks,
        "total_networks": total_networks,
        "unique_subnets": unique_subnets,
        "diversity_score": round(unique_subnets / max(total_networks, 1) * 100, 1),
    }


async def fetch_broken_backlinks(
    client,
    domain: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch broken backlinks pointing to the domain.
    Opportunities for link recovery via redirects or content restoration.
    """
    result = await client.post(
        "backlinks/backlinks/live",
        [{
            "target": domain,
            "limit": limit,
            "mode": "as_is",
            "filters": [["is_broken", "=", True]],
            "order_by": ["domain_from_rank,desc"],
        }]
    )

    items = _safe_get_items(result)

    broken_links = [
        {
            "source_url": item.get("url_from", ""),
            "source_domain": item.get("domain_from", ""),
            "target_url": item.get("url_to", ""),
            "anchor": item.get("anchor", ""),
            "domain_rank": item.get("domain_from_rank", 0),
            "first_seen": item.get("first_seen", ""),
            "last_seen": item.get("last_seen", ""),
        }
        for item in items
    ]

    return broken_links


async def fetch_backlink_history(
    client,
    domain: str,
    months: int = 12
) -> List[Dict[str, Any]]:
    """
    Fetch historical backlink counts.
    Shows backlink growth/decline over time.
    """
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")

    result = await client.post(
        "backlinks/history/live",
        [{
            "target": domain,
            "date_from": date_from,
            "date_to": date_to,
        }]
    )

    items = _safe_get_items(result)

    history = [
        {
            "date": item.get("date", ""),
            "backlinks": item.get("backlinks", 0),
            "referring_domains": item.get("referring_domains", 0),
            "rank": item.get("rank", 0),
        }
        for item in items
    ]

    return history


async def fetch_bulk_referring_domains(
    client,
    domains: List[str]
) -> Dict[str, Any]:
    """
    Fetch referring domain counts for multiple domains at once.
    Useful for competitor comparison.
    """
    result = await client.post(
        "backlinks/bulk_referring_domains/live",
        [{
            "targets": domains[:100],  # Max 100 domains
        }]
    )

    items = _safe_get_items(result, get_first=False)

    domain_data = {}
    for item in items:
        target = item.get("target", "")
        domain_data[target] = {
            "referring_domains": item.get("referring_domains", 0),
            "backlinks": item.get("backlinks", 0),
        }

    return domain_data


async def fetch_backlink_competitors(
    client,
    domain: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Find domains with similar backlink profiles (link competitors).
    Different from keyword competitors - these share similar link sources.
    """
    result = await client.post(
        "backlinks/competitors/live",
        [{
            "target": domain,
            "limit": limit,
        }]
    )

    items = _safe_get_items(result)

    competitors = [
        {
            "domain": item.get("domain", ""),
            "rank": item.get("rank", 0),
            "backlinks": item.get("backlinks", 0),
            "referring_domains": item.get("referring_domains", 0),
            "intersecting_domains": item.get("intersecting_referring_domains", 0),
        }
        for item in items
    ]

    return competitors


# ============================================================================
# TESTING
# ============================================================================

async def test_phase3():
    """Test Phase 3 collection."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Mock client for testing
    class MockClient:
        async def post(self, endpoint, data):
            return {"tasks": [{"result": [{"items": []}]}]}

    client = MockClient()

    result = await collect_competitive_data(
        client=client,
        domain="example.com",
        market="United States",
        language="English",  # FIXED: was "sv"
        competitors=["competitor1.com", "competitor2.com"],
    )

    print(f"Competitor metrics: {len(result['competitor_metrics'])}")
    print(f"Keyword overlaps: {len(result['keyword_overlaps'])}")
    print(f"Backlinks: {len(result['backlinks'])}")
    print(f"Link gap targets: {len(result['link_gap_targets'])}")
    print(f"Dofollow %: {result['dofollow_percentage']}")


if __name__ == "__main__":
    asyncio.run(test_phase3())

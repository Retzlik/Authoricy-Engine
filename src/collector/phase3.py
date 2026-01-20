"""
Phase 3: Competitive Intelligence & Backlinks

This module collects competitive and backlink data:
- Competitor domain metrics
- Keyword overlaps with competitors
- SERP-level competition
- Backlink profile (top links, anchors, referring domains)
- Link gap analysis
- Link velocity (new/lost over time)

Endpoints used:
1. dataforseo_labs/google/domain_rank_overview (×5 competitors)
2. dataforseo_labs/google/domain_intersection (×3 competitors)
3. dataforseo_labs/google/serp_competitors
4. backlinks/backlinks
5. backlinks/anchors
6. backlinks/referring_domains
7. backlinks/domain_intersection (link gap)
8. backlinks/timeseries_new_lost_summary

Total: 14 API calls
Expected time: 6-10 seconds (with parallelization)
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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
        market: Location name (e.g., "Sweden")
        language: Language code (e.g., "sv")
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
            client, top_keywords or [domain], market, language
        )
        if not isinstance(serp_competitors_data, Exception):
            competitors = [c["domain"] for c in serp_competitors_data[:5]]
        else:
            logger.warning(f"Failed to fetch SERP competitors: {serp_competitors_data}")
            competitors = []
    
    competitors = [c for c in competitors if c != domain][:5]  # Top 5, exclude self
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
        
        link_gap_result = await fetch_backlink_domain_intersection(
            client, targets_to_analyze
        )
        
        if not isinstance(link_gap_result, Exception):
            link_gap_targets = link_gap_result
        else:
            logger.warning(f"Failed to analyze link gaps: {link_gap_result}")
    
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
            "language_code": language,
        }]
    )
    
    data = result.get("tasks", [{}])[0].get("result", [{}])[0]
    
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
            "language_code": language,
            "limit": limit,
            "intersections": True,  # Get shared keywords
        }]
    )
    
    task_result = result.get("tasks", [{}])[0].get("result", [{}])[0]
    items = task_result.get("items", [])
    
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
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Identify competitors from SERP data.
    
    Finds domains that rank for similar keywords.
    """
    result = await client.post(
        "dataforseo_labs/google/serp_competitors/live",
        [{
            "keywords": keywords[:200],  # Max 200 keywords
            "location_name": market,
            "language_code": language,
            "limit": limit,
        }]
    )
    
    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
    
    competitors = []
    for item in items:
        competitors.append({
            "domain": item.get("domain", ""),
            "visibility": item.get("visibility", 0),
            "relevant_serp_items": item.get("relevant_serp_items", 0),
            "keywords_count": item.get("keywords_count", 0),
            "avg_position": item.get("avg_position", 0),
        })
    
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
    
    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
    
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
    
    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
    total_backlinks = result.get("tasks", [{}])[0].get("result", [{}])[0].get("total_count", 1)
    
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
    
    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
    
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


async def fetch_backlink_domain_intersection(
    client,
    targets: List[str],
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Find domains linking to competitors but not to us (link gap).
    
    targets[0] = our domain, targets[1:] = competitors
    """
    result = await client.post(
        "backlinks/domain_intersection/live",
        [{
            "targets": targets,
            "limit": limit,
            "order_by": ["1.rank,desc"],  # Sort by domain rank
        }]
    )
    
    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
    
    # Filter: domains that link to at least one competitor but not to us
    # The API returns intersection data - we need to filter
    link_gaps = []
    
    for item in items:
        target_data = item.get("1", {})  # Our domain's data
        
        # If target_data is empty/null, this domain doesn't link to us = opportunity
        if not target_data or target_data.get("backlinks", 0) == 0:
            competitors_linked = []
            total_competitor_links = 0
            
            # Check each competitor (positions 2, 3, 4...)
            for i, target in enumerate(targets[1:], start=2):
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
    
    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
    
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
        market="Sweden",
        language="sv",
        competitors=["competitor1.com", "competitor2.com"],
    )
    
    print(f"Competitor metrics: {len(result['competitor_metrics'])}")
    print(f"Keyword overlaps: {len(result['keyword_overlaps'])}")
    print(f"Backlinks: {len(result['backlinks'])}")
    print(f"Link gap targets: {len(result['link_gap_targets'])}")
    print(f"Dofollow %: {result['dofollow_percentage']}")


if __name__ == "__main__":
    asyncio.run(test_phase3())

"""
Phase 1: Foundation Data Collection

Collects baseline domain data through 11 parallel API calls:
- Domain rank overview
- Historical rank data
- Subdomains
- Top pages (relevant_pages)
- Competitors
- Backlink summary
- Lighthouse audit
- Technologies
- Domain whois overview
- Page intersection
- Categories for domain

Note: domain_pages_summary endpoint removed (404 - does not exist)
Note: bulk_domain_rank_overview endpoint removed (404 - does not exist)
"""

import asyncio
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


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


async def collect_foundation_data(
    client,
    domain: str,
    market: str,
    language: str
) -> Dict[str, Any]:
    """
    Collect Phase 1: Foundation data.
    11 parallel API calls for domain baseline.

    Args:
        client: DataForSEOClient instance
        domain: Target domain (without protocol)
        market: Target market (e.g., "United States", "Sweden")
        language: Language name (e.g., "English", "Swedish") - NOT code!

    Returns:
        Dict containing all foundation data
    """
    logger.info(f"Phase 1: Starting foundation collection for {domain}")

    tasks = [
        fetch_domain_overview(client, domain, market, language),
        fetch_historical_overview(client, domain, market, language),
        fetch_subdomains(client, domain, market, language),
        fetch_relevant_pages(client, domain, market, language),
        fetch_competitors(client, domain, market, language),
        fetch_backlink_summary(client, domain),
        fetch_lighthouse(client, f"https://{domain}"),
        fetch_technologies(client, domain),
        fetch_domain_whois(client, domain),
        fetch_page_intersection(client, domain, market, language),
        fetch_categories_for_domain(client, domain, market, language),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    names = [
        "domain_overview",
        "historical_data",
        "subdomains",
        "top_pages",
        "competitors",
        "backlink_summary",
        "technical_baseline",
        "technologies",
        "whois_data",
        "page_intersection",
        "categories"
    ]

    data = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch {name}: {result}")
            # Use empty dict for single-value items, empty list for arrays
            if name in ["subdomains", "top_pages", "competitors", "technologies", "historical_data", "page_intersection", "categories"]:
                data[name] = []
            else:
                data[name] = {}
        else:
            data[name] = result
            logger.info(f"✓ Collected {name}")

    return data


async def fetch_domain_overview(client, domain: str, market: str, language: str) -> Dict:
    """Fetch current domain rank metrics."""
    try:
        result = await client.post(
            "dataforseo_labs/google/domain_rank_overview/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language
            }]
        )

        # Response structure: result[0].items[0].metrics
        items = _safe_get_items(result)
        if not items:
            return {}

        item = items[0]
        metrics = item.get("metrics") or {}
        organic = metrics.get("organic") or {}
        paid = metrics.get("paid") or {}

        return {
            "organic_keywords": organic.get("count", 0),
            "organic_traffic": organic.get("etv", 0),
            "paid_keywords": paid.get("count", 0),
            "rank": organic.get("pos_1", 0),
            "visibility": organic.get("is_lost", 0),
        }
    except Exception as e:
        logger.error(f"Domain overview failed: {e}")
        return {}


async def fetch_historical_overview(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch historical rank data (12 months)."""
    try:
        result = await client.post(
            "dataforseo_labs/google/historical_rank_overview/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language
            }]
        )

        items = _safe_get_items(result)

        return [
            {
                "date": item.get("date"),
                "organic_keywords": (item.get("metrics") or {}).get("organic", {}).get("count", 0),
                "organic_traffic": (item.get("metrics") or {}).get("organic", {}).get("etv", 0),
            }
            for item in items[-12:]  # Last 12 months
        ]
    except Exception as e:
        logger.error(f"Historical overview failed: {e}")
        return []


async def fetch_subdomains(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch subdomain performance data."""
    try:
        result = await client.post(
            "dataforseo_labs/google/subdomains/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language,
                "limit": 20
            }]
        )

        items = _safe_get_items(result)

        return [
            {
                "subdomain": item.get("target"),
                "organic_keywords": (item.get("metrics") or {}).get("organic", {}).get("count", 0),
                "organic_traffic": (item.get("metrics") or {}).get("organic", {}).get("etv", 0),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Subdomains failed: {e}")
        return []


async def fetch_relevant_pages(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch top performing pages."""
    try:
        result = await client.post(
            "dataforseo_labs/google/relevant_pages/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language,
                "limit": 50
            }]
        )

        items = _safe_get_items(result)

        return [
            {
                "page": item.get("page_address"),
                "organic_keywords": (item.get("metrics") or {}).get("organic", {}).get("count", 0),
                "organic_traffic": (item.get("metrics") or {}).get("organic", {}).get("etv", 0),
                "main_keyword": item.get("main_keyword"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Relevant pages failed: {e}")
        return []


async def fetch_competitors(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch organic competitors."""
    try:
        result = await client.post(
            "dataforseo_labs/google/competitors_domain/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language,
                "limit": 20
            }]
        )

        items = _safe_get_items(result)

        return [
            {
                "domain": item.get("domain"),
                "relevance": item.get("avg_position"),
                "common_keywords": item.get("se_keywords"),
                "organic_traffic": (item.get("metrics") or {}).get("organic", {}).get("etv", 0),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Competitors failed: {e}")
        return []


async def fetch_backlink_summary(client, domain: str) -> Dict:
    """Fetch backlink overview.

    Note: backlinks/summary returns result[0] directly with properties,
    not result[0].items - this is different from other endpoints.
    """
    try:
        result = await client.post(
            "backlinks/summary/live",
            [{"target": domain}]
        )

        # Backlinks summary returns properties directly in result[0]
        item = _safe_get_first_result(result)

        return {
            "total_backlinks": item.get("backlinks", 0),
            "referring_domains": item.get("referring_domains", 0),
            "referring_ips": item.get("referring_ips", 0),
            "dofollow_backlinks": item.get("backlinks_nofollow", 0),
            "domain_rank": item.get("rank", 0),
        }
    except Exception as e:
        logger.error(f"Backlink summary failed: {e}")
        return {}


async def fetch_lighthouse(client, url: str) -> Dict:
    """Fetch Lighthouse performance metrics.

    Note: Lighthouse returns result[0] directly with categories, not items array.
    """
    try:
        result = await client.post(
            "on_page/lighthouse/live/json",
            [{
                "url": url,
                "for_mobile": True
            }]
        )

        item = _safe_get_first_result(result)
        categories = item.get("categories") or {}

        return {
            "performance_score": (categories.get("performance") or {}).get("score", 0),
            "accessibility_score": (categories.get("accessibility") or {}).get("score", 0),
            "best_practices_score": (categories.get("best_practices") or {}).get("score", 0),
            "seo_score": (categories.get("seo") or {}).get("score", 0),
        }
    except Exception as e:
        logger.error(f"Lighthouse failed: {e}")
        return {}


async def fetch_technologies(client, domain: str) -> List[Dict]:
    """Fetch detected technologies.

    Note: Technologies endpoint returns result[0].technologies array,
    not result[0].items.
    """
    try:
        result = await client.post(
            "domain_analytics/technologies/domain_technologies/live",
            [{"target": domain}]
        )

        first_result = _safe_get_first_result(result)
        technologies_data = first_result.get("technologies")

        # Ensure we have a list before processing
        if not isinstance(technologies_data, list):
            logger.warning(f"Technologies data is not a list: {type(technologies_data)}")
            return []

        # Safely slice and process
        items = technologies_data[:20] if len(technologies_data) > 20 else technologies_data

        return [
            {
                "name": item.get("name") if isinstance(item, dict) else str(item),
                "category": item.get("category") if isinstance(item, dict) else "unknown",
            }
            for item in items
            if item is not None
        ]
    except Exception as e:
        logger.error(f"Technologies failed: {e}")
        return []


async def fetch_domain_whois(client, domain: str) -> Dict:
    """Fetch domain WHOIS data including registration and expiry info.

    Note: WHOIS returns result[0] directly with properties.
    """
    try:
        result = await client.post(
            "domain_analytics/whois/overview/live",
            [{"target": domain}]
        )

        item = _safe_get_first_result(result)

        return {
            "domain": item.get("domain", domain),
            "create_date": item.get("create_date", ""),
            "update_date": item.get("update_date", ""),
            "expiry_date": item.get("expiry_date", ""),
            "registrar": item.get("registrar", ""),
            "registered": item.get("registered", False),
            "domain_age_days": (item.get("metrics") or {}).get("age_days", 0),
        }
    except Exception as e:
        logger.error(f"WHOIS fetch failed: {e}")
        return {}


# REMOVED: fetch_domain_pages_summary - endpoint returns 404 (does not exist)


async def fetch_page_intersection(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch page intersection data showing which pages compete for same keywords."""
    try:
        result = await client.post(
            "dataforseo_labs/google/page_intersection/live",
            [{
                "pages": {
                    "1": f"https://{domain}/"
                },
                "location_name": market,
                "language_name": language,
                "limit": 50
            }]
        )

        items = _safe_get_items(result)

        return [
            {
                "keyword": (item.get("keyword_data") or {}).get("keyword", ""),
                "search_volume": (item.get("keyword_data") or {}).get("keyword_info", {}).get("search_volume", 0),
                "intersections": item.get("intersections") or []
            }
            for item in items[:50]
        ]
    except Exception as e:
        logger.error(f"Page intersection failed: {e}")
        return []


async def fetch_categories_for_domain(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch top categories/verticals the domain ranks for."""
    try:
        result = await client.post(
            "dataforseo_labs/google/categories_for_domain/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language,
                "limit": 20
            }]
        )

        items = _safe_get_items(result)

        return [
            {
                "category": item.get("category", ""),
                "category_code": item.get("category_code", 0),
                "keywords_count": (item.get("metrics") or {}).get("organic", {}).get("count", 0),
                "traffic_share": (item.get("metrics") or {}).get("organic", {}).get("etv", 0),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Categories for domain failed: {e}")
        return []


# REMOVED: fetch_bulk_domain_rank - endpoint returns 404 (does not exist)

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

from src.collector.client import safe_get_result
from src.utils.domain_filter import is_excluded_domain

logger = logging.getLogger(__name__)


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
                "language_name": language  # FIXED: was language_code
            }]
        )

        # DEBUG: Log the full response structure to diagnose data issues
        logger.info(f"Domain overview API response status: {result.get('status_code')}")

        # Properly check for empty/error results
        tasks = result.get("tasks", [])
        if not tasks:
            logger.warning(f"Domain overview: No tasks returned for {domain}")
            return {}

        task = tasks[0]
        task_status = task.get("status_code")
        task_message = task.get("status_message")
        logger.info(f"Domain overview task status: {task_status} - {task_message}")

        task_result = task.get("result")

        # Check if result is None, empty list, or error
        if not task_result:
            logger.warning(f"Domain overview: No result data for {domain} in {market}/{language}")
            return {}

        # Log what we actually received
        logger.info(f"Domain overview: Got {len(task_result)} result items for {domain}")

        item = task_result[0] if task_result else {}
        metrics = item.get("metrics")

        if not metrics:
            # Log what keys ARE present in the item
            logger.warning(f"Domain overview: No 'metrics' key for {domain}. Available keys: {list(item.keys())}")
            return {}

        organic = metrics.get("organic", {})
        logger.info(f"Domain overview metrics for {domain}: count={organic.get('count')}, etv={organic.get('etv')}")

        return {
            "organic_keywords": organic.get("count", 0),
            "organic_traffic": organic.get("etv", 0),
            "paid_keywords": metrics.get("paid", {}).get("count", 0),
            "rank": organic.get("pos_1", 0),
            "visibility": organic.get("is_lost", 0),
        }
    except Exception as e:
        logger.error(f"Domain overview failed for {domain}: {e}")
        return {}


async def fetch_historical_overview(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch historical rank data (12 months)."""
    try:
        result = await client.post(
            "dataforseo_labs/google/historical_rank_overview/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language  # FIXED: was language_code
            }]
        )

        items = safe_get_result(result, get_items=True)

        return [
            {
                "date": item.get("date"),
                "organic_keywords": (item.get("metrics") or {}).get("organic", {}).get("count") or 0,
                "organic_traffic": (item.get("metrics") or {}).get("organic", {}).get("etv") or 0,
            }
            for item in (items or [])[-12:]  # Last 12 months
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
                "language_name": language,  # FIXED: was language_code
                "limit": 20
            }]
        )

        items = safe_get_result(result, get_items=True)

        return [
            {
                "subdomain": item.get("target"),
                "organic_keywords": (item.get("metrics") or {}).get("organic", {}).get("count") or 0,
                "organic_traffic": (item.get("metrics") or {}).get("organic", {}).get("etv") or 0,
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
                "language_name": language,  # FIXED: was language_code
                "limit": 50
            }]
        )

        items = safe_get_result(result, get_items=True)

        return [
            {
                "page": item.get("page_address"),
                "organic_keywords": (item.get("metrics") or {}).get("organic", {}).get("count") or 0,
                "organic_traffic": (item.get("metrics") or {}).get("organic", {}).get("etv") or 0,
                "main_keyword": item.get("main_keyword"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Relevant pages failed: {e}")
        return []


async def fetch_competitors(client, domain: str, market: str, language: str) -> List[Dict]:
    """Fetch organic competitors with platform filtering."""
    try:
        result = await client.post(
            "dataforseo_labs/google/competitors_domain/live",
            [{
                "target": domain,
                "location_name": market,
                "language_name": language,  # FIXED: was language_code
                "limit": 50  # Fetch more to filter
            }]
        )

        # Safe parsing - handle empty lists and None values
        tasks = result.get("tasks") or [{}]
        task = tasks[0] if tasks else {}
        task_result = task.get("result") or [{}]
        first_result = task_result[0] if task_result else {}
        items = first_result.get("items") or []

        competitors = []
        for item in items:
            comp_domain = item.get("domain", "")
            if is_excluded_domain(comp_domain):
                continue
            competitors.append({
                "domain": comp_domain,
                "relevance": item.get("avg_position"),
                "common_keywords": item.get("se_keywords"),
                "organic_traffic": item.get("metrics", {}).get("organic", {}).get("etv", 0),
            })
            if len(competitors) >= 20:
                break

        return competitors
    except Exception as e:
        logger.error(f"Competitors failed: {e}")
        return []


async def fetch_backlink_summary(client, domain: str) -> Dict:
    """Fetch backlink overview."""
    try:
        result = await client.post(
            "backlinks/summary/live",
            [{"target": domain}]
        )

        item = safe_get_result(result, get_items=False)

        return {
            "total_backlinks": item.get("backlinks") or 0,
            "referring_domains": item.get("referring_domains") or 0,
            "referring_ips": item.get("referring_ips") or 0,
            "dofollow_backlinks": item.get("backlinks_nofollow") or 0,
            "domain_rank": item.get("rank") or 0,
        }
    except Exception as e:
        logger.error(f"Backlink summary failed: {e}")
        return {}


async def fetch_lighthouse(client, url: str) -> Dict:
    """Fetch Lighthouse performance metrics."""
    try:
        result = await client.post(
            "on_page/lighthouse/live/json",
            [{
                "url": url,
                "for_mobile": True
            }]
        )

        item = safe_get_result(result, get_items=False)
        categories = item.get("categories") or {}

        return {
            "performance_score": categories.get("performance", {}).get("score", 0),
            "accessibility_score": categories.get("accessibility", {}).get("score", 0),
            "best_practices_score": categories.get("best_practices", {}).get("score", 0),
            "seo_score": categories.get("seo", {}).get("score", 0),
        }
    except Exception as e:
        logger.error(f"Lighthouse failed: {e}")
        return {}


async def fetch_technologies(client, domain: str) -> List[Dict]:
    """Fetch detected technologies."""
    try:
        result = await client.post(
            "domain_analytics/technologies/domain_technologies/live",
            [{"target": domain}]
        )

        # Safe parsing - handle None values and unexpected types
        tasks = result.get("tasks") or [{}]
        task_result = tasks[0].get("result") if tasks else None
        items = []
        if task_result and isinstance(task_result, list) and len(task_result) > 0:
            tech_data = task_result[0].get("technologies") if isinstance(task_result[0], dict) else None
            if isinstance(tech_data, list):
                items = tech_data

        # Safely iterate with type checking
        output = []
        for item in items[:20]:  # Limit to top 20
            if isinstance(item, dict):
                output.append({
                    "name": item.get("name"),
                    "category": item.get("category"),
                })
        return output
    except Exception as e:
        logger.error(f"Technologies failed: {e}")
        return []


async def fetch_domain_whois(client, domain: str) -> Dict:
    """Fetch domain WHOIS data including registration and expiry info."""
    try:
        result = await client.post(
            "domain_analytics/whois/overview/live",
            [{"target": domain}]
        )

        item = safe_get_result(result, get_items=False)

        return {
            "domain": item.get("domain", domain),
            "create_date": item.get("create_date", ""),
            "update_date": item.get("update_date", ""),
            "expiry_date": item.get("expiry_date", ""),
            "registrar": item.get("registrar", ""),
            "registered": item.get("registered", False),
            "domain_age_days": (item.get("metrics") or {}).get("age_days") or 0,
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
                "language_name": language,  # FIXED: was language_code
                "limit": 50
            }]
        )

        items = safe_get_result(result, get_items=True)

        return [
            {
                "keyword": (item.get("keyword_data") or {}).get("keyword", ""),
                "search_volume": ((item.get("keyword_data") or {}).get("keyword_info") or {}).get("search_volume") or 0,
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
                "language_name": language,  # FIXED: was language_code
                "limit": 20
            }]
        )

        items = safe_get_result(result, get_items=True)

        return [
            {
                "category": item.get("category", ""),
                "category_code": item.get("category_code") or 0,
                "keywords_count": (item.get("metrics") or {}).get("organic", {}).get("count") or 0,
                "traffic_share": (item.get("metrics") or {}).get("organic", {}).get("etv") or 0,
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Categories for domain failed: {e}")
        return []


# REMOVED: fetch_bulk_domain_rank - endpoint returns 404 (does not exist)

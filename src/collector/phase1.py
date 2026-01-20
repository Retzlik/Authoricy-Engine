"""
Phase 1: Foundation Data Collection

Collects baseline domain data through 8 parallel API calls:
- Domain rank overview
- Historical rank data
- Subdomains
- Top pages
- Competitors
- Backlink summary
- Lighthouse audit
- Technologies
"""

import asyncio
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


async def collect_foundation_data(
    client,
    domain: str,
    market: str,
    language: str
) -> Dict[str, Any]:
    """
    Collect Phase 1: Foundation data.
    
    8 parallel API calls for domain baseline.
    
    Args:
        client: DataForSEOClient instance
        domain: Target domain (without protocol)
        market: Target market (e.g., "Sweden")
        language: Language code (e.g., "sv")
        
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
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    names = [
        "domain_overview", "historical_data", "subdomains", "top_pages",
        "competitors", "backlink_summary", "technical_baseline", "technologies"
    ]
    
    data = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch {name}: {result}")
            # Use empty dict for single-value items, empty list for arrays
            if name in ["subdomains", "top_pages", "competitors", "technologies", "historical_data"]:
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
                "language_code": language
            }]
        )
        
        items = result.get("tasks", [{}])[0].get("result", [{}])
        if not items:
            return {}
        
        item = items[0]
        return {
            "organic_keywords": item.get("metrics", {}).get("organic", {}).get("count", 0),
            "organic_traffic": item.get("metrics", {}).get("organic", {}).get("etv", 0),
            "paid_keywords": item.get("metrics", {}).get("paid", {}).get("count", 0),
            "rank": item.get("metrics", {}).get("organic", {}).get("pos_1", 0),
            "visibility": item.get("metrics", {}).get("organic", {}).get("is_lost", 0),
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
                "language_code": language
            }]
        )
        
        items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
        
        return [
            {
                "date": item.get("date"),
                "organic_keywords": item.get("metrics", {}).get("organic", {}).get("count", 0),
                "organic_traffic": item.get("metrics", {}).get("organic", {}).get("etv", 0),
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
                "language_code": language,
                "limit": 20
            }]
        )
        
        items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
        
        return [
            {
                "subdomain": item.get("target"),
                "organic_keywords": item.get("metrics", {}).get("organic", {}).get("count", 0),
                "organic_traffic": item.get("metrics", {}).get("organic", {}).get("etv", 0),
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
                "language_code": language,
                "limit": 50
            }]
        )
        
        items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
        
        return [
            {
                "page": item.get("page_address"),
                "organic_keywords": item.get("metrics", {}).get("organic", {}).get("count", 0),
                "organic_traffic": item.get("metrics", {}).get("organic", {}).get("etv", 0),
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
                "language_code": language,
                "limit": 20
            }]
        )
        
        items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
        
        return [
            {
                "domain": item.get("domain"),
                "relevance": item.get("avg_position"),
                "common_keywords": item.get("se_keywords"),
                "organic_traffic": item.get("metrics", {}).get("organic", {}).get("etv", 0),
            }
            for item in items
        ]
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
        
        item = result.get("tasks", [{}])[0].get("result", [{}])[0]
        
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
    """Fetch Lighthouse performance metrics."""
    try:
        result = await client.post(
            "on_page/lighthouse/live/json",
            [{
                "url": url,
                "for_mobile": True
            }]
        )
        
        item = result.get("tasks", [{}])[0].get("result", [{}])[0]
        categories = item.get("categories", {})
        
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
        
        items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("technologies", [])
        
        return [
            {
                "name": item.get("name"),
                "category": item.get("category"),
            }
            for item in items[:20]  # Limit to top 20
        ]
    except Exception as e:
        logger.error(f"Technologies failed: {e}")
        return []

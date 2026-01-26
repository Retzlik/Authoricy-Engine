"""
Phase 4: AI Visibility & Technical Analysis

This module collects AI-era and technical SEO data:
- AI keyword visibility metrics
- LLM mentions (ChatGPT, Google AI)
- Brand mentions and sentiment analysis
- Google Trends data
- Technical page audits
- Schema markup analysis
- Live SERP AI overview detection
- Search volume data
- Content ratings

Note: All endpoints use language_name (e.g., "English") not language_code (e.g., "en")
Note: LLM mentions endpoint requires target as array of objects: [{"domain": "..."}]
Note: on_page/microdata and on_page/duplicate_content are task-based (not instant)
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from src.collector.client import safe_get_result

logger = logging.getLogger(__name__)


def _safe_get_gather_result(results: list, idx: int, default):
    """Safely extract a result from asyncio.gather with return_exceptions=True."""
    if idx >= len(results):
        return default
    val = results[idx]
    return default if isinstance(val, Exception) else val


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AIVisibility:
    """AI visibility metrics for a keyword."""
    keyword: str
    ai_search_volume: int  # Volume in AI-context searches
    traditional_volume: int
    ai_share: float  # % of searches in AI context
    mentioned_in_chatgpt: bool
    mentioned_in_google_ai: bool


@dataclass
class BrandMention:
    """A brand mention across the web."""
    url: str
    domain: str
    title: str
    snippet: str
    sentiment: str  # positive, negative, neutral
    date: str
    domain_rank: int


@dataclass
class TechnicalAudit:
    """Technical audit for a page."""
    url: str
    title: str
    load_time: float  # seconds
    page_size: int  # bytes
    word_count: int
    h1_count: int
    h2_count: int
    internal_links: int
    external_links: int
    images_count: int
    images_without_alt: int
    meta_title: str
    meta_description: str
    canonical_url: str
    is_mobile_friendly: bool
    core_web_vitals: Dict[str, Any]
    issues: List[str]


@dataclass
class TrendData:
    """Google Trends data for keywords."""
    keyword: str
    trend_values: List[Dict[str, Any]]  # {date, value}
    trend_direction: str  # rising, falling, stable
    avg_interest: float


@dataclass
class Phase4Data:
    """Complete Phase 4 data container."""
    ai_visibility: List[AIVisibility] = field(default_factory=list)
    llm_mentions: Dict[str, Any] = field(default_factory=dict)
    brand_mentions: List[BrandMention] = field(default_factory=list)
    sentiment_summary: Dict[str, Any] = field(default_factory=dict)
    trend_data: List[TrendData] = field(default_factory=list)
    technical_audits: List[TechnicalAudit] = field(default_factory=list)

    # Aggregated metrics
    ai_visibility_score: float = 0
    brand_sentiment_score: float = 0
    technical_health_score: float = 0


# ============================================================================
# MAIN COLLECTION FUNCTION
# ============================================================================

async def collect_ai_technical_data(
    client,  # DataForSEOClient
    domain: str,
    brand_name: str,
    market: str,
    language: str,
    top_keywords: Optional[List[str]] = None,
    top_pages: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Collect Phase 4: AI Visibility & Technical Analysis data.

    Flow:
    1. Fetch AI keyword metrics for top keywords
    2. Check LLM visibility (ChatGPT + Google AI)
    3. Analyze brand mentions and sentiment
    4. Get Google Trends data
    5. Run technical audits on top pages

    Args:
        client: DataForSEO API client
        domain: Target domain
        brand_name: Brand name for mention tracking
        market: Location name (e.g., "United States", "Sweden")
        language: Language name (e.g., "English", "Swedish") - NOT code!
        top_keywords: Keywords to analyze (from Phase 2)
        top_pages: URLs to audit (from Phase 1)

    Returns:
        Dictionary with all Phase 4 data
    """

    logger.info(f"Phase 4: Starting AI & technical analysis for {domain}")

    # Default values if not provided
    if not top_keywords:
        top_keywords = [domain.replace(".", " ")]  # Use domain as fallback
    if not top_pages:
        top_pages = [f"https://{domain}/"]  # Use homepage as fallback

    # -------------------------------------------------------------------------
    # Step 1: AI keyword visibility (parallel)
    # -------------------------------------------------------------------------

    logger.info("Phase 4.1: Analyzing AI keyword visibility...")

    ai_tasks = [
        fetch_ai_keyword_data(client, top_keywords[:50], market, language),
        fetch_llm_mentions(client, domain, top_keywords[:20], "chat_gpt"),
        fetch_llm_mentions(client, domain, top_keywords[:20], "google"),
    ]

    ai_results = await asyncio.gather(*ai_tasks, return_exceptions=True)

    # Safe extraction with length checks
    ai_keyword_data = _safe_get_gather_result(ai_results, 0, [])
    chatgpt_mentions = _safe_get_gather_result(ai_results, 1, {})
    google_ai_mentions = _safe_get_gather_result(ai_results, 2, {})

    # Log any exceptions
    for idx, name in enumerate(["AI keyword data", "ChatGPT mentions", "Google AI mentions"]):
        if idx < len(ai_results) and isinstance(ai_results[idx], Exception):
            logger.warning(f"Failed to fetch {name}: {ai_results[idx]}")

    logger.info(f"Phase 4.1: Analyzed {len(ai_keyword_data)} keywords for AI visibility")

    # -------------------------------------------------------------------------
    # Step 2: Brand mentions and sentiment (parallel)
    # -------------------------------------------------------------------------

    logger.info("Phase 4.2: Analyzing brand mentions and sentiment...")

    brand_tasks = [
        fetch_brand_mentions(client, brand_name, limit=50),
        fetch_sentiment_summary(client, brand_name),
    ]

    brand_results = await asyncio.gather(*brand_tasks, return_exceptions=True)

    # Safe extraction with length checks
    brand_mentions = _safe_get_gather_result(brand_results, 0, [])
    sentiment_summary = _safe_get_gather_result(brand_results, 1, {})

    # Log any exceptions
    for idx, name in enumerate(["brand mentions", "sentiment"]):
        if idx < len(brand_results) and isinstance(brand_results[idx], Exception):
            logger.warning(f"Failed to fetch {name}: {brand_results[idx]}")

    logger.info(f"Phase 4.2: Found {len(brand_mentions)} brand mentions")

    # -------------------------------------------------------------------------
    # Step 3: Google Trends
    # -------------------------------------------------------------------------

    logger.info("Phase 4.3: Fetching trend data...")

    # Analyze top 5 keywords for trends
    trend_keywords = top_keywords[:5]
    trend_data = await fetch_trends_data(client, trend_keywords, market)

    if isinstance(trend_data, Exception):
        logger.warning(f"Failed to fetch trends: {trend_data}")
        trend_data = []

    logger.info(f"Phase 4.3: Got trends for {len(trend_data)} keywords")

    # -------------------------------------------------------------------------
    # Step 4: Technical audits (parallel for top 3 pages)
    # -------------------------------------------------------------------------

    logger.info("Phase 4.4: Running technical audits...")

    pages_to_audit = top_pages[:3]

    audit_tasks = [
        fetch_technical_audit(client, url, language)
        for url in pages_to_audit
    ]

    audit_results = await asyncio.gather(*audit_tasks, return_exceptions=True)

    technical_audits = []
    for url, result in zip(pages_to_audit, audit_results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to audit {url}: {result}")
        else:
            technical_audits.append(result)

    logger.info(f"Phase 4.4: Completed {len(technical_audits)} technical audits")

    # -------------------------------------------------------------------------
    # Step 5: Additional AI & Technical Intelligence (parallel)
    # -------------------------------------------------------------------------

    logger.info("Phase 4.5: Fetching additional AI & technical data...")

    additional_tasks = [
        fetch_live_serp_ai_overview(client, top_keywords[:5], market, language),
        fetch_content_ratings(client, brand_name),
        fetch_search_volume_live(client, top_keywords[:20], market, language),
    ]

    additional_results = await asyncio.gather(*additional_tasks, return_exceptions=True)

    # Safe extraction with length checks
    live_serp_data = _safe_get_gather_result(additional_results, 0, [])
    content_ratings = _safe_get_gather_result(additional_results, 1, {})
    search_volume_live = _safe_get_gather_result(additional_results, 2, [])

    # Log any exceptions
    for idx, name in enumerate(["live_serp", "content_ratings", "search_volume"]):
        if idx < len(additional_results) and isinstance(additional_results[idx], Exception):
            logger.warning(f"Failed to fetch {name}: {additional_results[idx]}")

    # -------------------------------------------------------------------------
    # Step 6: Calculate aggregated scores
    # -------------------------------------------------------------------------

    # AI visibility score (0-100)
    ai_visibility_score = calculate_ai_visibility_score(
        ai_keyword_data, chatgpt_mentions, google_ai_mentions
    )

    # Brand sentiment score (-100 to +100)
    brand_sentiment_score = calculate_sentiment_score(sentiment_summary)

    # Technical health score (0-100)
    technical_health_score = calculate_technical_score(technical_audits)

    # -------------------------------------------------------------------------
    # Return complete Phase 4 data
    # -------------------------------------------------------------------------

    # Build ai_visibility dict for reporter compatibility
    total_mentions = len(brand_mentions)
    chatgpt_mention_count = len(chatgpt_mentions.get("items", []) if isinstance(chatgpt_mentions, dict) else [])
    google_ai_mention_count = len(google_ai_mentions.get("items", []) if isinstance(google_ai_mentions, dict) else [])

    return {
        "ai_keyword_data": ai_keyword_data,
        "llm_mentions": {
            "chatgpt": chatgpt_mentions,
            "google_ai": google_ai_mentions,
        },
        # ai_visibility dict for reporter compatibility
        "ai_visibility": {
            "visibility_score": ai_visibility_score,
            "ai_visibility_score": ai_visibility_score,
            "mention_count": total_mentions,
            "chatgpt_mentions": chatgpt_mention_count,
            "google_ai_mentions": google_ai_mention_count,
            "brand_mentions_count": len(brand_mentions),
            "sentiment_score": brand_sentiment_score,
        },
        "brand_mentions": brand_mentions,
        "sentiment_summary": sentiment_summary,
        "trend_data": trend_data,
        "technical_audits": [
            {
                "url": a.url,
                "title": a.title,
                "load_time": a.load_time,
                "page_size": a.page_size,
                "word_count": a.word_count,
                "h1_count": a.h1_count,
                "h2_count": a.h2_count,
                "internal_links": a.internal_links,
                "external_links": a.external_links,
                "images_count": a.images_count,
                "images_without_alt": a.images_without_alt,
                "meta_title": a.meta_title,
                "meta_description": a.meta_description,
                "canonical_url": a.canonical_url,
                "is_mobile_friendly": a.is_mobile_friendly,
                "core_web_vitals": a.core_web_vitals,
                "issues": a.issues,
            }
            for a in technical_audits
        ],
        "live_serp_data": live_serp_data,
        "content_ratings": content_ratings,
        "search_volume_live": search_volume_live,
        "ai_visibility_score": ai_visibility_score,
        "brand_sentiment_score": brand_sentiment_score,
        "technical_health_score": technical_health_score,
    }


# ============================================================================
# INDIVIDUAL ENDPOINT FUNCTIONS
# ============================================================================

async def fetch_ai_keyword_data(
    client,
    keywords: List[str],
    market: str,
    language: str
) -> List[Dict[str, Any]]:
    """
    Fetch AI-era keyword metrics.

    Uses keyword overview to get search volume and AI-related metrics.
    """
    result = await client.post(
        "dataforseo_labs/google/keyword_overview/live",
        [{
            "keywords": keywords,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
        }]
    )

    # Safe parsing
    tasks = result.get("tasks") or [{}]
    items = tasks[0].get("result") or []

    keyword_data = []
    for item in items or []:
        kw_info = item.get("keyword_info") or {}

        keyword_data.append({
            "keyword": item.get("keyword", ""),
            "search_volume": kw_info.get("search_volume") or 0,
            "cpc": kw_info.get("cpc") or 0,
            "competition": kw_info.get("competition") or 0,
            "competition_level": kw_info.get("competition_level", ""),
            # AI-specific metrics (when available)
            "monthly_searches": kw_info.get("monthly_searches") or [],
        })

    return keyword_data


async def fetch_llm_mentions(
    client,
    domain: str,
    keywords: List[str],
    platform: str  # "chat_gpt" or "google"
) -> Dict[str, Any]:
    """
    Check if domain is mentioned in LLM responses.

    Uses AI Optimization LLM Mentions API.

    FIXED: target must be array of objects [{"domain": "..."}], not string
    """
    try:
        result = await client.post(
            "ai_optimization/llm_mentions/search/live",
            [{
                "target": [{"domain": domain}],  # FIXED: was just domain string
                "platform": platform,
                "limit": 50,
            }]
        )

        # Safe parsing - handle None values
        tasks = result.get("tasks") or [{}]
        task_result_list = tasks[0].get("result") if tasks else None
        task_result = {}
        if task_result_list and len(task_result_list) > 0:
            task_result = task_result_list[0] or {}

        items = task_result.get("items") or []
        return {
            "platform": platform,
            "total_mentions": task_result.get("total_count", 0),
            "items": items[:20],  # Top 20
            "metrics": task_result.get("metrics", {}),
        }
    except Exception as e:
        logger.warning(f"LLM mentions not available for {platform}: {e}")
        return {
            "platform": platform,
            "total_mentions": 0,
            "items": [],
            "metrics": {},
            "error": str(e),
        }


async def fetch_brand_mentions(
    client,
    brand_name: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Find brand mentions across the web.

    Uses Content Analysis API.
    """
    result = await client.post(
        "content_analysis/search/live",
        [{
            "keyword": f'"{brand_name}"',  # Exact match
            "limit": limit,
            "search_mode": "one_per_domain",
        }]
    )

    items = safe_get_result(result, get_items=True)

    mentions = []
    for item in items:
        content_info = item.get("content_info") or {}
        sentiment = content_info.get("sentiment_connotations") or {}

        # Determine overall sentiment
        positive = sentiment.get("positive", 0)
        negative = sentiment.get("negative", 0)

        if positive > negative:
            sentiment_label = "positive"
        elif negative > positive:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        mentions.append({
            "url": item.get("url", ""),
            "domain": item.get("domain", ""),
            "title": content_info.get("title", ""),
            "snippet": content_info.get("snippet", "")[:200],
            "sentiment": sentiment_label,
            "date": item.get("date", ""),
            "domain_rank": item.get("domain_rank", 0),
        })

    return mentions


async def fetch_sentiment_summary(
    client,
    keyword: str
) -> Dict[str, Any]:
    """
    Get sentiment summary for a keyword/brand.

    Uses Content Analysis Summary API.
    """
    result = await client.post(
        "content_analysis/summary/live",
        [{
            "keyword": keyword,
        }]
    )

    task_result = safe_get_result(result, get_items=False)

    sentiment_data = task_result.get("sentiment_connotations") or {}
    connotation_types = task_result.get("connotation_types") or {}

    return {
        "total_mentions": task_result.get("total_count") or 0,
        "sentiment_distribution": {
            "positive": connotation_types.get("positive") or 0,
            "negative": connotation_types.get("negative") or 0,
            "neutral": connotation_types.get("neutral") or 0,
        },
        "sentiment_scores": {
            "joy": sentiment_data.get("joy") or 0,
            "sadness": sentiment_data.get("sadness") or 0,
            "anger": sentiment_data.get("anger") or 0,
            "fear": sentiment_data.get("fear") or 0,
            "surprise": sentiment_data.get("surprise") or 0,
            "trust": sentiment_data.get("trust") or 0,
        },
        "top_domains": (task_result.get("top_domains") or [])[:10],
    }


async def fetch_trends_data(
    client,
    keywords: List[str],
    market: str
) -> List[Dict[str, Any]]:
    """
    Fetch Google Trends data for keywords.

    Returns trend data for past 12 months.
    """
    result = await client.post(
        "keywords_data/google_trends/explore/live",
        [{
            "keywords": keywords[:5],  # Max 5 per request
            "location_name": market,
            "time_range": "past_12_months",
            "item_types": ["google_trends_graph"],
        }]
    )

    # Safe parsing
    tasks = result.get("tasks") or [{}]
    items = tasks[0].get("result") or []

    trend_data = []

    for item in items or []:
        if item.get("type") == "google_trends_graph":
            for line in item.get("lines") or []:
                keyword = line.get("keyword", "")
                values = line.get("values") or []

                if values:
                    # Calculate trend direction
                    first_half = sum(v.get("value", 0) for v in values[:len(values)//2])
                    second_half = sum(v.get("value", 0) for v in values[len(values)//2:])

                    if second_half > first_half * 1.1:
                        direction = "rising"
                    elif second_half < first_half * 0.9:
                        direction = "falling"
                    else:
                        direction = "stable"

                    avg_interest = sum(v.get("value", 0) for v in values) / len(values)

                    trend_data.append({
                        "keyword": keyword,
                        "values": values,
                        "direction": direction,
                        "avg_interest": round(avg_interest, 1),
                    })

    return trend_data


async def fetch_live_serp_ai_overview(
    client,
    keywords: List[str],
    market: str,
    language: str
) -> List[Dict[str, Any]]:
    """
    Fetch live SERP data to detect AI Overview presence.

    Checks if keywords trigger AI Overview in search results.
    """
    serp_results = []

    for keyword in keywords[:5]:  # Limit to 5 to control costs
        try:
            result = await client.post(
                "serp/google/organic/live/regular",
                [{
                    "keyword": keyword,
                    "location_name": market,
                    "language_name": language,  # FIXED: was language_code
                    "device": "desktop",
                    "depth": 10,
                }]
            )

            task_result = safe_get_result(result, get_items=False)
            items = task_result.get("items") or []

            # Check for AI overview presence
            has_ai_overview = any(
                item.get("type") in ["ai_overview", "featured_snippet", "knowledge_graph"]
                for item in items
            )

            # Get AI overview content if present
            ai_overview_content = None
            for item in items:
                if item.get("type") == "ai_overview":
                    ai_overview_content = item.get("text", "")[:500]
                    break

            # Extract organic results with titles for format analysis
            organic_results = []
            for item in items:
                if item.get("type") == "organic":
                    organic_results.append({
                        "position": item.get("rank_group"),
                        "url": item.get("url", ""),
                        "domain": item.get("domain", ""),
                        "title": item.get("title", ""),  # SERP title for format analysis
                        "description": item.get("description", ""),
                    })

            serp_results.append({
                "keyword": keyword,
                "has_ai_overview": has_ai_overview,
                "ai_overview_content": ai_overview_content,
                "serp_features": [item.get("type") for item in items[:20]],
                "organic_results_count": len(organic_results),
                "organic_results": organic_results[:10],  # Top 10 organic results with titles
            })
        except Exception as e:
            logger.warning(f"Failed to fetch live SERP for '{keyword}': {e}")
            serp_results.append({
                "keyword": keyword,
                "has_ai_overview": False,
                "error": str(e),
            })

    return serp_results


# REMOVED: fetch_schema_markup - on_page/microdata is task-based, not instant
# REMOVED: fetch_duplicate_content - on_page/duplicate_content is task-based, not instant


async def fetch_content_ratings(
    client,
    keyword: str
) -> Dict[str, Any]:
    """
    Fetch content rating distribution for a keyword/brand.

    Shows how content about the topic is rated across the web.
    """
    try:
        result = await client.post(
            "content_analysis/rating_distribution/live",
            [{
                "keyword": keyword,
            }]
        )

        task_result = safe_get_result(result, get_items=False)

        return {
            "total_count": task_result.get("total_count") or 0,
            "rating_distribution": task_result.get("rating_distribution") or {},
            "average_rating": (task_result.get("metrics") or {}).get("average_rating") or 0,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch content ratings: {e}")
        return {"error": str(e)}


async def fetch_search_volume_live(
    client,
    keywords: List[str],
    market: str,
    language: str
) -> List[Dict[str, Any]]:
    """
    Fetch live search volume data (most current).

    More accurate than cached data for trending topics.
    """
    try:
        result = await client.post(
            "keywords_data/google/search_volume/live",
            [{
                "keywords": keywords[:100],  # Max 100
                "location_name": market,
                "language_name": language,  # FIXED: was language_code
            }]
        )

        # Safe parsing
        tasks = result.get("tasks") or [{}]
        items = tasks[0].get("result") or []

        volume_data = []
        for item in items or []:
            volume_data.append({
                "keyword": item.get("keyword", ""),
                "search_volume": item.get("search_volume") or 0,
                "competition": item.get("competition") or 0,
                "cpc": item.get("cpc") or 0,
                "monthly_searches": item.get("monthly_searches") or [],
            })

        return volume_data
    except Exception as e:
        logger.warning(f"Failed to fetch live search volume: {e}")
        return []


async def fetch_technical_audit(
    client,
    url: str,
    language: str
) -> TechnicalAudit:
    """
    Run technical SEO audit on a page.

    Uses On-Page Instant Pages API.
    """
    # Note: accept_language parameter not supported by instant_pages endpoint
    result = await client.post(
        "on_page/instant_pages",
        [{
            "url": url,
            "enable_javascript": True,
        }]
    )

    # Safe parsing
    tasks = result.get("tasks") or [{}]
    items = tasks[0].get("result") or []

    if not items:
        return TechnicalAudit(
            url=url,
            title="",
            load_time=0,
            page_size=0,
            word_count=0,
            h1_count=0,
            h2_count=0,
            internal_links=0,
            external_links=0,
            images_count=0,
            images_without_alt=0,
            meta_title="",
            meta_description="",
            canonical_url="",
            is_mobile_friendly=False,
            core_web_vitals={},
            issues=["Failed to analyze page"],
        )

    page = items[0]
    meta = page.get("meta", {})
    on_page = page.get("page_timing", {})
    checks = page.get("checks", {})

    # Collect issues
    issues = []

    if not meta.get("title"):
        issues.append("Missing title tag")
    elif len(meta.get("title", "")) > 60:
        issues.append("Title too long (>60 chars)")

    if not meta.get("description"):
        issues.append("Missing meta description")
    elif len(meta.get("description", "")) > 160:
        issues.append("Meta description too long (>160 chars)")

    if checks.get("no_h1_tag"):
        issues.append("Missing H1 tag")
    if checks.get("duplicate_h1_tag"):
        issues.append("Duplicate H1 tags")

    if checks.get("no_image_alt"):
        issues.append("Images missing alt text")

    if checks.get("is_broken"):
        issues.append("Page has broken elements")

    # Get word count
    content = page.get("content", {})
    word_count = content.get("plain_text_word_count", 0)

    return TechnicalAudit(
        url=url,
        title=meta.get("title", ""),
        load_time=on_page.get("duration_time", 0) / 1000,  # Convert to seconds
        page_size=page.get("resource_size", 0),
        word_count=word_count,
        h1_count=len(meta.get("htags", {}).get("h1") or []),
        h2_count=len(meta.get("htags", {}).get("h2") or []),
        internal_links=meta.get("internal_links_count", 0),
        external_links=meta.get("external_links_count", 0),
        images_count=meta.get("images_count", 0),
        images_without_alt=checks.get("no_image_alt_count", 0) or 0,
        meta_title=meta.get("title", ""),
        meta_description=meta.get("description", ""),
        canonical_url=meta.get("canonical", ""),
        is_mobile_friendly=checks.get("is_mobile_friendly", False),
        core_web_vitals={
            "largest_contentful_paint": on_page.get("time_to_interactive", 0),
            "first_input_delay": 0,  # Requires real user data
            "cumulative_layout_shift": 0,  # Requires real user data
        },
        issues=issues,
    )


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def calculate_ai_visibility_score(
    keyword_data: List[Dict],
    chatgpt_mentions: Dict,
    google_ai_mentions: Dict
) -> float:
    """
    Calculate AI visibility score (0-100).

    Based on:
    - Number of AI mentions
    - Coverage across platforms
    """
    score = 0

    # ChatGPT mentions (up to 40 points)
    chatgpt_count = chatgpt_mentions.get("total_mentions", 0)
    score += min(chatgpt_count * 2, 40)

    # Google AI mentions (up to 40 points)
    google_count = google_ai_mentions.get("total_mentions", 0)
    score += min(google_count * 2, 40)

    # Keyword coverage (up to 20 points)
    if keyword_data:
        score += min(len(keyword_data), 20)

    return min(score, 100)


def calculate_sentiment_score(sentiment_summary: Dict) -> float:
    """
    Calculate brand sentiment score (-100 to +100).

    Based on positive vs negative mention ratio.
    """
    distribution = sentiment_summary.get("sentiment_distribution", {})

    positive = distribution.get("positive", 0)
    negative = distribution.get("negative", 0)
    total = positive + negative

    if total == 0:
        return 0

    # Score: (positive - negative) / total * 100
    score = (positive - negative) / total * 100

    return round(score, 1)


def calculate_technical_score(audits: List[TechnicalAudit]) -> float:
    """
    Calculate technical health score (0-100).

    Based on:
    - Issue count
    - Load time
    - Mobile friendliness
    """
    if not audits:
        return 0

    total_score = 0

    for audit in audits:
        page_score = 100

        # Deduct for issues (5 points each)
        page_score -= len(audit.issues) * 5

        # Deduct for slow load time (> 3 seconds)
        if audit.load_time > 3:
            page_score -= min((audit.load_time - 3) * 10, 30)

        # Deduct if not mobile friendly
        if not audit.is_mobile_friendly:
            page_score -= 20

        # Deduct for missing content
        if audit.word_count < 300:
            page_score -= 10

        total_score += max(page_score, 0)

    return round(total_score / len(audits), 1)


# ============================================================================
# TESTING
# ============================================================================

async def test_phase4():
    """Test Phase 4 collection."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Mock client for testing
    class MockClient:
        async def post(self, endpoint, data):
            return {"tasks": [{"result": [{"items": []}]}]}

    client = MockClient()

    result = await collect_ai_technical_data(
        client=client,
        domain="example.com",
        brand_name="Example Brand",
        market="United States",
        language="English",  # FIXED: was "sv"
        top_keywords=["seo", "marketing"],
        top_pages=["https://example.com/"],
    )

    print(f"AI keyword data: {len(result['ai_keyword_data'])}")
    print(f"Brand mentions: {len(result['brand_mentions'])}")
    print(f"Technical audits: {len(result['technical_audits'])}")
    print(f"AI visibility score: {result['ai_visibility_score']}")
    print(f"Sentiment score: {result['brand_sentiment_score']}")
    print(f"Technical score: {result['technical_health_score']}")


if __name__ == "__main__":
    asyncio.run(test_phase4())

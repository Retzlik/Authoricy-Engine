"""
Phase 2: Keyword Intelligence Data Collection

Collects comprehensive keyword data including:
- Current rankings (what keywords the domain ranks for)
- Keyword universe (all relevant keywords for the site)
- Search intent classification
- Long-tail keyword expansion
- Semantic keyword expansion
- Keyword gap identification
- Difficulty scoring
- Historical search volume trends
- SERP element analysis
- Top searches by keyword
- Questions for keywords (People Also Ask)
- Bulk traffic estimation

Execution strategy:
- Initial calls (ranked_keywords, keywords_for_site) run in parallel
- Expansion calls depend on seed keywords from initial calls
- Bulk operations (difficulty, intent) batch multiple keywords

Expected API calls: 18-25 depending on seed keyword count
Expected time: 6-10 seconds (with parallelization)

Note: All endpoints use language_name (e.g., "English") not language_code (e.g., "en")
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class RankedKeyword:
    """A keyword the domain currently ranks for."""
    keyword: str
    position: int
    search_volume: int
    cpc: float
    competition: float
    url: str
    traffic: float
    traffic_value: float
    intent: Optional[str] = None


@dataclass
class KeywordGap:
    """A keyword opportunity the domain doesn't rank for."""
    keyword: str
    search_volume: int
    difficulty: int
    cpc: float
    competitor_count: int  # How many competitors rank for this
    opportunity_score: float  # Calculated: volume / difficulty


@dataclass
class KeywordCluster:
    """A group of related keywords around a seed topic."""
    seed_keyword: str
    keywords: List[Dict]
    total_volume: int
    avg_difficulty: float
    keyword_count: int


@dataclass
class Phase2Data:
    """Complete Phase 2 data container."""
    ranked_keywords: List[RankedKeyword] = field(default_factory=list)
    keyword_universe: List[Dict] = field(default_factory=list)
    intent_classification: Dict[str, Dict] = field(default_factory=dict)
    keyword_clusters: List[KeywordCluster] = field(default_factory=list)
    keyword_gaps: List[KeywordGap] = field(default_factory=list)
    difficulty_scores: Dict[str, int] = field(default_factory=dict)

    # Summary metrics
    total_ranking_keywords: int = 0
    total_search_volume: int = 0
    intent_distribution: Dict[str, int] = field(default_factory=dict)
    position_distribution: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# MAIN COLLECTION FUNCTION
# ============================================================================

async def collect_keyword_data(
    client,  # DataForSEOClient
    domain: str,
    market: str,
    language: str,
    seed_keywords: Optional[List[str]] = None,
    max_seed_keywords: int = 10,
    expansion_limit: int = 50
) -> Dict[str, Any]:
    """
    Collect Phase 2: Keyword Intelligence data.

    Args:
        client: DataForSEO API client
        domain: Target domain
        market: Target market (e.g., "United States", "Sweden")
        language: Language name (e.g., "English", "Swedish") - NOT code!
        seed_keywords: Optional seed keywords from Phase 1 (top page keywords)
        max_seed_keywords: Maximum seeds to expand (controls API cost)
        expansion_limit: Results limit per expansion call

    Returns:
        Dictionary with all Phase 2 data
    """

    logger.info(f"Phase 2: Starting keyword collection for {domain}")

    # -------------------------------------------------------------------------
    # Step 1: Initial parallel calls (ranked keywords + keyword universe)
    # -------------------------------------------------------------------------

    logger.info("Step 1: Fetching ranked keywords and keyword universe...")

    initial_tasks = [
        fetch_ranked_keywords(client, domain, market, language, limit=1000),
        fetch_keywords_for_site(client, domain, market, language, limit=500),
    ]

    ranked_result, universe_result = await asyncio.gather(
        *initial_tasks, return_exceptions=True
    )

    # Handle errors gracefully
    ranked_keywords = ranked_result if not isinstance(ranked_result, Exception) else []
    keyword_universe = universe_result if not isinstance(universe_result, Exception) else []

    if isinstance(ranked_result, Exception):
        logger.warning(f"Failed to fetch ranked keywords: {ranked_result}")
    if isinstance(universe_result, Exception):
        logger.warning(f"Failed to fetch keyword universe: {universe_result}")

    logger.info(f"Found {len(ranked_keywords)} ranked keywords, {len(keyword_universe)} universe keywords")

    # -------------------------------------------------------------------------
    # Step 2: Extract seed keywords for expansion
    # -------------------------------------------------------------------------

    # Use provided seeds or extract from ranked keywords
    if not seed_keywords:
        seed_keywords = extract_seed_keywords(ranked_keywords, max_count=max_seed_keywords)
    else:
        seed_keywords = seed_keywords[:max_seed_keywords]

    logger.info(f"Using {len(seed_keywords)} seed keywords for expansion: {seed_keywords[:5]}...")

    # -------------------------------------------------------------------------
    # Step 3: Keyword expansion (suggestions + related) - parallel per seed
    # -------------------------------------------------------------------------

    logger.info("Step 2: Expanding keywords...")

    keyword_clusters = []
    if seed_keywords:
        expansion_tasks = []
        for seed in seed_keywords:
            expansion_tasks.append(
                expand_keyword(client, seed, market, language, limit=expansion_limit)
            )

        expansion_results = await asyncio.gather(*expansion_tasks, return_exceptions=True)

        for seed, result in zip(seed_keywords, expansion_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to expand '{seed}': {result}")
            else:
                keyword_clusters.append(result)

    logger.info(f"Created {len(keyword_clusters)} keyword clusters")

    # -------------------------------------------------------------------------
    # Step 4: Search intent classification (batch call)
    # -------------------------------------------------------------------------

    logger.info("Step 3: Classifying search intent...")

    # Get top 200 keywords for intent classification
    top_keywords = [kw["keyword"] for kw in ranked_keywords[:200]]

    intent_classification = {}
    if top_keywords:
        intent_result = await fetch_search_intent(client, top_keywords, language)
        if not isinstance(intent_result, Exception):
            intent_classification = intent_result
        else:
            logger.warning(f"Failed to classify intent: {intent_result}")

    # -------------------------------------------------------------------------
    # Step 5: Keyword gap identification
    # -------------------------------------------------------------------------

    logger.info("Step 4: Identifying keyword gaps...")

    keyword_gaps = await fetch_keyword_ideas(
        client,
        seed_keywords[:5],  # Use top 5 seeds for gap analysis
        market,
        language,
        limit=200
    )

    if isinstance(keyword_gaps, Exception):
        logger.warning(f"Failed to fetch keyword gaps: {keyword_gaps}")
        keyword_gaps = []

    # -------------------------------------------------------------------------
    # Step 6: Difficulty scoring for priority keywords
    # -------------------------------------------------------------------------

    logger.info("Step 5: Scoring keyword difficulty...")

    # Combine gap keywords + top opportunities for difficulty scoring
    keywords_to_score = []
    keywords_to_score.extend([g["keyword"] for g in keyword_gaps[:100]])
    keywords_to_score.extend([kw["keyword"] for kw in ranked_keywords if kw.get("position", 100) > 10][:100])
    keywords_to_score = list(set(keywords_to_score))[:200]  # Dedupe, limit to 200

    difficulty_scores = {}
    if keywords_to_score:
        difficulty_result = await fetch_bulk_difficulty(client, keywords_to_score, market, language)
        if not isinstance(difficulty_result, Exception):
            difficulty_scores = difficulty_result
        else:
            logger.warning(f"Failed to fetch difficulty: {difficulty_result}")

    # -------------------------------------------------------------------------
    # Step 6b: Additional keyword intelligence (parallel)
    # -------------------------------------------------------------------------

    logger.info("Step 6: Fetching additional keyword intelligence...")

    additional_tasks = [
        fetch_historical_search_volume(client, seed_keywords[:10], market, language),
        fetch_serp_elements(client, seed_keywords[:20], market, language),
        fetch_questions_for_keywords(client, seed_keywords[:5], market, language),
        fetch_top_searches(client, domain, market, language),
        fetch_bulk_traffic_estimation(client, domain, seed_keywords[:50], market, language),
    ]

    additional_results = await asyncio.gather(*additional_tasks, return_exceptions=True)

    historical_volume = additional_results[0] if not isinstance(additional_results[0], Exception) else []
    serp_elements = additional_results[1] if not isinstance(additional_results[1], Exception) else []
    questions_data = additional_results[2] if not isinstance(additional_results[2], Exception) else []
    top_searches = additional_results[3] if not isinstance(additional_results[3], Exception) else []
    traffic_estimation = additional_results[4] if not isinstance(additional_results[4], Exception) else {}

    for i, name in enumerate(["historical_volume", "serp_elements", "questions", "top_searches", "traffic_estimation"]):
        if isinstance(additional_results[i], Exception):
            logger.warning(f"Failed to fetch {name}: {additional_results[i]}")

    # -------------------------------------------------------------------------
    # Step 7: Calculate summary metrics
    # -------------------------------------------------------------------------

    logger.info("Calculating summary metrics...")

    summary = calculate_keyword_summary(
        ranked_keywords,
        keyword_universe,
        intent_classification,
        keyword_clusters,
        keyword_gaps
    )

    logger.info(f"Phase 2 complete: {summary['total_ranking_keywords']} keywords, "
                f"{summary['total_search_volume']} total volume")

    return {
        "ranked_keywords": ranked_keywords,
        "keyword_universe": keyword_universe,
        "intent_classification": intent_classification,
        "keyword_clusters": [
            {
                "seed_keyword": c.seed_keyword,
                "keywords": c.keywords,
                "total_volume": c.total_volume,
                "avg_difficulty": c.avg_difficulty,
                "keyword_count": c.keyword_count
            }
            for c in keyword_clusters if isinstance(c, KeywordCluster)
        ],
        "keyword_gaps": keyword_gaps,
        "difficulty_scores": difficulty_scores,
        "historical_volume": historical_volume,
        "serp_elements": serp_elements,
        "questions_data": questions_data,
        "top_searches": top_searches,
        "traffic_estimation": traffic_estimation,
        **summary
    }


# ============================================================================
# INDIVIDUAL FETCH FUNCTIONS
# ============================================================================

async def fetch_ranked_keywords(
    client,
    domain: str,
    market: str,
    language: str,
    limit: int = 1000
) -> List[Dict]:
    """
    Fetch all keywords the domain currently ranks for.
    Returns keywords with: position, volume, CPC, URL, traffic
    """
    result = await client.post(
        "dataforseo_labs/google/ranked_keywords/live",
        [{
            "target": domain,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
            "limit": limit,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"]
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

    keywords = []
    for item in items:
        kw_data = item.get("keyword_data", {})
        kw_info = kw_data.get("keyword_info", {})
        serp_item = item.get("ranked_serp_element", {}).get("serp_item", {})

        keywords.append({
            "keyword": kw_data.get("keyword", ""),
            "position": serp_item.get("rank_group", 0),
            "search_volume": kw_info.get("search_volume", 0),
            "cpc": kw_info.get("cpc", 0),
            "competition": kw_info.get("competition", 0),
            "url": serp_item.get("url", ""),
            "traffic": item.get("ranked_serp_element", {}).get("etv", 0),
            "traffic_value": item.get("ranked_serp_element", {}).get("estimated_paid_traffic_cost", 0),
        })

    return keywords


async def fetch_keywords_for_site(
    client,
    domain: str,
    market: str,
    language: str,
    limit: int = 500
) -> List[Dict]:
    """
    Fetch keyword universe - all relevant keywords for the site.
    This includes keywords the site could/should rank for based on its content.
    """
    result = await client.post(
        "dataforseo_labs/google/keywords_for_site/live",
        [{
            "target": domain,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
            "limit": limit,
            "include_subdomains": True
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

    keywords = []
    for item in items:
        kw_info = item.get("keyword_info", {})

        keywords.append({
            "keyword": item.get("keyword", ""),
            "search_volume": kw_info.get("search_volume", 0),
            "cpc": kw_info.get("cpc", 0),
            "competition": kw_info.get("competition", 0),
            "competition_level": kw_info.get("competition_level", ""),
        })

    return keywords


async def fetch_search_intent(
    client,
    keywords: List[str],
    language: str
) -> Dict[str, Dict]:
    """
    Classify search intent for a list of keywords.
    Returns dict mapping keyword -> intent data
    """
    # API accepts max 1000 keywords per call
    keywords = keywords[:1000]

    result = await client.post(
        "dataforseo_labs/google/search_intent/live",
        [{
            "keywords": keywords,
            "language_name": language  # FIXED: was language_code
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [])

    intent_map = {}
    for item in items:
        keyword = item.get("keyword", "")
        intent_map[keyword] = {
            "intent": item.get("keyword_intent", {}).get("label", "unknown"),
            "probability": item.get("keyword_intent", {}).get("probability", 0),
            "secondary_intents": item.get("secondary_keyword_intents", [])
        }

    return intent_map


async def fetch_keyword_suggestions(
    client,
    keyword: str,
    market: str,
    language: str,
    limit: int = 100
) -> List[Dict]:
    """
    Fetch long-tail keyword suggestions for a seed keyword.
    Returns keywords that contain the seed keyword with additional terms.
    """
    result = await client.post(
        "dataforseo_labs/google/keyword_suggestions/live",
        [{
            "keyword": keyword,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
            "limit": limit
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

    suggestions = []
    for item in items:
        kw_info = item.get("keyword_info", {})

        suggestions.append({
            "keyword": item.get("keyword", ""),
            "search_volume": kw_info.get("search_volume", 0),
            "cpc": kw_info.get("cpc", 0),
            "competition": kw_info.get("competition", 0),
        })

    return suggestions


async def fetch_related_keywords(
    client,
    keyword: str,
    market: str,
    language: str,
    limit: int = 100,
    depth: int = 2
) -> List[Dict]:
    """
    Fetch semantically related keywords for a seed keyword.
    Uses DataForSEO's "searches related to" SERP data.
    """
    result = await client.post(
        "dataforseo_labs/google/related_keywords/live",
        [{
            "keyword": keyword,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
            "limit": limit,
            "depth": depth
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

    related = []
    for item in items:
        kw_data = item.get("keyword_data", {})
        kw_info = kw_data.get("keyword_info", {})

        related.append({
            "keyword": kw_data.get("keyword", ""),
            "search_volume": kw_info.get("search_volume", 0),
            "cpc": kw_info.get("cpc", 0),
            "competition": kw_info.get("competition", 0),
            "depth": item.get("depth", 0),
        })

    return related


async def fetch_keyword_ideas(
    client,
    seed_keywords: List[str],
    market: str,
    language: str,
    limit: int = 200
) -> List[Dict]:
    """
    Fetch keyword ideas - potential keywords not currently ranking for.
    These represent keyword gaps / opportunities.
    """
    result = await client.post(
        "dataforseo_labs/google/keyword_ideas/live",
        [{
            "keywords": seed_keywords,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
            "limit": limit,
            "filters": [["keyword_info.search_volume", ">", 50]]  # Filter low-volume
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

    ideas = []
    for item in items:
        kw_info = item.get("keyword_info", {})
        search_volume = kw_info.get("search_volume", 0)
        competition = kw_info.get("competition", 0.5)

        # Calculate opportunity score: volume / (competition * 100)
        # Higher = better opportunity
        opportunity_score = search_volume / max(competition * 100, 1)

        ideas.append({
            "keyword": item.get("keyword", ""),
            "search_volume": search_volume,
            "cpc": kw_info.get("cpc", 0),
            "competition": competition,
            "competition_level": kw_info.get("competition_level", ""),
            "opportunity_score": round(opportunity_score, 2),
        })

    # Sort by opportunity score
    ideas.sort(key=lambda x: x["opportunity_score"], reverse=True)

    return ideas


async def fetch_bulk_difficulty(
    client,
    keywords: List[str],
    market: str,
    language: str
) -> Dict[str, int]:
    """
    Fetch keyword difficulty scores in bulk.
    Returns dict mapping keyword -> difficulty score (0-100)
    """
    # API accepts max 1000 keywords
    keywords = keywords[:1000]

    result = await client.post(
        "dataforseo_labs/google/bulk_keyword_difficulty/live",
        [{
            "keywords": keywords,
            "location_name": market,
            "language_name": language  # FIXED: was language_code
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [])

    difficulty_map = {}
    for item in items:
        keyword = item.get("keyword", "")
        difficulty = item.get("keyword_difficulty", 0)
        difficulty_map[keyword] = difficulty

    return difficulty_map


async def fetch_historical_search_volume(
    client,
    keywords: List[str],
    market: str,
    language: str
) -> List[Dict]:
    """
    Fetch historical search volume data for keywords (12 months).
    Returns monthly volume trends for each keyword.
    """
    result = await client.post(
        "dataforseo_labs/google/historical_search_volume/live",
        [{
            "keywords": keywords[:100],  # Max 100 keywords
            "location_name": market,
            "language_name": language  # FIXED: was language_code
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [])

    historical_data = []
    for item in items:
        keyword = item.get("keyword", "")
        monthly_searches = item.get("keyword_info", {}).get("monthly_searches", [])

        historical_data.append({
            "keyword": keyword,
            "monthly_searches": monthly_searches,
            "trend_direction": calculate_trend_direction(monthly_searches),
        })

    return historical_data


def calculate_trend_direction(monthly_searches: List[Dict]) -> str:
    """Calculate if trend is rising, falling, or stable."""
    if not monthly_searches or len(monthly_searches) < 2:
        return "stable"

    values = [m.get("search_volume", 0) for m in monthly_searches]
    first_half = sum(values[:len(values)//2])
    second_half = sum(values[len(values)//2:])

    if second_half > first_half * 1.15:
        return "rising"
    elif second_half < first_half * 0.85:
        return "falling"
    return "stable"


async def fetch_serp_elements(
    client,
    keywords: List[str],
    market: str,
    language: str
) -> List[Dict]:
    """
    Fetch SERP element distribution for keywords.
    Shows what SERP features appear for each keyword (featured snippets, PAA, etc.)
    """
    # Note: item_types parameter not supported by serp_competitors endpoint
    result = await client.post(
        "dataforseo_labs/google/serp_competitors/live",
        [{
            "keywords": keywords[:200],  # Max 200 keywords
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
        }]
    )

    task_result = result.get("tasks", [{}])[0].get("result", [{}])[0]

    serp_elements = {
        "organic_results": task_result.get("organic_results_count", 0),
        "featured_snippets": task_result.get("featured_snippets_count", 0),
        "people_also_ask": task_result.get("people_also_ask_count", 0),
        "local_packs": task_result.get("local_pack_count", 0),
        "knowledge_graphs": task_result.get("knowledge_graph_count", 0),
        "items": task_result.get("items", [])[:50],
    }

    return [serp_elements]


async def fetch_questions_for_keywords(
    client,
    keywords: List[str],
    market: str,
    language: str
) -> List[Dict]:
    """
    Fetch People Also Ask questions for keywords.
    Returns related questions for content ideation.
    """
    all_questions = []

    for keyword in keywords[:5]:  # Limit to 5 keywords to control costs
        result = await client.post(
            "dataforseo_labs/google/related_keywords/live",
            [{
                "keyword": keyword,
                "location_name": market,
                "language_name": language,  # FIXED: was language_code
                "include_questions": True,
                "limit": 50
            }]
        )

        items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

        questions = [
            {
                "seed_keyword": keyword,
                "question": item.get("keyword_data", {}).get("keyword", ""),
                "search_volume": item.get("keyword_data", {}).get("keyword_info", {}).get("search_volume", 0),
            }
            for item in items
            if "?" in item.get("keyword_data", {}).get("keyword", "")
        ]

        all_questions.extend(questions)

    return all_questions


async def fetch_top_searches(
    client,
    domain: str,
    market: str,
    language: str,
    limit: int = 100
) -> List[Dict]:
    """
    Fetch top performing search queries for the domain.
    Returns highest traffic keywords.
    """
    result = await client.post(
        "dataforseo_labs/google/ranked_keywords/live",
        [{
            "target": domain,
            "location_name": market,
            "language_name": language,  # FIXED: was language_code
            "limit": limit,
            "order_by": ["ranked_serp_element.etv,desc"]  # Sort by estimated traffic
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

    return [
        {
            "keyword": item.get("keyword_data", {}).get("keyword", ""),
            "position": item.get("ranked_serp_element", {}).get("serp_item", {}).get("rank_group", 0),
            "traffic": item.get("ranked_serp_element", {}).get("etv", 0),
            "traffic_cost": item.get("ranked_serp_element", {}).get("estimated_paid_traffic_cost", 0),
            "url": item.get("ranked_serp_element", {}).get("serp_item", {}).get("url", ""),
        }
        for item in items
    ]


async def fetch_bulk_traffic_estimation(
    client,
    domain: str,
    keywords: List[str],
    market: str,
    language: str
) -> Dict[str, Any]:
    """
    Estimate traffic potential for keywords at different positions.
    Useful for opportunity sizing.
    """
    # Note: bulk_traffic_estimation uses 'keywords', not 'targets'
    result = await client.post(
        "dataforseo_labs/google/bulk_traffic_estimation/live",
        [{
            "keywords": keywords[:200],  # Max 200 keywords - FIXED: was 'targets'
            "location_name": market,
            "language_name": language  # FIXED: was language_code
        }]
    )

    items = result.get("tasks", [{}])[0].get("result", [])

    traffic_estimates = {}
    total_potential = 0

    for item in items:
        keyword = item.get("keyword", "")
        estimate = {
            "traffic_at_pos_1": item.get("metrics", {}).get("pos_1", {}).get("etv", 0),
            "traffic_at_pos_3": item.get("metrics", {}).get("pos_3", {}).get("etv", 0),
            "traffic_at_pos_10": item.get("metrics", {}).get("pos_10", {}).get("etv", 0),
        }
        traffic_estimates[keyword] = estimate
        total_potential += estimate["traffic_at_pos_1"]

    return {
        "keyword_estimates": traffic_estimates,
        "total_pos_1_potential": total_potential,
        "keywords_analyzed": len(traffic_estimates),
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def expand_keyword(
    client,
    seed_keyword: str,
    market: str,
    language: str,
    limit: int = 50
) -> KeywordCluster:
    """
    Expand a seed keyword into a full cluster.
    Combines suggestions + related keywords, deduplicates, calculates metrics.
    """
    # Fetch both suggestion types in parallel
    suggestions_task = fetch_keyword_suggestions(client, seed_keyword, market, language, limit)
    related_task = fetch_related_keywords(client, seed_keyword, market, language, limit)

    suggestions, related = await asyncio.gather(
        suggestions_task, related_task, return_exceptions=True
    )

    # Handle errors
    if isinstance(suggestions, Exception):
        suggestions = []
    if isinstance(related, Exception):
        related = []

    # Combine and deduplicate
    all_keywords = {}

    for kw in suggestions:
        keyword = kw.get("keyword", "").lower()
        if keyword and keyword not in all_keywords:
            all_keywords[keyword] = kw

    for kw in related:
        keyword = kw.get("keyword", "").lower()
        if keyword and keyword not in all_keywords:
            all_keywords[keyword] = kw

    # Convert to list
    keywords_list = list(all_keywords.values())

    # Calculate cluster metrics
    total_volume = sum(kw.get("search_volume", 0) for kw in keywords_list)
    competitions = [kw.get("competition", 0) for kw in keywords_list if kw.get("competition")]
    avg_difficulty = sum(competitions) / len(competitions) * 100 if competitions else 50

    return KeywordCluster(
        seed_keyword=seed_keyword,
        keywords=keywords_list,
        total_volume=total_volume,
        avg_difficulty=round(avg_difficulty, 1),
        keyword_count=len(keywords_list)
    )


def extract_seed_keywords(ranked_keywords: List[Dict], max_count: int = 10) -> List[str]:
    """
    Extract the best seed keywords from ranked keywords.

    Strategy:
    - Prioritize keywords in positions 4-20 (improvement opportunities)
    - Weight by search volume
    - Avoid branded keywords
    """
    # Filter to positions 4-20 (opportunity zone)
    opportunities = [
        kw for kw in ranked_keywords
        if 4 <= kw.get("position", 100) <= 20
    ]

    # If not enough, include top positions too
    if len(opportunities) < max_count:
        opportunities = ranked_keywords

    # Sort by search volume
    opportunities.sort(key=lambda x: x.get("search_volume", 0), reverse=True)

    # Extract unique keywords
    seeds = []
    seen = set()

    for kw in opportunities:
        keyword = kw.get("keyword", "").strip()

        # Skip if empty, duplicate, or likely branded (single word matching domain)
        if not keyword or keyword.lower() in seen:
            continue

        seeds.append(keyword)
        seen.add(keyword.lower())

        if len(seeds) >= max_count:
            break

    return seeds


def calculate_keyword_summary(
    ranked_keywords: List[Dict],
    keyword_universe: List[Dict],
    intent_classification: Dict,
    keyword_clusters: List[KeywordCluster],
    keyword_gaps: List[Dict]
) -> Dict[str, Any]:
    """
    Calculate summary metrics from all keyword data.
    """
    # Total counts
    total_ranking = len(ranked_keywords)
    total_volume = sum(kw.get("search_volume", 0) for kw in ranked_keywords)

    # Position distribution
    position_dist = {
        "pos_1_3": 0,
        "pos_4_10": 0,
        "pos_11_20": 0,
        "pos_21_50": 0,
        "pos_51_100": 0
    }

    for kw in ranked_keywords:
        pos = kw.get("position", 100)
        if pos <= 3:
            position_dist["pos_1_3"] += 1
        elif pos <= 10:
            position_dist["pos_4_10"] += 1
        elif pos <= 20:
            position_dist["pos_11_20"] += 1
        elif pos <= 50:
            position_dist["pos_21_50"] += 1
        else:
            position_dist["pos_51_100"] += 1

    # Intent distribution
    intent_dist = {
        "informational": 0,
        "commercial": 0,
        "transactional": 0,
        "navigational": 0,
        "unknown": 0
    }

    for keyword, intent_data in intent_classification.items():
        intent = intent_data.get("intent", "unknown").lower()
        if intent in intent_dist:
            intent_dist[intent] += 1
        else:
            intent_dist["unknown"] += 1

    # Cluster metrics
    total_cluster_volume = sum(
        c.total_volume for c in keyword_clusters
        if isinstance(c, KeywordCluster)
    )
    total_cluster_keywords = sum(
        c.keyword_count for c in keyword_clusters
        if isinstance(c, KeywordCluster)
    )

    # Gap metrics
    total_gap_volume = sum(g.get("search_volume", 0) for g in keyword_gaps)
    high_opportunity_gaps = [g for g in keyword_gaps if g.get("opportunity_score", 0) > 50]

    return {
        "total_ranking_keywords": total_ranking,
        "total_search_volume": total_volume,
        "position_distribution": position_dist,
        "intent_distribution": intent_dist,
        "cluster_metrics": {
            "cluster_count": len([c for c in keyword_clusters if isinstance(c, KeywordCluster)]),
            "total_keywords": total_cluster_keywords,
            "total_volume": total_cluster_volume
        },
        "gap_metrics": {
            "total_gaps": len(keyword_gaps),
            "total_gap_volume": total_gap_volume,
            "high_opportunity_count": len(high_opportunity_gaps)
        }
    }


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test Phase 2 collection standalone.

    Usage: python -m src.collector.phase2

    Requires: DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in environment
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    async def test():
        # Import client (assumes phase1.py structure)
        from src.collector.client import DataForSEOClient

        client = DataForSEOClient(
            login=os.getenv("DATAFORSEO_LOGIN"),
            password=os.getenv("DATAFORSEO_PASSWORD")
        )

        try:
            # Test with a domain
            result = await collect_keyword_data(
                client=client,
                domain="example.com",  # Replace with real domain
                market="United States",
                language="English",  # FIXED: was "sv"
                max_seed_keywords=5  # Limit for testing
            )

            print("\n=== PHASE 2 RESULTS ===\n")
            print(f"Ranked Keywords: {result['total_ranking_keywords']}")
            print(f"Total Search Volume: {result['total_search_volume']:,}")
            print(f"Position Distribution: {result['position_distribution']}")
            print(f"Intent Distribution: {result['intent_distribution']}")
            print(f"Clusters Created: {result['cluster_metrics']['cluster_count']}")
            print(f"Keyword Gaps Found: {result['gap_metrics']['total_gaps']}")

            print("\n=== TOP 10 RANKED KEYWORDS ===\n")
            for kw in result["ranked_keywords"][:10]:
                print(f"  {kw['position']:3d}. {kw['keyword'][:40]:40s} vol={kw['search_volume']:,}")

            print("\n=== TOP 10 KEYWORD GAPS ===\n")
            for gap in result["keyword_gaps"][:10]:
                print(f"  {gap['keyword'][:40]:40s} vol={gap['search_volume']:,} opp={gap['opportunity_score']}")

        finally:
            await client.close()

    asyncio.run(test())

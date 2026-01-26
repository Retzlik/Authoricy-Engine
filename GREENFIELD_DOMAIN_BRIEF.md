# Greenfield Domain Intelligence: Product Brief

**Version:** 1.0
**Date:** January 2026
**Status:** Ready for Implementation

---

## Executive Summary

Most SEO intelligence platforms fail new domains. They attempt to analyze domain-centric data that doesn't exist, producing empty dashboards and generic recommendations. This creates a critical market gap: the fastest-growing segment of potential customers—startups, new product launches, market expansions—receives the least value.

**This brief outlines Authoricy's Greenfield Domain Intelligence capability**: a complete methodological pivot that treats the competitive landscape as the primary data source when domain data is insufficient. Instead of "your traffic is 0," we show "the market opportunity is 2.4M monthly searches, and here's exactly how to capture it."

**Business Impact:**
- Expands addressable market to include all new domains (currently underserved)
- Differentiates from competitors who fail this segment
- Creates stickiness: clients who start with us at zero stay as they grow
- Higher perceived value: "here's how to build from zero" > "you have no data"

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Architecture](#2-solution-architecture)
3. [Data Sufficiency Classification](#3-data-sufficiency-classification)
4. [Competitor-First Collection Pipeline](#4-competitor-first-collection-pipeline)
5. [Core Algorithms](#5-core-algorithms)
6. [Database Schema Changes](#6-database-schema-changes)
7. [API Endpoints](#7-api-endpoints)
8. [Frontend Requirements](#8-frontend-requirements)
9. [Integration Points](#9-integration-points)
10. [Success Metrics](#10-success-metrics)
11. [Implementation Phases](#11-implementation-phases)

---

## 1. Problem Statement

### The Data Paradox

New domains face a fundamental data problem:

| What SEO Tools Need | What New Domains Have |
|---------------------|----------------------|
| Ranked keywords | 0 |
| Backlink profile | 0-10 links |
| Historical traffic | No data |
| Position trends | Nothing to trend |
| Content performance | No content yet |

**Current Authoricy behavior** (`orchestrator.py:400-404`):
```python
def _should_abbreviate(self, foundation: Dict) -> bool:
    keywords = foundation.get("domain_overview", {}).get("organic_keywords", 0)
    backlinks = foundation.get("backlink_summary", {}).get("total_backlinks", 0)
    return keywords < 10 and backlinks < 50
```

When triggered, we "abbreviate" analysis—essentially giving up. This fails the customer.

### Market Reality

Based on industry research:

| Domain Maturity | % of Potential Customers | Current Value Delivered |
|-----------------|--------------------------|------------------------|
| Established (DR 35+, 200+ kw) | ~30% | High |
| Growing (DR 20-35, 50-200 kw) | ~25% | Medium |
| New (DR <20, <50 kw) | ~45% | **Near Zero** |

**45% of potential customers receive near-zero value from current SEO tools.**

### What New Domains Actually Need

| Instead of This | Deliver This |
|-----------------|--------------|
| "You rank for 0 keywords" | "The market has 2.4M monthly searches across 8,432 keywords" |
| "Your traffic is 0" | "Competitors capture 450K monthly visits—here's your entry point" |
| "No data to analyze" | "23 beachhead keywords where you can rank within 90 days" |
| Generic recommendations | Phased growth roadmap with realistic milestones |

---

## 2. Solution Architecture

### The Three-Path Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOMAIN INPUT                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA SUFFICIENCY GATE                                     │
│                                                                              │
│   Fetch: Domain Rating, Organic Keywords, Organic Traffic, Referring Domains│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │INSUFFICIENT│   │ BORDERLINE │   │ SUFFICIENT │
            │  DR < 20   │   │ DR 20-35   │   │  DR > 35   │
            │  KW < 50   │   │ KW 50-200  │   │  KW > 200  │
            │Traffic<100 │   │Traffic<1K  │   │Traffic>1K  │
            └───────────┘   └───────────┘   └───────────┘
                    │               │               │
                    ▼               ▼               ▼
┌───────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│  GREENFIELD MODE      │ │  HYBRID MODE    │ │  STANDARD MODE      │
│                       │ │                 │ │                     │
│ • Competitor-first    │ │ • Domain data + │ │ • Domain-centric    │
│ • Market opportunity  │ │   competitor    │ │ • Current system    │
│ • Beachhead keywords  │ │   supplement    │ │ • Full analysis     │
│ • Growth roadmap      │ │ • Partial domain│ │                     │
│ • Scenario projections│ │   analysis      │ │                     │
└───────────────────────┘ └─────────────────┘ └─────────────────────┘
```

### Greenfield Mode: Core Principles

1. **Competitors ARE the data source** - Not supplements, the foundation
2. **Market opportunity framing** - Total addressable search market
3. **Winnability over difficulty** - What can you ACTUALLY rank for?
4. **Phased recommendations** - Not "optimize X" but "do X in month 1-3, Y in month 4-6"
5. **Honest projections** - Conservative/Expected/Aggressive scenarios

---

## 3. Data Sufficiency Classification

### Classification Algorithm

```python
class DomainMaturity(Enum):
    GREENFIELD = "greenfield"      # Competitor-first mode
    EMERGING = "emerging"          # Hybrid mode
    ESTABLISHED = "established"    # Standard mode

def classify_domain_maturity(metrics: DomainMetrics) -> DomainMaturity:
    """
    Classify domain into maturity tier for analysis routing.

    Thresholds based on industry research:
    - DR < 20 with < 50 keywords = insufficient for domain-centric analysis
    - DR 20-35 or 50-200 keywords = partial data, needs supplementation
    - DR > 35 with > 200 keywords = sufficient for full analysis
    """
    dr = metrics.domain_rating or 0
    kw = metrics.organic_keywords or 0
    traffic = metrics.organic_traffic or 0
    ref_domains = metrics.referring_domains or 0

    # GREENFIELD: Truly new domains
    if (dr < 20 and kw < 50) or (traffic < 100 and kw < 30):
        return DomainMaturity.GREENFIELD

    # EMERGING: Has some data but not enough for full analysis
    if dr < 35 or kw < 200 or traffic < 1000:
        return DomainMaturity.EMERGING

    # ESTABLISHED: Full data available
    return DomainMaturity.ESTABLISHED
```

### Required User Inputs for Greenfield Mode

When domain data is insufficient, we MUST collect business context to enable analysis:

**Tier 1: Essential (Required)**
```python
class GreenfieldContext(BaseModel):
    # Business Identity
    business_name: str
    business_description: str  # 2-3 sentences
    primary_offering: str      # Main product/service

    # Market Definition
    target_market: str         # Geographic (US, UK, Sweden)
    target_language: str       # Content language
    industry_vertical: str     # SaaS, E-commerce, Local Service, etc.

    # Seed Keywords (minimum 5)
    seed_keywords: List[str]   # Core terms representing offering

    # Known Competitors (minimum 3)
    known_competitors: List[str]  # Domains user knows compete
```

**Tier 2: Strategic Context (Recommended)**
```python
class StrategicContext(BaseModel):
    # Audience
    target_audience: str       # Who buys from you
    buyer_journey_type: str    # Impulse, considered, enterprise

    # Differentiation
    unique_value_prop: str     # What makes you different
    competitive_advantages: List[str]

    # Constraints
    content_budget: str        # Low/Medium/High
    timeline_expectations: str # 6mo, 12mo, 24mo

    # Goals
    primary_goal: str          # Traffic, Leads, Authority, Balanced
```

---

## 4. Competitor-First Collection Pipeline

### Phase G1: Competitor Discovery (No Domain Data Needed)

**Objective:** Identify 10-15 true competitors from seed keywords and user input.

```python
async def discover_competitors_greenfield(
    seed_keywords: List[str],
    known_competitors: List[str],
    market: str,
    language: str
) -> List[ValidatedCompetitor]:
    """
    Discover competitors using seed keywords when target domain has no data.

    Method:
    1. SERP analysis for seed keywords → extract ranking domains
    2. Traffic Share by Domain → who captures search demand
    3. User-provided competitors → validate and enrich
    4. Filter: Remove platforms (Wikipedia, Reddit), media sites, non-competitors
    5. Validate: Check business model alignment
    """

    competitors = []

    # Step 1: SERP-based discovery
    for keyword in seed_keywords:
        serp_results = await client.get_serp_results(
            keyword=keyword,
            location_name=market,
            language_name=language,
            depth=20
        )
        for result in serp_results:
            competitors.append(result.domain)

    # Step 2: Traffic share analysis
    traffic_share = await client.get_traffic_share_by_domain(
        keywords=seed_keywords,
        location_name=market
    )
    for domain_data in traffic_share:
        competitors.append(domain_data.domain)

    # Step 3: Enrich user-provided competitors
    for domain in known_competitors:
        competitors.append(domain)

    # Step 4: Deduplicate and filter
    competitors = deduplicate(competitors)
    competitors = filter_non_competitors(competitors)  # Remove Wikipedia, etc.

    # Step 5: Fetch domain metrics for validation
    enriched = []
    for domain in competitors[:20]:
        metrics = await client.get_domain_rank_overview(domain, market)
        enriched.append(ValidatedCompetitor(
            domain=domain,
            domain_rating=metrics.rank,
            organic_traffic=metrics.organic_traffic,
            organic_keywords=metrics.organic_keywords,
            # ... more fields
        ))

    # Step 6: Filter by relevance (DR range, traffic threshold)
    validated = [c for c in enriched if is_relevant_competitor(c)]

    return validated[:15]
```

**Filtering Logic:**
```python
def filter_non_competitors(domains: List[str]) -> List[str]:
    """Remove domains that are platforms, not competitors."""

    PLATFORM_DOMAINS = {
        'wikipedia.org', 'reddit.com', 'quora.com', 'medium.com',
        'youtube.com', 'facebook.com', 'twitter.com', 'linkedin.com',
        'amazon.com', 'ebay.com',  # Unless e-commerce client
        'yelp.com', 'tripadvisor.com',  # Unless local client
    }

    MEDIA_DOMAINS = {
        'forbes.com', 'businessinsider.com', 'techcrunch.com',
        'nytimes.com', 'theguardian.com', 'bbc.com',
    }

    return [d for d in domains if d not in PLATFORM_DOMAINS | MEDIA_DOMAINS]

def is_relevant_competitor(comp: ValidatedCompetitor, target_dr: int = 30) -> bool:
    """
    Filter competitors by relevance.

    Rules:
    - DR within 2x of target (aspirational but achievable)
    - Has meaningful traffic (>100/mo)
    - Has ranking keywords (>20)
    """
    if comp.domain_rating > target_dr * 2.5:
        return False  # Too dominant to learn from
    if comp.organic_traffic < 100:
        return False  # Too small
    if comp.organic_keywords < 20:
        return False  # Not enough data
    return True
```

### Phase G2: Keyword Universe Construction

**Objective:** Build complete keyword universe from competitors, not from target domain.

```python
async def build_keyword_universe_greenfield(
    competitors: List[ValidatedCompetitor],
    seed_keywords: List[str],
    market: str,
    language: str,
    depth: CollectionDepth
) -> KeywordUniverse:
    """
    Build keyword universe entirely from competitor data.

    Sources:
    1. Competitor organic keywords (top 500 per competitor)
    2. Seed keyword expansion (suggestions, related, PAA)
    3. Competitor PPC keywords (commercial intent signals)
    4. Question keywords (informational opportunities)
    """

    all_keywords = []

    # Source 1: Mine competitor keywords
    for comp in competitors[:7]:  # Top 7 competitors
        comp_keywords = await client.get_domain_keywords(
            domain=comp.domain,
            location_name=market,
            language_name=language,
            limit=500,
            order_by=["organic_traffic,desc"]
        )
        for kw in comp_keywords:
            all_keywords.append(KeywordCandidate(
                keyword=kw.keyword,
                search_volume=kw.search_volume,
                keyword_difficulty=kw.keyword_difficulty,
                cpc=kw.cpc,
                source="competitor",
                source_domain=comp.domain,
                source_position=kw.position
            ))

    # Source 2: Seed keyword expansion
    for seed in seed_keywords:
        # Suggestions (long-tail)
        suggestions = await client.get_keyword_suggestions(
            keyword=seed,
            location_name=market,
            language_name=language,
            limit=100
        )
        all_keywords.extend([KeywordCandidate(
            keyword=s.keyword,
            search_volume=s.search_volume,
            keyword_difficulty=s.keyword_difficulty,
            source="expansion"
        ) for s in suggestions])

        # Related keywords
        related = await client.get_related_keywords(
            keyword=seed,
            location_name=market,
            include_questions=True,
            depth=2
        )
        all_keywords.extend([KeywordCandidate(
            keyword=r.keyword,
            search_volume=r.search_volume,
            keyword_difficulty=r.keyword_difficulty,
            source="related"
        ) for r in related])

    # Source 3: PPC keywords (commercial intent)
    for comp in competitors[:5]:
        ppc_keywords = await client.get_domain_paid_keywords(
            domain=comp.domain,
            location_name=market
        )
        all_keywords.extend([KeywordCandidate(
            keyword=p.keyword,
            search_volume=p.search_volume,
            cpc=p.cpc,
            source="ppc",
            commercial_intent=True
        ) for p in ppc_keywords])

    # Deduplicate
    unique_keywords = deduplicate_keywords(all_keywords)

    # Classify intent
    intents = await client.classify_search_intent(
        keywords=[k.keyword for k in unique_keywords[:1000]]
    )
    for kw, intent in zip(unique_keywords, intents):
        kw.search_intent = intent

    # Calculate business relevance score
    for kw in unique_keywords:
        kw.business_relevance = calculate_business_relevance(
            keyword=kw.keyword,
            seed_keywords=seed_keywords,
            industry=context.industry_vertical
        )

    return KeywordUniverse(
        keywords=unique_keywords,
        total_volume=sum(k.search_volume for k in unique_keywords),
        total_keywords=len(unique_keywords)
    )
```

### Phase G3: SERP Analysis for Winnability

**Objective:** For each keyword, analyze SERP composition to determine winnability.

```python
async def analyze_serp_winnability(
    keywords: List[KeywordCandidate],
    target_dr: int,  # User's target DR (or current if >0)
    limit: int = 200
) -> List[KeywordWithWinnability]:
    """
    Analyze SERP composition to determine if keywords are winnable.

    Winnability factors:
    1. Average DR of top 10 results
    2. Presence of low-DR sites (if DR 15 site ranks, you can too)
    3. Content quality signals (outdated content, thin pages)
    4. SERP feature opportunities
    5. AI Overview presence (reduces opportunity)
    """

    results = []

    # Prioritize by opportunity score for SERP analysis
    priority_keywords = sorted(
        keywords,
        key=lambda k: k.search_volume / (k.keyword_difficulty + 1),
        reverse=True
    )[:limit]

    for kw in priority_keywords:
        # Get SERP results
        serp = await client.get_serp_results(
            keyword=kw.keyword,
            depth=10  # Top 10
        )

        # Calculate SERP metrics
        serp_drs = [r.domain_rating for r in serp.organic if r.domain_rating]
        avg_serp_dr = statistics.mean(serp_drs) if serp_drs else 50
        min_serp_dr = min(serp_drs) if serp_drs else 50

        # Check for low-DR opportunities
        low_dr_positions = [
            r.position for r in serp.organic
            if r.domain_rating and r.domain_rating < 30
        ]
        has_low_dr_rankings = len(low_dr_positions) > 0

        # Check for weak content signals
        weak_content_signals = []
        for r in serp.organic[:5]:
            if r.last_updated and r.last_updated.year < 2024:
                weak_content_signals.append("outdated_content")
            if r.word_count and r.word_count < 1000:
                weak_content_signals.append("thin_content")

        # Check for AI Overview
        has_ai_overview = serp.ai_overview is not None

        # Check for SERP features we can target
        targetable_features = []
        if serp.featured_snippet and not serp.featured_snippet.owned_by_target:
            targetable_features.append("featured_snippet")
        if serp.people_also_ask:
            targetable_features.append("paa")

        # Calculate winnability score (0-100)
        winnability = calculate_winnability(
            target_dr=target_dr,
            avg_serp_dr=avg_serp_dr,
            min_serp_dr=min_serp_dr,
            has_low_dr_rankings=has_low_dr_rankings,
            weak_content_signals=weak_content_signals,
            has_ai_overview=has_ai_overview,
            keyword_difficulty=kw.keyword_difficulty
        )

        # Calculate personalized difficulty
        personalized_kd = calculate_personalized_difficulty(
            base_kd=kw.keyword_difficulty,
            target_dr=target_dr,
            avg_serp_dr=avg_serp_dr
        )

        results.append(KeywordWithWinnability(
            **kw.dict(),
            avg_serp_dr=avg_serp_dr,
            min_serp_dr=min_serp_dr,
            has_low_dr_rankings=has_low_dr_rankings,
            weak_content_signals=weak_content_signals,
            has_ai_overview=has_ai_overview,
            targetable_features=targetable_features,
            winnability_score=winnability,
            personalized_difficulty=personalized_kd
        ))

    return results
```

### Phase G4: Market Opportunity Calculation

**Objective:** Size the total addressable market from competitor data.

```python
async def calculate_market_opportunity(
    competitors: List[ValidatedCompetitor],
    keyword_universe: KeywordUniverse
) -> MarketOpportunity:
    """
    Calculate total market opportunity from competitor landscape.

    Metrics:
    1. Total Addressable Market (TAM) - All search volume in universe
    2. Serviceable Addressable Market (SAM) - Keywords matching our offering
    3. Serviceable Obtainable Market (SOM) - Realistic capture based on winnability
    4. Competitor share distribution
    """

    # TAM: Total search volume
    tam_volume = sum(k.search_volume for k in keyword_universe.keywords)
    tam_keywords = len(keyword_universe.keywords)

    # SAM: Business-relevant keywords only
    sam_keywords = [k for k in keyword_universe.keywords if k.business_relevance >= 0.6]
    sam_volume = sum(k.search_volume for k in sam_keywords)

    # SOM: Winnable keywords (winnability > 50)
    som_keywords = [k for k in sam_keywords if k.winnability_score >= 50]
    som_volume = sum(k.search_volume for k in som_keywords)

    # Estimate traffic potential (using CTR curves)
    traffic_potential = estimate_traffic_from_rankings(
        keywords=som_keywords,
        target_positions={
            "90_day": 15,   # Avg position at 90 days
            "180_day": 8,   # Avg position at 180 days
            "365_day": 5    # Avg position at 365 days
        }
    )

    # Calculate competitor market share
    competitor_shares = []
    total_competitor_traffic = sum(c.organic_traffic for c in competitors)
    for comp in competitors:
        share = (comp.organic_traffic / total_competitor_traffic * 100) if total_competitor_traffic > 0 else 0
        competitor_shares.append(CompetitorShare(
            domain=comp.domain,
            traffic=comp.organic_traffic,
            share_percent=share,
            keyword_count=comp.organic_keywords
        ))

    return MarketOpportunity(
        tam=MarketSize(volume=tam_volume, keyword_count=tam_keywords),
        sam=MarketSize(volume=sam_volume, keyword_count=len(sam_keywords)),
        som=MarketSize(volume=som_volume, keyword_count=len(som_keywords)),
        traffic_potential=traffic_potential,
        competitor_shares=sorted(competitor_shares, key=lambda x: x.share_percent, reverse=True)
    )
```

---

## 5. Core Algorithms

### 5.1 Winnability Score

```python
def calculate_winnability(
    target_dr: int,
    avg_serp_dr: float,
    min_serp_dr: float,
    has_low_dr_rankings: bool,
    weak_content_signals: List[str],
    has_ai_overview: bool,
    keyword_difficulty: int
) -> float:
    """
    Calculate winnability score (0-100) for a keyword.

    Factors:
    - DR gap (your DR vs SERP average)
    - Low-DR presence (proof of concept)
    - Content quality gaps (exploitable weaknesses)
    - AI Overview (reduces organic opportunity)
    - Base keyword difficulty

    Higher score = more likely to rank.
    """
    score = 100.0

    # Factor 1: DR Gap (-40 points max)
    dr_gap = avg_serp_dr - target_dr
    if dr_gap > 0:
        # Penalize keywords where SERP DR is much higher
        penalty = min(40, dr_gap * 1.5)
        score -= penalty
    else:
        # Bonus if our DR exceeds SERP average
        bonus = min(10, abs(dr_gap) * 0.5)
        score += bonus

    # Factor 2: Low-DR Presence (+15 points)
    if has_low_dr_rankings:
        score += 15
        # Extra bonus if low-DR site is in top 5
        if min_serp_dr < target_dr:
            score += 5

    # Factor 3: Weak Content Signals (+5 points each, max 15)
    content_bonus = min(15, len(weak_content_signals) * 5)
    score += content_bonus

    # Factor 4: AI Overview (-20 points)
    if has_ai_overview:
        score -= 20

    # Factor 5: Base KD Adjustment (-0.3 per KD point above 30)
    if keyword_difficulty > 30:
        kd_penalty = (keyword_difficulty - 30) * 0.3
        score -= kd_penalty

    return max(0, min(100, score))
```

### 5.2 Personalized Keyword Difficulty

```python
def calculate_personalized_difficulty(
    base_kd: int,
    target_dr: int,
    avg_serp_dr: float
) -> float:
    """
    Calculate personalized keyword difficulty based on domain authority.

    Concept: KD 50 means something different for DR 10 vs DR 60 site.

    Formula:
    Personalized KD = Base KD × Authority Multiplier

    Where Authority Multiplier = 1 + (SERP_DR - Your_DR) / 100
    - If SERP DR > Your DR: difficulty increases
    - If SERP DR < Your DR: difficulty decreases
    """
    authority_gap = avg_serp_dr - target_dr
    authority_multiplier = 1 + (authority_gap / 100)

    # Clamp multiplier between 0.5 and 2.0
    authority_multiplier = max(0.5, min(2.0, authority_multiplier))

    personalized_kd = base_kd * authority_multiplier

    return min(100, max(0, personalized_kd))
```

### 5.3 Beachhead Keyword Selection

```python
def select_beachhead_keywords(
    keywords: List[KeywordWithWinnability],
    target_count: int = 20,
    max_kd: int = 30,
    min_volume: int = 100
) -> List[BeachheadKeyword]:
    """
    Select beachhead keywords: narrow, winnable cluster to establish dominance.

    Beachhead Criteria:
    1. Winnability score >= 70
    2. Personalized KD <= 30
    3. Search volume >= 100 (practical traffic)
    4. High business relevance
    5. Topically clustered (enables authority building)

    Strategy: Win these first, then expand outward.
    """

    # Filter candidates
    candidates = [
        k for k in keywords
        if k.winnability_score >= 70
        and k.personalized_difficulty <= max_kd
        and k.search_volume >= min_volume
        and k.business_relevance >= 0.7
    ]

    # Score by beachhead value
    for k in candidates:
        k.beachhead_score = calculate_beachhead_score(k)

    # Sort by beachhead score
    candidates.sort(key=lambda x: x.beachhead_score, reverse=True)

    # Cluster selection: prefer topically related keywords
    selected = []
    topic_clusters = cluster_by_topic(candidates)

    # Take keywords from top clusters to build authority
    for cluster in topic_clusters:
        cluster_keywords = sorted(
            cluster.keywords,
            key=lambda x: x.beachhead_score,
            reverse=True
        )[:5]  # Top 5 from each cluster
        selected.extend(cluster_keywords)

        if len(selected) >= target_count:
            break

    # Add beachhead metadata
    beachhead = []
    for kw in selected[:target_count]:
        beachhead.append(BeachheadKeyword(
            **kw.dict(),
            recommended_content_type=determine_content_type(kw),
            estimated_time_to_rank=estimate_time_to_rank(kw),
            priority=calculate_beachhead_priority(kw)
        ))

    return beachhead

def calculate_beachhead_score(kw: KeywordWithWinnability) -> float:
    """
    Calculate beachhead value score.

    Formula: (Volume × Business_Relevance × Winnability) / (Personalized_KD + 10)
    """
    numerator = kw.search_volume * kw.business_relevance * (kw.winnability_score / 100)
    denominator = kw.personalized_difficulty + 10
    return numerator / denominator
```

### 5.4 Traffic Projection Model

```python
def project_traffic_scenarios(
    beachhead_keywords: List[BeachheadKeyword],
    growth_keywords: List[KeywordWithWinnability],
    domain_maturity: DomainMaturity
) -> TrafficProjections:
    """
    Generate three-scenario traffic projections.

    Scenarios:
    - Conservative (70-80% confidence): Assumes headwinds, slower progress
    - Expected (50% confidence): Mid-range, standard timelines
    - Aggressive (20-30% confidence): Best case, everything goes well

    Based on:
    - Ahrefs data: Only 1.74% of new pages reach top 10 in year 1
    - AI Overview impact: 32% CTR reduction when present
    - Google Sandbox: 3-9 month trust-building period
    """

    # CTR curves by position (post-AI Overview era)
    CTR_CURVE = {
        1: 0.19,   # Down from 0.28 pre-AI
        2: 0.10,
        3: 0.07,
        4: 0.05,
        5: 0.04,
        6: 0.03,
        7: 0.025,
        8: 0.02,
        9: 0.018,
        10: 0.015
    }

    # AI Overview CTR penalty
    AI_OVERVIEW_MULTIPLIER = 0.16  # Only 16% of normal CTR

    # Ranking probability by month (for new domains)
    RANKING_PROBABILITY = {
        3: 0.05,   # 5% chance of ranking at month 3
        6: 0.15,   # 15% at month 6
        9: 0.30,   # 30% at month 9
        12: 0.50,  # 50% at month 12
        18: 0.70,  # 70% at month 18
        24: 0.85   # 85% at month 24
    }

    projections = {}

    for scenario, multiplier in [("conservative", 0.6), ("expected", 1.0), ("aggressive", 1.5)]:
        monthly_traffic = {}

        for month in [3, 6, 9, 12, 18, 24]:
            ranking_prob = RANKING_PROBABILITY[month] * multiplier

            # Beachhead keywords (easier, rank faster)
            beachhead_traffic = 0
            for kw in beachhead_keywords:
                # Expected position based on winnability
                expected_position = estimate_position_at_month(kw, month)
                ctr = CTR_CURVE.get(expected_position, 0.01)

                # Apply AI Overview penalty if present
                if kw.has_ai_overview:
                    ctr *= AI_OVERVIEW_MULTIPLIER

                # Traffic = Volume × CTR × Ranking Probability
                kw_traffic = kw.search_volume * ctr * ranking_prob
                beachhead_traffic += kw_traffic

            # Growth keywords (harder, rank slower)
            growth_traffic = 0
            growth_ranking_prob = ranking_prob * 0.5  # Harder keywords rank slower
            for kw in growth_keywords[:50]:  # Top 50 growth targets
                expected_position = estimate_position_at_month(kw, month) + 5  # Worse positions
                ctr = CTR_CURVE.get(expected_position, 0.005)

                if kw.has_ai_overview:
                    ctr *= AI_OVERVIEW_MULTIPLIER

                kw_traffic = kw.search_volume * ctr * growth_ranking_prob
                growth_traffic += kw_traffic

            monthly_traffic[month] = int(beachhead_traffic + growth_traffic)

        projections[scenario] = ScenarioProjection(
            traffic_by_month=monthly_traffic,
            confidence={"conservative": 0.75, "expected": 0.50, "aggressive": 0.25}[scenario]
        )

    return TrafficProjections(
        conservative=projections["conservative"],
        expected=projections["expected"],
        aggressive=projections["aggressive"]
    )
```

### 5.5 Growth Roadmap Generator

```python
def generate_growth_roadmap(
    beachhead_keywords: List[BeachheadKeyword],
    growth_keywords: List[KeywordWithWinnability],
    market_opportunity: MarketOpportunity,
    strategic_context: StrategicContext
) -> GrowthRoadmap:
    """
    Generate phased growth roadmap for greenfield domain.

    Phases:
    1. Foundation (Months 1-3): Technical + beachhead content
    2. Traction (Months 4-6): Long-tail wins + expansion
    3. Growth (Months 6-12): Medium difficulty + authority building
    4. Competitive (Year 2+): High-value keywords
    """

    phases = []

    # Phase 1: Foundation
    phase1_keywords = [k for k in beachhead_keywords if k.personalized_difficulty < 20][:10]
    phases.append(RoadmapPhase(
        name="Foundation",
        timeline="Months 1-3",
        focus="Establish technical baseline and create beachhead content",
        activities=[
            RoadmapActivity(
                category="Technical",
                action="Complete technical SEO audit and fixes",
                priority=1,
                effort="2-3 weeks"
            ),
            RoadmapActivity(
                category="Content",
                action=f"Create {len(phase1_keywords)} cornerstone content pieces",
                priority=1,
                effort="Ongoing",
                keywords=[k.keyword for k in phase1_keywords]
            ),
            RoadmapActivity(
                category="Indexing",
                action="Submit sitemap, request indexing, set up GSC",
                priority=1,
                effort="1 week"
            )
        ],
        expected_outcomes=[
            "Site fully indexed",
            "Technical health score > 80",
            f"{len(phase1_keywords)} content pieces published",
            "Beginning to see impressions in GSC"
        ],
        keywords=phase1_keywords,
        estimated_traffic="50-200/month"
    ))

    # Phase 2: Traction
    phase2_keywords = [k for k in beachhead_keywords if 20 <= k.personalized_difficulty < 35][:15]
    phases.append(RoadmapPhase(
        name="Early Traction",
        timeline="Months 4-6",
        focus="Win long-tail keywords and build topical clusters",
        activities=[
            RoadmapActivity(
                category="Content",
                action=f"Expand content to {len(phase2_keywords)} additional pieces",
                priority=1,
                effort="Ongoing",
                keywords=[k.keyword for k in phase2_keywords]
            ),
            RoadmapActivity(
                category="Authority",
                action="Build internal linking between related content",
                priority=2,
                effort="Ongoing"
            ),
            RoadmapActivity(
                category="Links",
                action="Begin outreach for 5-10 quality backlinks",
                priority=2,
                effort="Ongoing"
            )
        ],
        expected_outcomes=[
            "First page 1 rankings for long-tail terms",
            "Increasing GSC impressions and clicks",
            "5-10 referring domains acquired",
            "Topical clusters taking shape"
        ],
        keywords=phase2_keywords,
        estimated_traffic="500-1,500/month"
    ))

    # Phase 3: Growth
    phase3_keywords = [k for k in growth_keywords if k.personalized_difficulty < 50][:20]
    phases.append(RoadmapPhase(
        name="Growth",
        timeline="Months 6-12",
        focus="Scale content production and target medium-difficulty keywords",
        activities=[
            RoadmapActivity(
                category="Content",
                action=f"Target {len(phase3_keywords)} medium-difficulty keywords",
                priority=1,
                effort="Ongoing",
                keywords=[k.keyword for k in phase3_keywords]
            ),
            RoadmapActivity(
                category="Authority",
                action="Develop comprehensive pillar content",
                priority=1,
                effort="Ongoing"
            ),
            RoadmapActivity(
                category="Links",
                action="Scale link building to 10-20 links/month",
                priority=2,
                effort="Ongoing"
            ),
            RoadmapActivity(
                category="Optimization",
                action="Refresh and optimize early content based on performance",
                priority=2,
                effort="Monthly"
            )
        ],
        expected_outcomes=[
            "Top 10 rankings for beachhead keywords",
            "Top 20 positions for medium-difficulty terms",
            "Significant traffic growth visible",
            "30-50 referring domains"
        ],
        keywords=phase3_keywords,
        estimated_traffic="3,000-8,000/month"
    ))

    # Phase 4: Competitive
    phase4_keywords = [k for k in growth_keywords if k.personalized_difficulty >= 50][:15]
    phases.append(RoadmapPhase(
        name="Competitive Positioning",
        timeline="Year 2+",
        focus="Target high-value keywords and compete with established players",
        activities=[
            RoadmapActivity(
                category="Content",
                action=f"Create definitive content for {len(phase4_keywords)} competitive keywords",
                priority=1,
                effort="Ongoing",
                keywords=[k.keyword for k in phase4_keywords]
            ),
            RoadmapActivity(
                category="Authority",
                action="Pursue industry recognition, speaking, publications",
                priority=2,
                effort="Ongoing"
            ),
            RoadmapActivity(
                category="Links",
                action="Develop link-worthy assets (research, tools, data)",
                priority=2,
                effort="Quarterly"
            )
        ],
        expected_outcomes=[
            "Competing for high-value keywords",
            "Established topical authority",
            "Sustainable organic traffic channel",
            "100+ referring domains"
        ],
        keywords=phase4_keywords,
        estimated_traffic="10,000-25,000/month"
    ))

    return GrowthRoadmap(
        phases=phases,
        total_timeline="18-24 months to competitive positioning",
        market_opportunity=market_opportunity,
        success_metrics=define_success_metrics()
    )
```

---

## 6. Database Schema Changes

### New Tables

```python
class GreenfieldAnalysis(Base):
    """
    Greenfield analysis results - stored separately from standard analysis.
    """
    __tablename__ = "greenfield_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"))

    # Domain maturity classification
    maturity_classification = Column(String(20), nullable=False)  # greenfield, emerging
    domain_rating_at_analysis = Column(Integer)
    organic_keywords_at_analysis = Column(Integer)
    organic_traffic_at_analysis = Column(Integer)

    # User-provided context
    greenfield_context = Column(JSONB, nullable=False)  # GreenfieldContext
    strategic_context = Column(JSONB)  # StrategicContext

    # Competitor discovery results
    discovered_competitors = Column(JSONB, default=[])  # List of validated competitors
    competitor_count = Column(Integer)

    # Market opportunity
    market_opportunity = Column(JSONB)  # MarketOpportunity
    tam_volume = Column(Integer)
    sam_volume = Column(Integer)
    som_volume = Column(Integer)

    # Keyword universe stats
    total_keywords_discovered = Column(Integer)
    beachhead_keyword_count = Column(Integer)
    growth_keyword_count = Column(Integer)

    # Projections
    traffic_projections = Column(JSONB)  # TrafficProjections
    growth_roadmap = Column(JSONB)  # GrowthRoadmap

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_greenfield_domain", "domain_id", "created_at"),
    )


class KeywordWinnability(Base):
    """
    SERP-based winnability analysis for keywords.
    """
    __tablename__ = "keyword_winnability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey("keywords.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    # SERP composition
    avg_serp_dr = Column(Float)
    min_serp_dr = Column(Float)
    max_serp_dr = Column(Float)
    has_low_dr_rankings = Column(Boolean, default=False)
    low_dr_positions = Column(JSONB, default=[])  # Positions where DR < 30 ranks

    # Content quality signals
    outdated_content_count = Column(Integer, default=0)
    thin_content_count = Column(Integer, default=0)
    weak_content_signals = Column(JSONB, default=[])

    # SERP features
    has_ai_overview = Column(Boolean, default=False)
    has_featured_snippet = Column(Boolean, default=False)
    featured_snippet_owner = Column(String(255))
    targetable_features = Column(JSONB, default=[])

    # Calculated scores
    winnability_score = Column(Float)  # 0-100
    personalized_difficulty = Column(Float)  # Adjusted KD

    # Beachhead classification
    is_beachhead_candidate = Column(Boolean, default=False)
    beachhead_score = Column(Float)
    beachhead_priority = Column(Integer)  # 1-5

    # Timestamps
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_winnability_keyword", "keyword_id"),
        Index("idx_winnability_score", "analysis_run_id", "winnability_score"),
        Index("idx_beachhead", "analysis_run_id", "is_beachhead_candidate", "beachhead_score"),
    )


class CompetitorKeyword(Base):
    """
    Keywords discovered from competitor analysis.
    """
    __tablename__ = "competitor_keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Keyword data
    keyword = Column(String(500), nullable=False)
    keyword_normalized = Column(String(500))

    # Metrics
    search_volume = Column(Integer)
    keyword_difficulty = Column(Integer)
    cpc = Column(Float)
    search_intent = Column(Enum(SearchIntent))

    # Source tracking
    source_competitor = Column(String(255))
    source_position = Column(Integer)  # Where competitor ranks
    discovered_from = Column(String(50))  # competitor_organic, competitor_ppc, expansion, related

    # Business relevance
    business_relevance = Column(Float)  # 0-1

    # Multiple competitor tracking
    competitor_count = Column(Integer)  # How many competitors rank for this
    competitor_positions = Column(JSONB, default={})  # {domain: position}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_comp_keyword_analysis", "analysis_run_id", "search_volume"),
        Index("idx_comp_keyword_relevance", "analysis_run_id", "business_relevance"),
    )
```

### Schema Additions to Existing Tables

```python
# Add to Keyword table
class Keyword(Base):
    # ... existing fields ...

    # Winnability fields
    winnability_score = Column(Float)  # 0-100
    personalized_difficulty = Column(Float)  # Adjusted KD for this domain
    is_beachhead = Column(Boolean, default=False)
    beachhead_priority = Column(Integer)  # 1-5

    # SERP composition cache
    serp_avg_dr = Column(Float)
    serp_min_dr = Column(Float)
    has_ai_overview = Column(Boolean)

    # Business relevance
    business_relevance = Column(Float)  # 0-1, for greenfield prioritization


# Add to AnalysisRun table
class AnalysisRun(Base):
    # ... existing fields ...

    # Greenfield mode flag
    analysis_mode = Column(String(20), default="standard")  # standard, greenfield, hybrid

    # Market opportunity summary (for greenfield)
    tam_volume = Column(Integer)
    sam_volume = Column(Integer)
    som_volume = Column(Integer)
```

---

## 7. API Endpoints

### Greenfield Analysis Endpoints

```python
# api/greenfield.py

router = APIRouter(prefix="/api/greenfield", tags=["Greenfield Analysis"])


@router.post("/analyze")
async def start_greenfield_analysis(
    request: GreenfieldAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> GreenfieldAnalysisResponse:
    """
    Start greenfield analysis for a new domain.

    Required inputs:
    - domain: Target domain (even if new)
    - business_name, business_description, primary_offering
    - target_market, target_language, industry_vertical
    - seed_keywords: List of 5-10 core keywords
    - known_competitors: List of 3-5 known competitor domains

    Returns analysis_id for tracking progress.
    """
    pass


@router.get("/analysis/{analysis_id}/status")
async def get_greenfield_status(
    analysis_id: UUID,
    db: Session = Depends(get_db)
) -> GreenfieldStatusResponse:
    """Get status of greenfield analysis."""
    pass


@router.get("/analysis/{analysis_id}/market-opportunity")
async def get_market_opportunity(
    analysis_id: UUID,
    db: Session = Depends(get_db)
) -> MarketOpportunityResponse:
    """
    Get market opportunity analysis.

    Returns:
    - TAM/SAM/SOM sizing
    - Competitor market share distribution
    - Total keyword universe stats
    - Traffic potential estimates
    """
    pass


@router.get("/analysis/{analysis_id}/beachhead-keywords")
async def get_beachhead_keywords(
    analysis_id: UUID,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
) -> BeachheadKeywordsResponse:
    """
    Get beachhead keyword recommendations.

    Returns keywords that are:
    - High winnability (>70)
    - Low personalized difficulty (<30)
    - Good search volume (>100)
    - High business relevance (>0.7)

    Includes:
    - Recommended content type
    - Estimated time to rank
    - Priority score
    - SERP composition details
    """
    pass


@router.get("/analysis/{analysis_id}/growth-keywords")
async def get_growth_keywords(
    analysis_id: UUID,
    phase: str = Query("all", regex="^(all|phase2|phase3|phase4)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
) -> GrowthKeywordsResponse:
    """
    Get growth keywords beyond beachhead.

    Phases:
    - phase2: Medium-easy (personalized KD 20-35)
    - phase3: Medium (personalized KD 35-50)
    - phase4: Competitive (personalized KD 50+)
    """
    pass


@router.get("/analysis/{analysis_id}/competitors")
async def get_competitor_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db)
) -> CompetitorAnalysisResponse:
    """
    Get detailed competitor analysis.

    For each competitor:
    - Domain metrics (DR, traffic, keywords)
    - Top keywords they rank for
    - Their market share
    - Content gaps vs them
    - Backlink profile summary
    """
    pass


@router.get("/analysis/{analysis_id}/traffic-projections")
async def get_traffic_projections(
    analysis_id: UUID,
    db: Session = Depends(get_db)
) -> TrafficProjectionsResponse:
    """
    Get three-scenario traffic projections.

    Returns:
    - Conservative (75% confidence)
    - Expected (50% confidence)
    - Aggressive (25% confidence)

    Each with monthly traffic estimates for months 3, 6, 9, 12, 18, 24.
    """
    pass


@router.get("/analysis/{analysis_id}/growth-roadmap")
async def get_growth_roadmap(
    analysis_id: UUID,
    db: Session = Depends(get_db)
) -> GrowthRoadmapResponse:
    """
    Get phased growth roadmap.

    Returns:
    - Phase 1: Foundation (months 1-3)
    - Phase 2: Traction (months 4-6)
    - Phase 3: Growth (months 6-12)
    - Phase 4: Competitive (year 2+)

    Each phase includes:
    - Timeline
    - Activities with priorities
    - Target keywords
    - Expected outcomes
    - Estimated traffic
    """
    pass


@router.get("/analysis/{analysis_id}/keyword-universe")
async def get_keyword_universe(
    analysis_id: UUID,
    cursor: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("opportunity", regex="^(opportunity|volume|difficulty|winnability)$"),
    min_winnability: Optional[int] = None,
    max_difficulty: Optional[int] = None,
    intent: Optional[str] = None,
    db: Session = Depends(get_db)
) -> KeywordUniverseResponse:
    """
    Get full keyword universe with filtering.

    Supports:
    - Cursor pagination
    - Sorting by opportunity, volume, difficulty, winnability
    - Filtering by winnability, difficulty, intent
    """
    pass
```

### Dashboard Integration Endpoints

```python
# Add to api/dashboard.py

@router.get("/{domain_id}/market-opportunity", response_model=MarketOpportunityResponse)
async def get_dashboard_market_opportunity(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> MarketOpportunityResponse:
    """
    Get market opportunity for dashboard.

    For greenfield domains: Full market sizing
    For established domains: Remaining opportunity vs current capture
    """
    pass


@router.get("/{domain_id}/beachhead", response_model=BeachheadResponse)
async def get_dashboard_beachhead(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> BeachheadResponse:
    """
    Get beachhead keywords for dashboard.

    Returns top 20 beachhead opportunities with:
    - Winnability scores
    - SERP composition
    - Recommended actions
    """
    pass


@router.get("/{domain_id}/growth-roadmap", response_model=GrowthRoadmapResponse)
async def get_dashboard_roadmap(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> GrowthRoadmapResponse:
    """
    Get growth roadmap for dashboard.

    Includes current phase indicator based on domain metrics.
    """
    pass
```

---

## 8. Frontend Requirements

### Greenfield Analysis Flow

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ NEW ANALYSIS                                                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  We detected this is a new domain (DR: 5, Keywords: 12)                        │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ 💡 For new domains, we use Competitor-First Analysis                    │   │
│  │                                                                         │   │
│  │ Instead of analyzing your (limited) data, we'll:                        │   │
│  │ • Discover and analyze your competitors                                 │   │
│  │ • Size the total market opportunity                                     │   │
│  │ • Find "beachhead" keywords you can win quickly                         │   │
│  │ • Create a phased growth roadmap                                        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  To begin, we need to understand your business:                                │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1 OF 4: Business Context                                           │   │
│  │                                                                         │   │
│  │ Business Name *                                                         │   │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │   │
│  │ │ Acme Project Tools                                                  │ │   │
│  │ └─────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                         │   │
│  │ What does your business do? (2-3 sentences) *                           │   │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │   │
│  │ │ We build project management software for creative agencies.         │ │   │
│  │ │ Our tool helps teams track projects, manage resources, and          │ │   │
│  │ │ collaborate with clients in real-time.                              │ │   │
│  │ └─────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                         │   │
│  │ Primary product/service *                                               │   │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │   │
│  │ │ Project management software for agencies                            │ │   │
│  │ └─────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                         │   │
│  │ Industry *                                                              │   │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │   │
│  │ │ SaaS / Software                                                   ▼ │ │   │
│  │ └─────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                         │   │
│  │                                               [Next: Seed Keywords →]   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Market Opportunity Dashboard

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ MARKET OPPORTUNITY                                          acme-tools.com     │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ THE OPPORTUNITY                                                          │   │
│  │                                                                         │   │
│  │ ┌───────────────┐   ┌───────────────┐   ┌───────────────┐              │   │
│  │ │ TAM           │   │ SAM           │   │ SOM           │              │   │
│  │ │ Total Market  │   │ Serviceable   │   │ Obtainable    │              │   │
│  │ │               │   │               │   │               │              │   │
│  │ │ 2.4M          │   │ 890K          │   │ 156K          │              │   │
│  │ │ monthly       │   │ monthly       │   │ monthly       │              │   │
│  │ │ searches      │   │ searches      │   │ searches      │              │   │
│  │ │               │   │               │   │               │              │   │
│  │ │ 8,432 kws     │   │ 2,156 kws     │   │ 342 kws       │              │   │
│  │ └───────────────┘   └───────────────┘   └───────────────┘              │   │
│  │                                                                         │   │
│  │ SOM represents keywords where you have >50% winnability                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ COMPETITOR MARKET SHARE                                                 │   │
│  │                                                                         │   │
│  │ monday.com        ████████████████████████████████  28%    125K/mo     │   │
│  │ asana.com         ██████████████████████████        23%    103K/mo     │   │
│  │ clickup.com       ████████████████████              18%     81K/mo     │   │
│  │ teamwork.com      ████████████                      11%     49K/mo     │   │
│  │ wrike.com         ██████████                         9%     40K/mo     │   │
│  │ Others            ████████████                      11%     50K/mo     │   │
│  │                                                                         │   │
│  │ YOUR OPPORTUNITY  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%      0K/mo     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ TRAFFIC PROJECTIONS                                                     │   │
│  │                                                                         │   │
│  │      │                                              ╱ Aggressive        │   │
│  │ 25K  │                                           ╱                      │   │
│  │      │                                        ╱     ╱ Expected          │   │
│  │ 20K  │                                     ╱     ╱                      │   │
│  │      │                                  ╱     ╱                         │   │
│  │ 15K  │                               ╱     ╱        ╱ Conservative      │   │
│  │      │                            ╱     ╱        ╱                      │   │
│  │ 10K  │                         ╱     ╱        ╱                         │   │
│  │      │                      ╱     ╱        ╱                            │   │
│  │  5K  │                   ╱     ╱        ╱                               │   │
│  │      │      ___------╱     ╱        ╱                                   │   │
│  │   0  ├───────────────────────────────────────────────────              │   │
│  │      Mo3   Mo6   Mo9   Mo12  Mo18  Mo24                                │   │
│  │                                                                         │   │
│  │ Conservative (75% confidence): 8,000/mo at month 24                    │   │
│  │ Expected (50% confidence): 15,000/mo at month 24                       │   │
│  │ Aggressive (25% confidence): 25,000/mo at month 24                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Beachhead Keywords View

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ BEACHHEAD KEYWORDS                                    Your Starting Points     │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  These 23 keywords are your entry point to this market.                        │
│  Win these first, then expand outward.                                         │
│                                                                                 │
│  Selection criteria: Winnability >70 • Personalized KD <30 • Volume >100      │
│                                                                                 │
│ ┌────────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                            │ │
│ │ Keyword                    │Volume│ KD │P.KD│Win │SERP │Time  │Priority   │ │
│ ├────────────────────────────────────────────────────────────────────────────┤ │
│ │ agency project management  │ 1,200│ 24 │ 18 │ 85 │DR:22│ 8wk │ ⚡ P1      │ │
│ │   └ SERP has DR 15 site at #4 • Outdated content at #2                    │ │
│ │                                                                            │ │
│ │ creative agency workflow   │   890│ 21 │ 16 │ 82 │DR:25│ 8wk │ ⚡ P1      │ │
│ │   └ Featured snippet available • No AI Overview                           │ │
│ │                                                                            │ │
│ │ project management for     │   720│ 28 │ 22 │ 79 │DR:28│10wk │ ⚡ P1      │ │
│ │ design teams                                                               │ │
│ │   └ Thin content at #3 and #5 • PAA opportunity                           │ │
│ │                                                                            │ │
│ │ agency resource planning   │   650│ 22 │ 17 │ 78 │DR:24│ 8wk │    P2      │ │
│ │   └ Reddit ranking at #6 indicates weak competition                       │ │
│ │                                                                            │ │
│ │ client project portal      │   580│ 26 │ 21 │ 76 │DR:27│10wk │    P2      │ │
│ │                                                                            │ │
│ │ ... 18 more beachhead keywords                                            │ │
│ │                                                                            │ │
│ └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  Legend:                                                                        │
│  KD = Base Keyword Difficulty • P.KD = Personalized (adjusted for your DR)    │
│  Win = Winnability Score • SERP = Average DR of top 10 • Time = Est. to rank  │
│                                                                                 │
│                                          [Add All to Strategy] [Export CSV]    │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Growth Roadmap View

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ GROWTH ROADMAP                                         18-24 Month Journey     │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ══════════════════════════════════════════════════════════════════════════   │
│  │ FOUNDATION ││ TRACTION  ││   GROWTH    ││     COMPETITIVE      │           │
│  │  Months 1-3 ││ Months 4-6 ││ Months 6-12 ││      Year 2+        │           │
│  ══════════════════════════════════════════════════════════════════════════   │
│        ▲                                                                        │
│    YOU ARE HERE                                                                 │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: FOUNDATION                                       Months 1-3    │   │
│  │                                                                         │   │
│  │ Focus: Establish technical baseline and create beachhead content        │   │
│  │                                                                         │   │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │   │
│  │ │ ACTIVITIES                                                          │ │   │
│  │ │                                                                     │ │   │
│  │ │ ⚡ P1  Technical SEO audit and fixes                    2-3 weeks   │ │   │
│  │ │        Crawlability, indexing, site speed, mobile                  │ │   │
│  │ │                                                                     │ │   │
│  │ │ ⚡ P1  Create 10 cornerstone content pieces             Ongoing     │ │   │
│  │ │        Targeting beachhead keywords (see list below)               │ │   │
│  │ │                                                                     │ │   │
│  │ │    P2  Set up tracking: GSC, Analytics, rank tracking   1 week     │ │   │
│  │ │                                                                     │ │   │
│  │ │    P2  Initial backlink outreach (5-10 links)           Ongoing    │ │   │
│  │ └─────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                         │   │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │   │
│  │ │ TARGET KEYWORDS (10)                                                │ │   │
│  │ │                                                                     │ │   │
│  │ │ agency project management (1,200 vol) • creative agency workflow   │ │   │
│  │ │ (890 vol) • project management for design teams (720 vol) •        │ │   │
│  │ │ agency resource planning (650 vol) • + 6 more                      │ │   │
│  │ └─────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                         │   │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │   │
│  │ │ EXPECTED OUTCOMES                                                   │ │   │
│  │ │                                                                     │ │   │
│  │ │ ✓ Site fully indexed in Google                                     │ │   │
│  │ │ ✓ Technical health score > 80                                      │ │   │
│  │ │ ✓ 10 content pieces published                                      │ │   │
│  │ │ ✓ Beginning to see impressions in GSC                              │ │   │
│  │ │ ✓ Estimated traffic: 50-200/month                                  │ │   │
│  │ └─────────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  [Expand Phase 2] [Expand Phase 3] [Expand Phase 4]                            │
│                                                                                 │
│                                                        [Export Full Roadmap]   │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Integration Points

### With Existing Collection Pipeline

```python
# In orchestrator.py

async def collect_all(self, config: CollectionConfig) -> CollectionResult:
    """Execute collection based on domain maturity."""

    # Step 1: Fetch domain metrics
    foundation = await collect_foundation_data(...)

    # Step 2: Classify domain maturity
    maturity = classify_domain_maturity(DomainMetrics(
        domain_rating=foundation.get("domain_overview", {}).get("rank", 0),
        organic_keywords=foundation.get("domain_overview", {}).get("organic_keywords", 0),
        organic_traffic=foundation.get("domain_overview", {}).get("organic_traffic", 0),
        referring_domains=foundation.get("backlink_summary", {}).get("referring_domains", 0)
    ))

    # Step 3: Route based on maturity
    if maturity == DomainMaturity.GREENFIELD:
        # Require greenfield context
        if not config.greenfield_context:
            raise ValueError("Greenfield analysis requires business context input")

        return await self._collect_greenfield(config)

    elif maturity == DomainMaturity.EMERGING:
        # Hybrid: domain data + competitor supplementation
        return await self._collect_hybrid(config, foundation)

    else:
        # Standard domain-centric collection
        return await self._collect_standard(config, foundation)
```

### With Strategy Builder

```python
# Beachhead keywords automatically suggested as first thread

async def suggest_initial_threads(
    analysis_run_id: UUID,
    db: Session
) -> List[SuggestedThread]:
    """
    Suggest initial threads based on analysis type.

    For greenfield: Suggest beachhead keyword cluster as first thread
    For established: Suggest based on opportunity score
    """

    analysis = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_run_id).first()

    if analysis.analysis_mode == "greenfield":
        # Get beachhead keywords
        beachhead = db.query(Keyword).filter(
            Keyword.analysis_run_id == analysis_run_id,
            Keyword.is_beachhead == True
        ).order_by(desc(Keyword.beachhead_priority)).all()

        # Cluster beachhead keywords by topic
        clusters = cluster_by_parent_topic(beachhead)

        suggestions = []
        for cluster in clusters[:5]:
            suggestions.append(SuggestedThread(
                name=f"Beachhead: {cluster.name}",
                description=f"Quick-win keywords in {cluster.name}",
                keywords=cluster.keywords,
                priority=1,
                recommended=True,
                reason="High winnability, low difficulty - start here"
            ))

        return suggestions

    # Standard suggestions for established domains
    return await suggest_standard_threads(analysis_run_id, db)
```

### With Dashboard

```python
# Dashboard detects domain maturity and shows appropriate views

@router.get("/{domain_id}/overview")
async def get_dashboard_overview(domain_id: UUID, db: Session = Depends(get_db)):
    """Get overview based on domain maturity."""

    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    analysis = get_latest_analysis(domain_id, db)

    if analysis.analysis_mode == "greenfield":
        # Return greenfield-specific overview
        return GreenfieldOverviewResponse(
            domain=domain.domain,
            maturity="greenfield",
            market_opportunity=get_market_opportunity(analysis.id, db),
            beachhead_count=count_beachhead_keywords(analysis.id, db),
            current_phase=determine_current_phase(domain, analysis),
            traffic_projections=get_traffic_projections(analysis.id, db),
            # ... greenfield-specific metrics
        )

    # Standard overview for established domains
    return StandardOverviewResponse(...)
```

---

## 10. Success Metrics

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Greenfield analysis completion rate | >90% | Analyses started vs completed |
| User satisfaction (greenfield) | >4.5/5 | Post-analysis survey |
| Conversion: greenfield → strategy | >60% | Created strategy after analysis |
| Retention: greenfield users | >70% at 6mo | Active after 6 months |
| Expansion revenue | >20% | Greenfield users upgrading |

### Product Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to first insight | <10 min | From input to market opportunity display |
| Beachhead keyword accuracy | >70% | Keywords that achieve top 20 within 6 months |
| Traffic projection accuracy | Within 30% | Actual vs projected at month 12 |
| Roadmap milestone completion | >60% | Users completing phase 1 activities |

### Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Greenfield collection time | <15 min | Total pipeline duration |
| API reliability | >99.5% | Successful requests |
| SERP analysis coverage | >80% | Keywords with winnability scores |

---

## 11. Implementation Phases

### Phase 1: Foundation (2 weeks)

**Goal:** Basic greenfield detection and routing

- [ ] Implement `classify_domain_maturity()` function
- [ ] Add maturity classification to `AnalysisRun` model
- [ ] Create greenfield context input schema
- [ ] Add greenfield flag to collection pipeline
- [ ] Basic routing based on maturity

**Deliverable:** System correctly identifies and flags greenfield domains

### Phase 2: Competitor Discovery (2 weeks)

**Goal:** Build competitor universe without domain data

- [ ] Implement `discover_competitors_greenfield()`
- [ ] Add SERP-based competitor extraction
- [ ] Create competitor validation logic
- [ ] Store validated competitors in database
- [ ] API endpoint: `/api/greenfield/analysis/{id}/competitors`

**Deliverable:** Accurate competitor discovery from seed keywords

### Phase 3: Keyword Universe (2 weeks)

**Goal:** Build complete keyword universe from competitors

- [ ] Implement `build_keyword_universe_greenfield()`
- [ ] Add competitor keyword mining
- [ ] Implement keyword expansion from seeds
- [ ] Add intent classification
- [ ] Add business relevance scoring
- [ ] Database: `CompetitorKeyword` table
- [ ] API endpoint: `/api/greenfield/analysis/{id}/keyword-universe`

**Deliverable:** Complete keyword universe with 1000+ keywords

### Phase 4: Winnability Analysis (2 weeks)

**Goal:** SERP-based winnability scoring

- [ ] Implement `analyze_serp_winnability()`
- [ ] Calculate `winnability_score` for keywords
- [ ] Calculate `personalized_difficulty`
- [ ] Identify beachhead candidates
- [ ] Database: `KeywordWinnability` table
- [ ] API endpoint: `/api/greenfield/analysis/{id}/beachhead-keywords`

**Deliverable:** Winnability scores and beachhead recommendations

### Phase 5: Market Opportunity (1 week)

**Goal:** Size the market from competitor data

- [ ] Implement `calculate_market_opportunity()`
- [ ] Calculate TAM/SAM/SOM
- [ ] Calculate competitor market share
- [ ] Database: Store in `GreenfieldAnalysis`
- [ ] API endpoint: `/api/greenfield/analysis/{id}/market-opportunity`

**Deliverable:** Complete market sizing with competitor breakdown

### Phase 6: Projections & Roadmap (2 weeks)

**Goal:** Traffic projections and growth roadmap

- [ ] Implement `project_traffic_scenarios()`
- [ ] Implement `generate_growth_roadmap()`
- [ ] Create three-scenario projection model
- [ ] Create phased roadmap generator
- [ ] API endpoints: `/traffic-projections`, `/growth-roadmap`

**Deliverable:** Actionable projections and phased recommendations

### Phase 7: Frontend Integration (3 weeks)

**Goal:** Complete greenfield UI

- [ ] Greenfield analysis wizard (4-step input)
- [ ] Market opportunity dashboard view
- [ ] Beachhead keywords view
- [ ] Growth roadmap view
- [ ] Traffic projections chart
- [ ] Integration with Strategy Builder

**Deliverable:** Complete greenfield user experience

### Phase 8: Testing & Refinement (2 weeks)

**Goal:** Validate accuracy and refine

- [ ] Test with 20+ real greenfield domains
- [ ] Validate beachhead keyword recommendations
- [ ] Refine winnability algorithm based on results
- [ ] Adjust projection model based on feedback
- [ ] Performance optimization

**Deliverable:** Production-ready greenfield capability

---

## Appendix A: Example Analysis Output

### Input

```json
{
  "domain": "acme-agency-tools.com",
  "greenfield_context": {
    "business_name": "Acme Agency Tools",
    "business_description": "Project management software built specifically for creative agencies. Helps teams track projects, manage resources, and collaborate with clients.",
    "primary_offering": "Project management software for agencies",
    "target_market": "United States",
    "target_language": "English",
    "industry_vertical": "SaaS",
    "seed_keywords": [
      "agency project management",
      "creative project management software",
      "client project portal",
      "agency resource planning",
      "project management for agencies"
    ],
    "known_competitors": [
      "monday.com",
      "asana.com",
      "teamwork.com",
      "clickup.com"
    ]
  }
}
```

### Output Summary

```json
{
  "maturity_classification": "greenfield",
  "market_opportunity": {
    "tam": {
      "volume": 2400000,
      "keyword_count": 8432
    },
    "sam": {
      "volume": 890000,
      "keyword_count": 2156
    },
    "som": {
      "volume": 156000,
      "keyword_count": 342
    },
    "competitor_shares": [
      {"domain": "monday.com", "share_percent": 28, "traffic": 125000},
      {"domain": "asana.com", "share_percent": 23, "traffic": 103000},
      {"domain": "clickup.com", "share_percent": 18, "traffic": 81000},
      {"domain": "teamwork.com", "share_percent": 11, "traffic": 49000}
    ]
  },
  "beachhead_keywords": [
    {
      "keyword": "agency project management",
      "volume": 1200,
      "base_kd": 24,
      "personalized_kd": 18,
      "winnability_score": 85,
      "serp_avg_dr": 22,
      "has_ai_overview": false,
      "estimated_time_to_rank": "8 weeks",
      "priority": 1
    }
  ],
  "traffic_projections": {
    "conservative": {
      "month_12": 3000,
      "month_24": 8000,
      "confidence": 0.75
    },
    "expected": {
      "month_12": 5000,
      "month_24": 15000,
      "confidence": 0.50
    },
    "aggressive": {
      "month_12": 8000,
      "month_24": 25000,
      "confidence": 0.25
    }
  },
  "growth_roadmap": {
    "phases": [
      {
        "name": "Foundation",
        "timeline": "Months 1-3",
        "keyword_count": 10,
        "estimated_traffic": "50-200/month"
      },
      {
        "name": "Early Traction",
        "timeline": "Months 4-6",
        "keyword_count": 15,
        "estimated_traffic": "500-1500/month"
      },
      {
        "name": "Growth",
        "timeline": "Months 6-12",
        "keyword_count": 20,
        "estimated_traffic": "3000-8000/month"
      },
      {
        "name": "Competitive",
        "timeline": "Year 2+",
        "keyword_count": 15,
        "estimated_traffic": "10000-25000/month"
      }
    ]
  }
}
```

---

**End of Brief**

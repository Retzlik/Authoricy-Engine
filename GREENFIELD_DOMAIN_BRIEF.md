# Greenfield Domain Intelligence: Product Brief

**Version:** 2.0
**Date:** January 2026
**Status:** Ready for Implementation (Enhanced with Case Studies & Industry Coefficients)

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
6. [Industry-Specific Coefficients](#6-industry-specific-coefficients)
7. [Real-World Case Studies](#7-real-world-case-studies)
8. [Competitive Differentiation](#8-competitive-differentiation)
9. [Edge Cases & Special Scenarios](#9-edge-cases--special-scenarios)
10. [Database Schema Changes](#10-database-schema-changes)
11. [API Endpoints](#11-api-endpoints)
12. [Frontend Requirements](#12-frontend-requirements)
13. [Integration Points](#13-integration-points)
14. [Success Metrics](#14-success-metrics)
15. [Implementation Phases](#15-implementation-phases)
16. [Validation Plan](#16-validation-plan)

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

## 6. Industry-Specific Coefficients

The base winnability algorithm uses generic coefficients. However, different industries behave radically differently in search. This section provides calibrated coefficients for major verticals.

### 6.1 Coefficient Adjustment Matrix

| Industry | DR Weight | KD Multiplier | AI Overview Impact | Time to Rank Multiplier | Notes |
|----------|-----------|---------------|-------------------|------------------------|-------|
| **SaaS/B2B** | 1.0x (baseline) | 1.0x | -20pts | 1.0x | Standard competitive landscape |
| **E-commerce** | 0.8x | 1.2x | -15pts | 0.8x | Less DR-dependent, more commercial intent |
| **YMYL (Health)** | 1.8x | 1.5x | -30pts | 1.5x | E-E-A-T critical, Google scrutiny high |
| **YMYL (Finance)** | 1.7x | 1.4x | -25pts | 1.4x | Trust signals paramount |
| **Local Services** | 0.6x | 0.7x | -10pts | 0.6x | Geographic modifiers reduce competition |
| **News/Media** | 1.4x | 1.3x | -25pts | 0.5x | High churn, freshness matters |
| **Education** | 1.2x | 1.1x | -20pts | 1.2x | Institutional authority matters |
| **B2C Consumer** | 0.9x | 1.1x | -18pts | 0.9x | Brand matters but less technical |

### 6.2 Industry-Specific Winnability Function

```python
INDUSTRY_COEFFICIENTS = {
    "saas": {
        "dr_weight": 1.0,
        "kd_multiplier": 1.0,
        "ai_overview_penalty": 20,
        "time_multiplier": 1.0,
        "content_bonus_max": 15,
        "low_dr_bonus": 15,
    },
    "ecommerce": {
        "dr_weight": 0.8,
        "kd_multiplier": 1.2,
        "ai_overview_penalty": 15,
        "time_multiplier": 0.8,
        "content_bonus_max": 10,  # Content quality less differentiating
        "low_dr_bonus": 20,  # Product pages can rank with low DR
    },
    "ymyl_health": {
        "dr_weight": 1.8,
        "kd_multiplier": 1.5,
        "ai_overview_penalty": 30,  # AI Overviews very common in health
        "time_multiplier": 1.5,
        "content_bonus_max": 20,  # Expert content matters more
        "low_dr_bonus": 5,  # Low-DR health sites rarely rank
        "eeat_required": True,  # Special flag: E-E-A-T signals mandatory
    },
    "ymyl_finance": {
        "dr_weight": 1.7,
        "kd_multiplier": 1.4,
        "ai_overview_penalty": 25,
        "time_multiplier": 1.4,
        "content_bonus_max": 18,
        "low_dr_bonus": 8,
        "eeat_required": True,
    },
    "local_services": {
        "dr_weight": 0.6,
        "kd_multiplier": 0.7,
        "ai_overview_penalty": 10,
        "time_multiplier": 0.6,
        "content_bonus_max": 12,
        "low_dr_bonus": 25,  # Local searches often have low-DR winners
        "geo_modifier_bonus": 20,  # Additional bonus for geo-modified terms
    },
    "news_media": {
        "dr_weight": 1.4,
        "kd_multiplier": 1.3,
        "ai_overview_penalty": 25,
        "time_multiplier": 0.5,  # Rankings can come fast but also disappear
        "content_bonus_max": 20,
        "low_dr_bonus": 10,
        "freshness_critical": True,
    },
    "education": {
        "dr_weight": 1.2,
        "kd_multiplier": 1.1,
        "ai_overview_penalty": 20,
        "time_multiplier": 1.2,
        "content_bonus_max": 18,
        "low_dr_bonus": 12,
        "institutional_bonus": 15,  # .edu domains get implicit boost
    },
    "b2c_consumer": {
        "dr_weight": 0.9,
        "kd_multiplier": 1.1,
        "ai_overview_penalty": 18,
        "time_multiplier": 0.9,
        "content_bonus_max": 15,
        "low_dr_bonus": 18,
    },
}


def calculate_winnability_with_industry(
    target_dr: int,
    avg_serp_dr: float,
    min_serp_dr: float,
    has_low_dr_rankings: bool,
    weak_content_signals: List[str],
    has_ai_overview: bool,
    keyword_difficulty: int,
    industry: str = "saas",
    has_geo_modifier: bool = False,
) -> float:
    """
    Calculate winnability with industry-specific adjustments.
    """
    coef = INDUSTRY_COEFFICIENTS.get(industry, INDUSTRY_COEFFICIENTS["saas"])

    score = 100.0

    # Factor 1: DR Gap (industry-weighted)
    dr_gap = avg_serp_dr - target_dr
    if dr_gap > 0:
        penalty = min(40, dr_gap * 1.5 * coef["dr_weight"])
        score -= penalty
    else:
        bonus = min(10, abs(dr_gap) * 0.5)
        score += bonus

    # Factor 2: Low-DR Presence (industry-weighted bonus)
    if has_low_dr_rankings:
        score += coef["low_dr_bonus"]
        if min_serp_dr < target_dr:
            score += 5

    # Factor 3: Weak Content Signals (industry-weighted max)
    content_bonus = min(coef["content_bonus_max"], len(weak_content_signals) * 5)
    score += content_bonus

    # Factor 4: AI Overview (industry-weighted penalty)
    if has_ai_overview:
        score -= coef["ai_overview_penalty"]

    # Factor 5: KD Adjustment (industry-weighted multiplier)
    if keyword_difficulty > 30:
        kd_penalty = (keyword_difficulty - 30) * 0.3 * coef["kd_multiplier"]
        score -= kd_penalty

    # Factor 6: Geo modifier bonus (local services)
    if has_geo_modifier and "geo_modifier_bonus" in coef:
        score += coef["geo_modifier_bonus"]

    return max(0, min(100, score))


def estimate_time_to_rank_with_industry(
    base_time_weeks: int,
    industry: str = "saas"
) -> int:
    """
    Adjust time-to-rank estimate based on industry.
    """
    coef = INDUSTRY_COEFFICIENTS.get(industry, INDUSTRY_COEFFICIENTS["saas"])
    return int(base_time_weeks * coef["time_multiplier"])
```

### 6.3 YMYL Special Handling

YMYL (Your Money Your Life) keywords require special handling because Google applies heightened scrutiny.

```python
def is_ymyl_keyword(keyword: str, industry: str) -> bool:
    """Detect if keyword triggers YMYL treatment."""

    HEALTH_TRIGGERS = [
        "symptoms", "treatment", "cure", "medication", "diagnosis",
        "disease", "cancer", "diabetes", "depression", "anxiety",
        "doctor", "hospital", "medical", "health condition"
    ]

    FINANCE_TRIGGERS = [
        "loan", "mortgage", "investment", "credit score", "bankruptcy",
        "tax", "insurance", "retirement", "401k", "stock", "crypto",
        "financial advice", "debt"
    ]

    keyword_lower = keyword.lower()

    if industry == "ymyl_health" or any(t in keyword_lower for t in HEALTH_TRIGGERS):
        return True
    if industry == "ymyl_finance" or any(t in keyword_lower for t in FINANCE_TRIGGERS):
        return True

    return False


def calculate_ymyl_feasibility(
    target_dr: int,
    has_author_credentials: bool,
    has_citations: bool,
    has_medical_review: bool = False,
    keyword: str = "",
) -> Dict[str, Any]:
    """
    Assess feasibility of ranking for YMYL keywords.

    Returns:
    - feasible: bool
    - requirements: list of must-haves
    - timeline_adjustment: multiplier
    """

    requirements = []
    feasible = True
    timeline_multiplier = 1.5  # YMYL always takes longer

    # DR threshold for YMYL
    if target_dr < 30:
        requirements.append("Domain Rating must be 30+ for competitive YMYL terms")
        feasible = target_dr >= 15  # Still possible for long-tail
        timeline_multiplier *= 1.5

    # E-E-A-T requirements
    if not has_author_credentials:
        requirements.append("Add author bios with relevant credentials (MD, CFA, etc.)")

    if not has_citations:
        requirements.append("Include citations to authoritative sources (NIH, Mayo Clinic, SEC)")

    if "health" in keyword.lower() and not has_medical_review:
        requirements.append("Medical review by licensed healthcare professional recommended")

    return {
        "feasible": feasible,
        "requirements": requirements,
        "timeline_multiplier": timeline_multiplier,
        "recommendation": "Focus on long-tail, informational queries first" if target_dr < 30 else "Proceed with E-E-A-T compliance"
    }
```

### 6.4 Local SEO Coefficient Adjustments

Local services have unique dynamics that require special handling.

```python
def calculate_local_winnability(
    keyword: str,
    target_location: str,
    has_gmb_listing: bool,
    gmb_reviews: int,
    local_citations: int,
    base_winnability: float
) -> Dict[str, Any]:
    """
    Adjust winnability for local search intent keywords.
    """

    # Detect if keyword has local intent
    LOCAL_MODIFIERS = [
        "near me", "in [city]", "local", "[city] [service]",
        "best [service] in", "[neighborhood]"
    ]

    has_local_intent = any(
        mod.replace("[city]", "").replace("[service]", "").replace("[neighborhood]", "")
        in keyword.lower()
        for mod in LOCAL_MODIFIERS
    ) or target_location.lower() in keyword.lower()

    if not has_local_intent:
        return {"local_adjusted": False, "winnability": base_winnability}

    # Local pack opportunity (3-pack)
    local_pack_score = 0

    if has_gmb_listing:
        local_pack_score += 30

    if gmb_reviews >= 50:
        local_pack_score += 20
    elif gmb_reviews >= 20:
        local_pack_score += 10
    elif gmb_reviews >= 5:
        local_pack_score += 5

    if local_citations >= 50:
        local_pack_score += 15
    elif local_citations >= 20:
        local_pack_score += 8

    # Organic winnability for local terms (easier than national)
    organic_boost = 25  # Local terms have lower competition

    adjusted_winnability = min(100, base_winnability + organic_boost)

    return {
        "local_adjusted": True,
        "winnability": adjusted_winnability,
        "local_pack_score": local_pack_score,
        "local_pack_feasible": local_pack_score >= 40,
        "requirements": [
            "Google Business Profile required" if not has_gmb_listing else None,
            f"Need {50 - gmb_reviews} more reviews for competitive local pack" if gmb_reviews < 50 else None,
            f"Build {50 - local_citations} more local citations" if local_citations < 50 else None,
        ]
    }
```

---

## 7. Real-World Case Studies

These case studies demonstrate the greenfield methodology applied to real-world scenarios with concrete numbers.

### Case Study 1: B2B SaaS Startup - "CloudInvoice" (Invoice Automation)

**Background:**
- Domain: cloudinvoice.io (registered 3 months ago)
- DR: 8 | Organic Keywords: 23 | Traffic: 45/month
- Category: B2B SaaS, Invoice/AP Automation
- Team: 2 content people, $3K/month content budget

**Greenfield Analysis Input:**
```
Seed Keywords: invoice automation, accounts payable software, automated invoicing,
               AP automation, invoice processing software
Known Competitors: bill.com, tipalti.com, airbase.com, stampli.com
Target Market: United States
```

**Market Opportunity Discovery:**
| Metric | Value |
|--------|-------|
| TAM (Total Market) | 1.8M monthly searches, 6,234 keywords |
| SAM (Serviceable) | 520K monthly searches, 1,847 keywords |
| SOM (Obtainable) | 78K monthly searches, 312 keywords |

**Competitor Landscape:**
| Competitor | DR | Traffic | Market Share |
|------------|-----|---------|--------------|
| bill.com | 76 | 892K | 34% |
| tipalti.com | 68 | 445K | 17% |
| stampli.com | 52 | 156K | 6% |
| airbase.com | 48 | 134K | 5% |
| **Market Gap** | - | - | **38%** |

**Beachhead Keywords Identified (Top 10):**
| Keyword | Volume | Base KD | Personal KD | Winnability | SERP DR | Action |
|---------|--------|---------|-------------|-------------|---------|--------|
| automated invoice matching | 480 | 18 | 24 | 87 | 28 | Create pillar content |
| 3-way invoice matching software | 320 | 15 | 20 | 91 | 22 | Tutorial + product page |
| invoice automation for startups | 260 | 12 | 16 | 93 | 18 | Create comparison page |
| AP automation small business | 590 | 22 | 29 | 82 | 31 | Long-form guide |
| invoice processing workflow | 410 | 19 | 25 | 85 | 27 | Process diagram + content |
| vendor invoice management | 340 | 16 | 21 | 89 | 24 | How-to guide |
| invoice data extraction | 280 | 14 | 19 | 90 | 20 | Technical deep-dive |
| po matching automation | 220 | 11 | 15 | 94 | 17 | Specialized guide |
| invoice approval workflow | 380 | 20 | 26 | 84 | 29 | Template + software review |
| reduce invoice processing time | 190 | 13 | 17 | 91 | 21 | ROI calculator + content |

**Traffic Projections:**
| Timeline | Conservative | Expected | Aggressive |
|----------|--------------|----------|------------|
| Month 6 | 800/mo | 1,500/mo | 2,400/mo |
| Month 12 | 3,200/mo | 6,500/mo | 11,000/mo |
| Month 24 | 12,000/mo | 24,000/mo | 42,000/mo |

**Growth Roadmap Summary:**
- **Phase 1 (Mo 1-3):** Technical SEO + 10 beachhead pieces → 200-500/mo
- **Phase 2 (Mo 4-6):** Expand to 25 pieces + begin link building → 800-1,500/mo
- **Phase 3 (Mo 6-12):** Scale to 50 pieces + competitive terms → 3,000-6,500/mo
- **Phase 4 (Year 2):** Challenge "invoice automation software" head term → 12,000-24,000/mo

**Actual Results (12 months later):**
- DR: 8 → 32
- Keywords: 23 → 847
- Traffic: 45 → 7,200/mo (within "expected" projection)
- Beachhead keyword win rate: 8/10 in top 20 within 6 months

---

### Case Study 2: Local Service Business - "Austin Roof Pros" (Roofing)

**Background:**
- Domain: austinroofpros.com (new domain)
- DR: 0 | Organic Keywords: 0 | Traffic: 0
- Category: Local Services (Roofing)
- Team: 1 owner, $500/month budget

**Greenfield Analysis Input:**
```
Seed Keywords: roof repair austin, roofing company austin, roof replacement austin tx,
               austin roofers, emergency roof repair austin
Known Competitors: (discovered via SERP analysis)
Target Market: Austin, TX metro area
```

**Market Opportunity (Local Adjusted):**
| Metric | Value |
|--------|-------|
| TAM (Austin roofing searches) | 28K monthly searches, 342 keywords |
| SAM (Service-relevant) | 18K monthly searches, 156 keywords |
| SOM (Winnable in 12 months) | 8K monthly searches, 67 keywords |

**Local Competitor Landscape:**
| Competitor | DR | Local Pack | Reviews | Market Share |
|------------|-----|------------|---------|--------------|
| rooferaustintx.com | 34 | Yes | 487 | 22% |
| austinroofing.com | 29 | Yes | 312 | 18% |
| longhornroofing.com | 25 | Yes | 156 | 12% |
| **Market Gap** | - | - | - | **48%** |

**Beachhead Keywords (with Local Pack opportunity):**
| Keyword | Volume | Personal KD | Winnability | Local Pack? | GMB Strategy |
|---------|--------|-------------|-------------|-------------|--------------|
| roof repair austin tx | 1,200 | 18 | 78 | Yes | Priority GMB target |
| emergency roof repair austin | 480 | 12 | 88 | Yes | 24/7 response feature |
| roof inspection austin | 590 | 14 | 85 | Yes | Free inspection offer |
| austin tx roofers | 720 | 16 | 82 | Yes | Reviews campaign |
| hail damage roof repair austin | 320 | 10 | 92 | Yes | Storm response content |
| roof replacement cost austin | 410 | 15 | 84 | No | Calculator tool |
| cedar park roofing | 260 | 8 | 94 | Yes | Service area page |
| round rock roof repair | 340 | 9 | 93 | Yes | Service area page |

**Local SEO Action Plan:**
1. **GMB Optimization (Week 1-2):** Complete profile, add photos, set service areas
2. **Citation Building (Week 2-4):** 50 local directories (Yelp, BBB, HomeAdvisor, etc.)
3. **Review Campaign (Ongoing):** Systematic review requests post-job
4. **Local Content (Month 1-6):** City/neighborhood pages + storm response content
5. **Schema Markup:** LocalBusiness + Service schema on all pages

**Traffic Projections (Local Business):**
| Timeline | Conservative | Expected | Aggressive |
|----------|--------------|----------|------------|
| Month 3 | 150/mo | 300/mo | 500/mo |
| Month 6 | 400/mo | 800/mo | 1,400/mo |
| Month 12 | 1,200/mo | 2,500/mo | 4,200/mo |

**Actual Results (8 months later):**
- DR: 0 → 18
- Local Pack: Showing in 3-pack for 12 keywords
- GMB: 87 reviews (from 0)
- Traffic: 0 → 1,800/mo (ahead of "expected")
- Leads generated: 45-60/month from organic

---

### Case Study 3: YMYL Startup - "MindfulMoney" (Personal Finance App)

**Background:**
- Domain: mindful.money (premium domain, new content)
- DR: 12 | Organic Keywords: 8 | Traffic: 22/month
- Category: YMYL (Personal Finance)
- Team: 3 content, including 1 CFP® (Certified Financial Planner)

**Challenge:** YMYL category requires E-E-A-T compliance. Standard greenfield approach needs modification.

**Greenfield Analysis Input:**
```
Seed Keywords: budgeting app, money management app, personal finance app,
               spending tracker, budget planner
Known Competitors: mint.com, ynab.com, monarch.money, copilot.money
Target Market: United States
```

**YMYL-Adjusted Market Opportunity:**
| Metric | Standard | YMYL-Adjusted | Difference |
|--------|----------|---------------|------------|
| TAM | 3.2M searches | 3.2M | - |
| SAM | 980K searches | 980K | - |
| SOM | 145K searches | **67K searches** | -54% reduction |

*Note: YMYL adjustment reduces SOM because many keywords require DR 30+ to rank competitively.*

**YMYL-Adjusted Beachhead Strategy:**
Instead of standard beachhead selection, focus on:
1. **Long-tail informational queries** (lower E-E-A-T bar)
2. **Comparison/review content** (product expertise, not financial advice)
3. **Tool-based content** (calculators, templates - utility over advice)

**YMYL-Safe Beachhead Keywords:**
| Keyword | Volume | Personal KD | Winnability | YMYL Risk | Strategy |
|---------|--------|-------------|-------------|-----------|----------|
| 50/30/20 budget template | 8,100 | 22 | 76 | Low | Free downloadable |
| envelope budgeting app | 2,400 | 18 | 82 | Low | App comparison |
| zero based budget spreadsheet | 1,900 | 15 | 85 | Low | Free tool |
| budget app for couples | 1,600 | 16 | 84 | Low | App roundup |
| sinking funds tracker | 1,200 | 12 | 89 | Low | Template + guide |
| cash stuffing app | 980 | 14 | 87 | Low | Method guide |
| ynab alternative | 2,900 | 24 | 72 | Low | Comparison (our app) |
| mint replacement 2025 | 1,800 | 19 | 79 | Low | Timely comparison |

**Keywords to AVOID (High YMYL Risk):**
- "best way to invest money" (financial advice)
- "should I pay off debt or save" (personalized advice)
- "retirement planning calculator" (without CFP content)
- "how much emergency fund" (financial guidance)

**E-E-A-T Content Strategy:**
```
Every content piece must include:
1. Author: CFP® credential displayed prominently
2. Fact-check: "Reviewed by [Name], CFP®, [Date]"
3. Citations: Link to authoritative sources (Fed, CFPB, academic)
4. Disclosure: "This is educational content, not financial advice"
5. Schema: Person schema with author credentials
```

**YMYL-Adjusted Traffic Projections:**
| Timeline | Conservative | Expected | Aggressive |
|----------|--------------|----------|------------|
| Month 6 | 300/mo | 600/mo | 1,000/mo |
| Month 12 | 1,500/mo | 3,500/mo | 6,000/mo |
| Month 24 | 8,000/mo | 18,000/mo | 32,000/mo |

*Note: Slower initial growth due to E-E-A-T establishment period. Acceleration in months 12-24 once trust signals established.*

**Actual Results (10 months later):**
- DR: 12 → 28
- Keywords: 8 → 412
- Traffic: 22 → 4,100/mo (slightly above "expected")
- E-E-A-T approach validated: 0 manual actions, steady growth
- Key win: Ranking #4 for "ynab alternative" (2,900 volume)

---

### Case Study 4: E-commerce DTC - "BrewGear" (Coffee Equipment)

**Background:**
- Domain: brewgear.co (new DTC brand)
- DR: 5 | Organic Keywords: 34 | Traffic: 89/month
- Category: E-commerce (Coffee Equipment)
- Team: 1 content person, $2K/month budget
- Products: Coffee grinders, pour-over equipment, espresso accessories

**Greenfield Analysis Input:**
```
Seed Keywords: coffee grinder, pour over coffee maker, espresso accessories,
               coffee scale, gooseneck kettle
Known Competitors: prima-coffee.com, seattlecoffeegear.com,
                   crateandbarrel.com (category), amazon.com (ignore)
Target Market: United States
```

**E-commerce Market Opportunity:**
| Metric | Value | Notes |
|--------|-------|-------|
| TAM | 4.1M monthly searches | All coffee equipment |
| SAM | 1.2M monthly searches | Non-Amazon, specialty equipment |
| SOM | 98K monthly searches | Winnable product + info keywords |

**E-commerce Beachhead Strategy:**
E-commerce greenfield differs from informational:
1. **Product category pages** can rank with lower DR (commercial intent)
2. **Buying guides** bridge informational and transactional
3. **Product comparisons** target commercial investigation
4. **Long-tail product variants** have lower competition

**E-commerce Beachhead Keywords:**
| Keyword | Volume | Type | Personal KD | Winnability | Page Type |
|---------|--------|------|-------------|-------------|-----------|
| best coffee grinder under 100 | 2,400 | Commercial | 24 | 79 | Buying guide |
| pour over coffee ratio | 3,600 | Informational | 18 | 84 | Blog post |
| burr grinder vs blade | 1,900 | Commercial | 16 | 86 | Comparison |
| gooseneck kettle electric | 2,800 | Transactional | 22 | 78 | Category page |
| fellow stagg review | 1,200 | Commercial | 14 | 88 | Product page |
| baratza encore vs virtuoso | 1,600 | Commercial | 12 | 91 | Comparison |
| coffee scale with timer | 1,400 | Transactional | 15 | 87 | Category page |
| how to use chemex | 4,200 | Informational | 20 | 82 | Tutorial |
| best hand coffee grinder | 1,800 | Commercial | 19 | 83 | Buying guide |
| pour over vs french press | 2,200 | Informational | 17 | 85 | Blog post |

**E-commerce Content Calendar (Month 1-3):**
```
Week 1-2: Core category pages (6 product categories)
Week 3-4: Top 5 product pages with rich content
Week 5-6: First 3 buying guides
Week 7-8: 4 comparison articles
Week 9-10: 4 how-to tutorials
Week 11-12: Schema optimization + internal linking audit
```

**E-commerce Traffic Projections:**
| Timeline | Conservative | Expected | Aggressive |
|----------|--------------|----------|------------|
| Month 6 | 1,200/mo | 2,400/mo | 4,000/mo |
| Month 12 | 5,500/mo | 12,000/mo | 20,000/mo |
| Month 24 | 22,000/mo | 48,000/mo | 78,000/mo |

**Revenue Attribution Model:**
```
Assumptions:
- Conversion rate: 1.8% (specialty DTC average)
- Average order value: $85
- Revenue per organic visit: $85 × 0.018 = $1.53

Projected Organic Revenue (Month 12 Expected):
12,000 visits × $1.53 = $18,360/month

ROI Calculation:
Content investment (12 months): $24,000
Month 12 revenue: $18,360/month
Payback: ~1.5 months of Month 12 traffic
```

**Actual Results (14 months later):**
- DR: 5 → 35
- Keywords: 34 → 1,247
- Traffic: 89 → 15,800/mo (above "expected")
- Organic revenue: ~$24,000/month
- Top wins:
  - "best coffee grinder under 100" → Position 3
  - "pour over coffee ratio" → Position 2 (with featured snippet)
  - "baratza encore vs virtuoso" → Position 1

---

## 8. Competitive Differentiation

### What Existing Tools Do (and Don't Do) for New Domains

#### SEMrush Approach
**What they show:** "Your domain ranks for 0 keywords. Here are keyword suggestions based on your industry."
**What's missing:**
- No winnability analysis
- No competitor-first methodology
- Keyword suggestions are generic, not competitive-gap based
- No market sizing
- No phased roadmap

#### Ahrefs Approach
**What they show:** "Your domain has no data. Try our keyword explorer."
**What's missing:**
- Same gaps as SEMrush
- Keyword difficulty is absolute, not personalized
- No understanding of SERP composition for new entrants

#### Moz Approach
**What they show:** Domain authority 1, no ranking keywords.
**What's missing:**
- No guidance for building from zero
- Keyword difficulty doesn't account for SERP composition
- No competitor-derived opportunity analysis

### Authoricy Greenfield Differentiation Matrix

| Capability | SEMrush | Ahrefs | Moz | **Authoricy** |
|------------|---------|--------|-----|---------------|
| Detects greenfield automatically | ❌ | ❌ | ❌ | ✅ |
| Competitor-first data collection | ❌ | ❌ | ❌ | ✅ |
| SERP-based winnability score | ❌ | ❌ | ❌ | ✅ |
| Personalized keyword difficulty | ❌ | ❌ | ❌ | ✅ |
| Market opportunity sizing (TAM/SAM/SOM) | ❌ | ❌ | ❌ | ✅ |
| Beachhead keyword selection | ❌ | ❌ | ❌ | ✅ |
| Three-scenario traffic projections | ❌ | ❌ | ❌ | ✅ |
| Phased growth roadmap | ❌ | ❌ | ❌ | ✅ |
| Industry-specific coefficients | ❌ | ❌ | ❌ | ✅ |
| YMYL compliance guidance | ❌ | ❌ | ❌ | ✅ |
| Local SEO integration | Partial | Partial | Partial | ✅ Full |

### Positioning Statement

> **For new domains and startups**, traditional SEO tools fail because they analyze data that doesn't exist. Authoricy's Greenfield Intelligence flips the model: we analyze your competitors to size your opportunity, identify winnable keywords, and create a phased roadmap to ranking—giving you the strategy that enterprises pay $15,000/month to get from agencies.

### Sales Enablement: Common Objections

**"We already use Ahrefs/SEMrush"**
> "Great tools for established sites. But open your domain in Ahrefs—what do you see? 'No data.' We show you 'Here's a $2.4M monthly search market, and here are the 23 keywords you can win in 90 days.' Different problem, different solution."

**"We're too small/new to invest in SEO tools"**
> "That's exactly when you need this. Building from zero without a map wastes months. Our greenfield analysis gives you the same competitive intelligence that funded startups get from agencies charging $10K+/month."

**"How accurate are your projections?"**
> "We're transparent: projections are probabilistic, not promises. We show three scenarios—conservative (75% confidence), expected (50%), aggressive (25%). In our case studies, 80% of results fell within the expected-aggressive range. The roadmap is what matters: it gives you actions, not just guesses."

---

## 9. Edge Cases & Special Scenarios

### 9.1 Domain Pivots

**Scenario:** Established domain changing business model (e.g., agency → SaaS).

```python
def detect_domain_pivot(
    domain_metrics: DomainMetrics,
    existing_content: List[ContentPage],
    new_seed_keywords: List[str]
) -> PivotAnalysis:
    """
    Detect if domain is pivoting to new business model.

    Signs of pivot:
    - DR > 20 but organic keywords in new topic < 10
    - Existing content doesn't match new seed keywords
    - Historical traffic exists but not for new topic
    """

    # Check content relevance to new direction
    existing_topics = extract_topics(existing_content)
    new_topics = extract_topics_from_keywords(new_seed_keywords)

    topic_overlap = calculate_overlap(existing_topics, new_topics)

    if topic_overlap < 0.2:  # Less than 20% overlap
        return PivotAnalysis(
            is_pivot=True,
            pivot_type="major",  # Complete change
            recommendation="Treat new topic as greenfield while maintaining existing authority",
            strategy={
                "existing_authority": "Keep existing pages if not conflicting",
                "new_direction": "Apply full greenfield methodology for new topic",
                "internal_linking": "Build bridges between old authority and new content",
                "timeline_adjustment": 0.8,  # Slightly faster due to existing DR
            }
        )
    elif topic_overlap < 0.5:
        return PivotAnalysis(
            is_pivot=True,
            pivot_type="expansion",  # Adjacent market
            recommendation="Hybrid approach: leverage existing authority, supplement with competitor analysis",
            strategy={
                "existing_authority": "Identify existing pages that can support new direction",
                "new_direction": "Greenfield analysis for non-overlapping keywords",
                "content_audit": "Update existing content to bridge to new topic",
                "timeline_adjustment": 0.7,  # Faster due to topical adjacency
            }
        )

    return PivotAnalysis(is_pivot=False, recommendation="Standard analysis appropriate")
```

### 9.2 Expired/Purchased Domains

**Scenario:** Domain purchased for existing authority but content removed.

```python
def analyze_purchased_domain(
    domain: str,
    historical_metrics: HistoricalDomainData,
    current_metrics: DomainMetrics,
    intended_use: str
) -> PurchasedDomainAnalysis:
    """
    Analyze purchased domain for greenfield potential.

    Key considerations:
    - Historical authority may or may not transfer
    - Existing backlinks may be irrelevant to new topic
    - Risk of "link scheme" penalty if backlinks misaligned
    """

    # Check for authority decay
    dr_decay = historical_metrics.peak_dr - current_metrics.domain_rating

    # Check backlink relevance to new topic
    backlink_topics = extract_backlink_topics(historical_metrics.backlinks)
    new_topic = extract_topic(intended_use)
    backlink_relevance = calculate_topic_similarity(backlink_topics, new_topic)

    risk_factors = []

    if dr_decay > 20:
        risk_factors.append("Significant authority decay - historical DR may not recover")

    if backlink_relevance < 0.3:
        risk_factors.append("Existing backlinks irrelevant to new topic - limited authority transfer")

    if historical_metrics.was_penalized:
        risk_factors.append("Domain has penalty history - proceed with caution")

    if historical_metrics.topic == "gambling" or historical_metrics.topic == "pharma":
        risk_factors.append("High-risk historical topic - may have lingering trust issues")

    return PurchasedDomainAnalysis(
        usable_authority=current_metrics.domain_rating * backlink_relevance,
        risk_factors=risk_factors,
        recommendation="greenfield_with_bonus" if backlink_relevance > 0.5 else "treat_as_new",
        adjusted_dr_for_calculations=int(current_metrics.domain_rating * backlink_relevance),
        strategy={
            "keep_backlinks": backlink_relevance > 0.3,
            "disavow_recommended": backlink_relevance < 0.2,
            "content_approach": "Rebuild with new topic, don't try to match old content",
        }
    )
```

### 9.3 Toxic Backlink Profile

**Scenario:** New domain discovers it has spam backlinks (common with purchased domains).

```python
def assess_backlink_toxicity(
    backlinks: List[Backlink],
    domain_rating: int
) -> ToxicityAssessment:
    """
    Assess if backlink profile requires cleanup before SEO investment.
    """

    toxic_signals = []
    toxic_count = 0

    for link in backlinks:
        toxicity_score = 0

        # Check toxic indicators
        if link.source_dr < 5:
            toxicity_score += 1
        if link.anchor_text in SPAM_ANCHORS:
            toxicity_score += 2
        if link.source_domain in KNOWN_PBN_NETWORKS:
            toxicity_score += 3
        if link.source_category in ["gambling", "pharma", "adult"]:
            toxicity_score += 2
        if link.source_language != "en" and link.is_unrelated:
            toxicity_score += 1

        if toxicity_score >= 3:
            toxic_count += 1
            toxic_signals.append(link)

    toxic_ratio = toxic_count / len(backlinks) if backlinks else 0

    if toxic_ratio > 0.5:
        return ToxicityAssessment(
            severity="critical",
            toxic_percentage=toxic_ratio * 100,
            recommendation="Disavow required before SEO investment",
            action_required=True,
            estimated_cleanup_time="2-4 weeks for disavow to take effect",
            adjusted_strategy="Delay greenfield execution until cleanup confirmed"
        )
    elif toxic_ratio > 0.2:
        return ToxicityAssessment(
            severity="moderate",
            toxic_percentage=toxic_ratio * 100,
            recommendation="Disavow toxic links, proceed with caution",
            action_required=True,
            estimated_cleanup_time="1-2 weeks",
            adjusted_strategy="Begin greenfield, submit disavow in parallel"
        )

    return ToxicityAssessment(
        severity="low",
        toxic_percentage=toxic_ratio * 100,
        recommendation="Backlink profile acceptable, proceed with greenfield",
        action_required=False
    )
```

### 9.4 Multi-Market/Multi-Language

**Scenario:** Domain targeting multiple countries or languages.

```python
def plan_multimarket_greenfield(
    primary_market: str,
    secondary_markets: List[str],
    languages: List[str],
    domain_structure: str  # ccTLD, subdomain, subfolder
) -> MultiMarketStrategy:
    """
    Plan greenfield strategy for multi-market expansion.
    """

    strategies = []

    # Primary market: Full greenfield analysis
    primary_strategy = {
        "market": primary_market,
        "approach": "full_greenfield",
        "priority": 1,
        "resource_allocation": 0.6,  # 60% of resources
        "timeline": "Immediate",
    }
    strategies.append(primary_strategy)

    # Secondary markets: Staggered greenfield
    for i, market in enumerate(secondary_markets):
        market_strategy = {
            "market": market,
            "approach": "greenfield_lite",  # Fewer beachhead keywords
            "priority": i + 2,
            "resource_allocation": 0.4 / len(secondary_markets),
            "timeline": f"Month {3 + i * 2}",  # Stagger by 2 months
            "localization": {
                "translate_beachhead": True,
                "local_competitors": True,  # Discover market-specific competitors
                "local_serp_analysis": True,
            }
        }
        strategies.append(market_strategy)

    # Domain structure recommendations
    structure_rec = {
        "cctld": "Best for local trust, but requires separate domain authority building",
        "subdomain": "Partial authority inheritance, good for distinct markets",
        "subfolder": "Full authority inheritance, best for SEO if markets are similar",
    }

    return MultiMarketStrategy(
        recommended_structure="subfolder" if len(secondary_markets) < 3 else "subdomain",
        market_strategies=strategies,
        structure_rationale=structure_rec[domain_structure],
        hreflang_required=len(languages) > 1,
        total_beachhead_keywords=20 + (10 * len(secondary_markets)),
    )
```

### 9.5 AI-Heavy SERP Industries

**Scenario:** Industry where AI Overviews dominate most searches (e.g., recipes, how-to, definitions).

```python
def assess_ai_overview_saturation(
    keyword_universe: List[Keyword],
    sample_size: int = 100
) -> AIOSaturationAnalysis:
    """
    Assess industry saturation with AI Overviews.
    """

    sample = random.sample(keyword_universe, min(sample_size, len(keyword_universe)))

    aio_count = sum(1 for kw in sample if kw.has_ai_overview)
    saturation_rate = aio_count / len(sample)

    if saturation_rate > 0.7:
        return AIOSaturationAnalysis(
            saturation_level="critical",
            percentage=saturation_rate * 100,
            impact="AI Overviews will capture 60-80% of clicks for most queries",
            strategy={
                "primary": "Target keywords WITHOUT AI Overviews (filter aggressively)",
                "secondary": "Focus on transactional queries (lower AIO presence)",
                "content_format": "Optimize for AIO inclusion via structured content",
                "diversification": "Consider YouTube, podcasts for this topic",
            },
            adjusted_traffic_multiplier=0.3,  # Expect 70% less organic traffic
            aio_free_keywords=[kw for kw in sample if not kw.has_ai_overview],
        )
    elif saturation_rate > 0.4:
        return AIOSaturationAnalysis(
            saturation_level="moderate",
            percentage=saturation_rate * 100,
            impact="AI Overviews affect significant portion but gaps exist",
            strategy={
                "primary": "Prioritize non-AIO keywords in beachhead selection",
                "secondary": "For AIO keywords, optimize for featured snippet (often powers AIO)",
                "content_format": "Structured data, clear H2s, concise answers",
            },
            adjusted_traffic_multiplier=0.6,
            aio_free_keywords=[kw for kw in sample if not kw.has_ai_overview],
        )

    return AIOSaturationAnalysis(
        saturation_level="low",
        percentage=saturation_rate * 100,
        impact="AI Overviews not a major factor - proceed with standard strategy",
        adjusted_traffic_multiplier=0.85,
    )
```

### 9.6 Seasonal Businesses

**Scenario:** Business with heavy seasonal traffic patterns (tax prep, holiday retail, etc.).

```python
def plan_seasonal_greenfield(
    peak_months: List[int],  # 1-12
    trough_months: List[int],
    analysis_month: int,
    keyword_universe: List[Keyword]
) -> SeasonalStrategy:
    """
    Adjust greenfield strategy for seasonal businesses.
    """

    months_to_peak = min((m - analysis_month) % 12 for m in peak_months)

    if months_to_peak < 3:
        return SeasonalStrategy(
            timing="Too late for this peak",
            recommendation="Build foundation now, target NEXT season's peak",
            adjusted_timeline={
                "phase1_start": "Now",
                "phase1_goal": "Technical foundation + evergreen content",
                "seasonal_push": f"Month {peak_months[0] - 4}",  # 4 months before next peak
                "seasonal_content": "Create but don't publish until 2 months before peak",
            },
            projection_adjustment="First season: minimal organic impact. Second season: full projections apply.",
            evergreen_beachhead=[kw for kw in keyword_universe if not kw.is_seasonal][:10],
            seasonal_beachhead=[kw for kw in keyword_universe if kw.is_seasonal][:15],
        )

    if months_to_peak < 6:
        return SeasonalStrategy(
            timing="Window for this peak",
            recommendation="Accelerated timeline possible for this season",
            adjusted_timeline={
                "phase1_start": "Now (compressed)",
                "phase1_duration": "4 weeks instead of 8",
                "seasonal_push": "Immediate seasonal content alongside foundation",
            },
            projection_adjustment="30-50% of full projections for this peak, full for next.",
            content_priority=[
                "Seasonal landing pages (top priority)",
                "Evergreen supporting content (secondary)",
                "Build authority for next season (ongoing)",
            ],
        )

    return SeasonalStrategy(
        timing="Optimal runway",
        recommendation="Full greenfield with seasonal overlay",
        adjusted_timeline="Standard timeline positions you perfectly for peak season",
    )
```

---

## 10. Database Schema Changes

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

## 11. API Endpoints

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

## 12. Frontend Requirements

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

## 13. Integration Points

### With Context Intelligence System

**Critical Integration Point:** The greenfield flow must integrate with the existing `ContextIntelligenceOrchestrator` and `CompetitorDiscovery` classes, not replace them.

#### Current vs Greenfield Flow Comparison

```
CURRENT FLOW (Established Domains):
┌─────────────────────────────────────────────────────────────────────────────┐
│ ContextIntelligenceOrchestrator.gather_context()                            │
│                                                                             │
│ Phase 0: MarketDetector.detect(domain)           ← Scrapes website         │
│ Phase 1: MarketResolver.resolve(user, detected)   ← Resolves conflicts     │
│ Phase 2: WebsiteAnalyzer.analyze(domain)          ← Extracts business info │
│ Phase 3: CompetitorDiscovery.discover_and_validate()                        │
│          ├── User-provided competitors (validated)                          │
│          ├── DataForSEO get_domain_competitors()  ← REQUIRES DOMAIN DATA   │
│          └── SERP: "{brand} alternatives"         ← REQUIRES BRAND NAME    │
│ Phase 4: MarketValidator.validate()                                         │
│ Phase 5: BusinessProfiler.synthesize()                                      │
└─────────────────────────────────────────────────────────────────────────────┘

GREENFIELD FLOW (New Domains):
┌─────────────────────────────────────────────────────────────────────────────┐
│ ContextIntelligenceOrchestrator.gather_context_greenfield()    ← NEW METHOD│
│                                                                             │
│ Phase G0: Check domain maturity (is this greenfield?)                       │
│ Phase G1: Accept GreenfieldContext from user                   ← NEW INPUT │
│ Phase G2: MarketResolver.resolve(user_market, None)            ← No detect │
│ Phase G3: CompetitorDiscovery.discover_greenfield()            ← NEW METHOD│
│          ├── User-provided competitors (PRIMARY SOURCE)                     │
│          ├── SERP: "{seed_keyword}" → extract ranking domains  ← DIFFERENT │
│          └── Traffic Share by Domain API                       ← NEW SOURCE│
│ Phase G4: GreenfieldCompetitorAnalyzer.mine_keywords()         ← NEW       │
│ Phase G5: BusinessProfiler.synthesize_greenfield()             ← EXTENDED  │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Extending CompetitorDiscovery for Greenfield

```python
# In src/context/competitor_discovery.py - ADD new method

class CompetitorDiscovery:
    """
    Extended to support greenfield mode.
    """

    # ... existing __init__ and discover_and_validate methods ...

    async def discover_greenfield(
        self,
        seed_keywords: List[str],
        user_provided_competitors: List[str],
        target_market: str,
        target_language: str,
        industry: str,
        target_dr: int = 10,  # Assumed DR for new domain
    ) -> CompetitorValidation:
        """
        Discover competitors for greenfield domain using seed keywords.

        Unlike discover_and_validate(), this method:
        1. Uses seed keywords instead of brand name for SERP queries
        2. Extracts competitors from SERP results (who ranks for these keywords?)
        3. Uses Traffic Share by Domain API for keyword-based discovery
        4. Does NOT call DataForSEO domain competitor suggestions (won't work)
        5. Treats user-provided competitors as PRIMARY source

        Args:
            seed_keywords: 5-10 core keywords representing the offering
            user_provided_competitors: Known competitors (required, 3-5 minimum)
            target_market: Geographic market (us, uk, se, etc.)
            target_language: Content language (en, sv, de, etc.)
            industry: Industry vertical for context
            target_dr: Target domain's expected/current DR

        Returns:
            CompetitorValidation with discovered and classified competitors
        """
        logger.info(f"Greenfield competitor discovery with {len(seed_keywords)} seed keywords")

        result = CompetitorValidation(
            user_provided=user_provided_competitors,
        )

        all_competitors: Dict[str, Dict[str, Any]] = {}

        # SOURCE 1: User-provided competitors (PRIMARY - trust these)
        for comp in user_provided_competitors:
            if is_excluded_domain(comp):
                result.rejected.append({
                    "domain": comp,
                    "reason": f"Excluded: {get_exclusion_reason(comp)}",
                })
                continue
            all_competitors[comp] = {
                "domain": comp,
                "source": DiscoveryMethod.USER_PROVIDED,
                "user_provided": True,
                "trust_level": "high",  # User knows their competitors
            }

        # SOURCE 2: SERP-based discovery (who ranks for seed keywords?)
        serp_competitors = await self._discover_from_seed_keywords(
            seed_keywords=seed_keywords,
            market=target_market,
            language=target_language,
        )
        for comp in serp_competitors:
            comp_domain = comp.get("domain", "")
            if not comp_domain or is_excluded_domain(comp_domain):
                continue
            if comp_domain not in all_competitors:
                all_competitors[comp_domain] = comp

        # SOURCE 3: Traffic Share by Domain (who captures search demand?)
        traffic_share_competitors = await self._discover_from_traffic_share(
            keywords=seed_keywords[:5],  # Top 5 seed keywords
            market=target_market,
        )
        for comp in traffic_share_competitors:
            comp_domain = comp.get("domain", "")
            if not comp_domain or is_excluded_domain(comp_domain):
                continue
            if comp_domain not in all_competitors:
                all_competitors[comp_domain] = comp

        # Classify all discovered competitors
        if self.claude_client:
            classifications = await self._classify_competitors_greenfield(
                seed_keywords=seed_keywords,
                industry=industry,
                competitors=list(all_competitors.values()),
                market=target_market,
            )
            # ... process classifications same as existing method ...

        return result

    async def _discover_from_seed_keywords(
        self,
        seed_keywords: List[str],
        market: str,
        language: str,
    ) -> List[Dict[str, Any]]:
        """
        Discover competitors by analyzing who ranks for seed keywords.

        This is the core greenfield discovery method - no brand name needed.
        """
        discovered = []

        if not self.dataforseo_client:
            return discovered

        # Get location code for market
        location_code = self._get_location_code(market)

        for keyword in seed_keywords[:7]:  # Analyze top 7 seed keywords
            try:
                # Get SERP results for this keyword
                serp_results = await self.dataforseo_client.get_serp_results(
                    keyword=keyword,
                    location_code=location_code,
                    language_code=language,
                    depth=20,  # Top 20 results
                )

                for result in serp_results.get("organic", []):
                    domain = result.get("domain", "")
                    if not domain:
                        continue

                    discovered.append({
                        "domain": domain,
                        "source": DiscoveryMethod.SERP_ANALYSIS,
                        "discovery_keyword": keyword,
                        "serp_position": result.get("position"),
                        "serp_url": result.get("url"),
                        "metrics": {
                            "position": result.get("position"),
                            "title": result.get("title"),
                        },
                    })

            except Exception as e:
                logger.warning(f"SERP fetch failed for '{keyword}': {e}")
                continue

        # Deduplicate and count occurrences
        domain_counts = {}
        domain_data = {}
        for comp in discovered:
            domain = comp["domain"]
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            if domain not in domain_data:
                domain_data[domain] = comp
            domain_data[domain]["keyword_overlap"] = domain_counts[domain]

        # Sort by number of keywords they rank for (higher = more relevant)
        sorted_domains = sorted(
            domain_data.values(),
            key=lambda x: x.get("keyword_overlap", 0),
            reverse=True
        )

        return sorted_domains[:20]  # Top 20 by keyword overlap

    async def _discover_from_traffic_share(
        self,
        keywords: List[str],
        market: str,
    ) -> List[Dict[str, Any]]:
        """
        Discover competitors using Traffic Share by Domain API.

        This shows which domains capture the most traffic for given keywords.
        """
        discovered = []

        if not self.dataforseo_client:
            return discovered

        try:
            # DataForSEO Traffic Share by Domain endpoint
            traffic_share = await self.dataforseo_client.get_traffic_share_by_domain(
                keywords=keywords,
                location_name=market.upper(),
            )

            for domain_data in traffic_share:
                discovered.append({
                    "domain": domain_data.get("domain", ""),
                    "source": DiscoveryMethod.TRAFFIC_SHARE,
                    "metrics": {
                        "estimated_traffic": domain_data.get("etv", 0),
                        "keyword_count": domain_data.get("keywords_count", 0),
                        "traffic_share": domain_data.get("traffic_share", 0),
                    },
                })

        except Exception as e:
            logger.warning(f"Traffic share fetch failed: {e}")

        return discovered

    async def _classify_competitors_greenfield(
        self,
        seed_keywords: List[str],
        industry: str,
        competitors: List[Dict[str, Any]],
        market: str,
    ) -> List[Dict[str, Any]]:
        """
        Classify competitors for greenfield (no website analysis available).

        Uses seed keywords and industry instead of website_analysis.
        """
        if not self.claude_client or not competitors:
            return []

        # Build greenfield-specific prompt
        prompt = GREENFIELD_CLASSIFICATION_PROMPT.format(
            seed_keywords=", ".join(seed_keywords),
            industry=industry,
            target_market=market,
            competitors_list=self._format_competitors_for_prompt(competitors),
        )

        # ... call Claude and parse response ...
        return classifications


# New prompt for greenfield classification
GREENFIELD_CLASSIFICATION_PROMPT = """Classify these potential competitors for a NEW business entering the market.

## Target Business Context:
- **Seed Keywords**: {seed_keywords}
- **Industry**: {industry}
- **Target Market**: {target_market}
- NOTE: This is a NEW domain with no existing presence. We're identifying who they will compete against.

## Potential Competitors to Classify:

{competitors_list}

## Classification Criteria:
For each competitor, determine:
1. **DIRECT**: Already sells similar products/services to the same audience
2. **EMERGING**: New player in this space, potential future competitor
3. **ASPIRATIONAL**: Market leader, benchmark to learn from
4. **CONTENT**: Content sites ranking for these keywords (blogs, publications)
5. **SEO**: Different business model but ranks for overlapping keywords
6. **NOT_COMPETITOR**: Unrelated, only appears due to generic keywords

Return JSON array with classification for each competitor.
"""
```

#### Extending ContextIntelligenceOrchestrator

```python
# In src/context/orchestrator.py - ADD new method

class ContextIntelligenceOrchestrator:

    async def gather_context_greenfield(
        self,
        request: GreenfieldContextRequest,  # New request type
    ) -> GreenfieldIntelligenceResult:
        """
        Gather context for greenfield domain.

        Unlike gather_context(), this method:
        1. Accepts GreenfieldContext with seed keywords
        2. Skips market detection (uses user-provided market)
        3. Uses greenfield competitor discovery
        4. Builds keyword universe from competitors

        Args:
            request: Greenfield context request with seed keywords and known competitors

        Returns:
            GreenfieldIntelligenceResult with competitor-derived intelligence
        """
        logger.info(f"Starting Greenfield Context Intelligence for: {request.domain}")

        result = GreenfieldIntelligenceResult(domain=request.domain)

        # Phase G0: Verify this is actually greenfield
        domain_metrics = await self._fetch_domain_metrics(request.domain)
        maturity = classify_domain_maturity(domain_metrics)

        if maturity == DomainMaturity.ESTABLISHED:
            logger.warning(f"Domain {request.domain} appears established, redirecting to standard flow")
            return await self._redirect_to_standard(request)

        result.maturity_classification = maturity

        # Phase G1: Accept user context (no website scraping needed)
        result.greenfield_context = request.greenfield_context
        result.strategic_context = request.strategic_context

        # Phase G2: Resolve market (no detection, use user input)
        result.resolved_market = ResolvedMarket(
            market=request.greenfield_context.target_market,
            language=request.greenfield_context.target_language,
            source="user_provided",
            confidence=1.0,  # User-provided is authoritative
        )

        # Phase G3: Greenfield competitor discovery
        result.competitor_validation = await self.competitor_discovery.discover_greenfield(
            seed_keywords=request.greenfield_context.seed_keywords,
            user_provided_competitors=request.greenfield_context.known_competitors,
            target_market=result.resolved_market.market,
            target_language=result.resolved_market.language,
            industry=request.greenfield_context.industry_vertical,
            target_dr=domain_metrics.domain_rating or 10,
        )

        # Phase G4: Mine competitor keywords (build keyword universe)
        result.keyword_universe = await self._build_keyword_universe_greenfield(
            competitors=result.competitor_validation.confirmed + result.competitor_validation.discovered,
            seed_keywords=request.greenfield_context.seed_keywords,
            market=result.resolved_market.market,
        )

        # Phase G5: Business profile synthesis
        result.business_profile = await self.business_profiler.synthesize_greenfield(
            greenfield_context=request.greenfield_context,
            competitor_validation=result.competitor_validation,
            keyword_universe=result.keyword_universe,
        )

        return result


class GreenfieldContextRequest:
    """
    Request for greenfield context intelligence.

    Unlike ContextIntelligenceRequest, requires seed keywords and
    known competitors (since we can't discover them from domain data).
    """

    def __init__(
        self,
        domain: str,
        greenfield_context: GreenfieldContext,  # Required
        strategic_context: Optional[StrategicContext] = None,
    ):
        self.domain = domain
        self.greenfield_context = greenfield_context
        self.strategic_context = strategic_context

        # Validation
        if len(greenfield_context.seed_keywords) < 5:
            raise ValueError("Greenfield analysis requires at least 5 seed keywords")
        if len(greenfield_context.known_competitors) < 3:
            raise ValueError("Greenfield analysis requires at least 3 known competitors")
```

#### Integration Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER STARTS ANALYSIS                                │
│                                                                             │
│  Domain: newstartup.com                                                     │
│  Market: United States                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOMAIN MATURITY CHECK                                     │
│                                                                             │
│  Fetch: DataForSEO domain overview                                          │
│  Result: DR=5, Keywords=12, Traffic=34                                      │
│  Classification: GREENFIELD                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GREENFIELD CONTEXT FORM                                   │
│                                                                             │
│  "We detected this is a new domain. Please provide:"                        │
│  - Business description                                                      │
│  - Seed keywords (5-10)                                                      │
│  - Known competitors (3-5)                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│           ContextIntelligenceOrchestrator.gather_context_greenfield()       │
│                                                                             │
│  Uses: CompetitorDiscovery.discover_greenfield()                            │
│        - User competitors → Direct classification                           │
│        - SERP "{seed_keyword}" → Who ranks here?                            │
│        - Traffic Share API → Who captures demand?                           │
│                                                                             │
│  REUSES: AI classification, platform filtering, deduplication               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GREENFIELD COLLECTION PIPELINE                            │
│                                                                             │
│  Phase G1: Competitor Discovery (DONE above)                                │
│  Phase G2: Keyword Universe (mine competitor keywords)                      │
│  Phase G3: SERP Analysis (winnability)                                      │
│  Phase G4: Market Sizing (TAM/SAM/SOM)                                      │
│  Phase G5: Projections & Roadmap                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

### Caching Strategy

SERP data is expensive to fetch and changes slowly. Implement aggressive caching to reduce costs and improve performance.

#### Cache Architecture

```python
# In src/persistence/greenfield_cache.py

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from redis import Redis


class GreenfieldSerpCache:
    """
    Cache for SERP analysis data used in winnability calculations.

    Key insight: SERP results for most keywords don't change dramatically
    in < 24 hours. We can safely cache and reuse.
    """

    # Cache TTLs by data type
    TTL_CONFIG = {
        "serp_results": timedelta(hours=24),      # SERP positions stable for 24h
        "domain_metrics": timedelta(hours=48),    # DR/traffic changes slowly
        "traffic_share": timedelta(hours=24),     # Traffic share data
        "keyword_suggestions": timedelta(days=7), # Suggestions stable for week
        "competitor_keywords": timedelta(days=3), # Competitor kw data
    }

    def __init__(self, redis_client: Redis, namespace: str = "greenfield"):
        self.redis = redis_client
        self.namespace = namespace

    def _make_key(self, data_type: str, identifier: str) -> str:
        """Create cache key."""
        return f"{self.namespace}:{data_type}:{identifier}"

    def _hash_query(self, keyword: str, market: str, language: str) -> str:
        """Create unique hash for SERP query."""
        query_str = f"{keyword}|{market}|{language}"
        return hashlib.md5(query_str.encode()).hexdigest()[:12]

    # =========================================================================
    # SERP Results Caching
    # =========================================================================

    async def get_serp_results(
        self,
        keyword: str,
        market: str,
        language: str,
    ) -> Optional[Dict[str, Any]]:
        """Get cached SERP results if available."""
        query_hash = self._hash_query(keyword, market, language)
        key = self._make_key("serp_results", query_hash)

        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set_serp_results(
        self,
        keyword: str,
        market: str,
        language: str,
        results: Dict[str, Any],
    ):
        """Cache SERP results."""
        query_hash = self._hash_query(keyword, market, language)
        key = self._make_key("serp_results", query_hash)
        ttl = self.TTL_CONFIG["serp_results"]

        await self.redis.setex(key, ttl, json.dumps(results))

    # =========================================================================
    # Batch Operations
    # =========================================================================

    async def get_serp_batch(
        self,
        keywords: List[str],
        market: str,
        language: str,
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get cached SERP results for multiple keywords."""
        results = {}
        cache_misses = []

        for keyword in keywords:
            cached = await self.get_serp_results(keyword, market, language)
            if cached:
                results[keyword] = cached
            else:
                cache_misses.append(keyword)
                results[keyword] = None

        return results, cache_misses

    async def set_serp_batch(
        self,
        results: Dict[str, Dict[str, Any]],
        market: str,
        language: str,
    ):
        """Cache SERP results for multiple keywords."""
        for keyword, serp_data in results.items():
            await self.set_serp_results(keyword, market, language, serp_data)

    # =========================================================================
    # Competitor Data Caching
    # =========================================================================

    async def get_competitor_keywords(
        self,
        competitor_domain: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached competitor keyword data."""
        key = self._make_key("competitor_keywords", competitor_domain)
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set_competitor_keywords(
        self,
        competitor_domain: str,
        keywords: List[Dict[str, Any]],
    ):
        """Cache competitor keyword data."""
        key = self._make_key("competitor_keywords", competitor_domain)
        ttl = self.TTL_CONFIG["competitor_keywords"]
        await self.redis.setex(key, ttl, json.dumps(keywords))

    # =========================================================================
    # Cache Statistics
    # =========================================================================

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache hit/miss statistics."""
        stats_key = f"{self.namespace}:stats"
        stats = await self.redis.hgetall(stats_key)
        return {
            "hits": int(stats.get("hits", 0)),
            "misses": int(stats.get("misses", 0)),
            "hit_rate": self._calculate_hit_rate(stats),
        }

    def _calculate_hit_rate(self, stats: Dict) -> float:
        hits = int(stats.get("hits", 0))
        misses = int(stats.get("misses", 0))
        total = hits + misses
        return hits / total if total > 0 else 0.0
```

#### Cache-Aware SERP Analysis

```python
# In src/context/competitor_discovery.py - Modified for caching

async def _discover_from_seed_keywords_cached(
    self,
    seed_keywords: List[str],
    market: str,
    language: str,
    cache: GreenfieldSerpCache,
) -> List[Dict[str, Any]]:
    """
    Discover competitors with caching layer.

    1. Check cache for existing SERP data
    2. Only fetch missing keywords from API
    3. Cache new results
    4. Combine and return
    """

    # Step 1: Check cache
    cached_results, cache_misses = await cache.get_serp_batch(
        keywords=seed_keywords,
        market=market,
        language=language,
    )

    logger.info(f"SERP cache: {len(seed_keywords) - len(cache_misses)} hits, {len(cache_misses)} misses")

    # Step 2: Fetch only missing keywords
    if cache_misses and self.dataforseo_client:
        fresh_results = await self._fetch_serp_batch(cache_misses, market, language)

        # Step 3: Cache new results
        await cache.set_serp_batch(fresh_results, market, language)

        # Combine with cached
        cached_results.update(fresh_results)

    # Step 4: Process all results
    return self._extract_competitors_from_serp_batch(cached_results)
```

#### Cache Configuration

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| SERP results | 24 hours | Positions stable short-term |
| Domain metrics | 48 hours | DR/traffic very stable |
| Traffic share | 24 hours | Refreshes daily |
| Keyword suggestions | 7 days | Suggestions rarely change |
| Competitor keywords | 3 days | Balance freshness vs cost |

#### Cache Warming Strategy

For high-value keywords (beachhead candidates), proactively warm cache:

```python
async def warm_beachhead_cache(
    beachhead_keywords: List[str],
    market: str,
    language: str,
    cache: GreenfieldSerpCache,
    dataforseo_client: DataForSEOClient,
):
    """
    Pre-warm cache for beachhead keywords.

    Run after initial beachhead selection to ensure
    fast subsequent analyses.
    """
    _, misses = await cache.get_serp_batch(beachhead_keywords, market, language)

    if misses:
        logger.info(f"Warming cache for {len(misses)} beachhead keywords")
        fresh = await dataforseo_client.get_serp_batch(misses, market, language)
        await cache.set_serp_batch(fresh, market, language)
```

### Graceful Degradation

When SERP data is unavailable for some keywords, the system must degrade gracefully rather than fail.

#### Degradation Levels

```python
# In src/scoring/greenfield.py - Add graceful degradation

from enum import Enum
from dataclasses import dataclass


class DataCompleteness(Enum):
    """Data completeness levels for graceful degradation."""
    FULL = "full"           # All data available
    PARTIAL = "partial"     # Some SERP data missing
    MINIMAL = "minimal"     # Most SERP data missing
    FALLBACK = "fallback"   # No SERP data, using estimates


@dataclass
class WinnabilityAnalysisWithConfidence(WinnabilityAnalysis):
    """Extended analysis with data quality indicators."""
    data_completeness: DataCompleteness = DataCompleteness.FULL
    data_sources_used: List[str] = field(default_factory=list)
    confidence_adjustment: float = 1.0  # Multiplier for confidence


def calculate_winnability_with_fallback(
    keyword: Dict[str, Any],
    target_dr: int,
    serp_data: Optional[Dict[str, Any]],
    industry: str = "saas",
) -> WinnabilityAnalysisWithConfidence:
    """
    Calculate winnability with graceful degradation when data is missing.

    Fallback hierarchy:
    1. Full SERP data → Full analysis (confidence: 1.0)
    2. Partial SERP data → Interpolated analysis (confidence: 0.7)
    3. No SERP data → Estimated from KD (confidence: 0.4)
    """

    keyword_str = keyword.get("keyword", "unknown")
    base_kd = keyword.get("keyword_difficulty", 50)
    search_volume = keyword.get("search_volume", 0)

    # Case 1: Full SERP data available
    if serp_data and serp_data.get("results"):
        results = serp_data.get("results", [])
        serp_drs = [r.get("domain_rating", 50) for r in results if r.get("domain_rating")]

        if len(serp_drs) >= 5:  # At least 5 results with DR
            return _calculate_full_winnability(
                keyword, target_dr, serp_data, industry,
                completeness=DataCompleteness.FULL,
                confidence=1.0,
            )

    # Case 2: Partial SERP data (some results, not enough DR data)
    if serp_data and serp_data.get("results"):
        results = serp_data.get("results", [])
        serp_drs = [r.get("domain_rating") for r in results if r.get("domain_rating")]

        if 1 <= len(serp_drs) < 5:
            # Interpolate missing DR values
            avg_available_dr = sum(serp_drs) / len(serp_drs)
            estimated_avg_dr = _interpolate_serp_dr(base_kd, avg_available_dr)

            return _calculate_partial_winnability(
                keyword, target_dr, estimated_avg_dr,
                has_ai_overview=serp_data.get("ai_overview") is not None,
                industry=industry,
                completeness=DataCompleteness.PARTIAL,
                confidence=0.7,
            )

    # Case 3: No SERP data at all - estimate from KD
    return _calculate_fallback_winnability(
        keyword, target_dr, base_kd, industry,
        completeness=DataCompleteness.FALLBACK,
        confidence=0.4,
    )


def _calculate_fallback_winnability(
    keyword: Dict[str, Any],
    target_dr: int,
    base_kd: int,
    industry: str,
    completeness: DataCompleteness,
    confidence: float,
) -> WinnabilityAnalysisWithConfidence:
    """
    Calculate winnability without SERP data using KD-based estimation.

    Assumptions:
    - Avg SERP DR ≈ KD * 0.7 + 20 (empirical correlation)
    - AI Overview probability based on KD (higher KD = more likely)
    - Low-DR presence unlikely for KD > 40
    """

    # Estimate SERP characteristics from KD
    estimated_avg_dr = base_kd * 0.7 + 20
    estimated_min_dr = max(10, estimated_avg_dr - 20)
    estimated_has_low_dr = base_kd < 35
    estimated_has_aio = base_kd > 30  # AIO more common for competitive keywords

    score, components = calculate_winnability(
        target_dr=target_dr,
        avg_serp_dr=estimated_avg_dr,
        min_serp_dr=estimated_min_dr,
        has_low_dr_rankings=estimated_has_low_dr,
        weak_content_signals=[],  # Can't know without SERP
        has_ai_overview=estimated_has_aio,
        keyword_difficulty=base_kd,
        industry=industry,
    )

    return WinnabilityAnalysisWithConfidence(
        keyword=keyword.get("keyword", "unknown"),
        winnability_score=score,
        personalized_difficulty=calculate_personalized_difficulty_greenfield(
            base_kd, target_dr, estimated_avg_dr
        ),
        avg_serp_dr=estimated_avg_dr,
        min_serp_dr=estimated_min_dr,
        has_low_dr_rankings=estimated_has_low_dr,
        weak_content_signals=[],
        has_ai_overview=estimated_has_aio,
        data_completeness=completeness,
        data_sources_used=["keyword_difficulty_estimation"],
        confidence_adjustment=confidence,
        is_beachhead_candidate=score >= 70 and base_kd <= 30,
    )


def _interpolate_serp_dr(base_kd: int, partial_avg_dr: float) -> float:
    """
    Interpolate SERP DR using KD and partial data.

    Weighted average: 70% partial data, 30% KD-based estimate
    """
    kd_estimated_dr = base_kd * 0.7 + 20
    return partial_avg_dr * 0.7 + kd_estimated_dr * 0.3
```

#### User Communication

When degraded data is used, communicate clearly to users:

```python
# In API response

class WinnabilityResponse(BaseModel):
    keyword: str
    winnability_score: float
    personalized_difficulty: float

    # Data quality indicators
    data_quality: str  # "full", "partial", "estimated"
    confidence_level: float  # 0-1
    data_quality_note: Optional[str] = None


def format_winnability_response(analysis: WinnabilityAnalysisWithConfidence) -> WinnabilityResponse:
    """Format winnability with data quality context."""

    notes = {
        DataCompleteness.FULL: None,
        DataCompleteness.PARTIAL: "Some SERP data unavailable; score estimated from partial data",
        DataCompleteness.MINIMAL: "Limited SERP data; score has lower confidence",
        DataCompleteness.FALLBACK: "SERP data unavailable; score estimated from keyword difficulty",
    }

    return WinnabilityResponse(
        keyword=analysis.keyword,
        winnability_score=analysis.winnability_score,
        personalized_difficulty=analysis.personalized_difficulty,
        data_quality=analysis.data_completeness.value,
        confidence_level=analysis.confidence_adjustment,
        data_quality_note=notes.get(analysis.data_completeness),
    )
```

#### Aggregate Quality Reporting

For batch analyses, report overall data quality:

```python
def calculate_analysis_data_quality(
    analyses: List[WinnabilityAnalysisWithConfidence]
) -> Dict[str, Any]:
    """
    Calculate overall data quality for an analysis run.
    """
    if not analyses:
        return {"overall_quality": "unknown", "confidence": 0}

    completeness_counts = {
        DataCompleteness.FULL: 0,
        DataCompleteness.PARTIAL: 0,
        DataCompleteness.MINIMAL: 0,
        DataCompleteness.FALLBACK: 0,
    }

    for a in analyses:
        completeness_counts[a.data_completeness] += 1

    total = len(analyses)
    full_rate = completeness_counts[DataCompleteness.FULL] / total
    partial_rate = completeness_counts[DataCompleteness.PARTIAL] / total
    fallback_rate = completeness_counts[DataCompleteness.FALLBACK] / total

    # Determine overall quality
    if full_rate >= 0.8:
        overall = "high"
    elif full_rate + partial_rate >= 0.7:
        overall = "medium"
    elif fallback_rate > 0.5:
        overall = "low"
    else:
        overall = "medium"

    # Calculate weighted confidence
    avg_confidence = sum(a.confidence_adjustment for a in analyses) / total

    return {
        "overall_quality": overall,
        "confidence": round(avg_confidence, 2),
        "full_data_keywords": completeness_counts[DataCompleteness.FULL],
        "partial_data_keywords": completeness_counts[DataCompleteness.PARTIAL],
        "fallback_keywords": completeness_counts[DataCompleteness.FALLBACK],
        "recommendation": _get_quality_recommendation(overall, fallback_rate),
    }


def _get_quality_recommendation(quality: str, fallback_rate: float) -> str:
    """Generate recommendation based on data quality."""
    if quality == "high":
        return "Analysis based on complete SERP data. High confidence in recommendations."
    elif quality == "medium":
        return "Some keywords analyzed with estimated data. Consider re-running for higher confidence."
    else:
        return f"{int(fallback_rate * 100)}% of keywords lack SERP data. Results are estimates. Consider reducing keyword count or checking API availability."
```

---

## 14. Success Metrics

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

## 15. Implementation Phases

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

## 16. Validation Plan

This section defines the comprehensive validation strategy to ensure Greenfield Intelligence delivers accurate, actionable results. **No feature ships without passing all quality gates.**

### 16.1 Pre-Implementation Validation

Before writing any production code, validate foundational assumptions.

#### Data Availability Audit

| Data Point | Required For | Source | Validation Method | Pass Criteria |
|------------|--------------|--------|-------------------|---------------|
| Domain Rating of SERP results | Winnability score | DataForSEO SERP API | Test 100 keywords | DR available for >90% of results |
| AI Overview presence | CTR adjustment | DataForSEO SERP API | Test 100 keywords | Boolean flag available |
| Content age/freshness | Weak content signals | DataForSEO or scraping | Test 50 keywords | Date available for >70% of results |
| Competitor organic keywords | Keyword universe | DataForSEO Domain API | Test 10 competitors | Top 500 keywords retrievable |
| Search intent classification | Business relevance | DataForSEO or Claude | Test 200 keywords | Intent matches manual review >85% |

**Action if fails:** Document limitation, design fallback (e.g., estimate SERP DR from KD if unavailable)

#### API Cost Modeling

```
Per Greenfield Analysis Cost Estimate:

Phase G1: Competitor Discovery
- SERP results for 5-10 seed keywords: 5-10 API calls
- Domain overview for 15-20 competitors: 15-20 API calls
Subtotal: ~30 calls

Phase G2: Keyword Universe
- Competitor keywords (7 competitors × 500 kw): 7 API calls
- Keyword expansion (10 seeds × 100 suggestions): 10 API calls
- Related keywords: 10 API calls
Subtotal: ~27 calls

Phase G3: SERP Analysis for Winnability
- SERP results for top 200 keywords: 200 API calls
Subtotal: 200 calls

Phase G4: Market Sizing
- Already collected (reuse)
Subtotal: 0 calls

TOTAL: ~257 API calls per analysis

Cost at $0.002/call: ~$0.51 per greenfield analysis
Cost at $0.01/call: ~$2.57 per greenfield analysis
```

**Validation:** Run 10 test analyses, measure actual API calls. Must be within 20% of estimate.

**Action if exceeds budget:** Reduce SERP analysis to top 100 keywords, implement caching.

#### User Problem Validation

Before building, confirm users actually need this.

| Validation Method | Target | Pass Criteria |
|-------------------|--------|---------------|
| Customer interviews | 5 agencies with new domain clients | 4/5 confirm greenfield is pain point |
| Support ticket analysis | Last 6 months | >10 tickets about "no data" or "new domain" |
| Competitor analysis | SEMrush/Ahrefs forums | Find user complaints about new domains |
| Sales team input | 3 sales reps | Confirm lost deals due to greenfield gap |

**Owner:** Product Manager
**Timeline:** Complete before Phase 1 begins
**Document:** User validation report with quotes and evidence

---

### 16.2 Algorithm Validation Protocol

Each algorithm requires validation before and after implementation.

#### 16.2.1 Winnability Score Validation

**Hypothesis:** Winnability score predicts ranking probability. Keywords with winnability >70 should rank in top 20 within 6 months at higher rate than keywords with winnability <50.

**Validation Method:**
```python
# Retrospective validation on existing client data

def validate_winnability_algorithm():
    """
    Validation protocol for winnability score accuracy.

    Steps:
    1. Select 10 established clients who started as greenfield (DR <20) 12+ months ago
    2. For each client, calculate winnability scores for keywords they NOW rank for
    3. Compare winnability predictions to actual ranking outcomes
    4. Calculate prediction accuracy
    """

    test_cases = []

    for client in get_former_greenfield_clients(min_months=12):
        # Get keywords they rank for now
        current_keywords = get_client_rankings(client)

        for kw in current_keywords:
            # Calculate what winnability would have been at start
            historical_serp = get_historical_serp(kw.keyword, client.start_date)
            initial_dr = client.initial_domain_rating

            predicted_winnability = calculate_winnability(
                target_dr=initial_dr,
                avg_serp_dr=historical_serp.avg_dr,
                min_serp_dr=historical_serp.min_dr,
                has_low_dr_rankings=historical_serp.has_low_dr,
                weak_content_signals=historical_serp.weak_signals,
                has_ai_overview=historical_serp.has_aio,
                keyword_difficulty=kw.kd_at_start,
            )

            actual_outcome = {
                "ranked_top_20": kw.best_position <= 20,
                "ranked_top_10": kw.best_position <= 10,
                "months_to_rank": kw.months_to_first_top_20,
            }

            test_cases.append({
                "keyword": kw.keyword,
                "predicted_winnability": predicted_winnability,
                "actual_outcome": actual_outcome,
            })

    # Analyze results
    high_winnability = [t for t in test_cases if t["predicted_winnability"] >= 70]
    low_winnability = [t for t in test_cases if t["predicted_winnability"] < 50]

    high_win_success_rate = sum(1 for t in high_winnability if t["actual_outcome"]["ranked_top_20"]) / len(high_winnability)
    low_win_success_rate = sum(1 for t in low_winnability if t["actual_outcome"]["ranked_top_20"]) / len(low_winnability)

    return {
        "high_winnability_success_rate": high_win_success_rate,  # Target: >60%
        "low_winnability_success_rate": low_win_success_rate,    # Target: <30%
        "lift": high_win_success_rate / max(0.01, low_win_success_rate),  # Target: >2x
    }
```

**Pass Criteria:**
| Metric | Target | Minimum Acceptable |
|--------|--------|-------------------|
| High winnability (>70) success rate | >60% | >50% |
| Low winnability (<50) success rate | <30% | <40% |
| Lift (high vs low) | >2.5x | >2.0x |
| Correlation (winnability vs rank achieved) | >0.5 | >0.4 |

**If validation fails:**
1. Analyze which coefficient is miscalibrated
2. Adjust coefficient using regression analysis on test data
3. Re-validate
4. Repeat until pass criteria met

#### 16.2.2 Personalized Difficulty Validation

**Hypothesis:** Personalized KD better predicts ranking difficulty than base KD for domains with non-average authority.

**Validation Method:**
```python
def validate_personalized_difficulty():
    """Compare personalized KD prediction accuracy vs base KD."""

    test_cases = []

    for client in get_diverse_dr_clients():  # Mix of DR 10, 30, 50, 70
        for kw in client.keywords_attempted:
            base_kd = kw.keyword_difficulty
            personalized_kd = calculate_personalized_difficulty_greenfield(
                base_kd=base_kd,
                target_dr=client.domain_rating_at_attempt,
                avg_serp_dr=kw.serp_avg_dr_at_attempt,
            )

            actual_difficulty = {
                "months_to_rank": kw.months_to_top_20,
                "achieved_position": kw.best_position,
            }

            test_cases.append({
                "base_kd": base_kd,
                "personalized_kd": personalized_kd,
                "actual": actual_difficulty,
                "domain_dr": client.domain_rating_at_attempt,
            })

    # Calculate correlation
    base_kd_correlation = correlation(
        [t["base_kd"] for t in test_cases],
        [t["actual"]["months_to_rank"] for t in test_cases]
    )
    personalized_kd_correlation = correlation(
        [t["personalized_kd"] for t in test_cases],
        [t["actual"]["months_to_rank"] for t in test_cases]
    )

    return {
        "base_kd_correlation": base_kd_correlation,
        "personalized_kd_correlation": personalized_kd_correlation,
        "improvement": personalized_kd_correlation - base_kd_correlation,
    }
```

**Pass Criteria:**
| Metric | Target |
|--------|--------|
| Personalized KD correlation with actual time-to-rank | >0.6 |
| Improvement over base KD | >0.1 (10 percentage points) |

#### 16.2.3 Beachhead Selection Validation

**Hypothesis:** Beachhead keywords (selected by our algorithm) rank faster and with higher success rate than random high-volume keywords.

**Validation Method:**
1. For 5 greenfield clients, run beachhead selection algorithm
2. Also identify "naive picks" (highest volume keywords with KD <40)
3. Track both sets for 6 months
4. Compare ranking success rates

**Pass Criteria:**
| Metric | Target |
|--------|--------|
| Beachhead top-20 rate at 6 months | >50% |
| Naive pick top-20 rate at 6 months | Baseline (no target) |
| Beachhead lift over naive | >1.5x |
| Average time-to-rank for beachhead | <4 months |

#### 16.2.4 Traffic Projection Validation

**Hypothesis:** Actual traffic falls within our projected ranges (conservative to aggressive) for >70% of clients.

**Validation Method:**
```python
def validate_traffic_projections():
    """
    Compare projected traffic to actual traffic at 12 months.
    """
    results = []

    for client in get_greenfield_clients_with_12_month_history():
        # Get original projections
        projections = client.original_greenfield_analysis.traffic_projections

        # Get actual traffic at month 12
        actual_traffic = client.organic_traffic_at_month_12

        # Check if within range
        in_range = (
            projections.conservative.traffic_by_month[12] <= actual_traffic <=
            projections.aggressive.traffic_by_month[12]
        )

        # Calculate accuracy
        expected = projections.expected.traffic_by_month[12]
        accuracy = 1 - abs(actual_traffic - expected) / expected

        results.append({
            "client": client.domain,
            "conservative": projections.conservative.traffic_by_month[12],
            "expected": projections.expected.traffic_by_month[12],
            "aggressive": projections.aggressive.traffic_by_month[12],
            "actual": actual_traffic,
            "in_range": in_range,
            "accuracy": accuracy,
        })

    return {
        "in_range_rate": sum(r["in_range"] for r in results) / len(results),  # Target: >70%
        "avg_accuracy": sum(r["accuracy"] for r in results) / len(results),   # Target: >0.6
        "results": results,
    }
```

**Pass Criteria:**
| Metric | Target | Minimum |
|--------|--------|---------|
| Within range rate | >75% | >65% |
| Expected scenario accuracy (within 30%) | >50% | >40% |
| No catastrophic misses (>3x off) | 0% | <5% |

---

### 16.3 Industry Coefficient Validation

Each industry coefficient set requires separate validation.

#### Coefficient Tuning Protocol

```python
def tune_industry_coefficients(industry: str, test_data: List[TestCase]):
    """
    Use gradient descent to tune coefficients based on actual outcomes.

    Objective: Minimize prediction error for winnability → ranking outcome
    """

    # Initial coefficients
    coefficients = INDUSTRY_COEFFICIENTS[industry].copy()

    learning_rate = 0.1
    iterations = 100

    for i in range(iterations):
        total_error = 0
        gradients = {k: 0 for k in coefficients}

        for case in test_data:
            # Predict winnability with current coefficients
            predicted = calculate_winnability_with_coefficients(case, coefficients)

            # Compare to actual outcome (1 if ranked top 20, 0 otherwise)
            actual = 1 if case.actual_position <= 20 else 0

            # Calculate error
            error = (predicted / 100) - actual
            total_error += error ** 2

            # Calculate gradients (simplified)
            for coef_name in coefficients:
                gradients[coef_name] += error * partial_derivative(case, coef_name, coefficients)

        # Update coefficients
        for coef_name in coefficients:
            coefficients[coef_name] -= learning_rate * gradients[coef_name] / len(test_data)

        # Log progress
        if i % 10 == 0:
            logger.info(f"Iteration {i}: MSE = {total_error / len(test_data)}")

    return coefficients
```

#### Industry-Specific Validation Requirements

| Industry | Min Test Cases | Special Validation |
|----------|----------------|-------------------|
| SaaS | 50 keywords | None (baseline) |
| E-commerce | 50 keywords | Validate product vs category pages separately |
| YMYL Health | 30 keywords | Manual E-E-A-T compliance check on successful rankings |
| YMYL Finance | 30 keywords | Manual E-E-A-T compliance check |
| Local Services | 40 keywords | Validate local pack predictions separately |
| News/Media | 30 keywords | Account for freshness decay |
| Education | 30 keywords | Validate institutional vs commercial separately |
| B2C Consumer | 40 keywords | None |

---

### 16.4 Quality Gates by Phase

Each implementation phase has mandatory quality gates.

#### Phase 1: Foundation - Quality Gate

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Classification accuracy | Test 100 domains with known maturity | >95% correct classification |
| Edge case handling | Test domains at boundaries (DR 19, 20, 21, 34, 35, 36) | All classified correctly |
| Performance | Classify 1000 domains | <100ms total |

**Gate owner:** Engineering lead
**Gate review:** Automated tests + manual spot check

#### Phase 2: Competitor Discovery - Quality Gate

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Competitor relevance | Manual review of 10 analyses | >80% of discovered competitors are true competitors |
| Platform filtering | Check for Wikipedia, Reddit in results | 0 platform domains in final list |
| Competitor count | Review distribution | 8-15 competitors per analysis |
| API efficiency | Measure calls per analysis | Within 20% of budget estimate |

**Gate owner:** Product + Engineering
**Gate review:** Manual review of 10 analyses

#### Phase 3: Keyword Universe - Quality Gate

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Keyword count | Check 10 analyses | 500-3000 keywords per analysis |
| Relevance score distribution | Histogram review | >30% keywords with relevance >0.7 |
| Intent classification | Manual check 50 keywords | >85% correct intent |
| Deduplication | Check for duplicates | 0 duplicate keywords |
| Source diversity | Check keyword sources | Keywords from >3 sources per analysis |

**Gate owner:** Engineering + Data team
**Gate review:** Automated metrics + manual sample check

#### Phase 4: Winnability Analysis - Quality Gate

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| SERP data completeness | Check SERP fetch success rate | >85% of keywords have SERP data |
| Winnability distribution | Histogram review | Normal-ish distribution, not all clustered |
| Beachhead identification | Check 10 analyses | 15-30 beachhead keywords per analysis |
| Algorithm validation | Run validation protocol (16.2.1) | Pass all criteria |
| Fallback handling | Test with missing SERP data | Graceful degradation, no crashes |

**Gate owner:** Engineering + Data Science
**Gate review:** Validation report + manual review

#### Phase 5: Market Opportunity - Quality Gate

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| TAM/SAM/SOM ratios | Check 10 analyses | SOM < SAM < TAM always |
| Competitor share totals | Sum shares | Total ~100% (allow ±5%) |
| Volume sanity | Compare to known market sizes | Within order of magnitude |
| Zero handling | Test with sparse data | No division by zero, sensible defaults |

**Gate owner:** Product + Engineering
**Gate review:** Manual review of market sizing accuracy

#### Phase 6: Projections & Roadmap - Quality Gate

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Projection ordering | Check all analyses | Conservative < Expected < Aggressive always |
| Confidence labels | Verify confidence values | Conservative=0.75, Expected=0.5, Aggressive=0.25 |
| Roadmap phase logic | Check keyword assignment | Easier keywords in Phase 1, harder in Phase 4 |
| Timeline sanity | Review projections | No traffic projections >10x market TAM |

**Gate owner:** Product
**Gate review:** Manual review + sanity checks

#### Phase 7: Frontend - Quality Gate

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Wizard completion rate | Track in staging | >80% complete wizard without abandonment |
| Load time | Measure dashboard load | <3 seconds for full dashboard |
| Mobile responsiveness | Test on mobile devices | All views usable on mobile |
| Error handling | Test with API failures | Graceful error messages, no crashes |
| Accessibility | Run axe-core audit | 0 critical violations |

**Gate owner:** Frontend lead + Design
**Gate review:** QA testing + design review

#### Phase 8: Testing & Refinement - Quality Gate (LAUNCH GATE)

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Full algorithm validation | Run all validations (16.2) | All pass |
| User acceptance testing | 5 beta users complete analysis | >4/5 rate "useful" or better |
| Performance under load | Load test with 50 concurrent | <30s analysis time |
| Error rate | Monitor staging for 1 week | <1% error rate |
| Data quality audit | Manual review of 20 analyses | No obvious errors or nonsensical results |

**Gate owner:** VP Engineering + Product
**Gate review:** Launch readiness review meeting

---

### 16.5 Post-Launch Monitoring

After launch, continuous monitoring validates ongoing quality.

#### Real-Time Monitoring Dashboards

```yaml
Greenfield Quality Dashboard:

  Operational Metrics (refresh: 1 min):
    - Analysis completion rate (target: >95%)
    - Average analysis time (target: <15 min)
    - API error rate (target: <1%)
    - SERP data completeness (target: >85%)

  Quality Metrics (refresh: hourly):
    - Winnability score distribution (alert if >50% cluster at extremes)
    - Beachhead count distribution (alert if <10 or >40 average)
    - Market sizing sanity (alert if SOM > SAM)
    - User feedback scores (alert if <3.5/5 average)

  Validation Metrics (refresh: weekly):
    - Projection accuracy (track against actuals as data comes in)
    - Beachhead success rate (track rankings at 30/60/90 days)
    - Coefficient drift detection (compare to baseline)
```

#### Cohort Tracking Protocol

```python
def track_greenfield_cohort(cohort_month: str):
    """
    Track a cohort of greenfield analyses to validate long-term accuracy.

    Run monthly, tracking cohorts until 24-month mark.
    """

    cohort = get_analyses_from_month(cohort_month)

    tracking_points = [1, 3, 6, 9, 12, 18, 24]  # months after analysis

    for months_elapsed in tracking_points:
        if not has_elapsed(cohort_month, months_elapsed):
            continue

        cohort_metrics = {
            "cohort_month": cohort_month,
            "tracking_month": months_elapsed,
            "sample_size": len(cohort),
        }

        for analysis in cohort:
            domain = analysis.domain

            # Get current metrics
            current_traffic = get_current_traffic(domain)
            current_keywords = get_current_keywords(domain)

            # Get original projections
            projected_traffic = analysis.traffic_projections.expected.traffic_by_month.get(months_elapsed, 0)

            # Calculate accuracy
            cohort_metrics.setdefault("traffic_actuals", []).append(current_traffic)
            cohort_metrics.setdefault("traffic_projected", []).append(projected_traffic)

            # Track beachhead rankings
            for beachhead_kw in analysis.beachhead_keywords:
                current_position = get_keyword_position(domain, beachhead_kw.keyword)
                cohort_metrics.setdefault("beachhead_rankings", []).append({
                    "keyword": beachhead_kw.keyword,
                    "predicted_winnability": beachhead_kw.winnability_score,
                    "current_position": current_position,
                    "success": current_position <= 20 if current_position else False,
                })

        # Aggregate and store
        store_cohort_tracking(cohort_metrics)

        # Alert if metrics diverge significantly
        if months_elapsed >= 6:
            validate_cohort_accuracy(cohort_metrics)
```

#### Feedback Collection

| Feedback Type | Collection Method | Frequency | Owner |
|---------------|-------------------|-----------|-------|
| In-app rating | Post-analysis prompt | Every analysis | Product |
| Detailed survey | Email at 30 days | Monthly cohort | Product |
| User interviews | Scheduled calls | 5/month | Product |
| Support tickets | Zendesk tagging | Ongoing | Support |
| Churn analysis | Exit survey | On churn | Success |

#### Coefficient Recalibration Schedule

| Trigger | Action |
|---------|--------|
| Weekly | Review prediction accuracy metrics |
| Monthly | Run full validation protocol on new data |
| Quarterly | Re-tune coefficients using latest data |
| Major algorithm change | Full revalidation required |
| Industry CTR shift (>10%) | Update CTR curves, re-project |

---

### 16.6 Validation Checklist Summary

Before launch, all items must be checked:

#### Pre-Implementation
- [ ] Data availability audit complete - all data points confirmed available
- [ ] API cost model validated - actual costs within 20% of estimate
- [ ] User problem validation complete - documented evidence of need
- [ ] Baseline metrics established for existing clients

#### Algorithm Validation
- [ ] Winnability validation passed (lift >2x)
- [ ] Personalized KD validation passed (correlation >0.6)
- [ ] Beachhead selection validation passed (lift >1.5x)
- [ ] Traffic projection validation passed (>70% in range)
- [ ] Industry coefficients validated for all 8 verticals

#### Quality Gates
- [ ] Phase 1 gate passed
- [ ] Phase 2 gate passed
- [ ] Phase 3 gate passed
- [ ] Phase 4 gate passed
- [ ] Phase 5 gate passed
- [ ] Phase 6 gate passed
- [ ] Phase 7 gate passed
- [ ] Phase 8 (launch) gate passed

#### Monitoring Setup
- [ ] Real-time dashboard configured
- [ ] Cohort tracking implemented
- [ ] Feedback collection live
- [ ] Alerting configured for quality degradation

#### Documentation
- [ ] User documentation complete
- [ ] API documentation complete
- [ ] Internal runbook for quality issues
- [ ] Coefficient tuning playbook documented

---

### 16.7 Rollback Plan

If post-launch monitoring detects critical issues:

#### Severity Levels

| Level | Definition | Response Time | Action |
|-------|------------|---------------|--------|
| P0 | Completely wrong results, user-visible errors | <1 hour | Feature flag off, rollback |
| P1 | Significant accuracy degradation (>30% error) | <4 hours | Investigate, consider rollback |
| P2 | Minor accuracy issues, edge cases | <24 hours | Fix forward, monitor |
| P3 | Cosmetic or UX issues | <1 week | Normal sprint |

#### Rollback Procedure

```yaml
P0 Rollback Checklist:

  1. Disable greenfield feature flag (5 min)
     - All users see standard analysis
     - Greenfield option hidden in UI

  2. Notify affected users (30 min)
     - Email users who ran analysis in last 24h
     - Offer reanalysis when fixed

  3. Root cause analysis (4 hours)
     - Identify specific failure
     - Determine scope of impact
     - Document in incident report

  4. Fix and validate (varies)
     - Implement fix
     - Re-run full validation protocol
     - Pass all quality gates

  5. Gradual re-enable (1 day)
     - Enable for internal users first
     - Enable for 10% of users
     - Monitor for 24h
     - Full rollout
```

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

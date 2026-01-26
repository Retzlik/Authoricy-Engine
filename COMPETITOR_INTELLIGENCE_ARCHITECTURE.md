# Competitor Intelligence Architecture

## The Definitive Guide to World-Class Competitor Discovery

**Version:** 1.0
**Status:** Architecture Specification
**Last Updated:** 2025-01-26

---

## Table of Contents

1. [The Core Problem](#1-the-core-problem)
2. [What We Must Know First](#2-what-we-must-know-first)
3. [Data Sources Deep Dive](#3-data-sources-deep-dive)
4. [The Complete Pipeline](#4-the-complete-pipeline)
5. [Module Architecture](#5-module-architecture)
6. [Implementation Specifications](#6-implementation-specifications)
7. [Quality Assurance](#7-quality-assurance)
8. [Cost Analysis](#8-cost-analysis)
9. [Migration Strategy](#9-migration-strategy)

---

## 1. The Core Problem

### 1.1 Why Competitor Discovery is Hard

Finding "competitors" seems simple but is actually one of the hardest problems in market intelligence:

```
THE FUNDAMENTAL CHALLENGE
========================

Input:  "example.com"
Output: "10 on-point competitors that will drive our entire analysis"

The gap between these is ENORMOUS.
```

**Why it's hard:**

1. **"Competitor" is context-dependent**
   - A dictionary site is NOT a competitor to a SaaS company, even if they rank for the same keywords
   - A $50M enterprise vendor is NOT comparable to a $2M startup, even if they sell similar products
   - A US-only company is NOT relevant for UK market analysis

2. **No single data source has the truth**
   - SEO tools find keyword overlap, not business competition
   - Business databases have company info but miss SEO dynamics
   - Web searches are noisy and require interpretation

3. **Garbage in, garbage out**
   - Wrong competitors → wrong keyword opportunities → wrong strategy → wasted effort
   - This is the MOST consequential decision in our entire pipeline

### 1.2 The Quality Bar

Our competitor intelligence must be:

| Criterion | Requirement | Why |
|-----------|-------------|-----|
| **Relevant** | Same industry, same audience | Keyword stealing only works from real competitors |
| **Balanced** | Mix of peer/aspirational/emerging | Different competitors serve different strategic purposes |
| **Verifiable** | Clear reasoning for each selection | User must understand and trust the choices |
| **Market-aware** | Operates in target geography | UK analysis needs UK-relevant competitors |
| **Actionable** | Competitors we can actually learn from | Giant platforms (Amazon, Google) are not useful |

---

## 2. What We Must Know First

### 2.1 The Context Acquisition Problem

**Critical insight:** We cannot find competitors until we deeply understand the target business.

```
WRONG APPROACH
==============
1. Get domain name
2. Search "[domain] competitors"
3. Return top 10 results

Result: Generic, often wrong competitors

RIGHT APPROACH
==============
1. Get domain name
2. DEEPLY understand what this business does
3. Understand WHO they serve
4. Understand HOW they make money
5. Understand WHERE they operate
6. THEN search for competitors with full context
7. Evaluate each candidate against context

Result: Precisely targeted, relevant competitors
```

### 2.2 Required Context Dimensions

Before searching for competitors, we MUST know:

#### Dimension 1: Business Identity
```yaml
business_identity:
  company_name: "Acme Corp"
  primary_offering: "Project management software"
  offering_category: "SaaS / Productivity"
  value_proposition: "AI-powered project management for remote teams"
  key_features:
    - "AI task prioritization"
    - "Time tracking"
    - "Team collaboration"
  founding_year: 2020  # Helps gauge maturity
```

#### Dimension 2: Target Market
```yaml
target_market:
  customer_type: "B2B"
  company_size: ["SMB", "Mid-market"]  # NOT enterprise
  industries_served: ["Technology", "Marketing agencies", "Consulting"]
  geographic_focus: ["United States", "United Kingdom", "Europe"]
  decision_maker: "Operations managers, Team leads"
```

#### Dimension 3: Business Model
```yaml
business_model:
  type: "SaaS"
  pricing_model: "Subscription"
  price_tier: "Mid-market"  # $20-100/user/month
  price_range: "$29-99/user/month"
  sales_motion: "Product-led growth with sales assist"
```

#### Dimension 4: Competitive Position
```yaml
competitive_position:
  market_maturity: "Growth stage"
  main_differentiator: "AI capabilities"
  perceived_competitors:  # From their own website
    - "Monday.com"
    - "Asana"
  positioning_statement: "The AI-first alternative to legacy PM tools"
```

### 2.3 Context Acquisition Sources

| Source | What It Provides | Reliability |
|--------|------------------|-------------|
| **Homepage** | Value proposition, key features | High |
| **About page** | Company story, founding, mission | High |
| **Pricing page** | Business model, target tier | Very High |
| **Product pages** | Detailed features, use cases | High |
| **Blog/Resources** | Industry focus, thought leadership | Medium |
| **Case studies** | Target customer profile | Very High |
| **Footer/Legal** | Geographic presence, company info | High |

---

## 3. Data Sources Deep Dive

### 3.1 Source Matrix

| Source | Type | Best For | Limitations | Cost |
|--------|------|----------|-------------|------|
| **Website Scraping** | Context | Understanding target | Requires interpretation | Low |
| **Perplexity API** | Discovery | Finding business competitors | Rate limits | Medium |
| **DataForSEO** | SEO Intel | SEO competitors, metrics | Only SEO perspective | Already have |
| **G2 Crowd API** | Business Intel | SaaS alternatives | Only software | High |
| **Crunchbase API** | Business Intel | Company data, funding | Limited coverage | High |
| **SimilarWeb API** | Traffic Intel | Audience overlap | Expensive | Very High |
| **SERP Analysis** | Discovery | Keyword competitors | Noisy results | Low |

### 3.2 Source 1: Website Scraping (Context Acquisition)

**Purpose:** Extract deep context about the TARGET business

**Implementation Options:**

```
Option A: Firecrawl (Recommended)
================================
- Managed service, handles JS rendering
- Clean markdown output
- Rate: ~$0.001/page
- API: https://firecrawl.dev

Option B: Self-hosted (Playwright + Custom)
==========================================
- Full control
- No external dependency
- Requires infrastructure
- More maintenance

Option C: ScrapingBee / Browserless
===================================
- Managed headless browsers
- Handle anti-bot measures
- Mid-range cost
```

**What to scrape:**

```python
TARGET_PAGES = [
    "/",                    # Homepage - value proposition
    "/about",               # Company info
    "/about-us",
    "/pricing",             # Business model (CRITICAL)
    "/product",             # Features
    "/features",
    "/solutions",           # Use cases
    "/customers",           # Target market
    "/case-studies",
]

EXTRACTION_TARGETS = {
    "homepage": {
        "h1": "primary_headline",
        "meta_description": "value_proposition",
        "nav_items": "product_structure",
    },
    "pricing": {
        "plan_names": "pricing_tiers",
        "prices": "price_points",
        "features_per_plan": "feature_matrix",
    },
    "about": {
        "company_description": "company_story",
        "team_size_indicators": "company_size",
        "founding_info": "company_age",
    }
}
```

**Output Schema:**

```python
@dataclass
class ScrapedContext:
    domain: str

    # Raw content
    homepage_content: str
    about_content: Optional[str]
    pricing_content: Optional[str]

    # Extracted structure
    primary_headline: str
    navigation_structure: List[str]
    pricing_tiers: List[PricingTier]

    # Metadata
    pages_scraped: int
    scrape_timestamp: datetime
    scrape_quality_score: float  # 0-1
```

### 3.3 Source 2: Perplexity API (Intelligent Discovery)

**Purpose:** AI-powered web search for finding competitors

**Why Perplexity is CRITICAL:**

```
Traditional SERP Search:
Query: "Acme alternatives"
Result: Random blog posts, affiliate sites, outdated lists

Perplexity Search:
Query: "Who are the main competitors to Acme Corp project management software?"
Result: Synthesized, contextual answer with real competitors
```

**Implementation:**

```python
PERPLEXITY_QUERIES = [
    # Direct competitor queries
    {
        "query": "Who are the main competitors to {company_name} in the {industry} space?",
        "purpose": "direct_competitors"
    },
    {
        "query": "What are the best alternatives to {company_name} for {use_case}?",
        "purpose": "alternatives"
    },

    # Market landscape queries
    {
        "query": "Who are the leading companies in {industry} for {target_audience}?",
        "purpose": "market_leaders"
    },
    {
        "query": "What startups are disrupting the {industry} market in 2024-2025?",
        "purpose": "emerging_competitors"
    },

    # Specific comparison queries
    {
        "query": "{company_name} vs competitors comparison",
        "purpose": "head_to_head"
    }
]
```

**API Integration:**

```python
class PerplexityClient:
    """
    Perplexity API client for intelligent competitor discovery.

    API Docs: https://docs.perplexity.ai/
    Pricing: ~$5/1000 queries (sonar model)
    """

    BASE_URL = "https://api.perplexity.ai/chat/completions"

    async def search_competitors(
        self,
        company_name: str,
        industry: str,
        context: ScrapedContext,
    ) -> List[DiscoveredCompetitor]:
        """
        Use Perplexity to find competitors with full context.
        """
        system_prompt = f"""You are a competitive intelligence analyst.

Context about the target company:
- Company: {company_name}
- Industry: {industry}
- Value proposition: {context.primary_headline}
- Pricing: {context.pricing_tiers}

Your task is to identify REAL business competitors - companies that:
1. Sell similar products/services
2. Target similar customers
3. Compete for the same budget

DO NOT include:
- Generic platforms (Google, Amazon, Microsoft)
- Content sites / blogs
- Unrelated businesses that happen to rank for similar keywords"""

        # Run multiple queries for comprehensive coverage
        all_competitors = []

        for query_template in PERPLEXITY_QUERIES:
            query = query_template["query"].format(
                company_name=company_name,
                industry=industry,
                use_case=context.primary_headline,
                target_audience=context.target_audience,
            )

            response = await self._query(
                query=query,
                system=system_prompt,
                model="sonar",  # Fast, good for search
            )

            # Extract company names from response
            competitors = self._extract_companies(response)
            all_competitors.extend(competitors)

        return self._deduplicate(all_competitors)
```

**Perplexity Response Parsing:**

```python
def _extract_companies(self, response: str) -> List[DiscoveredCompetitor]:
    """
    Extract company names and domains from Perplexity response.

    Perplexity returns prose - we need to extract structured data.
    """
    # Use Claude to extract structured data from prose
    extraction_prompt = f"""Extract all company names mentioned as competitors from this text.

TEXT:
{response}

Return a JSON array of objects:
[
    {{
        "company_name": "Company Name",
        "domain": "company.com",  // Best guess if not mentioned
        "context": "Why they were mentioned as a competitor"
    }}
]

Only include actual companies, not generic categories."""

    # This secondary AI call ensures clean extraction
    return await self.claude_client.extract_json(extraction_prompt)
```

### 3.4 Source 3: G2 Crowd / Capterra (Business Intelligence)

**Purpose:** Structured business competitor data for software companies

**Why G2 is valuable:**

```
G2 Data Structure:
==================
Category: "Project Management"
├── Leaders: [Monday.com, Asana, Smartsheet]
├── High Performers: [ClickUp, Notion, Wrike]
├── Contenders: [Basecamp, Teamwork]
└── Niche: [Hive, Paymo, ProofHub]

This IS the competitive landscape, pre-organized.
```

**API Integration:**

```python
class G2Client:
    """
    G2 Crowd API for software competitive intelligence.

    Note: G2 API is expensive and requires enterprise agreement.
    Alternative: Scrape public G2 category pages (with rate limiting).
    """

    async def get_category_competitors(
        self,
        product_url: str,  # G2 product URL if known
        category: str,
    ) -> List[G2Competitor]:
        """
        Get competitors from G2 category.
        """
        # Option 1: Direct API (if available)
        # Option 2: Scrape category page
        # Option 3: Use Perplexity to query G2 data
        pass

    async def get_alternatives(
        self,
        product_name: str,
    ) -> List[G2Competitor]:
        """
        Get G2's "alternatives" for a product.
        """
        # G2 has dedicated "alternatives to X" pages
        # These are gold for competitor discovery
        pass
```

**Fallback: Perplexity + G2:**

```python
# If no direct G2 API access, use Perplexity to query G2
query = f"site:g2.com alternatives to {product_name}"

# Or more sophisticated:
query = f"According to G2 Crowd, what are the top alternatives to {product_name}?"
```

### 3.5 Source 4: DataForSEO (SEO Intelligence)

**Purpose:** SEO competitor discovery and metrics enrichment

**Already implemented in current system, but needs enhancement:**

```python
class EnhancedDataForSEOClient:
    """
    Enhanced DataForSEO client for competitor intelligence.
    """

    async def get_seo_competitors(
        self,
        domain: str,
        market: str,
    ) -> List[SEOCompetitor]:
        """
        Get SEO competitors (existing functionality).
        """
        return await self.dataforseo_client.get_competitors(domain)

    async def get_keyword_competitors(
        self,
        keywords: List[str],
        market: str,
    ) -> List[SEOCompetitor]:
        """
        NEW: Find who ranks for specific keywords.

        This is different from domain competitors -
        it finds who we'll be competing with for OUR target keywords.
        """
        competitors = {}

        for keyword in keywords[:20]:  # Limit for cost
            serp = await self.get_serp_results(
                keyword=keyword,
                location=market,
            )

            for result in serp.get("organic", [])[:10]:
                domain = result.get("domain")
                if domain not in competitors:
                    competitors[domain] = {
                        "domain": domain,
                        "keywords_overlap": [],
                        "avg_position": 0,
                    }
                competitors[domain]["keywords_overlap"].append({
                    "keyword": keyword,
                    "position": result.get("position"),
                })

        return list(competitors.values())

    async def enrich_competitor_metrics(
        self,
        domains: List[str],
    ) -> Dict[str, CompetitorMetrics]:
        """
        Enrich competitor list with SEO metrics.

        This is called AFTER discovery to add DR, traffic, etc.
        """
        metrics = {}

        for domain in domains:
            overview = await self.get_domain_overview(domain)
            metrics[domain] = CompetitorMetrics(
                domain=domain,
                domain_rating=overview.get("domain_rank", 0),
                organic_traffic=overview.get("organic_traffic", 0),
                organic_keywords=overview.get("organic_keywords", 0),
                backlinks=overview.get("backlinks", 0),
            )

        return metrics
```

### 3.6 Source 5: SERP Analysis (Discovery)

**Purpose:** Find who ranks for brand + competitor queries

**Enhancement over current implementation:**

```python
ENHANCED_SERP_QUERIES = [
    # Brand-based (already have)
    "{brand} alternatives",
    "{brand} competitors",
    "{brand} vs",

    # NEW: Category-based
    "best {category} software",
    "top {category} tools",
    "{category} comparison",

    # NEW: Use-case based
    "best tool for {use_case}",
    "{use_case} software",

    # NEW: Audience-based
    "{category} for {audience}",
    "best {category} for {company_size}",

    # NEW: Problem-based
    "how to {problem_solved}",
    "{problem_solved} tools",
]
```

### 3.7 Source Priority Matrix

For MVP, prioritize sources by value/effort ratio:

```
PRIORITY 1 (Must Have)
======================
1. Website Scraping (Firecrawl)     - Context acquisition
2. Perplexity API                   - Intelligent discovery
3. DataForSEO                       - SEO metrics (already have)

PRIORITY 2 (Should Have)
========================
4. Enhanced SERP Analysis           - Broader discovery
5. Claude Classification            - Purpose-based classification

PRIORITY 3 (Nice to Have)
=========================
6. G2 Crowd Data                    - Business intelligence
7. Crunchbase                       - Company metadata
8. SimilarWeb                       - Traffic data
```

---

## 4. The Complete Pipeline

### 4.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPETITOR INTELLIGENCE PIPELINE                  │
└─────────────────────────────────────────────────────────────────────┘

PHASE 1: CONTEXT ACQUISITION (Before we search)
├── 1.1 Scrape target website (homepage, about, pricing)
├── 1.2 AI analysis of scraped content
├── 1.3 Generate structured business profile
└── 1.4 User validation/enhancement of context (optional)

PHASE 2: MULTI-SOURCE DISCOVERY (Cast a wide net)
├── 2.1 Perplexity: "Competitors to [company]"
├── 2.2 Perplexity: "Alternatives for [use case]"
├── 2.3 Perplexity: "Leaders in [industry]"
├── 2.4 DataForSEO: SEO competitors
├── 2.5 SERP: Brand + alternatives queries
└── 2.6 [Optional] G2/Crunchbase queries

PHASE 3: CANDIDATE PROCESSING (Make sense of results)
├── 3.1 Deduplicate across sources
├── 3.2 Filter excluded domains (platforms, etc.)
├── 3.3 Domain resolution (company name → domain)
└── 3.4 Initial relevance scoring

PHASE 4: ENRICHMENT (Add intelligence)
├── 4.1 Fetch SEO metrics (DR, traffic, keywords)
├── 4.2 Scrape competitor homepages (optional)
├── 4.3 Calculate SERP overlap score
└── 4.4 Estimate business similarity score

PHASE 5: INTELLIGENT CLASSIFICATION (AI analysis)
├── 5.1 Purpose-based classification
│   ├── Benchmark Peer (40% weight)
│   ├── Keyword Source (35% weight)
│   ├── Content Model (15% weight)
│   └── Aspirational (10% weight)
├── 5.2 Threat level assessment
├── 5.3 Confidence scoring
└── 5.4 Generate selection rationale

PHASE 6: SELECTION & RANKING (Pick the best 15)
├── 6.1 Score all candidates
├── 6.2 Ensure purpose balance
├── 6.3 Select top 15
└── 6.4 Generate "why selected" for each

PHASE 7: USER CURATION (Human-in-the-loop)
├── 7.1 Present 15 candidates with rationale
├── 7.2 User removes 5 (REQUIRED)
├── 7.3 [Optional] User adds replacements
└── 7.4 Validate final balance

PHASE 8: POST-VALIDATION (Quality check)
├── 8.1 Check purpose distribution
├── 8.2 Warn if unbalanced
├── 8.3 Lock competitor set
└── 8.4 Proceed to main analysis
```

### 4.2 Phase 1: Context Acquisition (Detailed)

```python
async def acquire_context(
    domain: str,
    user_hints: Optional[UserHints] = None,
) -> BusinessContext:
    """
    Phase 1: Deep understanding of target business.

    This is the FOUNDATION - everything else depends on this.
    """

    # Step 1.1: Scrape target website
    scraper = WebsiteScraper(client=firecrawl_client)
    scraped_data = await scraper.scrape_business_pages(
        domain=domain,
        pages=["homepage", "about", "pricing", "product"],
        timeout_per_page=10,
    )

    # Step 1.2: AI analysis of scraped content
    analyzer = ContextAnalyzer(client=claude_client)
    raw_context = await analyzer.analyze_business(
        scraped_data=scraped_data,
        analysis_prompt=BUSINESS_ANALYSIS_PROMPT,
    )

    # Step 1.3: Generate structured profile
    context = BusinessContext(
        domain=domain,
        company_name=raw_context.company_name,

        # What they do
        primary_offering=raw_context.primary_offering,
        offering_category=raw_context.offering_category,
        key_features=raw_context.key_features,
        value_proposition=raw_context.value_proposition,

        # Who they serve
        customer_type=raw_context.customer_type,  # B2B/B2C
        company_sizes=raw_context.company_sizes,  # SMB/Mid/Enterprise
        industries_served=raw_context.industries_served,

        # Business model
        business_model=raw_context.business_model,  # SaaS/Ecommerce/etc
        pricing_model=raw_context.pricing_model,
        price_tier=raw_context.price_tier,

        # Market
        geographic_focus=raw_context.geographic_focus,
        primary_language=raw_context.primary_language,

        # Competitive hints from their own site
        self_mentioned_competitors=raw_context.self_mentioned_competitors,
        positioning_statement=raw_context.positioning_statement,

        # Meta
        confidence_score=raw_context.confidence_score,
        context_quality=self._assess_context_quality(raw_context),
    )

    # Step 1.4: Enhance with user hints (if provided)
    if user_hints:
        context = self._merge_user_hints(context, user_hints)

    return context
```

**The Business Analysis Prompt:**

```python
BUSINESS_ANALYSIS_PROMPT = """Analyze this company's website content to understand their business.

SCRAPED CONTENT:
{scraped_content}

Extract the following information. Be precise - this will be used to find their competitors.

## Required Analysis:

### 1. Company Identity
- Company name (official name, not domain)
- Primary offering (main product/service in one sentence)
- Offering category (e.g., "Project Management Software", "E-commerce Platform")
- Key features (top 5 differentiating features)
- Value proposition (their main pitch)

### 2. Target Market
- Customer type: B2B, B2C, or Both
- Company sizes served: SMB, Mid-market, Enterprise (can be multiple)
- Industries they focus on (if specific)
- Geographic focus (if apparent)

### 3. Business Model
- Type: SaaS, E-commerce, Marketplace, Services, Content, Other
- Pricing model: Subscription, One-time, Freemium, Usage-based
- Price tier: Budget (<$20/mo), Mid-market ($20-100/mo), Enterprise ($100+/mo)
- Actual prices if visible

### 4. Competitive Position
- Any competitors they mention on their site
- Their positioning statement (how they differentiate)
- Market maturity signals

Return as structured JSON:
```json
{
    "company_name": "...",
    "primary_offering": "...",
    "offering_category": "...",
    "key_features": ["...", "..."],
    "value_proposition": "...",
    "customer_type": "B2B|B2C|Both",
    "company_sizes": ["SMB", "Mid-market"],
    "industries_served": ["...", "..."],
    "geographic_focus": ["...", "..."],
    "business_model": "SaaS|Ecommerce|...",
    "pricing_model": "Subscription|...",
    "price_tier": "Budget|Mid-market|Enterprise",
    "self_mentioned_competitors": ["...", "..."],
    "positioning_statement": "...",
    "confidence_score": 0.0-1.0
}
```

Be conservative with confidence_score - only high if information is clearly stated."""
```

### 4.3 Phase 2: Multi-Source Discovery (Detailed)

```python
async def discover_competitors(
    context: BusinessContext,
    config: DiscoveryConfig,
) -> List[RawCandidate]:
    """
    Phase 2: Cast a wide net across multiple sources.

    Goal: Find ALL potential competitors, filter later.
    """

    all_candidates: List[RawCandidate] = []

    # 2.1-2.3: Perplexity queries (intelligent discovery)
    if config.use_perplexity:
        perplexity = PerplexityDiscovery(client=perplexity_client)

        # Query 1: Direct competitors
        direct = await perplexity.query(
            f"Who are the main competitors to {context.company_name} "
            f"in the {context.offering_category} market?",
            context=context,
        )
        all_candidates.extend(direct)

        # Query 2: Alternatives
        alternatives = await perplexity.query(
            f"What are the best alternatives to {context.company_name} "
            f"for {context.value_proposition}?",
            context=context,
        )
        all_candidates.extend(alternatives)

        # Query 3: Market leaders
        leaders = await perplexity.query(
            f"Who are the leading companies in {context.offering_category} "
            f"for {context.customer_type} customers?",
            context=context,
        )
        all_candidates.extend(leaders)

        # Query 4: Emerging players
        emerging = await perplexity.query(
            f"What startups or new companies are disrupting "
            f"the {context.offering_category} market?",
            context=context,
        )
        all_candidates.extend(emerging)

    # 2.4: DataForSEO SEO competitors
    if config.use_dataforseo:
        seo_discovery = SEOCompetitorDiscovery(client=dataforseo_client)
        seo_competitors = await seo_discovery.get_competitors(
            domain=context.domain,
            market=config.market,
        )
        all_candidates.extend(seo_competitors)

    # 2.5: SERP analysis
    if config.use_serp:
        serp_discovery = SERPDiscovery(client=dataforseo_client)
        serp_competitors = await serp_discovery.discover(
            brand=context.company_name,
            category=context.offering_category,
            market=config.market,
        )
        all_candidates.extend(serp_competitors)

    # 2.6: G2/Crunchbase (optional)
    if config.use_business_intel:
        business_intel = BusinessIntelDiscovery()
        bi_competitors = await business_intel.discover(
            company=context.company_name,
            category=context.offering_category,
        )
        all_candidates.extend(bi_competitors)

    return all_candidates
```

### 4.4 Phase 3: Candidate Processing

```python
async def process_candidates(
    raw_candidates: List[RawCandidate],
    target_domain: str,
) -> List[ProcessedCandidate]:
    """
    Phase 3: Clean up and deduplicate candidates.
    """

    # 3.1: Deduplicate
    seen_domains = set()
    unique_candidates = []

    for candidate in raw_candidates:
        # Normalize domain
        domain = normalize_domain(candidate.domain or candidate.company_name)

        if domain and domain not in seen_domains and domain != target_domain:
            seen_domains.add(domain)
            candidate.domain = domain
            unique_candidates.append(candidate)

    # 3.2: Filter excluded domains
    filtered = []
    for candidate in unique_candidates:
        if not is_excluded_domain(candidate.domain):
            filtered.append(candidate)
        else:
            logger.debug(f"Filtered excluded domain: {candidate.domain}")

    # 3.3: Resolve company names to domains (if needed)
    resolver = DomainResolver()
    for candidate in filtered:
        if not candidate.domain and candidate.company_name:
            candidate.domain = await resolver.resolve(candidate.company_name)

    # 3.4: Initial relevance scoring
    for candidate in filtered:
        candidate.initial_relevance = calculate_initial_relevance(
            candidate=candidate,
            sources=candidate.discovery_sources,
        )

    # Sort by initial relevance
    filtered.sort(key=lambda c: c.initial_relevance, reverse=True)

    return filtered[:50]  # Keep top 50 for enrichment
```

### 4.5 Phase 4: Enrichment

```python
async def enrich_candidates(
    candidates: List[ProcessedCandidate],
    target_context: BusinessContext,
) -> List[EnrichedCandidate]:
    """
    Phase 4: Add intelligence to each candidate.
    """

    enriched = []

    for candidate in candidates:
        # 4.1: Fetch SEO metrics
        metrics = await dataforseo_client.get_domain_overview(candidate.domain)

        candidate.seo_metrics = SEOMetrics(
            domain_rating=metrics.get("domain_rank", 0),
            organic_traffic=metrics.get("organic_traffic", 0),
            organic_keywords=metrics.get("organic_keywords", 0),
            backlinks=metrics.get("backlinks", 0),
        )

        # 4.2: Scrape competitor homepage (optional, for deeper analysis)
        if candidate.initial_relevance > 0.7:  # Only for promising candidates
            homepage = await scraper.scrape_page(f"https://{candidate.domain}")
            candidate.homepage_content = homepage

        # 4.3: Calculate SERP overlap
        if target_context.seed_keywords:
            overlap = await calculate_serp_overlap(
                candidate_domain=candidate.domain,
                seed_keywords=target_context.seed_keywords[:10],
                market=target_context.market,
            )
            candidate.serp_overlap_score = overlap

        # 4.4: Estimate business similarity
        if candidate.homepage_content:
            similarity = await estimate_business_similarity(
                target_context=target_context,
                candidate_content=candidate.homepage_content,
            )
            candidate.business_similarity_score = similarity

        enriched.append(candidate)

    return enriched
```

### 4.6 Phase 5: Intelligent Classification

```python
async def classify_candidates(
    candidates: List[EnrichedCandidate],
    target_context: BusinessContext,
) -> List[ClassifiedCandidate]:
    """
    Phase 5: AI-powered purpose-based classification.
    """

    classifier = CompetitorClassifier(client=claude_client)

    classified = []

    for candidate in candidates:
        classification = await classifier.classify(
            candidate=candidate,
            target_context=target_context,
        )

        candidate.purpose_classification = classification.purpose
        candidate.threat_level = classification.threat_level
        candidate.confidence = classification.confidence
        candidate.classification_rationale = classification.rationale

        # Calculate composite score
        candidate.composite_score = calculate_composite_score(
            purpose=classification.purpose,
            seo_metrics=candidate.seo_metrics,
            serp_overlap=candidate.serp_overlap_score,
            business_similarity=candidate.business_similarity_score,
            source_count=len(candidate.discovery_sources),
        )

        classified.append(candidate)

    return classified
```

**Classification Prompt:**

```python
CLASSIFICATION_PROMPT = """Classify this potential competitor based on their PURPOSE for our analysis.

## Target Business:
- Company: {target_company}
- Offering: {target_offering}
- Category: {target_category}
- Target audience: {target_audience}
- Price tier: {target_price_tier}

## Candidate to Classify:
- Domain: {candidate_domain}
- Discovered via: {discovery_sources}
- SEO Metrics: DR={dr}, Traffic={traffic}, Keywords={keywords}
- SERP Overlap Score: {serp_overlap}
- Homepage content: {homepage_excerpt}

## Purpose Categories:

1. **BENCHMARK_PEER** (40% of ideal set)
   - Similar size, similar stage
   - Direct comparison makes sense
   - Their keywords are achievable for us
   - Example: A Series A startup analyzing another Series A startup

2. **KEYWORD_SOURCE** (35% of ideal set)
   - Ranks well for keywords we want
   - May or may not be direct business competitor
   - Valuable for keyword/content strategy
   - Example: Industry blog that ranks for our target terms

3. **CONTENT_MODEL** (15% of ideal set)
   - Excellent content strategy to learn from
   - May be larger or different business model
   - Valuable for content inspiration
   - Example: Well-known brand with great blog

4. **ASPIRATIONAL** (10% of ideal set)
   - Market leader we want to become
   - Too large for direct competition now
   - Valuable for long-term positioning
   - Example: Category-defining company

5. **NOT_RELEVANT**
   - Different industry entirely
   - No strategic value
   - Appeared due to keyword noise

## Output:
```json
{
    "purpose": "BENCHMARK_PEER|KEYWORD_SOURCE|CONTENT_MODEL|ASPIRATIONAL|NOT_RELEVANT",
    "threat_level": "CRITICAL|HIGH|MEDIUM|LOW|NONE",
    "confidence": 0.0-1.0,
    "rationale": "One sentence explaining classification",
    "key_insight": "What we can learn from this competitor"
}
```"""
```

### 4.7 Phase 6: Selection & Ranking

```python
async def select_top_candidates(
    classified: List[ClassifiedCandidate],
    target_count: int = 15,
) -> List[SelectedCandidate]:
    """
    Phase 6: Select top 15 with balanced purposes.
    """

    # Target distribution
    TARGET_DISTRIBUTION = {
        "BENCHMARK_PEER": 6,      # 40%
        "KEYWORD_SOURCE": 5,      # 33%
        "CONTENT_MODEL": 2,       # 13%
        "ASPIRATIONAL": 2,        # 13%
    }

    selected = []

    # Filter out NOT_RELEVANT
    relevant = [c for c in classified if c.purpose_classification != "NOT_RELEVANT"]

    # Sort by composite score within each purpose
    by_purpose = {}
    for candidate in relevant:
        purpose = candidate.purpose_classification
        if purpose not in by_purpose:
            by_purpose[purpose] = []
        by_purpose[purpose].append(candidate)

    for purpose in by_purpose:
        by_purpose[purpose].sort(key=lambda c: c.composite_score, reverse=True)

    # Select target count from each purpose
    for purpose, target_count in TARGET_DISTRIBUTION.items():
        candidates = by_purpose.get(purpose, [])
        selected.extend(candidates[:target_count])

    # If we don't have enough, fill from highest scoring remaining
    if len(selected) < 15:
        remaining = [c for c in relevant if c not in selected]
        remaining.sort(key=lambda c: c.composite_score, reverse=True)
        selected.extend(remaining[:15 - len(selected)])

    # Generate "why selected" for each
    for candidate in selected:
        candidate.selection_reason = generate_selection_reason(candidate)

    return selected[:15]
```

### 4.8 Phase 7: User Curation

```python
async def user_curation(
    selected: List[SelectedCandidate],
    user_decisions: UserCurationDecisions,
) -> List[FinalCompetitor]:
    """
    Phase 7: Human-in-the-loop curation.

    User MUST remove 5 competitors (cannot proceed without).
    """

    # Validate user removed exactly 5
    if len(user_decisions.removed) != 5:
        raise ValidationError(
            f"Must remove exactly 5 competitors. "
            f"You removed {len(user_decisions.removed)}."
        )

    # Remove user-rejected competitors
    remaining = [c for c in selected if c.domain not in user_decisions.removed]

    # Add user-suggested competitors (if any)
    if user_decisions.added:
        for added in user_decisions.added:
            # Quick validation of user-added competitor
            validated = await quick_validate_competitor(added)
            if validated:
                remaining.append(validated)

    # Ensure we have exactly 10
    if len(remaining) != 10:
        raise ValidationError(
            f"Final set must be exactly 10 competitors. "
            f"Current count: {len(remaining)}."
        )

    # Convert to final competitors
    final = []
    for candidate in remaining:
        final.append(FinalCompetitor(
            domain=candidate.domain,
            purpose=candidate.purpose_classification,
            threat_level=candidate.threat_level,
            seo_metrics=candidate.seo_metrics,
            selection_reason=candidate.selection_reason,
            user_approved=True,
        ))

    return final
```

### 4.9 Phase 8: Post-Validation

```python
async def post_validation(
    final_competitors: List[FinalCompetitor],
) -> ValidationResult:
    """
    Phase 8: Quality check before proceeding.
    """

    warnings = []

    # Check purpose distribution
    distribution = Counter(c.purpose for c in final_competitors)

    if distribution.get("BENCHMARK_PEER", 0) < 3:
        warnings.append(
            "LOW_BENCHMARK_PEERS: Less than 3 benchmark peers. "
            "Strategy may lack realistic comparisons."
        )

    if distribution.get("KEYWORD_SOURCE", 0) < 2:
        warnings.append(
            "LOW_KEYWORD_SOURCES: Less than 2 keyword sources. "
            "Keyword discovery may be limited."
        )

    # Check for metric diversity
    dr_values = [c.seo_metrics.domain_rating for c in final_competitors]
    if max(dr_values) - min(dr_values) < 20:
        warnings.append(
            "LOW_DR_DIVERSITY: All competitors have similar DR. "
            "Consider including more aspirational targets."
        )

    # Check geographic relevance
    # (Would need additional data to implement fully)

    return ValidationResult(
        is_valid=len(warnings) == 0,
        warnings=warnings,
        competitor_count=len(final_competitors),
        purpose_distribution=dict(distribution),
    )
```

---

## 5. Module Architecture

### 5.1 Directory Structure

```
src/
├── competitor_intelligence/          # NEW MODULE
│   ├── __init__.py
│   │
│   ├── # Core Pipeline
│   ├── pipeline.py                   # Main orchestration
│   ├── models.py                     # All data models
│   │
│   ├── # Phase 1: Context
│   ├── context/
│   │   ├── __init__.py
│   │   ├── scraper.py                # Website scraping (Firecrawl)
│   │   ├── analyzer.py               # AI context analysis
│   │   └── models.py                 # Context data models
│   │
│   ├── # Phase 2: Discovery
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── perplexity.py             # Perplexity API client
│   │   ├── seo_competitors.py        # DataForSEO competitor discovery
│   │   ├── serp_analysis.py          # SERP-based discovery
│   │   ├── business_intel.py         # G2/Crunchbase (optional)
│   │   └── aggregator.py             # Multi-source aggregation
│   │
│   ├── # Phase 3-4: Processing
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── deduplication.py          # Candidate deduplication
│   │   ├── enrichment.py             # Metrics enrichment
│   │   └── domain_resolver.py        # Company name → domain
│   │
│   ├── # Phase 5: Classification
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── classifier.py             # AI classification
│   │   ├── prompts.py                # Classification prompts
│   │   └── scoring.py                # Composite scoring
│   │
│   ├── # Phase 6-7: Selection
│   ├── selection/
│   │   ├── __init__.py
│   │   ├── selector.py               # Top-15 selection
│   │   ├── curation.py               # User curation handling
│   │   └── validation.py             # Post-selection validation
│   │
│   └── # Utilities
│   └── utils/
│       ├── __init__.py
│       ├── domain_utils.py           # Domain normalization
│       └── filters.py                # Platform/exclusion filters

├── context/                          # EXISTING - Keep for now
│   ├── competitor_discovery.py       # Will be deprecated
│   └── ...

└── ...
```

### 5.2 Key Interfaces

```python
# src/competitor_intelligence/pipeline.py

class CompetitorIntelligencePipeline:
    """
    Main orchestrator for competitor intelligence.

    This replaces/enhances the existing competitor_discovery.py
    for the greenfield and emerging domain flows.
    """

    def __init__(
        self,
        firecrawl_client: FirecrawlClient,
        perplexity_client: PerplexityClient,
        dataforseo_client: DataForSEOClient,
        claude_client: ClaudeClient,
        config: PipelineConfig,
    ):
        self.context_acquirer = ContextAcquirer(firecrawl_client, claude_client)
        self.discoverer = MultiSourceDiscoverer(
            perplexity_client, dataforseo_client, config
        )
        self.processor = CandidateProcessor()
        self.enricher = CandidateEnricher(dataforseo_client)
        self.classifier = CompetitorClassifier(claude_client)
        self.selector = CompetitorSelector()
        self.validator = SelectionValidator()

    async def run_full_pipeline(
        self,
        domain: str,
        market: str,
        user_hints: Optional[UserHints] = None,
    ) -> PipelineResult:
        """
        Run complete competitor intelligence pipeline.

        Returns candidates for user curation.
        """
        # Phase 1: Context
        context = await self.context_acquirer.acquire(domain, user_hints)

        # Phase 2: Discovery
        raw_candidates = await self.discoverer.discover(context)

        # Phase 3: Processing
        processed = await self.processor.process(raw_candidates, domain)

        # Phase 4: Enrichment
        enriched = await self.enricher.enrich(processed, context)

        # Phase 5: Classification
        classified = await self.classifier.classify(enriched, context)

        # Phase 6: Selection
        selected = await self.selector.select(classified, target_count=15)

        return PipelineResult(
            context=context,
            selected_candidates=selected,
            total_discovered=len(raw_candidates),
            total_processed=len(processed),
            ready_for_curation=True,
        )

    async def finalize_with_curation(
        self,
        pipeline_result: PipelineResult,
        user_curation: UserCurationDecisions,
    ) -> FinalCompetitorSet:
        """
        Apply user curation and validate final set.
        """
        # Phase 7: User Curation
        final = await apply_user_curation(
            pipeline_result.selected_candidates,
            user_curation,
        )

        # Phase 8: Validation
        validation = await self.validator.validate(final)

        return FinalCompetitorSet(
            competitors=final,
            validation_result=validation,
            context=pipeline_result.context,
        )
```

### 5.3 Data Models

```python
# src/competitor_intelligence/models.py

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime


class CompetitorPurpose(Enum):
    """Purpose-based classification for competitor analysis."""
    BENCHMARK_PEER = "benchmark_peer"
    KEYWORD_SOURCE = "keyword_source"
    CONTENT_MODEL = "content_model"
    ASPIRATIONAL = "aspirational"
    NOT_RELEVANT = "not_relevant"


class ThreatLevel(Enum):
    """Competitive threat assessment."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class DiscoverySource(Enum):
    """Source where competitor was discovered."""
    PERPLEXITY_DIRECT = "perplexity_direct"
    PERPLEXITY_ALTERNATIVES = "perplexity_alternatives"
    PERPLEXITY_MARKET = "perplexity_market"
    DATAFORSEO_COMPETITORS = "dataforseo_competitors"
    SERP_BRAND = "serp_brand"
    SERP_CATEGORY = "serp_category"
    G2_ALTERNATIVES = "g2_alternatives"
    CRUNCHBASE = "crunchbase"
    USER_PROVIDED = "user_provided"
    SELF_MENTIONED = "self_mentioned"  # Found on target's own website


@dataclass
class BusinessContext:
    """Deep context about the target business."""
    domain: str
    company_name: str

    # What they do
    primary_offering: str
    offering_category: str
    key_features: List[str]
    value_proposition: str

    # Who they serve
    customer_type: str  # B2B, B2C, Both
    company_sizes: List[str]  # SMB, Mid-market, Enterprise
    industries_served: List[str]

    # Business model
    business_model: str  # SaaS, Ecommerce, Services, etc.
    pricing_model: str  # Subscription, One-time, Freemium
    price_tier: str  # Budget, Mid-market, Enterprise

    # Market
    geographic_focus: List[str]
    primary_language: str
    target_market: str  # For analysis

    # Competitive hints
    self_mentioned_competitors: List[str]
    positioning_statement: Optional[str]

    # Quality indicators
    confidence_score: float
    context_quality: str  # HIGH, MEDIUM, LOW

    # Metadata
    acquired_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SEOMetrics:
    """SEO metrics for a competitor."""
    domain_rating: float
    organic_traffic: int
    organic_keywords: int
    backlinks: int
    referring_domains: Optional[int] = None


@dataclass
class RawCandidate:
    """Candidate as discovered from a source."""
    company_name: Optional[str]
    domain: Optional[str]
    discovery_source: DiscoverySource
    discovery_context: str  # Why/how discovered
    raw_data: Dict = field(default_factory=dict)


@dataclass
class EnrichedCandidate:
    """Candidate with full enrichment."""
    domain: str
    company_name: Optional[str]

    # Discovery
    discovery_sources: List[DiscoverySource]
    source_count: int

    # Metrics
    seo_metrics: Optional[SEOMetrics]
    serp_overlap_score: float = 0.0
    business_similarity_score: float = 0.0

    # Content
    homepage_content: Optional[str] = None
    homepage_excerpt: Optional[str] = None

    # Scoring
    initial_relevance: float = 0.0


@dataclass
class ClassifiedCandidate:
    """Candidate with AI classification."""
    domain: str
    company_name: Optional[str]

    # Discovery
    discovery_sources: List[DiscoverySource]

    # Metrics
    seo_metrics: Optional[SEOMetrics]
    serp_overlap_score: float
    business_similarity_score: float

    # Classification
    purpose_classification: CompetitorPurpose
    threat_level: ThreatLevel
    confidence: float
    classification_rationale: str
    key_insight: str

    # Final scoring
    composite_score: float


@dataclass
class SelectedCandidate:
    """Candidate selected for user curation."""
    domain: str
    company_name: Optional[str]

    # Classification
    purpose: CompetitorPurpose
    threat_level: ThreatLevel

    # Metrics
    seo_metrics: SEOMetrics

    # Selection
    composite_score: float
    selection_reason: str
    key_insight: str

    # For UI
    why_selected_short: str  # One-line summary
    why_selected_detailed: str  # Full explanation


@dataclass
class UserCurationDecisions:
    """User's curation decisions."""
    removed: List[str]  # Domains to remove (must be 5)
    removal_reasons: Dict[str, str]  # Optional reasons
    added: List[str]  # Optional domains to add
    notes: Optional[str] = None


@dataclass
class FinalCompetitor:
    """Final, user-approved competitor."""
    domain: str
    company_name: Optional[str]

    purpose: CompetitorPurpose
    threat_level: ThreatLevel
    seo_metrics: SEOMetrics

    selection_reason: str
    user_approved: bool

    # For downstream analysis
    analysis_priority: int  # 1-10, based on purpose weight


@dataclass
class FinalCompetitorSet:
    """The final set of competitors for analysis."""
    competitors: List[FinalCompetitor]
    validation_result: 'ValidationResult'
    context: BusinessContext

    # Metadata
    pipeline_version: str = "1.0"
    finalized_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Result of post-selection validation."""
    is_valid: bool
    warnings: List[str]
    competitor_count: int
    purpose_distribution: Dict[str, int]
```

---

## 6. Implementation Specifications

### 6.1 Firecrawl Integration

```python
# src/competitor_intelligence/context/scraper.py

import asyncio
from typing import List, Optional
import aiohttp

class FirecrawlClient:
    """
    Firecrawl API client for website scraping.

    Firecrawl handles:
    - JavaScript rendering
    - Anti-bot bypass
    - Clean markdown output

    API: https://firecrawl.dev
    Pricing: ~$0.001/page (very affordable)
    """

    BASE_URL = "https://api.firecrawl.dev/v0"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def scrape_url(
        self,
        url: str,
        formats: List[str] = ["markdown"],
        timeout: int = 30,
    ) -> dict:
        """
        Scrape a single URL.

        Args:
            url: URL to scrape
            formats: Output formats (markdown, html, text)
            timeout: Request timeout in seconds

        Returns:
            {
                "success": bool,
                "data": {
                    "markdown": "...",
                    "metadata": {...}
                }
            }
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "url": url,
            "formats": formats,
            "timeout": timeout * 1000,  # ms
        }

        async with self.session.post(
            f"{self.BASE_URL}/scrape",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout + 10),
        ) as response:
            return await response.json()

    async def scrape_multiple(
        self,
        urls: List[str],
        concurrency: int = 3,
    ) -> List[dict]:
        """
        Scrape multiple URLs with concurrency control.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_semaphore(url: str):
            async with semaphore:
                try:
                    return await self.scrape_url(url)
                except Exception as e:
                    return {"success": False, "error": str(e), "url": url}

        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)


class WebsiteScraper:
    """
    High-level scraper for business context acquisition.
    """

    BUSINESS_PAGES = [
        "/",
        "/about",
        "/about-us",
        "/pricing",
        "/product",
        "/features",
        "/solutions",
        "/customers",
        "/case-studies",
    ]

    def __init__(self, client: FirecrawlClient):
        self.client = client

    async def scrape_business_pages(
        self,
        domain: str,
        pages: Optional[List[str]] = None,
    ) -> dict:
        """
        Scrape key business pages from a domain.
        """
        pages = pages or self.BUSINESS_PAGES
        base_url = f"https://{domain}"

        urls_to_scrape = []
        for page in pages:
            url = f"{base_url}{page}" if page != "/" else base_url
            urls_to_scrape.append(url)

        results = await self.client.scrape_multiple(urls_to_scrape)

        # Organize by page type
        scraped_data = {
            "domain": domain,
            "pages": {},
            "success_count": 0,
            "total_pages": len(urls_to_scrape),
        }

        for url, result in zip(urls_to_scrape, results):
            page_path = url.replace(base_url, "") or "/"

            if result.get("success"):
                scraped_data["pages"][page_path] = {
                    "content": result.get("data", {}).get("markdown", ""),
                    "metadata": result.get("data", {}).get("metadata", {}),
                }
                scraped_data["success_count"] += 1
            else:
                scraped_data["pages"][page_path] = {
                    "error": result.get("error", "Unknown error"),
                }

        return scraped_data
```

### 6.2 Perplexity Integration

```python
# src/competitor_intelligence/discovery/perplexity.py

import aiohttp
from typing import List, Optional
import json


class PerplexityClient:
    """
    Perplexity API client for intelligent competitor discovery.

    Perplexity provides AI-powered web search that understands
    context and can answer complex questions about competitors.

    API: https://docs.perplexity.ai/
    Pricing: $5/1000 queries (sonar model)
    """

    BASE_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def query(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        model: str = "sonar",  # sonar or sonar-pro
    ) -> dict:
        """
        Query Perplexity with a question.

        Returns:
            {
                "answer": "...",
                "citations": [...],
                "raw_response": {...}
            }
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})

        payload = {
            "model": model,
            "messages": messages,
        }

        async with self.session.post(
            self.BASE_URL,
            headers=headers,
            json=payload,
        ) as response:
            data = await response.json()

            return {
                "answer": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "citations": data.get("citations", []),
                "raw_response": data,
            }


class PerplexityDiscovery:
    """
    Competitor discovery using Perplexity AI search.
    """

    def __init__(
        self,
        perplexity_client: PerplexityClient,
        claude_client,  # For extraction
    ):
        self.perplexity = perplexity_client
        self.claude = claude_client

    async def discover_competitors(
        self,
        context: 'BusinessContext',
    ) -> List['RawCandidate']:
        """
        Discover competitors using multiple Perplexity queries.
        """
        all_candidates = []

        # Query 1: Direct competitors
        q1 = await self._query_and_extract(
            question=f"Who are the main competitors to {context.company_name} "
                     f"in the {context.offering_category} market? "
                     f"List specific company names and their websites.",
            context=context,
            source=DiscoverySource.PERPLEXITY_DIRECT,
        )
        all_candidates.extend(q1)

        # Query 2: Alternatives
        q2 = await self._query_and_extract(
            question=f"What are the best alternatives to {context.company_name} "
                     f"for {context.primary_offering}? "
                     f"Include both direct competitors and similar tools.",
            context=context,
            source=DiscoverySource.PERPLEXITY_ALTERNATIVES,
        )
        all_candidates.extend(q2)

        # Query 3: Market leaders
        q3 = await self._query_and_extract(
            question=f"Who are the leading companies in the {context.offering_category} "
                     f"market for {context.customer_type} customers in 2024-2025?",
            context=context,
            source=DiscoverySource.PERPLEXITY_MARKET,
        )
        all_candidates.extend(q3)

        # Query 4: Emerging players
        q4 = await self._query_and_extract(
            question=f"What are the fastest growing startups or new companies "
                     f"in the {context.offering_category} space?",
            context=context,
            source=DiscoverySource.PERPLEXITY_MARKET,
        )
        all_candidates.extend(q4)

        return all_candidates

    async def _query_and_extract(
        self,
        question: str,
        context: 'BusinessContext',
        source: 'DiscoverySource',
    ) -> List['RawCandidate']:
        """
        Query Perplexity and extract company names from response.
        """
        # Add context to help Perplexity understand what we're looking for
        system_prompt = f"""You are helping identify competitors for a company.

Target company context:
- Name: {context.company_name}
- Offering: {context.primary_offering}
- Category: {context.offering_category}
- Target audience: {context.customer_type}
- Price tier: {context.price_tier}

When answering, focus on companies that would genuinely compete for the same customers.
Include specific company names and their website domains when possible."""

        # Query Perplexity
        result = await self.perplexity.query(
            question=question,
            system_prompt=system_prompt,
        )

        # Extract company names using Claude
        extraction_prompt = f"""Extract all company names and domains from this text.

TEXT:
{result['answer']}

Return a JSON array. For each company:
- company_name: The company name as mentioned
- domain: Their website domain (best guess if not explicitly mentioned)
- context: Brief note on why they were mentioned

Only include actual companies that could be competitors. Exclude:
- Generic terms or categories
- The target company itself ({context.company_name})
- Platform companies (Google, Amazon, Microsoft, etc.)

```json
[
    {{"company_name": "...", "domain": "...", "context": "..."}}
]
```"""

        extraction = await self.claude.analyze_with_retry(
            prompt=extraction_prompt,
            max_tokens=2000,
            temperature=0.1,
        )

        # Parse extraction result
        try:
            import re
            json_match = re.search(r'\[[\s\S]*\]', extraction.content)
            if json_match:
                companies = json.loads(json_match.group())

                return [
                    RawCandidate(
                        company_name=c.get("company_name"),
                        domain=c.get("domain"),
                        discovery_source=source,
                        discovery_context=c.get("context", ""),
                        raw_data={"perplexity_answer": result["answer"][:500]},
                    )
                    for c in companies
                ]
        except (json.JSONDecodeError, AttributeError):
            pass

        return []
```

### 6.3 Composite Scoring

```python
# src/competitor_intelligence/classification/scoring.py

from typing import Optional
from ..models import (
    CompetitorPurpose,
    SEOMetrics,
    DiscoverySource,
)


def calculate_composite_score(
    purpose: CompetitorPurpose,
    seo_metrics: Optional[SEOMetrics],
    serp_overlap: float,
    business_similarity: float,
    source_count: int,
    discovery_sources: list[DiscoverySource],
) -> float:
    """
    Calculate composite score for competitor ranking.

    Score range: 0-100
    """

    # Base score from purpose (purpose determines base value)
    PURPOSE_BASE_SCORES = {
        CompetitorPurpose.BENCHMARK_PEER: 40,
        CompetitorPurpose.KEYWORD_SOURCE: 35,
        CompetitorPurpose.CONTENT_MODEL: 25,
        CompetitorPurpose.ASPIRATIONAL: 20,
        CompetitorPurpose.NOT_RELEVANT: 0,
    }
    base_score = PURPOSE_BASE_SCORES.get(purpose, 0)

    # SEO metrics bonus (max +20)
    seo_bonus = 0
    if seo_metrics:
        # DR bonus (0-10)
        if seo_metrics.domain_rating >= 50:
            seo_bonus += 10
        elif seo_metrics.domain_rating >= 30:
            seo_bonus += 7
        elif seo_metrics.domain_rating >= 15:
            seo_bonus += 4

        # Traffic bonus (0-10)
        if seo_metrics.organic_traffic >= 100000:
            seo_bonus += 10
        elif seo_metrics.organic_traffic >= 10000:
            seo_bonus += 7
        elif seo_metrics.organic_traffic >= 1000:
            seo_bonus += 4

    # SERP overlap bonus (max +15)
    serp_bonus = serp_overlap * 15

    # Business similarity bonus (max +15)
    similarity_bonus = business_similarity * 15

    # Multi-source bonus (max +10)
    # Found in multiple sources = more reliable
    multi_source_bonus = min(source_count * 2, 10)

    # Premium source bonus (+5)
    premium_bonus = 0
    premium_sources = {
        DiscoverySource.PERPLEXITY_DIRECT,
        DiscoverySource.G2_ALTERNATIVES,
        DiscoverySource.SELF_MENTIONED,
    }
    if any(s in premium_sources for s in discovery_sources):
        premium_bonus = 5

    total = (
        base_score +
        seo_bonus +
        serp_bonus +
        similarity_bonus +
        multi_source_bonus +
        premium_bonus
    )

    return min(total, 100)


def generate_selection_reason(
    candidate: 'ClassifiedCandidate',
) -> str:
    """
    Generate human-readable selection reason.
    """
    purpose = candidate.purpose_classification
    metrics = candidate.seo_metrics

    # Purpose-specific templates
    templates = {
        CompetitorPurpose.BENCHMARK_PEER: (
            f"Selected as BENCHMARK PEER: Similar scale and market position. "
            f"DR {metrics.domain_rating if metrics else 'N/A'}, "
            f"{metrics.organic_keywords if metrics else 'N/A'} keywords. "
            f"{candidate.classification_rationale}"
        ),
        CompetitorPurpose.KEYWORD_SOURCE: (
            f"Selected as KEYWORD SOURCE: Strong keyword ranking potential. "
            f"Ranks for {metrics.organic_keywords if metrics else 'many'} keywords "
            f"with SERP overlap score of {candidate.serp_overlap_score:.0%}. "
            f"{candidate.classification_rationale}"
        ),
        CompetitorPurpose.CONTENT_MODEL: (
            f"Selected as CONTENT MODEL: Excellent content to learn from. "
            f"Strong content presence with {metrics.organic_traffic if metrics else 'high'} "
            f"organic traffic. {candidate.classification_rationale}"
        ),
        CompetitorPurpose.ASPIRATIONAL: (
            f"Selected as ASPIRATIONAL: Market leader to learn from. "
            f"DR {metrics.domain_rating if metrics else 'N/A'}, "
            f"industry-leading presence. {candidate.classification_rationale}"
        ),
    }

    return templates.get(purpose, candidate.classification_rationale)
```

---

## 7. Quality Assurance

### 7.1 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Context Completeness** | >80% | Fields filled in BusinessContext |
| **Discovery Coverage** | >3 sources | Avg sources per selected competitor |
| **Classification Confidence** | >0.7 avg | AI confidence scores |
| **Purpose Balance** | Within 20% of target | Distribution vs ideal |
| **User Curation Rate** | <30% changes | User additions after removal |

### 7.2 Quality Checks

```python
class QualityChecker:
    """
    Quality assurance for competitor intelligence pipeline.
    """

    async def check_context_quality(
        self,
        context: BusinessContext,
    ) -> QualityReport:
        """
        Check quality of acquired context.
        """
        issues = []

        # Required fields
        if not context.primary_offering:
            issues.append("MISSING: primary_offering")
        if not context.offering_category:
            issues.append("MISSING: offering_category")
        if not context.customer_type:
            issues.append("MISSING: customer_type")

        # Quality indicators
        if len(context.key_features) < 3:
            issues.append("LOW: Less than 3 key features identified")
        if context.confidence_score < 0.6:
            issues.append("LOW: Context confidence below 0.6")

        return QualityReport(
            component="context_acquisition",
            passed=len(issues) == 0,
            issues=issues,
            score=context.confidence_score,
        )

    async def check_discovery_quality(
        self,
        candidates: List[EnrichedCandidate],
        min_candidates: int = 20,
    ) -> QualityReport:
        """
        Check quality of discovered candidates.
        """
        issues = []

        if len(candidates) < min_candidates:
            issues.append(f"LOW: Only {len(candidates)} candidates (target: {min_candidates})")

        # Source diversity
        all_sources = set()
        for c in candidates:
            all_sources.update(c.discovery_sources)

        if len(all_sources) < 3:
            issues.append(f"LOW: Only {len(all_sources)} discovery sources used")

        # Multi-source candidates
        multi_source = [c for c in candidates if len(c.discovery_sources) > 1]
        multi_source_pct = len(multi_source) / len(candidates) if candidates else 0

        if multi_source_pct < 0.3:
            issues.append(f"LOW: Only {multi_source_pct:.0%} candidates from multiple sources")

        return QualityReport(
            component="discovery",
            passed=len(issues) == 0,
            issues=issues,
            score=min(len(candidates) / min_candidates, 1.0),
        )

    async def check_selection_quality(
        self,
        selected: List[SelectedCandidate],
    ) -> QualityReport:
        """
        Check quality of final selection.
        """
        issues = []

        # Purpose distribution
        distribution = {}
        for c in selected:
            p = c.purpose.value
            distribution[p] = distribution.get(p, 0) + 1

        # Check against targets
        TARGET = {
            "benchmark_peer": 6,
            "keyword_source": 5,
            "content_model": 2,
            "aspirational": 2,
        }

        for purpose, target in TARGET.items():
            actual = distribution.get(purpose, 0)
            if actual < target * 0.5:  # Less than 50% of target
                issues.append(f"LOW: Only {actual} {purpose} (target: {target})")

        # Confidence check
        avg_confidence = sum(c.confidence for c in selected) / len(selected)
        if avg_confidence < 0.7:
            issues.append(f"LOW: Average confidence {avg_confidence:.2f} (target: >0.7)")

        return QualityReport(
            component="selection",
            passed=len(issues) == 0,
            issues=issues,
            score=avg_confidence,
        )
```

---

## 8. Cost Analysis

### 8.1 Per-Analysis Cost Breakdown

| Component | API Calls | Cost per Call | Total |
|-----------|-----------|---------------|-------|
| **Firecrawl Scraping** | 5-8 pages | $0.001 | $0.01 |
| **Perplexity Queries** | 4 queries | $0.005 | $0.02 |
| **DataForSEO Competitors** | 1 call | $0.05 | $0.05 |
| **DataForSEO Enrichment** | 30 domains | $0.02 | $0.60 |
| **DataForSEO SERP** | 4 queries | $0.03 | $0.12 |
| **Claude Classification** | 2-3 calls | $0.05 | $0.15 |
| **TOTAL** | | | **~$0.95** |

### 8.2 Monthly Projections

| Volume | Total Cost | Cost per Analysis |
|--------|------------|-------------------|
| 100 analyses/mo | $95 | $0.95 |
| 500 analyses/mo | $475 | $0.95 |
| 1000 analyses/mo | $950 | $0.95 |

### 8.3 Cost Optimization Strategies

1. **Caching**: Cache Perplexity results for similar queries (24hr TTL)
2. **Batching**: Batch DataForSEO enrichment calls
3. **Tiered scraping**: Only deep-scrape promising candidates
4. **Progressive enrichment**: Start with cheap sources, add expensive only if needed

---

## 9. Migration Strategy

### 9.1 Coexistence with Existing Code

The new `competitor_intelligence` module will coexist with the existing `competitor_discovery.py`:

```
PHASE 1: Parallel Implementation
================================
- New module handles greenfield/emerging flows
- Existing code handles established domain flows
- No breaking changes

PHASE 2: Feature Parity
=======================
- Migrate established flow to new module
- Maintain backward compatibility
- Add feature flags

PHASE 3: Deprecation
====================
- Remove old competitor_discovery.py
- Full migration complete
```

### 9.2 Integration Points

```python
# src/collector/orchestrator.py

async def collect_for_analysis(self, domain: str, market: str) -> Dict:
    """
    Main collection orchestrator - now with competitor intelligence.
    """

    # Determine domain maturity
    maturity = await self._assess_domain_maturity(domain)

    if maturity in [DomainMaturity.GREENFIELD, DomainMaturity.EMERGING]:
        # NEW: Use competitor intelligence pipeline
        competitor_intel = CompetitorIntelligencePipeline(
            firecrawl_client=self.firecrawl,
            perplexity_client=self.perplexity,
            dataforseo_client=self.dataforseo,
            claude_client=self.claude,
        )

        # Run pipeline (returns candidates for user curation)
        pipeline_result = await competitor_intel.run_full_pipeline(
            domain=domain,
            market=market,
        )

        # Store for user curation step
        return {
            "status": "awaiting_competitor_curation",
            "pipeline_result": pipeline_result,
            "maturity": maturity.value,
        }

    else:
        # EXISTING: Use traditional flow for established domains
        return await self._collect_established_flow(domain, market)
```

### 9.3 Database Schema Additions

```sql
-- New tables for competitor intelligence

CREATE TABLE competitor_intelligence_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(255) NOT NULL,
    market VARCHAR(10) NOT NULL,

    -- Context
    business_context JSONB NOT NULL,
    context_quality VARCHAR(20),

    -- Pipeline state
    pipeline_status VARCHAR(50) NOT NULL,
    discovered_count INTEGER,
    selected_count INTEGER,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    curation_completed_at TIMESTAMP
);

CREATE TABLE competitor_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES competitor_intelligence_sessions(id),

    -- Candidate data
    domain VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),

    -- Discovery
    discovery_sources JSONB NOT NULL,
    discovery_context TEXT,

    -- Classification
    purpose VARCHAR(50),
    threat_level VARCHAR(20),
    confidence FLOAT,
    classification_rationale TEXT,

    -- Metrics
    seo_metrics JSONB,
    serp_overlap_score FLOAT,
    business_similarity_score FLOAT,
    composite_score FLOAT,

    -- Selection
    is_selected BOOLEAN DEFAULT FALSE,
    selection_reason TEXT,

    -- Curation
    user_removed BOOLEAN DEFAULT FALSE,
    user_removal_reason TEXT,
    user_added BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE final_competitor_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES competitor_intelligence_sessions(id),
    domain VARCHAR(255) NOT NULL,

    -- Final competitors (array of domains)
    competitors JSONB NOT NULL,

    -- Validation
    validation_passed BOOLEAN,
    validation_warnings JSONB,
    purpose_distribution JSONB,

    -- Lock
    is_locked BOOLEAN DEFAULT FALSE,
    locked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 10. Summary: The Path to World-Class Competitor Intelligence

### What Makes This Different

1. **Context-First**: We deeply understand the target business BEFORE searching for competitors
2. **Multi-Source**: No single source has the truth; we triangulate from multiple sources
3. **Intelligent Discovery**: Perplexity AI search understands context, not just keywords
4. **Purpose-Based Classification**: Competitors serve different strategic purposes
5. **Human-in-the-Loop**: User curation ensures alignment with business reality
6. **Quality Validated**: Multiple checkpoints ensure high-quality output

### Implementation Priority

```
WEEK 1-2: Foundation
- Firecrawl integration for context acquisition
- Perplexity integration for intelligent discovery
- Basic pipeline orchestration

WEEK 3-4: Intelligence
- AI-powered classification
- Composite scoring
- Selection algorithm

WEEK 5-6: User Experience
- User curation API endpoints
- Validation and warnings
- Integration with main analysis flow

WEEK 7-8: Quality & Polish
- Quality metrics and monitoring
- Cost optimization
- Documentation and testing
```

### The Bottom Line

With this architecture:
- Every greenfield/emerging domain gets **world-class competitor intelligence**
- The user is **involved at the right moment** (curation)
- The system **explains its reasoning** (transparency)
- Quality is **validated before proceeding** (no garbage in)
- Costs are **predictable and reasonable** (~$1/analysis)

This is the foundation that makes everything downstream valuable.

---

*Document Version: 1.0*
*Created: 2025-01-26*
*Author: Claude (Competitor Intelligence Architecture)*

# Authoricy Engine: Complete Data Flow Audit

## How to Read This Document

- `[OK]` = Working correctly
- `[BROKEN]` = Fails, loses data, or produces wrong results
- `[MISSING]` = Not implemented / not wired in
- `[PARTIAL]` = Partially working, significant gaps
- `[UNUSED]` = Code exists but is not active in production
- Numbers in parentheses = exact limits from code

---

## 1. SYSTEM OVERVIEW: Three Parallel Pipelines

```
                    USER REQUEST
                         |
                    Unified v2 API
                   (api/unified.py)
                         |
              Auto-detect domain maturity
              (DataForSEO: overview + backlinks)
                         |
            +------------+------------+
            |            |            |
       GREENFIELD     HYBRID      STANDARD
       (DR<20,KW<50)  (DR<35,KW<200) (Established)
            |            |            |
      Full pipeline   Partial     [MISSING]
      (G1-G5)        pipeline     Not implemented!
            |            |         (line 2042-2055)
            v            v
      Dashboard      Dashboard
      (greenfield)   (hybrid)
            |            |
            v            v
      Strategy       Strategy
      Builder        Builder
```

**FINDING: Standard mode (`ESTABLISHED` domains) is a TODO stub. It marks analysis as complete immediately without running any analysis.**

---

## 2. DATA COLLECTION PIPELINE

### 2.1 Standard Collection (orchestrator.py)

```
User submits domain
       |
       v
  CollectionConfig
  (domain, market, language, depth)
       |
       +---> get_depth() returns CollectionDepth preset
       |     (testing / basic / balanced / comprehensive / enterprise)
       |
       v
  +---------+     +---------+     +---------+     +---------+
  | PHASE 1 |     | PHASE 2 |     | PHASE 3 |     | PHASE 4 |
  |Foundation|     |Keywords |     |Competit.|     |AI/Tech  |
  +---------+     +---------+     +---------+     +---------+
       |               |               |               |
  [BROKEN]         [OK]           [BROKEN]         [BROKEN]
  Depth NOT        Depth IS        Depth NOT        Depth NOT
  wired in         wired in        wired in         wired in
       |               |               |               |
       v               v               v               v
  CollectionResult (in-memory, contains ALL raw data)
       |
       +---> compile_analysis_data() -----> Analysis Engine
       |     (passes in-memory data)
       |
       +---> extract_*_from_result() -----> Database tables
             (selective extraction)          (partial data)
```

### 2.2 Volume Stages: What Actually Works

The depth system has 5 presets. Here is what each controls:

```
                    Testing  Basic  Balanced  Comprehensive  Enterprise
                    ($0.40)  ($1.50) ($4.00)   ($12.00)      ($25.00)
                    -------  ------  --------  ------------  ----------
PHASE 1 (Foundation):
  Subdomains           20      20      20          20            20     [BROKEN] Hardcoded
  Top pages            50      50      50          50            50     [BROKEN] Hardcoded
  Competitors          20      20      20          20            20     [BROKEN] Hardcoded
  Technologies         20      20      20          20            20     [BROKEN] Hardcoded
  Page intersections   50      50      50          50            50     [BROKEN] Hardcoded

PHASE 2 (Keywords):
  Seed keywords         5      10      25          50           100     [OK] Wired
  Keyword universe    200     500   1,000       2,000         5,000     [OK] Wired
  Keyword gaps        100     200     500       1,000         2,000     [OK] Wired
  Expansion/seed       30      50      50          75           100     [OK] Wired
  Intent classif.      50     200     500       1,000         2,000     [OK] Wired
  Difficulty scoring   50     200     500       1,000         2,000     [OK] Wired
  SERP analysis        10      20      50         100           200     [OK] Wired
  Historical volume     5      10      25          50           100     [OK] Wired
  Questions             3       5      15          30            50     [OK] Wired

PHASE 3 (Competitive):
  Competitors           5       5       5           5             5     [BROKEN] Hardcoded
  Backlinks           500     500     500         500           500     [BROKEN] Hardcoded
  Anchors             100     100     100         100           100     [BROKEN] Hardcoded
  Referring domains   200     200     200         200           200     [BROKEN] Hardcoded
  Link gaps           100     100     100         100           100     [BROKEN] Hardcoded

PHASE 4 (AI/Technical):
  AI keywords          50      50      50          50            50     [BROKEN] Hardcoded
  LLM mention kws      20      20      20          20            20     [BROKEN] Hardcoded
  Pages audited         3       3       3           3             3     [BROKEN] Hardcoded
  Trend keywords        5       5       5           5             5     [BROKEN] Hardcoded
  Brand mentions       50      50      50          50            50     [BROKEN] Hardcoded
```

**Bottom line: "Testing" at $0.40 and "Enterprise" at $25.00 collect IDENTICAL data for Phases 1, 3, and 4. Only Phase 2 (keywords) actually scales with the depth preset.**

---

## 3. DATA STORAGE: Collection to Database

```
CollectionResult (in-memory, ALL fields from DataForSEO)
       |
       |  extract_keywords_from_result()
       |  extracts ONLY 9 fields out of 20+ per keyword:
       |    keyword, search_volume, cpc, competition,
       |    position, url, etv, intent, keyword_difficulty
       |
       |  LOST FIELDS:
       |    - SERP feature ownership (featured snippets, PAA)
       |    - Click metrics (CTR, clicks)
       |    - Historical rankings
       |    - Seasonal patterns
       |    - Related keywords / question variations
       |
       v
  +------------------+
  | keywords table   |  Deduplicated: ranked + universe + gaps
  | (~700-5000 rows) |  One position snapshot per analysis
  +------------------+
       |
       v
  +------------------+
  | competitors      |  Aggregated metrics only (traffic, KW count, DR)
  | (max 20 rows)    |  NOT individual keyword overlaps
  +------------------+
       |
       v
  +------------------+
  | backlinks        |  Individual rows stored
  | (max 500 rows)   |  Phase 3 hardcoded limit
  +------------------+
       |
       v
  +--------------------+
  | referring_domains   |  Aggregate: backlink_count, dofollow_count
  | keyword_gaps        |  Per-keyword gap with competitor positions
  | serp_features       |  Per-keyword SERP feature data
  | content_clusters    |  Topical clusters with authority scores
  | ai_visibility       |  AI mention detection
  | ranking_history     |  Position snapshots over time
  +--------------------+
```

**FINDING: The analysis engine uses the full in-memory CollectionResult. The dashboard uses the partial database. They see different data.**

---

## 4. ANALYSIS ENGINE: Two Versions

### 4.1 V4 Engine (PRODUCTION - 4 Loop Architecture)

```
compile_analysis_data(CollectionResult)
       |
       v
  analysis_data dict
  (phase1_foundation, phase2_keywords, phase3_competitive, phase4_ai_technical)
       |
       +---> Loop 1: Data Interpreter
       |     Input: analysis_data (full compiled data)
       |     Output: Markdown findings
       |     [BROKEN] Gets everything but Claude context window
       |              can't process 5000 keywords meaningfully
       |
       +---> Loop 2: Strategic Insights
       |     Input: analysis_data + Loop 1 output
       |     Output: Markdown strategy
       |
       +---> Loop 3: Enrichment (optional)
       |     Input: analysis_data + Loop 1-2 outputs
       |     Output: Enhanced analysis
       |
       +---> Loop 4: Quality Synthesis
       |     Input: All previous + analysis_data
       |     Output: Final markdown
       |
       v
  AnalysisResult
  (loop1-4 findings as markdown strings)
       |
       +---> Store 4 agent_output rows in DB
       |     (output_raw = markdown, quality_score)
       |
       +---> ReportGenerator.generate()  [This was the premium PDF]
             (but you said this is deprecated)
```

### 4.2 V5 Engine (EXISTS BUT NOT IN PRODUCTION)

```
                                                         [UNUSED]
compile_analysis_data(CollectionResult)          api/analyze.py line 1052 imports v4
       |                                         engine_v5.py exists but never called
       v
  +-----------------------+
  | 7 Specialized Agents  |   (run in parallel via asyncio.gather)
  +-----------------------+
       |
       +---> Keyword Intelligence Agent
       |     Receives: phase1 + phase2
       |     Truncation: ranked_keywords[:100], gaps[:50], suggestions[:50]
       |
       +---> Backlink Intelligence Agent
       |     Receives: phase1 + phase3
       |     Truncation: competitor_backlinks[:30], link_gaps[:50]
       |
       +---> Technical SEO Agent
       |     Receives: phase1 + phase4
       |     Truncation: technical_audits[:20], schema_data[:10]
       |
       +---> Content Analysis Agent
       |     Receives: phase1 + phase2
       |     Truncation: top_pages[:50], ranked_keywords[:100]
       |
       +---> Semantic Architecture Agent
       +---> AI Visibility Agent
       +---> SERP Analysis Agent
       |
       +---> (conditional) Local SEO Agent
       |
       v
  Quality Gate: 23/25 checks must pass (92%)
  Retry: Up to 2 attempts per agent
       |
       v
  Master Strategy Agent
  Receives: First 5 findings + 5 recommendations from EACH agent
  Synthesizes: Priority stack, 90-day roadmap, overall score
       |
       v
  AnalysisResultV5
```

**FINDING: V5 has much better data isolation (each agent gets only its relevant data) and quality gates, but it is NOT wired into production. Production still runs V4.**

---

## 5. FRONTEND DATA FLOW: Dashboard API

```
  Database tables
       |
       +---> Precomputation (after analysis completes)
       |     Computes dashboard components and caches them
       |
       v
  +---------------------------+
  | precomputed_dashboard     |
  | (PostgreSQL cache table)  |
  | TTL: 4 hours              |
  +---------------------------+
       |
       v
  Dashboard API Endpoints (api/dashboard.py)
  Each endpoint reads from cache OR computes from DB
       |
       +---> GET /overview
       |     Health scores, position distribution, metric comparisons
       |     Data: Full calculation from all keywords + previous analysis
       |     [OK] No truncation on overview metrics
       |
       +---> GET /sparklines
       |     Position trends for keywords
       |     [PARTIAL] Default: top 20 keywords by traffic only
       |     Full history returned (no sampling) but only for 20 kws
       |
       +---> GET /sov (Share of Voice)
       |     Market share vs competitors
       |     [PARTIAL] Hard limit: 10 TRUE_COMPETITOR type only
       |     [BROKEN] 30-day trend always returns null (not implemented)
       |
       +---> GET /battleground
       |     Attack/Defend keyword recommendations
       |     [PARTIAL] 25 per category (100 total max)
       |     Source: KeywordGap table (attack) + Keyword table (defend)
       |
       +---> GET /clusters
       |     Topical authority analysis
       |     [OK] Returns ALL clusters, no limit
       |
       +---> GET /content-audit
       |     KUCK recommendations (Keep/Update/Consolidate/Kill)
       |     [PARTIAL] 50 pages per category displayed, all counted
       |
       +---> GET /opportunities
       |     Ranked opportunity list
       |     [PARTIAL] 20 total (5 per category: quick wins, gaps, pages, snippets)
       |
       +---> GET /intelligence-summary
       |     AI-generated findings
       |     [PARTIAL] 5 findings per agent, max 10 per priority tier
       |     [BROKEN] Not cached, recomputes every request
       |
       +---> GET /bundle
             All components in one call
             [OK] Structure, but inherits all limits above

  ZERO pagination on any dashboard endpoint.
  All use hardcoded .limit() or Python slicing.
```

---

## 6. GREENFIELD PIPELINE (G1-G5)

```
Domain detected as GREENFIELD (DR<20, KW<50)
       |
       v
  G1: Competitor Discovery
       |
       +---> User-provided competitors
       +---> Perplexity AI discovery
       +---> SERP analysis of seed keywords (5 max)
       +---> Traffic share analysis
       |
       v
  Validation: Fetch DR/traffic for each candidate
  [PARTIAL] Hard cap: 15 competitors max
       |
       v
  G2: Keyword Universe Construction
       |
       +---> Seed keyword expansion (50 per seed)
       +---> Competitor rankings (200 per competitor, max 10 comps)
       |
       v
  Deduplication + filter volume >= 10
  [PARTIAL] Hard cap: 1,000 keywords max
  (Could discover 3,000+ but caps at 1,000)
       |
       v
  G3: SERP Analysis & Winnability
       |
       +---> Sort keywords by volume DESC
       +---> Analyze top 200 only (10 SERP results each)
       |
       v
  [BROKEN] 800 keywords get NO winnability score
  (winnability_score stays 0.0, serp_analyzed=False)
  Frontend cannot distinguish "not analyzed" from "zero winnability"
       |
       v
  G4: Market Sizing (TAM/SAM/SOM)
       |
       +---> TAM = all keywords volume
       +---> SAM = keywords where business_relevance >= 0.6
       +---> SOM = keywords where winnability >= 50
       |
       v
  [PARTIAL] SOM only includes the 200 analyzed keywords
  The 800 unanalyzed are excluded even if they'd qualify
       |
       v
  G5: Beachhead Selection & Roadmap
       |
       +---> Filter: winnability >= 55-60, KD <= 30, vol >= 50-100
       +---> Score: (Volume x Relevance x Winnability%) / (KD + 10)
       +---> Select top 20 beachheads
       |
       v
  Growth Roadmap:
    Phase 1 (months 1-3): Top 10 beachheads
    Phase 2 (months 4-6): Remaining beachheads + medium difficulty
    Phase 3 (months 7-12): Competitive keywords (winnability 30-50)
       |
       v
  Database Storage:
    - 1,000 keywords stored (source="greenfield_competitor_mining")
    - 20 beachhead keywords flagged
    - Market opportunity metrics
    - Traffic projections (3 scenarios)

  DATA LOSS FUNNEL:
  Discovered ~3,000+ keywords
    --> 1,000 cap                     (67% lost)
    --> 200 analyzed                  (80% of remaining unscored)
    --> 20 beachheads selected        (98% total loss)
```

---

## 7. HYBRID PIPELINE

```
Domain detected as EMERGING (DR<35, KW<200)
       |
       v
  Collect existing ranked keywords
  [PARTIAL] Limit: 500 keywords
       |
       v
  Discover competitors via SERP overlap
  [PARTIAL] Returns 15, false-competitor filtered
       |
       v
  Analyze keyword gaps (top 5 competitors)
  [PARTIAL] 100 gap keywords per competitor
       |
       v
  Select beachheads from two sources:
    1. Striking distance (pos 11-30): max 20
    2. Low-difficulty gaps (KD<40, vol>=100): max 15
       |
       v
  [PARTIAL] 500 keywords collected,
  but only 35 max selected as beachheads
```

---

## 8. STRATEGY BUILDER FLOW

```
  Analysis completes (any mode)
       |
       v
  User creates Strategy (POST /strategies)
  Links to analysis_run_id
       |
       v
  Browse available keywords
  (GET /strategies/{id}/available-keywords)
  Source: keywords table (database, NOT in-memory)
  [OK] Keyset pagination, filters, sorting
  [PARTIAL] Only sees 9 extracted fields, not full DataForSEO data
       |
       v
  View suggested clusters
  (GET /strategies/{id}/suggested-clusters)
  Source: keywords grouped by parent_topic field
  [OK] Top 50 clusters by volume, min 2 keywords per cluster
       |
       v
  Create Threads (content categories)
  Assign Keywords to Threads (bulk, max 1000 per request)
  Create Topics (content pieces) within Threads
       |
       v
  Validate for Export
  Hard errors: no threads, confirmed thread without keywords,
               confirmed thread without strategic_context
       |
       v
  Export (JSON for Monok AI / CSV / Text)
  [OK] Full strategy exported, no truncation
```

**FINDING: Strategy builder reads from DATABASE, which has partial data (9 fields per keyword). The user-facing keyword browser shows less information than what was originally collected from DataForSEO.**

---

## 9. COMPLETE FAILURE POINT MAP

### Stage 1: Collection

| # | Failure Point | Severity | Details |
|---|---------------|----------|---------|
| F1 | Depth not wired to Phase 1 | HIGH | Foundation data identical across all pricing tiers |
| F2 | Depth not wired to Phase 3 | HIGH | Competitive data identical across all tiers, $400+ API calls on "testing" |
| F3 | Depth not wired to Phase 4 | MEDIUM | AI/Technical always same small scale |
| F4 | Competitor hardcoded to 5 | MEDIUM | Phase 3 always analyzes exactly 5 competitors |

### Stage 2: Storage

| # | Failure Point | Severity | Details |
|---|---------------|----------|---------|
| F5 | 9/20+ fields extracted per keyword | HIGH | SERP features, click metrics, seasonality, related keywords all lost |
| F6 | Competitor data aggregated only | MEDIUM | Individual keyword overlaps not stored |
| F7 | Two data paths diverge | HIGH | Analysis engine sees full in-memory data; dashboard sees partial DB data |

### Stage 3: Analysis Engine

| # | Failure Point | Severity | Details |
|---|---------------|----------|---------|
| F8 | V5 engine not in production | HIGH | Better architecture exists but V4 (4-loop) still active |
| F9 | V4 passes entire dataset to Claude | HIGH | No per-agent data isolation; context window overflow risk |
| F10 | V5 agent truncation inconsistent | MEDIUM | Each agent decides its own limits (100, 50, 30, 20, 10) |

### Stage 4: Dashboard API

| # | Failure Point | Severity | Details |
|---|---------------|----------|---------|
| F11 | Zero pagination on dashboard | MEDIUM | All endpoints use hardcoded limits |
| F12 | Sparklines: 20 keywords default | LOW | Configurable via top_n param, but default is small |
| F13 | SoV: 10 competitors max | MEDIUM | Hardcoded, no pagination |
| F14 | SoV: 30-day trend always null | MEDIUM | Not implemented (line 866 comment) |
| F15 | Intelligence summary: not cached | LOW | Recomputes on every request |
| F16 | Opportunities: 5 per category | MEDIUM | Total 20, no way to see more |

### Stage 5: Greenfield Pipeline

| # | Failure Point | Severity | Details |
|---|---------------|----------|---------|
| F17 | 1,000 keyword hard cap | HIGH | Could discover 3,000+ but caps early |
| F18 | 800/1000 keywords never scored | CRITICAL | Only top 200 by volume get winnability analysis |
| F19 | Unscored keywords show as 0.0 | HIGH | Frontend can't distinguish "not analyzed" from "zero winnability" |
| F20 | SOM excludes unanalyzed keywords | HIGH | Market sizing is systematically underestimated |

### Stage 6: Unified v2 API

| # | Failure Point | Severity | Details |
|---|---------------|----------|---------|
| F21 | STANDARD mode not implemented | CRITICAL | Established domains get no analysis at all |
| F22 | Hybrid: 500 keyword limit | MEDIUM | Emerging domains may have more |
| F23 | Hybrid: 35 max beachheads | LOW | By design, but users may want more |

### Stage 7: Strategy Builder

| # | Failure Point | Severity | Details |
|---|---------------|----------|---------|
| F24 | Reads from DB not collection data | MEDIUM | 9 fields per keyword instead of 20+ |
| F25 | No SERP feature data in keywords | MEDIUM | Can't see featured snippet ownership |

---

## 10. END-TO-END FLOW: Where the Frontend Breaks

```
USER SUBMITS DOMAIN
         |
    [F21] If ESTABLISHED domain: NO ANALYSIS RUNS (standard mode = TODO stub)
         |
    [F1-F3] Collection runs, but depth only affects Phase 2 keywords
         |     Phase 1/3/4 always same regardless of plan tier
         |
         v
    CollectionResult (in-memory, FULL data)
         |
         +------[F7]------+
         |                 |
    compile_analysis_data  extract_*_from_result
    (full data)            (partial: 9 fields/keyword) [F5]
         |                 |
    Analysis Engine        Database
    (V4 - 4 loops) [F8]   |
         |                 +---> keywords table
    [F9] Entire dataset    +---> competitors (aggregated) [F6]
    sent to Claude         +---> backlinks (max 500)
    in single prompt       +---> intelligence tables
         |                 |
         v                 v
    Agent Outputs     Precomputed Dashboard Cache
    (stored in DB)         |
                           v
                    Dashboard API Endpoints
                           |
                    [F11] No pagination
                    [F12] 20 keywords for sparklines
                    [F13] 10 competitors for SoV
                    [F14] SoV trend = null
                    [F16] 20 opportunities max
                           |
                           v
                    FRONTEND DISPLAY
                           |
                    Strategy Builder
                    [F24] Sees 9 fields per keyword
                    [F25] No SERP feature data
                           |
                           v
                    Export to Monok AI
                    (full strategy, no truncation here)
```

### For Greenfield Specifically:

```
NEW DOMAIN SUBMITTED
         |
    Maturity detection: DR<20, KW<50
         |
    G1: Competitor Discovery
    15 competitors max
         |
    G2: Keyword Universe
    [F17] Hard cap at 1,000 keywords
         |
    G3: Winnability Analysis
    [F18] Only top 200 analyzed
    [F19] Remaining 800 show winnability = 0.0
         |
    G4: Market Sizing
    [F20] SOM excludes 800 unscored keywords
    Market opportunity UNDERESTIMATED
         |
    G5: Beachhead Selection
    20 beachheads from 200 analyzed keywords
    (ignoring 800 potentially good keywords)
         |
    Dashboard shows:
    - 1,000 keywords (but 800 have no real scores)
    - Market sizing (but SOM is wrong)
    - 20 beachheads (from a pool of only 200, not 1,000)
    - 3-phase roadmap
```

---

## 11. ANSWER TO YOUR QUESTIONS

### "Is it the same problem in the frontend?"

**Yes, but different.** The frontend has its OWN set of problems on top of the analysis problems:

1. **Analysis path**: Gets full in-memory data, but V4 engine dumps it all into Claude prompts without intelligent scoping
2. **Frontend path**: Gets partial database data (9/20+ fields per keyword), further truncated by dashboard endpoint limits (20 keywords, 10 competitors, 25 per battleground category)
3. **Both paths** share the collection problem: depth only controls Phase 2

### "I thought we implemented volume stages"

**You did -- but only 40% of it.** The `CollectionDepth` system in `src/collector/depth.py` is well-designed with 5 presets and clear escalation. But it's only wired into Phase 2 (keywords). Phases 1, 3, and 4 completely ignore the depth parameter because `collect_foundation_data()`, `collect_competitive_data()`, and `collect_ai_technical_data()` don't accept a depth argument.

### The standard mode problem

**Critical**: The `STANDARD` analysis mode for established domains (your most valuable potential customers) is a TODO stub. When a domain is classified as ESTABLISHED, `run_standard_analysis_background()` at unified.py line 2042-2055 just marks the analysis as complete immediately without doing anything.

---

## 12. PRIORITY FIXES

### Tier 1: Blocking Issues
1. **F21**: Implement STANDARD mode in unified v2 API (established domains get zero analysis)
2. **F18/F19**: Score ALL 1,000 greenfield keywords, not just top 200 (or at minimum, mark unscored keywords explicitly)
3. **F8**: Switch production to V5 engine (it exists, has quality gates, just needs to be imported)

### Tier 2: Data Integrity
4. **F1-F3**: Wire depth parameter into Phases 1, 3, 4
5. **F5**: Extract more keyword fields to database (SERP features, clicks, CTR, seasonality)
6. **F7**: Ensure dashboard and analysis see the same data

### Tier 3: Frontend Experience
7. **F11**: Add pagination to dashboard endpoints
8. **F14**: Implement SoV 30-day trend
9. **F20**: Fix SOM calculation to account for unscored keywords
10. **F24**: Surface more keyword data in strategy builder

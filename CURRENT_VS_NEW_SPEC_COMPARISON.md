# Current Authoricy Engine vs. New Build Spec (v2.3): Full Gap Analysis

## Overview

This document compares the **current Authoricy Engine** (45,000 LoC Python/FastAPI SaaS platform with 70+ API endpoints) against the **v2.3 Build Spec** (`authoricy-seo-spec-v2.3.md`).

The current system is a multi-tenant SaaS platform with authentication, interactive dashboards, a strategy builder, greenfield intelligence, and client-facing APIs. The v2.3 spec is a CLI/script-based consultant workflow with a specific focus on **Feed Exports** (structured content production data) and **content decay monitoring** — neither of which exist in the current system.

**Key shift from v1.0 to v2.3:** The spec dropped DataForSEO, Screaming Frog, Moz, and Gephi from the tool stack. Cross-validation simplified from 3 sources to 2 (Semrush + Ahrefs). Two major new deliverables added: Feed Exports and Link Target Exports. Content decay monitoring added as an ongoing operational capability. Dashboard expanded from 7 to 9 pages (Feed Performance + Content Health). And the philosophical stance changed — v2.3 says "Claude Code owns all architecture decisions," defining capabilities rather than prescribing implementation.

---

## Part 1: Current System — Complete Feature Inventory

### 1.1 Multi-Mode Analysis (3 paths)

| Mode | Trigger | What It Does | Status |
|------|---------|-------------|--------|
| **Greenfield** | DR<20, KW<50 | 5-stage pipeline: competitor discovery → keyword universe (1K cap) → SERP winnability (top 200) → market sizing (TAM/SAM/SOM) → beachhead selection (20 keywords) | Working (with documented data loss issues) |
| **Hybrid/Emerging** | DR<35, KW<200 | Collects 500 ranked keywords, discovers competitors via SERP overlap, analyzes keyword gaps (100 per competitor), selects 35 beachheads from striking distance + low-KD gaps | Working (partial) |
| **Standard/Established** | DR>35, KW>200 | Auto-detection triggers but analysis is a TODO stub — marks complete immediately without running anything | **NOT IMPLEMENTED** |

### 1.2 Interactive Dashboard — Standard Domains (9 endpoints)

| Endpoint | What It Shows | Limits |
|----------|-------------|--------|
| `GET /overview` | Health scores, position distribution, metric comparisons | No truncation |
| `GET /sov` | Share of Voice — market share vs competitors | 10 competitors max |
| `GET /sparklines` | Position trends for keywords | Top 20 keywords only |
| `GET /battleground` | Attack/Defend keyword recommendations | 25 per category (100 total) |
| `GET /clusters` | Topical authority analysis | Returns ALL clusters |
| `GET /content-audit` | KUCK recommendations (Keep/Update/Consolidate/Kill) | 50 pages per category |
| `GET /intelligence-summary` | AI-generated findings from agent outputs | 5 per agent, 10 per priority tier |
| `GET /opportunities` | Quick wins, gaps, pages, snippet opportunities | 5 per category (20 total) |
| `GET /bundle` | All above in single API call | Inherits all limits |

### 1.3 Interactive Dashboard — Greenfield Domains (5 endpoints)

| Endpoint | What It Shows |
|----------|-------------|
| `GET /greenfield/bundle` | All greenfield data in one call |
| `GET /greenfield/beachheads` | High-winnability entry keywords with scores |
| `GET /greenfield/market-map` | TAM/SAM/SOM market opportunity sizing |
| `GET /greenfield/roadmap` | 3-phase growth plan (Foundation → Traction → Authority) |
| `GET /greenfield/projections` | Traffic projections: conservative/expected/aggressive over 24 months |

### 1.4 Strategy Builder (30+ endpoints)

Full CRUD for a 3-tier content strategy hierarchy:

| Feature | Endpoints | What It Does |
|---------|-----------|-------------|
| **Strategy CRUD** | Create, get, update, list, duplicate, archive, restore, delete | Named strategies linked to analysis runs |
| **Thread Management** | Create, update, move, delete, list | Topic clusters (threads) within strategies |
| **Topic Planning** | Create, update, move between threads, delete, list | Individual content pieces within threads |
| **Keyword Assignment** | Add/remove to threads, batch move between threads, assign from cluster | Link keywords to content structure |
| **AI Suggestions** | Suggested clusters, format recommendations | Platform suggests keyword groupings |
| **Available Keywords** | Keyset-paginated browser with filters | Browse unassigned keywords |
| **Export** | Validate, export (JSON/CSV/Text), download, history | Ship strategy to Monok AI or CSV |
| **Activity Log** | Full change history | Track who changed what |

**Export format:** The Monok JSON export flattens strategy → threads → topics → keywords into a structured JSON. It includes thread metadata, custom_instructions (strategic_context, differentiation_points, competitors_to_address, content_angle, format_recommendations, target_audience), topics, keyword assignments, and summary stats.

### 1.5 Context Intelligence System (8 files, ~200K LoC)

| Component | What It Does |
|-----------|-------------|
| **Business Profiler** | Auto-detects business model (B2B SaaS, B2B Service, B2C Ecommerce, etc.), products, target market, audience from website |
| **Market Detection** | 9 signal sources (schema.org address, hreflang, TLD, phone codes, VAT, currency, store selector, shipping pages, language) |
| **Market Resolver** | Maps detected market to DataForSEO location codes |
| **Market Validator** | Validates market fit, detects conflicts between declared and detected markets |
| **Competitor Discovery** | SERP overlap + Perplexity AI semantic search + traffic share analysis |
| **Competitor Classification** | Classifies as DIRECT, SEO, CONTENT, EMERGING, ASPIRATIONAL, NOT_COMPETITOR with threat levels |
| **Website Analyzer** | Analyzes site structure, navigation, content patterns |
| **Sitemap Parser** | Parses XML sitemaps to understand site scope |

### 1.6 Scoring Algorithms (6 modules)

| Algorithm | File | What It Calculates |
|-----------|------|-------------------|
| **Winnability** | `src/scoring/greenfield.py` | 0-100 score: likelihood a new domain can rank. Components: (100 - personalized_difficulty) × 0.6 + volume_score × 0.2 + competitor_saturation × 0.1 + topical_distance × 0.1 |
| **Opportunity** | `src/scoring/opportunity.py` | Composite: volume (20%) + difficulty (20%) + intent (20%) + position gap (20%) + topical alignment (20%), with freshness modifier |
| **Difficulty** | `src/scoring/difficulty.py` | Adjusts base KD for SERP authority, SERP complexity, content freshness, and domain-specific factors |
| **Competitor Scoring** | `src/scoring/competitor_scoring.py` | Threat level: (DR/100 × 0.3) + (overlap/100 × 0.4) + (traffic_share × 0.3) × 100 |
| **Decay** | `src/scoring/decay.py` | 0-1 score with 4 components: traffic decay (40%), position decay (30%), CTR decay (20%), age factor (10%). Severity: CRITICAL >0.5, MAJOR 0.3-0.5, LIGHT 0.1-0.3. Maps to KUCK actions (Keep/Update/Consolidate/Kill). |
| **Domain Maturity** | `src/scoring/greenfield.py` | Classifies domains: greenfield / emerging / established based on DR + keyword thresholds |

### 1.7 Authentication & Multi-Tenancy

| Feature | Implementation |
|---------|---------------|
| JWT validation | Supabase JWT tokens |
| User management | Get/update profile, list users, roles, enable/disable |
| Domain ownership | Users own domains, access checks on all endpoints |
| Admin access | Admins can access any domain/strategy |

### 1.8 Data Collection (DataForSEO Only — 60 endpoints)

4-phase parallel collection, ALL from DataForSEO:

| Phase | Endpoints | Data |
|-------|-----------|------|
| Phase 1: Foundation | 8 | Domain metrics, traffic, technologies, subdomains, top pages |
| Phase 2: Keywords | 16 | Ranked keywords, universe, gaps, suggestions, intent, difficulty, SERP, historical, questions |
| Phase 3: Competitive | 19 | Competitor metrics, backlinks, anchors, referring domains, link gaps |
| Phase 4: AI/Technical | 17 | AI visibility, LLM mentions, on-page audit, trends, brand mentions, CWV |

### 1.9 Database (20+ tables)

Key models:
- **Keyword** (lines 287-374): `keyword`, `search_volume`, `keyword_difficulty`, `current_position`, `parent_topic`, `cluster_name`, `is_cluster_seed`, `opportunity_score`, `winnability_score`, `intent`
- **ContentCluster** (lines 948-999): `cluster_name`, `pillar_keyword`, `total_keywords`, `ranking_keywords`, `keywords` (JSONB), `missing_subtopics`, `topical_authority_score`
- **Backlink** (lines 438-485): `source_domain`, `anchor_text`, `anchor_type`, `source_domain_rating`, `link_quality_score`, `spam_score`, `relevance_score`, `first_seen`, `last_seen`, `is_lost`
- **ReferringDomain** (lines 845-901): `domain_rating`, `organic_traffic`, `backlink_count`, `anchor_distribution` (JSONB), `quality_score`, `domain_type`
- **Page** (lines 490-530): `decay_score`, `kuck_recommendation`
- **RankingHistory** (lines 907-942): Position tracking over time
- **Strategy/Thread/Topic/ThreadKeyword**: Full strategy builder hierarchy with optimistic locking

### 1.10 Report Generation & Email

| Feature | Status |
|---------|--------|
| External Report (10-15 pg executive) | Implemented |
| Internal Report (40-60 pg tactical) | Implemented |
| SVG chart generation | Implemented |
| Confidence scoring per section | Implemented |
| WeasyPrint HTML → PDF | Implemented |
| Email delivery via Resend | Implemented |

### 1.11 Caching

- PostgreSQL-backed cache with 4-hour TTL
- ETag + stale-while-revalidate HTTP headers
- Per-domain, per-analysis, or full cache invalidation
- Proactive cache warming

---

## Part 2: v2.3 Spec — Complete Feature Inventory

### 2.1 Tool Stack (Simplified from v1.0)

| Tool | Role | Change from v1.0 |
|------|------|------------------|
| **Ahrefs** | Backlinks, DR, parent_topic clustering, Brand Radar, Site Audit, SERP overview, related-terms ("also talk about") | **Expanded role** — now primary for technical audit, entity extraction, SERP overlap |
| **Semrush** | Keyword volumes (primary), PKD, Topical Authority, Traffic Analytics, search intent | Same role |
| **GSC** | Ground truth: clicks, impressions, queries, indexation | Same role |
| **PageSpeed Insights** | Core Web Vitals, Lighthouse | Same role |
| **claude-seo skill** | 12 slash commands: audit, schema, GEO, E-E-A-T, sitemap, etc. | Same role |
| ~~DataForSEO~~ | ~~SERP scraping, bulk keywords, on-page, intent~~ | **DROPPED entirely** |
| ~~Screaming Frog~~ | ~~Deep technical crawls, JS rendering~~ | **DROPPED entirely** |
| ~~Moz~~ | ~~DA, spam score~~ | **DROPPED entirely** |
| ~~Gephi~~ | ~~Site architecture visualization~~ | **DROPPED entirely** |

### 2.2 Cross-Validation (Simplified)

| Data Type | v1.0 Method | v2.3 Method |
|-----------|-------------|-------------|
| Keyword volumes | Semrush (0.45) + DataForSEO (0.30) + Ahrefs (0.25) weighted average | Semrush primary + Ahrefs validation. <30% variance = high confidence. 30-50% = moderate. >50% = low. |
| Backlinks | Ahrefs primary + Semrush comparison + Moz spam score | Ahrefs primary + Semrush comparison only. No averaging. |
| Traffic (competitors) | Range [MIN, MAX] across all tools | Same — range [MIN, MAX] |
| Authority | Ahrefs DR + Moz DA + Semrush AS (3 sources) | Ahrefs DR + Semrush AS (2 sources only) |
| Link quality | Ahrefs DR × 0.40 + Moz DA × 0.25 + (1 - Moz spam) × 0.20 + relevance × 0.15 | Ahrefs DR + Semrush AS + spam pattern heuristics |

### 2.3 Four-Session Workflow

| Session | Duration | Key Output |
|---------|----------|------------|
| **GATHER** | ~30 min | Raw data from all sources + claude-seo outputs → phase1-briefing.md (<2500 words) |
| **ANALYSE** | ~30 min | Clustering, topic extraction, entity extraction, gap analysis → phase2-briefing.md (<3000 words) |
| **STRATEGISE** | ~45 min | Feed Exports + Q1 Activation Plan + Link Targets + Roadmap → phase3-briefing.md (<3000 words) + HUMAN REVIEW |
| **DELIVER** | ~60 min | report.docx + Feed Exports (JSON) + Link Target Export + CSVs + dashboard data |

### 2.4 Feed Export System (NEW in v2.3 — Not in v1.0)

The **primary production-facing deliverable**. Two outputs:

**A. Full Cluster Map** — Every viable cluster gets a structured Feed definition:
```
Feed: [Cluster Name]
├── Description
├── Priority Score: [KOB × business fit × competitive feasibility]
├── Topics: [distinct topical angles]
│   ├── Topic name + description
│   ├── Source: keyword_cluster | content_gap | entity_expansion
│   └── Estimated search demand: high | medium | low
├── Keywords: [shared validated pool]
│   ├── Term, volume, KD, intent, role (primary | supporting)
│   └── Cross-validation confidence
├── Entities: [depth signals from "also talk about"]
├── Competitive Context:
│   ├── Dominant competitor + DR
│   ├── Competitor article count
│   └── Difficulty: open | contested | dominated
└── Existing Client Content
```

**B. Q1 Activation Plan** — Top clusters selected for immediate work:
- Article velocity per Feed
- Initial Topics to prioritize
- Feed activation sequence

This is the structured data that tells the content production system what to write about. It persists between quarterly re-audits and grows over time.

### 2.5 Link Target Export (NEW in v2.3 — Not in v1.0)

Structured export from backlink gap analysis:
- Target domain, DR, competitor overlap count, specific linking URLs
- Recommended anchor text (target: ~60% branded, ~40% diverse)
- Acquisition method (guest post, resource page, broken link, digital PR, expert commentary)
- Contact page URL per target domain
- Priority tier: Tier 1 (DR 50+, 3+ competitors), Tier 2 (DR 30-50, 2+), Tier 3 (DR 20-30, niche)

Typical output: 50-200 targets per client, 20-30 Tier 1.

### 2.6 Content Decay Monitoring (NEW in v2.3, Section 15 — Not in v1.0)

Starts month 4+ (after content indexed and GSC has 3 months of data).

**Detection thresholds:**
- Average position drops 3+ spots from 3-month trailing average
- Monthly clicks drop 20%+ from 3-month trailing average
- Monthly impressions drop 30%+ from 3-month trailing average

**Output:** Prioritized refresh queue with:
- URL, Feed (cluster), decay signal type, magnitude
- Suggested action: Refresh (moderate decay), Expand (outranked by deeper content), Consolidate (cannibalization)

Refresh tasks become Topics in their Feeds — the content production system treats them like any other Topic.

### 2.7 Session 2 ANALYSE — Enhanced Topic Model (Changed from v1.0)

v2.3 adds significant depth to Session 2 beyond what v1.0 specified:

1. **Topic extraction within clusters:** SERP overlap validation to collapse keyword variants into distinct Topics. Keywords whose top-ranking pages overlap = same Topic.
2. **Entity extraction:** "Also talk about" data from Ahrefs becomes the entity layer — concepts signaling topical depth, not standalone keywords.
3. **Keyword role tagging:** Every keyword tagged as "primary" (high volume, cluster-defining) or "supporting" (long-tail, supplementary).
4. **Competitive context per cluster:** Dominant competitor, article count, internal linking strength, difficulty assessment (open/contested/dominated).

### 2.8 Report (.docx, 12 sections)

Largely same as v1.0 but with key changes:
- **Section V renamed:** "Topical Map & Feed Architecture" (was just "Topical Map") — now describes Feed → Topic relationships with activation status
- **Section VI renamed:** "Content Strategy & Feed Activation Plan" — now covers Q1 Feed activation with velocity allocation, Topic priorities, and expansion criteria
- **Section XI updated:** Implementation Roadmap now organized around Feed activation per quarter, not just generic content phases
- **Section XII updated:** Appendices now reference Feed Exports and Link Target Exports

### 2.9 Looker Studio Dashboard (9 pages — was 7 in v1.0)

| Page | New? | What It Shows |
|------|------|---------------|
| Executive Overview | No | Scorecard row, traffic trend, MoM changes, top 5 pages |
| Keyword Performance | No | Rankings distribution, top keywords, gained/lost |
| Content Performance | No | Top pages by traffic, engagement, content plan coverage |
| **Feed Performance** | **YES** | Per-Feed view: topics published vs total (cluster completion %), impressions/clicks from Feed keywords, avg position trend, Feed-level traffic growth |
| **Content Health** | **YES** | Decay detection: articles flagged for refresh, health status (growing/stable/declining), refresh queue with priority |
| Backlink Health | No | Referring domains trend, new vs lost, DR distribution |
| Technical Health | No | CWV gauges, indexation, crawl errors |
| AI Visibility | No | SOV comparison, mentions trend by platform, top cited pages |
| Competitive Snapshot | No | Competitor comparison table, radar chart |

### 2.10 Google Sheets (9 tabs — was 7 in v1.0)

New tabs:
- **`feeds`** — per Feed: name, status (active/planned/backlog), topic count, topics published, keyword pool size, impressions, clicks, avg position
- **`content-health`** — published URL watchlist with position, traffic, 3-month trailing average, decay flag

### 2.11 Quarterly Re-Audit (Enhanced from v1.0)

v2.3 adds two additional inputs:
1. GSC performance data per Feed for the last quarter
2. Current Feed activation status (what's active, what's been published)

Updates:
- Keyword pools per Feed (new terms, volume changes)
- Cluster priority scores (based on actual performance, not estimates)
- Topic lists (new content gaps from competitor movements)
- Link target export (new competitor links = new gap opportunities)
- Next quarter's Feed Activation Plan

Each audit lives in its own timestamped folder. Previous Feed Exports persist — they are updated, not replaced.

---

## Part 3: Gap Analysis — What v2.3 Does NOT Cover

These are features in the current system that v2.3 completely omits.

### 3.1 CRITICAL GAPS — Must Be Addressed

| # | Current Feature | Why It Matters | Recommendation |
|---|----------------|----------------|----------------|
| **G1** | **SaaS Platform / Web UI** (70+ REST endpoints powering interactive dashboards) | v2.3 is a CLI/script workflow operated by Alex. No client self-service. | **Intentional for consultant model.** The Looker Studio dashboard IS the client-facing UI. If team/client self-service needed later, add a web layer on top. |
| **G2** | **Authentication & Multi-Tenancy** (JWT, user roles, domain ownership) | v2.3 has no auth — it's a local tool. | Not needed for consultant-operated. Client isolation happens via folder structure (`clients/{slug}/`). |
| **G3** | **Domain Maturity Auto-Detection & Routing** (Greenfield/Emerging/Established) | v2.3 assumes Alex manually knows the client's maturity level. All clients get the same workflow. | **Port as a pre-Session-1 check:** Run Ahrefs batch-analysis, check DR + keyword count, route to workflow variant. Greenfield clients need competitor-first discovery before Session 1 can collect keyword data. |
| **G4** | **Strategy Builder** (30+ interactive endpoints: threads, topics, keywords, drag-drop, bulk ops, Monok export) | v2.3 replaces this with **Feed Exports** — structured JSON per cluster generated programmatically in Session 3. No interactive editing. | **Feed Exports cover 80% of the use case.** The missing 20% is interactive refinement. Options: (a) export Feed data to Google Sheets for manual adjustment, (b) build interactive builder later, (c) accept that Alex curates in Session 3 before approving. |

### 3.2 HIGH-VALUE GAPS — Should Be Preserved

| # | Current Feature | Why It Matters | Recommendation |
|---|----------------|----------------|----------------|
| **G5** | **Greenfield Pipeline** (G1-G5: competitor discovery → keyword universe → SERP winnability → TAM/SAM/SOM → beachhead selection) | Unique methodology for new domains with no existing SEO data. v2.3 doesn't distinguish greenfield from established. | **Port as Session 1 variant.** For greenfield clients: competitor-first discovery replaces direct domain keyword analysis. Winnability scoring applies to Session 2 clustering. TAM/SAM/SOM becomes part of Session 3 strategy. Fix the 1K keyword cap and top-200 scoring limit. |
| **G6** | **Scoring Algorithms** (6 modules: winnability, opportunity, difficulty, competitor, decay, maturity) | These are proprietary mathematical formulas — pure functions that don't depend on the engine architecture. v2.3 describes KOB scoring conceptually but has no specific algorithms. | **Port directly** into new system's processing scripts. The winnability score feeds into Feed cluster prioritization. The opportunity score feeds into keyword role tagging. The decay score feeds into content decay monitoring. |
| **G7** | **Context Intelligence** (business profiler, 9-signal market detection, market resolver, competitor discovery + classification) | Auto-detects business model, market, audience from website signals. v2.3 assumes Alex manually creates client config. | **Port as pre-Session-1 automation.** Run context intelligence → auto-populate `config/clients/{slug}.json` → Alex confirms. Saves 15-20 min per client onboarding. |
| **G8** | **Competitor Discovery & Classification** (SERP overlap + Perplexity + traffic share → classify as DIRECT/SEO/CONTENT/EMERGING/ASPIRATIONAL) | v2.3 mentions Semrush "organic competitors discovery (top 10 by keyword overlap)" in Session 1, but has no classification system. | **Port the classification logic.** Auto-discover via Ahrefs SERP overlap + Semrush organic competitors. Classify by type + threat level. Present for Alex's curation in Session 1 before proceeding with analysis. |
| **G9** | **Backlink Data Models** (Backlink table with anchor_type, quality_score, spam_score, temporal tracking; ReferringDomain with anchor_distribution, domain_type) | Rich backlink metadata exists but isn't exported in the format v2.3 requires. | **Adapt into Link Target Export.** The data models have the fields — need to add: contact URL, acquisition method tag, priority tier calculation. |
| **G10** | **Interactive Dashboard Components** (SoV, Attack/Defend battleground, KUCK content audit, topical authority visualization) | Valuable analysis concepts even if the REST API delivery mechanism changes. | **Port the calculation logic into Google Sheets tabs + Looker Studio.** SoV → `sov` tab. Battleground → report Section IV (quick wins are already there). KUCK → `content-health` tab maps naturally to v2.3's content decay monitoring. |

### 3.3 MEDIUM-VALUE GAPS — Nice to Have

| # | Current Feature | Why It Matters | Recommendation |
|---|----------------|----------------|----------------|
| **G11** | **Real-Time Job Status Polling** | Not needed for consultant-operated tool. | Drop. |
| **G12** | **Database Persistence** (PostgreSQL, 20+ tables, ranking history) | v2.3 uses files on disk. For quarterly re-audits, need historical comparison. | Files are simpler. For historical comparison: keep previous audit folders intact, diff against them in quarterly re-audits. Add lightweight SQLite if needed later. |
| **G13** | **Analysis Engine (V4: 4 loops, V5: 7 agents)** | Both engines are replaced by v2.3's approach: Python processing + Claude synthesis across 4 sessions. | **Drop entirely.** v2.3's session-based architecture is fundamentally better — it processes data in Python and uses Claude for strategic synthesis, avoiding the truncation/fabrication problems of feeding raw data into LLM prompts. |
| **G14** | **Email Delivery** (Resend API, automated PDF on completion) | v2.3 delivers .docx manually + Looker Studio link. | Add later if needed. Could also use Google Drive sharing + email notification. |
| **G15** | **Multiple Report Formats** (External 10-15pg + Internal 40-60pg) | v2.3 has one 12-section report. | Consider keeping the split: 12-section report for client, Feed Exports + Link Targets for internal production use. The Feed Exports essentially replace the internal tactical report. |
| **G16** | **Precomputed Cache + Warming** (PostgreSQL cache, ETag headers, proactive warming) | v2.3 uses file-based caching with per-type TTL. Looker Studio auto-refreshes from Sheets. | File cache is sufficient. Google Sheets IS the precomputed cache layer for dashboards. |

### 3.4 DROP ENTIRELY

| Feature | Why |
|---------|-----|
| **V4 Analysis Engine** (4 sequential Claude loops with 10-item truncation) | Fundamentally broken: truncation, fabrication, unstructured output |
| **V5 Analysis Engine** (7 parallel agents, never deployed) | Replaced by v2.3's session architecture |
| **DataForSEO as sole data source** (60 endpoints) | v2.3 uses Ahrefs + Semrush + GSC. DataForSEO dropped entirely. |
| **WeasyPrint PDF generation** | Replaced by .docx generation |
| **PostgreSQL-backed caching** | Replaced by file cache + Google Sheets |
| **Tally webhook integration** | Not needed for consultant workflow |
| **Monolithic 60-endpoint data collection** | Replaced by per-source scripts |

---

## Part 4: Gap Analysis — What v2.3 Has That the Current System LACKS

| # | v2.3 Feature | Current System | Impact |
|---|-------------|----------------|--------|
| **N1** | **Feed Export system** (per-cluster JSON with Topics, Keywords, Entities, Competitive Context) | Monok export exists but is Strategy-level, not per-cluster. No entity extraction. No "also talk about" integration. No keyword role tagging (primary/supporting). | **Transformational** — Feed Exports are the primary production-facing deliverable. Current system has no equivalent. |
| **N2** | **Entity extraction** from Ahrefs "also talk about" data | **Not implemented at all.** Keywords have `parent_topic` field but no entity/concept layer. No depth signals. | **Major gap** — entities are what distinguish shallow SEO coverage from true topical authority. |
| **N3** | **Content Decay Monitoring** with GSC-based thresholds (position drop ≥3, clicks drop ≥20%, impressions drop ≥30%) | Decay scoring module exists (`src/scoring/decay.py`) with traffic/position/CTR/age components and KUCK mapping. But it's calculated from DataForSEO estimates, not GSC actuals. No 3-month trailing average. No refresh queue. | **Current scoring logic is portable** — needs GSC data source and trailing average calculation added. |
| **N4** | **Link Target Export** with acquisition methods, anchor text recommendations, contact URLs, priority tiers | Backlink/ReferringDomain models store DR, anchor_text, quality_score. Backlink Intelligence agent generates narrative recommendations. But no structured export format, no contact URLs, no acquisition method tags. | **Adapt existing models** — data fields mostly exist, need structured export format + contact URL scraping + method tagging. |
| **N5** | **Multi-source data** (Ahrefs + Semrush + GSC + PageSpeed + claude-seo) | DataForSEO only for all data. No Ahrefs, no Semrush, no GSC, no PageSpeed direct integration. | **Transformational** — cross-validated data vs single-source estimates. |
| **N6** | **Cross-validation** with confidence levels | None. All data from DataForSEO taken at face value. | **Quality leap** — honest confidence levels, catches data errors. |
| **N7** | **Topic extraction within clusters** via SERP overlap deduplication | Keywords grouped by `parent_topic` (DataForSEO field). No SERP overlap validation. No within-cluster Topic identification. | **New capability needed** — Ahrefs SERP overview can validate which keywords share top-10 results. |
| **N8** | **Keyword role tagging** (primary vs supporting) | All keywords treated equally. No role distinction. | **Simple addition** — high volume + cluster-defining = primary, everything else = supporting. |
| **N9** | **Competitive context per cluster** (dominant competitor, article count, difficulty assessment) | ContentCluster model has `competitive_assessment` field (text) but no structured per-cluster competitor data. | **Port competitor scoring logic** into cluster-level analysis. |
| **N10** | **Feed Performance dashboard page** | No Feed/cluster-level performance tracking. | **New Looker Studio page** — requires `feeds` Google Sheets tab with GSC data per cluster. |
| **N11** | **Content Health dashboard page** | No content health monitoring page. Dashboard shows KUCK recommendations but not ongoing health tracking. | **New Looker Studio page** — requires `content-health` Google Sheets tab with position/click/impression history. |
| **N12** | **Looker Studio live dashboards** (auto-refreshing via Google Sheets bridge) | Static PostgreSQL cache. Dashboard is REST API-served, not auto-refreshing. | **Architectural improvement** — clients see live data without API calls. |
| **N13** | **Data provenance** on every data point (source, date, confidence) | None. No metadata tracking which tool produced which data point. | **Trust and quality** — essential for client-facing reports. |
| **N14** | **Human checkpoint** before delivery | Fully automated pipeline. | **Prevents hallucinated strategy** from reaching clients. |
| **N15** | **Session isolation** (context clears between phases) | Single long context that overflows on large domains. | **Prevents context corruption** — each session works from condensed briefings. |
| **N16** | **Sacred raw data** (never modified after writing) | In-memory data lost after analysis. No audit trail. | **Reproducibility** — can reprocess from raw if something goes wrong. |
| **N17** | **Quarterly re-audit with Feed updates** | No historical comparison capability. Single-shot analysis only. | **Ongoing client value** — shows progress, updates strategy based on actual performance. |
| **N18** | **AI search visibility** (Brand Radar across 6 platforms) | Basic AI visibility endpoints from DataForSEO. | **Comprehensive GEO/AIO coverage** — Brand Radar tracks mentions in ChatGPT, Gemini, Perplexity, Google AI Overviews, Google AI Mode, Copilot. |
| **N19** | **Phased roadmap built around Feed activation** (Q1-Q4 with per-Feed targets) | Generic 4-quarter roadmap in report. | **Operationalizable** — tied to specific Feeds with velocity allocations and expansion criteria. |

---

## Part 5: Recommendations — What to Port from Current into v2.3

### Tier 1: Port Directly (Pure functions, no architecture dependency)

| Current Code | Port To | What to Preserve | What to Change |
|-------------|---------|------------------|----------------|
| `src/scoring/opportunity.py` | `scripts/process/scoring.py` | Formula: volume(20%) + difficulty(20%) + intent(20%) + position_gap(20%) + topical(20%) + freshness modifier | Input: change from DataForSEO data to Ahrefs+Semrush cross-validated data. Add keyword role output (primary if score ≥60 + high volume, else supporting). |
| `src/scoring/difficulty.py` | `scripts/process/scoring.py` | Personalized difficulty adjustment: base_kd ± SERP factors ± domain factors | Input: change from DataForSEO KD to Semrush PKD as base. Ahrefs DR for SERP authority analysis. |
| `src/scoring/greenfield.py` (winnability) | `scripts/process/scoring.py` | Formula: (100 - difficulty) × 0.6 + volume × 0.2 + competitor_saturation × 0.1 + topical_distance × 0.1 | This feeds into Feed cluster prioritization for greenfield clients. Remove the 200-keyword scoring cap. |
| `src/scoring/competitor_scoring.py` | `scripts/process/scoring.py` | Threat level: (DR × 0.3 + overlap × 0.4 + traffic_share × 0.3) × 100 | Replace DataForSEO overlap data with Ahrefs SERP overlap + Semrush organic competitors. |
| `src/scoring/decay.py` | `scripts/process/content_decay.py` | Decay components: traffic(40%) + position(30%) + CTR(20%) + age(10%). KUCK action mapping. | Change input from DataForSEO estimates to GSC actuals. Add 3-month trailing average. Add v2.3 thresholds (position ≥3, clicks ≥20%, impressions ≥30%). Output becomes refresh queue format. |
| `src/scoring/greenfield.py` (maturity) | `scripts/process/scoring.py` | Domain classification: greenfield/emerging/established | Use Ahrefs DR + keyword count instead of DataForSEO. |

### Tier 2: Adapt (Needs architectural changes)

| Current Code | Adapt To | What Changes |
|-------------|----------|-------------|
| `src/context/business_profiler.py` + `market_detection.py` + `competitor_discovery.py` | Pre-Session-1 automation: `scripts/gather/context_intelligence.py` | Run before Session 1 to auto-populate `config/clients/{slug}.json`. Remove DataForSEO dependency — use Ahrefs batch-analysis for domain metrics, Semrush organic competitors for competitor discovery. Keep the 9-signal market detection (schema.org, hreflang, TLD, etc.) — those are website-analysis based, not API-dependent. |
| `src/context/competitor_discovery.py` (classification logic) | Part of Session 1 GATHER | Keep the DIRECT/SEO/CONTENT/EMERGING/ASPIRATIONAL classification. Keep the "Facebook problem" solver (filtering out platforms). Replace DataForSEO discovery with Ahrefs SERP overlap + Semrush organic competitors. Present candidates for Alex's curation before Session 2. |
| Strategy Builder → `build_monok_export()` | `scripts/export/feed_export.py` | The Monok export flattens strategy→threads→topics→keywords into JSON. The Feed Export needs per-cluster structure: Topics array + Keyword pool + Entities + Competitive Context. The thread→topic hierarchy maps roughly to Feed→Topic, but Entities don't exist in the current model and must be added from "also talk about" data. |
| Dashboard SoV calculation | Google Sheets `sov` tab | Port the share-of-voice calculation logic. Write results to Sheets instead of serving via REST API. Looker Studio visualizes from Sheets. |
| Dashboard KUCK logic | Google Sheets `content-health` tab | KUCK (Keep/Update/Consolidate/Kill) maps directly to v2.3's content decay monitoring. Port the action determination logic, change input to GSC data with trailing averages. |
| Greenfield pipeline (G1-G5) | Session 1 variant for low-DR clients | G1 (competitor discovery) → Session 1 with competitor-first discovery. G2 (keyword universe) → Ahrefs organic-keywords on discovered competitors. G3 (winnability) → scoring.py applied in Session 2. G4 (TAM/SAM/SOM) → Session 3 strategy. G5 (beachheads) → Feed cluster prioritization. Fix: remove 1K keyword cap, score ALL keywords not just top 200. |

### Tier 3: Add Later (When Needed)

| Feature | When to Add |
|---------|-------------|
| Web UI / SaaS platform | If/when you want client self-service or team collaboration |
| Authentication | When building web UI |
| Interactive strategy builder | When clients need to self-edit Feed structures (consider Google Sheets as interactive layer) |
| Email delivery | When you want automated report delivery |
| Real-time progress tracking | When building web UI |

### Drop Entirely

| Feature | Why |
|---------|-----|
| V4 analysis engine (4 sequential Claude loops) | Broken: 10-item truncation, fabricated research, unstructured output |
| V5 analysis engine (7 parallel agents, never deployed) | Replaced by v2.3's session architecture |
| DataForSEO as data source | Dropped from v2.3 tool stack entirely |
| WeasyPrint PDF generation | Replaced by .docx generation |
| 60-endpoint monolithic data collection | Replaced by per-source scripts with Ahrefs + Semrush |
| PostgreSQL-backed caching | Replaced by file cache + Google Sheets bridge |
| Tally webhook integration | Not needed for consultant workflow |

---

## Part 6: Summary Decision Matrix

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| **SaaS vs. Consultant tool** | Start consultant-operated (v2.3 as-is), add web layer later if needed | Validate quality first. Looker Studio IS the client-facing UI. |
| **Feed Exports** | Build as v2.3 specifies — this is the core new capability | No equivalent in current system. Strategy Builder export is too flat. |
| **Scoring algorithms** | Port all 6 modules into `scripts/process/scoring.py`, adapt inputs from DataForSEO to Ahrefs+Semrush | Pure functions, no architecture dependency. Immediate value. |
| **Context intelligence** | Port as pre-Session-1 automation | Saves 15-20 min per client. Replace DataForSEO deps with Ahrefs+Semrush. |
| **Competitor discovery + classification** | Port classification logic, replace discovery sources | Keep DIRECT/SEO/CONTENT/EMERGING taxonomy. Use Ahrefs+Semrush instead of DataForSEO+Perplexity. |
| **Content decay monitoring** | Port decay scoring formulas, add GSC-based thresholds per v2.3 | Current formula components are good. Need GSC actuals + 3-month trailing average + refresh queue format. |
| **Link Target Export** | Build new export format, adapt existing backlink models | Data fields mostly exist in current Backlink/ReferringDomain models. Add contact URL, acquisition method, tier calculation. |
| **Greenfield pipeline** | Port as Session 1 variant for low-DR clients | Competitor-first discovery + winnability scoring + TAM/SAM/SOM, but without DataForSEO. Fix the data loss issues (1K cap, 200-keyword scoring limit). |
| **Strategy Builder** | Don't port the interactive UI. Feed Exports replace it. | If interactive editing is needed, use Google Sheets on the Feed Export JSON. |
| **Database** | Files on disk (v2.3 approach) | Simpler, auditable, no schema migrations. Historical comparison via folder structure. |
| **Dashboard** | Looker Studio 9 pages (v2.3) + ported SoV/KUCK logic | Current dashboard components port well into Sheets tabs. |

---

## Conclusion

The v2.3 spec is a fundamentally different product than the current system:

- **Current system:** A SaaS platform that serves interactive dashboards and an editable strategy builder via REST APIs, powered by a single data source (DataForSEO) feeding into LLM-based analysis loops that truncate and fabricate data.
- **v2.3 spec:** A consultant-operated tool that produces structured deliverables (Feed Exports, Link Target Exports, .docx report, Looker Studio dashboard) from multi-source cross-validated data, processed in Python and synthesized by Claude across 4 isolated sessions with a human checkpoint.

**What the current system has that's worth keeping (and why):**

1. **Scoring algorithms** (6 modules of pure mathematical formulas) — they power keyword prioritization, cluster ranking, competitor assessment, and content decay detection. Port them into v2.3's processing scripts.
2. **Context Intelligence** (business profiling, 9-signal market detection, competitor discovery + classification) — automates client onboarding that v2.3 assumes is manual. Port as pre-Session-1 step.
3. **Greenfield methodology** (competitor-first discovery, winnability scoring, TAM/SAM/SOM market sizing) — unique approach for new domains. Port as Session 1 variant.
4. **Dashboard calculation logic** (SoV, KUCK) — valuable analysis concepts that map to v2.3's Google Sheets tabs.
5. **Decay scoring formulas** — the 4-component weighted score with KUCK mapping. Adapt for GSC-based monitoring with v2.3's specific thresholds.

**What the current system has that should be dropped:**

Everything else — the V4/V5 analysis engines, the monolithic DataForSEO pipeline, the PostgreSQL cache, the SaaS platform layer, the auth system, the interactive strategy builder UI. These either have fundamental quality problems (engines), are replaced by better approaches (file cache, Google Sheets, Feed Exports), or are premature for a consultant workflow (SaaS, auth).

**Build v2.3 first. Port the 5 categories of valuable IP into it. Validate that the system produces quality deliverables for 2-3 real clients. Then decide if you need a platform layer on top.**

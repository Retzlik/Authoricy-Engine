# Current System vs. New Build Spec: Full Gap Analysis

## Overview

This document provides a **thorough gap analysis** between the **current Authoricy Engine** (45,000 LoC Python/FastAPI SaaS platform with 70+ API endpoints, interactive dashboards, strategy builder, multi-mode analysis) and the **New Build Spec** defined in `authoricy-seo-infrastructure-spec.md`.

The current system is far more than just an analysis engine — it's a multi-tenant SaaS platform with authentication, interactive dashboards, a strategy builder, greenfield intelligence, and client-facing APIs. The new spec is a CLI/script-based consultant workflow. This comparison maps every feature in both systems and identifies what must be carried forward.

---

## Part 1: Complete Feature Inventory — Current System

### 1.1 Multi-Mode Analysis (3 paths)

| Mode | Trigger | What It Does | Status |
|------|---------|-------------|--------|
| **Greenfield** | DR<20, KW<50 | 5-stage pipeline: competitor discovery → keyword universe (1K cap) → SERP winnability (top 200) → market sizing (TAM/SAM/SOM) → beachhead selection (20 keywords) | Working (with documented data loss issues) |
| **Hybrid/Emerging** | DR<35, KW<200 | Collects 500 ranked keywords, discovers competitors via SERP overlap, analyzes keyword gaps (100 per competitor), selects 35 beachheads from striking distance + low-KD gaps | Working (partial) |
| **Standard/Established** | DR>35, KW>200 | Auto-detection triggers but analysis is a TODO stub — marks complete immediately without running anything | **NOT IMPLEMENTED** |

### 1.2 Interactive Dashboard — Standard Domains (9 endpoints)

| Endpoint | What It Shows | Limits |
|----------|-------------|--------|
| `GET /overview` | Health scores, position distribution, metric comparisons | No truncation on overview |
| `GET /sov` | Share of Voice — market share vs competitors | 10 competitors max, 30-day trend always null |
| `GET /sparklines` | Position trends for keywords | Top 20 keywords only |
| `GET /battleground` | Attack/Defend keyword recommendations | 25 per category (100 total) |
| `GET /clusters` | Topical authority analysis | Returns ALL clusters |
| `GET /content-audit` | KUCK recommendations (Keep/Update/Consolidate/Kill) | 50 pages per category |
| `GET /intelligence-summary` | AI-generated findings from agent outputs | 5 per agent, 10 per priority tier, not cached |
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

### 1.5 Context Intelligence System (8 files, ~200K LoC)

| Component | What It Does |
|-----------|-------------|
| **Business Profiler** | Auto-detects business model, products, target market, audience from website |
| **Market Detection** | 9 signal sources (schema.org address, hreflang, TLD, phone codes, VAT, currency, store selector, shipping pages, language) |
| **Market Resolver** | Maps detected market to DataForSEO location codes |
| **Market Validator** | Validates market fit, detects conflicts |
| **Competitor Discovery** | SERP overlap + Perplexity AI semantic search + traffic share analysis |
| **Website Analyzer** | Analyzes site structure, navigation, content patterns |
| **Sitemap Parser** | Parses XML sitemaps to understand site scope |

### 1.6 Scoring Algorithms (6 modules)

| Algorithm | What It Calculates |
|-----------|-------------------|
| **Winnability** (`greenfield.py`) | 0-100 score: likelihood a new domain can rank for a keyword based on SERP analysis |
| **Opportunity** (`opportunity.py`) | Composite: volume × CTR estimate ÷ difficulty, adjusted for intent |
| **Difficulty** (`difficulty.py`) | Adjusted keyword difficulty personalized for domain maturity |
| **Competitor Scoring** (`competitor_scoring.py`) | Threat level: true competitor vs affiliate vs media vs platform |
| **Decay** (`decay.py`) | Time-decay weighting for historical data freshness |
| **Domain Maturity** (`greenfield.py`) | Classifies domains: greenfield / emerging / established |

### 1.7 Authentication & Multi-Tenancy (9 files)

| Feature | Implementation |
|---------|---------------|
| JWT validation | Supabase JWT tokens |
| User management | Get/update profile, list users, roles, enable/disable |
| Domain ownership | Users own domains, access checks on all endpoints |
| Admin access | Admins can access any domain/strategy |
| Usage tracking | Per-user API usage monitoring |

### 1.8 Caching & Performance (5 endpoints + infrastructure)

| Feature | Implementation |
|---------|---------------|
| PostgreSQL cache | Precomputed dashboard components, 4-hour TTL |
| HTTP cache headers | ETag, stale-while-revalidate, conditional 304 responses |
| Cache invalidation | Per-domain, per-analysis, or flush all |
| Precomputation trigger | On-demand precompute after analysis |
| Cache warming | Proactively warm cache for a domain |

### 1.9 Data Collection (60 DataForSEO endpoints)

4-phase parallel collection:

| Phase | Endpoints | Data |
|-------|-----------|------|
| Phase 1: Foundation | 8 | Domain metrics, traffic, technologies, subdomains, top pages |
| Phase 2: Keywords | 16 | Ranked keywords, universe, gaps, suggestions, intent, difficulty, SERP, historical, questions |
| Phase 3: Competitive | 19 | Competitor metrics, backlinks, anchors, referring domains, link gaps |
| Phase 4: AI/Technical | 17 | AI visibility, LLM mentions, on-page audit, trends, brand mentions, CWV |

### 1.10 Report Generation

| Format | Sections | Status |
|--------|----------|--------|
| **External Report** | 10-15 page executive summary for leads | Implemented |
| **Internal Report** | 40-60 page tactical playbook | Implemented |
| **Charts** | SVG chart generation (position distribution, traffic trends, etc.) | Implemented |
| **Confidence Scoring** | Data completeness ratings on each section | Implemented |
| **PDF Generation** | WeasyPrint HTML → PDF | Implemented |

### 1.11 Email Delivery

| Feature | Implementation |
|---------|---------------|
| PDF delivery | Resend API with PDF attachment |
| Automated sending | Triggered on analysis completion |

### 1.12 Database (20+ tables)

Full PostgreSQL schema with:
- Domains, analysis runs, keywords, competitors, backlinks, pages
- Ranking history, domain metrics history
- Content clusters, keyword gaps, SERP features
- AI visibility, technical metrics
- Agent outputs (analysis results)
- Strategies, threads, topics, thread keywords
- Strategy exports, activity logs
- Greenfield analyses, greenfield competitors
- Competitor intelligence sessions
- Precomputed dashboard cache

---

## Part 2: Complete Feature Inventory — New Build Spec

### 2.1 Data Collection (5 APIs + 2 local tools)

| Source | Primary Role | Method |
|--------|-------------|--------|
| **Ahrefs** | Backlinks, DR, parent topic clustering, Brand Radar, Site Audit | MCP connector |
| **Semrush** | Keyword volumes (most accurate), PKD, topical authority | MCP connector |
| **DataForSEO** | SERP scraping, bulk keywords, on-page/Lighthouse, intent classification | MCP connector |
| **Google Search Console** | Ground truth: clicks, impressions, queries, indexation | Native API |
| **PageSpeed Insights** | Core Web Vitals, Lighthouse scores | REST API |
| **Screaming Frog** | Deep technical crawls, JS rendering, structured data, internal linking | CLI/headless (local) |
| **claude-seo skill** | 12 slash commands: audit, schema, GEO, E-E-A-T, sitemap, images, hreflang | Local skill |

### 2.2 Cross-Validation Methodology

| Data Type | Primary → Validation → Tiebreaker | Formula |
|-----------|-----------------------------------|---------|
| Keyword volumes | Semrush (0.45) → DataForSEO (0.30) → Ahrefs (0.25) | Weighted average with variance detection |
| Backlinks | Ahrefs (primary) → Semrush (comparison) | Report both, don't average |
| Traffic (competitors) | Range: [MIN(all tools), MAX(all tools)] | Never single numbers |
| Traffic (own site) | GSC only (ground truth) | Never use estimates when actuals available |
| Domain authority | Ahrefs DR + Moz DA + Semrush AS | Three independent sources |

### 2.3 Processing Scripts

| Script | What It Does |
|--------|-------------|
| `cross_validate.py` | 3-source weighted volume validation with confidence tiers |
| `keyword_cluster.py` | Groups by Ahrefs parent_topic field |
| `backlink_gap.py` | Domains linking to 2+ competitors but not client |
| `content_gap.py` | Keywords competitors rank for, client doesn't |
| `technical_aggregate.py` | Combines Screaming Frog + Ahrefs + claude-seo + PSI findings |
| `generate_briefing.py` | Creates phase briefing files from processed data |

### 2.4 Four-Session Workflow

| Session | Duration | Input → Output |
|---------|----------|---------------|
| **GATHER** | ~30 min | Domain → raw data + claude-seo outputs → phase1-briefing.md |
| **ANALYSE** | ~30 min | Phase 1 briefing → cross-validated processed data → phase2-briefing.md |
| **STRATEGISE** | ~45 min | Phase 2 briefing → prioritized strategy → phase3-briefing.md + HUMAN REVIEW |
| **DELIVER** | ~60 min | Approved phase 3 briefing → report.docx + dashboard data |

### 2.5 Report (.docx, 12 sections)

Executive Summary, Current State, Technical SEO, Keyword Research, Topical Map, Content Strategy, Backlink Profile, SERP Features & AI Search (GEO), Local SEO, Competitive Intelligence, Implementation Roadmap, Appendices with data provenance.

### 2.6 Looker Studio Dashboard (7 pages)

Executive Overview, Keyword Performance, Content Performance, Backlink Health, Technical Health, AI Visibility, Competitive Snapshot.

### 2.7 Ongoing Operations

- Monthly monitoring: 15 min/client via `to_sheets.py`
- Quarterly re-audits: full 4-session workflow
- Client onboarding checklist
- GSC onboarding process for clients without it

### 2.8 Caching

File-based: `cache/{domain}/{tool}/{datatype}_{date}.json` with per-type TTL (1-30 days).

---

## Part 3: Gap Analysis — What the New Spec DOES NOT Cover

These are features in the current system that the new spec **completely omits or doesn't address**. These represent the "what would we lose?" question.

### 3.1 CRITICAL GAPS — Must Be Addressed

| # | Current Feature | Why It Matters | Recommendation |
|---|----------------|----------------|----------------|
| **G1** | **SaaS Platform / Web UI** | The current system has 70+ REST API endpoints powering an interactive web dashboard. The new spec is a CLI/script workflow operated by you (Alex). If you want clients or team members to self-serve, you need a frontend. | **Decision needed**: Is the new system consultant-operated only (you run it, clients get deliverables)? Or do you still want a self-service SaaS? The spec assumes consultant-operated. If so, this gap is intentional. |
| **G2** | **Authentication & Multi-Tenancy** | JWT auth, user roles, domain ownership, admin access. The new spec has no auth — it's a local tool. | If consultant-operated: not needed. If SaaS: must be reimplemented. |
| **G3** | **Auto-Detection / Domain Routing** | Unified API auto-detects greenfield/emerging/established and routes to different workflows. The new spec assumes you manually know the client's maturity level. | Add to new spec: run `ahrefs_pull.py` for domain overview first, classify maturity, then route to appropriate workflow variant. |
| **G4** | **Strategy Builder** (30+ endpoints) | Full interactive CRUD for strategies → threads → topics → keywords. Drag-and-drop organization, bulk operations, AI-suggested clusters, export to Monok. | **This is significant IP**. The new spec produces a content strategy in the report but has no interactive tool for refining it. Options: (a) Rebuild as standalone app, (b) Export strategy data as structured CSVs that can be imported into a tool, (c) Build a lightweight Notion/Sheets-based equivalent. |
| **G5** | **Greenfield Pipeline** (G1-G5) | Despite its data loss problems, the greenfield pipeline has a unique methodology: competitor-first discovery, winnability scoring, TAM/SAM/SOM market sizing, beachhead selection. The new spec doesn't distinguish between new and established domains. | Preserve the methodology but fix the data loss. The greenfield workflow should become a variant of Session 1 GATHER that uses competitor mining instead of direct domain analysis. |

### 3.2 HIGH-VALUE GAPS — Should Be Preserved

| # | Current Feature | Why It Matters | Recommendation |
|---|----------------|----------------|----------------|
| **G6** | **Scoring Algorithms** (6 modules) | Winnability, opportunity, difficulty adjustment, competitor threat scoring, time decay, domain maturity classification. These are proprietary IP. | Port these into the new spec's `scripts/process/` directory. The winnability scoring belongs in `keyword_cluster.py` or a new `scoring.py`. |
| **G7** | **Context Intelligence** (business profiling, market detection) | Auto-detects business model, target market, audience from website signals. 9-signal market detection (schema.org, hreflang, TLD, phone codes, etc.). | Port into new spec as a preprocessing step before Session 1. Run `context_intelligence.py` to populate `config/clients/{slug}.json` automatically instead of manual config creation. |
| **G8** | **Competitor Discovery & Classification** | Auto-discovers via SERP + Perplexity, classifies as true competitor vs affiliate vs media vs platform ("Facebook problem" solver). | Port the discovery logic into new spec's Session 1. Replace manual competitor entry in client config with auto-discovery + curation. |
| **G9** | **Competitor Curation Workflow** | User reviews 15 auto-discovered competitors, removes irrelevant ones, adds custom ones, assigns purposes. | Add a curation step to Session 1: auto-discover → present candidates → human curates → proceed with curated set. |
| **G10** | **Interactive Dashboard Components** | Share of Voice, Attack/Defend battleground, KUCK content audit, topical authority visualization. Even with documented limits (10 competitors, 20 sparklines), these are valuable visualizations. | The new spec has Looker Studio dashboards but with different components. Port the SoV, battleground, and KUCK concepts into Looker Studio pages or Google Sheets tabs. |

### 3.3 MEDIUM-VALUE GAPS — Nice to Have

| # | Current Feature | Why It Matters | Recommendation |
|---|----------------|----------------|----------------|
| **G11** | **Real-Time Job Status Polling** | Users can poll analysis progress. | Not needed if consultant-operated. If building a web UI later, add back then. |
| **G12** | **Database Persistence** | PostgreSQL with 20+ tables, ranking history, metrics history. | The new spec uses files on disk. For single-consultant use, files are simpler. If you need historical comparison across quarterly re-audits, add a lightweight SQLite database or structured JSON archive. |
| **G13** | **V5 Analysis Engine** (7 parallel agents + quality gates) | Better architecture than V4 but never deployed. | The new spec's approach (Python processing + Claude synthesis) is superior to both V4 and V5. Don't port this — the new architecture solves the same problem better. |
| **G14** | **Email Delivery** | Automated PDF-to-email via Resend. | The new spec delivers .docx manually. If you want automated delivery, add Resend or use Google Drive sharing + email notification. |
| **G15** | **Tally Webhook Integration** | Form submission triggers analysis. | Not needed if consultant-operated. Useful if you want a lead-gen form that auto-triggers audits later. |
| **G16** | **Cache Warming & Precomputation** | Proactive cache population for fast dashboard loads. | The new spec has file-based caching with TTL. For Looker Studio, Google Sheets acts as the cache layer. |
| **G17** | **Multiple Report Formats** | External (10-15 pg executive) + Internal (40-60 pg tactical). | The new spec has one 12-section report. Consider keeping the external/internal split: external for client delivery, internal for your reference. |

### 3.4 LOW-VALUE GAPS — Can Be Dropped

| # | Current Feature | Why | Recommendation |
|---|----------------|-----|----------------|
| **G18** | V4 Analysis Engine (4 sequential loops) | Fundamentally broken: 10-item truncation, fabricated research, unstructured output. | Do not port. The new architecture replaces this entirely. |
| **G19** | WeasyPrint PDF Generation | .docx is more editable and client-friendly than PDF. | Drop in favor of docx-js. |
| **G20** | DataForSEO as sole data source | The new spec uses 5+ sources with cross-validation. | Drop exclusivity. DataForSEO remains as one source among many. |
| **G21** | 60-endpoint DataForSEO collection | Most endpoints feed data that gets truncated to 10 items anyway. | Collect what you need from each tool, not everything from one tool. |

---

## Part 4: Gap Analysis — What the New Spec HAS That the Current System LACKS

| # | New Spec Feature | Current System | Impact |
|---|-----------------|----------------|--------|
| **N1** | Multi-source data (Ahrefs, Semrush, DataForSEO, GSC, PSI) | DataForSEO only | Transformational — cross-validated data vs single-source estimates |
| **N2** | Cross-validation with weighted formulas | None | Quality leap — honest confidence levels |
| **N3** | Screaming Frog deep technical crawls | No crawling at all | Full technical audit vs estimated on-page data |
| **N4** | claude-seo skill (schema, E-E-A-T, GEO, sitemap, hreflang, images) | No on-page analysis | Actual page content analysis vs API summaries |
| **N5** | GSC as ground truth | No GSC integration | Real clicks/impressions vs estimated traffic |
| **N6** | Looker Studio live dashboards (auto-refreshing) | Static PostgreSQL cache | Clients can check progress anytime without your involvement |
| **N7** | Data provenance on every data point | None | Audit trail, client trust, methodology transparency |
| **N8** | Human checkpoint before delivery | Fully automated | Prevents hallucinated strategy from reaching clients |
| **N9** | Quality gates at phase transitions | Quality gates check prose form, not data substance | Actually catches problems vs rubber-stamping |
| **N10** | Fallback chains per data type | Single-source, fail = no data | Resilient data collection |
| **N11** | Session isolation (context clears) | Single long context that overflows | Prevents context window corruption |
| **N12** | Idempotent, re-runnable scripts | Monolithic pipeline, crash = restart everything | Session recovery |
| **N13** | Sacred raw data (never modified) | In-memory data lost after analysis | Reproducible, auditable |
| **N14** | Monthly monitoring workflow | Single-shot analysis only | Ongoing client value |
| **N15** | Quarterly re-audit with comparison | No historical comparison | Shows progress over time |
| **N16** | AI search visibility (Brand Radar, 6 platforms) | Basic AI visibility endpoints | Comprehensive GEO/AIO coverage |
| **N17** | Topic cluster maps (5-8 clusters × 8-15 articles) | Content clusters exist but shallow | Operationalizable content strategy |
| **N18** | Content briefs based on SERP analysis | Content briefs from Claude imagination | Briefs grounded in competitive reality |
| **N19** | Link building targets categorized by acquisition method | Backlink gap exists but no acquisition strategy | Actionable link building vs list of domains |
| **N20** | Explicit tool selection rules | Use whatever DataForSEO returns | Right tool for right job |

---

## Part 5: Merged Feature Map — What the New System Should Include

This is the recommended feature set for the new build, combining the best of both systems.

### Tier 1: Core (New Spec + Critical Current Features)

| Feature | Source | Implementation |
|---------|--------|---------------|
| Multi-source data collection | New Spec | `scripts/gather/` per source |
| Cross-validation methodology | New Spec | `scripts/process/cross_validate.py` |
| 4-session workflow (GATHER → ANALYSE → STRATEGISE → DELIVER) | New Spec | Session structure with context clears |
| Quality gates at phase transitions | New Spec | `scripts/validate/data_check.py` |
| 12-section .docx report | New Spec | `scripts/report/generate_report.js` |
| Looker Studio dashboards (7 pages) | New Spec | Google Sheets bridge + template |
| Monthly monitoring + quarterly re-audit | New Spec | `scripts/export/to_sheets.py` |
| Data provenance + confidence tracking | New Spec | `metadata.json` per audit |
| **Domain maturity auto-detection** | Current (G3) | Run Ahrefs/DataForSEO domain overview → classify → route to appropriate workflow variant |
| **Greenfield variant** | Current (G5), fixed | Competitor-first discovery in Session 1, winnability scoring in Session 2, market sizing in briefing |
| **Scoring algorithms** | Current (G6) | Port winnability, opportunity, difficulty, competitor scoring into `scripts/process/` |
| **Context intelligence** | Current (G7) | Auto-populate client config from website analysis before Session 1 |
| **Competitor discovery + classification** | Current (G8, G9) | Auto-discover in Session 1, present for curation, proceed with curated set |

### Tier 2: High Value (Port from Current)

| Feature | Source | Implementation |
|---------|--------|---------------|
| **Strategy export structure** | Current (G4) | Generate structured JSON/CSV strategy output compatible with Monok AI format |
| **Share of Voice calculation** | Current (G10) | Port SoV logic into Google Sheets tab for Looker Studio |
| **Attack/Defend battleground** | Current (G10) | Include as section in report + dashboard tab |
| **KUCK content audit** | Current (G10) | Port Keep/Update/Consolidate/Kill logic into `scripts/process/content_audit.py` |
| **Traffic projections** (3 scenarios) | Current (G5) | Port projection model into Session 3 strategy output |
| **Beachhead selection** (fixed) | Current (G5) | Score ALL keywords, not just top 200; include in greenfield report variant |
| **Historical comparison** | Current (G12) | Store audit data by date, compare in quarterly re-audit reports |

### Tier 3: Add Later (When Needed)

| Feature | Source | When to Add |
|---------|--------|-------------|
| **Web UI / SaaS platform** | Current (G1-G2) | If/when you want client self-service or team collaboration |
| **Authentication** | Current (G2) | When building web UI |
| **Interactive strategy builder** | Current (G4) | When clients need to self-edit strategies (consider Notion/Sheets as MVP) |
| **Email delivery** | Current (G14) | When you want automated report delivery |
| **Real-time progress tracking** | Current (G11) | When building web UI |

### Drop Entirely

| Feature | Why |
|---------|-----|
| V4 analysis engine (4 loops) | Broken core: 10-item truncation, fabricated research |
| V5 analysis engine (unused) | New architecture is superior |
| DataForSEO as sole source | Replaced by multi-source approach |
| WeasyPrint PDF | Replaced by docx-js |
| 60-endpoint monolithic collection | Replaced by per-source scripts |
| PostgreSQL-backed cache | Replaced by file cache + Google Sheets bridge |

---

## Part 6: Implementation Approach

### How to Preserve Current IP in the New Architecture

**1. Scoring Algorithms → `scripts/process/scoring.py`**

```
Current:  src/scoring/greenfield.py    → New: scripts/process/scoring.py
          src/scoring/opportunity.py
          src/scoring/difficulty.py
          src/scoring/competitor_scoring.py
          src/scoring/decay.py
```

Port the mathematical formulas (winnability, opportunity, difficulty adjustment). These are pure functions that don't depend on the V4/V5 engine.

**2. Context Intelligence → `scripts/gather/context_intelligence.py`**

```
Current:  src/context/business_profiler.py     → New: scripts/gather/context_intelligence.py
          src/context/market_detection.py
          src/context/competitor_discovery.py
          src/context/website_analyzer.py
```

Run before Session 1 to auto-populate `config/clients/{slug}.json`. Replaces manual client config creation.

**3. Competitor Discovery → `scripts/gather/competitor_discovery.py`**

```
Current:  src/context/competitor_discovery.py   → New: scripts/gather/competitor_discovery.py
          src/scoring/competitor_scoring.py
```

Auto-discover competitors, classify as true/affiliate/media/platform, present for human curation in Session 1.

**4. Dashboard Concepts → Google Sheets Tabs + Looker Studio**

```
Current:  SoV calculation (dashboard.py)        → New: Google Sheets "sov" tab
          Battleground (dashboard.py)            → New: Google Sheets "battleground" tab
          KUCK content audit (dashboard.py)      → New: scripts/process/content_audit.py → "content-audit" tab
```

Port the calculation logic into Python scripts that write to Google Sheets tabs. Looker Studio visualizes them.

**5. Greenfield Pipeline → Session 1 Variant**

```
Current:  G1: Competitor Discovery              → New: scripts/gather/competitor_discovery.py
          G2: Keyword Universe                  → New: scripts/gather/ahrefs_pull.py + semrush_pull.py (competitor keywords)
          G3: SERP Winnability                  → New: scripts/process/winnability.py (score ALL keywords)
          G4: TAM/SAM/SOM                       → New: scripts/process/market_sizing.py
          G5: Beachhead Selection               → New: scripts/process/beachhead_selection.py
```

Same methodology, but: (a) no 1,000 keyword cap, (b) score ALL keywords not just top 200, (c) multi-source data instead of DataForSEO only.

**6. Strategy Export → `scripts/export/strategy.py`**

```
Current:  api/strategy.py (30+ endpoints)       → New: scripts/export/strategy.py
```

Instead of an interactive builder, generate the strategy structure programmatically in Session 3 and export as structured JSON/CSV compatible with Monok AI format.

---

## Part 7: Summary Decision Matrix

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **SaaS vs. Consultant tool** | (a) Rebuild as SaaS with new backend, (b) Consultant-only CLI/script tool, (c) Start consultant, add SaaS later | **(c)** Start with the spec as-is (consultant-operated), validate quality, then add a web layer when needed |
| **Strategy builder** | (a) Rebuild interactive builder, (b) Generate strategy as structured CSV/JSON, (c) Use Notion/Sheets as interactive layer | **(b)** for launch, **(c)** as quick enhancement — export strategy data into a shared Google Sheet that acts as the interactive layer |
| **Greenfield mode** | (a) Drop it, (b) Port methodology into new architecture | **(b)** Port as a Session 1 variant with fixed data loss issues |
| **Scoring algorithms** | (a) Drop (new spec doesn't mention them), (b) Port as-is, (c) Port and improve with multi-source data | **(c)** Port the formulas, enhance with cross-validated data inputs |
| **Context intelligence** | (a) Manual client config, (b) Auto-populate from website analysis | **(b)** Run context intelligence → auto-populate client config → human confirms |
| **Database** | (a) PostgreSQL (current), (b) Files only (new spec), (c) Files + lightweight SQLite for historical tracking | **(b)** for launch, **(c)** when quarterly re-audits need historical comparison |
| **Frontend** | (a) Build React frontend, (b) Looker Studio + manual workflow, (c) Build frontend later | **(b)** for launch — Looker Studio IS the client-facing UI |

---

## Conclusion

The new spec is a better foundation, but it shouldn't start from absolute zero. The current system has **four categories of IP worth preserving**:

1. **Scoring algorithms** (mathematical formulas, pure functions) — port directly
2. **Context intelligence** (market detection, competitor discovery) — port as preprocessing
3. **Greenfield methodology** (competitor-first, winnability, TAM/SAM/SOM) — port as workflow variant
4. **Dashboard calculation logic** (SoV, battleground, KUCK) — port into Google Sheets/Looker Studio

Everything else — the V4/V5 analysis engines, the monolithic DataForSEO collection, the prompt truncation pipeline, the PostgreSQL-backed caching — gets replaced by the new spec's simpler, more reliable architecture.

The new system is **narrower in platform features** (no SaaS, no auth, no interactive builder) but **deeper in analysis quality** (multi-source, cross-validated, human-reviewed). That's the right trade-off for a consultancy serving B2B clients at €2M-50M revenue.

Build the new spec first. Validate that it produces quality deliverables. Then decide if you need a SaaS platform on top of it.

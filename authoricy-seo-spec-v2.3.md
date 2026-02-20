# Authoricy SEO Infrastructure Specification
## Source of Truth — v2.3

> **This document is the project constitution.** It defines what to build, why, and what quality looks like. It does NOT prescribe implementation — Claude Code owns all code, architecture decisions, and technical solutions. When this document says "build a script that does X," it means deliver the capability. How you build it is your call.

> **Owner:** Alex / Authoricy AB
> **Last Updated:** 2026-02-20
> **Status:** Approved for implementation

---

## 1. MISSION

Build a multi-source SEO analysis system operated through Claude Code that takes a client domain + competitors as input and produces:

1. A comprehensive strategic audit report (.docx, 12 sections)
2. Feed Exports — structured, machine-readable cluster definitions (Topics, Keywords, Entities, Competitive Context) ready for ingestion by the content production system
3. Link Target Exports — prioritized backlink gap targets with acquisition intelligence
4. A live performance dashboard (Looker Studio via Google Sheets bridge)
5. Ongoing monthly monitoring data including content decay detection

**The system is the intelligence layer that powers content production.** It does not produce content itself. Its primary operational output is the Feed Export — the structured data that tells the content production system what to write about, which keywords to use, and what topical territory to cover. The audit report is the client-facing deliverable. The Feed Export is the production-facing deliverable. Both matter equally.

**Target clients:** B2B companies in the €2M-50M revenue range who are digitally under-invested. Expect 60-80% to have no Google Search Console configured, minimal existing SEO work, and need their entire organic strategy built from scratch.

**Target delivery time:** 2.5-4 hours per client audit (after system is built and tested).

**Operator:** Alex, who reviews strategy before final deliverable. This is not a fully automated pipeline — it's an analyst tool with a human checkpoint.

---

## 2. TOOL STACK

### 2.1 Data Sources (APIs via MCP)

| Tool | Access Method | Primary Role | Why This Tool |
|------|--------------|-------------|---------------|
| **Ahrefs** | MCP connector (Claude.ai / Claude Code) | Backlinks, Domain Rating, Parent Topic clustering, Brand Radar AI visibility, Content Explorer, Site Audit, SERP overview | Largest live backlink index (35T links, 15-30 min freshness). Parent Topic is the best automated clustering signal available. Brand Radar tracks AI mentions across 6 platforms — no alternative exists at this depth. Site Audit provides technical crawl data. |
| **Semrush** | MCP connector (Claude.ai / Claude Code) | Keyword volume validation, Personal Keyword Difficulty, Topical Authority, Traffic Analytics, search intent classification | 0% mismatch with Google Keyword Planner — most accurate keyword volumes available. Personal KD and Topical Authority are unique signals no other tool offers. Includes search intent with every keyword pull. |
| **Google Search Console** | Native API + Looker Studio connector | Ground truth for own-site performance: actual clicks, impressions, queries, indexation, manual actions | This is real Google data, not estimates. Irreplaceable from month 2 onward. |
| **Google PageSpeed Insights** | REST API (free, 25K queries/day) | Core Web Vitals field data, Lighthouse performance scores | Free, authoritative, uses real Chrome user experience data. |

### 2.2 Analysis Tools

| Tool | Role |
|------|------|
| **claude-seo skill** (free, MIT license) | 12 slash commands for Claude Code. Audit orchestration with 6 parallel subagents, E-E-A-T analysis (Dec 2025 core update), schema JSON-LD generation, GEO/AI search optimization framework. See Section 8 for integration details. |

### 2.3 Output Tools

| Tool | Role |
|------|------|
| **Looker Studio** (free) | Live client dashboards, auto-updating |
| **Google Sheets** (free) | Data bridge between APIs and Looker Studio for data that has no native Looker connector |
| **docx generation** (via Claude Code) | Strategic report generation (.docx) |
| **Chart generation** (via Python) | PNG charts embedded in reports |

---

## 3. TOOL SELECTION RULES

These are strategic decisions, not suggestions. Each data point in the system has a designated primary source and validation source. Claude Code must respect these assignments.

### 3.1 Keyword Volumes (for deliverables)

- **Primary:** Semrush — 0% GKP mismatch, most accurate
- **Validation:** Ahrefs — independent clickstream methodology
- **Ground truth (own site only):** GSC actual impressions
- **Cross-validation:** Compare Semrush vs Ahrefs. If variance < 30%: high confidence, use Semrush as the reported number. If variance > 30%: moderate confidence, flag in metadata, present both numbers. If variance > 50%: low confidence, investigate manually, note in report.
- When GSC is available for own site, use actual impressions as ground truth and calculate per-tool correction factors.

### 3.2 Backlink Analysis

- **Primary:** Ahrefs — largest live index, freshest data (15-30 min updates)
- **Validation:** Semrush — different crawler, catches some links Ahrefs misses
- **Reporting:** Always report Ahrefs count as primary, note Semrush for comparison. Do NOT average backlink counts — different indexes find different links.
- **Link quality assessment:** Combine Ahrefs DR of referring domain + Semrush Authority Score + spam pattern heuristics (low DR + excessive outlinks, exact-match commercial anchors, 100+ external links per page)

### 3.3 Authority Metrics

Two independent sources:
- **Ahrefs DR** — industry standard, used in all client communications
- **Semrush Authority Score** — cross-validation, incorporates traffic + organic data

### 3.4 Traffic Estimates

- **Own site:** GSC + GA4 only. Never use third-party estimates when real data exists.
- **Competitors:** Present as RANGE [MIN(Ahrefs, Semrush), MAX(Ahrefs, Semrush)], never a single number. All third-party traffic estimates have 22-62% error rates. Always note this.
- **If GSC is available for own site:** Calculate a correction factor (GSC actual ÷ average of third-party estimates) and note it.

### 3.5 Rankings

- **Own site:** GSC actual positions
- **Competitors:** Ahrefs organic-keywords + Semrush validation

### 3.6 Topic Clustering

- **Primary signal:** Ahrefs Keywords Explorer `parent_topic` field — this automatically groups keywords that share the same top-ranking page
- **Expansion:** Ahrefs `related-terms` endpoint ("also rank for" and "also talk about" keywords)
- **SERP overlap validation:** Ahrefs `serp-overview` to check if keywords share top-10 results (SERP overlap = same Topic)

### 3.7 AI Search Visibility

- **Data:** Ahrefs Brand Radar — tracks mentions, impressions, share of voice across: google_ai_overviews, google_ai_mode, chatgpt, gemini, perplexity, copilot
- **Analysis framework:** claude-seo `/seo geo` command
- **No alternative exists at comparable depth.** If Brand Radar is unavailable, skip this section with a note.

### 3.8 Technical Audit

- **Primary crawl:** Ahrefs Site Audit (cloud-based crawler, covers technical issues at scale)
- **Structured analysis:** claude-seo `/seo audit` (6 parallel subagents — technical, content, schema, sitemap, performance, visual)
- **Core Web Vitals:** PageSpeed Insights API (Lighthouse + real Chrome field data)
- **Ground truth:** GSC Coverage report + URL Inspection API (when available)

### 3.9 Search Intent Classification

- **Primary:** Semrush — includes intent data with every keyword pull
- **Supplementary:** Ahrefs organic-keywords response includes intent
- **Categories:** informational, navigational, commercial, transactional

---

## 4. THE WORKFLOW

### 4.1 Concept

Each client audit consists of four Claude Code sessions separated by context clears. The reason for the clears is purely technical — raw API responses for a site with 50,000 keywords would be millions of tokens. Claude Code cannot hold that in context. So each session works from condensed briefing files, not raw data.

Think of sessions as "close your browser tabs, start fresh with a summary of what you found."

### 4.2 Session Flow

```
SESSION 1: GATHER  →  all raw data to disk + claude-seo outputs  →  phase1-briefing.md
     ↓ /clear
SESSION 2: ANALYSE →  clustering, gaps, cross-validation          →  phase2-briefing.md
     ↓ /clear
SESSION 3: STRATEGISE → prioritized recommendations               →  phase3-briefing.md
     ↓ ALEX REVIEWS AND APPROVES
SESSION 4: DELIVER  →  report.docx + dashboard data + CSV exports →  client deliverables
```

### 4.3 Session 1: GATHER (~30 minutes)

**Goal:** Collect all raw data from every source and produce a concise summary of findings.

**What happens:**

1. Run claude-seo commands against the client domain:
   - `/seo audit` — full site audit via 6 parallel subagents
   - `/seo schema` — schema markup detection and validation
   - `/seo geo` — AI search citability analysis
   - `/seo content` — E-E-A-T quality analysis
   - `/seo sitemap` — XML sitemap analysis
   - `/seo hreflang` — only for international/multi-language clients
   - Save each output to disk

2. Pull API data via scripts (all results saved directly to disk, never loaded into context):
   - **Ahrefs:** batch-analysis (client + all competitors in one call, max 100 URLs), organic keywords with parent_topic and traffic_potential, all backlinks + referring domains, Brand Radar data, site audit issues, related-terms ("also rank for" + "also talk about")
   - **Semrush:** keyword overview for validation, organic research for client + competitors, backlink analytics summary, organic competitors discovery (top 10 by keyword overlap)
   - **GSC:** only if access is configured (most new clients won't have it)
   - **PageSpeed Insights:** top 5-10 client pages

3. Run cross-validation on keyword volumes (Semrush vs Ahrefs). Flag any variance above 30%.

4. Generate Phase 1 briefing — a concise document (<2500 words) summarizing everything found. This is the ONLY thing Session 2 needs to read.

5. Clear context.

**The Phase 1 briefing must include:**
- Domain overview: DR, Authority Score, estimated traffic range, keyword count, referring domains, indexed pages
- Competitors snapshot table with same metrics
- Key technical findings (from claude-seo + Ahrefs Site Audit + PageSpeed)
- Key content findings (E-E-A-T assessment, content gaps identified)
- Key backlink findings (referring domains, DR distribution, toxic signals)
- AI search visibility (Brand Radar: mentions, SOV, top citing domains)
- Data quality notes (cross-validation variance, confidence levels, GSC availability)
- Top 20 keywords by traffic potential (with validated volume, KD, position, parent topic, intent)

### 4.4 Session 2: ANALYSE (~30 minutes)

**Goal:** Transform raw data into strategic insights through clustering, gap analysis, competitive benchmarking, and Feed-ready content intelligence.

**Input:** Phase 1 briefing + targeted reads of processed CSVs as needed (never load everything at once).

**What happens:**

1. **Keyword clustering:** Group all keywords by Ahrefs parent_topic. Score each cluster: total traffic potential × number of keywords ÷ average difficulty. Do not preset how many clusters to expect — let the data reveal the natural structure.

2. **Topic extraction within each cluster:** Keywords within a cluster represent different things. Some are variants of the same topic ("gut health test" and "gut microbiome test" share the same SERP results). Others represent genuinely distinct topical angles ("gut health test" vs "leaky gut symptoms"). Collapse keyword variants into distinct Topics using SERP overlap as the signal — keywords whose top-ranking pages overlap significantly are the same Topic. Each Topic gets a descriptive name (a substantive area, not just a keyword string). Additionally, pull Ahrefs related-terms with the "also talk about" view for each cluster. Any entities or concepts that appear in "also talk about" but aren't already covered by an existing Topic become candidate Topics — these are gaps in topical coverage the keyword data alone would miss. Also map content gap results (keywords where competitors rank but client doesn't) into the cluster structure as Topics.

3. **Entity extraction per cluster:** From the "also talk about" data, extract the entity/concept layer for each cluster. These are terms that signal topical depth and comprehensive coverage — not standalone Topics, but vocabulary the content production system should know about and weave across articles in the cluster. Examples: for a "gut health testing" cluster, entities might include "dysbiosis," "short-chain fatty acids," "zonulin," "Bristol stool scale." These go into the Feed as the `entities` field.

4. **Keyword pool curation per cluster:** All validated keywords within the cluster become the shared keyword pool. Each keyword carries: the term, validated monthly volume (cross-validated per Section 9), keyword difficulty, search intent classification, and a role tag — either "primary" (high volume, cluster-defining) or "supporting" (long-tail, niche, supplementary). The keyword pool belongs to the cluster, not to individual Topics. The content production system uses keywords across whichever Topics are most relevant.

5. **Content gap analysis:** Find keywords where competitors rank in top 20 but client doesn't. Map gaps to topic clusters and flag as Topics within those clusters (see step 2).

6. **Backlink gap analysis:** Find domains that link to 2+ competitors but not the client. These have a 20-30% higher outreach success rate. Prioritize by DR and number of competitor connections.

7. **Competitive matrix:** Build comparison across DR, traffic, keywords, content volume, AI visibility for client vs all competitors.

8. **Competitive context per cluster:** For each cluster, identify: which competitor dominates (most keywords, highest traffic), how many articles they have in the cluster, their DR, and how strong their internal linking is within the cluster. This context tells the content production system what it's up against per Feed.

9. **Technical issue prioritization:** Aggregate findings from Ahrefs Site Audit, claude-seo audit, and PageSpeed. Rank by impact × fix complexity.

10. **Quick wins identification:** Find keywords where client ranks positions 8-20 with low KD — these can move to page 1 with minimal effort.

11. Generate Phase 2 briefing (<3000 words) with all analysis results.

12. Clear context.

**The Phase 2 briefing must include:**
- All clusters identified (table: cluster name, topic count, keyword count, total volume, avg KD, traffic potential, existing client content, gap vs competitors)
- Per cluster: list of Topics (name + description), keyword pool summary (count, volume range, primary vs supporting), entity list, competitive context
- Backlink gap summary (total opportunities, avg DR, top 10 targets)
- Competitive position matrix
- Technical priority stack (ranked by impact)
- Quick wins list (positions 8-20, low KD, high volume)
- Key strategic observations (patterns, competitor weaknesses, opportunities)

### 4.5 Session 3: STRATEGISE (~45 minutes)

**Goal:** Turn analysis into a prioritized, phased strategy with Feed-ready output for content production and actionable link building targets.

**Input:** Phase 2 briefing.

**What happens:**

1. Run `/seo plan` (claude-seo strategic planning framework) for scaffolding.

2. **Cluster prioritization:** Score all clusters using KOB (volume × CTR ÷ difficulty) combined with business fit (proximity to money pages / conversion paths) and competitive feasibility (can we realistically compete given client's current DR?). Rank all clusters. Do not preset how many to activate — the phased plan determines that.

3. **Feed Export — Full Cluster Map:** For EVERY viable cluster the data revealed, produce a structured Feed definition:

   ```
   Feed: [Cluster Name]
   ├── Description: What this cluster covers, what authority it builds
   ├── Priority Score: [KOB × business fit × competitive feasibility]
   ├── Topics: [all distinct topical angles identified in Session 2]
   │   ├── Topic name + description (substantive area, not keyword)
   │   ├── Source: keyword_cluster | content_gap | entity_expansion
   │   └── Estimated search demand: high | medium | low
   ├── Keywords: [full validated pool for this cluster]
   │   ├── Term, volume, KD, intent, role (primary | supporting)
   │   └── Cross-validation confidence: high | moderate | low
   ├── Entities: [concepts/terms signaling topical depth]
   ├── Competitive Context:
   │   ├── Dominant competitor + their DR
   │   ├── Competitor article count in this cluster
   │   └── Cluster difficulty assessment: open | contested | dominated
   └── Existing Client Content: [URLs already covering this cluster, if any]
   ```

   This is the complete territory map. It persists between quarterly re-audits and grows over time.

4. **Feed Export — Q1 Activation Plan:** Select the top clusters for immediate activation. Selection criteria:
   - Enough topic depth to sustain the allocated article velocity for 3 months (if allocating 4-5 articles/month to a Feed, it needs at least 12-15 Topics)
   - Competitive feasibility — don't activate a cluster where the dominant competitor has DR 80+ and 50 articles unless the client has a clear angle
   - Business relevance — clusters that connect to money pages and conversion paths get priority
   - Quick win potential — clusters where the client already has some positions 8-20 can compound faster

   For each activated Feed, mark the initial Topics to prioritize (highest demand × weakest competition). The content production system picks from these first, then expands to remaining Topics as the Feed matures.

   Feeds NOT activated in Q1 remain in the Full Cluster Map for future quarters. They are not discarded — they are sequenced.

   **The Q1 Activation Plan also specifies:** article velocity per Feed (how many articles/month allocated), which Topics to prioritize first within each Feed, and the Feed activation sequence (which Feed starts week 1 vs week 3).

5. **Link building target export:** From the backlink gap analysis, produce a structured export:
   - Target domain, DR, number of competitors it links to, specific linking URLs
   - Recommended anchor text (based on gaps in client's current anchor text distribution — target ~60% branded, ~40% diverse across keyword-rich, topical, and naked URL anchors)
   - Suggested acquisition method (guest post, resource page, broken link, digital PR, expert commentary)
   - Contact page URL for each target domain
   - Priority tier: Tier 1 (DR 50+, links to 3+ competitors), Tier 2 (DR 30-50, links to 2+ competitors), Tier 3 (DR 20-30, relevant niche)

   Typical output: 50-200 targets per client, with 20-30 Tier 1 targets. This export updates on every quarterly re-audit as competitors gain new links that create new gap opportunities.

6. **Technical fix roadmap:** Prioritize into immediate (week 1), short-term (month 1), medium-term (month 2-3). Each with specific URLs, exact fix, expected impact.

7. **AI search optimization (GEO) strategy:** Combine Brand Radar data with claude-seo GEO analysis. Define: fact density targets, entity markup priorities, platform-specific tactics, citation-worthy content formats to create.

8. **Phased implementation roadmap:** 
   - **Q1 (months 1-3):** Technical fixes + quick wins + GSC setup. Activate first Feeds. Content production begins on priority Topics within activated Feeds.
   - **Q2 (months 4-6):** Assess Feed performance using GSC data. Expand winning Feeds (add remaining Topics). Activate 1-2 new Feeds. Refresh keyword pools from quarterly re-audit. Begin content decay monitoring (see Section 15).
   - **Q3 (months 7-9):** Focus on cluster completion — deepen existing Feeds to reach topical authority thresholds. Entity coverage becomes more important than keyword coverage. Slower new Feed activation; depth over breadth.
   - **Q4 (months 10-12):** Compounding growth. Full topical authority push in established Feeds. Activate remaining viable Feeds. Advanced link building. AI visibility optimization for high-performing clusters.
   
   Each quarter with estimated traffic impact range.

9. Generate Phase 3 briefing (<3000 words).

10. **STOP. Alex reviews before Session 4.** This is the human checkpoint — does the strategy make business sense for this specific client? Are the right Feeds activated first? Does the phasing make sense? Adjust, add context, override as needed.

11. Clear context.

**The Phase 3 briefing must include:**
- Full Cluster Map summary (all clusters with priority scores)
- Q1 Activation Plan (which Feeds, which Topics first, velocity allocation)
- Link building target summary (counts by tier, top 10 targets)
- Technical fix roadmap
- GEO strategy
- Phased implementation roadmap (Q1-Q4)
- Decisions requiring Alex's input (cluster selection overrides, business fit judgments)

### 4.6 Session 4: DELIVER (~60 minutes)

**Goal:** Produce the final client deliverables.

**Input:** Approved Phase 3 briefing.

**Outputs:**
1. **Strategic audit report** (.docx) — 12 sections, see Section 6 for full spec
2. **Charts** — PNG files embedded in report
3. **Feed Exports** — structured JSON per cluster (Full Cluster Map + Q1 Activation Plan), ready for content production system ingestion
4. **Link Target Export** — structured CSV/JSON of all backlink gap targets with DR, competitor overlap, anchor recommendations, acquisition method, contact URLs
5. **CSV exports** — keyword opportunities, technical fixes, topic clusters
6. **Dashboard data** — push key metrics to Google Sheets for Looker Studio
7. **Complete metadata** — timestamps, sources, confidence levels for everything

---

## 5. DATA MANAGEMENT PRINCIPLES

These are non-negotiable rules. Not suggestions.

### 5.1 Raw Data Is Sacred

Every API response and tool output goes to disk exactly as received. Never modify raw files after writing. Processing scripts read from raw, write to a separate processed location. If something goes wrong, you can always reprocess from raw. This is the audit trail.

### 5.2 Every Data Point Has Provenance

The system must track, for every data source used in the final report: which tool produced it, when it was pulled, what it was validated against, what the cross-validation variance was, and the resulting confidence level (high/moderate/low).

### 5.3 One Client = One Folder = One Truth

Never mix client data. Never share processed files between clients. Each audit gets its own timestamped folder. Previous audits remain for historical comparison.

### 5.4 Briefings Are the Only Bridge Between Sessions

Claude Code never carries context from Session 1 to Session 2. The briefing file IS the interface. If it's not in the briefing, it doesn't exist for the next session. This is what prevents context overload.

### 5.5 Validation Before Every Phase Transition

Before each session begins, verify: all expected data files present, record counts above minimum thresholds, cross-validation variance within acceptable range, no stale cached data used, previous phase briefing exists and is within word limit. If any check fails, the session doesn't proceed.

### 5.6 Caching

To avoid burning API credits on repeated pulls:
- Domain metrics (DR, AS): cache for 14 days
- Keyword volumes: cache for 30 days
- SERP rankings: cache for 1-3 days
- Backlink profiles: cache for 7 days
- GSC data: cache until new data arrives (2-3 day Google processing lag)
- Brand Radar: cache for 14 days
- PageSpeed/CWV: cache for 7 days

Always log whether data came from cache or fresh pull.

---

## 6. REPORT SPECIFICATION — 12 SECTIONS

The strategic audit report is the primary client deliverable. Generated as .docx.

### Cover Page
Client logo (if provided) + Authoricy logo. Title: "SEO Audit & Strategy Report." Client name, domain, date. "Prepared by Authoricy AB."

### Table of Contents
Auto-generated from headings.

### Section I: Executive Summary (1-2 pages)
SEO Health Score (0-100, weighted composite). Top 3-5 findings stated in plain business language (not SEO jargon). Competitive positioning summary. 90-day priority actions (max 5). Estimated impact of full strategy implementation stated as a traffic range, not false precision.

### Section II: Current State Analysis (2-3 pages)
Organic traffic trend (12-month chart from GSC if available, else Ahrefs estimated). Keyword visibility breakdown by position bucket (1-3, 4-10, 11-20, 21-50, 51-100). Top 10 pages by traffic with primary keywords. Brand vs non-brand split if GSC available. All estimates clearly labeled with confidence levels.

### Section III: Technical SEO Audit (2-4 pages)
Core Web Vitals with pass/fail (LCP < 2.5s, INP < 200ms, CLS < 0.1). Crawlability (robots.txt, sitemap, redirects, orphan pages). Indexation status. Mobile usability. URL architecture. Internal linking structure. Schema markup status. JS rendering issues. Security (HTTPS, mixed content). Source attribution stating which tools contributed findings.

### Section IV: Keyword Research & Opportunity Analysis (3-4 pages)
Current keyword portfolio overview. Cross-validated top keywords table. Quick wins (positions 8-20, low KD). KOB analysis (Keyword Opposition to Benefit: volume × CTR estimate ÷ difficulty). Search intent distribution. Source attribution noting cross-validation between Semrush and Ahrefs.

### Section V: Topical Map & Feed Architecture (3-5 pages)
Visual cluster map showing Feed → Topic relationships. For each cluster: Feed name and description, total topic count and keyword pool size, priority score (KOB × business fit × competitive feasibility), competitive context (dominant competitor, their article count, difficulty assessment), activation status (Q1 active, Q2 planned, backlog). For Q1-activated Feeds: the initial priority Topics, keyword pool highlights (top 10 by volume), entity coverage requirements, and estimated content velocity allocation. Internal linking strategy between Feeds (how clusters connect to each other and to money pages). Source: Ahrefs parent_topic clustering with SERP overlap validation, related-terms "also talk about" for entities.

### Section VI: Content Strategy & Feed Activation Plan (2-3 pages)
Content gap analysis summary. E-E-A-T assessment from claude-seo. Phased Feed activation plan: Q1 Feeds with rationale for selection, velocity allocation per Feed, initial Topic priorities within each Feed, and criteria for Q2 expansion decisions (what GSC data needs to show before adding Topics or activating new Feeds). Content production integration: how Feeds, Topics, keywords, and entities flow into the content production system. Format recommendations per cluster (driven by search intent distribution within the cluster).

### Section VII: Backlink Profile & Link Strategy (2-3 pages)
Current profile: referring domains, DR distribution, anchor text breakdown. Toxic/spam assessment. Anchor text distribution analysis (target: ~60% branded, ~40% diverse). Link gap: domains linking to competitors but not client. Top 20-30 prioritized targets with DR and recommended acquisition method. Broken backlink recovery opportunities. Monthly link building targets. Source: Ahrefs primary, Semrush validation.

### Section VIII: SERP Features & AI Search / GEO (2-3 pages)
SERP feature ownership (featured snippets, PAA, knowledge panels). Featured snippet optimization opportunities. AI Search section: Brand Radar data (mentions, impressions, SOV across platforms), which platforms mention client vs competitors, what questions trigger mentions, which pages get cited. GEO strategy: fact density recommendations (every 150-200 words), entity markup priorities, platform-specific tactics, citation-worthy content formats. Source: Ahrefs Brand Radar + claude-seo GEO analysis.

### Section IX: Local SEO (1-2 pages, if applicable)
Google Business Profile audit. Local citations. Reviews. Local keywords. NAP consistency. **Skip entirely for B2B clients with no physical customer-facing locations.**

### Section X: Competitive Intelligence (2-3 pages)
Competitive matrix table (DR, traffic range, keywords, content volume, AI visibility). Per-competitor paragraph: strengths, weaknesses, strategy observations. Content comparison by topic. Backlink comparison: velocity, top sources. AI visibility comparison. All metrics include confidence indicators.

### Section XI: Implementation Roadmap (2-3 pages)
Four quarters, built around the phased Feed activation model:
- **Q1:** Technical fixes + quick wins + GSC setup. Activate first 3-4 Feeds. Content production begins on priority Topics within each Feed. Link building launches with Tier 1 targets. Baseline metrics established.
- **Q2:** Quarterly re-audit refreshes keyword data. Assess Feed performance using GSC data (which Feeds drive impressions/clicks, which Topics perform). Expand winning Feeds with additional Topics. Activate 1-2 new Feeds. Begin content decay monitoring. Refresh link target export.
- **Q3:** Focus shifts to cluster depth — fill remaining Topics in high-performing Feeds to reach topical authority thresholds. Entity coverage becomes priority. Slower new Feed activation; comprehensive coverage matters more than breadth. GEO optimization for top-performing clusters.
- **Q4:** Compounding growth. Activate remaining viable Feeds. Full topical authority push in established clusters. Advanced link building. AI visibility optimization across all active Feeds.
Each quarter with estimated traffic impact range and Feed-level performance targets.

### Section XII: Appendices
References to CSV exports (keyword opportunities, technical fixes, backlink targets). Data provenance table: for every section, which tools contributed, when data was pulled, confidence level.

### Every section footer must include:
Data sources used, date pulled, confidence level.

---

## 7. DASHBOARD SPECIFICATION

### 7.1 Architecture

GSC and GA4 connect directly to Looker Studio via native connectors (free, auto-refreshing). Ahrefs and Semrush data reaches Looker Studio through Google Sheets as a bridge — a monthly script pushes key metrics to Sheets, Looker reads from Sheets.

### 7.2 Google Sheets Structure (one workbook per client)

Tabs needed:
- **overview** — DR, AS, organic traffic estimate, keyword count, referring domains (monthly update from Ahrefs batch-analysis)
- **keywords** — top 50 tracked keywords with position, volume, URL, change (monthly from Ahrefs organic-keywords)
- **backlinks** — new/lost referring domains, DR distribution summary (monthly from Ahrefs referring-domains)
- **competitors** — competitor DR, traffic, keywords, referring domains (monthly from Ahrefs batch-analysis)
- **technical** — CWV scores, crawl errors, indexation status (monthly from PSI + GSC)
- **ai-visibility** — Brand Radar mentions, impressions, SOV per platform (monthly from Ahrefs Brand Radar)
- **content** — top 20 pages with traffic, keywords, position changes (monthly from Ahrefs top-pages)
- **feeds** — per Feed: name, status (active/planned/backlog), topic count, topics published, keyword pool size, total impressions, total clicks, avg position across cluster keywords (monthly from GSC + Ahrefs)
- **content-health** — published URL watchlist with current position, traffic, 3-month trailing average, decay flag (see Section 15)

### 7.3 Looker Studio Dashboard Pages

**Page 1: Executive Overview** — Scorecard row (DR, traffic, keywords, referring domains), traffic trend line (GSC 12 months), MoM change indicators, top 5 pages.

**Page 2: Keyword Performance** — Rankings distribution bar chart by position bucket, top keywords table with change, new gained / lost.

**Page 3: Content Performance** — Top pages by organic traffic (GSC), engagement metrics (GA4), content plan coverage progress.

**Page 4: Feed Performance** — Per-Feed view: topics published vs total topics (cluster completion %), total impressions and clicks from Feed keywords (GSC), average position trend across Feed keywords, Feed-level traffic growth. This is the primary view for assessing which Feeds to expand.

**Page 5: Content Health** — Decay detection dashboard: articles flagged for refresh (position drop ≥3 or clicks drop ≥20% from 3-month average), articles by health status (growing / stable / declining), refresh queue with priority ranking.

**Page 6: Backlink Health** — Referring domains trend, new vs lost per month, DR distribution of linking domains.

**Page 7: Technical Health** — CWV gauges (green/yellow/red), indexation chart, crawl errors trend.

**Page 8: AI Visibility** — SOV comparison bar chart (client vs competitors), mentions trend by platform, top cited pages.

**Page 9: Competitive Snapshot** — Competitor comparison table, radar chart across 5 key metrics.

### 7.4 Setup Per Client

~30 minutes: clone master template sheet, clone master Looker Studio dashboard, connect GSC + GA4, point to client's Google Sheet, customize branding.

~15 minutes per month: run update script, spot-check data.

---

## 8. claude-seo INTEGRATION

### 8.1 What It Is

claude-seo is a set of 12 slash commands that install into Claude Code as skill files. It provides structured SEO analysis frameworks with curated reference data (CWV thresholds, E-E-A-T criteria, schema types, etc.). It does NOT call APIs itself — it analyzes based on what it can access and the frameworks it has.

### 8.2 Installation

```bash
curl -fsSL https://raw.githubusercontent.com/AgriciDaniel/claude-seo/main/install.sh | bash
```

### 8.3 Where Each Command Fits

**Session 1 (Gather) — run these against client domain, save outputs to disk:**
- `/seo audit` — full site audit via 6 parallel subagents (technical, content, schema, sitemap, performance, visual)
- `/seo schema` — schema detection, validation, JSON-LD generation
- `/seo geo` — AI search citability analysis (GEO framework)
- `/seo content` — E-E-A-T quality analysis (Dec 2025 core update criteria)
- `/seo sitemap` — XML sitemap analysis
- `/seo images` — image optimization analysis
- `/seo hreflang` — only for multi-language clients

**Session 3 (Strategise) — use for strategic planning:**
- `/seo plan` — strategic planning framework scaffolding
- `/seo competitor-pages` — competitor content comparison

**Ad-hoc (not part of standard audit):**
- `/seo page {url}` — single page deep analysis, use for pre-publish content checks
- `/seo programmatic` — programmatic SEO guidance when scaling content

### 8.4 What claude-seo Does NOT Do

It does not call APIs, cross-validate data, generate reports, track AI visibility, manage client data, or push to dashboards. Those capabilities must be built separately. claude-seo is a task-level accelerator inside sessions, not the workflow itself.

### 8.5 How Its Outputs Feed Into the System

claude-seo audit findings get merged with Ahrefs Site Audit + PageSpeed data during technical issue aggregation in Session 2. claude-seo GEO output gets combined with Brand Radar data during strategy development in Session 3. Both feed into the final report.

---

## 9. CROSS-VALIDATION METHODOLOGY

### 9.1 Keyword Volumes

Pull volumes from Semrush and Ahrefs. Compare variance. If variance < 30%: high confidence, use Semrush as the reported number. If variance 30-50%: moderate confidence, flag in metadata, present both numbers, use Semrush as primary. If variance > 50%: low confidence, investigate manually, note in report.

When GSC is available for own site, use actual impressions as ground truth and calculate per-tool correction factors.

When GSC is available for own site, use actual impressions as ground truth and calculate per-tool correction factors.

### 9.2 Backlinks

Do NOT average backlink counts across tools — different indexes genuinely find different links. Report Ahrefs count as primary (largest, freshest index). Note Semrush count for comparison. For link quality scoring, combine: Ahrefs DR of referring domain, Semrush Authority Score, and spam pattern detection (low DR + excessive outlinks, exact-match commercial anchors, pages with 100+ external links).

### 9.3 Traffic Estimates

For competitors, always present as a range [MIN, MAX] across tools. Never present a single traffic number for a competitor — the error rates are too high (22-62%). Always caveat third-party traffic estimates in the report.

---

## 10. ERROR HANDLING PRINCIPLES

### 10.1 API Failures

Retry with exponential backoff (max 5 attempts). If a tool is completely unavailable, fall back:
- Backlinks: Ahrefs → Semrush → note gap
- Keyword volumes: Semrush → Ahrefs → note gap
- Domain authority: Ahrefs DR → Semrush AS → note gap
- Technical audit: Ahrefs Site Audit → claude-seo → note limitations
- AI visibility: Ahrefs Brand Radar → nothing (skip section with note)
- Core Web Vitals: PageSpeed Insights → note gap

### 10.2 Data Quality Issues

If cross-validation shows > 3x difference in any metric between Ahrefs and Semrush, present both numbers with explicit caveat — do not pick one silently. If GSC shows a manual action, escalate to Alex immediately — this changes the entire strategy.

### 10.3 Session Recovery

All raw data lives on disk. If Claude Code crashes mid-session, check which files exist, determine where processing stopped, and resume from there. Scripts should be idempotent — safe to re-run.

---

## 11. GSC ONBOARDING

60-80% of target clients have no GSC. This does NOT block the audit — Sessions 1-4 work fully on Ahrefs and Semrush data plus claude-seo and PageSpeed analysis. GSC setup is a parallel onboarding task (15-30 min, HTML meta tag or DNS verification). GSC becomes critical from month 2 onward for three irreplaceable things: actual click/impression data, real long-tail query data that third-party databases miss, and manual action / penalty detection.

---

## 12. QUALITY GATES

### Before Session 2
Phase 1 briefing exists and is within word limit. All expected raw data files are present. Both keyword sources (Semrush + Ahrefs) returned data. At least 1 backlink source returned data. Cross-validation has run. No raw files are empty.

### Before Session 3
Phase 2 briefing exists. Keyword clustering produced 3+ clusters. Content gap, backlink gap, and technical issues files exist with data. Competitors matrix exists.

### Before Session 4
Phase 3 briefing exists. Strategy has been marked as approved by Alex. Strategy contains: topic clusters, content plan, link targets, technical roadmap. Charts generated successfully.

### After Session 4
Report .docx exists and is reasonable size. All CSV exports present. Metadata is complete with timestamps and provenance for everything. Dashboard data pushed to Sheets.

### Report Quality
No placeholder text ({, TODO, TBD). All charts embedded. Data provenance footer on every section. Same metric shows same value throughout. Confidence flags on any moderate/low data. Correct client name everywhere. Current date.

---

## 13. SCALING

### Per-Client Onboarding
Create client config (domain, competitors, country). Run Ahrefs batch-analysis for domain validation. Request GSC + GA4 access. Create Google Sheet from template. Clone Looker Studio dashboard. Schedule initial audit.

### Monthly Maintenance (~20 min per client)
Run dashboard update script. Run content decay detection (see Section 15). Update Feed tracking (topics published, cluster completion). Quick dashboard review for anomalies. Check GSC for manual actions.

### Quarterly Re-Audit
Re-run the full 4-session workflow with two additional inputs: (1) GSC performance data per Feed for the last quarter, (2) the current Feed activation status (what's active, what's been published). The quarterly re-audit updates: keyword pools per Feed (new terms, volume changes), cluster priority scores (based on actual performance, not just estimates), Topic lists (new content gaps from competitor movements), link target export (new competitor links = new gap opportunities), and produces the next quarter's Feed Activation Plan. Each audit lives in its own timestamped folder. Previous Feed Exports persist — they are updated, not replaced.

---

## 14. IMPLEMENTATION ORDER

Build in this order. Test each step before proceeding.

**Phase A: Foundation (Day 1-2)**
1. Create project directory structure
2. Write CLAUDE.md pointing to this spec
3. Create config files and templates
4. Install claude-seo skill
5. Verify all MCP connections work

**Phase B: Data Gathering (Day 3-5)**
6. Build data-pulling capability for each tool (Ahrefs, Semrush, GSC, PageSpeed)
7. Build caching layer
8. Test against a real domain

**Phase C: Processing & Analysis (Day 6-9)**
9. Build cross-validation
10. Build keyword clustering (using Ahrefs parent_topic)
11. Build topic extraction within clusters (SERP overlap deduplication, "also talk about" entity extraction)
12. Build keyword pool curation per cluster (validation, role tagging primary/supporting)
13. Build backlink gap analysis
14. Build content gap analysis (mapping gaps to clusters as Topics)
15. Build technical issue aggregation and prioritization
16. Build briefing generation for all 3 phases

**Phase D: Feed Export & Validation (Day 10-12)**
17. Build Feed Export generator (JSON per cluster: Topics, Keywords, Entities, Competitive Context)
18. Build Q1 Activation Plan logic (cluster prioritization, velocity allocation, Topic sequencing)
19. Build link target export (backlink gap targets with DR, anchor recommendations, acquisition method)
20. Build quality gate checks
21. Build chart generation
22. Build CSV exports
23. Build Google Sheets push (including feeds and content-health tabs)

**Phase E: Report Generation (Day 13-15)**
24. Build .docx report generator with all 12 sections
25. Test full report with real data
26. Validate output opens correctly in Word / Google Docs

**Phase F: Dashboard (Day 16-17)**
27. Create Looker Studio master template (9 pages including Feed Performance and Content Health)
28. Connect test data
29. Verify auto-refresh

**Phase G: End-to-End Test (Day 18-19)**
30. Run complete 4-session workflow on authoricy.com
31. Time each session
32. Validate Feed Exports are correctly structured and contain all required fields
33. Review quality, fix issues
34. Run on a second domain to verify portability

**Phase H: First Client (Day 20+)**
35. Onboard first paying client
36. Run full audit, deliver report + dashboard + Feed Exports
37. Document workflow adjustments
38. Update this spec if needed

**Phase I: Content Decay (after content is live + 3 months GSC data)**
39. Build content decay detection script
40. Build content-health tab updater
41. Build Content Health dashboard page
42. Test with real published URLs
43. Integrate into monthly maintenance cycle

---

## 15. CONTENT DECAY MONITORING

### 14.1 When It Starts

Not before month 4. Content decay monitoring requires: (a) published content that has had time to index and establish baseline performance (minimum 8-12 weeks), and (b) GSC data flowing for the client domain. Do not build or run this before content is live and GSC has at least 3 months of data for the published URLs.

### 14.2 How It Works

The decay detection script runs as part of the monthly maintenance cycle. It operates on a watchlist of published URLs (maintained in the Google Sheets `content-health` tab).

For each URL on the watchlist, pull:
- Current average position for its target keywords (Ahrefs organic-keywords, filtered to the URL)
- Current monthly clicks and impressions (GSC, filtered to the URL)
- 3-month trailing average for position, clicks, and impressions (from stored historical data in the `content-health` tab)

Flag the URL for refresh if ANY of these conditions are met:
- Average position drops by 3+ spots from the 3-month trailing average
- Monthly clicks drop by 20%+ from the 3-month trailing average
- Monthly impressions drop by 30%+ from the 3-month trailing average (impressions drop faster than clicks when rankings slip)

### 14.3 Output

A prioritized refresh queue, written to the `content-health` tab and visible on the Content Health dashboard page. Each flagged URL includes: the URL, its Feed (cluster), the specific decay signal (position drop / click drop / impression drop), magnitude of change, current vs trailing average metrics, and a suggested action:
- **Refresh:** Update content with new data, expand thin sections, add recent developments. Triggered by moderate position decay (3-5 spots).
- **Expand:** Substantially expand the article to cover more of the topic, add entities, improve depth. Triggered by being outranked by significantly longer/deeper competitor content.
- **Consolidate:** Merge with another underperforming article in the same Feed if both are thin and competing with each other (keyword cannibalization). Triggered by two URLs in the same cluster targeting overlapping keywords where neither performs well.

### 14.4 Feeding Back Into Content Production

Flagged URLs become refresh tasks in their respective Feeds. The content production system should treat a refresh task as a Topic — it has the same keyword pool access, the same entity context, but the instruction is "improve this existing article" rather than "write a new article on this topic." Refresh tasks should be interleaved with new Topics, not queued separately. A Feed producing 4-5 articles/month might allocate 1 refresh and 3-4 new Topics.

### 14.5 Implementation Complexity

Low. This is a Python script that runs alongside the existing monthly data push. It reads the URL watchlist, pulls current GSC + Ahrefs data, compares against stored history, and outputs the flagged list. The comparison logic is simple arithmetic. The hardest part is maintaining the watchlist — every URL published by the content production system needs to be added. This should be part of the publishing workflow, not a manual step.

Build this in Phase G of implementation (after the core system works end-to-end and content is actually being published).

---

## 16. GLOSSARY

| Term | Definition |
|------|-----------|
| **Feed** | A topic cluster packaged for the content production system. Contains Topics, Keywords, and Entities. One Feed = one area of topical authority to build. |
| **Topic** | A distinct substantive area within a Feed. Each Topic represents one article's worth of content. The content production system selects which Topic to produce next based on relevance and timing. |
| **Keyword Pool** | The shared set of validated search terms for an entire Feed. Keywords are used across Topics based on natural relevance, not assigned per-article. |
| **Entity** | A concept or term that signals topical depth within a Feed. Not a standalone keyword target, but vocabulary that comprehensive coverage requires. From Ahrefs "also talk about" data. |
| **Feed Export** | The structured output (JSON) per cluster that the content production system ingests. Contains: Feed definition, Topics, Keyword Pool, Entities, Competitive Context. |
| **DR** | Domain Rating (Ahrefs) — 0-100 score of backlink profile strength. Industry standard. |
| **AS** | Authority Score (Semrush) — 0-100 composite of backlinks, traffic, organic data. |
| **KD** | Keyword Difficulty — how hard to rank in top 10 |
| **SERP** | Search Engine Results Page |
| **GEO** | Generative Engine Optimization — optimizing for AI search (ChatGPT, Perplexity, etc.) |
| **E-E-A-T** | Experience, Expertise, Authoritativeness, Trustworthiness — Google's quality framework |
| **Parent Topic** | Ahrefs concept — the broader topic a keyword's #1 ranking page targets. Used as the primary clustering signal for Feed identification. |
| **Traffic Potential** | Ahrefs metric — total organic traffic the #1 page gets from ALL its ranked keywords |
| **PKD** | Personal Keyword Difficulty (Semrush) — KD customized for your specific domain |
| **Brand Radar** | Ahrefs module tracking brand mentions across 6 AI platforms |
| **SOV** | Share of Voice — percentage of total AI mentions referencing your brand |
| **MCP** | Model Context Protocol — Anthropic's standard for connecting AI to external tools |
| **ICE** | Impact × Confidence × Ease — prioritization framework |
| **KOB** | Keyword Opposition to Benefit — volume × CTR ÷ difficulty |
| **CWV** | Core Web Vitals — LCP, INP, CLS |
| **LCP** | Largest Contentful Paint — target < 2.5 seconds |
| **INP** | Interaction to Next Paint — target < 200ms |
| **CLS** | Cumulative Layout Shift — target < 0.1 |
| **Content Decay** | The gradual decline in an article's rankings and traffic over time without updates. Detected by comparing current metrics against trailing 3-month averages. |

---

*End of specification. This document is the source of truth. Claude Code: build what's described here. How you build it is your domain.*

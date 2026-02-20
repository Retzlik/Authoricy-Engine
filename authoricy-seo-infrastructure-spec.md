# Authoricy SEO Infrastructure Specification
## Source of Truth — v1.0

> **Purpose:** This document is the complete specification for building Authoricy's automated SEO analysis and deliverable system. Claude Code should treat this as the project constitution. Every script, workflow, and output described here must be implemented exactly as specified unless a specific deviation is justified and documented.

> **Owner:** Alex / Authoricy AB
> **Last Updated:** 2026-02-20
> **Status:** Approved for implementation

---

## 1. MISSION

Build a multi-source SEO analysis system operated through Claude Code that takes a client domain + competitors as input and produces:

1. A comprehensive strategic audit report (.docx, 12 sections)
2. A live performance dashboard (Looker Studio)
3. Ongoing monthly monitoring data

For B2B clients in the €2M-50M revenue range who are digitally under-invested. These clients typically have no GSC configured, minimal existing SEO work, and need someone to build their entire organic strategy from scratch.

**Target delivery time:** 2.5-4 hours per client audit (after system is built and tested).

---

## 2. TOOL STACK

### 2.1 Data Sources (APIs via MCP)

| Tool | Access Method | Primary Role | Database Size | Cost Model |
|------|--------------|-------------|---------------|------------|
| **Ahrefs** | MCP connector in Claude.ai / Claude Code | Backlinks (best index), Domain Rating, Parent Topic clustering, Brand Radar AI visibility, Content Explorer, Site Audit | 35T external backlinks, 210M domains | Credits from existing subscription (~$129-249/mo) |
| **Semrush** | MCP connector in Claude.ai / Claude Code | Keyword volume validation (most accurate, 0% GKP mismatch), Personal Keyword Difficulty, Topical Authority, Traffic Analytics | 26.7B keywords, 808M domains, 43T backlinks | API units from existing subscription (~$140-250/mo) |
| **DataForSEO** | MCP connector in Claude Code | Real-time SERP scraping, bulk keyword operations, On-Page/Lighthouse, search intent classification, cross-validation tiebreaker | 7B+ keywords, 2.8T live backlinks | Pay-as-you-go (~$50-150/mo) |
| **Google Search Console** | Native API + Looker Studio connector | Ground truth: actual clicks, impressions, queries, indexation, manual actions | N/A — real Google data | Free |
| **Google PageSpeed Insights** | REST API (free, 25K queries/day) | Core Web Vitals field data, Lighthouse scores | N/A | Free |

### 2.2 Analysis Tools (Local)

| Tool | Role | Access |
|------|------|--------|
| **Screaming Frog SEO Spider** (paid) | Deep technical crawls, JS rendering, structured data validation, internal link mapping, redirect chains, orphan page detection | CLI/headless, €235/year |
| **Screaming Frog Log Analyser** (paid) | Googlebot crawl budget analysis from server logs | Desktop app, €115/year |
| **claude-seo skill** | 12 slash commands for structured SEO analysis — audit orchestration with 6 parallel subagents, E-E-A-T framework (Dec 2025 update), schema generation (12+ types), GEO/AI search optimization, sitemap analysis, hreflang validation, strategic planning frameworks | Free (MIT), installed at `~/.claude/skills/seo/` |
| **Gephi** | Site architecture visualization from Screaming Frog crawl exports | Free, open-source |
| **Google Rich Results Test + Schema Validator** | Structured data validation | Free web tools |

### 2.3 Output & Reporting Tools

| Tool | Role | Cost |
|------|------|------|
| **Looker Studio** | Live client dashboards (auto-updating) | Free |
| **Google Sheets** | Data bridge between APIs and Looker Studio | Free |
| **docx-js** (via Claude Code) | Strategic report generation (.docx) | Free |
| **matplotlib / plotly** (Python) | Chart generation for reports (PNG export) | Free |

### 2.4 Authority Metrics (Three Independent Sources)

| Metric | Provider | Scale | Use |
|--------|----------|-------|-----|
| Domain Rating (DR) | Ahrefs | 0-100 | Industry standard, used in client communications |
| Authority Score | Semrush | 0-100 | Cross-validation, incorporates traffic + link data |
| Domain Authority (DA) | Moz API | 0-100 | Third-party validation, spam score |

### 2.5 Tool Selection Rules

These rules determine WHICH tool to use for WHICH data point. Claude Code must follow these — do not use an inferior source when a better one is available.

**Keyword volumes (for deliverables):**
- Primary: Semrush (0% GKP mismatch — most accurate)
- Validation: DataForSEO (clickstream-refined)
- Tiebreaker: Ahrefs
- Ground truth (own site only): GSC actual impressions

**Backlink analysis:**
- Primary: Ahrefs (largest live index, 15-30 min freshness, best link type diversity)
- Validation: Semrush (larger total index including dead links, Authority Score)
- Link quality scoring: Ahrefs DR + Moz DA + Moz Spam Score combined
- Ground truth (own site only): GSC Links report

**Traffic estimates (competitors):**
- Present as RANGES, never single numbers: [MIN(all tools), MAX(all tools)]
- Note: All third-party traffic estimates have 22-62% error rates

**Traffic data (own site):**
- Only source: GSC + GA4 (actual data)
- Never use Ahrefs/Semrush estimated traffic for own site when GSC is available

**Rankings:**
- Own site: GSC (actual positions)
- Competitors: Ahrefs organic-keywords + Semrush validation
- Real-time spot checks: DataForSEO SERP API (live scrape)

**Topic clustering:**
- Primary: Ahrefs Keywords Explorer `parent_topic` field
- Expansion: Ahrefs `related-terms` endpoint ("also rank for" keywords)
- SERP overlap validation: DataForSEO (check if keywords share top-10 results)

**AI search visibility:**
- Primary: Ahrefs Brand Radar (tracks 6 platforms: google_ai_overviews, google_ai_mode, chatgpt, gemini, perplexity, copilot)
- Analysis framework: claude-seo `/seo geo` command
- No alternative source exists at comparable depth

**Technical audit:**
- Primary: Screaming Frog crawl (most comprehensive, JS rendering)
- Supplementary: Ahrefs Site Audit (cloud-based, different crawler perspective)
- Supplementary: claude-seo `/seo audit` (parallel subagent analysis)
- Core Web Vitals: PageSpeed Insights API (Lighthouse + field data)
- Ground truth: GSC Coverage report + URL Inspection API

**Search intent:**
- Primary: Ahrefs (classified per keyword in organic-keywords response)
- Bulk classification: DataForSEO Search Intent endpoint (up to 1000 keywords per call, cheapest)
- Categories: informational, navigational, commercial, transactional

---

## 3. PROJECT STRUCTURE

```
authoricy-seo/
│
├── CLAUDE.md                              # Points to this document as source of truth
│
├── config/
│   ├── tools.json                         # API credentials, endpoints, rate limits
│   ├── defaults.json                      # Default parameters (country, language, limits)
│   └── clients/
│       └── {client-slug}.json             # Per-client config
│
├── scripts/
│   ├── gather/
│   │   ├── ahrefs_pull.py                 # Ahrefs MCP data extraction
│   │   ├── semrush_pull.py                # Semrush MCP data extraction
│   │   ├── dataforseo_pull.py             # DataForSEO MCP data extraction
│   │   ├── gsc_pull.py                    # Google Search Console API
│   │   └── psi_pull.py                    # PageSpeed Insights API (batch)
│   ├── process/
│   │   ├── cross_validate.py              # Weighting formulas, variance detection
│   │   ├── keyword_cluster.py             # Groups by Ahrefs parent_topic
│   │   ├── backlink_gap.py                # Domains linking to 2+ competitors but not client
│   │   ├── content_gap.py                 # Keywords competitors rank for, client doesn't
│   │   ├── technical_aggregate.py         # Combines SF + Ahrefs + claude-seo audit findings
│   │   └── generate_briefing.py           # Creates phase briefing files from processed data
│   ├── export/
│   │   ├── to_sheets.py                   # Monthly metrics push to Google Sheets
│   │   ├── to_csv.py                      # Client-facing data exports
│   │   └── charts.py                      # PNG chart generation for reports
│   ├── report/
│   │   └── generate_report.js             # docx-js report builder
│   └── validate/
│       └── data_check.py                  # Pre-phase validation gates
│
├── clients/
│   └── {client-slug}/
│       ├── config.json                    # → symlink or copy from config/clients/
│       ├── audit-{YYYY-MM-DD}/
│       │   ├── data/
│       │   │   ├── raw/                   # SACRED — never modify after writing
│       │   │   │   ├── ahrefs/
│       │   │   │   │   ├── batch-analysis.json
│       │   │   │   │   ├── organic-keywords.json
│       │   │   │   │   ├── all-backlinks.json
│       │   │   │   │   ├── referring-domains.json
│       │   │   │   │   ├── brand-radar.json
│       │   │   │   │   └── site-audit.json
│       │   │   │   ├── semrush/
│       │   │   │   │   ├── keyword-overview.json
│       │   │   │   │   ├── organic-research.json
│       │   │   │   │   └── backlink-analytics.json
│       │   │   │   ├── dataforseo/
│       │   │   │   │   ├── serp-results.json
│       │   │   │   │   ├── keyword-data.json
│       │   │   │   │   └── onpage-audit.json
│       │   │   │   ├── gsc/
│       │   │   │   │   ├── search-analytics.json
│       │   │   │   │   └── coverage.json
│       │   │   │   ├── claude-seo/
│       │   │   │   │   ├── audit-output.md
│       │   │   │   │   ├── schema-output.md
│       │   │   │   │   ├── geo-output.md
│       │   │   │   │   ├── content-eeat-output.md
│       │   │   │   │   └── technical-output.md
│       │   │   │   └── screaming-frog/
│       │   │   │       ├── internal-all.csv
│       │   │   │       ├── response-codes.csv
│       │   │   │       └── structured-data.csv
│       │   │   ├── processed/
│       │   │   │   ├── keywords-validated.csv
│       │   │   │   ├── keywords-clustered.csv
│       │   │   │   ├── backlinks-validated.csv
│       │   │   │   ├── backlink-gap.csv
│       │   │   │   ├── content-gap.csv
│       │   │   │   ├── competitors-matrix.csv
│       │   │   │   ├── technical-issues-prioritized.csv
│       │   │   │   └── ai-visibility-summary.csv
│       │   │   └── briefings/
│       │   │       ├── phase1-briefing.md
│       │   │       ├── phase2-briefing.md
│       │   │       └── phase3-briefing.md
│       │   ├── reports/
│       │   │   ├── audit-report.docx
│       │   │   ├── charts/
│       │   │   │   ├── traffic-trend.png
│       │   │   │   ├── keyword-distribution.png
│       │   │   │   ├── backlink-growth.png
│       │   │   │   └── competitive-matrix.png
│       │   │   └── exports/
│       │   │       ├── keyword-opportunities.csv
│       │   │       ├── backlink-targets.csv
│       │   │       └── technical-fixes.csv
│       │   └── metadata.json              # Data provenance, timestamps, confidence scores
│       │
│       └── dashboard/
│           ├── sheets-config.json         # Google Sheets ID, tab mapping
│           └── update-log.json            # When dashboard data was last pushed
│
├── templates/
│   ├── briefing-phase1.md                 # Template for Phase 1 briefing
│   ├── briefing-phase2.md                 # Template for Phase 2 briefing
│   ├── briefing-phase3.md                 # Template for Phase 3 briefing
│   ├── report-template.js                 # docx-js report structure
│   ├── client-config-template.json        # New client config starter
│   └── looker-studio-setup.md             # Dashboard setup instructions
│
└── cache/
    └── {domain}/
        └── {tool}/
            └── {datatype}_{YYYY-MM-DD}.json
```

---

## 4. CONFIGURATION SCHEMAS

### 4.1 Client Configuration (`config/clients/{client-slug}.json`)

```json
{
  "client_name": "Example Corp",
  "slug": "example-corp",
  "domain": "example.com",
  "primary_country": "se",
  "primary_language": "sv",
  "additional_markets": [
    {"country": "gb", "language": "en"},
    {"country": "de", "language": "de"}
  ],
  "competitors": [
    "competitor-one.com",
    "competitor-two.com",
    "competitor-three.com"
  ],
  "brand_terms": ["example corp", "examplecorp", "example"],
  "gsc_property": "sc-domain:example.com",
  "gsc_access": false,
  "ga4_property_id": null,
  "industry": "industrial-manufacturing",
  "business_model": "b2b",
  "revenue_range": "5m-20m-eur",
  "notes": "No existing SEO work. Website is 5 years old, WordPress CMS.",
  "dashboard": {
    "google_sheet_id": null,
    "looker_studio_url": null
  }
}
```

### 4.2 Default Parameters (`config/defaults.json`)

```json
{
  "ahrefs": {
    "mode": "subdomains",
    "protocol": "both",
    "limit_organic_keywords": 10000,
    "limit_backlinks": 5000,
    "limit_referring_domains": 1000,
    "batch_analysis_max": 100
  },
  "semrush": {
    "database": "se",
    "display_limit": 5000,
    "export_columns": "Ph,Nq,Cp,Co,Nr,Td,Kd"
  },
  "dataforseo": {
    "priority": "normal",
    "serp_depth": 100,
    "max_serp_pages": 1,
    "language_code": "sv",
    "location_code": 2752
  },
  "processing": {
    "keyword_volume_weights": {
      "semrush": 0.45,
      "dataforseo": 0.30,
      "ahrefs": 0.25
    },
    "variance_thresholds": {
      "high_confidence": 0.20,
      "moderate_confidence": 0.50,
      "low_confidence_above": 0.50
    },
    "min_keyword_volume": 10,
    "min_backlink_dr": 10
  },
  "cache_ttl_days": {
    "domain_metrics": 14,
    "keyword_volumes": 30,
    "serp_rankings": 3,
    "backlink_profiles": 7,
    "gsc_data": 3
  },
  "report": {
    "page_size": "A4",
    "brand_color_primary": "#1a365d",
    "brand_color_secondary": "#2b6cb0",
    "font_body": "Arial",
    "font_heading": "Arial"
  }
}
```

### 4.3 Metadata Schema (`clients/{slug}/audit-{date}/metadata.json`)

```json
{
  "client": "example-corp",
  "audit_date": "2026-02-20",
  "initiated_by": "alex",
  "sessions": {
    "gather": {"started": "2026-02-20T09:00:00Z", "completed": "2026-02-20T09:28:00Z"},
    "analyse": {"started": "2026-02-20T09:30:00Z", "completed": "2026-02-20T10:05:00Z"},
    "strategise": {"started": "2026-02-20T10:10:00Z", "completed": "2026-02-20T10:55:00Z"},
    "deliver": {"started": "2026-02-20T11:00:00Z", "completed": "2026-02-20T11:50:00Z"}
  },
  "data_sources": {
    "organic_keywords": {
      "primary": "ahrefs_organic_keywords",
      "pulled_at": "2026-02-20T09:05:00Z",
      "raw_record_count": 47832,
      "processed_record_count": 2841,
      "validated_against": ["semrush", "dataforseo"],
      "cross_validation_variance": 0.12,
      "confidence": "high"
    },
    "backlinks": {
      "primary": "ahrefs_all_backlinks",
      "pulled_at": "2026-02-20T09:08:00Z",
      "raw_record_count": 8429,
      "processed_record_count": 8429,
      "validated_against": ["semrush"],
      "confidence": "high"
    },
    "technical_audit": {
      "sources": ["screaming_frog", "ahrefs_site_audit", "claude_seo_audit", "pagespeed_insights"],
      "screaming_frog_crawl_date": "2026-02-19",
      "pages_crawled": 342,
      "confidence": "high"
    },
    "ai_visibility": {
      "source": "ahrefs_brand_radar",
      "pulled_at": "2026-02-20T09:12:00Z",
      "platforms_tracked": ["chatgpt", "gemini", "perplexity", "google_ai_overviews", "google_ai_mode", "copilot"],
      "confidence": "high"
    },
    "gsc": {
      "available": false,
      "note": "Client had no GSC configured. Setup initiated during onboarding."
    }
  },
  "tools_versions": {
    "screaming_frog": "21.x",
    "claude_seo_skill": "latest",
    "ahrefs_api": "v3",
    "semrush_api": "v3"
  }
}
```

---

## 5. THE WORKFLOW — FOUR SESSIONS

### Overview

Each client audit consists of four Claude Code sessions. Sessions are separated by context clears (`/clear` or new session) to prevent context window overload. Each session reads only the briefing from the previous session plus targeted data files — never raw API dumps.

```
SESSION 1: GATHER  →  raw data + claude-seo outputs  →  phase1-briefing.md
     ↓ /clear
SESSION 2: ANALYSE →  cross-validated processed data  →  phase2-briefing.md
     ↓ /clear
SESSION 3: STRATEGISE → prioritized strategy           →  phase3-briefing.md
     ↓ HUMAN REVIEW
SESSION 4: DELIVER  →  report.docx + dashboard data    →  client deliverables
```

### 5.1 SESSION 1: GATHER (~30 minutes)

**Goal:** Collect all raw data from every source and produce initial findings.

**Context budget:** ~5K tokens for instructions, ~15K for claude-seo outputs in context during generation, then saved to disk.

**Step 1 — claude-seo analysis (run these commands, save each output to file):**

```bash
# Full site audit — fires 6 parallel subagents
/seo audit https://{client-domain}
# Save output → clients/{slug}/audit-{date}/data/raw/claude-seo/audit-output.md

# Schema markup detection and validation
/seo schema https://{client-domain}
# Save output → clients/{slug}/audit-{date}/data/raw/claude-seo/schema-output.md

# AI search optimization / GEO analysis
/seo geo https://{client-domain}
# Save output → clients/{slug}/audit-{date}/data/raw/claude-seo/geo-output.md

# E-E-A-T content quality analysis
/seo content https://{client-domain}
# Save output → clients/{slug}/audit-{date}/data/raw/claude-seo/content-eeat-output.md

# Sitemap analysis
/seo sitemap https://{client-domain}/sitemap.xml
# Save output → clients/{slug}/audit-{date}/data/raw/claude-seo/sitemap-output.md
```

**Step 2 — API data pulls (Python scripts, results saved directly to disk):**

```bash
# Ahrefs: batch analysis (client + all competitors in one call, max 100 URLs)
# Ahrefs: organic keywords with parent_topic, traffic_potential, intent
# Ahrefs: all backlinks + referring domains
# Ahrefs: Brand Radar mentions + impressions + share of voice
# Ahrefs: site audit issues
python scripts/gather/ahrefs_pull.py {client-slug}

# Semrush: keyword overview for top keywords from Ahrefs pull
# Semrush: organic research for client + competitors
# Semrush: backlink analytics summary
python scripts/gather/semrush_pull.py {client-slug}

# DataForSEO: live SERP for top 20 target keywords
# DataForSEO: bulk keyword difficulty + search intent
# DataForSEO: on-page analysis for top 10 client pages
python scripts/gather/dataforseo_pull.py {client-slug}

# GSC (only if access is configured)
python scripts/gather/gsc_pull.py {client-slug}

# PageSpeed Insights for top 10 pages
python scripts/gather/psi_pull.py {client-slug}
```

**Step 3 — Initial processing + briefing generation:**

```bash
# Cross-validate keyword volumes across three sources
# Cross-validate backlink counts
# Flag any variance > 50%
python scripts/process/cross_validate.py {client-slug} {audit-date}

# Generate Phase 1 briefing (<2000 words)
python scripts/process/generate_briefing.py {client-slug} {audit-date} --phase 1
```

**Step 4 — Validate and clear:**

```bash
# Check all expected files exist, record counts above thresholds
python scripts/validate/data_check.py {client-slug} {audit-date} --phase 1

# Clear context for Session 2
/clear
```

**Phase 1 Briefing Template** (`templates/briefing-phase1.md`):

```markdown
# Phase 1 Briefing: {client_name}
## Audit Date: {date}

### Domain Overview
- Domain: {domain}
- DR: {dr} | DA: {da} | Authority Score: {as}
- Estimated organic traffic: {range_low}-{range_high}/month
- Organic keywords (top 100 positions): {count}
- Referring domains: {count}
- Indexed pages: {count}

### Competitors Snapshot
| Domain | DR | Organic Traffic Est. | Keywords | Ref. Domains |
|--------|----|--------------------|----------|-------------|
| {comp1} | {dr} | {traffic} | {kw} | {rd} |
| {comp2} | {dr} | {traffic} | {kw} | {rd} |
| {comp3} | {dr} | {traffic} | {kw} | {rd} |

### Key Technical Findings (from claude-seo audit + Screaming Frog)
- {finding_1}
- {finding_2}
- {finding_3}
- Core Web Vitals: LCP {lcp}s | INP {inp}ms | CLS {cls}

### Key Content Findings (from claude-seo E-E-A-T)
- E-E-A-T assessment: {summary}
- Content gaps identified: {count} topic areas
- Schema status: {summary}

### Key Backlink Findings
- Total referring domains: {count} (Ahrefs) / {count} (Semrush)
- DR distribution: {summary}
- Toxic/spam signals: {summary}

### AI Search Visibility (Brand Radar)
- Brand mentions across AI platforms: {count}
- Share of voice vs. competitors: {percentage}
- Top citing domains in AI responses: {list}

### Data Quality Notes
- Cross-validation variance for keyword volumes: {percentage} — {confidence}
- Cross-validation variance for backlink counts: {percentage} — {confidence}
- GSC data: {available/not available}
- Files: {count} raw files, {total_size}

### Top 20 Keywords by Traffic Potential
| Keyword | Volume (validated) | KD | Position | Traffic Potential | Parent Topic | Intent |
|---------|-------------------|-----|----------|------------------|-------------|--------|
(table of top 20)
```

---

### 5.2 SESSION 2: ANALYSE (~30 minutes)

**Goal:** Transform raw data into strategic insights through clustering, gap analysis, and competitive benchmarking.

**Input:** `phase1-briefing.md` + processed CSVs (read specific files as needed, not all at once)

**Step 1 — Read briefing and orient:**

```
Read clients/{slug}/audit-{date}/data/briefings/phase1-briefing.md
```

**Step 2 — Run analysis scripts:**

```bash
# Cluster keywords by Ahrefs parent_topic
# Output: keywords-clustered.csv with columns:
# parent_topic, keyword, volume, kd, position, traffic_potential, intent, cluster_size
python scripts/process/keyword_cluster.py {client-slug} {audit-date}

# Find backlink gap: domains linking to 2+ competitors but not client
# Output: backlink-gap.csv with columns:
# domain, dr, linked_competitors, total_backlinks, contact_url
python scripts/process/backlink_gap.py {client-slug} {audit-date}

# Find content gap: keywords competitors rank for in top 20, client doesn't
# Output: content-gap.csv with columns:
# keyword, volume, kd, best_competitor, competitor_position, parent_topic, intent
python scripts/process/content_gap.py {client-slug} {audit-date}

# Aggregate technical issues from all sources with priority scoring
# Output: technical-issues-prioritized.csv with columns:
# issue, source, severity, affected_urls_count, estimated_impact, fix_complexity
python scripts/process/technical_aggregate.py {client-slug} {audit-date}
```

**Step 3 — Claude Code analysis (in context):**

With the processed CSVs available, Claude Code performs strategic analysis:

- Read `keywords-clustered.csv` — identify the 5-8 most valuable topic clusters by (total traffic potential × number of keywords ÷ average difficulty)
- Read `content-gap.csv` — map gaps to clusters, identify which clusters have the biggest content deficit
- Read `backlink-gap.csv` — prioritize link targets by DR and number of competitor connections
- Read `competitors-matrix.csv` — identify where client is strongest/weakest relative to competitors
- Combine with AI visibility data — which competitors dominate AI responses?

**Step 4 — Generate Phase 2 briefing:**

```bash
python scripts/process/generate_briefing.py {client-slug} {audit-date} --phase 2
/clear
```

**Phase 2 Briefing Template** (`templates/briefing-phase2.md`):

```markdown
# Phase 2 Briefing: {client_name}
## Analysis Summary

### Topic Clusters Identified ({count} clusters)
| Cluster (Parent Topic) | Keywords | Total Volume | Avg KD | Traffic Potential | Content Exists | Gap |
|----------------------|----------|-------------|--------|------------------|---------------|-----|
(table of all clusters, sorted by traffic potential)

### Top Content Gaps (opportunities)
| Topic Area | Keywords Missing | Combined Volume | Avg KD | Best Competitor | Their Position |
|-----------|-----------------|----------------|--------|----------------|---------------|
(top 15-20 content opportunities)

### Backlink Gap Analysis
- Total unique link opportunities: {count}
- Average DR of opportunity domains: {avg}
- Domains linking to 3+ competitors but not client: {count}
- Top 10 highest-value link targets: {list with DR and contact info}

### Competitive Position Matrix
| Metric | Client | Comp 1 | Comp 2 | Comp 3 |
|--------|--------|--------|--------|--------|
| DR | | | | |
| Organic keywords (top 10) | | | | |
| Estimated traffic | | | | |
| Referring domains | | | | |
| AI share of voice | | | | |

### Technical Priority Stack
| Priority | Issue | Affected Pages | Impact | Fix Effort |
|----------|-------|---------------|--------|-----------|
(ranked list of technical issues)

### Quick Wins (positions 8-20, low KD, high volume)
| Keyword | Current Position | Volume | KD | Page | Action Needed |
|---------|-----------------|--------|-----|------|--------------|
(top 10 quick wins)

### Key Strategic Observations
- {observation_1 — e.g., "Competitor X dominates cluster Y but has weak backlink profile"}
- {observation_2}
- {observation_3}
```

---

### 5.3 SESSION 3: STRATEGISE (~45 minutes)

**Goal:** Transform analysis into a prioritized, actionable strategy with specific recommendations.

**Input:** `phase2-briefing.md`

**Step 1 — Read briefing and activate claude-seo strategic planning:**

```
Read clients/{slug}/audit-{date}/data/briefings/phase2-briefing.md

# Use claude-seo strategic planning framework
/seo plan
# This provides industry-specific strategy templates and frameworks
# Save output → used as scaffolding for strategy development
```

**Step 2 — Claude Code develops strategy (in context — this is the intellectual work):**

Claude Code produces:

**A. Topic Cluster Prioritization (5-8 clusters for first 6 months)**
- Scoring formula: (traffic_potential × feasibility_score) ÷ difficulty_score
- Feasibility considers: existing content to optimize, keyword difficulty, competitor strength
- Each cluster gets: 1 pillar page definition + 8-15 supporting article briefs

**B. Content Plan with Briefs**
- For each of the top 10-15 content opportunities:
  - Target keyword + secondary keywords
  - Search intent classification
  - Recommended content format (guide, comparison, tool, case study)
  - Word count target (based on SERP analysis)
  - Key topics to cover (from "also rank for" keywords)
  - Internal linking targets
  - Schema markup to implement

**C. Link Building Strategy**
- Targets categorized by acquisition method: guest post, resource page, broken link, digital PR
- Prioritized by: DR × relevance score
- Monthly targets: {number} new referring domains

**D. Technical Fix Roadmap**
- Immediate (week 1): Critical errors blocking indexation
- Short-term (month 1): Performance and crawlability
- Medium-term (month 2-3): Schema, internal linking optimization
- Each fix with: specific pages/URLs affected, exact fix description, expected impact

**E. AI Search Optimization Strategy (GEO)**
- Based on Brand Radar data + claude-seo GEO analysis
- Fact density targets (every 150-200 words)
- Entity markup recommendations
- Platform-specific tactics (ChatGPT vs Perplexity vs Google AI)
- Citation-worthy content formats to create

**Step 3 — Generate Phase 3 briefing:**

```bash
python scripts/process/generate_briefing.py {client-slug} {audit-date} --phase 3
```

**Step 4 — HUMAN CHECKPOINT:**

> **STOP.** Alex reviews phase3-briefing.md before proceeding to Session 4. This is where the strategist evaluates whether the AI's recommendations make business sense for this specific client. Adjust, add context, override as needed. Mark as approved in metadata.json.

```bash
/clear
```

---

### 5.4 SESSION 4: DELIVER (~60 minutes)

**Goal:** Produce the final client deliverables — strategic report (.docx) and dashboard data.

**Input:** `phase3-briefing.md` (approved by human)

**Step 1 — Generate charts:**

```bash
# Creates PNG charts from processed data
python scripts/export/charts.py {client-slug} {audit-date}
# Outputs:
#   charts/traffic-trend.png
#   charts/keyword-distribution.png
#   charts/backlink-growth.png
#   charts/competitive-matrix.png
#   charts/technical-issues-breakdown.png
#   charts/ai-visibility-comparison.png
```

**Step 2 — Generate report (.docx):**

Claude Code reads the approved phase3-briefing.md and uses docx-js to generate the 12-section report (see Section 7 for full report specification).

```bash
node scripts/report/generate_report.js {client-slug} {audit-date}
# Output: clients/{slug}/audit-{date}/reports/audit-report.docx
```

**Step 3 — Generate CSV exports for client:**

```bash
python scripts/export/to_csv.py {client-slug} {audit-date}
# Outputs:
#   exports/keyword-opportunities.csv
#   exports/backlink-targets.csv
#   exports/technical-fixes.csv
#   exports/content-calendar.csv
#   exports/topic-clusters.csv
```

**Step 4 — Push dashboard data to Google Sheets:**

```bash
python scripts/export/to_sheets.py {client-slug} {audit-date}
# Updates the client's Google Sheet with latest metrics
# Looker Studio auto-refreshes from Sheets
```

**Step 5 — Final validation:**

```bash
python scripts/validate/data_check.py {client-slug} {audit-date} --phase 4
# Checks:
#   ✓ Report file exists and is valid .docx
#   ✓ All CSV exports present
#   ✓ Google Sheet updated
#   ✓ metadata.json complete
#   ✓ All data provenance entries filled
```

---

## 6. CROSS-VALIDATION METHODOLOGY

### 6.1 Keyword Volume Cross-Validation

**Weighted combination formula:**

```
validated_volume = (0.45 × semrush_volume) + (0.30 × dataforseo_volume) + (0.25 × ahrefs_volume)
```

**Rationale:** Semrush has 0% mismatch with Google Keyword Planner for US data and is most accurate globally. DataForSEO uses clickstream refinement of GKP data. Ahrefs uses independent clickstream methodology.

**Variance detection:**

```python
volumes = [semrush_vol, dataforseo_vol, ahrefs_vol]
mean = sum(volumes) / len(volumes)
max_deviation = max(abs(v - mean) / mean for v in volumes if mean > 0)

if max_deviation < 0.20:
    confidence = "high"        # Accept weighted average
elif max_deviation < 0.50:
    confidence = "moderate"    # Flag, use Semrush as primary
else:
    confidence = "low"         # Investigate, note in report
```

**When GSC data is available (own site):**

```
For keywords where GSC shows actual impressions:
- Use GSC impressions as ground truth for own site
- Compare against third-party estimates
- Calculate tool-specific correction factors for this domain
- Apply correction factors to competitor estimates
```

### 6.2 Backlink Cross-Validation

**Primary metric:** Referring domains count (more stable than raw backlink count)

```
# Report as: Ahrefs count (primary), with Semrush for comparison
# Do NOT average — different indexes find different links
# Instead, note both: "482 referring domains (Ahrefs) / 394 (Semrush)"
# Use Ahrefs as the authoritative number in report body
```

**Link quality scoring (per referring domain):**

```python
quality_score = (
    (ahrefs_dr / 100) * 0.40 +
    (moz_da / 100) * 0.25 +
    (1 - moz_spam_score / 100) * 0.20 +
    relevance_score * 0.15  # Manual or NLP-based (0-1)
)
# Flag as "potentially toxic" if quality_score < 0.15
```

### 6.3 Traffic Estimate Cross-Validation

**For competitors (no GSC access):**

```
# ALWAYS present as range, never single number
traffic_estimate = {
    "low": min(ahrefs_traffic, semrush_traffic),
    "high": max(ahrefs_traffic, semrush_traffic),
    "note": "Third-party estimates. Actual traffic may vary ±30-60%."
}
```

**For own site (with GSC):**

```
# Use GSC clicks as primary metric
# Note discrepancy with third-party estimates
# Calculate correction factor: gsc_actual / avg(ahrefs_est, semrush_est)
# This correction factor can be applied cautiously to competitor estimates
```

---

## 7. REPORT SPECIFICATION — 12 SECTIONS

The strategic report is the primary client deliverable. Generated as .docx using docx-js.

### Report Structure

**Cover Page:**
- Client logo (if provided) + Authoricy logo
- "SEO Audit & Strategy Report"
- Client name, domain
- Date
- "Prepared by Authoricy AB"

**Table of Contents** (auto-generated from headings)

**Section I: Executive Summary** (1-2 pages)
- SEO Health Score (0-100, weighted composite)
- Top 3-5 findings with business impact stated in plain language
- Competitive positioning summary (where client stands vs. competitors)
- 90-day priority actions (numbered list, max 5)
- Estimated impact of full strategy implementation (traffic range, not false precision)

**Section II: Current State Analysis** (2-3 pages)
- Organic traffic trend (chart: 12-month if GSC available, else Ahrefs estimated)
- Keyword visibility breakdown (positions 1-3, 4-10, 11-20, 21-50, 51-100)
- Top 10 pages by traffic with their primary keywords
- Brand vs non-brand traffic split (if GSC available)
- Data sources: clearly stated with confidence levels

**Section III: Technical SEO Audit** (2-4 pages)
- Core Web Vitals: LCP, INP, CLS with pass/fail per threshold
- Crawlability: robots.txt, sitemap, redirect chains, orphan pages
- Indexation: indexed vs submitted, coverage errors
- Mobile usability
- URL architecture assessment
- Internal linking structure (with visualization if Gephi export available)
- Schema markup status (from claude-seo `/seo schema`)
- JS rendering issues (from Screaming Frog JS crawl)
- Security: HTTPS, mixed content
- Source attribution: "Technical findings compiled from Screaming Frog crawl, Ahrefs Site Audit, claude-seo analysis, and PageSpeed Insights"

**Section IV: Keyword Research & Opportunity Analysis** (3-4 pages)
- Current keyword portfolio overview (volume distribution, intent breakdown)
- Cross-validated top keywords table (validated volume, KD, position, intent)
- Quick wins: positions 8-20 with low KD and actionable recommendations
- KOB analysis (Keyword Opposition to Benefit): volume × CTR estimate ÷ difficulty
- Search intent distribution pie chart
- Source attribution: "Keyword data cross-validated across Ahrefs, Semrush, and DataForSEO"

**Section V: Topical Map** (3-5 pages)
- Visual cluster map (showing pillar → supporting article relationships)
- For each cluster (5-8 clusters):
  - Pillar page: target keyword, volume, URL (existing or proposed)
  - Supporting articles: 8-15 per cluster, with keyword + volume + intent
  - Total cluster traffic potential
  - Estimated content effort (word count, number of pieces)
- URL architecture recommendations for cluster structure
- Internal linking strategy between cluster pages
- Source: "Clusters built from Ahrefs parent_topic analysis, validated against SERP overlap"

**Section VI: Content Strategy** (2-3 pages)
- Content gap analysis summary (what competitors have that client doesn't)
- E-E-A-T assessment (from claude-seo `/seo content`)
- ICE prioritization framework: Impact × Confidence × Ease
- 12-month content calendar (quarter by quarter)
- Content format recommendations per cluster (guides, comparisons, tools, case studies)

**Section VII: Backlink Profile & Link Strategy** (2-3 pages)
- Current backlink profile: referring domains, DR distribution, anchor text breakdown
- Toxic/spam link assessment
- Anchor text distribution analysis (target: ~60% branded, ~40% diverse)
- Link gap: domains linking to competitors but not client
- Prioritized link building targets (top 20-30) with DR and acquisition method
- Broken backlink recovery opportunities
- Monthly link building targets
- Source: "Backlink data from Ahrefs (primary index), validated against Semrush"

**Section VIII: SERP Features & AI Search (GEO)** (2-3 pages)
- SERP feature ownership: featured snippets, PAA, knowledge panels, image packs
- Featured snippet optimization opportunities
- AI Search landscape:
  - Brand Radar data: mentions, impressions, share of voice across platforms
  - Which AI platforms mention client vs competitors
  - What questions trigger client mentions
  - Which pages are cited in AI responses
- GEO strategy:
  - Fact density recommendations (every 150-200 words)
  - Entity markup priorities
  - Platform-specific tactics
  - Citation-worthy content formats to create
- Source: "AI visibility data from Ahrefs Brand Radar; GEO analysis via claude-seo"

**Section IX: Local SEO** (1-2 pages, if applicable)
- Google Business Profile audit
- Local citation consistency
- Review analysis
- Local keyword opportunities
- NAP consistency check
- (Skip this section entirely for B2B clients with no physical customer locations)

**Section X: Competitive Intelligence** (2-3 pages)
- Competitive matrix table (DR, traffic, keywords, content volume, AI visibility)
- Per-competitor analysis (1 paragraph each): strengths, weaknesses, strategy observations
- Content comparison: which topics each competitor owns
- Backlink comparison: link velocity, top link sources
- AI visibility comparison: who dominates which platforms
- All metrics include confidence indicators

**Section XI: Implementation Roadmap** (2-3 pages)
- **Q1 (Month 1-3):** Technical fixes + quick wins + GSC setup
  - Week-by-week technical fix schedule
  - Quick win content optimizations (existing pages, positions 8-20)
  - GSC and GA4 configuration
  - Estimated impact: +{X}% organic traffic
- **Q2 (Month 4-6):** First topic clusters + link building launch
  - Pillar content creation schedule
  - Supporting content calendar
  - Link building campaign targets
  - Estimated impact: +{X}% organic traffic
- **Q3 (Month 7-9):** Content scaling + GEO optimization
  - Additional cluster rollout
  - AI search optimization implementation
  - Content refresh schedule for existing pages
  - Estimated impact: +{X}% organic traffic
- **Q4 (Month 10-12):** Compounding growth + AI dominance
  - Full topical authority push
  - Advanced link building (digital PR, data-driven content)
  - AI share of voice targets
  - Estimated impact: +{X}% organic traffic

**Section XII: Appendices**
- A: Full keyword opportunities export (reference to CSV)
- B: Complete technical audit findings (reference to CSV)
- C: Backlink profile details (reference to CSV)
- D: Data provenance — for every data point in this report:
  - Source tool
  - Date pulled
  - Cross-validation method
  - Confidence level

**Every section footer includes:**
```
Data sources: {tools used} | Data pulled: {date} | Confidence: {high/moderate/low}
```

---

## 8. DASHBOARD SPECIFICATION

### 8.1 Architecture

```
Data Sources → Google Sheets (bridge) → Looker Studio (dashboard)
     ↓                                       ↓
GSC ─────────────────────────────→ Looker Studio (native connector)
GA4 ─────────────────────────────→ Looker Studio (native connector)
Ahrefs ──→ Python script ──→ Google Sheets ──→ Looker Studio
Semrush ─→ Python script ──→ Google Sheets ──→ Looker Studio
```

### 8.2 Google Sheets Structure (one sheet per client)

| Tab Name | Data | Update Frequency | Source |
|----------|------|-----------------|--------|
| `overview` | DR, DA, organic traffic estimate, keyword count, ref domains | Monthly | Ahrefs batch-analysis |
| `keywords` | Top 50 tracked keywords: position, volume, URL, change | Monthly | Ahrefs organic-keywords |
| `backlinks` | New/lost referring domains, DR distribution summary | Monthly | Ahrefs referring-domains |
| `competitors` | Competitor DR, traffic, keywords, ref domains | Monthly | Ahrefs batch-analysis |
| `technical` | CWV scores, crawl errors count, indexation status | Monthly | PSI API + GSC |
| `ai-visibility` | Brand Radar: mentions, impressions, SOV per platform | Monthly | Ahrefs Brand Radar |
| `content` | Top 20 pages: traffic, keywords, position changes | Monthly | Ahrefs top-pages |

### 8.3 Looker Studio Dashboard Pages

**Page 1: Executive Overview**
- Scorecard row: DR, Organic Traffic (GSC), Total Keywords, Referring Domains
- Traffic trend line chart (GSC, last 12 months)
- Month-over-month change indicators
- Top 5 pages by traffic

**Page 2: Keyword Performance**
- Rankings distribution bar chart (1-3, 4-10, 11-20, 21-50, 51-100)
- Top keywords table with position + change
- New keywords gained / keywords lost
- Filter by: brand vs non-brand

**Page 3: Content Performance**
- Top pages by organic traffic (GSC)
- Pages by engagement (GA4: avg session duration, bounce rate)
- Content gap coverage progress (how many planned pieces published)

**Page 4: Backlink Health**
- Referring domains trend line
- New vs lost referring domains per month
- DR distribution of referring domains (bar chart)

**Page 5: Technical Health**
- Core Web Vitals gauges (LCP, INP, CLS — green/yellow/red)
- Indexation: indexed vs submitted pages
- Crawl errors trend

**Page 6: AI Visibility**
- Share of voice comparison: client vs competitors (bar chart)
- Mentions trend by platform (line chart)
- Top cited pages

**Page 7: Competitive Snapshot**
- Competitor comparison table (DR, traffic, keywords)
- Radar chart: client vs top competitor across 5 metrics

### 8.4 Dashboard Setup Process

1. Create Google Sheet from template (clone master sheet)
2. Run `to_sheets.py` to populate initial data
3. Open Looker Studio, clone master dashboard template
4. Connect native connectors: GSC property, GA4 property
5. Connect Google Sheets data source (bridge data)
6. Customize: client name, logo, date range defaults
7. Share dashboard link with client (view-only)

**Setup time per new client:** ~30 minutes
**Monthly maintenance:** ~15 minutes (run `to_sheets.py`, spot-check data)

---

## 9. claude-seo INTEGRATION SPECIFICATION

### 9.1 Installation

```bash
curl -fsSL https://raw.githubusercontent.com/AgriciDaniel/claude-seo/main/install.sh | bash
```

Installs to:
- `~/.claude/skills/seo/` — Main skill (orchestrator)
- `~/.claude/skills/seo-*/` — 12 sub-skills
- `~/.claude/agents/seo-*.md` — 6 subagents for parallel audit

### 9.2 Commands and Their Role in This System

| Command | Session | Purpose in Our Workflow | Output Location |
|---------|---------|----------------------|----------------|
| `/seo audit {url}` | Session 1 | Full site audit via 6 parallel subagents — technical, content, schema, sitemap, performance, visual | `data/raw/claude-seo/audit-output.md` |
| `/seo schema {url}` | Session 1 | Schema detection, validation, JSON-LD generation for 12+ types | `data/raw/claude-seo/schema-output.md` |
| `/seo geo {url}` | Session 1 | AI search citability analysis — GEO framework for optimizing presence in ChatGPT, Perplexity, Google AI | `data/raw/claude-seo/geo-output.md` |
| `/seo content {url}` | Session 1 | E-E-A-T analysis (updated for Dec 2025 core update) | `data/raw/claude-seo/content-eeat-output.md` |
| `/seo technical {url}` | Session 1 | Technical audit across 8 categories with CWV thresholds | `data/raw/claude-seo/technical-output.md` |
| `/seo sitemap {url}` | Session 1 | XML sitemap analysis | `data/raw/claude-seo/sitemap-output.md` |
| `/seo images {url}` | Session 1 | Image optimization analysis | `data/raw/claude-seo/images-output.md` |
| `/seo plan` | Session 3 | Strategic planning with industry templates — provides framework scaffolding | Used in-context, not saved separately |
| `/seo competitor-pages` | Session 3 | Competitor comparison content generation | Used in-context for content strategy |
| `/seo hreflang {url}` | Session 1 | International SEO — only for multi-language clients | `data/raw/claude-seo/hreflang-output.md` |
| `/seo page {url}` | Ad-hoc | Single page deep analysis — use for pre-publish content checks | Not part of standard audit flow |
| `/seo programmatic` | Ad-hoc | Programmatic SEO with quality safeguards — use when scaling content | Not part of standard audit flow |

### 9.3 What claude-seo Does NOT Do (And How We Fill the Gaps)

| What it lacks | How we handle it |
|--------------|-----------------|
| Does not call APIs | Our Python scripts pull data from Ahrefs/Semrush/DataForSEO MCPs |
| Does not cross-validate data | Our `cross_validate.py` handles this |
| Does not generate .docx reports | Our `generate_report.js` handles this |
| Does not track AI visibility | Ahrefs Brand Radar provides this data |
| Does not manage client data structure | Our folder structure and metadata.json handle this |
| Does not push to dashboards | Our `to_sheets.py` handles this |

### 9.4 How claude-seo Outputs Feed Into Processing

```
claude-seo /seo audit output
    ↓
technical_aggregate.py reads audit-output.md
    ↓ extracts structured findings
    ↓ merges with Screaming Frog CSV + Ahrefs Site Audit JSON + PSI data
    ↓
technical-issues-prioritized.csv
    ↓
Phase 2 briefing includes prioritized technical findings
    ↓
Report Section III (Technical SEO Audit) draws from this
```

```
claude-seo /seo geo output
    ↓
Combined with Ahrefs Brand Radar data in Phase 3
    ↓
GEO strategy section in phase3-briefing.md
    ↓
Report Section VIII (SERP Features & AI Search) draws from both sources
```

---

## 10. CACHING STRATEGY

### 10.1 Cache Location and Format

```
cache/{domain}/{tool}/{datatype}_{YYYY-MM-DD}.json
```

Example:
```
cache/example.com/ahrefs/organic-keywords_2026-02-20.json
cache/example.com/semrush/keyword-overview_2026-02-15.json
```

### 10.2 TTL (Time To Live) Rules

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Domain metrics (DR, DA) | 14 days | Changes slowly |
| Keyword volumes | 30 days | Updated monthly by providers |
| SERP rankings | 1-3 days | Changes frequently |
| Backlink profiles | 7 days | New links found daily |
| GSC data | Until new data (2-3 day lag) | Google's processing delay |
| Brand Radar | 14 days | AI responses change weekly |
| PageSpeed / CWV | 7 days | Affected by site changes |

### 10.3 Cache Logic in Pull Scripts

```python
def get_cached_or_pull(domain, tool, datatype, ttl_days, pull_function):
    cache_path = find_latest_cache(domain, tool, datatype)
    if cache_path and is_within_ttl(cache_path, ttl_days):
        log(f"Using cached {datatype} for {domain} from {cache_path}")
        return load_json(cache_path)
    else:
        data = pull_function()
        save_cache(domain, tool, datatype, data)
        return data
```

### 10.4 Cache Invalidation

- Manual: Delete the cache file to force a fresh pull
- Automatic: TTL expiry
- Full reset: `rm -rf cache/{domain}/` for a complete refresh of one domain
- Scripts must log whether data came from cache or fresh pull in metadata.json

---

## 11. ERROR HANDLING

### 11.1 API Failures

**Retry strategy:** Exponential backoff with jitter

```python
import time, random

def api_call_with_retry(call_function, max_retries=5):
    for attempt in range(max_retries):
        try:
            return call_function()
        except (RateLimitError, TimeoutError, ConnectionError) as e:
            if attempt == max_retries - 1:
                raise
            wait = min(300, (2 ** attempt) + random.uniform(0, 1))
            log(f"Retry {attempt + 1}/{max_retries} after {wait:.1f}s: {e}")
            time.sleep(wait)
```

### 11.2 Fallback Chains

When a primary tool is unavailable, fall back to alternatives:

| Data Type | Primary | Fallback 1 | Fallback 2 | Last Resort |
|-----------|---------|-----------|-----------|-------------|
| Backlinks | Ahrefs | Semrush | DataForSEO | Note gap in metadata |
| Keyword volumes | Semrush | DataForSEO | Ahrefs | Note gap in metadata |
| SERP data | DataForSEO | Ahrefs serp-overview | Semrush | Note gap in metadata |
| Domain authority | Ahrefs DR | Moz DA | Semrush AS | Note gap in metadata |
| Technical audit | Screaming Frog | Ahrefs Site Audit | claude-seo audit | Note limitations |
| AI visibility | Ahrefs Brand Radar | — | — | Skip section with note |

### 11.3 Data Quality Failures

| Condition | Action |
|-----------|--------|
| Keyword volume variance > 50% between tools | Flag as "low confidence" in metadata, use Semrush as primary, note in report |
| Ahrefs returns 0 backlinks for a live site | Likely API error — retry. If persists, use Semrush as primary for backlinks |
| Screaming Frog crawl returns < 50% of expected pages | Check robots.txt blocking, JS rendering issues. Re-crawl with different settings |
| GSC shows manual action | ESCALATE — notify Alex immediately, this changes the entire strategy |
| Cross-validation shows > 3x difference in traffic estimates | Present both numbers with explicit caveat in report. Do not average |

### 11.4 Session Recovery

If Claude Code crashes or context corrupts mid-session:

1. Check which files have been written to `data/raw/` and `data/processed/`
2. Check briefing files — if the current phase briefing exists, skip to next session
3. If mid-phase, re-run from the last completed script (scripts are idempotent — safe to re-run)
4. All raw data is preserved on disk — nothing is lost from a context clear

---

## 12. GOOGLE SEARCH CONSOLE ONBOARDING

### 12.1 Reality Check

- 60-80% of B2B clients in our target range have NO GSC configured
- 10-25% have it but don't know login credentials
- This is normal and does NOT block the audit

### 12.2 Onboarding Process

**During initial sales call / onboarding:**

1. Ask if they have GSC configured (most won't)
2. If no: set up during onboarding call (15-30 minutes)
   - Preferred method: HTML meta tag verification via CMS
   - Alternative: DNS TXT record verification
   - Tool: Leadsie (for delegated access) or Loom video walkthrough
3. If yes but no access: Help locate credentials or set up delegated access
4. Add Authoricy as a user with "Full" permission level

### 12.3 Impact on Audit Workflow

| Audit Phase | Without GSC | With GSC |
|-------------|-------------|----------|
| Session 1 (Gather) | Use Ahrefs/Semrush/DataForSEO only | Add GSC data pull |
| Session 2 (Analyse) | Competitor-only traffic estimates | Real client traffic + competitor estimates |
| Session 3 (Strategy) | Strategy based on estimated data | Strategy validated against real data |
| Session 4 (Deliver) | Report notes "GSC pending setup" | Report includes actual performance data |
| Month 2+ | GSC now collecting → incorporate in monthly reporting | Full data available |

### 12.4 GSC Becomes Critical From Month 2

Three irreplaceable data types:
1. **Actual impression and click data** — third-party estimates have 30-80% error for low-volume B2B keywords
2. **Real query data** — including long-tail phrases that third-party databases miss entirely
3. **Manual actions / penalty detection** — no other tool surfaces this

---

## 13. QUALITY GATES

### 13.1 Pre-Phase Validation (`data_check.py`)

Run before each phase transition. Phase does not start if any check fails.

**Before Session 2 (Analyse):**
```
✓ phase1-briefing.md exists and is < 2500 words
✓ All expected raw data files present (check manifest)
✓ At least 2 of 3 keyword sources returned data
✓ At least 1 backlink source returned data
✓ cross_validate.py has run (processed files exist)
✓ No raw file is 0 bytes
✓ metadata.json has all gather-phase entries
```

**Before Session 3 (Strategise):**
```
✓ phase2-briefing.md exists and is < 2500 words
✓ keywords-clustered.csv exists with > 3 clusters
✓ content-gap.csv exists with > 0 rows
✓ backlink-gap.csv exists with > 0 rows
✓ technical-issues-prioritized.csv exists
✓ competitors-matrix.csv exists
```

**Before Session 4 (Deliver):**
```
✓ phase3-briefing.md exists and is < 3000 words
✓ phase3-briefing.md has been marked as "approved" in metadata.json
✓ Strategy contains: topic clusters, content plan, link targets, technical roadmap
✓ Charts generated successfully (all PNG files present)
```

**After Session 4 (Final):**
```
✓ audit-report.docx exists and is > 10KB
✓ All CSV exports present
✓ metadata.json is complete (all sessions have timestamps)
✓ Google Sheet updated (if dashboard configured)
✓ All data provenance entries in metadata.json
```

### 13.2 Report Quality Checks

Before delivering the report, verify:

1. **No placeholder text** — search for `{`, `TODO`, `TBD`, `PLACEHOLDER`
2. **All charts embedded** — verify PNG files are referenced and present
3. **Data provenance footer** on every section
4. **Consistent numbers** — same metric should show same value throughout report
5. **Confidence flags** — any "moderate" or "low" confidence data is explicitly noted
6. **Client name correct** — search and verify no other client names appear
7. **Date current** — audit date matches actual date

---

## 14. SCALING TO MULTIPLE CLIENTS

### 14.1 Client Onboarding Checklist

```
□ Client config JSON created (domain, competitors, markets)
□ Ahrefs batch-analysis run for domain validation
□ Screaming Frog crawl completed
□ GSC access requested / setup initiated
□ GA4 access requested
□ Google Sheet created from template
□ Looker Studio dashboard cloned and connected
□ Initial audit scheduled
```

### 14.2 Monthly Maintenance Per Client

| Task | Time | Tool |
|------|------|------|
| Run `to_sheets.py` to update dashboard data | 5 min | Script |
| Quick dashboard review for anomalies | 5 min | Looker Studio |
| Check GSC for new manual actions or issues | 5 min | GSC |
| Total per client per month | ~15 min | |

### 14.3 Quarterly Re-Audit

Every 3 months, re-run the full 4-session workflow to produce an updated strategic report. Compare against previous audit's data to show progress.

```
clients/{slug}/audit-2026-02-20/  ← Initial audit
clients/{slug}/audit-2026-05-20/  ← Q2 re-audit (compares against Q1)
clients/{slug}/audit-2026-08-20/  ← Q3 re-audit
clients/{slug}/audit-2026-11-20/  ← Q4 re-audit
```

---

## 15. IMPLEMENTATION ORDER

Build this system in the following order. Each step should be tested before proceeding.

### Phase A: Foundation (Day 1-2)
1. Create project directory structure
2. Write CLAUDE.md (points to this document)
3. Create config files (tools.json, defaults.json, client-config-template.json)
4. Install claude-seo skill
5. Verify MCP connections work (Ahrefs, Semrush, DataForSEO)

### Phase B: Data Gathering Scripts (Day 3-5)
6. Build `ahrefs_pull.py` — test with real domain
7. Build `semrush_pull.py` — test with same domain
8. Build `dataforseo_pull.py` — test with same domain
9. Build `gsc_pull.py` — test with own domain (authoricy.com)
10. Build `psi_pull.py` — test with same domain
11. Build caching layer — test TTL logic

### Phase C: Processing Scripts (Day 6-8)
12. Build `cross_validate.py` — test with data from Phase B
13. Build `keyword_cluster.py` — test parent_topic grouping
14. Build `backlink_gap.py` — test with competitor set
15. Build `content_gap.py` — test with competitor set
16. Build `technical_aggregate.py` — test with audit data
17. Build `generate_briefing.py` — test all 3 phase templates

### Phase D: Validation & Export (Day 9-10)
18. Build `data_check.py` — test all validation gates
19. Build `charts.py` — test chart generation
20. Build `to_csv.py` — test export formats
21. Build `to_sheets.py` — test Google Sheets integration

### Phase E: Report Generation (Day 11-13)
22. Build `generate_report.js` — docx template with all 12 sections
23. Test full report generation with real data
24. Validate .docx opens correctly in Word/Google Docs

### Phase F: Dashboard (Day 14-15)
25. Create Looker Studio master template (7 pages)
26. Connect to test Google Sheet
27. Connect GSC + GA4 for test domain
28. Verify auto-refresh works

### Phase G: End-to-End Test (Day 16-17)
29. Run complete 4-session workflow on authoricy.com
30. Time each session
31. Review output quality
32. Fix any issues found
33. Run on a second test domain to verify portability

### Phase H: First Client (Day 18+)
34. Onboard first paying client
35. Run full audit
36. Deliver report + dashboard
37. Document any workflow adjustments
38. Update this specification if needed

---

## 16. GLOSSARY

| Term | Definition |
|------|-----------|
| **DR** | Domain Rating (Ahrefs) — 0-100 score of a domain's backlink profile strength |
| **DA** | Domain Authority (Moz) — 0-100 prediction of ranking strength |
| **KD** | Keyword Difficulty — how hard to rank in top 10 for a keyword |
| **SERP** | Search Engine Results Page |
| **GEO** | Generative Engine Optimization — optimizing for AI search (ChatGPT, Perplexity, etc.) |
| **E-E-A-T** | Experience, Expertise, Authoritativeness, Trustworthiness — Google's quality framework |
| **Parent Topic** | Ahrefs concept — the broader topic that a keyword's #1 ranking page targets |
| **Traffic Potential** | Ahrefs metric — estimated organic traffic the #1 page gets from ALL keywords it ranks for |
| **PKD** | Personal Keyword Difficulty (Semrush) — KD customized for YOUR domain |
| **Brand Radar** | Ahrefs module tracking brand mentions across 6 AI platforms |
| **SOV** | Share of Voice — percentage of total AI mentions that reference your brand |
| **MCP** | Model Context Protocol — Anthropic's standard for connecting AI to external tools |
| **ICE** | Impact × Confidence × Ease — prioritization framework |
| **KOB** | Keyword Opposition to Benefit — volume × CTR ÷ difficulty |
| **CWV** | Core Web Vitals — LCP, INP, CLS |
| **LCP** | Largest Contentful Paint — target < 2.5 seconds |
| **INP** | Interaction to Next Paint — target < 200ms |
| **CLS** | Cumulative Layout Shift — target < 0.1 |

---

*End of specification. This document is the source of truth. When in doubt, refer here.*

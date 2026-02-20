# Authoricy Engine vs Claude-SEO: Comparative Analysis

## Executive Summary

These are **fundamentally different products** solving related problems in different ways:

- **Authoricy Engine** is a **backend API service** that generates comprehensive SEO reports using paid data APIs (DataForSEO) and AI analysis (Claude). It collects real market data, runs multi-loop AI analysis, generates PDFs, and delivers them via email. It's a **commercial SaaS product**.

- **Claude-SEO** is a **Claude Code skill** (plugin) that provides interactive SEO auditing from within the Claude Code CLI. It crawls websites directly, analyzes on-page factors, and gives real-time recommendations. It's an **open-source developer tool**.

They are complementary, not competitive. But there are lessons to learn from each.

---

## 1. Side-by-Side Comparison

| Dimension | Authoricy Engine | Claude-SEO |
|-----------|-----------------|------------|
| **Type** | Backend API / SaaS platform | Claude Code skill (CLI plugin) |
| **License** | Proprietary | MIT (open source) |
| **Language** | Python 3.11+ | Python 3.8+ / Markdown / Shell |
| **Framework** | FastAPI + SQLAlchemy | Claude Code skill framework |
| **Data Source** | DataForSEO API (60 endpoints, paid) | Direct crawling (BeautifulSoup, Playwright) |
| **AI Engine** | Claude API (4 sequential analysis loops) | Claude Code (6 parallel subagents) |
| **Database** | PostgreSQL (full persistence) | None (stateless) |
| **Output** | PDF reports (40-60 pages) + email delivery | Interactive CLI recommendations |
| **Authentication** | JWT/Supabase | None (inherits Claude Code auth) |
| **Cost per use** | $1.75-2.53/report (data + AI) | Free (no paid APIs) |
| **Deployment** | Railway, Vercel, Docker | Local install to ~/.claude/skills/ |
| **GitHub Stars** | Private/new | 942 stars, 137 forks |
| **Target User** | SEO agencies, enterprise teams | Individual developers, technical SEOs |

---

## 2. Feature Gap Analysis

### Features Authoricy Has That Claude-SEO Lacks

| Feature | Authoricy | Claude-SEO | Impact |
|---------|-----------|------------|--------|
| **60-endpoint data collection** | DataForSEO with 4-phase parallel collection | Direct crawling only | Authoricy gets deeper, historical, and market-level data |
| **Historical trend analysis** | 12-24 months of historical data | No historical data | Critical for trajectory analysis |
| **Keyword universe mapping** | Full keyword discovery, gaps, clusters, intent | No keyword research capability | Major gap for Claude-SEO |
| **Backlink intelligence** | Complete backlink profile, link gaps, velocity | No backlink analysis | Significant gap |
| **Competitor deep-dive** | 4-competitor analysis with trajectory comparison | Basic competitor page comparison | Authoricy far more thorough |
| **AI visibility assessment** | 10 dedicated endpoints (LLM mentions, brand sentiment) | GEO scoring (passage-level) | Different approaches, both valuable |
| **PDF report generation** | 40-60 page strategy guides via WeasyPrint | No report generation | Business-critical for agencies |
| **Email delivery** | Automated delivery via Resend | None | Required for SaaS model |
| **Database persistence** | PostgreSQL with full schema | Stateless | Required for multi-tenant SaaS |
| **Quality gate system** | 25 checks, 92% pass rate required, auto-retry | None | Ensures consistent output quality |
| **Multi-agent architecture** | 9 specialized agents (Keyword, Backlink, Technical, Content, Semantic, AI Visibility, SERP, Local, Master Strategy) | 6 subagents (Technical, Content, Schema, Sitemap, Performance, Visual) | Authoricy broader |
| **Greenfield mode** | Competitor-first analysis for new domains | No special handling for new domains | Valuable for startups |
| **Context intelligence** | Business profiling, market detection, competitor discovery | No business context gathering | Enables goal-aligned analysis |
| **Scoring algorithms** | Custom difficulty, opportunity, winnability, decay scoring | No proprietary scoring | Quantified prioritization |
| **Strategy builder** | Full strategy with threads, topics, keyword assignment | No strategy building | Operationalizes insights |
| **Cost tracking** | Per-report cost tracking and budgeting | N/A (free) | Important for commercial viability |
| **Authentication & multi-tenancy** | JWT, Supabase, usage tracking | None needed | Required for SaaS |
| **Caching layer** | PostgreSQL-based with precomputation | None | Performance optimization |

### Features Claude-SEO Has That Authoricy Lacks

| Feature | Claude-SEO | Authoricy | Impact |
|---------|------------|-----------|--------|
| **On-page crawling & analysis** | BeautifulSoup + Playwright direct crawling | No direct page crawling | Claude-SEO can analyze actual page content |
| **Schema.org validation** | JSON-LD detection, validation, generation (20+ types) | No schema analysis | Valuable for technical SEO |
| **Sitemap auditing** | XML sitemap validation + generation with templates | No sitemap features | Basic but useful |
| **Hreflang validation** | International SEO tag auditing, reciprocal checks | No i18n SEO support | Important for multi-language sites |
| **Image optimization** | Alt text, file size, format analysis | No image-specific analysis | Useful tactical feature |
| **Visual/screenshot analysis** | Playwright screenshots with AI visual assessment | No visual analysis | Innovative UX analysis |
| **E-E-A-T content evaluation** | Structured content quality scoring | Content analysis exists but different approach | Claude-SEO more formalized |
| **Interactive CLI experience** | 13 slash commands, real-time feedback | API-only, no interactive mode | Better developer experience |
| **MCP integrations** | Ahrefs, Semrush, Google Search Console, PageSpeed | DataForSEO only | More data source options |
| **Cross-platform installers** | Bash + PowerShell with verification | Docker/manual only | Better onboarding |
| **Programmatic SEO planning** | Scale-generated page planning with quality gates (500 page limit) | No programmatic SEO | Niche but valuable |
| **AI crawler detection** | Identifies GPTBot, ClaudeBot, PerplexityBot | No crawler detection | Forward-looking feature |
| **SEO plan templates** | Industry-specific roadmaps (SaaS, local, ecommerce, publisher, agency) | No templated plans | Quick-start value |
| **Comprehensive documentation** | Architecture docs, command ref, installation guide, MCP guide, changelog | README + spec docs only | Better for adoption |
| **Security hardening** | SSRF prevention, path traversal protection, output sanitization | Basic validation only | Security-conscious |

---

## 3. Architecture Comparison

### Authoricy Engine Architecture
```
User/Frontend -> FastAPI API -> Context Intelligence -> DataForSEO (60 endpoints)
                                                    -> Claude AI (4 loops)
                                                    -> PostgreSQL (persistence)
                                                    -> WeasyPrint (PDF)
                                                    -> Resend (email)
```
**Strengths**: Full data pipeline, persistence, quality gates, commercial-grade
**Weaknesses**: Single data provider (DataForSEO), no on-page crawling, API-only

### Claude-SEO Architecture
```
Claude Code CLI -> Skill Framework -> 12 Sub-skills
                                   -> 6 Subagents (parallel)
                                   -> Python crawlers (BS4 + Playwright)
                                   -> MCP servers (Ahrefs, Semrush, GSC, PageSpeed)
```
**Strengths**: Interactive, multi-source, on-page analysis, extensible via MCP
**Weaknesses**: Stateless, no persistence, no reporting, no automation

---

## 4. Which Is Better?

**Neither is universally better. They serve different purposes.**

### Authoricy Wins When:
- You need **automated, scalable** SEO analysis (run 100 reports/month)
- You need **historical data and trends** (12-24 months)
- You need **PDF deliverables** for clients
- You need **keyword research at scale** (universe mapping, gap analysis)
- You need **backlink intelligence** (link gaps, velocity, referring domains)
- You need a **commercial product** with auth, billing, multi-tenancy
- You need **consistent quality** (25-check quality gate)

### Claude-SEO Wins When:
- You need **interactive, on-demand** SEO auditing
- You want to **audit actual page content** (on-page SEO, schema, images)
- You need **zero-cost** analysis (no API fees)
- You want **multiple data sources** via MCP (Ahrefs + Semrush + GSC)
- You need **technical SEO checks** (sitemap, hreflang, Core Web Vitals)
- You want a **developer-friendly** CLI experience
- You need **open source** with community support

---

## 5. What Authoricy Can Learn from Claude-SEO

### High Priority

1. **On-page crawling capability**
   - Claude-SEO directly crawls and analyzes page content using BeautifulSoup/Playwright
   - Authoricy relies entirely on DataForSEO for page data, which means it cannot see actual page content, schema markup, or visual layout
   - **Recommendation**: Add a lightweight crawling module (even just for top 10 pages) to complement DataForSEO data. This would enable schema validation, content quality scoring, and image optimization checks

2. **Schema.org validation and generation**
   - Claude-SEO has comprehensive JSON-LD detection and generation for 20+ schema types
   - Authoricy collects `schema_data` from DataForSEO but doesn't validate or recommend schema improvements
   - **Recommendation**: Add schema validation to the technical SEO agent. Generate recommended JSON-LD snippets in reports

3. **MCP integration architecture**
   - Claude-SEO integrates with Ahrefs, Semrush, Google Search Console, and PageSpeed via MCP
   - Authoricy is locked to DataForSEO as its sole data source
   - **Recommendation**: Consider adding optional data enrichment from other sources. Even just Google Search Console integration would add verified click/impression data that DataForSEO cannot provide

4. **Interactive mode / real-time analysis**
   - Claude-SEO provides immediate, interactive feedback
   - Authoricy is batch-only (submit job, wait, get PDF)
   - **Recommendation**: Consider adding a lightweight real-time analysis endpoint that returns quick insights without running the full 60-endpoint pipeline. Useful for the frontend dashboard

### Medium Priority

5. **E-E-A-T content evaluation framework**
   - Claude-SEO has a structured E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) scoring system
   - Authoricy's content analysis agent exists but doesn't formalize E-E-A-T scoring
   - **Recommendation**: Add explicit E-E-A-T scoring to the Content Analysis Agent output

6. **Hreflang / international SEO**
   - Claude-SEO validates hreflang tags and reciprocal references
   - Authoricy has multi-market support but no hreflang validation
   - **Recommendation**: Add hreflang checks to the Technical SEO Agent, especially since Authoricy already handles multi-market analysis

7. **AI crawler optimization (GEO)**
   - Claude-SEO has sophisticated Generative Engine Optimization including AI crawler detection (GPTBot, ClaudeBot, PerplexityBot) and passage-level citability scoring
   - Authoricy has AI visibility endpoints but focuses on brand mentions rather than optimization guidance
   - **Recommendation**: Enhance the AI Visibility Agent to include crawler detection status and GEO recommendations

8. **Image optimization analysis**
   - Claude-SEO checks alt text, file size, and format
   - Authoricy doesn't analyze images
   - **Recommendation**: Low-effort addition to the technical audit. Could use top_pages data to check image optimization

### Lower Priority

9. **Industry-specific plan templates**
   - Claude-SEO offers pre-built roadmaps for SaaS, local, ecommerce, publisher, and agency sites
   - Authoricy's strategy builder is more flexible but less templated
   - **Recommendation**: Add optional industry templates as starting points for the Strategy Builder

10. **Better documentation structure**
    - Claude-SEO has dedicated docs for architecture, commands, installation, and MCP integration
    - Authoricy has extensive spec docs but they're planning documents, not user documentation
    - **Recommendation**: Convert planning docs into user-facing documentation as the product matures

11. **Security hardening patterns**
    - Claude-SEO explicitly addresses SSRF prevention, path traversal, and output sanitization
    - Authoricy has basic validation but no explicit security hardening
    - **Recommendation**: Audit for SSRF risks in the data collection pipeline, especially in the Firecrawl and Perplexity integrations

---

## 6. What Claude-SEO Could Learn from Authoricy

For completeness, here's what Claude-SEO lacks that Authoricy demonstrates well:

1. **Data-driven analysis** - Authoricy's 60-endpoint DataForSEO integration provides quantitative depth that crawling alone cannot match
2. **Quality gates** - The 25-check quality system with auto-retry ensures consistent output quality
3. **Multi-agent specialization** - 9 specialized agents vs 6 provides more granular analysis
4. **Persistence and history** - Database storage enables trend analysis and report comparison
5. **Greenfield intelligence** - Competitor-first analysis for new domains is innovative
6. **Custom scoring algorithms** - Winnability, opportunity, and difficulty scoring are proprietary differentiators
7. **Context intelligence** - Business profiling and market detection enable goal-aligned recommendations
8. **Automated delivery pipeline** - End-to-end from request to PDF to email

---

## 7. Summary

| Aspect | Winner | Why |
|--------|--------|-----|
| Data depth | Authoricy | 60 paid API endpoints vs free crawling |
| On-page analysis | Claude-SEO | Direct page crawling and visual analysis |
| Keyword intelligence | Authoricy | Full universe mapping, gaps, clustering |
| Technical SEO | Claude-SEO | Schema, sitemap, hreflang, image checks |
| Backlink analysis | Authoricy | Complete profile, gaps, velocity |
| AI/GEO optimization | Claude-SEO | Crawler detection, passage citability |
| Report generation | Authoricy | 40-60 page PDFs vs CLI output |
| Scalability | Authoricy | Database, auth, multi-tenant |
| Developer experience | Claude-SEO | Interactive CLI, 13 commands |
| Cost to user | Claude-SEO | Free vs $1.75-2.53/report |
| Community | Claude-SEO | 942 stars, MIT license |
| Quality assurance | Authoricy | 25-check quality gate system |
| Documentation | Claude-SEO | Structured user-facing docs |
| Security | Claude-SEO | Explicit SSRF/path traversal protection |

**Bottom line**: Authoricy is a deeper, more data-rich commercial platform. Claude-SEO is a more accessible, interactive developer tool. The biggest opportunity for Authoricy is to adopt Claude-SEO's on-page crawling, schema validation, and GEO optimization capabilities to complement its already strong data pipeline.

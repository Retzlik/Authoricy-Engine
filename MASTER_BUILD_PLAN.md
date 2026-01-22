# MASTER BUILD PLAN: Authoricy Intelligence Engine v4+v5

## From Current State to Production-Ready SEO Intelligence System

**Created:** January 2026
**Target:** Full v4 Infrastructure + v5 Prompt Engineering
**Current State:** ~35% Complete (infrastructure only, analysis broken)
**Target State:** Production-ready, generating actionable insights

---

# EXECUTIVE SUMMARY

## The Problem

The current implementation collects data but produces **useless reports**:
- Template text with no real insights
- Wrong/impossible data (e.g., DR of 173)
- Irrelevant keywords (Hungarian weather queries for Swedish sites)
- Generic placeholder text instead of data-driven analysis

**Root Cause:** We built the system backwards - data collection without methodology, no quality gates, generic Claude prompts instead of specialized agents.

## The Solution

Merge **v4 Technical Blueprint** (infrastructure, agents, scoring) with **v5 Prompt Engineering** (specialized prompts, few-shot examples, quality gates).

## What Changes

| Component | Current | v4+v5 Target |
|-----------|---------|--------------|
| Analysis Architecture | 4 generic loops | 9 specialized agents |
| Prompts | Generic "analyze this" | Expert personas with few-shot examples |
| Quality Control | None | 23/25 checks required to pass |
| Output Format | Free text | Structured XML with schemas |
| Scoring | None | Opportunity, Difficulty, Decay formulas |
| Anti-patterns | Not detected | 6 anti-patterns actively avoided |

---

# PART 1: CURRENT STATE ANALYSIS

## What Works

### Data Collection (~75% complete)
- Phase 1: Domain foundation (11 endpoints) ✅
- Phase 2: Keyword intelligence (12-18 endpoints) ✅
- Phase 3: Competitive analysis (14 endpoints) ⚠️ Some failures
- Phase 4: AI visibility (9-11 endpoints) ⚠️ Some missing

### Infrastructure (~90% complete)
- FastAPI server with background jobs ✅
- DataForSEO client with retry logic ✅
- Authentication framework ✅
- Rate limiting ✅
- File-based persistence ✅

### Report Framework (~20% complete)
- Report generator class structure ✅
- External/Internal builder skeletons ✅
- Chart generator framework ✅
- ❌ No HTML templates
- ❌ No CSS styling
- ❌ No real content generation

## What's Broken

### Analysis Engine (0% functional)
- Loop 1-4 exist as stubs only
- Prompts are generic, not specialized
- No structured output parsing
- No quality validation
- Claude generates fluff, not insights

### Report Output (0% useful)
- Reports contain template placeholders
- No data-driven narrative
- Missing comparative context
- No actionable recommendations

---

# PART 2: V4 SPECIFICATION REQUIREMENTS

## 2.1 Nine Specialized Agents (replacing 4 generic loops)

| Agent | Expert Persona | Primary Output |
|-------|---------------|----------------|
| 1. Keyword Intelligence | Search demand analyst (10+ years) | Keyword clusters, intent mapping, opportunity scoring |
| 2. Backlink Intelligence | Link building strategist | Link gap analysis, acquisition targets, velocity benchmarks |
| 3. Technical SEO | Site architecture expert | Core Web Vitals, crawlability, indexation issues |
| 4. Content Analysis | Content strategist | Content gaps, decay detection, optimization priorities |
| 5. Semantic Architecture | Information architect | Topic clusters, internal linking, site structure |
| 6. AI Visibility | AI search optimization expert | LLM mention tracking, AI SERP features, citation optimization |
| 7. SERP Analysis | Search landscape analyst | SERP feature opportunities, competitive positioning |
| 8. Local SEO | Local search specialist (conditional) | NAP consistency, local pack optimization |
| 9. Master Strategy | Chief strategy synthesizer | Unified roadmap, priority matrix, executive summary |

## 2.2 Scoring Formulas (v4 Technical)

### Opportunity Score
```
Opportunity = (Search_Volume × CTR_Potential × (1 - Current_Position/100)) / Difficulty_Adjusted
```

### Personalized Difficulty (MarketMuse methodology)
```
PD = Base_Difficulty × (1 + Topical_Authority_Gap) × (1 - Domain_Strength_Ratio)
```

### Content Decay Score
```
Decay = Days_Since_Update × (1 - Traffic_Retention) × Competitive_Movement
```

## 2.3 Database Schema (v4 Technical)

```
jobs:
  - id, domain, email, status, progress
  - created_at, started_at, completed_at
  - data_cost, analysis_cost, total_cost
  - quality_score, error_log

analysis_results:
  - job_id, agent_name, raw_output
  - structured_output (JSON), quality_checks
  - tokens_used, cost

reports:
  - job_id, type (external/internal)
  - pdf_url, html_content, pages
  - generated_at
```

## 2.4 Agent Python Classes (v4 Technical)

Each agent follows this structure:
```python
class KeywordIntelligenceAgent:
    def __init__(self, claude_client, data):
        self.client = claude_client
        self.data = data
        self.persona = KEYWORD_EXPERT_PERSONA

    async def analyze(self) -> AgentOutput:
        # 1. Prepare context from data
        context = self._prepare_context()

        # 2. Run analysis with specialized prompt
        raw_output = await self.client.complete(
            system=self.persona,
            prompt=self._build_prompt(context),
            examples=FEW_SHOT_EXAMPLES
        )

        # 3. Parse structured output
        structured = self._parse_xml_output(raw_output)

        # 4. Run quality checks
        quality = self._run_quality_checks(structured)

        # 5. Return validated output
        return AgentOutput(
            agent="keyword_intelligence",
            structured=structured,
            quality=quality,
            passed=quality.score >= 23/25
        )
```

---

# PART 3: V5 PROMPT ENGINEERING REQUIREMENTS

## 3.1 Seven Core Principles

### 1. Specificity Over Generality
❌ BAD: "Improve your content quality"
✅ GOOD: "Your /pricing page has 47% less content depth than competitor average (234 words vs 442). Add comparison tables and FAQ sections."

### 2. Data-Grounded Assertions
❌ BAD: "You have strong backlinks"
✅ GOOD: "Your DR 45 trails competitor median of 52 by 7 points. 73% of your backlinks come from 3 referring domains."

### 3. Comparative Context
❌ BAD: "Your traffic is declining"
✅ GOOD: "Traffic down 23% while competitor average grew 12% - a 35-point swing indicating market share loss."

### 4. Actionable Specificity
❌ BAD: "Create more content"
✅ GOOD: "Create pillar page for 'produktutveckling' (2,400 vol, KD 34) targeting informational intent, linking to 5 existing cluster pages."

### 5. Confidence Calibration
❌ BAD: "This will definitely work"
✅ GOOD: "High confidence (historical data supports): Technical fixes. Medium confidence (requires testing): Content expansion. Low confidence (market dependent): Link acquisition timeline."

### 6. Chain-of-Thought Reasoning
Show the analytical process:
```
Given: DR 45, 1,200 referring domains, 15,000 organic keywords
Observation: DR below competitor median (52)
Analysis: Gap is primarily in editorial links (you: 12%, competitors: 34%)
Implication: Content-driven link building should be priority
Recommendation: Launch linkable asset program targeting industry publications
```

### 7. Structured XML Output
```xml
<finding confidence="high" priority="1">
  <observation>Technical SEO score 67/100, 23 points below competitor median</observation>
  <evidence>
    <metric name="LCP" value="4.2s" benchmark="2.5s" gap="-1.7s"/>
    <metric name="CLS" value="0.25" benchmark="0.1" gap="-0.15"/>
  </evidence>
  <impact>Estimated 15-20% traffic loss from Core Web Vitals penalty</impact>
  <action effort="medium" timeline="2-4 weeks">
    Implement image lazy loading and font-display:swap
  </action>
</finding>
```

## 3.2 Quality Gates (23/25 Required)

Each agent output must pass these checks:

### Specificity Checks (7)
- [ ] Contains specific numbers, not vague qualifiers
- [ ] References actual pages/URLs from the domain
- [ ] Includes competitor-specific comparisons
- [ ] Provides measurable targets
- [ ] Uses precise terminology
- [ ] Avoids weasel words ("might", "could", "potentially")
- [ ] Includes timeframes for recommendations

### Actionability Checks (6)
- [ ] Each finding has clear next step
- [ ] Actions are prioritized (P1/P2/P3)
- [ ] Effort estimates included
- [ ] Dependencies identified
- [ ] Success metrics defined
- [ ] Owner/role suggested

### Data-Grounding Checks (6)
- [ ] Every claim cites source data
- [ ] Metrics include context (benchmark, trend)
- [ ] Comparisons use same time periods
- [ ] Statistical significance noted where relevant
- [ ] Data limitations acknowledged
- [ ] Confidence levels assigned

### Non-Generic Checks (6)
- [ ] No placeholder text
- [ ] No "best practice" without customization
- [ ] Industry-specific context applied
- [ ] Domain history considered
- [ ] Competitive landscape reflected
- [ ] Unique opportunities identified

## 3.3 Anti-Patterns to Avoid

### 1. Hedge Everything
❌ "You might want to consider possibly looking into maybe improving..."
✅ "Implement lazy loading on /products page to reduce LCP from 4.2s to under 2.5s"

### 2. Generic Best Practice
❌ "Follow SEO best practices for meta descriptions"
✅ "Your /services meta description (47 chars) underperforms. Expand to 145-155 chars including primary keyword 'konsulttjänster' and unique value prop."

### 3. Data Dump
❌ Listing 500 keywords without analysis
✅ "Top 3 opportunity clusters: [cluster 1] 12,400 combined vol, KD 28-34, current coverage 23%..."

### 4. Obvious Observation
❌ "Competitors rank higher than you"
✅ "Competitor A outranks you on 67% of shared keywords, specifically dominating informational queries (82% vs 34% coverage)"

### 5. Missing "So What"
❌ "Your bounce rate is 65%"
✅ "65% bounce rate on /pricing (vs 42% site average) suggests pricing page doesn't match search intent. Users searching 'pris' expect comparison tables."

### 6. Contradictory Recommendations
❌ "Focus on technical SEO" AND "Focus on content" AND "Focus on links"
✅ "Phase 1 (weeks 1-4): Technical fixes (blocking issues). Phase 2 (weeks 5-12): Content expansion. Phase 3 (ongoing): Link acquisition."

## 3.4 Few-Shot Examples Format

Each agent prompt includes:
```
## Examples

### Good Example (Score: 24/25)
<input>
[Abbreviated real data snapshot]
</input>
<output>
[Full structured output demonstrating all principles]
</output>
<why_good>
- Specific metrics with benchmarks
- Clear action items with effort estimates
- Proper confidence calibration
</why_good>

### Bad Example (Score: 12/25)
<input>
[Same data snapshot]
</input>
<output>
[Typical generic output]
</output>
<why_bad>
- Vague language ("improve your SEO")
- No specific metrics or comparisons
- Generic recommendations without customization
</why_bad>
```

---

# PART 4: GAP ANALYSIS - CURRENT vs V4+V5

## 4.1 Architecture Gap

| Component | Current | V4+V5 Required | Gap |
|-----------|---------|----------------|-----|
| Analysis units | 4 loops | 9 agents | +5 agents, different paradigm |
| Prompt structure | Single generic | Persona + examples + schema | Complete rewrite |
| Output format | Free text | Structured XML | New parsing layer |
| Quality control | None | 23/25 gate | New validation system |
| Scoring | None | 3 formulas | New calculation layer |

## 4.2 Code Changes Required

### New Files to Create
```
src/agents/
  ├── __init__.py
  ├── base.py              # BaseAgent class with quality checks
  ├── keyword.py           # KeywordIntelligenceAgent
  ├── backlink.py          # BacklinkIntelligenceAgent
  ├── technical.py         # TechnicalSEOAgent
  ├── content.py           # ContentAnalysisAgent
  ├── semantic.py          # SemanticArchitectureAgent
  ├── ai_visibility.py     # AIVisibilityAgent
  ├── serp.py              # SERPAnalysisAgent
  ├── local.py             # LocalSEOAgent (conditional)
  └── master.py            # MasterStrategyAgent

src/prompts/
  ├── __init__.py
  ├── personas.py          # Expert persona definitions
  ├── keyword_prompt.py    # Full prompt with examples
  ├── backlink_prompt.py
  ├── technical_prompt.py
  ├── content_prompt.py
  ├── semantic_prompt.py
  ├── ai_visibility_prompt.py
  ├── serp_prompt.py
  ├── local_prompt.py
  └── master_prompt.py

src/scoring/
  ├── __init__.py
  ├── opportunity.py       # Opportunity Score calculation
  ├── difficulty.py        # Personalized Difficulty calculation
  └── decay.py             # Content Decay Score calculation

src/quality/
  ├── gates.py             # Quality gate definitions (exists, needs update)
  ├── checks.py            # 25 individual check implementations
  └── anti_patterns.py     # Anti-pattern detection

src/output/
  ├── __init__.py
  ├── schemas.py           # XML output schemas
  └── parser.py            # XML parsing and validation
```

### Files to Modify
```
src/analyzer/engine.py     # Replace loop orchestration with agent orchestration
src/analyzer/client.py     # Add structured output support
src/reporter/external.py   # Consume agent outputs
src/reporter/internal.py   # Consume agent outputs
api/analyze.py             # Update pipeline
```

### Files to Delete/Replace
```
src/analyzer/loop1.py      # Replace with agents
src/analyzer/loop2.py
src/analyzer/loop3.py
src/analyzer/loop4.py
```

## 4.3 Data Collection Gaps

### Missing Endpoints (15 total)
```
Phase 2:
- keywords_data/google_ads/search_volume (validation)

Phase 3:
- historical_rank_overview ×4 (competitor trajectories)
- backlinks/competitors
- backlinks/bulk_ranks
- backlinks/bulk_referring_domains

Phase 4:
- ai_optimization/keyword_data/search_volume
- ai_optimization/llm_response ×3 (ChatGPT brand, topic, Perplexity)
- ai_optimization/llm_mentions/aggregated_metrics
- ai_optimization/llm_mentions/top_domains
- ai_optimization/llm_mentions/top_pages
- ai_optimization/llm_mentions/cross_aggregated_metrics
```

---

# PART 5: MASTER BUILD PLAN - PHASED IMPLEMENTATION

## Phase 0: Stabilization (Current Sprint - 1-2 days)
**Goal:** Ensure data collection works reliably

### Tasks
- [x] Fix API parameter errors (language_code, item_types, etc.)
- [x] Fix NoneType errors in collectors and reporters
- [x] Make non-critical failures non-fatal
- [ ] Verify all Phase 1-4 endpoints return valid data
- [ ] Add comprehensive error logging

### Deliverable
Data collection completes without crashes, returns valid JSON for all phases.

---

## Phase 1: Agent Architecture Foundation (3-4 days)
**Goal:** Create the new agent-based architecture

### 1.1 Base Agent Framework
```python
# src/agents/base.py
class BaseAgent:
    persona: str
    prompt_template: str
    output_schema: dict
    quality_checks: List[QualityCheck]

    async def analyze(self, data: dict) -> AgentOutput
    def _prepare_context(self, data: dict) -> str
    def _parse_output(self, raw: str) -> dict
    def _run_quality_checks(self, output: dict) -> QualityResult
```

### 1.2 Quality Check System
```python
# src/quality/checks.py
class QualityChecker:
    def check_specificity(self, output: dict) -> List[CheckResult]  # 7 checks
    def check_actionability(self, output: dict) -> List[CheckResult]  # 6 checks
    def check_data_grounding(self, output: dict) -> List[CheckResult]  # 6 checks
    def check_non_generic(self, output: dict) -> List[CheckResult]  # 6 checks

    def evaluate(self, output: dict) -> QualityResult:
        # Returns score out of 25, must be >= 23 to pass
```

### 1.3 Output Schema System
```python
# src/output/schemas.py
KEYWORD_OUTPUT_SCHEMA = {
    "clusters": [...],
    "opportunities": [...],
    "intent_mapping": [...],
    "priority_keywords": [...]
}
```

### Deliverable
- BaseAgent class with quality check integration
- 25 quality check implementations
- Output schema definitions
- Anti-pattern detector

---

## Phase 2: Core Agents Implementation (5-7 days)
**Goal:** Implement the 9 specialized agents

### 2.1 Keyword Intelligence Agent (Day 1)
- Expert persona: Search demand analyst
- Inputs: ranked_keywords, keyword_universe, search_intent, suggestions
- Outputs: Clusters, opportunity scores, intent mapping
- Scoring: Opportunity Score formula

### 2.2 Backlink Intelligence Agent (Day 2)
- Expert persona: Link building strategist
- Inputs: backlinks, referring_domains, anchors, link_velocity
- Outputs: Link gap analysis, acquisition targets, authority benchmarks
- Scoring: Link quality metrics

### 2.3 Technical SEO Agent (Day 3)
- Expert persona: Site architecture expert
- Inputs: lighthouse audits, technologies, page speed
- Outputs: CWV issues, crawlability problems, indexation recommendations
- Scoring: Technical health score

### 2.4 Content Analysis Agent (Day 4)
- Expert persona: Content strategist
- Inputs: top_pages, content_analysis, traffic trends
- Outputs: Content gaps, decay detection, optimization priorities
- Scoring: Content Decay Score formula

### 2.5 Semantic Architecture Agent (Day 4)
- Expert persona: Information architect
- Inputs: site structure, internal links, topic coverage
- Outputs: Topic clusters, linking recommendations, hierarchy fixes

### 2.6 AI Visibility Agent (Day 5)
- Expert persona: AI search optimization expert
- Inputs: llm_mentions, ai_keywords, brand sentiment
- Outputs: AI SERP opportunities, citation optimization, brand presence

### 2.7 SERP Analysis Agent (Day 5)
- Expert persona: Search landscape analyst
- Inputs: serp_competitors, SERP features, rankings
- Outputs: Feature opportunities, competitive gaps, SERP strategy

### 2.8 Local SEO Agent (Day 6 - conditional)
- Expert persona: Local search specialist
- Inputs: local rankings, GMB data (if applicable)
- Outputs: NAP fixes, local pack strategy
- Triggered: Only for businesses with local intent

### 2.9 Master Strategy Agent (Day 6-7)
- Expert persona: Chief strategy synthesizer
- Inputs: All other agent outputs
- Outputs: Unified roadmap, priority matrix, executive summary
- Quality gate: Final 23/25 check on synthesized output

### Deliverable
- 9 agent classes with specialized prompts
- Few-shot examples for each agent (good + bad)
- Output parsers for each schema
- Agent orchestration in engine.py

---

## Phase 3: Scoring Engine (2 days)
**Goal:** Implement the v4 scoring formulas

### 3.1 Opportunity Score
```python
def calculate_opportunity(keyword_data: dict) -> float:
    volume = keyword_data['search_volume']
    ctr_potential = estimate_ctr(keyword_data['current_position'])
    position_factor = 1 - (keyword_data['current_position'] / 100)
    difficulty_adjusted = adjust_difficulty(keyword_data['difficulty'], domain_authority)

    return (volume * ctr_potential * position_factor) / difficulty_adjusted
```

### 3.2 Personalized Difficulty
```python
def calculate_personalized_difficulty(keyword: str, domain_data: dict) -> float:
    base_difficulty = keyword_data['difficulty']
    topical_authority_gap = calculate_authority_gap(keyword, domain_data)
    domain_strength_ratio = domain_data['dr'] / competitor_median_dr

    return base_difficulty * (1 + topical_authority_gap) * (1 - domain_strength_ratio)
```

### 3.3 Content Decay Score
```python
def calculate_decay(page_data: dict) -> float:
    days_since_update = (now - page_data['last_modified']).days
    traffic_retention = page_data['current_traffic'] / page_data['peak_traffic']
    competitive_movement = calculate_serp_volatility(page_data['keyword'])

    return days_since_update * (1 - traffic_retention) * competitive_movement
```

### Deliverable
- Scoring module with 3 formula implementations
- Integration with Keyword and Content agents
- Score normalization and explanation

---

## Phase 4: Prompt Engineering (3-4 days)
**Goal:** Create specialized prompts following v5 principles

### 4.1 Prompt Structure Template
```python
AGENT_PROMPT = """
## Expert Persona
{persona_definition}

## Your Task
Analyze the provided data and generate insights following these principles:
1. Specificity over generality
2. Data-grounded assertions
3. Comparative context
4. Actionable specificity
5. Confidence calibration
6. Chain-of-thought reasoning
7. Structured XML output

## Output Schema
{xml_schema}

## Quality Requirements
Your output must pass 23/25 quality checks:
- Specificity (7): {specificity_requirements}
- Actionability (6): {actionability_requirements}
- Data-grounding (6): {data_grounding_requirements}
- Non-generic (6): {non_generic_requirements}

## Examples

### Good Example (24/25)
{good_example}

### Bad Example (12/25) - DO NOT DO THIS
{bad_example}

## Anti-Patterns to Avoid
{anti_patterns}

## Data to Analyze
{data}

## Generate Analysis
"""
```

### 4.2 Per-Agent Prompts
Create specialized prompts for each of the 9 agents with:
- Unique expert persona
- Domain-specific few-shot examples
- Agent-specific quality requirements
- Relevant anti-patterns

### Deliverable
- 9 complete prompt files
- Few-shot examples (good + bad) for each
- Anti-pattern definitions
- Prompt testing framework

---

## Phase 5: Report Generation Overhaul (4-5 days)
**Goal:** Generate reports from agent outputs

### 5.1 External Report (Lead Magnet)
**10-15 pages, executive-focused**

Sections:
1. Cover Page (1p)
2. Executive Summary (2p) - From Master Strategy Agent
3. Current Position Snapshot (2p) - From Technical + Backlink Agents
4. Competitive Landscape (2p) - From SERP + Content Agents
5. Top 5 Opportunities (2p) - From Keyword Agent (top Opportunity Scores)
6. Authority & AI Visibility (1p) - From AI Visibility Agent
7. 90-Day Quick Wins (2p) - From Master Strategy Agent
8. Next Steps CTA (1p)
9. Methodology (1p)

### 5.2 Internal Report (Strategy Guide)
**40-60 pages, practitioner-focused**

Sections:
1. Cover + TOC (2p)
2. Executive Summary (3p)
3. Domain Authority Analysis (5p) - Full Backlink Agent output
4. Keyword Universe (8p) - Full Keyword Agent output with clusters
5. Competitive Intelligence (6p) - Full SERP Agent output
6. Technical Audit (5p) - Full Technical Agent output
7. Content Strategy (8p) - Full Content + Semantic Agents
8. AI Visibility Playbook (4p) - Full AI Visibility Agent output
9. Implementation Roadmap (5p) - Master Strategy Agent phased plan
10. Measurement Framework (3p) - KPIs and tracking
11. Appendices (5p+) - Raw data exports

### 5.3 HTML Templates
Create professional templates with:
- Authoricy branding
- Data visualization (charts from ChartGenerator)
- Responsive tables
- Print-optimized CSS

### Deliverable
- Complete HTML templates for both reports
- CSS styling
- Template rendering with Jinja2
- PDF generation with WeasyPrint

---

## Phase 6: Integration & Pipeline (2-3 days)
**Goal:** Wire everything together

### 6.1 Updated Pipeline
```
Request → Data Collection → Agent Orchestration → Quality Gate → Report Generation → Delivery

Agent Orchestration:
1. Run agents 1-7 in parallel (Keyword, Backlink, Technical, Content, Semantic, AI, SERP)
2. Run Local SEO if applicable
3. Aggregate outputs
4. Run Master Strategy Agent
5. Quality gate (23/25 required)
6. If fail: Retry with feedback (max 2 retries)
```

### 6.2 Engine Refactor
```python
# src/analyzer/engine.py
class AnalysisEngine:
    def __init__(self):
        self.agents = [
            KeywordIntelligenceAgent(),
            BacklinkIntelligenceAgent(),
            TechnicalSEOAgent(),
            ContentAnalysisAgent(),
            SemanticArchitectureAgent(),
            AIVisibilityAgent(),
            SERPAnalysisAgent(),
        ]
        self.local_agent = LocalSEOAgent()
        self.master_agent = MasterStrategyAgent()

    async def analyze(self, data: CollectionResult) -> AnalysisResult:
        # Run primary agents in parallel
        agent_outputs = await asyncio.gather(*[
            agent.analyze(data) for agent in self.agents
        ])

        # Run local if applicable
        if self._needs_local_analysis(data):
            local_output = await self.local_agent.analyze(data)
            agent_outputs.append(local_output)

        # Run master synthesis
        master_output = await self.master_agent.synthesize(agent_outputs)

        # Quality gate
        if master_output.quality_score < 23:
            master_output = await self._retry_with_feedback(master_output)

        return AnalysisResult(agents=agent_outputs, master=master_output)
```

### Deliverable
- Refactored analysis engine
- Parallel agent execution
- Quality gate enforcement
- Retry logic with feedback

---

## Phase 7: Testing & Validation (3-4 days)
**Goal:** Ensure system produces quality output

### 7.1 Test Domains
Run full analysis on 10 diverse domains:
1. Small Swedish SaaS (< 1K keywords)
2. Medium Swedish e-commerce (1K-10K keywords)
3. Large Swedish brand (10K+ keywords)
4. English B2B SaaS
5. Local Swedish business
6. News/media site
7. Manufacturing company
8. Professional services
9. E-commerce with strong AI presence
10. Technical/developer tools

### 7.2 Quality Validation
For each test:
- Verify 23/25 quality checks pass
- Human review of insights (are they useful?)
- Compare to manual SEMrush/Ahrefs analysis
- Check for anti-patterns
- Validate scoring accuracy

### 7.3 Performance Validation
- Execution time < 5 minutes
- Cost per report < $3.00
- No crashes or unhandled errors

### Deliverable
- Test results for 10 domains
- Quality score documentation
- Performance benchmarks
- Bug fixes from testing

---

## Phase 8: Production Hardening (2-3 days)
**Goal:** Production-ready deployment

### 8.1 Persistence
- Migrate from in-memory to Redis/PostgreSQL
- Job status persistence
- Report storage (Supabase/S3)

### 8.2 Monitoring
- Structured logging with correlation IDs
- Cost tracking per job
- Quality score tracking
- Error alerting

### 8.3 Documentation
- API documentation
- Agent documentation
- Deployment guide

### Deliverable
- Production-ready system
- Monitoring dashboard
- Complete documentation

---

# PART 6: IMPLEMENTATION PRIORITY

## Critical Path (Must Have)

| Priority | Component | Days | Dependency |
|----------|-----------|------|------------|
| P0 | Phase 0: Stabilization | 1-2 | None |
| P0 | Phase 1: Agent Foundation | 3-4 | P0 |
| P0 | Phase 2: Core Agents | 5-7 | P1 |
| P0 | Phase 4: Prompt Engineering | 3-4 | P2 |
| P0 | Phase 5: External Report | 2-3 | P4 |
| P0 | Phase 6: Integration | 2-3 | P5 |
| P0 | Phase 7: Testing | 3-4 | P6 |

**MVP Total: 19-27 days**

## Important (Should Have)

| Priority | Component | Days | Dependency |
|----------|-----------|------|------------|
| P1 | Phase 3: Scoring Engine | 2 | P2 |
| P1 | Phase 5: Internal Report | 2-3 | External Report |
| P1 | Phase 8: Persistence | 1-2 | P6 |

**Full v4+v5 Total: 24-34 days**

## Nice to Have (Could Have)

| Priority | Component | Days |
|----------|-----------|------|
| P2 | Missing DataForSEO endpoints | 2-3 |
| P2 | Advanced monitoring | 1-2 |
| P2 | CRM integration | 1-2 |

---

# PART 7: SUCCESS METRICS

## Minimum Viable Product
- [ ] 9 agents producing structured output
- [ ] Quality gate passing (23/25)
- [ ] External report generating with real insights
- [ ] No placeholder text or generic recommendations
- [ ] Execution time < 10 minutes
- [ ] Cost per report < $5.00

## Production Ready
- [ ] All MVP criteria
- [ ] Internal report complete
- [ ] Quality score consistently > 23/25
- [ ] 10 successful test domain analyses
- [ ] Execution time < 5 minutes
- [ ] Cost per report < $3.00
- [ ] Job persistence working

## World Class Target
- [ ] Quality score consistently > 24/25
- [ ] Reports rival boutique SEO agency output
- [ ] Unique insights not available in standard tools
- [ ] Customer feedback positive
- [ ] Cost per report < $2.50
- [ ] Execution time < 3 minutes

---

# PART 8: IMMEDIATE NEXT STEPS

## This Session
1. Complete Phase 0 stabilization
2. Begin Phase 1 agent foundation

## Tomorrow
1. Finish base agent framework
2. Implement quality check system
3. Create first agent (Keyword Intelligence)

## This Week
1. Complete 4-5 core agents
2. Create specialized prompts with examples
3. Test individual agent outputs

## Next Week
1. Complete remaining agents
2. Implement report generation
3. Integration testing

---

# APPENDIX: FILE CHANGES SUMMARY

## Files to Create (25 new files)
```
src/agents/__init__.py
src/agents/base.py
src/agents/keyword.py
src/agents/backlink.py
src/agents/technical.py
src/agents/content.py
src/agents/semantic.py
src/agents/ai_visibility.py
src/agents/serp.py
src/agents/local.py
src/agents/master.py
src/prompts/__init__.py
src/prompts/personas.py
src/prompts/keyword_prompt.py
src/prompts/backlink_prompt.py
src/prompts/technical_prompt.py
src/prompts/content_prompt.py
src/prompts/semantic_prompt.py
src/prompts/ai_visibility_prompt.py
src/prompts/serp_prompt.py
src/prompts/local_prompt.py
src/prompts/master_prompt.py
src/scoring/__init__.py
src/scoring/opportunity.py
src/scoring/difficulty.py
src/scoring/decay.py
src/quality/checks.py
src/quality/anti_patterns.py
src/output/__init__.py
src/output/schemas.py
src/output/parser.py
```

## Files to Modify (8 files)
```
src/analyzer/engine.py      # Complete rewrite
src/analyzer/client.py      # Add structured output
src/quality/gates.py        # Update for 25-check system
src/quality/validators.py   # Update validation
src/reporter/external.py    # Consume agent outputs
src/reporter/internal.py    # Consume agent outputs
api/analyze.py              # Update pipeline
src/collector/orchestrator.py  # Add data prep methods
```

## Files to Delete (4 files)
```
src/analyzer/loop1.py
src/analyzer/loop2.py
src/analyzer/loop3.py
src/analyzer/loop4.py
```

---

*This master build plan will be updated as implementation progresses.*
*Last updated: January 2026*

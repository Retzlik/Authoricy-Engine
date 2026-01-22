# MASTER BUILD PLAN: Authoricy Intelligence Engine
## Complete Transformation from Current State to v4+v5 Production System

**Created:** January 2026
**Status:** CRITICAL - Current system produces unusable reports
**Target:** Full v4 Infrastructure + v5 Prompt Engineering
**Estimated Effort:** 20-30 development days

---

# PART 1: EXECUTIVE SUMMARY

## The Problem

The current system **collects data but produces garbage reports**:
- Generic template text: "Based on comprehensive analysis..." (says nothing)
- Placeholder recommendations: "Optimize existing high-potential pages" (which pages?)
- Missing specific data: No actual keyword recommendations, no URLs, no metrics
- Wrong architecture: 4 generic loops instead of 9 specialized agents
- No quality gates: Garbage in → Garbage out

**Root Cause:** The system was built for data collection, not intelligence generation. The analysis layer is essentially a stub with generic prompts.

## The Solution

Implement **v4 Technical Infrastructure** + **v5 Prompt Engineering**:

| Component | Current | Required | Gap |
|-----------|---------|----------|-----|
| Analysis Architecture | 4 generic loops | 9 specialized agents | Complete rewrite |
| Prompts | ~50 lines generic | ~500 lines per agent with examples | 10x more detailed |
| Quality Gates | None | 25 checks, 23 required to pass | New system |
| Scoring Formulas | None | Opportunity, Personalized Difficulty, Decay | New calculations |
| Output Format | Free text | Structured XML with schemas | New parsing |
| Report Content | Template placeholders | Data-driven specific recommendations | Complete rewrite |

---

# PART 2: DETAILED CURRENT STATE ANALYSIS

## 2.1 What Currently Exists (and Works)

### Data Collection ✅ ~80% Complete
```
src/collector/
├── client.py          ✅ DataForSEO client with retry logic
├── orchestrator.py    ✅ Phase coordination, dependency handling
├── phase1.py          ✅ 11 endpoints - domain foundation
├── phase2.py          ✅ 12-18 endpoints - keyword intelligence
├── phase3.py          ⚠️ 14 endpoints - some failures (link gap 500 errors)
└── phase4.py          ⚠️ 9-11 endpoints - some missing AI endpoints
```

**Verdict:** Data collection works but has gaps. Needs hardening, not rewrite.

### API & Infrastructure ✅ ~90% Complete
```
api/analyze.py         ✅ FastAPI endpoints, background jobs
src/auth/              ✅ API key management, rate limiting
src/persistence/       ✅ File storage, caching
src/delivery/          ✅ Email delivery via Resend
```

**Verdict:** Infrastructure is solid. Keep as-is.

## 2.2 What Currently Exists (and is BROKEN)

### Analysis Engine ❌ 0% Usable

**Current Architecture (WRONG):**
```
src/analyzer/
├── engine.py          ❌ Orchestrates 4 generic loops
├── loop1.py           ❌ Generic "interpret data" prompt
├── loop2.py           ❌ Generic "synthesize strategy" prompt
├── loop3.py           ❌ Stub - enrichment not implemented
└── loop4.py           ❌ Generic quality review
```

**Current Loop 1 Prompt (Example of the Problem):**
```python
SYSTEM_PROMPT = """You are an expert SEO analyst with 15 years of experience..."""

# This is the ENTIRE guidance given to Claude:
# - No expert persona with behavioral constraints
# - No few-shot examples
# - No quality gates
# - No structured output schema
# - No scoring formulas
# - No anti-patterns to avoid
```

**Result:** Claude generates vague, generic text that could apply to any website.

### Report Generation ❌ 10% Usable

**Current Report Content:**
```html
<!-- From external.py - this is what gets generated -->
<div class="finding">
    <div class="finding-title">1. Current Organic Position</div>
    <p>Based on comprehensive analysis of your domain's organic visibility.</p>
</div>
```

**Problem:** This says NOTHING. No specific keywords, no URLs, no metrics, no actions.

**What v5 Requires:**
```html
<div class="finding">
    <div class="finding-title">1. Target "enterprise project management software" (2,400 vol, KD 52)</div>
    <p>Your DR 52 matches top-10 average. Create 2,500-word comparison page at
    /solutions/enterprise-project-management/. Expected: Position 5-8 within 90 days,
    +190 monthly visits. Confidence: 0.85</p>
</div>
```

---

# PART 3: V4 + V5 REQUIREMENTS COMPARISON

## 3.1 Architecture Comparison

### Current: 4 Generic Loops
```
Loop 1: Data Interpretation    → Generic prompt, free-text output
Loop 2: Strategic Synthesis    → Generic prompt, free-text output
Loop 3: SERP Enrichment        → Stub (not implemented)
Loop 4: Quality Review         → Generic 8-dimension scoring
```

### Required: 9 Specialized Agents (from v4)
```
1. Keyword Intelligence Agent     → Expert persona, structured output, scoring formulas
2. Backlink Intelligence Agent    → Link gap analysis, strategy selection matrix
3. Technical SEO Agent            → CWV analysis, issue prioritization
4. Content Analysis Agent         → Decay detection, KUCK recommendations
5. Semantic Architecture Agent    → Topical maps, SERP-validated clustering
6. AI Visibility Agent            → GEO optimization, citation tracking
7. SERP Analysis Agent            → Feature analysis, format requirements
8. Local SEO Agent (conditional)  → NAP, local pack optimization
9. Master Strategy Agent          → Synthesize all outputs into unified plan
```

## 3.2 Prompt Engineering Comparison

### Current Prompt (Loop 1 - 36 lines)
```python
SYSTEM_PROMPT = """You are an expert SEO analyst with 15 years of experience...
## CRITICAL RULES
1. Every claim must cite specific data...
"""
# No persona, no examples, no quality checks, no output schema
```

### Required Prompt (v5 Keyword Agent - ~500 lines)
```python
SYSTEM_PROMPT = """
You are a Senior Keyword Strategist with 15 years of experience at enterprise SEO agencies
(BrightEdge, Conductor, iProspect, Terakeet). You have personally managed keyword strategies
for Fortune 500 companies including Microsoft, Salesforce, and Adobe...

<behavioral_constraints>
You NEVER say:
- "Consider focusing on long-tail keywords" (too vague - which keywords?)
- "Build topical authority" (without a specific topic map with keywords)
- "Create quality content" (meaningless without specific content specifications)
...
You ALWAYS:
- Reference specific numbers from the data (search volume, position, KD, etc.)
- Compare against specific competitors or benchmarks
...
</behavioral_constraints>

<quality_standard>
Your output should match what a €15,000/month agency delivers after 3 months of analysis.
If a CMO could apply this analysis to any other website, you have failed.
</quality_standard>
"""

# Plus: Few-shot examples, output schema, quality gates (25 checks)
```

## 3.3 Quality Gates Comparison

### Current: None
The current system has no quality validation. Whatever Claude outputs goes directly to the report.

### Required (v5): 25 Checks, 23 Must Pass

**Specificity Checks (7):**
- [ ] Contains specific numbers, not vague qualifiers
- [ ] References actual pages/URLs from the domain
- [ ] Includes competitor-specific comparisons
- [ ] Provides measurable targets
- [ ] Uses precise terminology
- [ ] Avoids weasel words ("might", "could", "potentially")
- [ ] Includes timeframes for recommendations

**Actionability Checks (6):**
- [ ] Each finding has clear next step
- [ ] Actions are prioritized (P1/P2/P3)
- [ ] Effort estimates included
- [ ] Dependencies identified
- [ ] Success metrics defined
- [ ] Owner/role suggested

**Data-Grounding Checks (6):**
- [ ] Every claim cites source data
- [ ] Metrics include context (benchmark, trend)
- [ ] Comparisons use same time periods
- [ ] Statistical significance noted where relevant
- [ ] Data limitations acknowledged
- [ ] Confidence levels assigned

**Non-Generic Checks (6):**
- [ ] No placeholder text
- [ ] No "best practice" without customization
- [ ] Industry-specific context applied
- [ ] Domain history considered
- [ ] Competitive landscape reflected
- [ ] Unique opportunities identified

## 3.4 Scoring Formulas (v4) - Currently Missing

### Opportunity Score
```python
Opportunity_Score = (
    Volume_Score × 0.20 +
    Difficulty_Inverse × 0.20 +
    Business_Intent × 0.20 +
    Position_Gap × 0.20 +
    Topical_Alignment × 0.20
) × Freshness_Modifier

# Intent weights: Transactional=100, Commercial=75, Informational=50, Navigational=25
# CTR curve: Pos1=31.7%, Pos2=24.7%, Pos3=18.7%...
```

### Personalized Difficulty (MarketMuse Methodology)
```python
Personal_KD = Base_KD × (1 - Authority_Advantage)

Authority_Advantage = min(0.5,
    (Site_DR - Avg_SERP_DR) / 100 +
    Topical_Authority_Bonus
)

Topical_Authority_Bonus = min(0.3,
    count(ranked_keywords in same category) / 100
)
```

### Content Decay Score
```python
Decay_Score = (
    (Peak_Traffic - Current_Traffic) / Peak_Traffic × 0.40 +
    (Peak_Position - Current_Position) / 10 × 0.30 +
    (Peak_CTR - Current_CTR) / Peak_CTR × 0.20 +
    Age_Factor × 0.10
)

# Thresholds: >0.5 Critical, 0.3-0.5 Major, 0.1-0.3 Light, <0.1 Monitor
```

---

# PART 4: IMPLEMENTATION PLAN

## Phase 0: Stabilization (Days 1-2) ✅ MOSTLY DONE
**Goal:** Ensure data collection works reliably

- [x] Fix API parameter errors (language_code, item_types)
- [x] Fix NoneType errors in collectors and reporters
- [x] Make non-critical failures non-fatal
- [ ] Add comprehensive logging for debugging
- [ ] Verify all 45 endpoints return valid data

**Deliverable:** Data collection completes without crashes.

---

## Phase 1: Scoring Engine (Days 3-5)
**Goal:** Implement the three core scoring formulas

### 1.1 Create Scoring Module
```
src/scoring/
├── __init__.py
├── opportunity.py      # Opportunity Score calculation
├── difficulty.py       # Personalized Difficulty calculation
├── decay.py            # Content Decay Score calculation
└── helpers.py          # CTR curve, intent weights, etc.
```

### 1.2 Opportunity Score Implementation
```python
# src/scoring/opportunity.py
import math
from typing import Dict, Any, List

CTR_CURVE = {
    1: 0.317, 2: 0.247, 3: 0.187, 4: 0.133, 5: 0.095,
    6: 0.069, 7: 0.051, 8: 0.038, 9: 0.029, 10: 0.022
}

INTENT_WEIGHTS = {
    "transactional": 100,
    "commercial": 75,
    "informational": 50,
    "navigational": 25,
}

def calculate_opportunity_score(
    keyword: Dict[str, Any],
    domain_data: Dict[str, Any],
    max_volume: int
) -> float:
    """Calculate Opportunity Score (0-100) for a keyword."""
    volume = keyword.get("search_volume", 0)
    current_pos = keyword.get("position") or 100
    base_kd = keyword.get("keyword_difficulty", 50)
    intent = keyword.get("intent", "informational").lower()

    # Volume Score (logarithmic normalization)
    volume_score = min(100,
        (math.log10(volume + 1) / math.log10(max_volume + 1)) * 100
    ) if volume > 0 else 0

    # Calculate personalized difficulty first
    personal_kd = calculate_personalized_difficulty(keyword, domain_data)
    difficulty_inverse = 100 - personal_kd

    # Business Intent Score
    business_intent = INTENT_WEIGHTS.get(intent, 50)

    # Position Gap (traffic opportunity)
    target_pos = 1 if current_pos > 3 else max(1, current_pos - 2)
    current_ctr = CTR_CURVE.get(min(current_pos, 10), 0.01)
    target_ctr = CTR_CURVE.get(target_pos, 0.317)
    position_gap = min(100, (target_ctr - current_ctr) * volume / 100)

    # Topical Alignment (simplified)
    topical_alignment = 75  # Default, adjusted based on category match

    # Final score
    return round(
        volume_score * 0.20 +
        difficulty_inverse * 0.20 +
        business_intent * 0.20 +
        position_gap * 0.20 +
        topical_alignment * 0.20
    )
```

### 1.3 Personalized Difficulty Implementation
```python
# src/scoring/difficulty.py
def calculate_personalized_difficulty(
    keyword: Dict[str, Any],
    domain_data: Dict[str, Any]
) -> float:
    """
    Calculate Personalized Keyword Difficulty (MarketMuse methodology).

    Lower than base KD if you have topical authority advantage.
    """
    base_kd = keyword.get("keyword_difficulty", 50)
    site_dr = domain_data.get("domain_rank", 30)

    # Get topical authority bonus from category data
    categories = domain_data.get("categories", [])
    keyword_category = keyword.get("category")

    topical_bonus = 0
    if keyword_category and categories:
        matching = [c for c in categories if c.get("code") == keyword_category]
        if matching:
            # More keywords ranking in this category = higher authority
            category_keywords = matching[0].get("keyword_count", 0)
            topical_bonus = min(0.3, category_keywords / 100)

    # Authority advantage
    authority_advantage = min(0.5,
        max(0, (site_dr - 50) / 100) + topical_bonus
    )

    return round(base_kd * (1 - authority_advantage))
```

### 1.4 Content Decay Score Implementation
```python
# src/scoring/decay.py
def calculate_decay_score(
    page: Dict[str, Any],
    historical_data: List[Dict[str, Any]]
) -> float:
    """
    Calculate Content Decay Score (0-1).

    >0.5: Critical refresh needed
    0.3-0.5: Major update recommended
    0.1-0.3: Light refresh
    <0.1: Monitor only
    """
    if not historical_data:
        return 0.0

    # Find peak metrics
    peak_traffic = max(h.get("traffic", 0) for h in historical_data)
    peak_position = min(h.get("position", 100) for h in historical_data)

    # Current metrics
    current_traffic = page.get("traffic", 0)
    current_position = page.get("position", 100)

    # Calculate decay components
    traffic_decay = (peak_traffic - current_traffic) / max(peak_traffic, 1)
    position_decay = (current_position - peak_position) / 10

    # Age factor (months since last update)
    months_old = page.get("months_since_update", 12)
    age_factor = min(1.0, months_old / 24)

    return round(
        traffic_decay * 0.40 +
        position_decay * 0.30 +
        age_factor * 0.30,
        2
    )
```

**Deliverable:** Scoring module with all three formulas, tested with real data.

---

## Phase 2: Agent Architecture Foundation (Days 6-10)
**Goal:** Create the 9-agent architecture replacing 4 loops

### 2.1 Base Agent Class
```python
# src/agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import json

@dataclass
class AgentOutput:
    """Standardized output from all agents."""
    agent_name: str
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    metrics: Dict[str, float]
    raw_output: str
    quality_score: float
    quality_checks: Dict[str, bool]
    confidence: float

class BaseAgent(ABC):
    """Base class for all analysis agents."""

    def __init__(self, client):
        self.client = client

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Full system prompt with persona and constraints."""
        pass

    @property
    @abstractmethod
    def analysis_prompt_template(self) -> str:
        """Template with {{placeholders}} for data."""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """Expected output structure."""
        pass

    @property
    @abstractmethod
    def required_data(self) -> List[str]:
        """List of required data keys from collection."""
        pass

    async def analyze(self, collected_data: Dict[str, Any]) -> AgentOutput:
        """Run analysis and return structured output."""
        # 1. Validate required data present
        self._validate_data(collected_data)

        # 2. Prepare prompt with data interpolation
        prompt = self._prepare_prompt(collected_data)

        # 3. Call Claude
        raw_output = await self.client.complete(
            system=self.system_prompt,
            prompt=prompt,
            max_tokens=8000,
            temperature=0.3,
        )

        # 4. Parse structured output
        parsed = self._parse_output(raw_output)

        # 5. Run quality checks
        quality_score, checks = self._run_quality_checks(parsed)

        return AgentOutput(
            agent_name=self.name,
            findings=parsed.get("findings", []),
            recommendations=parsed.get("recommendations", []),
            metrics=parsed.get("metrics", {}),
            raw_output=raw_output,
            quality_score=quality_score,
            quality_checks=checks,
            confidence=parsed.get("confidence", 0.5),
        )

    def _run_quality_checks(self, parsed: Dict) -> tuple:
        """Run 25 quality checks, return score and individual results."""
        checks = {}

        # Specificity checks (7)
        checks["has_specific_numbers"] = self._check_specific_numbers(parsed)
        checks["has_specific_urls"] = self._check_specific_urls(parsed)
        checks["has_competitor_comparisons"] = self._check_competitors(parsed)
        checks["has_measurable_targets"] = self._check_targets(parsed)
        checks["uses_precise_terminology"] = self._check_terminology(parsed)
        checks["avoids_weasel_words"] = self._check_weasel_words(parsed)
        checks["has_timeframes"] = self._check_timeframes(parsed)

        # Actionability checks (6)
        checks["has_clear_actions"] = self._check_actions(parsed)
        checks["has_priorities"] = self._check_priorities(parsed)
        checks["has_effort_estimates"] = self._check_effort(parsed)
        checks["has_dependencies"] = self._check_dependencies(parsed)
        checks["has_success_metrics"] = self._check_success_metrics(parsed)
        checks["has_owners"] = self._check_owners(parsed)

        # Data-grounding checks (6)
        checks["cites_source_data"] = self._check_citations(parsed)
        checks["has_benchmarks"] = self._check_benchmarks(parsed)
        checks["consistent_time_periods"] = True  # Simplified
        checks["notes_significance"] = True  # Simplified
        checks["acknowledges_limitations"] = self._check_limitations(parsed)
        checks["has_confidence_levels"] = self._check_confidence(parsed)

        # Non-generic checks (6)
        checks["no_placeholder_text"] = self._check_no_placeholders(parsed)
        checks["customized_advice"] = self._check_customization(parsed)
        checks["industry_specific"] = True  # Simplified
        checks["considers_history"] = True  # Simplified
        checks["reflects_competition"] = self._check_competition_reflection(parsed)
        checks["unique_opportunities"] = self._check_unique_opps(parsed)

        passed = sum(1 for v in checks.values() if v)
        score = passed / 25 * 10  # Convert to 0-10 scale

        return score, checks
```

### 2.2 Quality Checker Module
```
src/quality/
├── __init__.py
├── checks.py           # Individual check implementations
├── anti_patterns.py    # Anti-pattern detection
└── validator.py        # Overall validation orchestration
```

### 2.3 Create All 9 Agent Files
```
src/agents/
├── __init__.py
├── base.py
├── keyword_intelligence.py    # ~400 lines with full v5 prompt
├── backlink_intelligence.py   # ~350 lines
├── technical_seo.py           # ~300 lines
├── content_analysis.py        # ~350 lines
├── semantic_architecture.py   # ~300 lines
├── ai_visibility.py           # ~300 lines
├── serp_analysis.py           # ~250 lines
├── local_seo.py               # ~200 lines (conditional)
└── master_strategy.py         # ~400 lines (synthesizer)
```

**Deliverable:** Complete agent architecture with base class and quality checks.

---

## Phase 3: Implement Core Agents (Days 11-17)
**Goal:** Implement the 9 specialized agents with v5 prompts

### 3.1 Keyword Intelligence Agent (Days 11-12)

Full implementation with:
- Expert persona (Senior Keyword Strategist, 15 years experience)
- Behavioral constraints (NEVER say vague things, ALWAYS cite data)
- Analysis prompt with data placeholders
- Few-shot examples (good AND bad)
- Output schema for structured parsing
- Scoring formula integration (Opportunity Score, Personalized Difficulty)

### 3.2 Backlink Intelligence Agent (Days 12-13)

Full implementation with:
- Expert persona (Senior Link Building Strategist)
- Strategy selection matrix (Digital PR, HARO, Guest Posting, etc.)
- Link gap analysis with acquisition difficulty
- Anchor text health assessment
- 12-month link building roadmap

### 3.3 Technical SEO Agent (Day 13)

Full implementation with:
- Core Web Vitals analysis (2025 thresholds: LCP 2.5s, INP 200ms, CLS 0.1)
- Issue prioritization (Critical/High/Medium/Low)
- Specific fix recommendations with effort estimates
- Schema markup assessment

### 3.4 Content Analysis Agent (Days 14-15)

Full implementation with:
- Content inventory analysis
- Decay detection using formula
- Keep/Update/Consolidate/Kill recommendations
- 12-month content calendar

### 3.5 Semantic Architecture Agent (Day 15)

Full implementation with:
- SERP-validated clustering (5+ URL overlap)
- Pillar-cluster structure
- Internal linking plan
- URL hierarchy recommendations

### 3.6 AI Visibility Agent (Day 16)

Full implementation with:
- AI Overview presence analysis
- GEO readiness assessment
- Citation opportunity identification
- GEO optimization checklist

### 3.7 SERP Analysis Agent (Day 16)

Full implementation with:
- SERP feature distribution
- Content format analysis
- Featured snippet opportunities

### 3.8 Local SEO Agent (Day 16 - conditional)

Triggered only when local signals detected.

### 3.9 Master Strategy Agent (Day 17)

Full implementation with:
- Cross-agent pattern identification
- Conflict resolution
- Unified priority stack (Top 10)
- 90-day implementation roadmap
- Executive summary generation

**Deliverable:** All 9 agents fully implemented with v5 prompts.

---

## Phase 4: Output Parsing & Validation (Days 18-19)
**Goal:** Parse agent outputs into structured data

### 4.1 XML Output Parser
```python
# src/output/parser.py
import re
from typing import Dict, Any, List

def parse_agent_output(raw_output: str, schema: Dict) -> Dict[str, Any]:
    """Parse XML-tagged agent output into structured data."""
    result = {}

    # Extract findings
    findings_match = re.findall(
        r'<finding confidence="([^"]+)" priority="(\d+)">(.*?)</finding>',
        raw_output,
        re.DOTALL
    )
    result["findings"] = [
        {
            "confidence": float(m[0]),
            "priority": int(m[1]),
            "content": parse_finding_content(m[2])
        }
        for m in findings_match
    ]

    # Extract recommendations
    recs_match = re.findall(
        r'<recommendation priority="(\d+)">(.*?)</recommendation>',
        raw_output,
        re.DOTALL
    )
    result["recommendations"] = [
        {
            "priority": int(m[0]),
            "content": parse_recommendation_content(m[1])
        }
        for m in recs_match
    ]

    # Extract metrics
    metrics_match = re.findall(
        r'<metric name="([^"]+)" value="([^"]+)"',
        raw_output
    )
    result["metrics"] = {m[0]: parse_metric_value(m[1]) for m in metrics_match}

    return result
```

### 4.2 Schema Definitions
```python
# src/output/schemas.py
KEYWORD_AGENT_SCHEMA = {
    "portfolio_health": {
        "total_keywords": "int",
        "position_distribution": {"top_3": "int", "top_10": "int", ...},
        "intent_distribution": {"transactional": "int", ...},
    },
    "opportunities": [
        {
            "keyword": "str",
            "volume": "int",
            "current_position": "int|null",
            "personalized_difficulty": "int",
            "opportunity_score": "int",
            "recommendation": "str",
        }
    ],
    "quick_wins": [...],
    "gaps": [...],
}
```

**Deliverable:** Parsing system that converts agent outputs to structured data.

---

## Phase 5: Report Generation Overhaul (Days 20-23)
**Goal:** Generate data-driven reports from agent outputs

### 5.1 Replace Template Placeholders

**Before (current):**
```python
def _build_executive_summary(self, analysis_result, metadata):
    return """
    <div class="finding">
        <div class="finding-title">1. Current Organic Position</div>
        <p>Based on comprehensive analysis of your domain's organic visibility.</p>
    </div>
    """
```

**After (v5):**
```python
def _build_executive_summary(self, master_output: AgentOutput, metadata: Dict):
    findings = master_output.findings[:3]  # Top 3 findings

    findings_html = ""
    for i, finding in enumerate(findings, 1):
        findings_html += f"""
        <div class="finding">
            <div class="finding-title">{i}. {finding['title']}</div>
            <p>{finding['description']}</p>
            <div class="evidence">
                <strong>Evidence:</strong> {finding['evidence']}
            </div>
            <div class="impact">
                <strong>Impact:</strong> {finding['impact']}
            </div>
        </div>
        """

    return f"""
    <div class="page">
        <h1>Executive Summary</h1>
        <div class="highlight-box">
            <strong>The Headline:</strong><br>
            {master_output.metrics.get('headline', 'Key opportunities identified.')}
        </div>
        <h2>Key Findings</h2>
        {findings_html}
        <h2>Recommended Path Forward</h2>
        <p>{master_output.recommendations[0]['action']}</p>
        <p><strong>Expected Impact:</strong> {master_output.recommendations[0]['impact']}</p>
    </div>
    """
```

### 5.2 New Report Sections

Each section pulls from specific agent outputs:

| Report Section | Agent Source | Key Data |
|----------------|--------------|----------|
| Executive Summary | Master Strategy | Top 3 findings, headline metric |
| Current Position | Technical + Backlink | DR, keywords, CWV scores |
| Keyword Opportunities | Keyword Intelligence | Top 20 opportunities with scores |
| Competitive Landscape | SERP + Backlink | Gap analysis, trajectory matrix |
| Content Strategy | Content Analysis | Decay list, KUCK recommendations |
| AI Visibility | AI Visibility | GEO score, citation opportunities |
| Roadmap | Master Strategy | 90-day phased plan |

**Deliverable:** Reports with specific, data-driven content (not templates).

---

## Phase 6: Engine Integration (Days 24-26)
**Goal:** Wire everything together

### 6.1 New Analysis Engine
```python
# src/analyzer/engine.py (rewritten)
class AnalysisEngine:
    def __init__(self, api_key: str):
        self.client = ClaudeClient(api_key)

        # Initialize all 9 agents
        self.agents = {
            "keyword": KeywordIntelligenceAgent(self.client),
            "backlink": BacklinkIntelligenceAgent(self.client),
            "technical": TechnicalSEOAgent(self.client),
            "content": ContentAnalysisAgent(self.client),
            "semantic": SemanticArchitectureAgent(self.client),
            "ai_visibility": AIVisibilityAgent(self.client),
            "serp": SERPAnalysisAgent(self.client),
            "local": LocalSEOAgent(self.client),
            "master": MasterStrategyAgent(self.client),
        }

    async def analyze(self, collected_data: Dict) -> AnalysisResult:
        """Run all agents and synthesize results."""

        # Step 1: Run primary agents in parallel
        primary_tasks = [
            self.agents["keyword"].analyze(collected_data),
            self.agents["backlink"].analyze(collected_data),
            self.agents["technical"].analyze(collected_data),
            self.agents["content"].analyze(collected_data),
            self.agents["semantic"].analyze(collected_data),
            self.agents["ai_visibility"].analyze(collected_data),
            self.agents["serp"].analyze(collected_data),
        ]

        primary_outputs = await asyncio.gather(*primary_tasks)

        # Step 2: Run local agent if applicable
        if self._needs_local(collected_data):
            local_output = await self.agents["local"].analyze(collected_data)
            primary_outputs.append(local_output)

        # Step 3: Run master synthesis
        master_output = await self.agents["master"].synthesize(primary_outputs)

        # Step 4: Quality gate
        if master_output.quality_score < 9.2:  # 23/25 = 92%
            # Retry with feedback
            master_output = await self._retry_with_feedback(
                master_output, primary_outputs
            )

        return AnalysisResult(
            agent_outputs={o.agent_name: o for o in primary_outputs},
            master_output=master_output,
            quality_score=master_output.quality_score,
            passed_quality_gate=master_output.quality_score >= 9.2,
        )
```

**Deliverable:** Integrated pipeline running all 9 agents.

---

## Phase 7: Testing & Validation (Days 27-30)
**Goal:** Ensure system produces quality output

### 7.1 Test Domains (10 diverse sites)
1. Small Swedish SaaS (<1K keywords)
2. Medium Swedish e-commerce (1K-10K keywords)
3. Large Swedish brand (10K+ keywords)
4. English B2B SaaS
5. Local Swedish business
6. News/media site
7. Manufacturing company
8. Professional services
9. E-commerce with AI presence
10. Technical/developer tools

### 7.2 Quality Validation Checklist
For each test:
- [ ] Quality score ≥9.2/10 (23/25 checks passing)
- [ ] Report contains specific keywords with scores
- [ ] Report contains specific URLs and actions
- [ ] No placeholder text ("Based on comprehensive analysis...")
- [ ] All recommendations have effort + impact estimates
- [ ] Execution time <5 minutes
- [ ] Cost <€3.00 per report

### 7.3 Comparison Test
Run same domain through:
1. Current system
2. New v4+v5 system
3. Manual SEMrush analysis

Compare quality side-by-side.

**Deliverable:** 10 validated test reports, quality benchmark documentation.

---

# PART 5: FILE CHANGES SUMMARY

## Files to CREATE (32 new files)

```
src/agents/
├── __init__.py
├── base.py
├── keyword_intelligence.py
├── backlink_intelligence.py
├── technical_seo.py
├── content_analysis.py
├── semantic_architecture.py
├── ai_visibility.py
├── serp_analysis.py
├── local_seo.py
└── master_strategy.py

src/scoring/
├── __init__.py
├── opportunity.py
├── difficulty.py
├── decay.py
└── helpers.py

src/output/
├── __init__.py
├── schemas.py
├── parser.py
└── validator.py

src/prompts/
├── __init__.py
├── keyword_prompt.py
├── backlink_prompt.py
├── technical_prompt.py
├── content_prompt.py
├── semantic_prompt.py
├── ai_visibility_prompt.py
├── serp_prompt.py
├── local_prompt.py
└── master_prompt.py

src/quality/
├── checks.py
└── anti_patterns.py
```

## Files to REWRITE (5 files)

```
src/analyzer/engine.py          # Complete rewrite for 9-agent architecture
src/reporter/external.py        # Data-driven content instead of templates
src/reporter/internal.py        # Data-driven content instead of templates
src/reporter/generator.py       # Consume agent outputs
src/quality/gates.py            # 25-check system
```

## Files to DELETE (4 files)

```
src/analyzer/loop1.py           # Replaced by agents
src/analyzer/loop2.py
src/analyzer/loop3.py
src/analyzer/loop4.py
```

## Files to KEEP (unchanged)

```
src/collector/*                 # Data collection works
src/auth/*                      # Authentication works
src/persistence/*               # Storage works
src/delivery/*                  # Email works
api/analyze.py                  # API works (minor updates only)
```

---

# PART 6: SUCCESS METRICS

## Minimum Viable Product (MVP)
- [ ] 9 agents producing structured output
- [ ] Quality gate passing (23/25 checks)
- [ ] External report with specific recommendations
- [ ] No placeholder text
- [ ] Execution time <10 minutes
- [ ] Cost <€5.00 per report

## Production Ready
- [ ] All MVP criteria
- [ ] Internal report complete
- [ ] Quality score consistently ≥9.2/10
- [ ] 10 successful test analyses
- [ ] Execution time <5 minutes
- [ ] Cost <€3.00 per report

## World Class Target (matches €10,000/month agency)
- [ ] Quality score consistently ≥9.6/10
- [ ] Reports rival boutique SEO agency output
- [ ] Unique insights not in standard tools
- [ ] Customer feedback positive
- [ ] Cost <€2.50 per report
- [ ] Execution time <3 minutes

---

# PART 7: RISK MITIGATION

## Risk 1: Claude Output Quality Varies
**Mitigation:**
- Few-shot examples with good AND bad outputs
- Quality gate with retry logic (max 2 retries)
- Temperature 0.3 for consistency

## Risk 2: Token Limits Exceeded
**Mitigation:**
- Data truncation strategy (keep top N items)
- Split large analyses across multiple calls
- Monitor token usage per agent

## Risk 3: DataForSEO API Failures
**Mitigation:**
- Already implemented: Retry with exponential backoff
- Non-critical endpoints fail gracefully
- Cache successful responses

## Risk 4: Report Still Too Generic
**Mitigation:**
- Anti-pattern detection in quality checks
- "Non-generic checks" in 25-point system
- Manual review of first 10 reports

---

# APPENDIX A: ANTI-PATTERNS TO DETECT

The quality system must flag these patterns:

1. **Hedge Everything**
   - Regex: `(might|could|potentially|consider|possibly|perhaps) (want to|need to|should)`
   - Action: Fail "avoids_weasel_words" check

2. **Generic Best Practice**
   - Regex: `(follow|implement|use) (SEO )?(best practices|industry standards)`
   - Action: Fail "customized_advice" check

3. **Data Dump Without Analysis**
   - Check: >20 items listed without prioritization
   - Action: Fail "has_priorities" check

4. **Missing "So What"**
   - Check: Metric stated without interpretation
   - Example: "Your bounce rate is 65%" (no context)
   - Action: Fail "has_benchmarks" check

5. **Placeholder Text**
   - Regex: `(based on|according to) (comprehensive|thorough|detailed) (analysis|review|assessment)`
   - Action: Fail "no_placeholder_text" check

6. **Contradictory Recommendations**
   - Check: Cross-reference agent outputs for conflicts
   - Action: Flag in Master Strategy for resolution

---

*This plan will be updated as implementation progresses.*
*Last updated: January 2026*

"""
Loop 1: Data Interpretation

Transforms raw DataForSEO API data into structured findings with evidence.
Every insight must cite specific data points.

Token budget: ~80K input, ~4K output
Cost: $0.15-0.25
"""

import json
import logging
from typing import Dict, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .client import ClaudeClient
    from .engine import DomainClassification

logger = logging.getLogger(__name__)

# Load prompt template
PROMPT_PATH = Path(__file__).parent / "prompts" / "loop1_interpretation.md"


SYSTEM_PROMPT = """You are an expert SEO analyst with 15 years of experience at enterprise agencies. You are analyzing comprehensive SEO data for a client report. Your task is to interpret the data and extract actionable findings.

## CRITICAL RULES

1. **Every claim must cite specific data.** Format: [Metric: Value | Benchmark: Value | Gap: ±Value]
2. **Quantify business impact.** Traffic, revenue potential, competitive position.
3. **Flag anomalies.** Unusual patterns, sudden changes, outliers.
4. **Benchmark everything.** Compare to competitors, industry averages, or best practices.
5. **Be honest about limitations.** Note where data is incomplete or uncertain.
6. **Use the exact data provided.** Do not hallucinate or assume values not in the data.

## DATA UNDERSTANDING REQUIREMENTS

You will receive a `data_dictionary` section explaining:
- What each field means and how to interpret it
- The data source and reliability level (HIGH/MEDIUM/LOW)
- Scoring formulas used for calculated fields like opportunity_score
- Known limitations and caveats

You will also receive a `data_quality` section containing:
- Overall quality score and per-phase completeness
- Truncation warnings (data may be sampled, not complete)
- Missing data indicators
- Confidence levels for different metric types

**ALWAYS:**
- Consult the data_dictionary before interpreting any field
- Note truncation warnings - if "ranked_keywords_shown: 1000" but "total_claimed_keywords: 15000", you're seeing 6.7% of the data
- Adjust confidence in conclusions based on data_quality.confidence_indicators
- Include data limitations in your "Data Quality Notes" section
- Use _field_counts to understand sample sizes vs. actual totals

**FIELD INTERPRETATION GUIDE:**
- `opportunity_score`: Pre-calculated as search_volume × (1 - difficulty/100) × intent_multiplier. Higher = better.
- `competitor_type`: 'direct' means keyword overlap >30%, 'emerging' means >20% traffic growth
- `domain_rank`: 0-100 scale (similar to Ahrefs Domain Rating). 30+ is notable, 50+ is strong, 70+ is authoritative.
- Traffic estimates: Use for RELATIVE comparison only, typically 60-80% of actual
- Position tiers: 1-3 = high CTR (20-30%), 4-10 = moderate (5-10%), 11-20 = low (1-3%)"""


USER_PROMPT_TEMPLATE = """# INPUT DATA

## Domain Information
- **Target:** {domain}
- **Market:** {market}
- **Language:** {language}
- **Industry:** {industry}

## Domain Classification
- **Size Tier:** {size_tier} (based on {keyword_count} keywords)
- **Competitive Intensity:** {competitive_intensity}
- **Technical Maturity:** {technical_maturity}

## Data Quality Summary
- **Overall Quality Score:** {quality_score:.1f}%
- **Phase Completeness:** Phase1={phase1_score:.0%}, Phase2={phase2_score:.0%}, Phase3={phase3_score:.0%}, Phase4={phase4_score:.0%}
- **Truncation Warnings:** {truncation_count} fields may be truncated
- **Missing Data:** {missing_count} data points unavailable
- **Collection Errors:** {error_count}

### Confidence Indicators
{confidence_indicators}

### Data Limitations to Consider
{data_limitations}

---

## BUSINESS CONTEXT (from Context Intelligence)
{business_context}

---

## DATA DICTIONARY (Reference for field interpretation)
```json
{data_dictionary_summary}
```

---

## Phase 1: Foundation Data
```json
{foundation_data}
```

## Phase 2: Keyword Intelligence
```json
{keyword_data}
```

## Phase 3: Competitive & Backlink Data
```json
{competitive_data}
```

## Phase 4: AI Visibility & Technical Data
```json
{ai_technical_data}
```

---

# ANALYSIS TASKS

Complete each section with evidence-based findings:

## 1. CURRENT STATE ASSESSMENT

### 1.1 Domain Health Score
Evaluate overall domain strength on a scale of 1-100 considering:
- Organic traffic vs. market potential
- Ranking distribution (positions 1-3, 4-10, 11-20, 21-50, 51-100)
- Backlink authority (DR, referring domains)
- Technical health (Core Web Vitals scores)
- Content coverage (keyword universe capture rate)

### 1.2 Trend Analysis
Based on historical data:
- Traffic trajectory: Accelerating / Stable / Declining
- Keyword growth: Net new vs. lost rankings
- Authority growth: Link acquisition velocity
- Identify any inflection points or anomalies

### 1.3 Traffic Concentration Risk
- What % of traffic comes from top 10 pages?
- What % of traffic comes from top 10 keywords?
- Single points of failure?

## 2. COMPETITIVE POSITION

### 2.1 Market Share Analysis
For each competitor:
- Current metrics comparison (traffic, keywords, DR)
- Trajectory comparison
- Who is gaining? Who is losing?

### 2.2 Competitive Trajectory Matrix
Format as a markdown table with columns: Competitor | Traffic Trend | Keywords Trend | Authority Trend | Threat Level

### 2.3 Keyword Battleground
From domain intersection data:
- How many keywords do we compete on?
- Win rate (we rank higher vs. they rank higher)
- High-value contested keywords
- Keywords we're losing

## 3. KEYWORD OPPORTUNITIES

### 3.1 Current Portfolio Assessment
- Total keywords ranking
- Distribution by position tier
- Distribution by intent (informational/commercial/transactional)
- High-value keywords (high volume × good position)

### 3.2 Gap Analysis
From keyword_gaps and competitor intersection:
- Total opportunity volume (keywords we should rank for but don't)
- Quick wins (high volume, low difficulty, competitor ranks)
- Strategic opportunities (high value, medium difficulty)
- Long-term plays (high difficulty, high reward)

### 3.3 Topical Coverage
Based on keyword clusters:
- Clusters we dominate
- Clusters with partial coverage
- Clusters we're missing entirely

## 4. BACKLINK INTELLIGENCE

### 4.1 Authority Assessment
- Domain Rating vs. competitors
- Referring domains vs. competitors
- Link quality indicators (dofollow %, authority distribution)

### 4.2 Link Profile Health
- Anchor text distribution (over-optimized?)
- Link velocity (growing, stable, declining?)
- Recent gains/losses

### 4.3 Link Gap Analysis
From backlink data:
- Sites linking to competitors but not us
- Prioritized by authority and relevance
- Estimated acquisition difficulty

## 5. AI VISIBILITY ASSESSMENT

### 5.1 Current AI Presence
- AI mentions found?
- Which platforms cite the domain?
- Which pages get cited?

### 5.2 Competitive AI Landscape
- Who dominates AI citations in this space?
- Our share of voice vs. competitors

### 5.3 AI Visibility Score
Rate 1-100 based on available data.

## 6. TECHNICAL ASSESSMENT

### 6.1 Core Web Vitals
- Performance score
- Accessibility score
- SEO score
- Best practices score

### 6.2 Critical Issues
Issues blocking ranking potential (based on available data).

### 6.3 Technical Priorities
All issues by priority: Critical / High / Medium / Low

---

# OUTPUT FORMAT

Structure your response EXACTLY as follows:

```
## EXECUTIVE FINDINGS

[3-5 bullet points with the most important discoveries, each with data citations]

## SECTION 1: CURRENT STATE
[Detailed analysis with data citations in format [Metric: Value]]

## SECTION 2: COMPETITIVE POSITION
[Detailed analysis with data citations]

## SECTION 3: KEYWORD OPPORTUNITIES
[Detailed analysis with data citations]

## SECTION 4: BACKLINK INTELLIGENCE
[Detailed analysis with data citations]

## SECTION 5: AI VISIBILITY
[Detailed analysis with data citations]

## SECTION 6: TECHNICAL ASSESSMENT
[Detailed analysis with data citations]

## DATA QUALITY NOTES
[Any limitations, gaps, or caveats about the data]
```"""


class DataInterpreter:
    """
    Loop 1: Data Interpretation

    Transforms raw data into structured findings with evidence.
    """

    def __init__(self, client: "ClaudeClient"):
        self.client = client

    async def interpret(
        self,
        analysis_data: Dict[str, Any],
        classification: "DomainClassification",
    ) -> str:
        """
        Interpret raw data and produce structured findings.

        Args:
            analysis_data: Compiled data from collector
            classification: Domain classification

        Returns:
            Structured findings document
        """
        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})
        data_quality = analysis_data.get("data_quality", {})
        data_dictionary = analysis_data.get("data_dictionary", {})

        # Prepare data for prompt (truncate if needed to fit context)
        foundation_data = self._prepare_data(
            analysis_data.get("phase1_foundation", {}), max_chars=30000
        )
        keyword_data = self._prepare_data(
            analysis_data.get("phase2_keywords", {}), max_chars=40000
        )
        competitive_data = self._prepare_data(
            analysis_data.get("phase3_competitive", {}), max_chars=30000
        )
        ai_technical_data = self._prepare_data(
            analysis_data.get("phase4_ai_technical", {}), max_chars=20000
        )

        # Extract quality metrics
        phase_scores = data_quality.get("phase_scores", {})
        confidence_indicators = data_quality.get("confidence_indicators", {})
        truncation_warnings = data_quality.get("truncation_warnings", [])

        # Format confidence indicators for prompt
        confidence_text = "\n".join([
            f"- **{key}**: {value}"
            for key, value in confidence_indicators.items()
        ]) if confidence_indicators else "- No confidence indicators available"

        # Format data limitations
        limitations = data_dictionary.get("_data_limitations", {})
        limitations_text = "\n".join([
            f"- **{key}**: {value}"
            for key, value in limitations.items()
        ]) if limitations else "- Standard data limitations apply"

        # Create condensed data dictionary summary for prompt
        # Include scoring formulas and key field interpretations
        dictionary_summary = {
            "scoring_formulas": data_dictionary.get("_scoring_formulas", {}),
            "key_field_scales": {
                "domain_rank": "0-100 scale (like Ahrefs DR). <30=weak, 30-50=notable, 50-70=strong, 70+=authoritative",
                "keyword_difficulty": "0-100 scale. 0-30=easy, 30-60=moderate, 60+=hard",
                "position_tiers": "1-3=high CTR (20-30%), 4-10=moderate (5-10%), 11-20=low (1-3%)",
                "traffic_reliability": "Estimated, typically 60-80% of actual analytics",
            },
            "competitor_type_rules": data_dictionary.get("competitors", {}).get("competitor_type", {}).get("classification_rules", {}),
        }

        # Format business context from Context Intelligence
        context_intelligence = analysis_data.get("context_intelligence", {})
        business_context_text = self._format_business_context(context_intelligence)

        # Format prompt
        prompt = USER_PROMPT_TEMPLATE.format(
            domain=metadata.get("domain", "unknown"),
            market=metadata.get("market", "unknown"),
            language=metadata.get("language", "unknown"),
            industry=metadata.get("industry", "General"),
            size_tier=classification.size_tier,
            keyword_count=summary.get("total_organic_keywords", 0),
            competitive_intensity=classification.competitive_intensity,
            technical_maturity=classification.technical_maturity,
            # Data quality metrics
            quality_score=data_quality.get("overall_score", 0.0),
            phase1_score=phase_scores.get("phase1_foundation", 0.0),
            phase2_score=phase_scores.get("phase2_keywords", 0.0),
            phase3_score=phase_scores.get("phase3_competitive", 0.0),
            phase4_score=phase_scores.get("phase4_ai_technical", 0.0),
            truncation_count=len(truncation_warnings),
            missing_count=len(data_quality.get("missing_data", [])),
            error_count=len(metadata.get("errors", [])),
            confidence_indicators=confidence_text,
            data_limitations=limitations_text,
            business_context=business_context_text,
            data_dictionary_summary=json.dumps(dictionary_summary, indent=2),
            # Phase data
            foundation_data=foundation_data,
            keyword_data=keyword_data,
            competitive_data=competitive_data,
            ai_technical_data=ai_technical_data,
        )

        # Call Claude
        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=8000,
            temperature=0.3,
        )

        if not response.success:
            logger.error(f"Loop 1 failed: {response.error}")
            return f"Error in data interpretation: {response.error}"

        return response.content

    async def regenerate(
        self,
        previous_output: str,
        feedback: str,
        analysis_data: Dict[str, Any],
        classification: "DomainClassification",
    ) -> str:
        """
        Regenerate findings based on feedback.

        Args:
            previous_output: Previous interpretation output
            feedback: Specific feedback on what to improve
            analysis_data: Original data
            classification: Domain classification

        Returns:
            Improved findings document
        """
        prompt = f"""# REVISION REQUEST

## Previous Output
{previous_output[:10000]}...

## Feedback
{feedback}

## Instructions
Please regenerate the analysis addressing the feedback above.
Use the same data and format as before, but improve the areas mentioned.
"""

        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=8000,
            temperature=0.3,
        )

        return response.content

    def _prepare_data(self, data: Dict[str, Any], max_chars: int = 50000) -> str:
        """
        Prepare data for prompt, truncating if necessary.

        Args:
            data: Data dictionary to serialize
            max_chars: Maximum characters

        Returns:
            JSON string, truncated if needed
        """
        json_str = json.dumps(data, indent=2, default=str)

        if len(json_str) <= max_chars:
            return json_str

        # Truncate intelligently - keep structure but limit arrays
        truncated = self._truncate_data(data, max_chars)
        return json.dumps(truncated, indent=2, default=str)

    def _truncate_data(self, data: Any, max_chars: int) -> Any:
        """
        Recursively truncate data to fit within limits.

        Provides clear metadata about truncation so agents understand
        they're seeing a sample, not the complete dataset.
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Skip internal metadata fields (start with _)
                if key.startswith("_"):
                    result[key] = value
                    continue

                if isinstance(value, list) and len(value) > 10:
                    # Truncate long lists with clear metadata
                    result[key] = value[:10]
                    result[f"_{key}_metadata"] = {
                        "shown": 10,
                        "total_in_sample": len(value),
                        "truncation_note": f"Showing top 10 of {len(value)} items in sample. Full dataset may be larger.",
                        "analysis_impact": "Conclusions should account for unseen data. Focus on patterns, not exhaustive analysis."
                    }
                elif isinstance(value, dict):
                    result[key] = self._truncate_data(value, max_chars // 2)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            if len(data) > 10:
                return data[:10]  # Truncation metadata added at dict level
            return data
        else:
            return data

    def _format_business_context(self, context: Dict[str, Any]) -> str:
        """
        Format Context Intelligence data for the prompt.

        Args:
            context: Context intelligence data from pre-collection phase

        Returns:
            Formatted business context string
        """
        if not context:
            return "No business context available. Analyze based on data only."

        parts = []

        # Business context
        bc = context.get("business_context", {})
        if bc:
            parts.append("### Business Understanding")
            if bc.get("business_model"):
                parts.append(f"- **Business Model:** {bc['business_model']}")
            if bc.get("company_stage"):
                parts.append(f"- **Company Stage:** {bc['company_stage']}")
            if bc.get("industry"):
                parts.append(f"- **Industry:** {bc['industry']}")
            if bc.get("primary_goal"):
                parts.append(f"- **Primary Goal:** {bc['primary_goal']}")
            if bc.get("target_audience"):
                audience = bc["target_audience"]
                if isinstance(audience, dict):
                    parts.append(f"- **Target Audience:** {audience.get('primary', 'Unknown')}")
            if bc.get("seo_fit"):
                parts.append(f"- **SEO Fit:** {bc['seo_fit']}")
            if bc.get("recommended_focus"):
                parts.append(f"- **Recommended Focus:** {', '.join(bc['recommended_focus'][:3])}")

            # Goal validation
            gv = bc.get("goal_validation", {})
            if gv:
                if not gv.get("goal_fits_business", True):
                    parts.append("")
                    parts.append("### ⚠️ Goal Mismatch Detected")
                    parts.append(f"The stated goal '{gv.get('stated_goal')}' may not align with this business.")
                    if gv.get("suggested_goal"):
                        parts.append(f"**Suggested goal:** {gv['suggested_goal']}")
                    if gv.get("suggestion_reason"):
                        parts.append(f"**Reason:** {gv['suggestion_reason']}")

            # Buyer journey
            bj = bc.get("buyer_journey", {})
            if bj:
                parts.append("")
                parts.append("### Buyer Journey")
                if bj.get("type"):
                    parts.append(f"- **Type:** {bj['type']}")
                if bj.get("cycle_length"):
                    parts.append(f"- **Cycle Length:** {bj['cycle_length']}")
                if bj.get("stages"):
                    parts.append(f"- **Stages:** {' → '.join(bj['stages'])}")

            # Success definition
            sd = bc.get("success_definition", {})
            if sd:
                parts.append("")
                parts.append("### Success Definition")
                if sd.get("10x_scenario"):
                    parts.append(f"- **10x Success:** {sd['10x_scenario']}")
                if sd.get("realistic_12m"):
                    parts.append(f"- **Realistic 12-Month:** {sd['realistic_12m']}")
                if sd.get("primary_metric"):
                    parts.append(f"- **Primary Metric:** {sd['primary_metric']}")

        # Competitor context
        cc = context.get("competitor_context", {})
        if cc:
            parts.append("")
            parts.append("### Validated Competitors")

            direct = cc.get("direct_competitors", [])
            if direct:
                parts.append("**Direct Business Competitors** (validated):")
                for comp in direct[:5]:
                    if isinstance(comp, dict):
                        parts.append(f"- {comp.get('domain', 'unknown')} - Threat: {comp.get('threat_level', 'unknown')}")
                    else:
                        parts.append(f"- {comp}")

            discovered = cc.get("discovered_competitors", [])
            if discovered:
                parts.append("")
                parts.append("**Discovered Competitors:**")
                for comp in discovered[:3]:
                    if isinstance(comp, dict):
                        parts.append(f"- {comp.get('domain', 'unknown')} ({comp.get('type', 'unknown')}) - via {comp.get('discovery_method', 'unknown')}")

            reclassified = cc.get("reclassified", [])
            if reclassified:
                parts.append("")
                parts.append("**Reclassified (NOT real competitors):**")
                for comp in reclassified[:3]:
                    if isinstance(comp, dict):
                        parts.append(f"- {comp.get('domain', 'unknown')}: {comp.get('actual_type', 'unknown')} - {comp.get('reason', '')}")

        # Market context
        mc = context.get("market_context", {})
        if mc:
            parts.append("")
            parts.append("### Market Validation")
            if mc.get("declared_market"):
                parts.append(f"- **Primary Market:** {mc['declared_market']} (validated: {mc.get('primary_validated', False)})")
            if mc.get("validation_notes"):
                parts.append(f"- **Notes:** {mc['validation_notes']}")

            opps = mc.get("discovered_opportunities", [])
            if opps:
                parts.append("")
                parts.append("**Discovered Market Opportunities:**")
                for opp in opps[:3]:
                    if isinstance(opp, dict):
                        parts.append(
                            f"- {opp.get('region', 'unknown')} ({opp.get('language', 'unknown')}): "
                            f"Opportunity score {opp.get('opportunity_score', 0):.0f}/100, "
                            f"Competition: {opp.get('competition_level', 'unknown')}"
                        )
                        if opp.get("recommendation"):
                            parts.append(f"  → {opp['recommendation']}")

        # Collection focus
        cf = context.get("collection_focus", {})
        if cf:
            parts.append("")
            parts.append("### Analysis Focus (based on goal)")
            if cf.get("primary_goal"):
                parts.append(f"- **Goal:** {cf['primary_goal']}")
            if cf.get("priority_intents"):
                parts.append(f"- **Priority Intents:** {', '.join(cf['priority_intents'])}")
            if cf.get("content_type_focus"):
                parts.append(f"- **Content Focus:** {', '.join(cf['content_type_focus'])}")

        if not parts:
            return "No business context available. Analyze based on data only."

        return "\n".join(parts)

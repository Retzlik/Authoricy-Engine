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
6. **Use the exact data provided.** Do not hallucinate or assume values not in the data."""


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
        """Recursively truncate data to fit within limits."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 10:
                    # Truncate long lists
                    result[key] = value[:10]
                    result[f"_{key}_truncated"] = f"... and {len(value) - 10} more items"
                elif isinstance(value, dict):
                    result[key] = self._truncate_data(value, max_chars // 2)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return data[:10]
        else:
            return data

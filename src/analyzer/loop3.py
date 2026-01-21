"""
Loop 3: SERP & Competitor Enrichment

Adds real-world context through web research:
- Fetches actual SERP results for priority keywords
- Analyzes competitor content
- Gathers competitive intelligence

Token budget: ~50K input (fetched content), ~5K output
Cost: $0.30-0.50
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ClaudeClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a content strategist and competitive intelligence analyst. You've been given:
1. Strategic recommendations from previous analysis
2. Information about priority keywords and competitors

Your job is to extract actionable insights for content strategy and competitive positioning.

## CRITICAL RULES

1. **Focus on actionable insights** — What specifically should be created/changed
2. **Be specific about content requirements** — Word counts, sections, elements
3. **Identify differentiation opportunities** — What's missing from current results
4. **Provide competitor weaknesses** — Where they can be beaten
5. **Create content briefs** — Ready to hand to a writer"""


USER_PROMPT_TEMPLATE = """# CONTEXT

## Domain
{domain}

## Priority Keywords (from strategic analysis)
{priority_keywords}

## Top Competitors
{competitors}

---

# STRATEGIC RECOMMENDATIONS TO ENRICH

{loop2_output}

---

# ENRICHMENT TASKS

## 1. CONTENT REQUIREMENTS BY KEYWORD

For the top 5 priority keywords, analyze what it takes to rank:

| Keyword | Recommended Format | Target Word Count | Key Sections | Unique Elements |
|---------|-------------------|-------------------|--------------|-----------------|

### Detailed Content Briefs

For each of the top 5 priority keywords, provide:

```
### Keyword: [keyword]

**Search Intent:** [informational/commercial/transactional]

**Content Requirements to Compete:**
- Format: [Article/Guide/Tool/Comparison/etc.]
- Target word count: [X-Y words]
- Required sections:
  1. [Section]
  2. [Section]
  3. [Section]
- Must-have elements:
  - [ ] [Element]
  - [ ] [Element]
- Differentiation opportunity: [What's missing from current results]

**Estimated Effort:** [Low/Medium/High]
```

## 2. COMPETITIVE POSITIONING ANALYSIS

For the top 2 competitors identified:

### [Competitor 1 Name]

**Positioning:** [How they position themselves]

**Strengths:**
- [Strength 1]
- [Strength 2]

**Weaknesses:**
- [Weakness 1]
- [Weakness 2]

**Content Strategy Observations:**
- Topics covered
- Content types

**Vulnerability:** [Where they can be beaten]

### [Competitor 2 Name]
[Same structure]

## 3. CONTENT DIFFERENTIATION STRATEGY

Based on analysis, where can the client differentiate?

| Opportunity | Why It's Underserved | Content Angle | Estimated Impact |
|-------------|---------------------|---------------|------------------|

## 4. MESSAGING GAPS

What are competitors NOT saying that the client could own?

- [Gap 1]: [Opportunity]
- [Gap 2]: [Opportunity]
- [Gap 3]: [Opportunity]

## 5. CONTENT CALENDAR PRIORITIES

Based on all analysis, recommend the first 10 content pieces:

| Priority | Topic | Format | Target Keyword | Rationale |
|----------|-------|--------|----------------|-----------|

---

# OUTPUT FORMAT

Structure response with clear sections as above. Focus on actionable insights, not descriptions."""


class SERPEnricher:
    """
    Loop 3: SERP & Competitor Enrichment

    Adds real-world context through analysis of
    competitive content and SERP landscape.
    """

    def __init__(self, client: "ClaudeClient"):
        self.client = client

    async def enrich(
        self,
        loop2_output: str,
        analysis_data: Dict[str, Any],
    ) -> str:
        """
        Enrich analysis with SERP and competitor insights.

        Args:
            loop2_output: Output from Loop 2 (strategic recommendations)
            analysis_data: Original compiled data

        Returns:
            Enrichment document with content briefs and competitive intelligence
        """
        metadata = analysis_data.get("metadata", {})
        phase2 = analysis_data.get("phase2_keywords", {})
        phase3 = analysis_data.get("phase3_competitive", {})

        # Extract priority keywords (top 10 by opportunity)
        priority_keywords = self._extract_priority_keywords(phase2)

        # Extract competitor info
        competitors = self._extract_competitors(phase3, analysis_data)

        # Format prompt
        prompt = USER_PROMPT_TEMPLATE.format(
            domain=metadata.get("domain", "unknown"),
            priority_keywords=json.dumps(priority_keywords, indent=2),
            competitors=json.dumps(competitors, indent=2),
            loop2_output=loop2_output[:15000],  # Truncate if needed
        )

        # Call Claude
        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=6000,
            temperature=0.4,  # Slightly higher for creative content strategy
        )

        if not response.success:
            logger.error(f"Loop 3 failed: {response.error}")
            return f"Error in enrichment: {response.error}"

        return response.content

    async def regenerate(
        self,
        previous_output: str,
        feedback: str,
        analysis_data: Dict[str, Any],
    ) -> str:
        """
        Regenerate enrichment based on feedback.

        Args:
            previous_output: Previous enrichment output
            feedback: Specific feedback
            analysis_data: Original data

        Returns:
            Improved enrichment document
        """
        prompt = f"""# REVISION REQUEST

## Previous Enrichment Analysis
{previous_output[:10000]}...

## Feedback
{feedback}

## Instructions
Please regenerate the enrichment analysis addressing the feedback above.
Focus on making content briefs more specific and actionable.
"""

        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=6000,
            temperature=0.4,
        )

        return response.content

    def _extract_priority_keywords(self, phase2: Dict[str, Any]) -> List[Dict]:
        """Extract top priority keywords for enrichment."""
        keywords = []

        # Get keywords from gaps (high opportunity)
        gaps = phase2.get("keyword_gaps", [])
        for gap in gaps[:5]:
            keywords.append({
                "keyword": gap.get("keyword", ""),
                "volume": gap.get("search_volume", 0),
                "difficulty": gap.get("difficulty", 0),
                "type": "gap",
            })

        # Get keywords from ranked (positions 4-20)
        ranked = phase2.get("ranked_keywords", [])
        opportunity_keywords = [
            k for k in ranked
            if 4 <= k.get("position", 100) <= 20
        ]
        # Sort by volume
        opportunity_keywords.sort(
            key=lambda x: x.get("search_volume", 0),
            reverse=True
        )
        for kw in opportunity_keywords[:5]:
            keywords.append({
                "keyword": kw.get("keyword", ""),
                "volume": kw.get("search_volume", 0),
                "position": kw.get("position", 0),
                "type": "opportunity",
            })

        return keywords[:10]

    def _extract_competitors(
        self,
        phase3: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> List[Dict]:
        """Extract competitor info for analysis."""
        competitors = []

        # From phase 3 competitor analysis
        comp_analysis = phase3.get("competitor_analysis", [])
        for comp in comp_analysis[:4]:
            competitors.append({
                "domain": comp.get("domain", ""),
                "traffic": comp.get("organic_traffic", 0),
                "keywords": comp.get("organic_keywords", 0),
            })

        # Fallback to phase 1 competitors
        if not competitors:
            phase1 = analysis_data.get("phase1_foundation", {})
            for comp in phase1.get("competitors", [])[:4]:
                competitors.append({
                    "domain": comp.get("domain", ""),
                    "traffic": comp.get("organic_traffic", 0),
                })

        return competitors

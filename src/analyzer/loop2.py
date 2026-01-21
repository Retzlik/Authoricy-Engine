"""
Loop 2: Strategic Synthesis

Transforms findings into prioritized, actionable recommendations
with business impact quantification.

Token budget: ~20K input, ~6K output
Cost: $0.20-0.30
"""

import json
import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ClaudeClient
    from .engine import DomainClassification

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a senior marketing strategist advising a B2B company. You've received a comprehensive SEO analysis and must now create strategic recommendations that drive business outcomes.

## CRITICAL RULES

1. **Lead with the "One Big Thing"** — The single most important finding/recommendation
2. **Quantify everything in business terms** — Traffic → Leads → Pipeline → Revenue
3. **Prioritize ruthlessly** — Maximum 3 priorities per time horizon
4. **Be specific** — "Create 5 comparison pages" not "improve content"
5. **Include effort estimates** — Hours, resources, complexity
6. **Create decision points** — What to do if X happens
7. **Never include time estimates** — Focus on what, not when"""


USER_PROMPT_TEMPLATE = """# CONTEXT

## Domain Classification
- **Domain:** {domain}
- **Size Tier:** {size_tier} ({keyword_count} keywords)
- **Industry:** {industry}
- **Competitive Intensity:** {competitive_intensity}

## Key Assumptions
- B2B conversion rate: 2-3%
- Assumed average deal value: Industry standard
- Available resources: Standard marketing team

---

# INPUT: ANALYSIS FINDINGS FROM LOOP 1

{loop1_output}

---

# SYNTHESIS TASKS

## 1. THE ONE BIG THING

What is the single most important finding from this analysis? This should be:
- Surprising or non-obvious
- Quantifiable in business impact
- Actionable
- Urgent (cost of inaction is clear)

Format:
```
### THE ONE BIG THING

**[Headline finding in bold]**

**What we found:** [1-2 sentences with data]

**Why it matters:** [Business impact quantified]

**What happens if we ignore it:** [Cost of inaction]

**What to do:** [Specific action]
```

## 2. STRATEGIC OPTIONS

Present 3 paths the client could take:

### Option A: Conservative
- Investment: Low (define hours/month)
- Focus: Quick wins only
- Expected outcome: [Quantified]
- Risk: [What could go wrong]

### Option B: Moderate (Recommended)
- Investment: Medium (define hours/month)
- Focus: Quick wins + foundation building
- Expected outcome: [Quantified]
- Risk: [What could go wrong]

### Option C: Aggressive
- Investment: High (define hours/month)
- Focus: Full strategic execution
- Expected outcome: [Quantified]
- Risk: [What could go wrong]

## 3. PRIORITIZED ROADMAP

### Immediate Actions (First Priority)
| # | Action | Effort | Expected Outcome | Dependencies |
|---|--------|--------|------------------|--------------|

### Foundation Building (Second Priority)
| # | Action | Effort | Expected Outcome | Dependencies |

### Scale & Accelerate (Third Priority)
| # | Action | Effort | Expected Outcome | Dependencies |

## 4. KEYWORD STRATEGY

### Tier 1: Defend (Keywords in positions 1-3)
- Keywords to protect
- Actions to maintain position

### Tier 2: Attack (Keywords in positions 4-20)
- Keywords to push into top 3
- Specific actions per keyword

### Tier 3: Capture (Keywords not ranking)
- New keyword targets
- Content required

## 5. CONTENT PRIORITIES

Based on keyword analysis, prioritize content creation:

| Priority | Topic/Keyword | Format | Target Position | Est. Traffic | Est. Effort |
|----------|---------------|--------|-----------------|--------------|-------------|

Include content refresh priorities (existing content to update).

## 6. LINK BUILDING STRATEGY

### Target Profile
- Current DR: [X] → Target DR: [Y]
- Current RDs: [X] → Target RDs: [Y]
- Required link velocity: [X] links/month

### Acquisition Strategy
| Tier | Target Type | Approach | Est. Success Rate |
|------|-------------|----------|-------------------|

## 7. AI VISIBILITY STRATEGY

Based on AI visibility assessment:
- Current AI share of voice: [X]%
- Target: Improve visibility

Priority actions:
1. [Specific action]
2. [Specific action]
3. [Specific action]

## 8. TECHNICAL PRIORITIES

Critical fixes (blocking performance):
| Issue | Impact | Fix | Effort |
|-------|--------|-----|--------|

## 9. SUCCESS METRICS

### Leading Indicators
- [Metric]: [Target]
- [Metric]: [Target]

### Lagging Indicators
- [Metric]: [Target]
- [Metric]: [Target]

## 10. RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|

---

# OUTPUT FORMAT

Structure your response with clear headers as shown above. Ensure every recommendation includes:
- Specific action (what)
- Effort estimate (how much work - hours/complexity, NOT time)
- Expected outcome (why)
- Dependencies (what else needs to happen)"""


class StrategicSynthesizer:
    """
    Loop 2: Strategic Synthesis

    Transforms findings into prioritized recommendations.
    """

    def __init__(self, client: "ClaudeClient"):
        self.client = client

    async def synthesize(
        self,
        loop1_output: str,
        analysis_data: Dict[str, Any],
        classification: "DomainClassification",
    ) -> str:
        """
        Synthesize findings into strategic recommendations.

        Args:
            loop1_output: Output from Loop 1
            analysis_data: Original compiled data
            classification: Domain classification

        Returns:
            Strategic recommendations document
        """
        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})

        # Format prompt
        prompt = USER_PROMPT_TEMPLATE.format(
            domain=metadata.get("domain", "unknown"),
            size_tier=classification.size_tier,
            keyword_count=summary.get("total_organic_keywords", 0),
            industry=classification.industry,
            competitive_intensity=classification.competitive_intensity,
            loop1_output=loop1_output,
        )

        # Call Claude
        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=8000,
            temperature=0.3,
        )

        if not response.success:
            logger.error(f"Loop 2 failed: {response.error}")
            return f"Error in strategic synthesis: {response.error}"

        return response.content

    async def regenerate(
        self,
        previous_output: str,
        feedback: str,
        analysis_data: Dict[str, Any],
        classification: "DomainClassification",
    ) -> str:
        """
        Regenerate strategy based on feedback.

        Args:
            previous_output: Previous synthesis output
            feedback: Specific feedback on what to improve
            analysis_data: Original data
            classification: Domain classification

        Returns:
            Improved strategic recommendations
        """
        prompt = f"""# REVISION REQUEST

## Previous Strategic Recommendations
{previous_output[:15000]}...

## Feedback
{feedback}

## Instructions
Please regenerate the strategic recommendations addressing the feedback above.
Maintain the same structure but improve the areas mentioned.
Ensure all recommendations remain specific and actionable.
"""

        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=8000,
            temperature=0.3,
        )

        return response.content

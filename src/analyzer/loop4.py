"""
Loop 4: Quality Review & Executive Summary

Final validation, fact-checking, and executive summary generation.
Implements the quality gate (score ≥8/10 to proceed).

Token budget: ~30K input, ~3K output
Cost: $0.15-0.20
"""

import json
import logging
import re
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ClaudeClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a senior editor and quality assurance lead reviewing an SEO analysis before client delivery. Your job is to:
1. Validate the quality of the analysis
2. Check for internal consistency
3. Generate the executive summary
4. Assign a quality score

## CRITICAL RULES

1. **Be rigorous** — Don't pass poor quality work
2. **Check consistency** — Numbers should match across sections
3. **Verify actionability** — Every recommendation must be specific
4. **Business focus** — Executive summary must speak to business outcomes
5. **Honest assessment** — Score fairly, don't inflate
6. **Acknowledge data limitations** — If underlying data quality is poor, note it in the executive summary

## DATA QUALITY AWARENESS

You will receive data quality metrics. Use these to:
- Adjust expectations if data was incomplete
- Flag when conclusions are based on limited data
- Note in executive summary if certain sections lack confidence
- Consider data completeness in "Data Completeness" scoring dimension"""


USER_PROMPT_TEMPLATE = """# QUALITY REVIEW REQUEST

## Domain
{domain}

## Original Data Summary
- Total Keywords: {keyword_count}
- Competitors Analyzed: {competitor_count}
- Backlinks: {backlink_count}
- Collection Duration: {duration}s

## Data Quality Assessment
- **Overall Quality Score:** {data_quality_score:.1f}%
- **Collection Errors:** {error_count}
- **Missing Data Points:** {missing_data}
- **Truncation Warnings:** {truncation_warnings}

### Confidence Levels
{confidence_levels}

---

# LOOP 1 OUTPUT: DATA INTERPRETATION

{loop1_output}

---

# LOOP 2 OUTPUT: STRATEGIC SYNTHESIS

{loop2_output}

---

# LOOP 3 OUTPUT: SERP & COMPETITOR ENRICHMENT

{loop3_output}

---

# QUALITY REVIEW TASKS

## 1. ACTIONABILITY CHECK

For each major recommendation, verify:
- [ ] Action is specific (not vague)
- [ ] Effort estimate provided
- [ ] Expected outcome stated
- [ ] Dependencies identified

List any recommendations that fail this test and why.

## 2. INTERNAL CONSISTENCY

Check for contradictions between sections:
- Do priorities align across loops?
- Are metrics referenced consistently?
- Do recommendations conflict?

Note any inconsistencies found.

## 3. EXECUTIVE SUMMARY

Write a compelling 1-page executive summary that:
- Opens with the single most compelling finding
- States business impact clearly
- Presents top 3 recommendations
- Creates appropriate urgency
- Ends with clear next step

### Structure:
```
# EXECUTIVE SUMMARY: [DOMAIN] SEO & AUTHORITY ANALYSIS

## The Headline

[One powerful sentence capturing the most important finding]

## Key Findings

1. **[Finding 1]:** [1-2 sentences with key data point]
2. **[Finding 2]:** [1-2 sentences with key data point]
3. **[Finding 3]:** [1-2 sentences with key data point]

## Business Impact

[Paragraph quantifying the opportunity - traffic potential, competitive position, etc.]

## Recommended Action

[The recommended path forward - specific and clear, based on Option B from strategic analysis]

## What Happens If We Wait

[Cost of inaction - what competitors are doing, market trends]

## Next Step

[Specific call to action - what should happen next]
```

## 4. QUALITY SCORECARD

Rate the analysis on each dimension (1-10):

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Data Completeness | /10 | [Brief reason] |
| Evidence Quality | /10 | [Brief reason] |
| Actionability | /10 | [Brief reason] |
| Business Relevance | /10 | [Brief reason] |
| Prioritization | /10 | [Brief reason] |
| Internal Consistency | /10 | [Brief reason] |
| AI Visibility Coverage | /10 | [Brief reason] |
| Technical Depth | /10 | [Brief reason] |
| **OVERALL** | **/10** | |

### Quality Gate Decision
- Score ≥8: **PASS** — Proceed to report generation
- Score 6-7: **REVISE** — Flag specific improvements needed
- Score <6: **FAIL** — Requires significant rework

---

# OUTPUT FORMAT

Structure your response EXACTLY as follows:

```
## ACTIONABILITY REVIEW

[List of any recommendations that need improvement]

## CONSISTENCY CHECK

[Any inconsistencies found, or "No inconsistencies found"]

## EXECUTIVE SUMMARY

[Full executive summary as structured above]

## QUALITY SCORECARD

[Scoring table with all 8 dimensions plus overall]

## FINAL ASSESSMENT

**Decision:** [PASS / REVISE / FAIL]

**Overall Score:** [X/10]

**Improvement Notes:** [If REVISE or FAIL, specific changes needed]
```"""


class QualityReviewer:
    """
    Loop 4: Quality Review & Executive Summary

    Validates analysis quality and generates executive summary.
    Implements quality gate (≥8/10 to pass).
    """

    QUALITY_DIMENSIONS = [
        "Data Completeness",
        "Evidence Quality",
        "Actionability",
        "Business Relevance",
        "Prioritization",
        "Internal Consistency",
        "AI Visibility Coverage",
        "Technical Depth",
    ]

    def __init__(self, client: "ClaudeClient"):
        self.client = client

    async def review(
        self,
        loop1_output: str,
        loop2_output: str,
        loop3_output: str,
        analysis_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Review analysis quality and generate executive summary.

        Args:
            loop1_output: Data interpretation output
            loop2_output: Strategic synthesis output
            loop3_output: Enrichment output
            analysis_data: Original compiled data

        Returns:
            Dict containing:
                - review: Full review text
                - executive_summary: Executive summary
                - quality_score: Overall score (0-10)
                - quality_checks: Individual dimension scores
                - passed: Boolean if quality gate passed
        """
        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})
        data_quality = analysis_data.get("data_quality", {})

        # Extract data quality information
        confidence_indicators = data_quality.get("confidence_indicators", {})
        confidence_text = "\n".join([
            f"- **{key}**: {value}"
            for key, value in confidence_indicators.items()
        ]) if confidence_indicators else "- Standard confidence levels"

        missing_data = data_quality.get("missing_data", [])
        missing_text = ", ".join(missing_data[:5]) if missing_data else "None"
        if len(missing_data) > 5:
            missing_text += f" (+{len(missing_data) - 5} more)"

        truncation_warnings = data_quality.get("truncation_warnings", [])
        truncation_text = ", ".join([
            f"{w.get('field', 'unknown')} ({w.get('shown', 0)} of {w.get('threshold', 0)}+)"
            for w in truncation_warnings[:3]
        ]) if truncation_warnings else "None"

        # Format prompt
        prompt = USER_PROMPT_TEMPLATE.format(
            domain=metadata.get("domain", "unknown"),
            keyword_count=summary.get("ranked_keywords_count", 0),
            competitor_count=summary.get("competitor_count", 0),
            backlink_count=summary.get("total_backlinks", 0),
            duration=metadata.get("duration_seconds", 0),
            # Data quality fields
            data_quality_score=data_quality.get("overall_score", 0.0),
            error_count=len(metadata.get("errors", [])),
            missing_data=missing_text,
            truncation_warnings=truncation_text,
            confidence_levels=confidence_text,
            # Loop outputs
            loop1_output=loop1_output[:20000],  # Truncate if needed
            loop2_output=loop2_output[:15000],
            loop3_output=loop3_output[:10000],
        )

        # Call Claude
        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=4000,
            temperature=0.2,  # Lower temperature for consistent evaluation
        )

        if not response.success:
            logger.error(f"Loop 4 failed: {response.error}")
            return {
                "review": f"Error in quality review: {response.error}",
                "executive_summary": "",
                "quality_score": 0.0,
                "quality_checks": {},
                "passed": False,
            }

        # Parse the response
        return self._parse_review(response.content)

    def _parse_review(self, content: str) -> Dict[str, Any]:
        """Parse the review response to extract structured data."""
        result = {
            "review": content,
            "executive_summary": "",
            "quality_score": 0.0,
            "quality_checks": {},
            "passed": False,
        }

        # Extract executive summary
        exec_match = re.search(
            r"## EXECUTIVE SUMMARY\s*\n(.*?)(?=## QUALITY SCORECARD|\Z)",
            content,
            re.DOTALL
        )
        if exec_match:
            result["executive_summary"] = exec_match.group(1).strip()

        # Extract overall score
        score_match = re.search(
            r"\*\*Overall Score:\*\*\s*(\d+(?:\.\d+)?)/10",
            content
        )
        if score_match:
            result["quality_score"] = float(score_match.group(1))
        else:
            # Try alternative format
            score_match = re.search(
                r"\*\*OVERALL\*\*\s*\|\s*\*\*(\d+(?:\.\d+)?)/10\*\*",
                content
            )
            if score_match:
                result["quality_score"] = float(score_match.group(1))

        # Extract individual dimension scores
        for dimension in self.QUALITY_DIMENSIONS:
            pattern = rf"\|\s*{dimension}\s*\|\s*(\d+)/10"
            match = re.search(pattern, content)
            if match:
                result["quality_checks"][dimension] = int(match.group(1))

        # Determine if passed
        result["passed"] = result["quality_score"] >= 8.0

        # Log result
        logger.info(
            f"Quality review: score={result['quality_score']}/10, "
            f"passed={result['passed']}"
        )

        return result

    def validate_executive_summary(self, summary: str) -> Dict[str, bool]:
        """
        Validate that executive summary has required components.

        Args:
            summary: Executive summary text

        Returns:
            Dict of validation checks
        """
        checks = {
            "has_headline": "## The Headline" in summary or "Headline" in summary,
            "has_findings": "Key Findings" in summary or "Finding" in summary,
            "has_impact": "Business Impact" in summary or "Impact" in summary,
            "has_recommendation": "Recommended" in summary,
            "has_next_step": "Next Step" in summary or "next step" in summary.lower(),
            "minimum_length": len(summary) > 500,
        }

        return checks

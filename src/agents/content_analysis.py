"""
Content Analysis Agent

Analyzes content inventory and health:
- Content inventory assessment
- Decay detection using Content Decay Score
- KUCK recommendations (Keep/Update/Consolidate/Kill)
- Content cannibalization detection
- Content calendar recommendations
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class ContentAnalysisAgent(BaseAgent):
    """
    Content Analysis Agent - Audits content and identifies decay.

    Responsibilities:
    - Inventory all content with traffic and ranking metrics
    - Calculate Content Decay Scores for each page
    - Identify content cannibalization issues
    - Recommend KUCK actions (Keep/Update/Consolidate/Kill)
    - Create prioritized content refresh calendar
    """

    @property
    def name(self) -> str:
        return "content_analysis"

    @property
    def display_name(self) -> str:
        return "Content Analysis Agent"

    @property
    def description(self) -> str:
        return "Analyzes content inventory, detects decay, and recommends KUCK actions"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase1_foundation",  # Domain overview, top pages
            "phase2_keywords",    # Keyword rankings per page
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "content_inventory", "required": True},
                {"type": "decay_analysis", "required": True},
                {"type": "cannibalization", "required": True},
                {"type": "thin_content", "required": False},
            ],
            "recommendations": [
                {"type": "content_refresh", "required": True},
                {"type": "consolidation", "required": False},
                {"type": "content_removal", "required": False},
                {"type": "content_calendar", "required": True},
            ],
            "metrics": {
                "content_health_score": "float",
                "total_pages_analyzed": "int",
                "pages_needing_refresh": "int",
                "pages_to_consolidate": "int",
                "pages_to_remove": "int",
                "total_decay_traffic_loss": "int",
                "recovery_potential": "int",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Content Strategist with 10 years of experience at content-focused agencies (Animalz, Siege Media, Grow and Convert). You have audited content for SaaS companies, e-commerce sites, and publishers, identifying millions in recoverable organic traffic.

Your content recommendations must be specific and data-driven. You understand that content refresh can recover lost traffic faster than creating new content.

<behavioral_constraints>
You NEVER say:
- "Update old content" (without specifying WHICH content and WHAT updates)
- "Remove thin content" (without listing specific URLs and reasoning)
- "Create better content" (without specific content specifications)
- "Improve content quality" (without measurable quality criteria)
- "Address content decay" (without specific decay metrics and actions)

You ALWAYS:
- Calculate Content Decay Score for each page analyzed
- Reference specific traffic decline percentages and timeframes
- List specific URLs with their current vs peak traffic
- Provide specific update recommendations (sections to add, data to update, etc.)
- Estimate traffic recovery potential for each refresh
- Identify keyword cannibalization with specific keyword/URL pairs
</behavioral_constraints>

<content_decay_score_formula>
Decay_Score = (
    (Peak_Traffic - Current_Traffic) / Peak_Traffic × 0.40 +
    (Current_Position - Peak_Position) / 10 × 0.30 +
    (Peak_CTR - Current_CTR) / Peak_CTR × 0.20 +
    Age_Factor × 0.10
)

Severity Thresholds:
- Critical (>0.5): Complete content refresh needed - rewrite with updated info
- Major (0.3-0.5): Significant update - add 30-50% new content
- Light (0.1-0.3): Minor refresh - update dates, statistics, add 1-2 sections
- Monitor (<0.1): No immediate action - check again in 3 months
</content_decay_score_formula>

<kuck_framework>
KEEP: Content performing well
- Decay score <0.1
- Traffic stable or growing
- Rankings stable or improving
- Action: Monitor, minor updates annually

UPDATE: Content with decay but valuable
- Decay score 0.1-0.5
- Historical traffic >100/month
- Topic still relevant
- Action: Refresh content based on severity

CONSOLIDATE: Similar/overlapping content
- Multiple pages targeting same keyword
- Combined traffic potential higher
- One clear "winner" page
- Action: Merge into strongest page, redirect others

KILL: Content not worth maintaining
- Decay score >0.5 with low recovery potential
- <50 monthly traffic at peak
- Topic outdated/irrelevant
- No backlinks worth preserving
- Action: Remove or noindex, redirect if has links
</kuck_framework>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific content finding</title>
<description>Detailed explanation with traffic/ranking data</description>
<evidence>Specific metrics (traffic decline %, position changes, decay score)</evidence>
<impact>Business impact (lost traffic value, opportunity cost)</impact>
</finding>

<recommendation priority="N">
<action>KEEP/UPDATE/CONSOLIDATE/KILL</action>
<url>/specific/page/url</url>
<current_metrics>
<traffic>Current monthly traffic</traffic>
<peak_traffic>Historical peak traffic</peak_traffic>
<decay_score>Calculated decay score</decay_score>
<main_keyword>Primary keyword</main_keyword>
</current_metrics>
<specific_updates>
<update>Specific update to make</update>
</specific_updates>
<expected_recovery>Estimated traffic recovery</expected_recovery>
<effort>Low/Medium/High + estimated hours</effort>
<timeline>When to complete</timeline>
<success_metrics>
<metric>How to measure success</metric>
</success_metrics>
<owner>Content team / SEO team</owner>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every content recommendation must include:
1. Specific URL with current metrics
2. Calculated Decay Score with component breakdown
3. Clear KUCK action with rationale
4. Specific updates required (for UPDATE actions)
5. Target page for merge (for CONSOLIDATE actions)
6. Expected traffic recovery (quantified)
7. Implementation timeline
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# CONTENT ANALYSIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Organic Traffic: {organic_traffic}
- Total Ranking Keywords: {keyword_count}

## CONTENT DATA

### Phase 1 Data (Domain Foundation - Top Pages)
{phase1_foundation_json}

### Phase 2 Data (Keyword Rankings by Page)
{phase2_keywords_json}

---

## YOUR TASK

Analyze this content data and provide:

### 1. CONTENT INVENTORY SUMMARY
- Total pages analyzed
- Content type distribution (blog, product, landing, etc.)
- Average content age
- Traffic distribution (top 20% of pages drive X% of traffic)

### 2. CONTENT DECAY ANALYSIS
Calculate Decay Scores and identify:
- Critical decay (score >0.5): Pages needing immediate attention
- Major decay (score 0.3-0.5): Pages for priority refresh
- Light decay (score 0.1-0.3): Pages for scheduled updates
- Healthy content (score <0.1): Pages to monitor

For each decaying page, show:
- URL
- Peak traffic vs current traffic
- Peak position vs current position
- Decay Score with breakdown
- Months since last update (if available)

### 3. CONTENT CANNIBALIZATION AUDIT
Identify keywords where multiple pages compete:
- Keyword being cannibalized
- Competing URLs with their metrics
- Recommended winner page
- Consolidation action

### 4. THIN CONTENT IDENTIFICATION
Find pages that may be hurting the site:
- Pages with <300 words
- Pages with no organic traffic
- Duplicate or near-duplicate content
- Pages with high bounce rates

### 5. KUCK RECOMMENDATIONS
For each content piece, provide clear action:

**KEEP** (Top performers)
- List pages to maintain as-is
- Minor update schedule

**UPDATE** (Decay candidates with potential)
- Specific refresh recommendations
- Expected traffic recovery
- Priority order

**CONSOLIDATE** (Merge opportunities)
- Source pages to merge
- Target page to keep
- Redirect strategy

**KILL** (Remove or noindex)
- Pages not worth maintaining
- Redirect targets (if has backlinks)

### 6. 12-MONTH CONTENT CALENDAR
Prioritized refresh schedule:
- Month 1-3: Critical decays and quick wins
- Month 4-6: Major decays
- Month 7-9: Light decays
- Month 10-12: Maintenance and monitoring

Remember: Be SPECIFIC about URLs and metrics. Calculate ACTUAL decay scores. Provide MEASURABLE expected outcomes.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare content-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        # Add content-specific data
        phase1 = data.get("phase1_foundation", {})
        phase2 = data.get("phase2_keywords", {})

        # Top pages with traffic
        top_pages = phase1.get("top_pages", [])

        # Truncate for token management
        if phase1:
            truncated_phase1 = {
                "domain_overview": phase1.get("domain_overview", {}),
                "top_pages": top_pages[:50],
                "historical_traffic": phase1.get("historical_traffic", [])[:12],
            }
            result["phase1_foundation_json"] = json.dumps(truncated_phase1, indent=2, default=str)

        if phase2:
            truncated_phase2 = {
                "ranked_keywords": phase2.get("ranked_keywords", [])[:100],
                "pages_with_keywords": phase2.get("pages_with_keywords", {})
            }
            # Limit pages_with_keywords to top 50 pages
            if "pages_with_keywords" in truncated_phase2:
                pages = truncated_phase2["pages_with_keywords"]
                if isinstance(pages, dict) and len(pages) > 50:
                    truncated_phase2["pages_with_keywords"] = dict(list(pages.items())[:50])
            result["phase2_keywords_json"] = json.dumps(truncated_phase2, indent=2, default=str)

        return result

"""
Backlink Intelligence Agent

Analyzes link profile and develops strategic link building recommendations:
- Link profile health assessment
- Competitor backlink gap analysis
- Anchor text distribution analysis
- Link building strategy recommendations
- Toxic link identification
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class BacklinkIntelligenceAgent(BaseAgent):
    """
    Backlink Intelligence Agent - Analyzes link profile and builds strategy.

    Responsibilities:
    - Assess current link profile health (DR, referring domains, velocity)
    - Analyze anchor text distribution for naturalness
    - Identify competitor link gaps (domains linking to competitors but not you)
    - Recommend link building strategies based on domain profile
    - Flag toxic/spammy links for disavow consideration
    """

    @property
    def name(self) -> str:
        return "backlink_intelligence"

    @property
    def display_name(self) -> str:
        return "Backlink Intelligence Agent"

    @property
    def description(self) -> str:
        return "Analyzes link profile, identifies gaps, and develops link building strategy"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase1_foundation",  # Domain overview, backlink summary
            "phase3_competitive",  # Competitor backlinks, link gaps
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "link_profile_health", "required": True},
                {"type": "anchor_distribution", "required": True},
                {"type": "competitor_gap", "required": True},
                {"type": "toxic_links", "required": False},
            ],
            "recommendations": [
                {"type": "link_building_strategy", "required": True},
                {"type": "quick_win_links", "required": True},
                {"type": "toxic_cleanup", "required": False},
            ],
            "metrics": {
                "domain_rating": "int",
                "referring_domains": "int",
                "link_velocity": "float",
                "toxic_percentage": "float",
                "competitor_gap_count": "int",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Link Building Strategist with 12 years of experience at premier digital PR and SEO agencies (Siege Media, Fractl, NeoMam Studios). You have secured links from publications including Forbes, TechCrunch, HubSpot, and industry-leading trade publications across dozens of verticals.

Your link building recommendations must be specific, actionable, and achievable for the domain's current authority level. You understand that a DR 30 site cannot execute the same strategies as a DR 70 site.

<behavioral_constraints>
You NEVER say:
- "Build high-quality backlinks" (meaningless - WHICH links from WHERE?)
- "Focus on earning links naturally" (without specific linkable asset recommendations)
- "Reach out to relevant websites" (without naming specific domains or publications)
- "Create link-worthy content" (without specific content specifications)
- "Guest posting opportunities" (without naming target publications and topics)

You ALWAYS:
- Name specific domains/publications to target with their DR and traffic
- Provide specific outreach angles and pitch concepts
- Calculate link gap opportunities with difficulty estimates
- Assess anchor text health with specific recommendations
- Estimate timeline and resource requirements for each strategy
- Assign acquisition difficulty scores (1-10) to target domains
</behavioral_constraints>

<strategy_selection_matrix>
Based on domain characteristics, recommend appropriate strategies:

| Domain DR | Primary Strategies | Secondary Strategies |
|-----------|-------------------|---------------------|
| DR 10-25 | Resource links, Niche directories, HARO | Local citations, Forum links |
| DR 26-40 | Guest posting (tier 2-3), Broken link building | Digital PR (trade), Expert quotes |
| DR 41-55 | Digital PR (mid-tier), Skyscraper, Original research | Podcast guesting, Expert roundups |
| DR 56-70 | Digital PR (top-tier), Data journalism, Tools/calculators | Speaking, Industry reports |
| DR 71+ | Thought leadership, Proprietary data, News jacking | Brand mentions reclamation |
</strategy_selection_matrix>

<anchor_text_guidelines>
Healthy anchor text distribution:
- Branded: 35-50%
- Naked URL: 15-25%
- Generic (click here, learn more): 10-15%
- Partial match: 5-10%
- Exact match: 1-5% (NEVER exceed 10%)

Flag distributions that deviate significantly.
</anchor_text_guidelines>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific, data-driven title</title>
<description>Detailed explanation with numbers</description>
<evidence>Specific data points from backlink analysis</evidence>
<impact>Business impact of this finding</impact>
</finding>

<recommendation priority="N">
<action>Specific link building action</action>
<rationale>Why this strategy fits this domain</rationale>
<target_domains>
<domain dr="X" traffic="Y" difficulty="Z">domain.com - outreach angle</domain>
</target_domains>
<effort>Low/Medium/High</effort>
<impact>Low/Medium/High</impact>
<timeline>Specific timeline</timeline>
<expected_links>Number of links expected</expected_links>
<success_metrics>
<metric>Measurable outcome</metric>
</success_metrics>
<owner>Suggested role/team</owner>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every link building recommendation must include:
1. Specific target domains with DR and estimated traffic
2. Concrete outreach angle or content concept
3. Acquisition difficulty score (1-10)
4. Expected success rate based on domain's current authority
5. Resource requirements (time, content, tools)
6. ROI estimate (link value vs effort)
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# BACKLINK INTELLIGENCE ANALYSIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Total Backlinks: {backlink_count}
- Referring Domains: {referring_domains}
- Current Organic Traffic: {organic_traffic}

## BACKLINK DATA

### Phase 1 Data (Foundation - Backlink Profile)
{phase1_foundation_json}

### Phase 3 Data (Competitive - Link Gaps & Competitor Backlinks)
{phase3_competitive_json}

---

## YOUR TASK

Analyze this backlink data and provide:

### 1. LINK PROFILE HEALTH ASSESSMENT
- Current DR trend (improving/stable/declining)
- Link velocity (new links per month)
- Referring domain quality distribution (by DR tier)
- DoFollow vs NoFollow ratio
- Link type distribution (editorial, guest post, directory, etc.)

### 2. ANCHOR TEXT ANALYSIS
- Current anchor text distribution
- Compare to healthy benchmarks
- Flag any over-optimization risks
- Specific anchor text recommendations

### 3. COMPETITOR LINK GAP ANALYSIS
Identify domains linking to competitors but not this domain:
- Prioritize by DR and relevance
- Calculate acquisition difficulty
- Provide specific outreach angles
- Estimate success probability

### 4. LINK BUILDING STRATEGY RECOMMENDATIONS
Based on the domain's current DR ({domain_rank}), recommend:
- Primary strategy (highest ROI for this authority level)
- Secondary strategies
- Quick wins (easy acquisitions in next 30 days)
- Long-term targets (3-6 month horizon)

For each recommendation:
- Name specific target domains/publications
- Provide outreach angle or content concept
- Estimate effort and expected results
- Calculate link value vs effort ROI

### 5. TOXIC LINK ASSESSMENT (if applicable)
- Identify potentially harmful links
- Recommend disavow actions if needed
- Prioritize by risk level

Remember: Be SPECIFIC. Name ACTUAL domains. Provide REAL outreach angles. Every strategy must be executable TODAY.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare backlink-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        # Add backlink-specific stats
        phase1 = data.get("phase1_foundation", {})
        phase3 = data.get("phase3_competitive", {})

        # Backlink summary
        backlink_summary = phase1.get("backlink_summary", {})
        result["backlink_count"] = backlink_summary.get("total_backlinks", 0)
        result["referring_domains"] = backlink_summary.get("referring_domains", 0)

        # Truncate large arrays for token management
        if phase3:
            truncated_phase3 = {
                "competitor_backlinks": phase3.get("competitor_backlinks", [])[:30],
                "link_gaps": phase3.get("link_gaps", [])[:50],
                "anchor_distribution": phase3.get("anchor_distribution", {}),
                "referring_domains_by_dr": phase3.get("referring_domains_by_dr", {}),
            }
            result["phase3_competitive_json"] = json.dumps(truncated_phase3, indent=2, default=str)

        return result

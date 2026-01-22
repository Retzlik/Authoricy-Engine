"""
Master Strategy Agent

Synthesizes all agent outputs into unified strategy:
- Cross-agent pattern recognition
- Conflict resolution between recommendations
- Priority stack creation (Top 10)
- 90-day implementation roadmap
- Executive summary with key insights
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent, AgentOutput

logger = logging.getLogger(__name__)


class MasterStrategyAgent(BaseAgent):
    """
    Master Strategy Agent - Synthesizes all other agent outputs.

    Responsibilities:
    - Identify patterns across all agent analyses
    - Resolve conflicting recommendations
    - Create unified priority stack (Top 10)
    - Build 90-day implementation roadmap
    - Write executive summary for stakeholder presentation
    - Calculate overall SEO health score
    """

    @property
    def name(self) -> str:
        return "master_strategy"

    @property
    def display_name(self) -> str:
        return "Master Strategy Agent"

    @property
    def description(self) -> str:
        return "Synthesizes all agent outputs into unified strategic roadmap"

    @property
    def required_data(self) -> List[str]:
        return []  # Receives agent outputs, not raw data

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "executive_summary", "required": True},
                {"type": "cross_agent_patterns", "required": True},
                {"type": "conflict_resolutions", "required": True},
                {"type": "synergy_opportunities", "required": True},
            ],
            "recommendations": [
                {"type": "priority_stack", "required": True},
                {"type": "roadmap_phase1", "required": True},
                {"type": "roadmap_phase2", "required": True},
                {"type": "roadmap_phase3", "required": True},
            ],
            "metrics": {
                "overall_seo_score": "float",
                "total_opportunity_value": "float",
                "critical_issues_count": "int",
                "quick_wins_count": "int",
                "strategic_initiatives_count": "int",
                "estimated_traffic_uplift": "float",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are the Chief SEO Strategist at a top-tier digital agency, synthesizing insights from 8 specialized analysts into a unified strategic roadmap. You report directly to C-suite executives and your recommendations must be boardroom-ready.

Your role is to transform detailed technical analyses into clear strategic direction with prioritized actions and measurable outcomes.

<behavioral_constraints>
You NEVER say:
- "Consider improving..." (without specific priority and timeline)
- "There are opportunities in..." (without quantified impact)
- "We recommend focusing on..." (without ranking against alternatives)
- "The data suggests..." (without actionable conclusions)
- "Further analysis needed..." (without specifying what and why)

You ALWAYS:
- Lead with the single most important insight
- Quantify every opportunity (traffic, revenue impact)
- Rank all recommendations by impact/effort ratio
- Resolve conflicts between agent recommendations
- Create dependencies between related actions
- Assign clear ownership and timelines
- Include success metrics for every initiative
</behavioral_constraints>

<synthesis_framework>
Pattern Recognition:
1. SYNERGIES - Recommendations that reinforce each other
   - Content + Link building (create linkable assets)
   - Technical + Content (site speed + content pruning)
   - SERP + AI Visibility (featured snippet + GEO)

2. CONFLICTS - Recommendations that compete for resources
   - Resource conflicts (same team, different priorities)
   - Strategic conflicts (expand vs consolidate)
   - Timing conflicts (sequential dependencies)

3. DEPENDENCIES - What must happen first
   - Technical fixes before content expansion
   - Content audit before link building
   - Site structure before internal linking
</synthesis_framework>

<priority_scoring_matrix>
Impact Score (1-10):
- 10: >50% traffic increase potential
- 8-9: 25-50% traffic increase
- 6-7: 10-25% traffic increase
- 4-5: 5-10% traffic increase
- 1-3: <5% traffic increase

Effort Score (1-10):
- 1-2: Immediate fix (<1 day)
- 3-4: Quick implementation (1-5 days)
- 5-6: Medium project (1-2 weeks)
- 7-8: Major initiative (1 month)
- 9-10: Strategic program (2-3 months)

Priority = Impact / Effort
- Score >3: Critical Priority (Do First)
- Score 2-3: High Priority (This Month)
- Score 1-2: Medium Priority (This Quarter)
- Score <1: Low Priority (Backlog)
</priority_scoring_matrix>

<roadmap_structure>
Phase 1 (Days 1-30): Critical Fixes & Quick Wins
- Technical blockers (indexing, crawl issues)
- Low-effort, high-impact wins
- Foundation for later phases
- Target: Stabilize and quick wins

Phase 2 (Days 31-60): Strategic Initiatives
- Major content projects
- Link building campaigns
- Site architecture improvements
- Target: Growth acceleration

Phase 3 (Days 61-90): Long-term Investments
- Authority building
- New content verticals
- Advanced optimizations
- Target: Sustainable competitive advantage
</roadmap_structure>

<executive_summary_template>
The Headline Metric:
[Single number that captures biggest opportunity/threat]
"This domain is leaving $X/month in organic traffic value on the table"
OR "Without action, expect Y% traffic decline in Z months"

Three Key Findings:
1. [Most impactful opportunity with quantification]
2. [Most critical risk/issue to address]
3. [Competitive insight that informs strategy]

Strategic Direction:
[One-paragraph recommendation for where to focus]
</executive_summary_template>

<output_format>
Structure your response using these XML tags:

<executive_summary>
<headline_metric>Single most important number</headline_metric>
<key_finding priority="1">Finding with quantification</key_finding>
<key_finding priority="2">Finding with quantification</key_finding>
<key_finding priority="3">Finding with quantification</key_finding>
<strategic_direction>One-paragraph strategy recommendation</strategic_direction>
</executive_summary>

<pattern type="synergy|conflict|dependency">
<agents>Agent1, Agent2</agents>
<description>What the pattern is</description>
<resolution>How to address it</resolution>
<impact>Why this matters</impact>
</pattern>

<priority_stack rank="1-10">
<initiative>Initiative name</initiative>
<source_agent>Which agent(s) recommended this</source_agent>
<impact_score>1-10</impact_score>
<effort_score>1-10</effort_score>
<priority_score>Impact/Effort calculation</priority_score>
<expected_outcome>Quantified expected result</expected_outcome>
<dependencies>What must happen first</dependencies>
<owner>Team responsible</owner>
<timeline>Specific timeline</timeline>
<success_metrics>How to measure success</success_metrics>
</priority_stack>

<roadmap phase="1|2|3">
<phase_goal>What this phase achieves</phase_goal>
<initiatives>
<initiative rank="N" owner="Team">Description with deadline</initiative>
</initiatives>
<phase_milestones>
<milestone date="YYYY-MM-DD">Expected achievement</milestone>
</phase_milestones>
<phase_success_metrics>
<metric>How to measure phase success</metric>
</phase_success_metrics>
</roadmap>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every synthesis output must include:
1. Executive summary with headline metric
2. All cross-agent patterns identified and resolved
3. Complete Top 10 priority stack with scores
4. Full 90-day roadmap with milestones
5. Clear ownership for every initiative
6. Measurable success metrics throughout
7. Dependencies explicitly mapped
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# MASTER STRATEGY SYNTHESIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Current Organic Traffic: {organic_traffic}
- Agents Analyzed: {agent_count}

## AGENT OUTPUTS TO SYNTHESIZE

{agent_outputs_json}

---

## YOUR TASK

Synthesize all agent analyses into a unified strategic roadmap:

### 1. EXECUTIVE SUMMARY
Create a boardroom-ready summary:

**Headline Metric:**
The single most important number that captures the biggest opportunity or threat.
Format: "This domain is [doing X] which means [Y impact]"

**Three Key Findings:**
1. Most impactful opportunity (with traffic/revenue quantification)
2. Most critical risk or issue (with urgency framing)
3. Competitive insight that shapes strategy

**Strategic Direction:**
One clear paragraph on recommended focus areas and approach.

### 2. CROSS-AGENT PATTERN ANALYSIS

**Synergies (Opportunities that reinforce each other):**
- Which recommendations from different agents work together?
- How can we combine efforts for multiplied impact?
- What's the combined value of synergistic initiatives?

**Conflicts (Recommendations that compete):**
- Which recommendations compete for the same resources?
- Which strategies contradict each other?
- How do we resolve each conflict?

**Dependencies (What must happen first):**
- Which recommendations depend on others being done first?
- What's the critical path through all recommendations?
- What blockers must be removed before other work can start?

### 3. UNIFIED PRIORITY STACK (Top 10)

Rank ALL recommendations across ALL agents:
- Assign Impact Score (1-10) based on traffic/revenue potential
- Assign Effort Score (1-10) based on resources/time needed
- Calculate Priority Score (Impact / Effort)
- Resolve conflicts (same rank = tiebreaker logic)

For each of the Top 10:
- Initiative name and description
- Source agent(s)
- Impact and effort scores with justification
- Expected quantified outcome
- Dependencies
- Owner (which team)
- Timeline
- Success metrics

### 4. 90-DAY IMPLEMENTATION ROADMAP

**Phase 1 (Days 1-30): Critical Fixes & Quick Wins**
- All technical blockers
- All efforts with Priority Score >3
- Foundation-setting work
- Expected outcomes by Day 30

**Phase 2 (Days 31-60): Strategic Initiatives**
- Major content and link projects
- Site architecture improvements
- Expected outcomes by Day 60

**Phase 3 (Days 61-90): Long-term Investments**
- Authority building
- Competitive positioning
- Expected outcomes by Day 90

For each phase include:
- Specific initiatives with deadlines
- Milestone checkpoints
- Resource requirements
- Success metrics

### 5. OVERALL METRICS

Calculate and report:
- Overall SEO Score (0-100 based on all agents)
- Total Opportunity Value (estimated traffic × $value)
- Critical Issues Count (must-fix items)
- Estimated Traffic Uplift (% over 90 days)

Remember: This output goes directly to executives. Be CLEAR, QUANTIFIED, and ACTIONABLE. No hedging, no vague recommendations.

Begin your synthesis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare synthesis-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        # Agent outputs should be passed in data
        agent_outputs = data.get("agent_outputs", [])
        result["agent_count"] = len(agent_outputs)

        if agent_outputs:
            # Format agent outputs for synthesis
            formatted_outputs = []
            for output in agent_outputs:
                if isinstance(output, AgentOutput):
                    formatted_outputs.append({
                        "agent": output.agent_name,
                        "display_name": output.display_name,
                        "quality_score": output.quality_score,
                        "findings": [
                            f.__dict__ if hasattr(f, '__dict__') else f
                            for f in output.findings[:5]
                        ],
                        "recommendations": [
                            r.__dict__ if hasattr(r, '__dict__') else r
                            for r in output.recommendations[:5]
                        ],
                        "metrics": output.metrics,
                    })
                elif isinstance(output, dict):
                    formatted_outputs.append(output)

            result["agent_outputs_json"] = json.dumps(formatted_outputs, indent=2, default=str)
        else:
            result["agent_outputs_json"] = "No agent outputs provided"

        return result

    async def synthesize(self, agent_outputs: List[AgentOutput], context: Dict[str, Any] = None) -> AgentOutput:
        """
        Synthesize outputs from all other agents.

        This is the primary method for the Master Strategy Agent, called
        after all other agents have completed their analyses.

        Args:
            agent_outputs: List of AgentOutput from all other agents
            context: Optional context with domain info, etc.

        Returns:
            Unified AgentOutput with strategic synthesis
        """
        if not agent_outputs:
            logger.warning("No agent outputs to synthesize")
            return AgentOutput(
                agent_name=self.name,
                display_name=self.display_name,
                findings=[],
                recommendations=[],
                metrics={"overall_seo_score": 0},
                raw_response="No agent outputs provided for synthesis",
                quality_score=0,
            )

        # Prepare synthesis data
        synthesis_data = {
            "agent_outputs": agent_outputs,
        }

        # Add context if provided
        if context:
            synthesis_data.update(context)

        # Calculate aggregate metrics for context
        avg_quality = sum(o.quality_score for o in agent_outputs) / len(agent_outputs)
        total_findings = sum(len(o.findings) for o in agent_outputs)
        total_recommendations = sum(len(o.recommendations) for o in agent_outputs)

        logger.info(
            f"Synthesizing {len(agent_outputs)} agents: "
            f"avg quality={avg_quality:.1f}, "
            f"findings={total_findings}, "
            f"recommendations={total_recommendations}"
        )

        # Use the standard analyze method with synthesized data
        return await self.analyze(synthesis_data)

    def calculate_overall_seo_score(self, agent_outputs: List[AgentOutput]) -> float:
        """
        Calculate overall SEO health score from all agent outputs.

        Weights:
        - Technical SEO: 20%
        - Content Analysis: 20%
        - Backlink Intelligence: 15%
        - Keyword Intelligence: 15%
        - Semantic Architecture: 10%
        - SERP Analysis: 10%
        - AI Visibility: 5%
        - Local SEO: 5% (if applicable)

        Returns:
            Overall SEO score (0-100)
        """
        weights = {
            "technical_seo": 0.20,
            "content_analysis": 0.20,
            "backlink_intelligence": 0.15,
            "keyword_intelligence": 0.15,
            "semantic_architecture": 0.10,
            "serp_analysis": 0.10,
            "ai_visibility": 0.05,
            "local_seo": 0.05,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for output in agent_outputs:
            agent_name = output.agent_name
            if agent_name in weights:
                # Use agent's quality score as health indicator
                # Scale from quality score (0-100) to contribution
                agent_score = output.metrics.get("health_score", output.quality_score)
                weighted_sum += agent_score * weights[agent_name]
                total_weight += weights[agent_name]

        if total_weight > 0:
            return round(weighted_sum / total_weight, 1)
        return 0.0

    def identify_critical_issues(self, agent_outputs: List[AgentOutput]) -> List[Dict[str, Any]]:
        """
        Extract all critical issues from agent outputs.

        Returns list of critical issues with source agent.
        """
        critical_issues = []

        for output in agent_outputs:
            for finding in output.findings:
                # Check if finding is critical priority
                priority = getattr(finding, 'priority', None) or finding.get('priority', 99)
                if priority == 1:  # Critical
                    critical_issues.append({
                        "source_agent": output.agent_name,
                        "title": getattr(finding, 'title', '') or finding.get('title', ''),
                        "description": getattr(finding, 'description', '') or finding.get('description', ''),
                        "impact": getattr(finding, 'impact', '') or finding.get('impact', ''),
                    })

        return critical_issues

    def identify_quick_wins(self, agent_outputs: List[AgentOutput]) -> List[Dict[str, Any]]:
        """
        Extract quick wins (high impact, low effort) from agent outputs.

        Returns list of quick wins with source agent.
        """
        quick_wins = []

        for output in agent_outputs:
            for rec in output.recommendations:
                effort = getattr(rec, 'effort', '') or rec.get('effort', '')
                impact = getattr(rec, 'impact', '') or rec.get('impact', '')

                # Quick win = Low effort + High impact
                if effort.lower() == 'low' and impact.lower() == 'high':
                    quick_wins.append({
                        "source_agent": output.agent_name,
                        "action": getattr(rec, 'action', '') or rec.get('action', ''),
                        "impact": impact,
                        "effort": effort,
                    })

        return quick_wins

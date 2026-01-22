"""
Keyword Intelligence Agent

Analyzes keyword portfolio and identifies opportunities using:
- Opportunity Score calculations
- Personalized Difficulty (MarketMuse methodology)
- Competitor gap analysis
- Quick win identification

This is the FIRST agent in the analysis pipeline.
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class KeywordIntelligenceAgent(BaseAgent):
    """
    Keyword Intelligence Agent - Analyzes keyword portfolio and opportunities.

    Responsibilities:
    - Analyze current keyword rankings and distribution
    - Calculate Opportunity Scores for all keywords
    - Identify quick wins (high opportunity, low difficulty)
    - Perform competitor keyword gap analysis
    - Recommend keyword targeting strategy
    """

    @property
    def name(self) -> str:
        return "keyword_intelligence"

    @property
    def display_name(self) -> str:
        return "Keyword Intelligence Agent"

    @property
    def description(self) -> str:
        return "Analyzes keyword portfolio, identifies opportunities, and recommends targeting strategy"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase1_foundation",  # Domain overview
            "phase2_keywords",    # Keyword data
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "portfolio_health", "required": True},
                {"type": "competitor_gap", "required": True},
                {"type": "opportunity_analysis", "required": True},
            ],
            "recommendations": [
                {"type": "quick_wins", "required": True},
                {"type": "strategic_targets", "required": True},
                {"type": "keywords_to_defend", "required": False},
            ],
            "metrics": {
                "keyword_health_score": "float",
                "total_ranking_keywords": "int",
                "quick_win_count": "int",
                "estimated_traffic_opportunity": "int",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Keyword Strategist with 15 years of experience at enterprise SEO agencies (BrightEdge, Conductor, iProspect, Terakeet). You have personally managed keyword strategies for Fortune 500 companies including Microsoft, Salesforce, and Adobe.

Your analysis quality must match what a €15,000/month agency delivers after 3 months of deep analysis. If a CMO could apply your analysis to any other website without modification, you have failed.

<behavioral_constraints>
You NEVER say:
- "Consider focusing on long-tail keywords" (too vague - WHICH keywords?)
- "Build topical authority" (without a specific topic map with exact keywords)
- "Create quality content" (meaningless without specific content specifications)
- "Target high-intent keywords" (without listing specific keywords with volumes)
- "Optimize for search intent" (without explaining exactly how)
- "Improve keyword rankings" (without specific target positions and timelines)

You ALWAYS:
- Reference specific numbers from the data (search volume, position, KD, traffic, etc.)
- Name exact keywords with their metrics (e.g., "Target 'enterprise project management software' [2,400 vol, KD 52, current pos 15]")
- Compare against specific competitors with data
- Provide measurable targets with timelines
- Calculate and show Opportunity Scores
- Show Personalized Difficulty based on domain's authority
- Assign confidence levels (0.0-1.0) to predictions
</behavioral_constraints>

<quality_standard>
Every finding must include:
1. Specific data point (number, percentage, or metric)
2. Comparison context (vs competitors, vs benchmark, vs previous period)
3. Business impact statement
4. Confidence level

Every recommendation must include:
1. Exact keyword(s) with full metrics
2. Specific action to take
3. Target URL (existing or new)
4. Expected outcome with timeline
5. Priority level (P1/P2/P3)
6. Effort estimate
</quality_standard>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific, data-driven title</title>
<description>Detailed explanation with numbers</description>
<evidence>Specific data points</evidence>
<impact>Business impact statement</impact>
</finding>

<recommendation priority="N">
<action>Specific action with exact keywords</action>
<rationale>Why this matters with data</rationale>
<effort>Low/Medium/High</effort>
<impact>Low/Medium/High</impact>
<timeline>Specific timeline</timeline>
<success_metrics>
<metric>Measurable outcome 1</metric>
<metric>Measurable outcome 2</metric>
</success_metrics>
<owner>Suggested role/team</owner>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<scoring_formulas>
Opportunity Score (0-100):
= Volume_Score(20%) + Difficulty_Inverse(20%) + Intent_Score(20%) + Position_Gap(20%) + Topical_Alignment(20%)

Personalized Difficulty:
= Base_KD × (1 - Authority_Advantage)
Where Authority_Advantage = min(0.5, DR_Gap/100 + Topical_Bonus)

Quick Win Criteria:
- Opportunity Score ≥ 70
- Personalized Difficulty ≤ 40
- Current position 11-30 OR not ranking
</scoring_formulas>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# KEYWORD INTELLIGENCE ANALYSIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Current Organic Traffic: {organic_traffic:,}

## KEYWORD DATA

### Current Rankings Summary
Total ranking keywords: {keyword_count:,}

### Phase 1 Data (Domain Foundation)
{phase1_foundation_json}

### Phase 2 Data (Keyword Intelligence)
{phase2_keywords_json}

---

## YOUR TASK

Analyze this keyword data and provide:

### 1. PORTFOLIO HEALTH ANALYSIS
- Current position distribution (top 3, 4-10, 11-20, 21-50, 51-100)
- Intent distribution (transactional, commercial, informational, navigational)
- Trend analysis (improving, stable, declining)
- Comparison to competitor keyword portfolios

### 2. OPPORTUNITY IDENTIFICATION
Calculate Opportunity Scores for keywords and identify:
- Top 10 Quick Wins (high opportunity, low personalized difficulty)
- Top 10 Strategic Targets (high value, medium-long term)
- Keywords at risk (declining positions, competitors gaining)

### 3. COMPETITOR GAP ANALYSIS
- Keywords competitors rank for that this domain doesn't
- Prioritize gaps by opportunity score
- Identify low-hanging fruit gaps

### 4. SPECIFIC RECOMMENDATIONS
For each recommended keyword target, provide:
- Exact keyword with volume, KD, current position (if any)
- Personalized Difficulty calculation
- Opportunity Score
- Target URL (existing page to optimize OR new page to create)
- Specific action steps
- Expected traffic gain
- Timeline to achieve target position
- Confidence level

Remember: Be SPECIFIC. Use EXACT numbers. Reference ACTUAL data. Every recommendation must be actionable TODAY.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare keyword-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        # Add keyword-specific summary stats
        phase2 = data.get("phase2_keywords", {})

        # Count keywords by position
        ranked_keywords = phase2.get("ranked_keywords", [])
        position_counts = {"top_3": 0, "4_10": 0, "11_20": 0, "21_50": 0, "51_100": 0}

        for kw in ranked_keywords[:500]:  # Limit for token management
            pos = kw.get("position", 100)
            if pos <= 3:
                position_counts["top_3"] += 1
            elif pos <= 10:
                position_counts["4_10"] += 1
            elif pos <= 20:
                position_counts["11_20"] += 1
            elif pos <= 50:
                position_counts["21_50"] += 1
            else:
                position_counts["51_100"] += 1

        result["position_distribution"] = json.dumps(position_counts)

        # Truncate large arrays for token management
        if "phase2_keywords_json" in result:
            phase2_data = data.get("phase2_keywords", {})
            truncated = {
                "ranked_keywords": phase2_data.get("ranked_keywords", [])[:100],
                "keyword_gaps": phase2_data.get("keyword_gaps", [])[:50],
                "keyword_suggestions": phase2_data.get("keyword_suggestions", [])[:50],
                "intent_data": phase2_data.get("intent_data", {}),
            }
            result["phase2_keywords_json"] = json.dumps(truncated, indent=2, default=str)

        return result

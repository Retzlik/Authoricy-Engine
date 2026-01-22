"""
Backlink Intelligence Agent

Analyzes link profile and develops link building strategy.
"""

from typing import Dict, Any, List
from .base import BaseAgent


class BacklinkIntelligenceAgent(BaseAgent):
    """Backlink analysis and link building strategy agent."""

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
        return ["phase1_foundation", "phase3_competitive"]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [{"type": "link_profile_health"}, {"type": "competitor_analysis"}],
            "recommendations": [{"type": "link_building_strategy"}, {"type": "toxic_cleanup"}],
            "metrics": {"domain_rating": "int", "referring_domains": "int"},
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Link Building Strategist with 12 years experience at top agencies.
[Full prompt to be implemented in Phase 3]"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# BACKLINK ANALYSIS
Domain: {domain}
{phase1_foundation_json}
{phase3_competitive_json}
Analyze the backlink profile and provide recommendations."""

"""
Content Analysis Agent

Analyzes content inventory and detects decay.
"""

from typing import Dict, Any, List
from .base import BaseAgent


class ContentAnalysisAgent(BaseAgent):
    """Content inventory and decay detection agent."""

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
        return ["phase1_foundation", "phase2_keywords"]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [{"type": "content_inventory"}, {"type": "decay_analysis"}],
            "recommendations": [{"type": "content_action"}, {"type": "content_calendar"}],
            "metrics": {"content_health_score": "float", "pages_needing_refresh": "int"},
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Content Strategist specializing in content audits and optimization.
[Full prompt to be implemented in Phase 3]"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# CONTENT ANALYSIS
Domain: {domain}
{phase1_foundation_json}
{phase2_keywords_json}
Analyze content and recommend Keep/Update/Consolidate/Kill actions."""

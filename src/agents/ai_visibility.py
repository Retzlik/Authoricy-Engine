"""
AI Visibility Agent

Analyzes AI Overview presence and GEO optimization.
"""

from typing import Dict, Any, List
from .base import BaseAgent


class AIVisibilityAgent(BaseAgent):
    """AI visibility and GEO optimization agent."""

    @property
    def name(self) -> str:
        return "ai_visibility"

    @property
    def display_name(self) -> str:
        return "AI Visibility Agent"

    @property
    def description(self) -> str:
        return "Analyzes AI Overview presence and provides GEO optimization recommendations"

    @property
    def required_data(self) -> List[str]:
        return ["phase2_keywords", "phase4_ai_technical"]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [{"type": "ai_overview_analysis"}, {"type": "geo_readiness"}],
            "recommendations": [{"type": "geo_optimization"}, {"type": "citation_opportunity"}],
            "metrics": {"ai_visibility_score": "float", "ai_overview_presence": "float"},
        }

    @property
    def system_prompt(self) -> str:
        return """You are an AI Search Specialist focusing on AI Overviews and Generative Engine Optimization.
[Full prompt to be implemented in Phase 3]"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# AI VISIBILITY ANALYSIS
Domain: {domain}
{phase2_keywords_json}
{phase4_ai_technical_json}
Analyze AI visibility and recommend GEO optimizations."""

"""
SERP Analysis Agent

Analyzes SERP features and content format requirements.
"""

from typing import Dict, Any, List
from .base import BaseAgent


class SERPAnalysisAgent(BaseAgent):
    """SERP feature and content format analysis agent."""

    @property
    def name(self) -> str:
        return "serp_analysis"

    @property
    def display_name(self) -> str:
        return "SERP Analysis Agent"

    @property
    def description(self) -> str:
        return "Analyzes SERP features, content formats, and identifies opportunities"

    @property
    def required_data(self) -> List[str]:
        return ["phase2_keywords", "phase4_ai_technical"]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [{"type": "serp_features"}, {"type": "content_format_analysis"}],
            "recommendations": [{"type": "featured_snippet_target"}, {"type": "content_format_recommendation"}],
            "metrics": {"serp_feature_opportunity_score": "float", "featured_snippet_opportunities": "int"},
        }

    @property
    def system_prompt(self) -> str:
        return """You are a SERP Analyst specializing in feature optimization and content format strategy.
[Full prompt to be implemented in Phase 3]"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# SERP ANALYSIS
Domain: {domain}
{phase2_keywords_json}
{phase4_ai_technical_json}
Analyze SERP features and recommend content format optimizations."""

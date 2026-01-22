"""
Technical SEO Agent

Analyzes technical SEO issues and Core Web Vitals.
"""

from typing import Dict, Any, List
from .base import BaseAgent


class TechnicalSEOAgent(BaseAgent):
    """Technical SEO audit and CWV analysis agent."""

    @property
    def name(self) -> str:
        return "technical_seo"

    @property
    def display_name(self) -> str:
        return "Technical SEO Agent"

    @property
    def description(self) -> str:
        return "Audits technical SEO issues and Core Web Vitals performance"

    @property
    def required_data(self) -> List[str]:
        return ["phase1_foundation", "phase4_ai_technical"]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [{"type": "core_web_vitals"}, {"type": "crawl_issues"}],
            "recommendations": [{"type": "critical_fix"}, {"type": "performance_optimization"}],
            "metrics": {"technical_health_score": "float", "lcp_score": "float"},
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Technical SEO Specialist with deep expertise in site architecture and Core Web Vitals.
[Full prompt to be implemented in Phase 3]"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# TECHNICAL SEO ANALYSIS
Domain: {domain}
{phase1_foundation_json}
{phase4_ai_technical_json}
Analyze technical issues and provide recommendations."""

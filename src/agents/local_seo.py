"""
Local SEO Agent (Conditional)

Analyzes local SEO factors when local signals are detected.
"""

from typing import Dict, Any, List
from .base import BaseAgent


class LocalSEOAgent(BaseAgent):
    """Local SEO analysis agent (conditional activation)."""

    @property
    def name(self) -> str:
        return "local_seo"

    @property
    def display_name(self) -> str:
        return "Local SEO Agent"

    @property
    def description(self) -> str:
        return "Analyzes local SEO factors including GBP, citations, and local rankings"

    @property
    def required_data(self) -> List[str]:
        return ["phase1_foundation"]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [{"type": "gbp_analysis"}, {"type": "citation_analysis"}],
            "recommendations": [{"type": "gbp_optimization"}, {"type": "citation_building"}],
            "metrics": {"local_visibility_score": "float", "nap_consistency_score": "float"},
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Local SEO Expert specializing in Google Business Profile and local search optimization.
[Full prompt to be implemented in Phase 3]"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# LOCAL SEO ANALYSIS
Domain: {domain}
{phase1_foundation_json}
Analyze local SEO factors and recommend improvements."""

    @staticmethod
    def should_activate(collected_data: Dict[str, Any]) -> bool:
        """Determine if local SEO analysis is needed."""
        domain_overview = collected_data.get("phase1_foundation", {}).get("domain_overview", {})
        # Check for local signals
        has_local_keywords = any(
            "near me" in str(kw).lower() or "local" in str(kw).lower()
            for kw in collected_data.get("phase2_keywords", {}).get("ranked_keywords", [])[:100]
        )
        has_gbp = bool(domain_overview.get("google_business_profile"))
        return has_local_keywords or has_gbp

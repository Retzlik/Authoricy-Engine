"""
Master Strategy Agent

Synthesizes all agent outputs into unified strategy.
"""

from typing import Dict, Any, List
from .base import BaseAgent, AgentOutput


class MasterStrategyAgent(BaseAgent):
    """Master synthesis agent that combines all other agent outputs."""

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
            "findings": [{"type": "executive_summary"}, {"type": "cross_agent_patterns"}],
            "recommendations": [{"type": "priority_stack"}, {"type": "roadmap"}],
            "metrics": {"overall_seo_score": "float", "total_opportunity_value": "float"},
        }

    @property
    def system_prompt(self) -> str:
        return """You are the Chief SEO Strategist synthesizing insights from 8 specialized analysts.

Your role is to:
1. Identify patterns across all analyses
2. Resolve any conflicting recommendations
3. Create a unified priority stack (Top 10)
4. Build a 90-day implementation roadmap
5. Write an executive summary with the single most important insight

Quality standard: Your output must be boardroom-ready. A CEO should be able to present this directly.

[Full prompt to be implemented in Phase 3]"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# MASTER STRATEGY SYNTHESIS

## AGENT OUTPUTS TO SYNTHESIZE

{agent_outputs_json}

## YOUR TASK

1. EXECUTIVE SUMMARY
   - Single headline metric that captures the biggest opportunity/threat
   - 3 key findings across all analyses
   - Recommended strategic direction

2. CROSS-AGENT PATTERNS
   - Synergies (opportunities that reinforce each other)
   - Conflicts (recommendations that need resolution)
   - Dependencies (what must happen first)

3. UNIFIED PRIORITY STACK (Top 10)
   - Rank all recommendations by impact/effort
   - Ensure no conflicts
   - Clear ownership and timeline

4. 90-DAY ROADMAP
   - Phase 1 (Days 1-30): Quick wins and critical fixes
   - Phase 2 (Days 31-60): Strategic initiatives
   - Phase 3 (Days 61-90): Long-term investments

Begin your synthesis:"""

    async def synthesize(self, agent_outputs: List[AgentOutput]) -> AgentOutput:
        """
        Synthesize outputs from all other agents.

        Args:
            agent_outputs: List of AgentOutput from all other agents

        Returns:
            Unified AgentOutput with strategic synthesis
        """
        import json

        # Prepare synthesis data
        synthesis_data = {
            "agent_outputs": [
                {
                    "agent": output.agent_name,
                    "findings": [f.__dict__ if hasattr(f, '__dict__') else f for f in output.findings[:5]],
                    "recommendations": [r.__dict__ if hasattr(r, '__dict__') else r for r in output.recommendations[:5]],
                    "metrics": output.metrics,
                    "quality_score": output.quality_score,
                }
                for output in agent_outputs
            ],
            "metadata": {
                "total_agents": len(agent_outputs),
                "avg_quality_score": sum(o.quality_score for o in agent_outputs) / len(agent_outputs) if agent_outputs else 0,
            }
        }

        # Use the standard analyze method with synthesized data
        return await self.analyze({"agent_outputs_json": json.dumps(synthesis_data, indent=2, default=str)})

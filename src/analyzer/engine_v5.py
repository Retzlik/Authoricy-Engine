"""
Analysis Engine v5 - 9-Agent Architecture

Orchestrates 9 specialized AI agents for comprehensive SEO analysis:

Primary Agents (run in parallel):
1. Keyword Intelligence Agent
2. Backlink Intelligence Agent
3. Technical SEO Agent
4. Content Analysis Agent
5. Semantic Architecture Agent
6. AI Visibility Agent
7. SERP Analysis Agent

Conditional Agent:
8. Local SEO Agent (runs if local signals detected)

Synthesis Agent:
9. Master Strategy Agent (synthesizes all outputs)

Quality Gate: 23/25 checks must pass (92%) for output to be accepted.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .client import ClaudeClient

from ..agents import (
    KeywordIntelligenceAgent,
    BacklinkIntelligenceAgent,
    TechnicalSEOAgent,
    ContentAnalysisAgent,
    SemanticArchitectureAgent,
    AIVisibilityAgent,
    SERPAnalysisAgent,
    LocalSEOAgent,
    MasterStrategyAgent,
    AgentOutput,
)

from ..quality import AgentQualityChecker
from ..output import AgentOutputConverter, BatchOutputConverter

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResultV5:
    """Complete analysis result from v5 9-agent architecture."""

    # Metadata
    domain: str
    market: str
    timestamp: datetime
    duration_seconds: float

    # Agent outputs
    agent_outputs: Dict[str, AgentOutput]
    master_output: AgentOutput

    # Quality metrics
    quality_score: float  # 0-10 scale
    passed_quality_gate: bool
    checks_passed: int
    checks_failed: int
    failed_checks: List[str]

    # Aggregate metrics
    overall_seo_score: float  # 0-100 scale
    total_findings: int
    total_recommendations: int
    critical_issues: int
    quick_wins: int

    # Cost tracking
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def executive_summary(self) -> str:
        """Get executive summary from master output."""
        if self.master_output and self.master_output.structured_data:
            return self.master_output.structured_data.get("executive_summary", {}).get(
                "headline_metric", ""
            )
        return ""

    @property
    def priority_stack(self) -> List[Dict[str, Any]]:
        """Get priority stack from master output."""
        if self.master_output and self.master_output.structured_data:
            return self.master_output.structured_data.get("priority_stack", [])
        return []

    @property
    def roadmap(self) -> List[Dict[str, Any]]:
        """Get roadmap phases from master output."""
        if self.master_output and self.master_output.structured_data:
            return self.master_output.structured_data.get("roadmap", [])
        return []


class AnalysisEngineV5:
    """
    v5 Analysis Engine with 9 specialized agents.

    Architecture:
    1. Initialize Claude client and all agents
    2. Run 7 primary agents in parallel
    3. Conditionally run Local SEO agent
    4. Run Master Strategy agent to synthesize
    5. Enforce quality gate (23/25 checks)
    6. Retry with feedback if quality fails

    Usage:
        engine = AnalysisEngineV5(api_key="...")
        result = await engine.analyze(collected_data)
    """

    QUALITY_THRESHOLD = 9.2  # 92% = 23/25 checks passing

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize v5 analysis engine.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
        """
        self.client = ClaudeClient(api_key=api_key)
        self.quality_checker = AgentQualityChecker()
        self.output_converter = AgentOutputConverter()

        # Initialize all 9 agents
        self.agents = {
            "keyword_intelligence": KeywordIntelligenceAgent(self.client),
            "backlink_intelligence": BacklinkIntelligenceAgent(self.client),
            "technical_seo": TechnicalSEOAgent(self.client),
            "content_analysis": ContentAnalysisAgent(self.client),
            "semantic_architecture": SemanticArchitectureAgent(self.client),
            "ai_visibility": AIVisibilityAgent(self.client),
            "serp_analysis": SERPAnalysisAgent(self.client),
            "local_seo": LocalSEOAgent(self.client),
            "master_strategy": MasterStrategyAgent(self.client),
        }

        logger.info("AnalysisEngineV5 initialized with 9 agents")

    async def analyze(
        self,
        collected_data: Dict[str, Any],
        max_retries: int = 1,
    ) -> AnalysisResultV5:
        """
        Run complete 9-agent analysis.

        Args:
            collected_data: Compiled data from collector phases
            max_retries: Max retries if quality gate fails

        Returns:
            AnalysisResultV5 with all agent outputs
        """
        start_time = datetime.utcnow()
        metadata = collected_data.get("metadata", {})
        domain = metadata.get("domain", "unknown")
        market = metadata.get("market", "unknown")

        logger.info(f"Starting v5 analysis for {domain} ({market})")

        # ================================================================
        # STEP 1: Run primary agents in parallel
        # ================================================================
        logger.info("Step 1: Running 7 primary agents in parallel...")

        primary_agent_names = [
            "keyword_intelligence",
            "backlink_intelligence",
            "technical_seo",
            "content_analysis",
            "semantic_architecture",
            "ai_visibility",
            "serp_analysis",
        ]

        primary_tasks = [
            self._run_agent_safe(name, collected_data)
            for name in primary_agent_names
        ]

        primary_results = await asyncio.gather(*primary_tasks)

        # Build outputs dict
        agent_outputs = {}
        for name, output in zip(primary_agent_names, primary_results):
            if output:
                agent_outputs[name] = output
                logger.info(f"  {name}: quality={output.quality_score:.1f}")
            else:
                logger.warning(f"  {name}: FAILED")

        # ================================================================
        # STEP 2: Run Local SEO agent if applicable
        # ================================================================
        if self._needs_local_seo(collected_data):
            logger.info("Step 2: Running Local SEO agent (local signals detected)...")
            local_output = await self._run_agent_safe("local_seo", collected_data)
            if local_output:
                agent_outputs["local_seo"] = local_output
                logger.info(f"  local_seo: quality={local_output.quality_score:.1f}")
        else:
            logger.info("Step 2: Skipping Local SEO (no local signals)")

        # ================================================================
        # STEP 3: Run Master Strategy synthesis
        # ================================================================
        logger.info("Step 3: Running Master Strategy synthesis...")

        master_agent = self.agents["master_strategy"]
        outputs_list = list(agent_outputs.values())

        master_output = await master_agent.synthesize(
            outputs_list,
            context={"domain": domain, "market": market, **metadata}
        )

        logger.info(f"  master_strategy: quality={master_output.quality_score:.1f}")
        agent_outputs["master_strategy"] = master_output

        # ================================================================
        # STEP 4: Quality gate check
        # ================================================================
        logger.info("Step 4: Quality gate check...")

        quality_score = master_output.quality_score
        passed_gate = quality_score >= self.QUALITY_THRESHOLD

        logger.info(f"  Quality: {quality_score:.1f}/10, threshold={self.QUALITY_THRESHOLD}")

        # ================================================================
        # STEP 5: Retry with feedback if needed
        # ================================================================
        retry_count = 0
        while not passed_gate and retry_count < max_retries:
            retry_count += 1
            logger.info(f"Step 5: Quality gate failed, retry {retry_count}/{max_retries}...")

            master_output = await self._retry_with_feedback(
                master_output, outputs_list, collected_data
            )
            quality_score = master_output.quality_score
            passed_gate = quality_score >= self.QUALITY_THRESHOLD
            agent_outputs["master_strategy"] = master_output

            logger.info(f"  Retry quality: {quality_score:.1f}/10")

        # ================================================================
        # STEP 6: Calculate aggregate metrics
        # ================================================================
        duration = (datetime.utcnow() - start_time).total_seconds()
        usage = self.client.get_usage_summary()

        # Count findings and recommendations
        total_findings = sum(len(o.findings) for o in agent_outputs.values())
        total_recs = sum(len(o.recommendations) for o in agent_outputs.values())

        # Calculate overall SEO score
        overall_score = master_agent.calculate_overall_seo_score(outputs_list)

        # Count critical issues and quick wins
        critical = len(master_agent.identify_critical_issues(outputs_list))
        quick_wins = len(master_agent.identify_quick_wins(outputs_list))

        # Get failed checks
        failed_checks = []
        if master_output.quality_checks:
            failed_checks = [k for k, v in master_output.quality_checks.items() if not v]

        logger.info(
            f"Analysis complete: {duration:.1f}s, "
            f"quality={quality_score:.1f}, passed={passed_gate}, "
            f"findings={total_findings}, recs={total_recs}"
        )

        return AnalysisResultV5(
            domain=domain,
            market=market,
            timestamp=start_time,
            duration_seconds=duration,
            agent_outputs=agent_outputs,
            master_output=master_output,
            quality_score=quality_score,
            passed_quality_gate=passed_gate,
            checks_passed=master_output.checks_passed if master_output else 0,
            checks_failed=master_output.checks_failed if master_output else 25,
            failed_checks=failed_checks,
            overall_seo_score=overall_score,
            total_findings=total_findings,
            total_recommendations=total_recs,
            critical_issues=critical,
            quick_wins=quick_wins,
            total_tokens=usage.get("total_tokens", 0),
            total_cost_usd=usage.get("estimated_cost", 0.0),
            raw_data=collected_data,
        )

    async def _run_agent_safe(
        self,
        agent_name: str,
        data: Dict[str, Any]
    ) -> Optional[AgentOutput]:
        """
        Run an agent with error handling.

        Returns None if agent fails.
        """
        try:
            agent = self.agents[agent_name]
            output = await agent.analyze(data)
            return output
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            return None

    def _needs_local_seo(self, data: Dict[str, Any]) -> bool:
        """Check if local SEO analysis is needed."""
        return LocalSEOAgent.should_activate(data)

    async def _retry_with_feedback(
        self,
        failed_output: AgentOutput,
        primary_outputs: List[AgentOutput],
        collected_data: Dict[str, Any],
    ) -> AgentOutput:
        """
        Retry master synthesis with feedback on what failed.

        Args:
            failed_output: Previous output that failed quality gate
            primary_outputs: All primary agent outputs
            collected_data: Original collected data

        Returns:
            New AgentOutput from retry attempt
        """
        # Build feedback from failed checks
        failed_checks = []
        if failed_output.quality_checks:
            failed_checks = [k for k, v in failed_output.quality_checks.items() if not v]

        feedback = f"""
Your previous output failed the quality gate. Please improve on these areas:

Failed checks: {', '.join(failed_checks[:5])}

Requirements:
- Include specific numbers and metrics (not vague qualifiers)
- Reference actual URLs and pages from the domain
- Provide measurable targets for each recommendation
- Include effort and impact estimates for all actions
- Assign owners to recommendations
- Avoid placeholder text or generic best practices

Please regenerate the synthesis with these improvements.
"""

        # Prepare retry data
        retry_data = {
            "feedback": feedback,
            "previous_quality_score": failed_output.quality_score,
            "failed_checks": failed_checks,
        }

        # Re-run master synthesis
        master_agent = self.agents["master_strategy"]
        metadata = collected_data.get("metadata", {})

        return await master_agent.synthesize(
            primary_outputs,
            context={
                "domain": metadata.get("domain", ""),
                "market": metadata.get("market", ""),
                "retry_feedback": feedback,
                **metadata,
            }
        )

    async def analyze_single_agent(
        self,
        agent_name: str,
        collected_data: Dict[str, Any],
    ) -> Optional[AgentOutput]:
        """
        Run a single agent for testing/debugging.

        Args:
            agent_name: Name of agent to run
            collected_data: Data to analyze

        Returns:
            AgentOutput or None if failed
        """
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")

        return await self._run_agent_safe(agent_name, collected_data)

    def get_agent_names(self) -> List[str]:
        """Get list of all agent names."""
        return list(self.agents.keys())


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_analysis_engine(
    api_key: Optional[str] = None,
    version: str = "v5"
) -> "AnalysisEngineV5":
    """
    Factory function to create analysis engine.

    Args:
        api_key: Anthropic API key
        version: Engine version ("v5" for 9-agent, "v4" for 4-loop)

    Returns:
        AnalysisEngineV5 instance
    """
    if version == "v5":
        return AnalysisEngineV5(api_key=api_key)
    else:
        raise ValueError(f"Unknown engine version: {version}. Use 'v5'.")

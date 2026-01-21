"""
Analysis Engine - Orchestrates the 4-loop analysis architecture.

This engine coordinates:
1. Loop 1: Data Interpretation
2. Loop 2: Strategic Synthesis
3. Loop 3: SERP & Competitor Enrichment
4. Loop 4: Quality Review & Executive Summary
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .client import ClaudeClient, TokenUsage
from .loop1 import DataInterpreter
from .loop2 import StrategicSynthesizer
from .loop3 import SERPEnricher
from .loop4 import QualityReviewer

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Complete analysis result from all loops."""

    # Metadata
    domain: str
    timestamp: datetime
    duration_seconds: float

    # Loop outputs
    loop1_findings: str  # Structured findings
    loop2_strategy: str  # Strategic recommendations
    loop3_enrichment: str  # SERP & competitive intelligence
    loop4_review: str  # Quality review
    executive_summary: str  # Final executive summary

    # Quality metrics
    quality_score: float  # 0-10
    quality_checks: Dict[str, bool] = field(default_factory=dict)
    passed_quality_gate: bool = False

    # Token usage
    total_tokens: int = 0
    total_cost: float = 0.0

    # Raw data for reports
    raw_analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainClassification:
    """Classification of domain for adaptive analysis."""

    size_tier: str  # "<1K", "1K-10K", "10K-100K", ">100K"
    industry: str  # "SaaS", "Manufacturing", "Professional Services", "Other"
    competitive_intensity: str  # "Low", "Medium", "High"
    technical_maturity: str  # "Basic", "Intermediate", "Advanced"

    @classmethod
    def from_data(cls, analysis_data: Dict[str, Any]) -> "DomainClassification":
        """Classify domain based on collected data."""
        summary = analysis_data.get("summary", {})
        foundation = analysis_data.get("phase1_foundation", {})

        # Size tier based on keywords
        keywords = summary.get("total_organic_keywords", 0)
        if keywords < 1000:
            size_tier = "<1K"
        elif keywords < 10000:
            size_tier = "1K-10K"
        elif keywords < 100000:
            size_tier = "10K-100K"
        else:
            size_tier = ">100K"

        # Industry detection (simplified - can be enhanced)
        technologies = foundation.get("technologies", [])
        tech_names = [t.get("name", "").lower() for t in technologies]

        if any(t in tech_names for t in ["hubspot", "salesforce", "intercom"]):
            industry = "SaaS"
        elif any(t in tech_names for t in ["shopify", "woocommerce", "magento"]):
            industry = "E-commerce"
        else:
            industry = "General"

        # Competitive intensity based on competitor count and overlap
        competitors = summary.get("competitor_count", 0)
        if competitors > 15:
            competitive_intensity = "High"
        elif competitors > 5:
            competitive_intensity = "Medium"
        else:
            competitive_intensity = "Low"

        # Technical maturity based on Lighthouse scores
        technical = foundation.get("technical_baseline", {})
        perf_score = technical.get("performance_score", 0)
        if perf_score >= 0.8:
            technical_maturity = "Advanced"
        elif perf_score >= 0.5:
            technical_maturity = "Intermediate"
        else:
            technical_maturity = "Basic"

        return cls(
            size_tier=size_tier,
            industry=industry,
            competitive_intensity=competitive_intensity,
            technical_maturity=technical_maturity,
        )


class AnalysisEngine:
    """
    Main analysis engine coordinating all 4 loops.

    This engine implements the analysis architecture from the specification:
    - Sequential loop execution with dependency passing
    - Quality gate enforcement (score ≥8/10)
    - Cost and token tracking
    """

    QUALITY_THRESHOLD = 8.0  # Minimum score to pass

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize analysis engine.

        Args:
            api_key: Anthropic API key
        """
        self.client = ClaudeClient(api_key=api_key)
        self.loop1 = DataInterpreter(self.client)
        self.loop2 = StrategicSynthesizer(self.client)
        self.loop3 = SERPEnricher(self.client)
        self.loop4 = QualityReviewer(self.client)

    async def analyze(
        self,
        analysis_data: Dict[str, Any],
        skip_enrichment: bool = False,
    ) -> AnalysisResult:
        """
        Run complete 4-loop analysis.

        Args:
            analysis_data: Compiled data from collector
            skip_enrichment: Skip Loop 3 (web research) for faster analysis

        Returns:
            AnalysisResult with all loop outputs
        """
        start_time = datetime.utcnow()
        domain = analysis_data.get("metadata", {}).get("domain", "unknown")

        logger.info(f"Starting analysis for {domain}")

        # Classify domain for adaptive analysis
        classification = DomainClassification.from_data(analysis_data)
        logger.info(
            f"Domain classification: {classification.size_tier}, "
            f"{classification.industry}, {classification.competitive_intensity}"
        )

        # ================================================================
        # LOOP 1: Data Interpretation
        # ================================================================
        logger.info("Loop 1: Data Interpretation...")
        loop1_output = await self.loop1.interpret(analysis_data, classification)
        logger.info(f"Loop 1 complete: {len(loop1_output)} chars")

        # ================================================================
        # LOOP 2: Strategic Synthesis
        # ================================================================
        logger.info("Loop 2: Strategic Synthesis...")
        loop2_output = await self.loop2.synthesize(
            loop1_output, analysis_data, classification
        )
        logger.info(f"Loop 2 complete: {len(loop2_output)} chars")

        # ================================================================
        # LOOP 3: SERP & Competitor Enrichment (Optional)
        # ================================================================
        if skip_enrichment:
            logger.info("Loop 3: Skipped (enrichment disabled)")
            loop3_output = "Enrichment skipped."
        else:
            logger.info("Loop 3: SERP & Competitor Enrichment...")
            loop3_output = await self.loop3.enrich(loop2_output, analysis_data)
            logger.info(f"Loop 3 complete: {len(loop3_output)} chars")

        # ================================================================
        # LOOP 4: Quality Review & Executive Summary
        # ================================================================
        logger.info("Loop 4: Quality Review & Executive Summary...")
        loop4_result = await self.loop4.review(
            loop1_output, loop2_output, loop3_output, analysis_data
        )

        # Extract quality metrics
        quality_score = loop4_result.get("quality_score", 0.0)
        quality_checks = loop4_result.get("quality_checks", {})
        executive_summary = loop4_result.get("executive_summary", "")
        review_output = loop4_result.get("review", "")

        passed_gate = quality_score >= self.QUALITY_THRESHOLD
        logger.info(f"Loop 4 complete: quality={quality_score}/10, passed={passed_gate}")

        # Calculate duration and costs
        duration = (datetime.utcnow() - start_time).total_seconds()
        usage = self.client.get_usage_summary()

        logger.info(
            f"Analysis complete in {duration:.1f}s, "
            f"tokens={usage['total_tokens']}, cost=${usage['estimated_cost']:.2f}"
        )

        return AnalysisResult(
            domain=domain,
            timestamp=start_time,
            duration_seconds=duration,
            loop1_findings=loop1_output,
            loop2_strategy=loop2_output,
            loop3_enrichment=loop3_output,
            loop4_review=review_output,
            executive_summary=executive_summary,
            quality_score=quality_score,
            quality_checks=quality_checks,
            passed_quality_gate=passed_gate,
            total_tokens=usage["total_tokens"],
            total_cost=usage["estimated_cost"],
            raw_analysis={
                "loop1": loop1_output,
                "loop2": loop2_output,
                "loop3": loop3_output,
                "loop4": loop4_result,
                "classification": {
                    "size_tier": classification.size_tier,
                    "industry": classification.industry,
                    "competitive_intensity": classification.competitive_intensity,
                    "technical_maturity": classification.technical_maturity,
                },
            },
        )

    async def reanalyze_section(
        self,
        section: str,
        feedback: str,
        previous_output: str,
        analysis_data: Dict[str, Any],
    ) -> str:
        """
        Re-run a specific section with feedback.

        Used when quality gate fails to regenerate specific sections.

        Args:
            section: Which section to regenerate ("loop1", "loop2", etc.)
            feedback: Specific feedback on what to improve
            previous_output: Previous output to improve upon
            analysis_data: Original analysis data

        Returns:
            Regenerated section output
        """
        classification = DomainClassification.from_data(analysis_data)

        if section == "loop1":
            return await self.loop1.regenerate(
                previous_output, feedback, analysis_data, classification
            )
        elif section == "loop2":
            return await self.loop2.regenerate(
                previous_output, feedback, analysis_data, classification
            )
        elif section == "loop3":
            return await self.loop3.regenerate(
                previous_output, feedback, analysis_data
            )
        else:
            raise ValueError(f"Unknown section: {section}")

"""
Quality Gates Implementation

Defines and enforces quality thresholds for analysis pipeline.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Quality gate status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class QualityResult:
    """Result of a quality gate check."""
    gate_name: str
    status: GateStatus
    score: Optional[float] = None
    threshold: Optional[float] = None
    message: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "gate_name": self.gate_name,
            "status": self.status.value,
            "score": self.score,
            "threshold": self.threshold,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class QualityGate:
    """Definition of a quality gate."""
    name: str
    description: str
    threshold: float
    weight: float = 1.0  # Weight in composite score
    required: bool = True  # If True, failure blocks pipeline
    check_fn: Optional[Callable] = None  # Custom check function

    def check(self, data: Dict, context: Optional[Dict] = None) -> QualityResult:
        """
        Run the quality gate check.

        Args:
            data: Data to validate
            context: Additional context

        Returns:
            QualityResult with pass/fail status
        """
        if self.check_fn:
            try:
                score, message, details = self.check_fn(data, context or {})

                status = GateStatus.PASSED if score >= self.threshold else GateStatus.FAILED
                if not self.required and status == GateStatus.FAILED:
                    status = GateStatus.WARNING

                return QualityResult(
                    gate_name=self.name,
                    status=status,
                    score=score,
                    threshold=self.threshold,
                    message=message,
                    details=details
                )
            except Exception as e:
                logger.error(f"Gate {self.name} check failed: {e}")
                return QualityResult(
                    gate_name=self.name,
                    status=GateStatus.FAILED,
                    message=f"Check error: {str(e)}"
                )

        return QualityResult(
            gate_name=self.name,
            status=GateStatus.SKIPPED,
            message="No check function defined"
        )


class QualityEnforcer:
    """
    Enforces quality gates throughout the analysis pipeline.

    Specification requirements:
    - Quality score >= 8/10 required for analysis to pass
    - Multiple gates for different aspects
    - Weighted composite scoring
    """

    # Minimum quality score to pass (from specification)
    MINIMUM_QUALITY_SCORE = 8.0

    def __init__(self):
        """Initialize with default quality gates."""
        self.gates: Dict[str, QualityGate] = {}
        self._register_default_gates()
        self._results: List[QualityResult] = []

    def _register_default_gates(self):
        """Register default quality gates per specification."""

        # Gate 1: Data Completeness
        self.register_gate(QualityGate(
            name="data_completeness",
            description="Checks that all required data phases completed successfully",
            threshold=0.8,  # 80% of expected data points
            weight=1.5,
            required=True,
            check_fn=self._check_data_completeness
        ))

        # Gate 2: Evidence Quality
        self.register_gate(QualityGate(
            name="evidence_quality",
            description="Validates that findings are backed by data evidence",
            threshold=0.7,  # 70% of findings have evidence
            weight=1.5,
            required=True,
            check_fn=self._check_evidence_quality
        ))

        # Gate 3: Actionability
        self.register_gate(QualityGate(
            name="actionability",
            description="Ensures recommendations are specific and actionable",
            threshold=0.8,
            weight=1.2,
            required=True,
            check_fn=self._check_actionability
        ))

        # Gate 4: Business Relevance
        self.register_gate(QualityGate(
            name="business_relevance",
            description="Checks alignment with business context and goals",
            threshold=0.7,
            weight=1.0,
            required=False,
            check_fn=self._check_business_relevance
        ))

        # Gate 5: Prioritization
        self.register_gate(QualityGate(
            name="prioritization",
            description="Validates priority scoring and clear hierarchy",
            threshold=0.8,
            weight=1.0,
            required=True,
            check_fn=self._check_prioritization
        ))

        # Gate 6: Internal Consistency
        self.register_gate(QualityGate(
            name="internal_consistency",
            description="Ensures findings don't contradict each other",
            threshold=0.9,
            weight=1.3,
            required=True,
            check_fn=self._check_internal_consistency
        ))

        # Gate 7: AI Visibility Coverage
        self.register_gate(QualityGate(
            name="ai_visibility_coverage",
            description="Checks AI/LLM visibility analysis completeness",
            threshold=0.6,
            weight=0.8,
            required=False,
            check_fn=self._check_ai_visibility
        ))

        # Gate 8: Technical Depth
        self.register_gate(QualityGate(
            name="technical_depth",
            description="Validates technical analysis thoroughness",
            threshold=0.7,
            weight=1.0,
            required=False,
            check_fn=self._check_technical_depth
        ))

    def register_gate(self, gate: QualityGate):
        """Register a quality gate."""
        self.gates[gate.name] = gate
        logger.debug(f"Registered quality gate: {gate.name}")

    def run_gate(self, gate_name: str, data: Dict, context: Optional[Dict] = None) -> QualityResult:
        """Run a specific quality gate."""
        if gate_name not in self.gates:
            return QualityResult(
                gate_name=gate_name,
                status=GateStatus.SKIPPED,
                message=f"Gate '{gate_name}' not found"
            )

        gate = self.gates[gate_name]
        result = gate.check(data, context)
        self._results.append(result)

        log_fn = logger.info if result.status == GateStatus.PASSED else logger.warning
        log_fn(f"Gate {gate_name}: {result.status.value} (score: {result.score})")

        return result

    def run_all_gates(self, data: Dict, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run all quality gates and return composite result.

        Args:
            data: Analysis data to validate
            context: Additional context (domain info, etc.)

        Returns:
            Dict with overall status, score, and individual results
        """
        self._results = []
        results = []
        weighted_sum = 0
        total_weight = 0
        required_failed = []

        for gate_name, gate in self.gates.items():
            result = self.run_gate(gate_name, data, context)
            results.append(result)

            if result.score is not None:
                weighted_sum += result.score * gate.weight
                total_weight += gate.weight

            if gate.required and result.status == GateStatus.FAILED:
                required_failed.append(gate_name)

        # Calculate composite score (0-10 scale)
        composite_score = (weighted_sum / total_weight * 10) if total_weight > 0 else 0

        # Determine overall status
        overall_passed = (
            composite_score >= self.MINIMUM_QUALITY_SCORE and
            len(required_failed) == 0
        )

        return {
            "passed": overall_passed,
            "composite_score": round(composite_score, 2),
            "minimum_required": self.MINIMUM_QUALITY_SCORE,
            "required_gates_failed": required_failed,
            "gate_results": [r.to_dict() for r in results],
            "summary": {
                "total_gates": len(self.gates),
                "passed": sum(1 for r in results if r.status == GateStatus.PASSED),
                "failed": sum(1 for r in results if r.status == GateStatus.FAILED),
                "warnings": sum(1 for r in results if r.status == GateStatus.WARNING),
                "skipped": sum(1 for r in results if r.status == GateStatus.SKIPPED),
            }
        }

    def get_results(self) -> List[QualityResult]:
        """Get all results from last run."""
        return self._results

    # =========================================================================
    # Gate Check Functions
    # =========================================================================

    @staticmethod
    def _check_data_completeness(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check data completeness across all phases."""
        required_fields = [
            # Phase 1
            "domain_overview", "backlink_summary", "competitors", "technologies",
            # Phase 2
            "ranked_keywords", "keyword_gaps", "intent_classification",
            # Phase 3
            "competitor_metrics", "anchor_distribution", "link_velocity",
            # Phase 4
            "ai_keyword_data", "technical_audits", "trend_data"
        ]

        present = 0
        missing = []

        for field in required_fields:
            if field in data and data[field]:
                present += 1
            else:
                missing.append(field)

        score = present / len(required_fields)
        message = f"{present}/{len(required_fields)} required data fields present"

        return score, message, {"missing_fields": missing}

    @staticmethod
    def _check_evidence_quality(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check that findings have supporting evidence."""
        findings = data.get("findings", [])
        if not findings:
            # Check in analysis_result
            analysis = data.get("analysis_result", {})
            findings = analysis.get("findings", [])

        if not findings:
            return 0.5, "No findings to validate", {}

        with_evidence = sum(1 for f in findings if f.get("evidence") or f.get("data_sources"))
        score = with_evidence / len(findings) if findings else 0

        return score, f"{with_evidence}/{len(findings)} findings have evidence", {}

    @staticmethod
    def _check_actionability(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check that recommendations are actionable."""
        recommendations = data.get("recommendations", [])
        if not recommendations:
            analysis = data.get("analysis_result", {})
            recommendations = analysis.get("recommendations", [])

        if not recommendations:
            return 0.5, "No recommendations to validate", {}

        actionable_keywords = ["implement", "create", "add", "remove", "update", "optimize", "fix", "build"]
        actionable = 0

        for rec in recommendations:
            rec_text = str(rec).lower()
            if any(kw in rec_text for kw in actionable_keywords):
                actionable += 1

        score = actionable / len(recommendations) if recommendations else 0

        return score, f"{actionable}/{len(recommendations)} recommendations are actionable", {}

    @staticmethod
    def _check_business_relevance(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check business context alignment."""
        # Check if domain classification exists
        domain_class = data.get("domain_classification", {})
        if not domain_class:
            analysis = data.get("analysis_result", {})
            domain_class = analysis.get("domain_classification", {})

        has_industry = bool(domain_class.get("industry"))
        has_size = bool(domain_class.get("size_tier"))
        has_competitive_context = bool(data.get("competitor_metrics") or data.get("competitors"))

        checks = [has_industry, has_size, has_competitive_context]
        score = sum(checks) / len(checks)

        return score, f"{sum(checks)}/{len(checks)} business context elements present", {
            "has_industry": has_industry,
            "has_size": has_size,
            "has_competitive_context": has_competitive_context
        }

    @staticmethod
    def _check_prioritization(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check that recommendations are properly prioritized."""
        recommendations = data.get("recommendations", [])
        if not recommendations:
            analysis = data.get("analysis_result", {})
            recommendations = analysis.get("recommendations", [])

        if not recommendations:
            return 0.5, "No recommendations to validate", {}

        # Check for priority indicators
        with_priority = sum(
            1 for r in recommendations
            if isinstance(r, dict) and (
                r.get("priority") or
                r.get("impact") or
                r.get("effort") or
                r.get("score")
            )
        )

        score = with_priority / len(recommendations) if recommendations else 0

        return score, f"{with_priority}/{len(recommendations)} recommendations have priority scoring", {}

    @staticmethod
    def _check_internal_consistency(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check for internal contradictions."""
        # This is a simplified check - in production, would use NLP
        issues = []

        # Check keyword count consistency
        ranked_kw_count = len(data.get("ranked_keywords", []))
        reported_count = data.get("total_ranking_keywords", 0)

        if ranked_kw_count > 0 and reported_count > 0:
            if abs(ranked_kw_count - reported_count) / max(ranked_kw_count, reported_count) > 0.5:
                issues.append("Keyword count mismatch")

        # Check traffic consistency
        domain_traffic = data.get("domain_overview", {}).get("organic_traffic", 0)
        sum_traffic = sum(
            kw.get("traffic", 0)
            for kw in data.get("ranked_keywords", [])[:100]
        )

        if domain_traffic > 0 and sum_traffic > domain_traffic * 2:
            issues.append("Traffic sum exceeds total")

        score = 1.0 - (len(issues) * 0.2)  # Deduct 20% per issue
        score = max(0, score)

        return score, f"{len(issues)} consistency issues found", {"issues": issues}

    @staticmethod
    def _check_ai_visibility(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check AI visibility analysis completeness."""
        ai_data = data.get("ai_keyword_data", [])
        llm_mentions = data.get("llm_mentions", {})
        live_serp = data.get("live_serp_data", [])

        checks = [
            len(ai_data) > 0,
            bool(llm_mentions.get("chatgpt") or llm_mentions.get("google_ai")),
            len(live_serp) > 0,
        ]

        score = sum(checks) / len(checks)

        return score, f"{sum(checks)}/{len(checks)} AI visibility components present", {
            "has_ai_keywords": checks[0],
            "has_llm_mentions": checks[1],
            "has_live_serp": checks[2]
        }

    @staticmethod
    def _check_technical_depth(data: Dict, context: Dict) -> tuple[float, str, Dict]:
        """Check technical analysis thoroughness."""
        technical_audits = data.get("technical_audits", [])
        if isinstance(technical_audits, dict):
            technical_audits = [technical_audits]

        lighthouse = data.get("technical_baseline", {})
        schema_data = data.get("schema_data", [])

        checks = [
            len(technical_audits) > 0,
            bool(lighthouse),
            len(schema_data) > 0,
        ]

        score = sum(checks) / len(checks)

        return score, f"{sum(checks)}/{len(checks)} technical analysis components present", {
            "has_page_audits": checks[0],
            "has_lighthouse": checks[1],
            "has_schema": checks[2]
        }

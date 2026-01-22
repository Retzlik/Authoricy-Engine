"""
Quality Checks for Agent Output Validation (v5 Specification)

Implements 25 quality checks in 4 categories:
- Specificity (7 checks)
- Actionability (6 checks)
- Data-Grounding (6 checks)
- Non-Generic (6 checks)

Pass threshold: 23/25 (92%)
"""

import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class CheckCategory(Enum):
    """Quality check categories."""
    SPECIFICITY = "specificity"
    ACTIONABILITY = "actionability"
    DATA_GROUNDING = "data_grounding"
    NON_GENERIC = "non_generic"


@dataclass
class QualityCheck:
    """Definition of a single quality check."""
    name: str
    category: CheckCategory
    description: str
    check_fn: Callable[[str, Dict[str, Any]], bool]
    weight: float = 1.0
    required: bool = True


@dataclass
class CheckResult:
    """Result of running a quality check."""
    name: str
    category: CheckCategory
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class AgentQualityChecker:
    """
    Runs 25 quality checks on agent output.

    Usage:
        checker = AgentQualityChecker()
        results = checker.run_all_checks(raw_output, parsed_data)
        score = checker.calculate_score(results)
        passed = checker.passes_gate(results)  # >= 23/25
    """

    PASS_THRESHOLD = 23  # Out of 25

    def __init__(self):
        """Initialize with all 25 checks."""
        self.checks: List[QualityCheck] = []
        self._register_all_checks()

    def _register_all_checks(self):
        """Register all 25 quality checks."""

        # ===== SPECIFICITY CHECKS (7) =====

        self.checks.append(QualityCheck(
            name="has_specific_numbers",
            category=CheckCategory.SPECIFICITY,
            description="Contains specific numbers, not vague qualifiers",
            check_fn=self._check_specific_numbers,
        ))

        self.checks.append(QualityCheck(
            name="has_specific_urls",
            category=CheckCategory.SPECIFICITY,
            description="References actual pages/URLs from the domain",
            check_fn=self._check_specific_urls,
        ))

        self.checks.append(QualityCheck(
            name="has_competitor_comparisons",
            category=CheckCategory.SPECIFICITY,
            description="Includes competitor-specific comparisons",
            check_fn=self._check_competitor_comparisons,
        ))

        self.checks.append(QualityCheck(
            name="has_measurable_targets",
            category=CheckCategory.SPECIFICITY,
            description="Provides measurable targets",
            check_fn=self._check_measurable_targets,
        ))

        self.checks.append(QualityCheck(
            name="uses_precise_terminology",
            category=CheckCategory.SPECIFICITY,
            description="Uses precise SEO terminology",
            check_fn=self._check_precise_terminology,
        ))

        self.checks.append(QualityCheck(
            name="avoids_weasel_words",
            category=CheckCategory.SPECIFICITY,
            description="Avoids weasel words (might, could, potentially)",
            check_fn=self._check_avoids_weasel_words,
        ))

        self.checks.append(QualityCheck(
            name="has_timeframes",
            category=CheckCategory.SPECIFICITY,
            description="Includes timeframes for recommendations",
            check_fn=self._check_has_timeframes,
        ))

        # ===== ACTIONABILITY CHECKS (6) =====

        self.checks.append(QualityCheck(
            name="has_clear_actions",
            category=CheckCategory.ACTIONABILITY,
            description="Each finding has clear next step",
            check_fn=self._check_clear_actions,
        ))

        self.checks.append(QualityCheck(
            name="has_priorities",
            category=CheckCategory.ACTIONABILITY,
            description="Actions are prioritized (P1/P2/P3)",
            check_fn=self._check_has_priorities,
        ))

        self.checks.append(QualityCheck(
            name="has_effort_estimates",
            category=CheckCategory.ACTIONABILITY,
            description="Effort estimates included",
            check_fn=self._check_effort_estimates,
        ))

        self.checks.append(QualityCheck(
            name="has_dependencies",
            category=CheckCategory.ACTIONABILITY,
            description="Dependencies identified",
            check_fn=self._check_dependencies,
        ))

        self.checks.append(QualityCheck(
            name="has_success_metrics",
            category=CheckCategory.ACTIONABILITY,
            description="Success metrics defined",
            check_fn=self._check_success_metrics,
        ))

        self.checks.append(QualityCheck(
            name="has_owners",
            category=CheckCategory.ACTIONABILITY,
            description="Owner/role suggested",
            check_fn=self._check_has_owners,
        ))

        # ===== DATA-GROUNDING CHECKS (6) =====

        self.checks.append(QualityCheck(
            name="cites_source_data",
            category=CheckCategory.DATA_GROUNDING,
            description="Every claim cites source data",
            check_fn=self._check_cites_data,
        ))

        self.checks.append(QualityCheck(
            name="has_benchmarks",
            category=CheckCategory.DATA_GROUNDING,
            description="Metrics include context (benchmark, trend)",
            check_fn=self._check_has_benchmarks,
        ))

        self.checks.append(QualityCheck(
            name="consistent_time_periods",
            category=CheckCategory.DATA_GROUNDING,
            description="Comparisons use same time periods",
            check_fn=self._check_time_consistency,
        ))

        self.checks.append(QualityCheck(
            name="notes_significance",
            category=CheckCategory.DATA_GROUNDING,
            description="Statistical significance noted where relevant",
            check_fn=self._check_notes_significance,
        ))

        self.checks.append(QualityCheck(
            name="acknowledges_limitations",
            category=CheckCategory.DATA_GROUNDING,
            description="Data limitations acknowledged",
            check_fn=self._check_acknowledges_limitations,
        ))

        self.checks.append(QualityCheck(
            name="has_confidence_levels",
            category=CheckCategory.DATA_GROUNDING,
            description="Confidence levels assigned",
            check_fn=self._check_confidence_levels,
        ))

        # ===== NON-GENERIC CHECKS (6) =====

        self.checks.append(QualityCheck(
            name="no_placeholder_text",
            category=CheckCategory.NON_GENERIC,
            description="No placeholder or template text",
            check_fn=self._check_no_placeholders,
        ))

        self.checks.append(QualityCheck(
            name="customized_advice",
            category=CheckCategory.NON_GENERIC,
            description="No 'best practice' without customization",
            check_fn=self._check_customized_advice,
        ))

        self.checks.append(QualityCheck(
            name="industry_specific",
            category=CheckCategory.NON_GENERIC,
            description="Industry-specific context applied",
            check_fn=self._check_industry_specific,
        ))

        self.checks.append(QualityCheck(
            name="considers_history",
            category=CheckCategory.NON_GENERIC,
            description="Domain history considered",
            check_fn=self._check_considers_history,
        ))

        self.checks.append(QualityCheck(
            name="reflects_competition",
            category=CheckCategory.NON_GENERIC,
            description="Competitive landscape reflected",
            check_fn=self._check_reflects_competition,
        ))

        self.checks.append(QualityCheck(
            name="unique_opportunities",
            category=CheckCategory.NON_GENERIC,
            description="Unique opportunities identified",
            check_fn=self._check_unique_opportunities,
        ))

    def run_all_checks(
        self,
        raw_output: str,
        parsed_data: Dict[str, Any]
    ) -> List[CheckResult]:
        """
        Run all 25 quality checks.

        Args:
            raw_output: Raw text output from Claude
            parsed_data: Parsed structured data

        Returns:
            List of 25 CheckResult objects
        """
        results = []

        for check in self.checks:
            try:
                passed = check.check_fn(raw_output, parsed_data)
                results.append(CheckResult(
                    name=check.name,
                    category=check.category,
                    passed=passed,
                    message="Passed" if passed else f"Failed: {check.description}",
                ))
            except Exception as e:
                logger.warning(f"Check {check.name} error: {e}")
                results.append(CheckResult(
                    name=check.name,
                    category=check.category,
                    passed=False,
                    message=f"Error: {str(e)}",
                ))

        return results

    def calculate_score(self, results: List[CheckResult]) -> float:
        """
        Calculate quality score (0-10 scale).

        Args:
            results: List of check results

        Returns:
            Score from 0-10
        """
        if not results:
            return 0.0

        passed = sum(1 for r in results if r.passed)
        return round((passed / len(results)) * 10, 2)

    def passes_gate(self, results: List[CheckResult]) -> bool:
        """
        Check if output passes quality gate (23/25).

        Args:
            results: List of check results

        Returns:
            True if >= 23 checks passed
        """
        passed = sum(1 for r in results if r.passed)
        return passed >= self.PASS_THRESHOLD

    def get_failed_checks(self, results: List[CheckResult]) -> List[CheckResult]:
        """Get list of failed checks."""
        return [r for r in results if not r.passed]

    def get_summary(self, results: List[CheckResult]) -> Dict[str, Any]:
        """
        Get summary of check results.

        Args:
            results: List of check results

        Returns:
            Summary dict with counts by category
        """
        by_category = {cat.value: {"passed": 0, "failed": 0} for cat in CheckCategory}

        for result in results:
            key = "passed" if result.passed else "failed"
            by_category[result.category.value][key] += 1

        total_passed = sum(1 for r in results if r.passed)
        total_failed = len(results) - total_passed

        return {
            "total_checks": len(results),
            "passed": total_passed,
            "failed": total_failed,
            "score": self.calculate_score(results),
            "passes_gate": self.passes_gate(results),
            "by_category": by_category,
            "failed_checks": [r.name for r in results if not r.passed],
        }

    # =========================================================================
    # SPECIFICITY CHECK IMPLEMENTATIONS
    # =========================================================================

    def _check_specific_numbers(self, output: str, data: Dict) -> bool:
        """Check for specific numbers (not vague qualifiers)."""
        number_patterns = [
            r'\d+(?:,\d{3})*(?:\.\d+)?%',  # Percentages
            r'\d+(?:,\d{3})+',  # Large numbers
            r'(?:position|rank|#)\s*\d+',  # Rankings
            r'\$[\d,]+(?:\.\d{2})?',  # Money
            r'\d+\s*(?:keywords?|pages?|links?|backlinks?|visits?|sessions?)',
        ]
        matches = sum(len(re.findall(p, output, re.I)) for p in number_patterns)
        return matches >= 10  # Should have many specific numbers

    def _check_specific_urls(self, output: str, data: Dict) -> bool:
        """Check for specific URLs mentioned."""
        url_patterns = [
            r'https?://[^\s<>"\']+',  # Full URLs
            r'/[a-z0-9][a-z0-9\-_/]*(?:\.[a-z]+)?',  # Paths
        ]
        matches = sum(len(re.findall(p, output, re.I)) for p in url_patterns)
        return matches >= 5

    def _check_competitor_comparisons(self, output: str, data: Dict) -> bool:
        """Check for competitor comparisons."""
        patterns = [
            r'compared to\s+\w+',
            r'versus\s+\w+',
            r'competitor[s]?.*(?:has|have|ranks?|outranks?)',
            r'(?:ahead of|behind)\s+\w+',
            r'\w+\s+(?:outperforms?|underperforms?)',
        ]
        matches = sum(1 for p in patterns if re.search(p, output, re.I))
        return matches >= 2

    def _check_measurable_targets(self, output: str, data: Dict) -> bool:
        """Check for measurable targets."""
        patterns = [
            r'target(?:ing)?\s*[:\-]?\s*(?:position\s*)?\d+',
            r'goal\s*[:\-]?\s*\d+',
            r'aim(?:ing)?\s+(?:for|to)\s+\d+',
            r'increase\s+(?:by|to)\s+\d+',
            r'improve\s+(?:by|to)\s+\d+',
            r'reach\s+\d+',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    def _check_precise_terminology(self, output: str, data: Dict) -> bool:
        """Check for precise SEO terminology."""
        terms = [
            r'\bDR\b', r'\bDA\b', r'\bKD\b',
            r'keyword difficulty', r'search volume',
            r'CTR', r'click.through.rate',
            r'SERP', r'organic traffic',
            r'backlink', r'referring domain',
            r'anchor text', r'domain (?:rating|authority)',
            r'impressions', r'rankings?',
        ]
        matches = sum(1 for t in terms if re.search(t, output, re.I))
        return matches >= 8

    def _check_avoids_weasel_words(self, output: str, data: Dict) -> bool:
        """Check that weasel words are minimized."""
        weasel_patterns = [
            r'\b(?:might|may|could)\s+(?:want to|need to|consider|help)\b',
            r'\bpotentially\b',
            r'\bpossibly\b',
            r'\bperhaps\b',
            r'\bsomewhat\b',
            r'\bfairly\b',
            r'\bquite\b',
            r'\brather\b',
        ]
        weasel_count = sum(len(re.findall(p, output, re.I)) for p in weasel_patterns)
        word_count = len(output.split())
        # Allow max 0.5% weasel words
        return weasel_count < (word_count * 0.005) or weasel_count < 5

    def _check_has_timeframes(self, output: str, data: Dict) -> bool:
        """Check for timeframes in recommendations."""
        patterns = [
            r'\d+\s*(?:day|week|month|year)s?',
            r'Q[1-4]\s*\d{4}',
            r'(?:by|within|in)\s+(?:the\s+)?(?:next\s+)?\d+',
            r'short.term|medium.term|long.term',
            r'immediate(?:ly)?',
            r'(?:first|second|third)\s+(?:phase|quarter|month)',
        ]
        matches = sum(1 for p in patterns if re.search(p, output, re.I))
        return matches >= 3

    # =========================================================================
    # ACTIONABILITY CHECK IMPLEMENTATIONS
    # =========================================================================

    def _check_clear_actions(self, output: str, data: Dict) -> bool:
        """Check for clear action verbs."""
        action_verbs = [
            r'\b(?:create|implement|add|remove|update|optimize|fix|build|develop)\b',
            r'\b(?:write|publish|launch|deploy|migrate|consolidate)\b',
            r'\b(?:audit|review|analyze|monitor|track)\b',
        ]
        matches = sum(len(re.findall(p, output, re.I)) for p in action_verbs)
        return matches >= 10

    def _check_has_priorities(self, output: str, data: Dict) -> bool:
        """Check for priority assignments."""
        patterns = [
            r'P[1-3]',
            r'priority\s*[:\-]?\s*(?:1|2|3|high|medium|low|critical)',
            r'(?:high|medium|low)\s+priority',
            r'critical|important|urgent',
            r'(?:first|second|third)\s+priority',
        ]
        matches = sum(1 for p in patterns if re.search(p, output, re.I))
        return matches >= 3

    def _check_effort_estimates(self, output: str, data: Dict) -> bool:
        """Check for effort estimates."""
        patterns = [
            r'effort\s*[:\-]?\s*(?:low|medium|high)',
            r'(?:low|medium|high)\s+effort',
            r'\d+\s*(?:hour|day|week)s?\s+(?:of\s+)?(?:work|effort)',
            r'quick\s+win',
            r'resource.intensive',
            r'(?:easy|simple|complex|difficult)\s+to\s+implement',
        ]
        matches = sum(1 for p in patterns if re.search(p, output, re.I))
        return matches >= 2

    def _check_dependencies(self, output: str, data: Dict) -> bool:
        """Check for dependency identification."""
        patterns = [
            r'depend(?:s|ent|ing)?\s+on',
            r'require[sd]?\s+(?:first|before)',
            r'after\s+(?:completing|implementing)',
            r'prerequisite',
            r'blocked\s+by',
            r'before\s+(?:you\s+can|we\s+can)',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    def _check_success_metrics(self, output: str, data: Dict) -> bool:
        """Check for success metrics."""
        patterns = [
            r'success\s+(?:metric|criteria|measure)',
            r'KPI',
            r'measure[d]?\s+by',
            r'track(?:ing)?\s+(?:the\s+)?(?:following|these)',
            r'expected\s+(?:outcome|result|impact)',
            r'should\s+(?:see|result\s+in)\s+\d+',
        ]
        matches = sum(1 for p in patterns if re.search(p, output, re.I))
        return matches >= 2

    def _check_has_owners(self, output: str, data: Dict) -> bool:
        """Check for suggested owners/roles."""
        patterns = [
            r'(?:content|SEO|technical|dev|marketing)\s+team',
            r'(?:developer|writer|strategist|manager|analyst)',
            r'assigned?\s+to',
            r'responsible\s+(?:for|party)',
            r'owner',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    # =========================================================================
    # DATA-GROUNDING CHECK IMPLEMENTATIONS
    # =========================================================================

    def _check_cites_data(self, output: str, data: Dict) -> bool:
        """Check for data citations."""
        patterns = [
            r'\[.*?:\s*[\d,]+.*?\]',  # [Metric: Value] format
            r'according to\s+(?:the\s+)?data',
            r'data\s+shows',
            r'based on\s+(?:the\s+)?(?:keyword|traffic|backlink)',
            r'from\s+(?:DataForSEO|our\s+analysis)',
        ]
        matches = sum(1 for p in patterns if re.search(p, output, re.I))
        return matches >= 3

    def _check_has_benchmarks(self, output: str, data: Dict) -> bool:
        """Check for benchmark comparisons."""
        patterns = [
            r'(?:industry|sector)\s+average',
            r'benchmark',
            r'typical(?:ly)?',
            r'median',
            r'compared to\s+(?:average|typical|similar)',
            r'above|below\s+average',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    def _check_time_consistency(self, output: str, data: Dict) -> bool:
        """Check for consistent time period references."""
        patterns = [
            r'(?:past|last|previous)\s+\d+\s+(?:day|week|month|year)s?',
            r'(?:year|month).over.(?:year|month)',
            r'(?:Q[1-4]|H[12])\s*\d{4}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    def _check_notes_significance(self, output: str, data: Dict) -> bool:
        """Check for significance/importance notes."""
        patterns = [
            r'significant(?:ly)?',
            r'notable|notably',
            r'substantial(?:ly)?',
            r'meaningful',
            r'material',
            r'important(?:ly)?',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    def _check_acknowledges_limitations(self, output: str, data: Dict) -> bool:
        """Check for limitation acknowledgments."""
        patterns = [
            r'limitation',
            r'caveat',
            r'note\s+that',
            r'however',
            r'(?:in)?complete\s+data',
            r'(?:in)?sufficient',
            r'(?:un)?available',
            r'missing',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    def _check_confidence_levels(self, output: str, data: Dict) -> bool:
        """Check for confidence levels."""
        patterns = [
            r'confidence\s*[:\-]?\s*(?:high|medium|low|\d+)',
            r'(?:high|medium|low)\s+confidence',
            r'\d+(?:\.\d+)?%?\s+confiden(?:ce|t)',
            r'(?:likely|unlikely)',
            r'certainty',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    # =========================================================================
    # NON-GENERIC CHECK IMPLEMENTATIONS
    # =========================================================================

    def _check_no_placeholders(self, output: str, data: Dict) -> bool:
        """Check for absence of placeholder text."""
        placeholder_patterns = [
            r'based on (?:comprehensive|thorough|detailed) analysis',
            r'according to (?:our|the) (?:comprehensive|detailed) (?:analysis|review)',
            r'\[.*?placeholder.*?\]',
            r'lorem ipsum',
            r'\bTBD\b|\bTODO\b|\bFIXME\b',
            r'insert\s+(?:here|data|content)',
            r'\[your\s+\w+\s+here\]',
        ]
        return not any(re.search(p, output, re.I) for p in placeholder_patterns)

    def _check_customized_advice(self, output: str, data: Dict) -> bool:
        """Check for customized (not generic) advice."""
        generic_patterns = [
            r'follow\s+(?:SEO\s+)?best\s+practices',
            r'implement\s+industry\s+standards',
            r'optimize\s+your\s+(?:website|content|pages)',
            r'improve\s+your\s+(?:SEO|rankings)',
            r'create\s+quality\s+content',
            r'build\s+(?:quality\s+)?backlinks',
        ]
        generic_count = sum(len(re.findall(p, output, re.I)) for p in generic_patterns)
        return generic_count < 5

    def _check_industry_specific(self, output: str, data: Dict) -> bool:
        """Check for industry-specific context."""
        patterns = [
            r'(?:in|for)\s+(?:this|the|your)\s+(?:industry|sector|vertical|market|niche)',
            r'(?:B2B|B2C|SaaS|e-?commerce|retail|finance|healthcare)',
            r'(?:your|this)\s+(?:type of|kind of)\s+(?:business|company|site)',
            r'competitors\s+in\s+(?:this|your)\s+space',
        ]
        return any(re.search(p, output, re.I) for p in patterns)

    def _check_considers_history(self, output: str, data: Dict) -> bool:
        """Check for historical context."""
        patterns = [
            r'historically',
            r'over\s+(?:the\s+past|time)',
            r'trend(?:ing|s)?',
            r'previously',
            r'(?:growth|decline)\s+(?:of|in|over)',
            r'(?:has|have)\s+(?:been|shown)',
        ]
        matches = sum(1 for p in patterns if re.search(p, output, re.I))
        return matches >= 2

    def _check_reflects_competition(self, output: str, data: Dict) -> bool:
        """Check that competitive landscape is reflected."""
        patterns = [
            r'competitor',
            r'competitive',
            r'market\s+share',
            r'(?:out)?rank(?:s|ing|ed)?',
            r'competing',
            r'versus',
            r'(?:ahead|behind)\s+of',
        ]
        matches = sum(len(re.findall(p, output, re.I)) for p in patterns)
        return matches >= 5

    def _check_unique_opportunities(self, output: str, data: Dict) -> bool:
        """Check for unique/specific opportunities."""
        # Should identify specific keywords, pages, or actions
        specific_patterns = [
            r'(?:target|focus on)\s+"[^"]+"|\'[^\']+\'',  # Quoted keywords
            r'/[a-z0-9\-_/]+',  # URL paths
            r'(?:keyword|page|url)\s*[:\-]\s*\S+',  # Specific items
        ]
        matches = sum(len(re.findall(p, output, re.I)) for p in specific_patterns)
        return matches >= 5

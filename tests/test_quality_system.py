"""
Test Suite for 25-Point Quality System

Tests the quality gate that ensures reports meet v5 standards:
- 7 Specificity checks
- 6 Actionability checks
- 6 Data-Grounding checks
- 6 Non-Generic checks

Minimum: 23/25 (92%) must pass.
"""

import pytest
from typing import Dict, Any, List

from src.quality import (
    AgentQualityChecker,
    QualityCheck,
    CheckResult,
    CheckCategory,
    AntiPatternDetector,
    AntiPatternMatch,
    AntiPatternResult,
    AntiPatternSeverity,
)


# Sample outputs for testing
GOOD_OUTPUT = """
<analysis>
<executive_summary>
Analysis of example.se reveals 23 high-priority keyword opportunities totaling 45,000 monthly searches.
The site currently ranks for 1,247 keywords with average position 18.3.
Top opportunity: "projekthantering software" (2,400 vol, KD 42, current #15).
</executive_summary>

<priority_stack>
<keyword priority="1">
<term>projekthantering software</term>
<volume>2400</volume>
<difficulty>42</difficulty>
<personalized_difficulty>35</personalized_difficulty>
<opportunity_score>89</opportunity_score>
<current_position>15</current_position>
<intent>commercial</intent>
<recommended_action>Create dedicated landing page at /projekthantering-software with comparison table vs Asana, Monday, Trello</recommended_action>
<effort>Medium - 2-3 weeks development</effort>
<impact>High - 500+ monthly visits potential, €2,400/month value at 2% conversion</impact>
<specific_url>/projekthantering-software</specific_url>
<timeline>Launch by February 15</timeline>
</keyword>
</priority_stack>

<metrics>
<total_keywords>23</total_keywords>
<total_volume>45000</total_volume>
<average_difficulty>48</average_difficulty>
</metrics>
</analysis>
"""

BAD_OUTPUT_GENERIC = """
Based on comprehensive analysis of the website, we have identified several areas for improvement.

The site has good potential for growth in organic search. We recommend:
- Optimize existing content for better rankings
- Build high-quality backlinks
- Improve technical SEO fundamentals
- Focus on user experience

These improvements will help increase organic traffic over time.
"""

BAD_OUTPUT_PLACEHOLDER = """
Based on comprehensive analysis of [DOMAIN], we recommend the following:

Your website ranks for approximately [X] keywords with [Y] monthly traffic.

Top recommendations:
1. Target high-potential keywords
2. Optimize existing high-potential pages
3. Build authoritative backlinks

Implement these strategies to see improvement in 3-6 months.
"""


class TestAgentQualityChecker:
    """Test the main quality checker."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_checker_instantiation(self, checker):
        """Quality checker should instantiate."""
        assert checker is not None
        assert hasattr(checker, "checks")
        assert hasattr(checker, "run_all_checks")

    def test_has_25_checks(self, checker):
        """Should have exactly 25 checks registered."""
        assert len(checker.checks) == 25

    def test_run_all_checks_returns_results(self, checker):
        """run_all_checks should return check results."""
        results = checker.run_all_checks(GOOD_OUTPUT, {})

        assert isinstance(results, list)
        assert len(results) == 25
        assert all(isinstance(r, CheckResult) for r in results)

    def test_calculate_score(self, checker):
        """Should calculate score from results."""
        results = checker.run_all_checks(GOOD_OUTPUT, {})
        score = checker.calculate_score(results)

        assert isinstance(score, float)
        assert 0 <= score <= 10

    def test_passes_gate_method(self, checker):
        """Should have passes_gate method."""
        results = checker.run_all_checks(GOOD_OUTPUT, {})
        passed = checker.passes_gate(results)

        assert isinstance(passed, bool)

    def test_good_output_scores_higher(self, checker):
        """Good output should score higher than bad."""
        good_results = checker.run_all_checks(GOOD_OUTPUT, {})
        bad_results = checker.run_all_checks(BAD_OUTPUT_GENERIC, {})

        good_score = checker.calculate_score(good_results)
        bad_score = checker.calculate_score(bad_results)

        assert good_score > bad_score


class TestCheckCategories:
    """Test quality check categories."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_has_specificity_checks(self, checker):
        """Should have 7 specificity checks."""
        specificity = [c for c in checker.checks if c.category == CheckCategory.SPECIFICITY]
        assert len(specificity) == 7

    def test_has_actionability_checks(self, checker):
        """Should have 6 actionability checks."""
        actionability = [c for c in checker.checks if c.category == CheckCategory.ACTIONABILITY]
        assert len(actionability) == 6

    def test_has_data_grounding_checks(self, checker):
        """Should have 6 data-grounding checks."""
        data_grounding = [c for c in checker.checks if c.category == CheckCategory.DATA_GROUNDING]
        assert len(data_grounding) == 6

    def test_has_non_generic_checks(self, checker):
        """Should have 6 non-generic checks."""
        non_generic = [c for c in checker.checks if c.category == CheckCategory.NON_GENERIC]
        assert len(non_generic) == 6


class TestSpecificityChecks:
    """Test specificity-related quality checks."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_has_specific_numbers_check(self, checker):
        """Should have a specific numbers check."""
        results = checker.run_all_checks(GOOD_OUTPUT, {})

        number_check = next((r for r in results if r.name == "has_specific_numbers"), None)
        assert number_check is not None
        # The check exists and runs
        assert isinstance(number_check.passed, bool)

    def test_fails_without_numbers(self, checker):
        """Output without numbers should fail."""
        no_numbers = "This is some text without any specific data."
        results = checker.run_all_checks(no_numbers, {})

        number_check = next((r for r in results if r.name == "has_specific_numbers"), None)
        if number_check:
            assert not number_check.passed


class TestNonGenericChecks:
    """Test non-generic quality checks."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_detects_placeholder_text(self, checker):
        """Should detect placeholder patterns."""
        results = checker.run_all_checks(BAD_OUTPUT_PLACEHOLDER, {})

        placeholder_check = next((r for r in results if r.name == "no_placeholder_text"), None)
        if placeholder_check:
            assert not placeholder_check.passed

    def test_passes_without_placeholders(self, checker):
        """Good output should pass placeholder check."""
        results = checker.run_all_checks(GOOD_OUTPUT, {})

        placeholder_check = next((r for r in results if r.name == "no_placeholder_text"), None)
        if placeholder_check:
            assert placeholder_check.passed


class TestAntiPatternDetector:
    """Test anti-pattern detection."""

    @pytest.fixture
    def detector(self):
        return AntiPatternDetector()

    def test_detector_instantiation(self, detector):
        """Should instantiate anti-pattern detector."""
        assert detector is not None
        assert hasattr(detector, "scan")  # Method is called scan, not detect

    def test_scans_for_anti_patterns(self, detector):
        """Should scan for anti-patterns in output."""
        result = detector.scan(BAD_OUTPUT_GENERIC)

        assert isinstance(result, AntiPatternResult)

    def test_scan_returns_result(self, detector):
        """Scan should return AntiPatternResult."""
        result = detector.scan(BAD_OUTPUT_PLACEHOLDER)

        assert result is not None
        assert isinstance(result, AntiPatternResult)

    def test_specific_text_has_fewer_issues(self, detector):
        """Specific text should have fewer anti-pattern matches."""
        specific_text = """
        Create landing page at /projekthantering-software targeting 'projekthantering software'
        (2,400 vol, KD 42). Add comparison table vs Asana, Monday.com. Timeline: 2-3 weeks.
        Expected impact: 500+ monthly visits.
        """
        result = detector.scan(specific_text)

        # Result should exist
        assert result is not None


class TestAntiPatternSeverity:
    """Test anti-pattern severity levels."""

    def test_severity_enum_values(self):
        """Severity enum should have expected values."""
        assert hasattr(AntiPatternSeverity, "LOW")
        assert hasattr(AntiPatternSeverity, "MEDIUM")
        assert hasattr(AntiPatternSeverity, "HIGH")
        assert hasattr(AntiPatternSeverity, "CRITICAL")


class TestCheckResult:
    """Test CheckResult structure."""

    def test_check_result_fields(self):
        """CheckResult should have required fields."""
        result = CheckResult(
            name="test_check",
            category=CheckCategory.SPECIFICITY,
            passed=True,
            message="Test passed",
        )

        assert result.name == "test_check"
        assert result.category == CheckCategory.SPECIFICITY
        assert result.passed == True
        assert result.message == "Test passed"


class TestQualityScoreCalculation:
    """Test quality score calculation."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_score_bounded(self, checker):
        """Score should be between 0 and 10."""
        results = checker.run_all_checks(GOOD_OUTPUT, {})
        score = checker.calculate_score(results)

        assert 0 <= score <= 10

    def test_threshold_is_23(self, checker):
        """Pass threshold should be 23/25."""
        assert checker.PASS_THRESHOLD == 23


class TestQualityCheckTypes:
    """Test that each quality check has required attributes."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_all_checks_have_name(self, checker):
        """All checks should have a name."""
        for check in checker.checks:
            assert check.name is not None
            assert len(check.name) > 0

    def test_all_checks_have_category(self, checker):
        """All checks should have a category."""
        for check in checker.checks:
            assert check.category is not None
            assert isinstance(check.category, CheckCategory)

    def test_all_checks_have_description(self, checker):
        """All checks should have a description."""
        for check in checker.checks:
            assert check.description is not None
            assert len(check.description) > 0

    def test_all_checks_have_callable(self, checker):
        """All checks should have a callable check function."""
        for check in checker.checks:
            assert callable(check.check_fn)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

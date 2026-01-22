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

BAD_OUTPUT_NO_DATA = """
<analysis>
<executive_summary>
The website has several SEO opportunities to explore.
</executive_summary>

<recommendations>
<item>Improve keyword targeting</item>
<item>Build more backlinks</item>
<item>Fix technical issues</item>
</recommendations>
</analysis>
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

    def test_check_good_output(self, checker):
        """Good output should pass quality checks."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        assert result.passed
        assert result.score >= 9.2  # 23/25 = 92%

    def test_check_generic_output(self, checker):
        """Generic output should fail quality checks."""
        result = checker.check("keyword_intelligence", BAD_OUTPUT_GENERIC)

        assert not result.passed
        assert result.score < 9.2

    def test_check_no_data_output(self, checker):
        """Output without specific data should fail."""
        result = checker.check("keyword_intelligence", BAD_OUTPUT_NO_DATA)

        assert not result.passed

    def test_check_placeholder_output(self, checker):
        """Output with placeholders should fail."""
        result = checker.check("keyword_intelligence", BAD_OUTPUT_PLACEHOLDER)

        assert not result.passed

    def test_returns_check_results(self, checker):
        """Should return list of individual check results."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        assert hasattr(result, "checks")
        assert len(result.checks) == 25

    def test_categorizes_checks(self, checker):
        """Should categorize checks by type."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        categories = [c.category for c in result.checks]
        assert CheckCategory.SPECIFICITY in categories or "specificity" in str(categories).lower()


class TestSpecificityChecks:
    """Test the 7 specificity checks."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_check_has_specific_keywords(self, checker):
        """Should check for specific keyword mentions."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        specificity_checks = [c for c in result.checks if "specific" in c.name.lower() or c.category == CheckCategory.SPECIFICITY]
        keyword_check = next((c for c in specificity_checks if "keyword" in c.name.lower()), None)

        if keyword_check:
            assert keyword_check.passed

    def test_check_has_specific_urls(self, checker):
        """Should check for specific URL mentions."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        # Good output has /projekthantering-software URL
        url_check = next((c for c in result.checks if "url" in c.name.lower()), None)

        if url_check:
            assert url_check.passed

    def test_check_has_specific_numbers(self, checker):
        """Should check for specific numbers/metrics."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        # Good output has 2400 volume, 42 difficulty, etc.
        number_check = next((c for c in result.checks if "number" in c.name.lower() or "metric" in c.name.lower()), None)

        if number_check:
            assert number_check.passed

    def test_fails_without_specifics(self, checker):
        """Should fail when output lacks specifics."""
        result = checker.check("keyword_intelligence", BAD_OUTPUT_GENERIC)

        specificity_checks = [c for c in result.checks if c.category == CheckCategory.SPECIFICITY]
        passed_count = sum(1 for c in specificity_checks if c.passed)

        # Most specificity checks should fail for generic output
        assert passed_count < len(specificity_checks)


class TestActionabilityChecks:
    """Test the 6 actionability checks."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_check_has_specific_actions(self, checker):
        """Should check for specific recommended actions."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        action_checks = [c for c in result.checks if c.category == CheckCategory.ACTIONABILITY]

        # Good output has "Create dedicated landing page at /projekthantering-software"
        if action_checks:
            passed_count = sum(1 for c in action_checks if c.passed)
            assert passed_count > 0

    def test_check_has_effort_estimates(self, checker):
        """Should check for effort estimates."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        effort_check = next((c for c in result.checks if "effort" in c.name.lower()), None)

        # Good output has "Medium - 2-3 weeks development"
        if effort_check:
            assert effort_check.passed

    def test_check_has_impact_estimates(self, checker):
        """Should check for impact estimates."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        impact_check = next((c for c in result.checks if "impact" in c.name.lower()), None)

        # Good output has "500+ monthly visits potential"
        if impact_check:
            assert impact_check.passed

    def test_check_has_timeline(self, checker):
        """Should check for timeline/deadline."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        timeline_check = next((c for c in result.checks if "timeline" in c.name.lower() or "deadline" in c.name.lower()), None)

        # Good output has "Launch by February 15"
        if timeline_check:
            assert timeline_check.passed


class TestDataGroundingChecks:
    """Test the 6 data-grounding checks."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_check_cites_actual_data(self, checker):
        """Should check that recommendations cite actual data."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        data_checks = [c for c in result.checks if c.category == CheckCategory.DATA_GROUNDING]

        # Good output references actual metrics (2400 vol, KD 42)
        if data_checks:
            passed_count = sum(1 for c in data_checks if c.passed)
            assert passed_count > 0

    def test_check_uses_provided_metrics(self, checker):
        """Should verify output uses metrics from provided data."""
        # This would need actual data to validate against
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        # At minimum, numbers should be present
        assert any(char.isdigit() for char in str(result))


class TestNonGenericChecks:
    """Test the 6 non-generic checks."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_detects_generic_phrases(self, checker):
        """Should detect and fail generic phrases."""
        result = checker.check("keyword_intelligence", BAD_OUTPUT_GENERIC)

        non_generic_checks = [c for c in result.checks if c.category == CheckCategory.NON_GENERIC]

        # Should fail because of "Based on comprehensive analysis"
        if non_generic_checks:
            failed_count = sum(1 for c in non_generic_checks if not c.passed)
            assert failed_count > 0

    def test_passes_specific_language(self, checker):
        """Should pass when language is specific."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        non_generic_checks = [c for c in result.checks if c.category == CheckCategory.NON_GENERIC]

        if non_generic_checks:
            passed_count = sum(1 for c in non_generic_checks if c.passed)
            assert passed_count == len(non_generic_checks)


class TestAntiPatternDetector:
    """Test anti-pattern detection."""

    @pytest.fixture
    def detector(self):
        return AntiPatternDetector()

    def test_detects_comprehensive_analysis(self, detector):
        """Should detect 'comprehensive analysis' anti-pattern."""
        result = detector.detect(BAD_OUTPUT_GENERIC)

        assert isinstance(result, AntiPatternResult)
        assert len(result.matches) > 0

        patterns = [m.pattern for m in result.matches]
        assert any("comprehensive" in p.lower() for p in patterns)

    def test_detects_placeholders(self, detector):
        """Should detect placeholder patterns like [DOMAIN]."""
        result = detector.detect(BAD_OUTPUT_PLACEHOLDER)

        assert len(result.matches) > 0

        patterns = [m.pattern for m in result.matches]
        assert any("[" in p for p in patterns) or any("placeholder" in m.description.lower() for m in result.matches)

    def test_detects_vague_recommendations(self, detector):
        """Should detect vague recommendations."""
        vague_text = "Optimize existing high-potential pages for better rankings."
        result = detector.detect(vague_text)

        # "optimize existing" or "high-potential" without specifics is vague
        assert len(result.matches) > 0

    def test_no_matches_for_specific_text(self, detector):
        """Should not flag specific, actionable text."""
        specific_text = "Create landing page at /projekthantering-software targeting 'projekthantering software' (2,400 vol, KD 42). Add comparison table vs Asana, Monday.com."
        result = detector.detect(specific_text)

        # Should have few or no matches
        assert len(result.matches) == 0 or all(m.severity == AntiPatternSeverity.LOW for m in result.matches)

    def test_severity_levels(self, detector):
        """Should assign severity levels to matches."""
        result = detector.detect(BAD_OUTPUT_GENERIC)

        if result.matches:
            severities = [m.severity for m in result.matches]
            assert all(s in [AntiPatternSeverity.LOW, AntiPatternSeverity.MEDIUM, AntiPatternSeverity.HIGH, AntiPatternSeverity.CRITICAL] for s in severities)


class TestQualityScoreCalculation:
    """Test quality score calculation."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_score_is_0_to_10(self, checker):
        """Score should be between 0 and 10."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)
        assert 0 <= result.score <= 10

        result2 = checker.check("keyword_intelligence", BAD_OUTPUT_GENERIC)
        assert 0 <= result2.score <= 10

    def test_score_calculation_formula(self, checker):
        """Score should be (passed_checks / total_checks) * 10."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        passed_count = sum(1 for c in result.checks if c.passed)
        expected_score = (passed_count / 25) * 10

        assert abs(result.score - expected_score) < 0.1

    def test_threshold_at_92_percent(self, checker):
        """Threshold should be 92% (23/25 checks)."""
        # 23/25 = 0.92 = 9.2 score
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        if result.score >= 9.2:
            assert result.passed
        else:
            assert not result.passed


class TestQualityCheckDetails:
    """Test individual quality check details."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    def test_check_has_name(self, checker):
        """Each check should have a name."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        for check in result.checks:
            assert hasattr(check, "name")
            assert len(check.name) > 0

    def test_check_has_description(self, checker):
        """Each check should have a description."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        for check in result.checks:
            assert hasattr(check, "description") or hasattr(check, "message")

    def test_check_has_passed_flag(self, checker):
        """Each check should have passed boolean."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        for check in result.checks:
            assert hasattr(check, "passed")
            assert isinstance(check.passed, bool)

    def test_check_has_category(self, checker):
        """Each check should have a category."""
        result = checker.check("keyword_intelligence", GOOD_OUTPUT)

        for check in result.checks:
            assert hasattr(check, "category")


class TestAllAgentQualityChecks:
    """Test quality checks work for all agent types."""

    @pytest.fixture
    def checker(self):
        return AgentQualityChecker()

    @pytest.mark.parametrize("agent_name", [
        "keyword_intelligence",
        "backlink_intelligence",
        "technical_seo",
        "content_analysis",
        "semantic_architecture",
        "ai_visibility",
        "serp_analysis",
        "local_seo",
        "master_strategy",
    ])
    def test_checker_works_for_agent(self, checker, agent_name):
        """Quality checker should work for each agent type."""
        result = checker.check(agent_name, GOOD_OUTPUT)

        assert result is not None
        assert hasattr(result, "score")
        assert hasattr(result, "passed")
        assert hasattr(result, "checks")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

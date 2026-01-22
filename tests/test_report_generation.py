"""
Test Suite for Phase 5: Report Generation

Tests that reports are data-driven and not template-based:
- External Report (10-15 pages, executive-focused)
- Internal Report (40-60 pages, tactical playbook)
- No placeholder text
- Specific data from agents
"""

import pytest
from typing import Dict, Any
from datetime import datetime

from src.reporter import (
    ExternalReportBuilder,
    InternalReportBuilder,
    ChartGenerator,
)


# Mock agent outputs for testing
MOCK_AGENT_OUTPUTS = {
    "keyword_intelligence": {
        "executive_summary": "Analysis of example.se reveals 23 high-priority keyword opportunities.",
        "priority_stack": [
            {
                "term": "projekthantering software",
                "volume": 2400,
                "difficulty": 42,
                "personalized_difficulty": 35,
                "opportunity_score": 89,
                "current_position": 15,
                "intent": "commercial",
                "recommended_action": "Create dedicated landing page",
                "effort": "Medium - 2-3 weeks",
                "impact": "High - 500+ monthly visits",
            },
            {
                "term": "gratis projektverktyg",
                "volume": 1800,
                "difficulty": 38,
                "opportunity_score": 82,
                "current_position": 23,
                "intent": "informational",
            },
        ],
        "quick_wins": [
            {"term": "projekthantering gratis", "position": 11, "action": "Add FAQ section"},
        ],
        "total_opportunity_volume": 45000,
    },
    "backlink_intelligence": {
        "executive_summary": "Domain has 2,340 referring domains vs competitor average of 5,600.",
        "link_gap": {
            "total_gap": 3260,
            "top_competitors": [
                {"domain": "competitor1.se", "referring_domains": 8200},
                {"domain": "competitor2.se", "referring_domains": 4500},
            ],
        },
        "prospect_tiers": {
            "tier1": [
                {"domain": "techblog.se", "dr": 72, "approach": "Guest post"},
            ],
        },
        "anchor_distribution": {
            "branded": 45,
            "exact_match": 15,
            "partial_match": 25,
            "generic": 15,
        },
    },
    "technical_seo": {
        "executive_summary": "12 critical technical issues identified affecting organic visibility.",
        "critical_issues": [
            {
                "type": "Core Web Vitals",
                "metric": "LCP",
                "current": "4.2s",
                "target": "2.5s",
                "fix": "Optimize hero images",
                "effort": "Medium",
                "impact": "High",
            },
        ],
        "cwv_scores": {"lcp": 4.2, "fid": 89, "cls": 0.15},
        "indexing_status": {"indexed": 450, "blocked": 87},
    },
    "content_analysis": {
        "executive_summary": "Content audit reveals 15 pages for update, 8 for consolidation.",
        "kuck_recommendations": {
            "keep": ["/features", "/pricing"],
            "update": ["/blog/old-post-1", "/blog/old-post-2"],
            "consolidate": ["/blog/similar-1", "/blog/similar-2"],
            "kill": ["/outdated-page"],
        },
        "decay_analysis": [
            {"url": "/blog/post-1", "decay_score": 72, "recommendation": "update"},
        ],
    },
    "semantic_architecture": {
        "executive_summary": "Topic cluster analysis identifies 5 hub opportunities.",
        "topic_clusters": [
            {
                "hub": "Project Management",
                "spokes": ["agile", "scrum", "kanban", "gantt"],
                "content_gaps": 3,
            },
        ],
        "internal_linking": {
            "orphan_pages": 12,
            "weak_clusters": ["pricing", "features"],
        },
    },
    "ai_visibility": {
        "executive_summary": "GEO analysis: 23% of keywords trigger AI Overviews.",
        "ai_overview_keywords": [
            {"term": "projekthantering", "has_ai_overview": True},
        ],
        "optimization_opportunities": [
            {"type": "schema", "action": "Add FAQ schema", "pages": 15},
        ],
        "geo_score": 45,
    },
    "serp_analysis": {
        "executive_summary": "Competitor analysis reveals 3 feature snippet opportunities.",
        "serp_features": {
            "featured_snippets": 3,
            "people_also_ask": 12,
            "image_packs": 5,
        },
        "competitor_strengths": [
            {"competitor": "competitor1.se", "strength": "Content depth"},
        ],
    },
    "master_strategy": {
        "executive_summary": "Strategic roadmap prioritizes technical fixes, then content.",
        "overall_seo_score": 62,
        "priority_matrix": [
            {"priority": 1, "action": "Fix CWV issues", "effort": "Medium", "impact": "High"},
            {"priority": 2, "action": "Target quick-win keywords", "effort": "Low", "impact": "Medium"},
        ],
        "roadmap_90_days": {
            "month1": ["Fix LCP", "Update robots.txt"],
            "month2": ["Create keyword landing pages"],
            "month3": ["Launch link building campaign"],
        },
        "resource_allocation": {
            "technical": 30,
            "content": 40,
            "link_building": 30,
        },
    },
}

MOCK_ANALYSIS_DATA = {
    "metadata": {
        "domain": "example.se",
        "analysis_date": datetime.now().isoformat(),
    },
    "summary": {
        "total_organic_keywords": 1247,
        "total_organic_traffic": 8500,
        "domain_rank": 45,
        "competitor_count": 12,
    },
    "phase1_foundation": {
        "technologies": [{"name": "WordPress"}, {"name": "WooCommerce"}],
        "technical_baseline": {"performance_score": 0.65},
    },
}


class TestExternalReportBuilder:
    """Test external report (lead magnet) generation."""

    @pytest.fixture
    def builder(self):
        return ExternalReportBuilder()

    def test_build_returns_html(self, builder):
        """Should return HTML string."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert isinstance(html, str)
        assert "<html" in html.lower() or "<!doctype" in html.lower()

    def test_contains_domain_name(self, builder):
        """Report should contain the analyzed domain."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert "example.se" in html

    def test_contains_executive_summary(self, builder):
        """Report should have executive summary section."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert "executive" in html.lower() or "summary" in html.lower()

    def test_contains_keyword_data(self, builder):
        """Report should contain specific keywords."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Should contain actual keyword from data
        assert "projekthantering" in html.lower()

    def test_contains_metrics(self, builder):
        """Report should contain specific metrics."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Should contain volume or difficulty numbers
        assert "2400" in html or "2,400" in html

    def test_no_placeholder_text(self, builder):
        """Report should not contain placeholder text."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Check for common placeholders
        assert "[DOMAIN]" not in html
        assert "[X]" not in html
        assert "[Y]" not in html
        assert "Lorem ipsum" not in html

    def test_no_generic_phrases(self, builder):
        """Report should not contain generic filler phrases."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        generic_phrases = [
            "Based on comprehensive analysis",
            "optimize existing high-potential pages",
            "implement best practices",
        ]

        for phrase in generic_phrases:
            assert phrase.lower() not in html.lower(), f"Found generic phrase: {phrase}"

    def test_contains_roadmap(self, builder):
        """Report should contain strategic roadmap."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert "roadmap" in html.lower() or "month" in html.lower() or "90" in html

    def test_contains_priority_actions(self, builder):
        """Report should contain prioritized actions."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert "priority" in html.lower() or "action" in html.lower()


class TestInternalReportBuilder:
    """Test internal report (strategy guide) generation."""

    @pytest.fixture
    def builder(self):
        return InternalReportBuilder()

    def test_build_returns_html(self, builder):
        """Should return HTML string."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert isinstance(html, str)
        assert "<html" in html.lower() or "<!doctype" in html.lower()

    def test_more_detailed_than_external(self, builder):
        """Internal report should be more detailed than external."""
        external_builder = ExternalReportBuilder()

        external_html = external_builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)
        internal_html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Internal should be longer
        assert len(internal_html) > len(external_html)

    def test_contains_all_keyword_details(self, builder):
        """Should contain detailed keyword information."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Should have multiple keywords listed
        assert "projekthantering software" in html.lower()
        assert "projektverktyg" in html.lower() or "gratis" in html.lower()

    def test_contains_technical_details(self, builder):
        """Should contain technical SEO details."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Should have CWV data
        assert "lcp" in html.lower() or "4.2" in html

    def test_contains_backlink_strategy(self, builder):
        """Should contain backlink strategy details."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert "backlink" in html.lower() or "link" in html.lower()
        assert "prospect" in html.lower() or "outreach" in html.lower()

    def test_contains_content_audit(self, builder):
        """Should contain content audit results."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # KUCK framework terms
        assert "update" in html.lower() or "consolidate" in html.lower()


class TestChartGenerator:
    """Test chart/visualization generation."""

    @pytest.fixture
    def generator(self):
        return ChartGenerator()

    def test_generates_opportunity_chart(self, generator):
        """Should generate keyword opportunity chart."""
        chart = generator.generate_opportunity_chart(
            MOCK_AGENT_OUTPUTS["keyword_intelligence"]["priority_stack"]
        )

        assert chart is not None

    def test_generates_competitor_chart(self, generator):
        """Should generate competitor comparison chart."""
        chart = generator.generate_competitor_chart(
            MOCK_AGENT_OUTPUTS["backlink_intelligence"]["link_gap"]
        )

        assert chart is not None

    def test_generates_cwv_chart(self, generator):
        """Should generate Core Web Vitals chart."""
        chart = generator.generate_cwv_chart(
            MOCK_AGENT_OUTPUTS["technical_seo"]["cwv_scores"]
        )

        assert chart is not None

    def test_generates_roadmap_timeline(self, generator):
        """Should generate roadmap timeline."""
        chart = generator.generate_roadmap_timeline(
            MOCK_AGENT_OUTPUTS["master_strategy"]["roadmap_90_days"]
        )

        assert chart is not None


class TestReportDataIntegration:
    """Test that report integrates all agent data correctly."""

    @pytest.fixture
    def builder(self):
        return ExternalReportBuilder()

    def test_integrates_keyword_agent(self, builder):
        """Report should use keyword agent data."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Data from keyword agent
        assert "89" in html or "opportunity" in html.lower()  # Opportunity score 89

    def test_integrates_backlink_agent(self, builder):
        """Report should use backlink agent data."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Data from backlink agent
        assert "2,340" in html or "2340" in html or "referring" in html.lower()

    def test_integrates_technical_agent(self, builder):
        """Report should use technical agent data."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Data from technical agent
        assert "4.2" in html or "lcp" in html.lower() or "core web" in html.lower()

    def test_integrates_master_strategy(self, builder):
        """Report should use master strategy data."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Data from master strategy
        assert "62" in html or "seo score" in html.lower() or "roadmap" in html.lower()


class TestReportQuality:
    """Test report quality requirements."""

    @pytest.fixture
    def builder(self):
        return ExternalReportBuilder()

    def test_every_recommendation_has_data(self, builder):
        """Every recommendation should cite specific data."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Report should have numbers throughout
        import re
        numbers = re.findall(r'\d+', html)
        assert len(numbers) > 20, "Report should contain many specific numbers"

    def test_every_action_has_effort(self, builder):
        """Actions should have effort estimates."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        effort_terms = ["week", "day", "hour", "low", "medium", "high"]
        has_effort = any(term in html.lower() for term in effort_terms)
        assert has_effort, "Report should contain effort estimates"

    def test_every_action_has_impact(self, builder):
        """Actions should have impact estimates."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        impact_terms = ["impact", "result", "traffic", "visits", "conversion"]
        has_impact = any(term in html.lower() for term in impact_terms)
        assert has_impact, "Report should contain impact estimates"


class TestReportFormatting:
    """Test report HTML formatting."""

    @pytest.fixture
    def builder(self):
        return ExternalReportBuilder()

    def test_has_proper_html_structure(self, builder):
        """Should have proper HTML document structure."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert "<head>" in html.lower() or "<head" in html.lower()
        assert "<body>" in html.lower() or "<body" in html.lower()

    def test_has_styling(self, builder):
        """Should include CSS styling."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        assert "<style" in html.lower() or "class=" in html.lower()

    def test_has_sections(self, builder):
        """Should have clear sections."""
        html = builder.build(MOCK_AGENT_OUTPUTS, MOCK_ANALYSIS_DATA)

        # Should have multiple section-like elements
        assert html.count("<section") > 2 or html.count("<div") > 10


class TestReportEdgeCases:
    """Test report generation with edge cases."""

    def test_handles_missing_agent_output(self):
        """Should handle missing agent outputs gracefully."""
        builder = ExternalReportBuilder()

        partial_outputs = {
            "keyword_intelligence": MOCK_AGENT_OUTPUTS["keyword_intelligence"],
            "master_strategy": MOCK_AGENT_OUTPUTS["master_strategy"],
            # Missing other agents
        }

        html = builder.build(partial_outputs, MOCK_ANALYSIS_DATA)

        # Should still generate something
        assert len(html) > 0
        assert "example.se" in html

    def test_handles_empty_priority_stack(self):
        """Should handle empty keyword list."""
        builder = ExternalReportBuilder()

        outputs_with_empty = dict(MOCK_AGENT_OUTPUTS)
        outputs_with_empty["keyword_intelligence"] = {
            "executive_summary": "No keywords found.",
            "priority_stack": [],
        }

        html = builder.build(outputs_with_empty, MOCK_ANALYSIS_DATA)

        # Should not crash
        assert len(html) > 0

    def test_handles_special_characters(self):
        """Should handle special characters in data."""
        builder = ExternalReportBuilder()

        outputs_with_special = dict(MOCK_AGENT_OUTPUTS)
        outputs_with_special["keyword_intelligence"]["priority_stack"][0]["term"] = "köpa & sälja <produkter>"

        html = builder.build(outputs_with_special, MOCK_ANALYSIS_DATA)

        # Should escape or handle special chars
        assert len(html) > 0
        assert "&lt;" in html or "köpa" in html  # Either escaped or raw


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

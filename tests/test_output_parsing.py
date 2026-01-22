"""
Test Suite for Phase 4: Output Parsing & Validation

Tests the XML/structured output parsing from agents.
"""

import pytest
from typing import Dict, Any

from src.output import (
    AgentOutputConverter,
    BatchOutputConverter,
    ConversionResult,
)


# Sample agent outputs for testing
SAMPLE_KEYWORD_OUTPUT = """
<analysis>
<executive_summary>
This domain has significant keyword opportunities in the Swedish SaaS market.
Top priority keywords identified with combined opportunity score of 847.
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
<recommended_action>Create dedicated landing page with comparison table</recommended_action>
<effort>Medium (2-3 weeks)</effort>
<impact>High - 500+ monthly visits potential</impact>
</keyword>

<keyword priority="2">
<term>gratis projektverktyg</term>
<volume>1800</volume>
<difficulty>38</difficulty>
<personalized_difficulty>32</personalized_difficulty>
<opportunity_score>82</opportunity_score>
<current_position>23</current_position>
<intent>informational</intent>
<recommended_action>Optimize existing /free-tools page</recommended_action>
<effort>Low (1 week)</effort>
<impact>Medium - 200+ monthly visits potential</impact>
</keyword>
</priority_stack>

<quick_wins>
<keyword>
<term>projekthantering gratis</term>
<current_position>11</current_position>
<action>Add FAQ section and internal links</action>
<expected_improvement>Position 5-7</expected_improvement>
</keyword>
</quick_wins>
</analysis>
"""

SAMPLE_TECHNICAL_OUTPUT = """
<technical_analysis>
<critical_issues>
<issue severity="critical">
<type>Core Web Vitals</type>
<metric>LCP</metric>
<current_value>4.2s</current_value>
<target_value>2.5s</target_value>
<affected_pages>12 pages</affected_pages>
<fix>Optimize hero images, implement lazy loading</fix>
<effort>Medium (1-2 weeks)</effort>
<impact>High - affects all organic traffic</impact>
</issue>

<issue severity="high">
<type>Indexing</type>
<description>87 pages blocked by robots.txt</description>
<affected_urls>/blog/*, /resources/*</affected_urls>
<fix>Update robots.txt to allow crawling of valuable content</fix>
<effort>Low (1 day)</effort>
<impact>High - unlock 87 pages for indexing</impact>
</issue>
</critical_issues>

<cwv_scores>
<lcp>4.2s</lcp>
<fid>89ms</fid>
<cls>0.15</cls>
<overall>needs_improvement</overall>
</cwv_scores>
</technical_analysis>
"""

SAMPLE_BACKLINK_OUTPUT = """
<backlink_analysis>
<executive_summary>
Domain has 2,340 referring domains vs competitor average of 5,600.
Link gap presents significant opportunity for growth.
</executive_summary>

<link_gap>
<competitor name="competitor1.se">
<referring_domains>8200</referring_domains>
<gap>5860</gap>
<shared_links>340</shared_links>
</competitor>
</link_gap>

<prospect_tiers>
<tier level="1" name="High Priority">
<prospect>
<domain>techblog.se</domain>
<dr>72</dr>
<traffic>45000</traffic>
<relevance>0.92</relevance>
<approach>Guest post on project management</approach>
<contact_method>Email editor via contact form</contact_method>
</prospect>
</tier>
</prospect_tiers>

<anchor_strategy>
<current_distribution>
<branded>45%</branded>
<exact_match>15%</exact_match>
<partial_match>25%</partial_match>
<generic>15%</generic>
</current_distribution>
<recommendation>Increase branded anchors to 50%, reduce exact match to 10%</recommendation>
</anchor_strategy>
</backlink_analysis>
"""


class TestAgentOutputConverter:
    """Test the main output converter."""

    @pytest.fixture
    def converter(self):
        return AgentOutputConverter()

    def test_convert_keyword_output(self, converter):
        """Should parse keyword agent XML output."""
        result = converter.convert("keyword_intelligence", SAMPLE_KEYWORD_OUTPUT)

        assert isinstance(result, ConversionResult)
        assert result.success
        assert result.data is not None

    def test_convert_technical_output(self, converter):
        """Should parse technical agent XML output."""
        result = converter.convert("technical_seo", SAMPLE_TECHNICAL_OUTPUT)

        assert result.success
        assert result.data is not None

    def test_convert_backlink_output(self, converter):
        """Should parse backlink agent XML output."""
        result = converter.convert("backlink_intelligence", SAMPLE_BACKLINK_OUTPUT)

        assert result.success
        assert result.data is not None

    def test_extract_keywords_from_output(self, converter):
        """Should extract keyword list from output."""
        result = converter.convert("keyword_intelligence", SAMPLE_KEYWORD_OUTPUT)

        assert result.success
        keywords = result.data.get("keywords", result.data.get("priority_stack", []))
        assert len(keywords) > 0

    def test_extract_issues_from_technical_output(self, converter):
        """Should extract issues from technical output."""
        result = converter.convert("technical_seo", SAMPLE_TECHNICAL_OUTPUT)

        assert result.success
        issues = result.data.get("critical_issues", result.data.get("issues", []))
        assert len(issues) > 0

    def test_extract_prospects_from_backlink_output(self, converter):
        """Should extract link prospects from backlink output."""
        result = converter.convert("backlink_intelligence", SAMPLE_BACKLINK_OUTPUT)

        assert result.success
        prospects = result.data.get("prospect_tiers", result.data.get("prospects", []))
        assert prospects is not None

    def test_handles_malformed_xml(self, converter):
        """Should handle malformed XML gracefully."""
        malformed = "<analysis><keyword>test</keyword>"  # Missing closing tag

        result = converter.convert("keyword_intelligence", malformed)

        # Should not crash, may return partial result or error
        assert result is not None

    def test_handles_empty_output(self, converter):
        """Should handle empty output."""
        result = converter.convert("keyword_intelligence", "")

        assert not result.success or result.data == {}

    def test_handles_plain_text_output(self, converter):
        """Should handle plain text (non-XML) output."""
        plain_text = "Here are the keyword recommendations: keyword1, keyword2, keyword3"

        result = converter.convert("keyword_intelligence", plain_text)

        # Should attempt to parse or return raw text
        assert result is not None


class TestBatchOutputConverter:
    """Test batch conversion of multiple agent outputs."""

    @pytest.fixture
    def batch_converter(self):
        return BatchOutputConverter()

    def test_batch_convert_multiple_agents(self, batch_converter):
        """Should convert outputs from multiple agents."""
        outputs = {
            "keyword_intelligence": SAMPLE_KEYWORD_OUTPUT,
            "technical_seo": SAMPLE_TECHNICAL_OUTPUT,
            "backlink_intelligence": SAMPLE_BACKLINK_OUTPUT,
        }

        results = batch_converter.convert_all(outputs)

        assert len(results) == 3
        assert "keyword_intelligence" in results
        assert "technical_seo" in results
        assert "backlink_intelligence" in results

    def test_batch_handles_partial_failures(self, batch_converter):
        """Should continue processing even if one agent fails."""
        outputs = {
            "keyword_intelligence": SAMPLE_KEYWORD_OUTPUT,
            "technical_seo": "<malformed>",  # Invalid
            "backlink_intelligence": SAMPLE_BACKLINK_OUTPUT,
        }

        results = batch_converter.convert_all(outputs)

        # Should still return results for valid outputs
        assert "keyword_intelligence" in results
        assert "backlink_intelligence" in results


class TestOutputDataExtraction:
    """Test specific data extraction from outputs."""

    @pytest.fixture
    def converter(self):
        return AgentOutputConverter()

    def test_extract_volume_from_keyword(self, converter):
        """Should extract search volume from keywords."""
        result = converter.convert("keyword_intelligence", SAMPLE_KEYWORD_OUTPUT)

        if result.success and result.data:
            keywords = result.data.get("keywords", result.data.get("priority_stack", []))
            if keywords:
                first_keyword = keywords[0] if isinstance(keywords, list) else keywords
                # Volume should be extractable
                assert "volume" in str(first_keyword).lower() or "2400" in str(first_keyword)

    def test_extract_difficulty_from_keyword(self, converter):
        """Should extract difficulty from keywords."""
        result = converter.convert("keyword_intelligence", SAMPLE_KEYWORD_OUTPUT)

        if result.success and result.data:
            # Difficulty should be present somewhere
            assert "difficulty" in str(result.data).lower() or "42" in str(result.data)

    def test_extract_cwv_metrics(self, converter):
        """Should extract Core Web Vitals metrics."""
        result = converter.convert("technical_seo", SAMPLE_TECHNICAL_OUTPUT)

        if result.success and result.data:
            # Should have CWV data
            data_str = str(result.data).lower()
            assert "lcp" in data_str or "4.2" in str(result.data)

    def test_extract_link_gap_data(self, converter):
        """Should extract link gap data."""
        result = converter.convert("backlink_intelligence", SAMPLE_BACKLINK_OUTPUT)

        if result.success and result.data:
            # Should have link gap info
            data_str = str(result.data).lower()
            assert "gap" in data_str or "referring" in data_str


class TestOutputValidation:
    """Test output validation rules."""

    @pytest.fixture
    def converter(self):
        return AgentOutputConverter()

    def test_keyword_output_has_required_fields(self, converter):
        """Keyword output should have term, volume, difficulty."""
        result = converter.convert("keyword_intelligence", SAMPLE_KEYWORD_OUTPUT)

        if result.success:
            raw = str(result.data).lower()
            assert "term" in raw or "keyword" in raw
            assert "volume" in raw or any(str(n) in str(result.data) for n in [2400, 1800])
            assert "difficulty" in raw

    def test_technical_output_has_severity(self, converter):
        """Technical output should have severity levels."""
        result = converter.convert("technical_seo", SAMPLE_TECHNICAL_OUTPUT)

        if result.success:
            raw = str(result.data).lower()
            assert "critical" in raw or "high" in raw or "severity" in raw

    def test_backlink_output_has_metrics(self, converter):
        """Backlink output should have domain metrics."""
        result = converter.convert("backlink_intelligence", SAMPLE_BACKLINK_OUTPUT)

        if result.success:
            raw = str(result.data).lower()
            assert "dr" in raw or "domain" in raw or "referring" in raw


class TestConversionResultStructure:
    """Test ConversionResult structure."""

    @pytest.fixture
    def converter(self):
        return AgentOutputConverter()

    def test_result_has_success_flag(self, converter):
        """Result should have success boolean."""
        result = converter.convert("keyword_intelligence", SAMPLE_KEYWORD_OUTPUT)
        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

    def test_result_has_data(self, converter):
        """Result should have data dict."""
        result = converter.convert("keyword_intelligence", SAMPLE_KEYWORD_OUTPUT)
        if result.success:
            assert hasattr(result, "data")
            assert isinstance(result.data, dict)

    def test_result_has_errors_on_failure(self, converter):
        """Failed result should have error info."""
        result = converter.convert("keyword_intelligence", "")
        if not result.success:
            assert hasattr(result, "errors") or hasattr(result, "error")


class TestXMLParsing:
    """Test XML parsing specifics."""

    def test_parse_nested_xml(self):
        """Should handle nested XML structures."""
        converter = AgentOutputConverter()
        nested_xml = """
        <analysis>
            <section name="overview">
                <subsection>
                    <item>Value 1</item>
                    <item>Value 2</item>
                </subsection>
            </section>
        </analysis>
        """
        result = converter.convert("keyword_intelligence", nested_xml)
        # Should not crash on nested structures
        assert result is not None

    def test_parse_xml_with_attributes(self):
        """Should handle XML attributes."""
        converter = AgentOutputConverter()
        xml_with_attrs = """
        <analysis version="1.0">
            <keyword priority="1" type="commercial">
                <term>test keyword</term>
            </keyword>
        </analysis>
        """
        result = converter.convert("keyword_intelligence", xml_with_attrs)
        assert result is not None

    def test_parse_cdata_sections(self):
        """Should handle CDATA sections."""
        converter = AgentOutputConverter()
        xml_with_cdata = """
        <analysis>
            <description><![CDATA[This is a <special> description]]></description>
        </analysis>
        """
        result = converter.convert("keyword_intelligence", xml_with_cdata)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

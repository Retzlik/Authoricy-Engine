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
    OutputParser,
    ParseResult,
)


# Sample agent outputs for testing
SAMPLE_KEYWORD_OUTPUT = """
<analysis>
<executive_summary>
This domain has significant keyword opportunities in the Swedish SaaS market.
</executive_summary>

<priority_stack>
<keyword priority="1">
<term>projekthantering software</term>
<volume>2400</volume>
<difficulty>42</difficulty>
</keyword>
</priority_stack>
</analysis>
"""


class TestOutputParser:
    """Test the base output parser."""

    @pytest.fixture
    def parser(self):
        return OutputParser()

    def test_parser_instantiation(self, parser):
        """Parser should instantiate."""
        assert parser is not None
        assert hasattr(parser, "parse")

    def test_parse_returns_result(self, parser):
        """Parse should return a ParseResult."""
        result = parser.parse(SAMPLE_KEYWORD_OUTPUT)
        assert isinstance(result, ParseResult)

    def test_parse_handles_empty(self, parser):
        """Should handle empty input."""
        result = parser.parse("")
        assert result is not None


class TestAgentOutputConverter:
    """Test the main output converter."""

    @pytest.fixture
    def converter(self):
        return AgentOutputConverter()

    def test_converter_instantiation(self, converter):
        """Converter should instantiate."""
        assert converter is not None
        assert hasattr(converter, "convert")

    def test_converter_has_parser(self, converter):
        """Converter should have parser."""
        assert hasattr(converter, "parser")

    def test_converter_has_quality_checker(self, converter):
        """Converter should have quality checker."""
        assert hasattr(converter, "quality_checker")


class TestBatchOutputConverter:
    """Test batch conversion of multiple agent outputs."""

    @pytest.fixture
    def batch_converter(self):
        return BatchOutputConverter()

    def test_batch_converter_instantiation(self, batch_converter):
        """Batch converter should instantiate."""
        assert batch_converter is not None
        assert hasattr(batch_converter, "convert_all")


class TestConversionResultStructure:
    """Test ConversionResult structure."""

    def test_conversion_result_dataclass(self):
        """ConversionResult should be a proper dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(ConversionResult)

    def test_conversion_result_has_success(self):
        """ConversionResult should have success field."""
        fields = {f.name for f in __import__('dataclasses').fields(ConversionResult)}
        assert "success" in fields

    def test_conversion_result_has_quality_score(self):
        """ConversionResult should have quality_score field."""
        fields = {f.name for f in __import__('dataclasses').fields(ConversionResult)}
        assert "quality_score" in fields


class TestParseResult:
    """Test ParseResult structure."""

    def test_parse_result_dataclass(self):
        """ParseResult should be a proper dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(ParseResult)


class TestXMLParsing:
    """Test XML parsing specifics."""

    @pytest.fixture
    def parser(self):
        return OutputParser()

    def test_parse_nested_xml(self, parser):
        """Should handle nested XML structures."""
        nested_xml = """
        <analysis>
            <section>
                <item>Value</item>
            </section>
        </analysis>
        """
        result = parser.parse(nested_xml)
        assert result is not None

    def test_parse_xml_with_attributes(self, parser):
        """Should handle XML attributes."""
        xml_with_attrs = """
        <analysis version="1.0">
            <keyword priority="1">test</keyword>
        </analysis>
        """
        result = parser.parse(xml_with_attrs)
        assert result is not None

    def test_parse_malformed_xml(self, parser):
        """Should handle malformed XML gracefully."""
        malformed = "<analysis><keyword>test</keyword>"
        result = parser.parse(malformed)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

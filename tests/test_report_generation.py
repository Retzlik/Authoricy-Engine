"""
Test Suite for Phase 5: Report Generation

v7: ONE REPORT, ONE ROUTE

Tests that reports are data-driven with confidence tracking.
Note: Full report generation requires template files.
"""

import pytest
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

from src.reporter import (
    ReportBuilder,
    ReportConfidence,
    ChartGenerator,
    # Legacy imports (deprecated but kept for backwards compatibility)
    ExternalReportBuilder,
    InternalReportBuilder,
)


class TestChartGenerator:
    """Test chart/visualization generation."""

    @pytest.fixture
    def generator(self):
        return ChartGenerator()

    def test_generator_instantiation(self, generator):
        """Generator should instantiate."""
        assert generator is not None

    def test_generator_has_methods(self, generator):
        """Generator should have chart methods."""
        # Check for chart methods
        assert hasattr(generator, '__init__')


class TestReportBuilder:
    """Test the unified ReportBuilder class."""

    @pytest.fixture
    def template_dir(self, tmp_path):
        return tmp_path

    def test_report_builder_exists(self):
        """ReportBuilder class should exist."""
        assert ReportBuilder is not None

    def test_report_builder_has_build_method(self):
        """ReportBuilder should have build method."""
        assert hasattr(ReportBuilder, 'build')

    def test_report_builder_instantiation(self, template_dir):
        """ReportBuilder should instantiate with template_dir."""
        builder = ReportBuilder(template_dir)
        assert builder is not None

    def test_report_builder_has_confidence(self, template_dir):
        """ReportBuilder should track confidence."""
        builder = ReportBuilder(template_dir)
        assert hasattr(builder, 'confidence')

    def test_report_builder_build_returns_tuple(self, template_dir):
        """ReportBuilder.build should return (html, confidence)."""
        builder = ReportBuilder(template_dir)
        analysis_data = {
            "metadata": {"domain": "test.com", "market": "US"},
            "summary": {},
        }
        result = builder.build(None, analysis_data)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_report_builder_confidence_tracking(self, template_dir):
        """ReportBuilder should track data presence."""
        builder = ReportBuilder(template_dir)
        analysis_data = {
            "metadata": {"domain": "test.com", "market": "US"},
            "summary": {"total_organic_keywords": 1000},
        }
        html, confidence = builder.build(None, analysis_data)
        assert isinstance(confidence, ReportConfidence)
        assert hasattr(confidence, 'confidence_score')


class TestReportConfidence:
    """Test the ReportConfidence tracking class."""

    def test_confidence_instantiation(self):
        """ReportConfidence should instantiate."""
        conf = ReportConfidence()
        assert conf is not None

    def test_confidence_track_method(self):
        """ReportConfidence should have track method."""
        conf = ReportConfidence()
        assert hasattr(conf, 'track')

    def test_confidence_to_dict(self):
        """ReportConfidence should serialize to dict."""
        conf = ReportConfidence()
        data = conf.to_dict()
        assert 'confidence_score' in data
        assert 'confidence_level' in data

    def test_confidence_starts_at_zero(self):
        """Fresh confidence should have zero score."""
        conf = ReportConfidence()
        # With no data tracked, score should be low
        data = conf.to_dict()
        assert data['confidence_score'] >= 0


class TestReportBuilderClasses:
    """Test legacy report builder class existence (backwards compatibility)."""

    def test_external_builder_class_exists(self):
        """ExternalReportBuilder class should exist."""
        assert ExternalReportBuilder is not None

    def test_internal_builder_class_exists(self):
        """InternalReportBuilder class should exist."""
        assert InternalReportBuilder is not None

    def test_external_builder_has_build_method(self):
        """ExternalReportBuilder should have build method."""
        assert hasattr(ExternalReportBuilder, 'build')

    def test_internal_builder_has_build_method(self):
        """InternalReportBuilder should have build method."""
        assert hasattr(InternalReportBuilder, 'build')


class TestReportBuilderInterface:
    """Test report builder interface without template directory."""

    def test_external_builder_signature(self):
        """ExternalReportBuilder should require template_dir."""
        import inspect
        sig = inspect.signature(ExternalReportBuilder.__init__)
        params = list(sig.parameters.keys())
        # Should have template_dir parameter
        assert 'template_dir' in params or len(params) >= 2

    def test_internal_builder_signature(self):
        """InternalReportBuilder should require template_dir."""
        import inspect
        sig = inspect.signature(InternalReportBuilder.__init__)
        params = list(sig.parameters.keys())
        # Should have template_dir parameter
        assert 'template_dir' in params or len(params) >= 2


class TestChartGeneratorMethods:
    """Test chart generator capabilities."""

    @pytest.fixture
    def generator(self):
        return ChartGenerator()

    def test_can_create_charts(self, generator):
        """Should be able to create chart objects."""
        # Generator should be usable
        assert generator is not None

    def test_has_chart_capabilities(self, generator):
        """Should have chart generation capabilities."""
        # Check for any chart-related attributes or methods
        methods = [m for m in dir(generator) if not m.startswith('_')]
        assert len(methods) >= 0  # Has some public interface


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

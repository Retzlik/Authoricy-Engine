"""
Test Suite for Phase 6: Integration Testing

Tests the complete v5 analysis pipeline components.
Note: Full engine tests require anthropic SDK.
"""

import pytest
from typing import Dict, Any
from datetime import datetime
from unittest.mock import MagicMock

from src.agents import get_all_agents, get_core_agents, LocalSEOAgent


# Mock collected data for testing
MOCK_COLLECTED_DATA = {
    "metadata": {
        "domain": "example.se",
        "analysis_date": datetime.now().isoformat(),
        "collection_duration": 45.2,
    },
    "summary": {
        "total_organic_keywords": 1247,
        "total_organic_traffic": 8500,
        "domain_rank": 45,
        "competitor_count": 12,
        "has_local_presence": False,
    },
    "phase1_foundation": {
        "domain_overview": {
            "organic_keywords": 1247,
            "organic_traffic": 8500,
            "domain_rank": 45,
        },
        "technologies": [
            {"name": "WordPress"},
            {"name": "WooCommerce"},
        ],
        "technical_baseline": {
            "performance_score": 0.65,
            "accessibility_score": 0.82,
        },
    },
    "phase2_keywords": {
        "ranked_keywords": [
            {"keyword": "projekthantering", "position": 15, "volume": 2400},
            {"keyword": "projektverktyg", "position": 23, "volume": 1800},
        ],
    },
    "phase3_competitive": {
        "organic_competitors": [
            {"domain": "competitor1.se", "common_keywords": 450},
        ],
        "backlink_profile": {
            "referring_domains": 2340,
            "total_backlinks": 12500,
        },
    },
}

MOCK_LOCAL_DATA = {
    **MOCK_COLLECTED_DATA,
    "summary": {
        **MOCK_COLLECTED_DATA["summary"],
        "has_local_presence": True,
    },
    "phase1_foundation": {
        **MOCK_COLLECTED_DATA["phase1_foundation"],
        "gbp_info": {
            "name": "Example Business",
            "address": "Stockholm, Sweden",
            "rating": 4.5,
        },
    },
}


class TestAgentIntegration:
    """Test agent components work together."""

    def test_all_agents_instantiate(self):
        """All agents should instantiate with mock client."""
        mock_client = MagicMock()

        for AgentClass in get_all_agents():
            agent = AgentClass(mock_client)
            assert agent is not None
            assert hasattr(agent, "name")
            assert hasattr(agent, "analyze")

    def test_core_agents_count(self):
        """Should have 7 core agents."""
        assert len(get_core_agents()) == 7

    def test_total_agents_count(self):
        """Should have 9 total agents."""
        assert len(get_all_agents()) == 9


class TestLocalSEOActivation:
    """Test Local SEO agent conditional activation."""

    def test_activates_with_google_business_profile(self):
        """Should activate when google_business_profile present."""
        data_with_gbp = {
            "phase1_foundation": {
                "google_business_profile": {"name": "Test Business"},
            },
            "phase2_keywords": {"ranked_keywords": []},
        }
        assert LocalSEOAgent.should_activate(data_with_gbp)

    def test_does_not_activate_without_local(self):
        """Should not activate without local presence."""
        assert not LocalSEOAgent.should_activate(MOCK_COLLECTED_DATA)

    def test_does_not_activate_with_empty_data(self):
        """Should not activate with empty data."""
        assert not LocalSEOAgent.should_activate({})


class TestDataFlowStructure:
    """Test data structures used in the pipeline."""

    def test_collected_data_has_metadata(self):
        """Collected data should have metadata."""
        assert "metadata" in MOCK_COLLECTED_DATA
        assert "domain" in MOCK_COLLECTED_DATA["metadata"]

    def test_collected_data_has_summary(self):
        """Collected data should have summary."""
        assert "summary" in MOCK_COLLECTED_DATA
        assert "total_organic_keywords" in MOCK_COLLECTED_DATA["summary"]

    def test_collected_data_has_phases(self):
        """Collected data should have phase data."""
        assert "phase1_foundation" in MOCK_COLLECTED_DATA
        assert "phase2_keywords" in MOCK_COLLECTED_DATA
        assert "phase3_competitive" in MOCK_COLLECTED_DATA


class TestAgentAnalyzeMethod:
    """Test agent analyze methods exist and are callable."""

    def test_all_agents_have_analyze(self):
        """All agents should have analyze method."""
        mock_client = MagicMock()

        for AgentClass in get_all_agents():
            agent = AgentClass(mock_client)
            assert callable(agent.analyze), f"{AgentClass.__name__} analyze not callable"


class TestAgentNaming:
    """Test agent naming conventions."""

    def test_agent_names_are_strings(self):
        """Agent names should be strings."""
        mock_client = MagicMock()

        for AgentClass in get_all_agents():
            agent = AgentClass(mock_client)
            assert isinstance(agent.name, str)
            assert len(agent.name) > 0

    def test_agent_names_are_unique(self):
        """All agent names should be unique."""
        mock_client = MagicMock()
        names = []

        for AgentClass in get_all_agents():
            agent = AgentClass(mock_client)
            names.append(agent.name)

        assert len(names) == len(set(names)), "Agent names must be unique"


class TestPipelineComponents:
    """Test individual pipeline components."""

    def test_scoring_module_imports(self):
        """Scoring module should import correctly."""
        from src.scoring import (
            calculate_opportunity_score,
            calculate_personalized_difficulty,
            calculate_decay_score,
        )
        assert callable(calculate_opportunity_score)
        assert callable(calculate_personalized_difficulty)
        assert callable(calculate_decay_score)

    def test_quality_module_imports(self):
        """Quality module should import correctly."""
        from src.quality import (
            AgentQualityChecker,
            AntiPatternDetector,
        )
        assert AgentQualityChecker is not None
        assert AntiPatternDetector is not None

    def test_output_module_imports(self):
        """Output module should import correctly."""
        from src.output import (
            AgentOutputConverter,
            BatchOutputConverter,
        )
        assert AgentOutputConverter is not None
        assert BatchOutputConverter is not None

    def test_reporter_module_imports(self):
        """Reporter module should import correctly."""
        from src.reporter import (
            ExternalReportBuilder,
            InternalReportBuilder,
        )
        assert ExternalReportBuilder is not None
        assert InternalReportBuilder is not None


class TestEndToEndComponents:
    """Test end-to-end component integration."""

    def test_scoring_with_real_data(self):
        """Scoring should work with realistic data."""
        from src.scoring import calculate_opportunity_score

        keyword = {
            "keyword": "projekthantering software",
            "search_volume": 2400,
            "keyword_difficulty": 42,
            "position": 15,
            "intent": "commercial",
        }

        domain = {
            "domain_rank": 45,
            "categories": [{"name": "Software", "keyword_count": 100}],
        }

        result = calculate_opportunity_score(keyword, domain)
        assert result.opportunity_score >= 0
        assert result.opportunity_score <= 100

    def test_quality_checker_with_output(self):
        """Quality checker should process real output."""
        from src.quality import AgentQualityChecker

        checker = AgentQualityChecker()
        sample_output = """
        <analysis>
            <keyword>test keyword</keyword>
            <volume>1000</volume>
        </analysis>
        """

        results = checker.run_all_checks(sample_output, {})
        assert len(results) == 25

    def test_report_builder_class_exists(self):
        """Report builder class should exist and have build method."""
        from src.reporter import ExternalReportBuilder

        # Class should be importable and have build method
        assert ExternalReportBuilder is not None
        assert hasattr(ExternalReportBuilder, 'build')


class TestMockCollectedData:
    """Test the mock data structure is valid."""

    def test_mock_data_domain(self):
        """Mock data should have valid domain."""
        assert MOCK_COLLECTED_DATA["metadata"]["domain"] == "example.se"

    def test_mock_data_keywords(self):
        """Mock data should have keyword data."""
        keywords = MOCK_COLLECTED_DATA["phase2_keywords"]["ranked_keywords"]
        assert len(keywords) > 0
        assert "keyword" in keywords[0]
        assert "position" in keywords[0]

    def test_mock_local_data_has_gbp(self):
        """Mock local data should have GBP info."""
        assert "gbp_info" in MOCK_LOCAL_DATA["phase1_foundation"]
        assert "name" in MOCK_LOCAL_DATA["phase1_foundation"]["gbp_info"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

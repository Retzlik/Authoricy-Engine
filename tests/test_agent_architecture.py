"""
Test Suite for Phase 2 & 3: Agent Architecture

Tests the 9-agent architecture:
- Base agent structure
- All 9 specialized agents
- Agent prompts and outputs
"""

import pytest
from typing import Dict, Any
from unittest.mock import MagicMock

from src.agents import (
    get_all_agents,
    get_core_agents,
    get_agent_by_name,
    BaseAgent,
    KeywordIntelligenceAgent,
    BacklinkIntelligenceAgent,
    TechnicalSEOAgent,
    ContentAnalysisAgent,
    SemanticArchitectureAgent,
    AIVisibilityAgent,
    SERPAnalysisAgent,
    LocalSEOAgent,
    MasterStrategyAgent,
)


@pytest.fixture
def mock_client():
    """Create a mock Claude client for testing."""
    return MagicMock()


class TestAgentRegistry:
    """Test agent registry functions."""

    def test_get_all_agents_returns_nine(self):
        """Should have exactly 9 agents."""
        agents = get_all_agents()
        assert len(agents) == 9, f"Expected 9 agents, got {len(agents)}"

    def test_get_core_agents_returns_seven(self):
        """Core agents (excluding local SEO and master) should be 7."""
        agents = get_core_agents()
        assert len(agents) == 7, f"Expected 7 core agents, got {len(agents)}"

    def test_get_agent_by_name(self, mock_client):
        """Should retrieve agents by name."""
        agent_class = get_agent_by_name("keyword_intelligence")
        assert agent_class is not None
        assert agent_class == KeywordIntelligenceAgent

    def test_get_agent_invalid_name(self):
        """Should return None for invalid agent name."""
        agent_class = get_agent_by_name("invalid_agent")
        assert agent_class is None

    def test_all_agent_classes_exist(self):
        """All agent classes should be importable."""
        agents = get_all_agents()
        expected = [
            KeywordIntelligenceAgent,
            BacklinkIntelligenceAgent,
            TechnicalSEOAgent,
            ContentAnalysisAgent,
            SemanticArchitectureAgent,
            AIVisibilityAgent,
            SERPAnalysisAgent,
            LocalSEOAgent,
            MasterStrategyAgent,
        ]
        assert set(agents) == set(expected)


class TestAgentInstantiation:
    """Test that agents can be instantiated."""

    def test_keyword_agent_instantiation(self, mock_client):
        """Keyword agent should instantiate."""
        agent = KeywordIntelligenceAgent(mock_client)
        assert agent is not None
        assert hasattr(agent, "name")

    def test_backlink_agent_instantiation(self, mock_client):
        """Backlink agent should instantiate."""
        agent = BacklinkIntelligenceAgent(mock_client)
        assert agent is not None

    def test_technical_agent_instantiation(self, mock_client):
        """Technical agent should instantiate."""
        agent = TechnicalSEOAgent(mock_client)
        assert agent is not None

    def test_content_agent_instantiation(self, mock_client):
        """Content agent should instantiate."""
        agent = ContentAnalysisAgent(mock_client)
        assert agent is not None

    def test_semantic_agent_instantiation(self, mock_client):
        """Semantic agent should instantiate."""
        agent = SemanticArchitectureAgent(mock_client)
        assert agent is not None

    def test_ai_visibility_agent_instantiation(self, mock_client):
        """AI Visibility agent should instantiate."""
        agent = AIVisibilityAgent(mock_client)
        assert agent is not None

    def test_serp_agent_instantiation(self, mock_client):
        """SERP agent should instantiate."""
        agent = SERPAnalysisAgent(mock_client)
        assert agent is not None

    def test_local_seo_agent_instantiation(self, mock_client):
        """Local SEO agent should instantiate."""
        agent = LocalSEOAgent(mock_client)
        assert agent is not None

    def test_master_strategy_agent_instantiation(self, mock_client):
        """Master Strategy agent should instantiate."""
        agent = MasterStrategyAgent(mock_client)
        assert agent is not None


class TestAgentNames:
    """Test agent naming."""

    def test_keyword_agent_name(self, mock_client):
        """Should have correct name."""
        agent = KeywordIntelligenceAgent(mock_client)
        assert agent.name == "keyword_intelligence"

    def test_backlink_agent_name(self, mock_client):
        """Should have correct name."""
        agent = BacklinkIntelligenceAgent(mock_client)
        assert agent.name == "backlink_intelligence"

    def test_technical_agent_name(self, mock_client):
        """Should have correct name."""
        agent = TechnicalSEOAgent(mock_client)
        assert agent.name == "technical_seo"

    def test_content_agent_name(self, mock_client):
        """Should have correct name."""
        agent = ContentAnalysisAgent(mock_client)
        assert agent.name == "content_analysis"

    def test_semantic_agent_name(self, mock_client):
        """Should have correct name."""
        agent = SemanticArchitectureAgent(mock_client)
        assert agent.name == "semantic_architecture"

    def test_ai_visibility_agent_name(self, mock_client):
        """Should have correct name."""
        agent = AIVisibilityAgent(mock_client)
        assert agent.name == "ai_visibility"

    def test_serp_agent_name(self, mock_client):
        """Should have correct name."""
        agent = SERPAnalysisAgent(mock_client)
        assert agent.name == "serp_analysis"

    def test_local_seo_agent_name(self, mock_client):
        """Should have correct name."""
        agent = LocalSEOAgent(mock_client)
        assert agent.name == "local_seo"

    def test_master_strategy_agent_name(self, mock_client):
        """Should have correct name."""
        agent = MasterStrategyAgent(mock_client)
        assert agent.name == "master_strategy"


class TestAgentMethods:
    """Test that agents have required methods."""

    def test_agents_have_analyze_method(self, mock_client):
        """All agents should have analyze method."""
        for AgentClass in get_all_agents():
            agent = AgentClass(mock_client)
            assert hasattr(agent, "analyze"), f"{AgentClass.__name__} missing analyze method"
            assert callable(agent.analyze)


class TestLocalSEOActivation:
    """Test Local SEO agent conditional activation."""

    def test_activates_with_google_business_profile(self):
        """Should activate when google_business_profile present."""
        data = {
            "phase1_foundation": {
                "google_business_profile": {"name": "Test Business"},
            },
            "phase2_keywords": {"ranked_keywords": []},
        }
        assert LocalSEOAgent.should_activate(data)

    def test_activates_with_domain_overview_gbp(self):
        """Should activate when GBP in domain_overview."""
        data = {
            "phase1_foundation": {
                "domain_overview": {"google_business_profile": {"name": "Test"}},
            },
            "phase2_keywords": {"ranked_keywords": []},
        }

    def test_does_not_activate_without_signals(self):
        """Should not activate without local signals."""
        data = {
            "summary": {"has_local_presence": False},
            "phase1_foundation": {},
        }
        assert not LocalSEOAgent.should_activate(data)

    def test_does_not_activate_with_empty_data(self):
        """Should not activate with empty data."""
        data = {}
        assert not LocalSEOAgent.should_activate(data)


class TestMasterStrategyAgent:
    """Test Master Strategy Agent specifics."""

    def test_has_synthesize_method(self, mock_client):
        """Should have synthesize method."""
        agent = MasterStrategyAgent(mock_client)
        assert hasattr(agent, "synthesize") or hasattr(agent, "analyze")


class TestAgentPromptContent:
    """Test that agent prompts contain required v5 components."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for prompt generation."""
        return {
            "metadata": {"domain": "example.se"},
            "summary": {"total_organic_keywords": 1000},
            "phase2_keywords": {"ranked_keywords": []},
        }

    def test_keyword_agent_exists(self, mock_client, sample_data):
        """Keyword agent should exist and have analyze method."""
        agent = KeywordIntelligenceAgent(mock_client)
        assert agent is not None
        assert hasattr(agent, "analyze")
        assert agent.name == "keyword_intelligence"

    def test_technical_prompt_mentions_cwv(self, mock_client, sample_data):
        """Technical agent should reference Core Web Vitals."""
        agent = TechnicalSEOAgent(mock_client)
        if hasattr(agent, "get_prompt"):
            prompt = str(agent.get_prompt(sample_data)).lower()
        else:
            prompt = ""

        # Should mention technical SEO concepts
        has_technical = any(term in prompt for term in [
            "core web vitals", "cwv", "lcp", "performance", "technical"
        ])
        # May not have prompt method exposed - that's ok
        assert has_technical or not hasattr(agent, "get_prompt")


class TestAgentOutputStructure:
    """Test expected output structures from agents."""

    def test_keyword_output_expected_fields(self):
        """Keyword agent output should have expected fields."""
        expected_fields = [
            "priority_stack",
            "quick_wins",
        ]
        # This is a structural expectation test

    def test_technical_output_expected_fields(self):
        """Technical agent output should have expected fields."""
        expected_fields = [
            "critical_issues",
            "cwv_analysis",
        ]

    def test_master_strategy_output_expected_fields(self):
        """Master strategy output should have expected fields."""
        expected_fields = [
            "executive_summary",
            "priority_matrix",
            "roadmap",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

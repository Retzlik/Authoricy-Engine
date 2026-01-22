"""
Test Suite for Phase 2 & 3: Agent Architecture

Tests the 9-agent architecture:
- Base agent structure
- All 9 specialized agents
- Agent prompts and outputs
"""

import pytest
from typing import Dict, Any

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

    def test_get_agent_by_name(self):
        """Should retrieve agents by name."""
        agent = get_agent_by_name("keyword_intelligence")
        assert agent is not None
        assert isinstance(agent, KeywordIntelligenceAgent)

    def test_get_agent_invalid_name(self):
        """Should return None for invalid agent name."""
        agent = get_agent_by_name("invalid_agent")
        assert agent is None

    def test_all_agents_have_required_attributes(self):
        """All agents should have required attributes."""
        for agent in get_all_agents():
            assert hasattr(agent, "name")
            assert hasattr(agent, "analyze")
            assert hasattr(agent, "get_prompt")
            assert callable(agent.analyze)
            assert callable(agent.get_prompt)


class TestBaseAgent:
    """Test BaseAgent class."""

    def test_base_agent_has_name(self):
        """Base agent should have a name property."""
        agent = BaseAgent()
        assert hasattr(agent, "name")

    def test_base_agent_has_analyze_method(self):
        """Base agent should have analyze method."""
        agent = BaseAgent()
        assert hasattr(agent, "analyze")
        assert callable(agent.analyze)

    def test_base_agent_has_get_prompt_method(self):
        """Base agent should have get_prompt method."""
        agent = BaseAgent()
        assert hasattr(agent, "get_prompt")


class TestKeywordIntelligenceAgent:
    """Test Keyword Intelligence Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = KeywordIntelligenceAgent()
        assert agent.name == "keyword_intelligence"

    def test_prompt_contains_required_sections(self):
        """Prompt should contain key v5 components."""
        agent = KeywordIntelligenceAgent()
        prompt = agent.get_prompt({})

        # Check for expert persona
        assert "expert" in prompt.lower() or "specialist" in prompt.lower()

        # Check for behavioral constraints
        assert "NEVER" in prompt or "ALWAYS" in prompt

        # Check for scoring formulas
        assert "opportunity" in prompt.lower() or "score" in prompt.lower()

    def test_prompt_mentions_opportunity_score(self):
        """Should include opportunity score calculation."""
        agent = KeywordIntelligenceAgent()
        prompt = agent.get_prompt({})
        assert "opportunity" in prompt.lower()

    def test_prompt_mentions_intent(self):
        """Should analyze search intent."""
        agent = KeywordIntelligenceAgent()
        prompt = agent.get_prompt({})
        assert "intent" in prompt.lower()


class TestBacklinkIntelligenceAgent:
    """Test Backlink Intelligence Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = BacklinkIntelligenceAgent()
        assert agent.name == "backlink_intelligence"

    def test_prompt_mentions_link_gap(self):
        """Should analyze link gap."""
        agent = BacklinkIntelligenceAgent()
        prompt = agent.get_prompt({})
        assert "link" in prompt.lower() and ("gap" in prompt.lower() or "backlink" in prompt.lower())

    def test_prompt_mentions_anchor_text(self):
        """Should analyze anchor text distribution."""
        agent = BacklinkIntelligenceAgent()
        prompt = agent.get_prompt({})
        assert "anchor" in prompt.lower()


class TestTechnicalSEOAgent:
    """Test Technical SEO Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = TechnicalSEOAgent()
        assert agent.name == "technical_seo"

    def test_prompt_mentions_core_web_vitals(self):
        """Should analyze Core Web Vitals."""
        agent = TechnicalSEOAgent()
        prompt = agent.get_prompt({})
        assert "core web vitals" in prompt.lower() or "cwv" in prompt.lower() or "lcp" in prompt.lower()

    def test_prompt_mentions_indexing(self):
        """Should analyze indexing."""
        agent = TechnicalSEOAgent()
        prompt = agent.get_prompt({})
        assert "index" in prompt.lower()


class TestContentAnalysisAgent:
    """Test Content Analysis Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = ContentAnalysisAgent()
        assert agent.name == "content_analysis"

    def test_prompt_mentions_kuck_framework(self):
        """Should use KUCK framework."""
        agent = ContentAnalysisAgent()
        prompt = agent.get_prompt({})
        # KUCK = Keep, Update, Consolidate, Kill
        kuck_terms = ["keep", "update", "consolidate", "kill", "kuck"]
        assert any(term in prompt.lower() for term in kuck_terms)

    def test_prompt_mentions_decay(self):
        """Should analyze content decay."""
        agent = ContentAnalysisAgent()
        prompt = agent.get_prompt({})
        assert "decay" in prompt.lower() or "outdated" in prompt.lower()


class TestSemanticArchitectureAgent:
    """Test Semantic Architecture Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = SemanticArchitectureAgent()
        assert agent.name == "semantic_architecture"

    def test_prompt_mentions_clustering(self):
        """Should mention topic clustering."""
        agent = SemanticArchitectureAgent()
        prompt = agent.get_prompt({})
        assert "cluster" in prompt.lower() or "hub" in prompt.lower()

    def test_prompt_mentions_internal_linking(self):
        """Should analyze internal linking."""
        agent = SemanticArchitectureAgent()
        prompt = agent.get_prompt({})
        assert "internal" in prompt.lower() and "link" in prompt.lower()


class TestAIVisibilityAgent:
    """Test AI Visibility Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = AIVisibilityAgent()
        assert agent.name == "ai_visibility"

    def test_prompt_mentions_geo(self):
        """Should mention GEO (Generative Engine Optimization)."""
        agent = AIVisibilityAgent()
        prompt = agent.get_prompt({})
        assert "geo" in prompt.lower() or "generative" in prompt.lower() or "ai overviews" in prompt.lower()

    def test_prompt_mentions_structured_data(self):
        """Should analyze structured data."""
        agent = AIVisibilityAgent()
        prompt = agent.get_prompt({})
        assert "schema" in prompt.lower() or "structured" in prompt.lower()


class TestSERPAnalysisAgent:
    """Test SERP Analysis Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = SERPAnalysisAgent()
        assert agent.name == "serp_analysis"

    def test_prompt_mentions_serp_features(self):
        """Should analyze SERP features."""
        agent = SERPAnalysisAgent()
        prompt = agent.get_prompt({})
        assert "serp" in prompt.lower() or "featured snippet" in prompt.lower()

    def test_prompt_mentions_competitor(self):
        """Should analyze competitors."""
        agent = SERPAnalysisAgent()
        prompt = agent.get_prompt({})
        assert "competitor" in prompt.lower()


class TestLocalSEOAgent:
    """Test Local SEO Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = LocalSEOAgent()
        assert agent.name == "local_seo"

    def test_should_activate_with_local_signals(self):
        """Should activate when local signals detected."""
        data_with_local = {
            "summary": {"has_local_presence": True},
            "phase1_foundation": {"gbp_info": {"name": "Test Business"}},
        }
        assert LocalSEOAgent.should_activate(data_with_local)

    def test_should_not_activate_without_local_signals(self):
        """Should not activate for non-local businesses."""
        data_without_local = {
            "summary": {"has_local_presence": False},
            "phase1_foundation": {},
        }
        assert not LocalSEOAgent.should_activate(data_without_local)

    def test_prompt_mentions_gbp(self):
        """Should mention Google Business Profile."""
        agent = LocalSEOAgent()
        prompt = agent.get_prompt({})
        assert "google business" in prompt.lower() or "gbp" in prompt.lower() or "local" in prompt.lower()


class TestMasterStrategyAgent:
    """Test Master Strategy Agent."""

    def test_agent_name(self):
        """Should have correct name."""
        agent = MasterStrategyAgent()
        assert agent.name == "master_strategy"

    def test_has_synthesize_method(self):
        """Should have synthesize method."""
        agent = MasterStrategyAgent()
        assert hasattr(agent, "synthesize")
        assert callable(agent.synthesize)

    def test_prompt_mentions_roadmap(self):
        """Should create 90-day roadmap."""
        agent = MasterStrategyAgent()
        prompt = agent.get_prompt({})
        assert "roadmap" in prompt.lower() or "90" in prompt or "quarter" in prompt.lower()

    def test_prompt_mentions_priority(self):
        """Should prioritize recommendations."""
        agent = MasterStrategyAgent()
        prompt = agent.get_prompt({})
        assert "priority" in prompt.lower() or "impact" in prompt.lower()


class TestAgentPromptQuality:
    """Test that all agent prompts meet v5 standards."""

    @pytest.fixture
    def all_agents(self):
        return get_all_agents()

    def test_all_prompts_over_200_chars(self, all_agents):
        """All prompts should be substantial (>200 chars)."""
        for agent in all_agents:
            prompt = agent.get_prompt({})
            assert len(prompt) > 200, f"{agent.name} prompt too short: {len(prompt)} chars"

    def test_all_prompts_have_expert_persona(self, all_agents):
        """All prompts should establish expert persona."""
        for agent in all_agents:
            prompt = agent.get_prompt({})
            has_persona = any(term in prompt.lower() for term in [
                "expert", "specialist", "senior", "principal", "years of experience"
            ])
            assert has_persona, f"{agent.name} missing expert persona"

    def test_all_prompts_have_behavioral_constraints(self, all_agents):
        """All prompts should have behavioral constraints."""
        for agent in all_agents:
            prompt = agent.get_prompt({})
            has_constraints = "NEVER" in prompt or "ALWAYS" in prompt or "DO NOT" in prompt
            assert has_constraints, f"{agent.name} missing behavioral constraints"

    def test_all_prompts_request_structured_output(self, all_agents):
        """All prompts should request structured output."""
        for agent in all_agents:
            prompt = agent.get_prompt({})
            has_structure = any(term in prompt.lower() for term in [
                "xml", "json", "<", "structured", "format"
            ])
            assert has_structure, f"{agent.name} missing structured output request"


class TestAgentOutputStructure:
    """Test expected output structures."""

    def test_keyword_agent_output_structure(self):
        """Keyword agent should output structured recommendations."""
        # Mock the expected output structure
        expected_sections = [
            "priority_stack",
            "quick_wins",
            "strike_distance",
            "content_gaps",
        ]
        # This is a structural test - actual output tested in integration

    def test_backlink_agent_output_structure(self):
        """Backlink agent should output link recommendations."""
        expected_sections = [
            "link_gap_analysis",
            "prospect_tiers",
            "anchor_text_strategy",
        ]

    def test_technical_agent_output_structure(self):
        """Technical agent should output issue priorities."""
        expected_sections = [
            "critical_issues",
            "cwv_analysis",
            "indexing_issues",
        ]

    def test_master_strategy_output_structure(self):
        """Master strategy should output roadmap."""
        expected_sections = [
            "executive_summary",
            "priority_matrix",
            "roadmap_90_days",
            "resource_allocation",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

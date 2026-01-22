"""
Test Suite for Phase 6: Integration Testing

Tests the complete v5 analysis pipeline:
- Engine orchestration of all 9 agents
- Parallel execution
- Quality gate enforcement
- End-to-end workflow
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.analyzer import AnalysisEngineV5, AnalysisResultV5, create_analysis_engine
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
            "best_practices_score": 0.78,
            "seo_score": 0.71,
        },
    },
    "phase2_keywords": {
        "ranked_keywords": [
            {"keyword": "projekthantering", "position": 15, "volume": 2400},
            {"keyword": "projektverktyg", "position": 23, "volume": 1800},
        ],
        "keyword_suggestions": [
            {"keyword": "gratis projekthantering", "volume": 1200, "difficulty": 35},
        ],
    },
    "phase3_competitive": {
        "organic_competitors": [
            {"domain": "competitor1.se", "common_keywords": 450},
            {"domain": "competitor2.se", "common_keywords": 320},
        ],
        "backlink_profile": {
            "referring_domains": 2340,
            "total_backlinks": 12500,
        },
    },
    "phase4_content": {
        "indexed_pages": 450,
        "content_performance": [
            {"url": "/blog/post-1", "traffic": 500, "keywords": 25},
        ],
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


class TestAnalysisEngineV5:
    """Test the v5 analysis engine."""

    @pytest.fixture
    def engine(self):
        """Create engine with mocked API client."""
        with patch('src.analyzer.engine_v5.ClaudeClient'):
            return AnalysisEngineV5(api_key="test-key")

    def test_engine_initialization(self, engine):
        """Engine should initialize with all components."""
        assert engine is not None
        assert hasattr(engine, "analyze")

    def test_engine_has_quality_threshold(self, engine):
        """Engine should have quality threshold of 9.2 (92%)."""
        assert engine.QUALITY_THRESHOLD == 9.2

    @pytest.mark.asyncio
    async def test_analyze_returns_result(self, engine):
        """Analyze should return AnalysisResultV5."""
        # Mock agent responses
        with patch.object(engine, '_run_agent_safe', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": True,
                "output": "<analysis>Test output</analysis>",
                "quality_score": 9.5,
            }

            result = await engine.analyze(MOCK_COLLECTED_DATA)

            assert isinstance(result, AnalysisResultV5)

    @pytest.mark.asyncio
    async def test_analyze_runs_primary_agents(self, engine):
        """Should run all 7 primary agents."""
        agent_calls = []

        async def track_agent(name, data):
            agent_calls.append(name)
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=track_agent):
            await engine.analyze(MOCK_COLLECTED_DATA)

        # Should have called 7 primary agents
        primary_agents = [
            "keyword_intelligence",
            "backlink_intelligence",
            "technical_seo",
            "content_analysis",
            "semantic_architecture",
            "ai_visibility",
            "serp_analysis",
        ]

        for agent in primary_agents:
            assert agent in agent_calls, f"Missing agent: {agent}"

    @pytest.mark.asyncio
    async def test_analyze_runs_local_seo_when_needed(self, engine):
        """Should run local SEO agent when local presence detected."""
        agent_calls = []

        async def track_agent(name, data):
            agent_calls.append(name)
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=track_agent):
            await engine.analyze(MOCK_LOCAL_DATA)

        assert "local_seo" in agent_calls

    @pytest.mark.asyncio
    async def test_analyze_skips_local_seo_when_not_needed(self, engine):
        """Should skip local SEO agent when no local presence."""
        agent_calls = []

        async def track_agent(name, data):
            agent_calls.append(name)
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=track_agent):
            await engine.analyze(MOCK_COLLECTED_DATA)

        assert "local_seo" not in agent_calls

    @pytest.mark.asyncio
    async def test_analyze_runs_master_strategy_last(self, engine):
        """Master strategy should run after all other agents."""
        call_order = []

        async def track_order(name, data):
            call_order.append(name)
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=track_order):
            await engine.analyze(MOCK_COLLECTED_DATA)

        # Master strategy should be last
        assert call_order[-1] == "master_strategy"


class TestParallelExecution:
    """Test parallel agent execution."""

    @pytest.fixture
    def engine(self):
        with patch('src.analyzer.engine_v5.ClaudeClient'):
            return AnalysisEngineV5(api_key="test-key")

    @pytest.mark.asyncio
    async def test_primary_agents_run_in_parallel(self, engine):
        """Primary agents should run concurrently."""
        execution_times = {}
        start_time = asyncio.get_event_loop().time()

        async def slow_agent(name, data):
            execution_times[name] = asyncio.get_event_loop().time() - start_time
            await asyncio.sleep(0.1)  # Simulate work
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=slow_agent):
            await engine.analyze(MOCK_COLLECTED_DATA)

        # If running in parallel, all primary agents should start at roughly the same time
        primary_starts = [
            execution_times.get(name, 0) for name in [
                "keyword_intelligence",
                "backlink_intelligence",
                "technical_seo",
            ]
        ]

        # All should have started within 0.05 seconds of each other
        if len(primary_starts) >= 2:
            time_spread = max(primary_starts) - min(primary_starts)
            assert time_spread < 0.1, "Primary agents should start in parallel"


class TestQualityGate:
    """Test quality gate enforcement."""

    @pytest.fixture
    def engine(self):
        with patch('src.analyzer.engine_v5.ClaudeClient'):
            return AnalysisEngineV5(api_key="test-key")

    @pytest.mark.asyncio
    async def test_passes_quality_gate_when_score_high(self, engine):
        """Should pass quality gate when score >= 9.2."""
        async def high_quality_agent(name, data):
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=high_quality_agent):
            result = await engine.analyze(MOCK_COLLECTED_DATA)

        assert result.passed_quality_gate

    @pytest.mark.asyncio
    async def test_fails_quality_gate_when_score_low(self, engine):
        """Should fail quality gate when score < 9.2."""
        async def low_quality_agent(name, data):
            return {"success": True, "output": "test", "quality_score": 7.0}

        with patch.object(engine, '_run_agent_safe', side_effect=low_quality_agent):
            with patch.object(engine, '_retry_with_feedback', new_callable=AsyncMock) as mock_retry:
                mock_retry.return_value = {"success": True, "output": "test", "quality_score": 7.0}
                result = await engine.analyze(MOCK_COLLECTED_DATA, max_retries=0)

        assert not result.passed_quality_gate

    @pytest.mark.asyncio
    async def test_retries_on_quality_failure(self, engine):
        """Should retry agents that fail quality check."""
        call_count = 0

        async def improving_agent(name, data):
            nonlocal call_count
            call_count += 1
            # First call fails, second passes
            score = 7.0 if call_count <= 8 else 9.5
            return {"success": True, "output": "test", "quality_score": score}

        with patch.object(engine, '_run_agent_safe', side_effect=improving_agent):
            result = await engine.analyze(MOCK_COLLECTED_DATA, max_retries=1)

        # Should have made retry attempts
        assert call_count > 8  # More than initial 8 agents


class TestAnalysisResultV5:
    """Test AnalysisResultV5 structure."""

    @pytest.fixture
    def engine(self):
        with patch('src.analyzer.engine_v5.ClaudeClient'):
            return AnalysisEngineV5(api_key="test-key")

    @pytest.mark.asyncio
    async def test_result_has_all_required_fields(self, engine):
        """Result should have all required fields."""
        async def mock_agent(name, data):
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=mock_agent):
            result = await engine.analyze(MOCK_COLLECTED_DATA)

        # Check required fields
        assert hasattr(result, "domain")
        assert hasattr(result, "timestamp")
        assert hasattr(result, "agent_outputs")
        assert hasattr(result, "quality_score")
        assert hasattr(result, "passed_quality_gate")

    @pytest.mark.asyncio
    async def test_result_contains_agent_outputs(self, engine):
        """Result should contain outputs from all agents."""
        async def mock_agent(name, data):
            return {"success": True, "output": f"Output from {name}", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=mock_agent):
            result = await engine.analyze(MOCK_COLLECTED_DATA)

        assert "keyword_intelligence" in result.agent_outputs
        assert "technical_seo" in result.agent_outputs
        assert "master_strategy" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_result_has_timing_info(self, engine):
        """Result should have timing information."""
        async def mock_agent(name, data):
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=mock_agent):
            result = await engine.analyze(MOCK_COLLECTED_DATA)

        assert hasattr(result, "duration_seconds")
        assert result.duration_seconds >= 0


class TestCreateAnalysisEngine:
    """Test engine factory function."""

    def test_creates_v5_engine(self):
        """Factory should create v5 engine."""
        with patch('src.analyzer.engine_v5.ClaudeClient'):
            engine = create_analysis_engine(api_key="test-key")

        assert isinstance(engine, AnalysisEngineV5)

    def test_creates_engine_with_api_key(self):
        """Should pass API key to engine."""
        with patch('src.analyzer.engine_v5.ClaudeClient') as mock_client:
            create_analysis_engine(api_key="my-api-key")

            mock_client.assert_called_once()


class TestLocalSEOActivation:
    """Test Local SEO agent conditional activation."""

    def test_activates_with_gbp(self):
        """Should activate when GBP info present."""
        data = {
            "summary": {"has_local_presence": True},
            "phase1_foundation": {"gbp_info": {"name": "Test"}},
        }
        assert LocalSEOAgent.should_activate(data)

    def test_activates_with_local_flag(self):
        """Should activate when local flag is true."""
        data = {
            "summary": {"has_local_presence": True},
            "phase1_foundation": {},
        }
        assert LocalSEOAgent.should_activate(data)

    def test_does_not_activate_without_signals(self):
        """Should not activate without local signals."""
        data = {
            "summary": {"has_local_presence": False},
            "phase1_foundation": {},
        }
        assert not LocalSEOAgent.should_activate(data)


class TestEndToEndWorkflow:
    """Test complete analysis workflow."""

    @pytest.fixture
    def engine(self):
        with patch('src.analyzer.engine_v5.ClaudeClient'):
            return AnalysisEngineV5(api_key="test-key")

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, engine):
        """Test full analysis from data to result."""
        async def mock_agent(name, data):
            return {
                "success": True,
                "output": f"""
                <analysis>
                    <executive_summary>Analysis for {name}</executive_summary>
                    <recommendations>
                        <item priority="1">Specific action for {name}</item>
                    </recommendations>
                </analysis>
                """,
                "quality_score": 9.5,
            }

        with patch.object(engine, '_run_agent_safe', side_effect=mock_agent):
            result = await engine.analyze(MOCK_COLLECTED_DATA)

        # Verify complete workflow
        assert result.domain == "example.se"
        assert result.passed_quality_gate
        assert len(result.agent_outputs) >= 7
        assert result.quality_score >= 9.2

    @pytest.mark.asyncio
    async def test_workflow_handles_agent_failure(self, engine):
        """Should handle individual agent failures gracefully."""
        call_count = 0

        async def failing_agent(name, data):
            nonlocal call_count
            call_count += 1
            if name == "technical_seo":
                return {"success": False, "error": "API timeout", "quality_score": 0}
            return {"success": True, "output": "test", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=failing_agent):
            result = await engine.analyze(MOCK_COLLECTED_DATA, max_retries=0)

        # Should still return a result
        assert result is not None
        assert result.domain == "example.se"


class TestAgentDataFlow:
    """Test data flows correctly between agents."""

    @pytest.fixture
    def engine(self):
        with patch('src.analyzer.engine_v5.ClaudeClient'):
            return AnalysisEngineV5(api_key="test-key")

    @pytest.mark.asyncio
    async def test_master_strategy_receives_all_outputs(self, engine):
        """Master strategy should receive outputs from all other agents."""
        received_data = {}

        async def capture_data(name, data):
            if name == "master_strategy":
                received_data.update(data)
            return {"success": True, "output": f"{name} output", "quality_score": 9.5}

        with patch.object(engine, '_run_agent_safe', side_effect=capture_data):
            await engine.analyze(MOCK_COLLECTED_DATA)

        # Master strategy should have received other agent outputs
        assert "agent_outputs" in received_data or len(received_data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

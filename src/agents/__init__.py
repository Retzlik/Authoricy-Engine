"""
Analysis Agents Module

9 specialized agents for comprehensive SEO analysis:

1. KeywordIntelligenceAgent - Keyword portfolio and opportunity analysis
2. BacklinkIntelligenceAgent - Link profile and building strategy
3. TechnicalSEOAgent - Technical audit and Core Web Vitals
4. ContentAnalysisAgent - Content inventory and decay detection
5. SemanticArchitectureAgent - Topical authority and site structure
6. AIVisibilityAgent - AI Overview presence and GEO optimization
7. SERPAnalysisAgent - SERP features and content formats
8. LocalSEOAgent - Local SEO (conditional)
9. MasterStrategyAgent - Synthesizes all outputs

Usage:
    from src.agents import KeywordIntelligenceAgent, MasterStrategyAgent

    agent = KeywordIntelligenceAgent(claude_client)
    result = await agent.analyze(collected_data)
"""

from .base import (
    BaseAgent,
    AgentOutput,
    Finding,
    Recommendation,
)

from .keyword_intelligence import KeywordIntelligenceAgent
from .backlink_intelligence import BacklinkIntelligenceAgent
from .technical_seo import TechnicalSEOAgent
from .content_analysis import ContentAnalysisAgent
from .semantic_architecture import SemanticArchitectureAgent
from .ai_visibility import AIVisibilityAgent
from .serp_analysis import SERPAnalysisAgent
from .local_seo import LocalSEOAgent
from .master_strategy import MasterStrategyAgent

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentOutput",
    "Finding",
    "Recommendation",
    # Core Agents
    "KeywordIntelligenceAgent",
    "BacklinkIntelligenceAgent",
    "TechnicalSEOAgent",
    "ContentAnalysisAgent",
    "SemanticArchitectureAgent",
    "AIVisibilityAgent",
    "SERPAnalysisAgent",
    # Conditional Agent
    "LocalSEOAgent",
    # Synthesis Agent
    "MasterStrategyAgent",
]


def get_all_agents():
    """Get list of all available agent classes."""
    return [
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


def get_core_agents():
    """Get list of core agents (excludes conditional and synthesis)."""
    return [
        KeywordIntelligenceAgent,
        BacklinkIntelligenceAgent,
        TechnicalSEOAgent,
        ContentAnalysisAgent,
        SemanticArchitectureAgent,
        AIVisibilityAgent,
        SERPAnalysisAgent,
    ]


def get_agent_by_name(name: str):
    """Get agent class by name."""
    agents = {
        "keyword_intelligence": KeywordIntelligenceAgent,
        "backlink_intelligence": BacklinkIntelligenceAgent,
        "technical_seo": TechnicalSEOAgent,
        "content_analysis": ContentAnalysisAgent,
        "semantic_architecture": SemanticArchitectureAgent,
        "ai_visibility": AIVisibilityAgent,
        "serp_analysis": SERPAnalysisAgent,
        "local_seo": LocalSEOAgent,
        "master_strategy": MasterStrategyAgent,
    }
    return agents.get(name)

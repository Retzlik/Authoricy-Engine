"""
Context Intelligence Package

Provides pre-collection intelligence gathering for SEO analysis:
- Website analysis to understand the business
- Competitor discovery and classification
- Market validation and opportunity discovery
- Business profiling and goal alignment

Usage:
    from src.context import gather_context_intelligence, PrimaryGoal

    result = await gather_context_intelligence(
        domain="example.com",
        primary_market="se",
        primary_goal=PrimaryGoal.LEADS,
        known_competitors=["competitor1.com", "competitor2.com"],
    )

    # Use result.collection_config for focused data collection
    # Use result.to_analysis_context() for enhanced analysis prompts
"""

# Core models
from .models import (
    # Enums
    PrimaryGoal,
    BusinessModel,
    CompanyStage,
    CompetitorType,
    ThreatLevel,
    BuyerJourneyType,
    DiscoveryMethod,
    ValidationStatus,
    # Data classes
    DetectedOffering,
    WebsiteAnalysis,
    CompetitorEvidence,
    ValidatedCompetitor,
    CompetitorValidation,
    MarketOpportunity,
    MarketValidation,
    GoalValidation,
    BuyerJourney,
    SuccessDefinition,
    BusinessContext,
    IntelligentCollectionConfig,
    ContextIntelligenceResult,
)

# Agents
from .website_analyzer import WebsiteAnalyzer, analyze_website
from .competitor_discovery import CompetitorDiscovery, discover_competitors
from .market_validator import MarketValidator, validate_market
from .business_profiler import BusinessProfiler, profile_business

# Orchestrator
from .orchestrator import (
    ContextIntelligenceOrchestrator,
    ContextIntelligenceRequest,
    gather_context_intelligence,
)


__all__ = [
    # Enums
    "PrimaryGoal",
    "BusinessModel",
    "CompanyStage",
    "CompetitorType",
    "ThreatLevel",
    "BuyerJourneyType",
    "DiscoveryMethod",
    "ValidationStatus",
    # Data classes
    "DetectedOffering",
    "WebsiteAnalysis",
    "CompetitorEvidence",
    "ValidatedCompetitor",
    "CompetitorValidation",
    "MarketOpportunity",
    "MarketValidation",
    "GoalValidation",
    "BuyerJourney",
    "SuccessDefinition",
    "BusinessContext",
    "IntelligentCollectionConfig",
    "ContextIntelligenceResult",
    # Agents
    "WebsiteAnalyzer",
    "analyze_website",
    "CompetitorDiscovery",
    "discover_competitors",
    "MarketValidator",
    "validate_market",
    "BusinessProfiler",
    "profile_business",
    # Orchestrator
    "ContextIntelligenceOrchestrator",
    "ContextIntelligenceRequest",
    "gather_context_intelligence",
]

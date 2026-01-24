"""
Context Intelligence Package

Provides pre-collection intelligence gathering for SEO analysis:
- Market detection from website signals (NEW - Phase 1)
- Website analysis to understand the business
- Competitor discovery and classification
- Market validation and opportunity discovery
- Business profiling and goal alignment

Usage:
    from src.context import detect_market, gather_context_intelligence, PrimaryGoal

    # Phase 1: Detect market from website signals
    detection = await detect_market("example.com")
    print(f"Detected: {detection.primary.name} ({detection.primary.confidence:.0%})")

    # Phase 2+: Full context intelligence
    result = await gather_context_intelligence(
        domain="example.com",
        primary_market=detection.primary.code,  # Use detected market
        primary_goal=PrimaryGoal.LEADS,
        known_competitors=["competitor1.com", "competitor2.com"],
    )

    # Use result.collection_config for focused data collection
    # Use result.to_analysis_context() for enhanced analysis prompts
"""

# Market detection (Phase 1 - NEW)
from .market_detection import (
    MarketDetector,
    MarketSignal,
    SignalKind,
    DetectedMarket,
    MarketDetectionResult,
    detect_market,
    MARKET_CONFIG,
    SIGNAL_WEIGHTS,
)

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
    # Market detection (Phase 1 - NEW)
    "MarketDetector",
    "MarketSignal",
    "SignalKind",
    "DetectedMarket",
    "MarketDetectionResult",
    "detect_market",
    "MARKET_CONFIG",
    "SIGNAL_WEIGHTS",
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

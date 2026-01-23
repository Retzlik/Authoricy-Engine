"""
Tests for Context Intelligence Layer

Tests the pre-collection intelligence gathering:
- Website analysis
- Competitor discovery and classification
- Market validation
- Business profiling
- Orchestration
"""

import pytest
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

# Import models
from src.context.models import (
    PrimaryGoal,
    BusinessModel,
    CompanyStage,
    CompetitorType,
    ThreatLevel,
    BuyerJourneyType,
    DiscoveryMethod,
    ValidationStatus,
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


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestPrimaryGoalEnum:
    """Test PrimaryGoal enum."""

    def test_traffic_goal(self):
        assert PrimaryGoal.TRAFFIC.value == "traffic"

    def test_leads_goal(self):
        assert PrimaryGoal.LEADS.value == "leads"

    def test_authority_goal(self):
        assert PrimaryGoal.AUTHORITY.value == "authority"

    def test_balanced_goal(self):
        assert PrimaryGoal.BALANCED.value == "balanced"

    def test_goal_from_string(self):
        assert PrimaryGoal("traffic") == PrimaryGoal.TRAFFIC
        assert PrimaryGoal("leads") == PrimaryGoal.LEADS


class TestBusinessModelEnum:
    """Test BusinessModel enum."""

    def test_b2b_saas(self):
        assert BusinessModel.B2B_SAAS.value == "b2b_saas"

    def test_ecommerce(self):
        assert BusinessModel.B2C_ECOMMERCE.value == "b2c_ecommerce"

    def test_publisher(self):
        assert BusinessModel.PUBLISHER.value == "publisher"

    def test_local_service(self):
        assert BusinessModel.LOCAL_SERVICE.value == "local_service"


class TestCompetitorTypeEnum:
    """Test CompetitorType enum."""

    def test_direct_competitor(self):
        assert CompetitorType.DIRECT.value == "direct"

    def test_seo_competitor(self):
        assert CompetitorType.SEO.value == "seo"

    def test_content_competitor(self):
        assert CompetitorType.CONTENT.value == "content"

    def test_emerging_competitor(self):
        assert CompetitorType.EMERGING.value == "emerging"

    def test_not_competitor(self):
        assert CompetitorType.NOT_COMPETITOR.value == "not_competitor"


class TestWebsiteAnalysis:
    """Test WebsiteAnalysis dataclass."""

    def test_default_values(self):
        analysis = WebsiteAnalysis(domain="example.com")
        assert analysis.domain == "example.com"
        assert analysis.business_model == BusinessModel.UNKNOWN
        assert analysis.company_stage == CompanyStage.UNKNOWN
        assert analysis.offerings == []
        assert analysis.has_blog is False
        assert analysis.has_ecommerce is False

    def test_with_values(self):
        analysis = WebsiteAnalysis(
            domain="saas.com",
            business_model=BusinessModel.B2B_SAAS,
            company_stage=CompanyStage.GROWTH,
            has_demo_form=True,
            has_pricing_page=True,
            analysis_confidence=0.85,
        )
        assert analysis.business_model == BusinessModel.B2B_SAAS
        assert analysis.has_demo_form is True
        assert analysis.analysis_confidence == 0.85


class TestValidatedCompetitor:
    """Test ValidatedCompetitor dataclass."""

    def test_default_values(self):
        comp = ValidatedCompetitor(domain="competitor.com")
        assert comp.domain == "competitor.com"
        assert comp.competitor_type == CompetitorType.DIRECT
        assert comp.threat_level == ThreatLevel.MEDIUM
        assert comp.user_provided is False

    def test_with_classification(self):
        comp = ValidatedCompetitor(
            domain="bigplayer.com",
            competitor_type=CompetitorType.ASPIRATIONAL,
            threat_level=ThreatLevel.LOW,
            discovery_method=DiscoveryMethod.SERP_ANALYSIS,
            validation_status=ValidationStatus.CONFIRMED,
            confidence_score=0.9,
        )
        assert comp.competitor_type == CompetitorType.ASPIRATIONAL
        assert comp.validation_status == ValidationStatus.CONFIRMED


class TestCompetitorValidation:
    """Test CompetitorValidation dataclass."""

    def test_empty_validation(self):
        validation = CompetitorValidation()
        assert validation.user_provided == []
        assert validation.confirmed == []
        assert validation.discovered == []
        assert validation.total_direct_competitors == 0

    def test_with_competitors(self):
        comp1 = ValidatedCompetitor(domain="comp1.com", competitor_type=CompetitorType.DIRECT)
        comp2 = ValidatedCompetitor(domain="comp2.com", competitor_type=CompetitorType.SEO)

        validation = CompetitorValidation(
            user_provided=["comp1.com"],
            confirmed=[comp1],
            discovered=[comp2],
            total_direct_competitors=1,
            total_seo_competitors=1,
        )
        assert len(validation.confirmed) == 1
        assert validation.total_direct_competitors == 1


class TestMarketOpportunity:
    """Test MarketOpportunity dataclass."""

    def test_default_values(self):
        market = MarketOpportunity(region="se", language="sv")
        assert market.region == "se"
        assert market.language == "sv"
        assert market.opportunity_score == 0.0
        assert market.is_primary is False

    def test_high_opportunity(self):
        market = MarketOpportunity(
            region="de",
            language="de",
            opportunity_score=85.0,
            competition_level="medium",
            search_volume_potential=50000,
            is_recommended=True,
            recommendation_reason="Large market with moderate competition",
        )
        assert market.opportunity_score == 85.0
        assert market.is_recommended is True


class TestGoalValidation:
    """Test GoalValidation dataclass."""

    def test_goal_fits(self):
        validation = GoalValidation(
            stated_goal=PrimaryGoal.LEADS,
            goal_fits_business=True,
            confidence=0.85,
        )
        assert validation.goal_fits_business is True
        assert validation.suggested_goal is None

    def test_goal_mismatch(self):
        validation = GoalValidation(
            stated_goal=PrimaryGoal.TRAFFIC,
            goal_fits_business=False,
            confidence=0.75,
            suggested_goal=PrimaryGoal.LEADS,
            suggestion_reason="Your site has demo forms indicating B2B lead gen",
        )
        assert validation.goal_fits_business is False
        assert validation.suggested_goal == PrimaryGoal.LEADS


class TestBusinessContext:
    """Test BusinessContext dataclass."""

    def test_default_values(self):
        context = BusinessContext(domain="example.com")
        assert context.domain == "example.com"
        assert context.business_model == BusinessModel.UNKNOWN
        assert context.primary_goal == PrimaryGoal.BALANCED

    def test_full_context(self):
        context = BusinessContext(
            domain="saas.com",
            business_model=BusinessModel.B2B_SAAS,
            company_stage=CompanyStage.GROWTH,
            industry="Software",
            primary_goal=PrimaryGoal.LEADS,
            seo_fit="excellent",
            recommended_focus=["comparison keywords", "integration content"],
            context_confidence=0.8,
        )
        assert context.industry == "Software"
        assert len(context.recommended_focus) == 2


class TestIntelligentCollectionConfig:
    """Test IntelligentCollectionConfig dataclass."""

    def test_default_config(self):
        config = IntelligentCollectionConfig(
            domain="example.com",
            primary_market="se",
            primary_language="sv",
        )
        assert config.domain == "example.com"
        assert config.primary_goal == PrimaryGoal.BALANCED
        assert config.direct_competitors == []

    def test_leads_focused_config(self):
        config = IntelligentCollectionConfig(
            domain="b2b.com",
            primary_market="us",
            primary_language="en",
            primary_goal=PrimaryGoal.LEADS,
            priority_intents=["commercial", "transactional"],
            content_type_focus=["comparison", "pricing"],
            direct_competitors=["competitor1.com", "competitor2.com"],
        )
        assert config.primary_goal == PrimaryGoal.LEADS
        assert "commercial" in config.priority_intents
        assert len(config.direct_competitors) == 2


class TestContextIntelligenceResult:
    """Test ContextIntelligenceResult dataclass."""

    def test_empty_result(self):
        result = ContextIntelligenceResult(domain="example.com")
        assert result.domain == "example.com"
        assert result.website_analysis is None
        assert result.overall_confidence == 0.0

    def test_to_analysis_context_empty(self):
        result = ContextIntelligenceResult(domain="example.com")
        context = result.to_analysis_context()

        assert context["domain"] == "example.com"
        assert context["business_context"] == {}
        assert context["competitor_context"] == {}

    def test_to_analysis_context_with_data(self):
        website = WebsiteAnalysis(
            domain="saas.com",
            business_model=BusinessModel.B2B_SAAS,
        )
        business = BusinessContext(
            domain="saas.com",
            business_model=BusinessModel.B2B_SAAS,
            primary_goal=PrimaryGoal.LEADS,
            seo_fit="good",
            recommended_focus=["comparison content"],
        )
        result = ContextIntelligenceResult(
            domain="saas.com",
            website_analysis=website,
            business_context=business,
            overall_confidence=0.8,
        )

        context = result.to_analysis_context()
        assert context["business_context"]["business_model"] == "b2b_saas"
        assert context["business_context"]["primary_goal"] == "leads"


# =============================================================================
# WEBSITE ANALYZER TESTS
# =============================================================================

class TestWebsiteAnalyzer:
    """Test WebsiteAnalyzer class."""

    def test_instantiation(self):
        from src.context.website_analyzer import WebsiteAnalyzer
        analyzer = WebsiteAnalyzer()
        assert analyzer.claude_client is None

    def test_instantiation_with_client(self):
        from src.context.website_analyzer import WebsiteAnalyzer
        mock_client = MagicMock()
        analyzer = WebsiteAnalyzer(claude_client=mock_client)
        assert analyzer.claude_client == mock_client


class TestWebsiteFetcher:
    """Test WebsiteFetcher class."""

    def test_extract_text(self):
        from src.context.website_analyzer import WebsiteFetcher
        fetcher = WebsiteFetcher()

        html = "<html><script>var x = 1;</script><body>Hello World</body></html>"
        text = fetcher._extract_text(html)

        assert "Hello World" in text
        assert "var x" not in text


# =============================================================================
# COMPETITOR DISCOVERY TESTS
# =============================================================================

class TestCompetitorDiscovery:
    """Test CompetitorDiscovery class."""

    def test_instantiation(self):
        from src.context.competitor_discovery import CompetitorDiscovery
        discovery = CompetitorDiscovery()
        assert discovery.claude_client is None
        assert discovery.dataforseo_client is None

    def test_get_discovery_queries(self):
        from src.context.competitor_discovery import get_discovery_queries
        queries = get_discovery_queries("example.com", "Example")

        assert len(queries) >= 3
        assert any("alternatives" in q["query"] for q in queries)
        assert any("competitors" in q["query"] for q in queries)

    def test_market_to_location(self):
        from src.context.competitor_discovery import CompetitorDiscovery
        discovery = CompetitorDiscovery()

        assert discovery._market_to_location("us") == 2840
        assert discovery._market_to_location("se") == 2752
        assert discovery._market_to_location("de") == 2276

    def test_market_to_language(self):
        from src.context.competitor_discovery import CompetitorDiscovery
        discovery = CompetitorDiscovery()

        assert discovery._market_to_language("us") == "en"
        assert discovery._market_to_language("se") == "sv"
        assert discovery._market_to_language("de") == "de"


# =============================================================================
# MARKET VALIDATOR TESTS
# =============================================================================

class TestMarketValidator:
    """Test MarketValidator class."""

    def test_instantiation(self):
        from src.context.market_validator import MarketValidator
        validator = MarketValidator()
        assert validator.claude_client is None

    def test_market_config_exists(self):
        from src.context.market_validator import MARKET_CONFIG

        assert "us" in MARKET_CONFIG
        assert "se" in MARKET_CONFIG
        assert "de" in MARKET_CONFIG

        assert MARKET_CONFIG["se"]["language"] == "sv"
        assert MARKET_CONFIG["de"]["language"] == "de"

    def test_market_relations_exist(self):
        from src.context.market_validator import MARKET_RELATIONS

        assert "se" in MARKET_RELATIONS
        assert "no" in MARKET_RELATIONS["se"]  # Nordic markets related

    def test_competition_to_level(self):
        from src.context.market_validator import MarketValidator
        validator = MarketValidator()

        assert validator._competition_to_level(0.1) == "low"
        assert validator._competition_to_level(0.4) == "medium"
        assert validator._competition_to_level(0.6) == "high"
        assert validator._competition_to_level(0.9) == "very_high"

    def test_calculate_opportunity_score(self):
        from src.context.market_validator import MarketValidator
        validator = MarketValidator()

        # High volume, low competition = high score
        high_opp = validator._calculate_opportunity_score(
            volume=10000, competition=0.2, market_size=1.0
        )

        # Low volume, high competition = low score
        low_opp = validator._calculate_opportunity_score(
            volume=100, competition=0.8, market_size=0.1
        )

        assert high_opp > low_opp
        assert 0 <= high_opp <= 100
        assert 0 <= low_opp <= 100


# =============================================================================
# BUSINESS PROFILER TESTS
# =============================================================================

class TestBusinessProfiler:
    """Test BusinessProfiler class."""

    def test_instantiation(self):
        from src.context.business_profiler import BusinessProfiler
        profiler = BusinessProfiler()
        assert profiler.claude_client is None

    def test_goal_signals_exist(self):
        from src.context.business_profiler import GOAL_SIGNALS

        assert PrimaryGoal.LEADS in GOAL_SIGNALS
        assert PrimaryGoal.TRAFFIC in GOAL_SIGNALS
        assert "positive" in GOAL_SIGNALS[PrimaryGoal.LEADS]
        assert "negative" in GOAL_SIGNALS[PrimaryGoal.LEADS]

    def test_journey_by_model_exists(self):
        from src.context.business_profiler import JOURNEY_BY_MODEL

        assert BusinessModel.B2B_SAAS in JOURNEY_BY_MODEL
        assert JOURNEY_BY_MODEL[BusinessModel.B2B_SAAS] == BuyerJourneyType.COMPLEX_B2B

    def test_find_best_goal(self):
        from src.context.business_profiler import BusinessProfiler
        profiler = BusinessProfiler()

        # B2B signals should suggest LEADS
        signals = ["has_demo_form", "has_contact_form", "b2b"]
        best = profiler._find_best_goal(signals)
        assert best == PrimaryGoal.LEADS

        # Publisher signals should suggest TRAFFIC
        signals = ["has_blog", "publisher", "content_extensive"]
        best = profiler._find_best_goal(signals)
        assert best == PrimaryGoal.TRAFFIC

    def test_validate_goal_balanced_always_fits(self):
        from src.context.business_profiler import BusinessProfiler
        profiler = BusinessProfiler()

        validation = profiler._validate_goal(
            stated_goal=PrimaryGoal.BALANCED,
            website_analysis=None,
        )

        assert validation.goal_fits_business is True
        # Without website analysis, confidence is default 0.5
        assert validation.confidence >= 0.5

    def test_infer_buyer_journey_b2b(self):
        from src.context.business_profiler import BusinessProfiler
        profiler = BusinessProfiler()

        journey = profiler._infer_buyer_journey(
            business_model=BusinessModel.B2B_SAAS,
            website_analysis=None,
        )

        assert journey.journey_type == BuyerJourneyType.COMPLEX_B2B
        assert "awareness" in journey.typical_stages
        assert journey.cycle_length == "weeks_to_months"


# =============================================================================
# ORCHESTRATOR TESTS
# =============================================================================

class TestContextIntelligenceOrchestrator:
    """Test ContextIntelligenceOrchestrator class."""

    def test_instantiation(self):
        from src.context.orchestrator import ContextIntelligenceOrchestrator
        orchestrator = ContextIntelligenceOrchestrator()

        assert orchestrator.website_analyzer is not None
        assert orchestrator.competitor_discovery is not None
        assert orchestrator.market_validator is not None
        assert orchestrator.business_profiler is not None

    def test_context_intelligence_request(self):
        from src.context.orchestrator import ContextIntelligenceRequest

        request = ContextIntelligenceRequest(
            domain="example.com",
            primary_market="se",
            primary_goal=PrimaryGoal.LEADS,
            known_competitors=["comp1.com", "comp2.com"],
        )

        assert request.domain == "example.com"
        assert request.primary_goal == PrimaryGoal.LEADS
        assert len(request.known_competitors) == 2

    def test_request_to_dict(self):
        from src.context.orchestrator import ContextIntelligenceRequest

        request = ContextIntelligenceRequest(
            domain="example.com",
            primary_market="se",
            primary_goal=PrimaryGoal.LEADS,
        )

        data = request.to_dict()
        assert data["domain"] == "example.com"
        assert data["primary_goal"] == "leads"


# =============================================================================
# INTEGRATION TESTS (Package-level)
# =============================================================================

class TestContextPackage:
    """Test context package imports and exports."""

    def test_all_exports_importable(self):
        from src.context import (
            # Enums
            PrimaryGoal,
            BusinessModel,
            CompanyStage,
            CompetitorType,
            ThreatLevel,
            BuyerJourneyType,
            DiscoveryMethod,
            ValidationStatus,
            # Dataclasses
            WebsiteAnalysis,
            ValidatedCompetitor,
            CompetitorValidation,
            MarketOpportunity,
            MarketValidation,
            BusinessContext,
            IntelligentCollectionConfig,
            ContextIntelligenceResult,
            # Agents
            WebsiteAnalyzer,
            CompetitorDiscovery,
            MarketValidator,
            BusinessProfiler,
            # Orchestrator
            ContextIntelligenceOrchestrator,
            ContextIntelligenceRequest,
            gather_context_intelligence,
        )

        # All should be importable
        assert PrimaryGoal is not None
        assert WebsiteAnalyzer is not None
        assert gather_context_intelligence is not None

    def test_factory_functions_exist(self):
        from src.context import (
            analyze_website,
            discover_competitors,
            validate_market,
            profile_business,
        )

        # All factory functions should exist
        assert callable(analyze_website)
        assert callable(discover_competitors)
        assert callable(validate_market)
        assert callable(profile_business)


# =============================================================================
# DATAFORSEO CLIENT HELPER TESTS
# =============================================================================

class TestDataForSEOClientHelpers:
    """Test new DataForSEO client helper methods."""

    def test_client_has_get_serp_results(self):
        from src.collector.client import DataForSEOClient
        assert hasattr(DataForSEOClient, 'get_serp_results')

    def test_client_has_get_keywords_data(self):
        from src.collector.client import DataForSEOClient
        assert hasattr(DataForSEOClient, 'get_keywords_data')

    def test_client_has_get_domain_competitors(self):
        from src.collector.client import DataForSEOClient
        assert hasattr(DataForSEOClient, 'get_domain_competitors')

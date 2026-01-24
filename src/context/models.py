"""
Context Intelligence Data Models

Defines all types used by the Context Intelligence layer for:
- Business context understanding
- Competitor discovery and classification
- Market validation and opportunity discovery
- Goal alignment and strategy profiling
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .market_detection import MarketDetectionResult
    from .market_resolver import ResolvedMarket


# =============================================================================
# ENUMS
# =============================================================================


class PrimaryGoal(str, Enum):
    """User's primary business goal for SEO."""
    TRAFFIC = "traffic"  # Maximize visitors
    LEADS = "leads"  # Generate qualified inquiries
    AUTHORITY = "authority"  # Build domain strength/backlinks
    BALANCED = "balanced"  # Optimize across all metrics


class BusinessModel(str, Enum):
    """Detected or declared business model."""
    B2B_SAAS = "b2b_saas"
    B2B_SERVICE = "b2b_service"
    B2C_ECOMMERCE = "b2c_ecommerce"
    B2C_SUBSCRIPTION = "b2c_subscription"
    MARKETPLACE = "marketplace"
    PUBLISHER = "publisher"
    LOCAL_SERVICE = "local_service"
    NONPROFIT = "nonprofit"
    UNKNOWN = "unknown"


class CompanyStage(str, Enum):
    """Company lifecycle stage."""
    STARTUP = "startup"  # New, building foundation
    GROWTH = "growth"  # Established product, seeking scale
    MATURE = "mature"  # Market leader, defending position
    DECLINING = "declining"  # Losing market share
    UNKNOWN = "unknown"


class CompetitorType(str, Enum):
    """Classification of competitor relationship."""
    DIRECT = "direct"  # Same product/service, same market
    SEO = "seo"  # Ranks for same keywords but different business
    CONTENT = "content"  # Competes for attention, not customers
    EMERGING = "emerging"  # New player gaining traction
    ASPIRATIONAL = "aspirational"  # Who they want to be like
    NOT_COMPETITOR = "not_competitor"  # Misclassified, should be ignored


class ThreatLevel(str, Enum):
    """Competitor threat assessment."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class BuyerJourneyType(str, Enum):
    """Type of buyer journey for this business."""
    SIMPLE_B2C = "simple_b2c"  # Quick decisions, low consideration
    COMPLEX_B2B = "complex_b2b"  # Long cycles, multiple stakeholders
    RESEARCH_HEAVY = "research_heavy"  # Lots of comparison before purchase
    IMPULSE = "impulse"  # Emotion-driven, quick conversion
    SUBSCRIPTION = "subscription"  # Trial-based, ongoing relationship


class DiscoveryMethod(str, Enum):
    """How a competitor or market was discovered."""
    USER_PROVIDED = "user_provided"
    SERP_ANALYSIS = "serp_analysis"
    BRAND_SEARCH = "brand_search"
    DATAFORSEO_SUGGESTED = "dataforseo_suggested"
    INDUSTRY_RESEARCH = "industry_research"
    WEBSITE_ANALYSIS = "website_analysis"


class ValidationStatus(str, Enum):
    """Status of validation for user-provided data."""
    CONFIRMED = "confirmed"  # Validated as accurate
    CORRECTED = "corrected"  # User was wrong, we corrected
    ENHANCED = "enhanced"  # User was right, we added more
    UNVALIDATED = "unvalidated"  # Could not validate


# =============================================================================
# WEBSITE ANALYSIS
# =============================================================================


@dataclass
class DetectedOffering:
    """A product or service detected on the website."""
    name: str
    type: str  # "software", "service", "product", "subscription"
    description: Optional[str] = None
    pricing_model: Optional[str] = None  # "subscription", "one-time", "custom"
    confidence: float = 0.0


@dataclass
class WebsiteAnalysis:
    """Results of analyzing the target website."""
    domain: str

    # Business classification
    business_model: BusinessModel = BusinessModel.UNKNOWN
    company_stage: CompanyStage = CompanyStage.UNKNOWN

    # Offerings
    offerings: List[DetectedOffering] = field(default_factory=list)
    value_proposition: Optional[str] = None

    # Target audience
    target_audience: Dict[str, Any] = field(default_factory=dict)

    # Content & language
    detected_languages: List[str] = field(default_factory=list)
    primary_language: Optional[str] = None
    content_maturity: str = "unknown"  # none, minimal, moderate, extensive

    # Technical
    technical_sophistication: str = "unknown"  # basic, moderate, high
    has_blog: bool = False
    has_pricing_page: bool = False
    has_demo_form: bool = False
    has_contact_form: bool = False
    has_ecommerce: bool = False

    # Monetization signals
    monetization_model: Optional[str] = None

    # Confidence
    analysis_confidence: float = 0.0
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# COMPETITOR INTELLIGENCE
# =============================================================================


@dataclass
class CompetitorEvidence:
    """Evidence supporting competitor classification."""
    keyword_overlap_percentage: float = 0.0
    traffic_ratio: float = 0.0  # Their traffic / our traffic
    business_similarity: float = 0.0
    mentioned_in_searches: List[str] = field(default_factory=list)
    shared_backlinks: int = 0


@dataclass
class ValidatedCompetitor:
    """A validated and classified competitor."""
    domain: str
    name: Optional[str] = None

    # Classification
    competitor_type: CompetitorType = CompetitorType.DIRECT
    threat_level: ThreatLevel = ThreatLevel.MEDIUM

    # Discovery
    discovery_method: DiscoveryMethod = DiscoveryMethod.DATAFORSEO_SUGGESTED
    user_provided: bool = False

    # Validation
    validation_status: ValidationStatus = ValidationStatus.UNVALIDATED
    validation_notes: Optional[str] = None

    # Evidence
    evidence: CompetitorEvidence = field(default_factory=CompetitorEvidence)

    # Analysis insights
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # Metrics (populated during collection)
    organic_traffic: int = 0
    organic_keywords: int = 0
    domain_rating: float = 0.0
    traffic_trend: Optional[str] = None  # "growing", "stable", "declining"

    # Confidence
    confidence_score: float = 0.0


@dataclass
class CompetitorValidation:
    """Results of competitor validation process."""
    # User-provided competitors
    user_provided: List[str] = field(default_factory=list)

    # Validated results
    confirmed: List[ValidatedCompetitor] = field(default_factory=list)
    reclassified: List[ValidatedCompetitor] = field(default_factory=list)
    rejected: List[Dict[str, str]] = field(default_factory=list)  # domain + reason

    # Discovered competitors
    discovered: List[ValidatedCompetitor] = field(default_factory=list)

    # Summary
    total_direct_competitors: int = 0
    total_seo_competitors: int = 0
    emerging_threats: int = 0

    validation_timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# MARKET INTELLIGENCE
# =============================================================================


@dataclass
class MarketOpportunity:
    """A market/region opportunity assessment."""
    region: str  # Country code or name
    language: str

    # Opportunity assessment
    opportunity_score: float = 0.0  # 0-100
    competition_level: str = "unknown"  # low, medium, high, very_high

    # Volume estimates
    search_volume_potential: int = 0
    keyword_count_estimate: int = 0

    # Competitive landscape
    top_competitors_in_market: List[str] = field(default_factory=list)
    our_current_visibility: float = 0.0  # 0-100

    # Recommendation
    is_primary: bool = False
    is_recommended: bool = False
    priority_rank: int = 0
    recommendation_reason: Optional[str] = None

    # Discovery
    discovery_method: DiscoveryMethod = DiscoveryMethod.SERP_ANALYSIS


@dataclass
class MarketValidation:
    """Results of market validation process."""
    # User-declared market
    declared_primary: str
    declared_language: str
    declared_secondary: List[str] = field(default_factory=list)

    # Validation results
    primary_validated: bool = False
    primary_validation_notes: Optional[str] = None

    # Discovered opportunities
    validated_markets: List[MarketOpportunity] = field(default_factory=list)
    discovered_opportunities: List[MarketOpportunity] = field(default_factory=list)

    # Recommendations
    should_adjust_primary: bool = False
    suggested_primary: Optional[str] = None
    suggested_secondary: List[str] = field(default_factory=list)

    # Language insights
    site_languages: List[str] = field(default_factory=list)
    language_mismatch: bool = False
    language_recommendation: Optional[str] = None

    validation_timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# BUSINESS STRATEGY
# =============================================================================


@dataclass
class GoalValidation:
    """Validation of user's stated goal against detected signals."""
    stated_goal: PrimaryGoal

    # Validation
    goal_fits_business: bool = True
    confidence: float = 0.0

    # Mismatch detection
    detected_signals: List[str] = field(default_factory=list)
    suggested_goal: Optional[PrimaryGoal] = None
    suggestion_reason: Optional[str] = None

    # Implications
    goal_implications: Dict[str, str] = field(default_factory=dict)


@dataclass
class BuyerJourney:
    """Understanding of the buyer's journey for this business."""
    journey_type: BuyerJourneyType = BuyerJourneyType.SIMPLE_B2C

    # Stages
    typical_stages: List[str] = field(default_factory=list)
    cycle_length: str = "unknown"  # "instant", "days", "weeks", "months"

    # Decision makers (for B2B)
    decision_makers: List[str] = field(default_factory=list)

    # Content needs
    content_needs_by_stage: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class SuccessDefinition:
    """What success looks like for this business."""
    # Scenarios
    scenario_10x: str = ""
    scenario_realistic_12m: str = ""
    scenario_minimum_viable: str = ""

    # Metrics
    primary_success_metric: str = ""
    secondary_metrics: List[str] = field(default_factory=list)

    # KPIs
    target_kpis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessContext:
    """Complete business context understanding."""
    domain: str

    # Business classification
    business_model: BusinessModel = BusinessModel.UNKNOWN
    company_stage: CompanyStage = CompanyStage.UNKNOWN
    industry: Optional[str] = None

    # Goals
    primary_goal: PrimaryGoal = PrimaryGoal.BALANCED
    goal_validation: Optional[GoalValidation] = None

    # Buyer journey
    buyer_journey: Optional[BuyerJourney] = None

    # Target audience
    target_audience: Dict[str, Any] = field(default_factory=dict)

    # Success definition
    success_definition: Optional[SuccessDefinition] = None

    # Strategic alignment
    seo_fit: str = "unknown"  # poor, moderate, good, excellent
    quick_wins_potential: str = "unknown"
    recommended_focus: List[str] = field(default_factory=list)

    # Inferred constraints
    content_velocity: str = "unknown"  # low, medium, high
    technical_resources: str = "unknown"
    seo_maturity: str = "unknown"

    # Confidence
    context_confidence: float = 0.0
    user_validated: bool = False

    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# CONTEXT INTELLIGENCE OUTPUT
# =============================================================================


@dataclass
class IntelligentCollectionConfig:
    """
    Configuration for data collection, enhanced by Context Intelligence.

    This replaces simple domain/market/language with validated and
    enriched collection parameters.
    """
    domain: str

    # Validated markets
    primary_market: str
    primary_language: str
    secondary_markets: List[str] = field(default_factory=list)
    collect_languages: List[str] = field(default_factory=list)

    # Validated competitors
    direct_competitors: List[str] = field(default_factory=list)
    seo_competitors: List[str] = field(default_factory=list)
    aspirational_competitors: List[str] = field(default_factory=list)
    ignore_domains: List[str] = field(default_factory=list)

    # Business context
    business_context: Optional[BusinessContext] = None

    # Collection focus
    primary_goal: PrimaryGoal = PrimaryGoal.BALANCED
    priority_intents: List[str] = field(default_factory=list)
    content_type_focus: List[str] = field(default_factory=list)

    # Collection flags
    skip_local_seo: bool = False
    skip_news_keywords: bool = False
    enhance_competitor_analysis: bool = True
    collect_secondary_markets: bool = False


@dataclass
class ContextIntelligenceResult:
    """
    Complete output from Context Intelligence phase.

    Contains all discovered and validated context that will be used
    to focus data collection and enhance analysis.
    """
    domain: str

    # Market detection (Phase 0)
    market_detection: Optional["MarketDetectionResult"] = None

    # Resolved market (Phase 2) - single source of truth for market
    resolved_market: Optional["ResolvedMarket"] = None

    # Website analysis
    website_analysis: Optional[WebsiteAnalysis] = None

    # Competitor intelligence
    competitor_validation: Optional[CompetitorValidation] = None

    # Market intelligence
    market_validation: Optional[MarketValidation] = None

    # Business context
    business_context: Optional[BusinessContext] = None

    # Final collection config
    collection_config: Optional[IntelligentCollectionConfig] = None

    # Execution metadata
    execution_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Overall confidence
    overall_confidence: float = 0.0

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_analysis_context(self) -> Dict[str, Any]:
        """
        Convert to context dict for analysis prompts.

        This is what gets passed to the AI analysis loops.
        """
        context = {
            "domain": self.domain,
            "resolved_market": {},
            "market_detection": {},
            "business_context": {},
            "competitor_context": {},
            "market_context": {},
            "collection_focus": {},
        }

        # Resolved market (Phase 2) - single source of truth
        if self.resolved_market:
            rm = self.resolved_market
            context["resolved_market"] = {
                "code": rm.code,
                "name": rm.name,
                "location_code": rm.location_code,
                "location_name": rm.location_name,
                "language_code": rm.language_code,
                "language_name": rm.language_name,
                "source": rm.source.value,
                "confidence": rm.confidence.value,
                "has_conflict": rm.has_conflict,
                "is_multi_market_site": rm.is_multi_market_site,
            }

        # Market detection (Phase 0)
        if self.market_detection:
            md = self.market_detection
            context["market_detection"] = {
                "detected_market": md.primary.code if md.primary else None,
                "detected_market_name": md.primary.name if md.primary else None,
                "confidence": md.primary.confidence if md.primary else 0,
                "needs_confirmation": md.needs_confirmation,
                "confirmation_reason": md.confirmation_reason,
                "is_multi_market_site": md.is_multi_market_site,
                "hreflang_markets": md.hreflang_markets,
                "has_conflicts": md.has_conflicts,
                "candidates": [
                    {"code": c.code, "name": c.name, "confidence": c.confidence}
                    for c in md.candidates[:3]
                ] if md.candidates else [],
            }

        # Business context
        if self.business_context:
            bc = self.business_context
            context["business_context"] = {
                "business_model": bc.business_model.value,
                "company_stage": bc.company_stage.value,
                "industry": bc.industry,
                "primary_goal": bc.primary_goal.value,
                "target_audience": bc.target_audience,
                "seo_fit": bc.seo_fit,
                "recommended_focus": bc.recommended_focus,
            }

            if bc.goal_validation:
                gv = bc.goal_validation
                context["business_context"]["goal_validation"] = {
                    "stated_goal": gv.stated_goal.value,
                    "goal_fits_business": gv.goal_fits_business,
                    "confidence": gv.confidence,
                    "suggested_goal": gv.suggested_goal.value if gv.suggested_goal else None,
                    "suggestion_reason": gv.suggestion_reason,
                }

            if bc.buyer_journey:
                bj = bc.buyer_journey
                context["business_context"]["buyer_journey"] = {
                    "type": bj.journey_type.value,
                    "stages": bj.typical_stages,
                    "cycle_length": bj.cycle_length,
                    "content_needs": bj.content_needs_by_stage,
                }

            if bc.success_definition:
                sd = bc.success_definition
                context["business_context"]["success_definition"] = {
                    "10x_scenario": sd.scenario_10x,
                    "realistic_12m": sd.scenario_realistic_12m,
                    "primary_metric": sd.primary_success_metric,
                }

        # Competitor context
        if self.competitor_validation:
            cv = self.competitor_validation
            context["competitor_context"] = {
                "user_provided": cv.user_provided,
                "direct_competitors": [
                    {
                        "domain": c.domain,
                        "threat_level": c.threat_level.value,
                        "validation_status": c.validation_status.value,
                        "strengths": c.strengths,
                        "weaknesses": c.weaknesses,
                    }
                    for c in cv.confirmed
                    if c.competitor_type == CompetitorType.DIRECT
                ],
                "discovered_competitors": [
                    {
                        "domain": c.domain,
                        "type": c.competitor_type.value,
                        "threat_level": c.threat_level.value,
                        "discovery_method": c.discovery_method.value,
                    }
                    for c in cv.discovered
                ],
                "reclassified": [
                    {
                        "domain": c.domain,
                        "original_assumption": "competitor",
                        "actual_type": c.competitor_type.value,
                        "reason": c.validation_notes,
                    }
                    for c in cv.reclassified
                ],
                "summary": {
                    "total_direct": cv.total_direct_competitors,
                    "total_seo": cv.total_seo_competitors,
                    "emerging_threats": cv.emerging_threats,
                },
            }

        # Market context
        if self.market_validation:
            mv = self.market_validation
            context["market_context"] = {
                "declared_market": mv.declared_primary,
                "declared_language": mv.declared_language,
                "primary_validated": mv.primary_validated,
                "validation_notes": mv.primary_validation_notes,
                "should_adjust_primary": mv.should_adjust_primary,
                "suggested_primary": mv.suggested_primary,
                "discovered_opportunities": [
                    {
                        "region": m.region,
                        "language": m.language,
                        "opportunity_score": m.opportunity_score,
                        "competition_level": m.competition_level,
                        "search_volume_potential": m.search_volume_potential,
                        "recommendation": m.recommendation_reason,
                    }
                    for m in mv.discovered_opportunities
                ],
                "language_insights": {
                    "site_languages": mv.site_languages,
                    "language_mismatch": mv.language_mismatch,
                    "recommendation": mv.language_recommendation,
                },
            }

        # Collection focus
        if self.collection_config:
            cc = self.collection_config
            context["collection_focus"] = {
                "primary_goal": cc.primary_goal.value,
                "priority_intents": cc.priority_intents,
                "content_type_focus": cc.content_type_focus,
                "direct_competitors": cc.direct_competitors,
                "ignore_domains": cc.ignore_domains,
            }

        return context

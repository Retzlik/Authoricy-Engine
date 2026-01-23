"""
Business Profiler Agent

Synthesizes all gathered intelligence into comprehensive business context:
- Validates user's stated goal against detected signals
- Infers buyer journey type
- Defines success metrics
- Generates strategic recommendations
- Creates the final BusinessContext

This is the final synthesis step before analysis.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .models import (
    BusinessContext,
    BusinessModel,
    BuyerJourney,
    BuyerJourneyType,
    CompanyStage,
    CompetitorValidation,
    GoalValidation,
    MarketValidation,
    PrimaryGoal,
    SuccessDefinition,
    WebsiteAnalysis,
)

if TYPE_CHECKING:
    from src.analyzer.client import ClaudeClient

logger = logging.getLogger(__name__)


# =============================================================================
# GOAL VALIDATION RULES
# =============================================================================


# What signals suggest which goal
GOAL_SIGNALS = {
    PrimaryGoal.LEADS: {
        "positive": [
            "has_demo_form",
            "has_contact_form",
            "b2b",
            "saas",
            "service",
            "enterprise",
            "pricing_custom",
        ],
        "negative": [
            "has_ecommerce",
            "advertising",
            "publisher",
        ],
        "description": "Generate qualified business inquiries",
    },
    PrimaryGoal.TRAFFIC: {
        "positive": [
            "has_blog",
            "publisher",
            "advertising",
            "content_extensive",
        ],
        "negative": [
            "b2b",
            "high_price",
        ],
        "description": "Maximize visitors and visibility",
    },
    PrimaryGoal.AUTHORITY: {
        "positive": [
            "b2b",
            "thought_leadership",
            "industry_expert",
        ],
        "negative": [
            "ecommerce",
            "local_service",
        ],
        "description": "Build domain strength and industry authority",
    },
    PrimaryGoal.BALANCED: {
        "positive": [],
        "negative": [],
        "description": "Optimize across all metrics",
    },
}


# Buyer journey by business model
JOURNEY_BY_MODEL = {
    BusinessModel.B2B_SAAS: BuyerJourneyType.COMPLEX_B2B,
    BusinessModel.B2B_SERVICE: BuyerJourneyType.COMPLEX_B2B,
    BusinessModel.B2C_ECOMMERCE: BuyerJourneyType.SIMPLE_B2C,
    BusinessModel.B2C_SUBSCRIPTION: BuyerJourneyType.SUBSCRIPTION,
    BusinessModel.MARKETPLACE: BuyerJourneyType.RESEARCH_HEAVY,
    BusinessModel.PUBLISHER: BuyerJourneyType.SIMPLE_B2C,
    BusinessModel.LOCAL_SERVICE: BuyerJourneyType.SIMPLE_B2C,
}


# Content needs by journey stage
CONTENT_BY_STAGE = {
    BuyerJourneyType.COMPLEX_B2B: {
        "awareness": ["Educational blog posts", "Industry reports", "Thought leadership"],
        "consideration": ["Comparison guides", "Use case studies", "Webinars"],
        "evaluation": ["ROI calculators", "Technical documentation", "Free trials"],
        "decision": ["Case studies", "Pricing transparency", "Implementation guides"],
    },
    BuyerJourneyType.SIMPLE_B2C: {
        "awareness": ["Product discovery content", "Social proof"],
        "decision": ["Product pages", "Reviews", "Clear pricing"],
    },
    BuyerJourneyType.SUBSCRIPTION: {
        "awareness": ["Value proposition content", "Free resources"],
        "trial": ["Onboarding content", "Feature guides"],
        "conversion": ["Pricing comparison", "Upgrade benefits"],
    },
    BuyerJourneyType.RESEARCH_HEAVY: {
        "research": ["Comparison content", "Reviews", "Guides"],
        "evaluation": ["Detailed specifications", "Expert opinions"],
        "decision": ["Trust signals", "Guarantees"],
    },
}


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================


SYNTHESIS_SYSTEM_PROMPT = """You are a business strategy expert. Your task is to synthesize business intelligence into actionable insights.

Given information about a business (website analysis, competitors, market), you will:
1. Validate if their stated SEO goal aligns with their business model
2. Define what success looks like for this specific business
3. Identify strategic focus areas for SEO

Be specific and actionable. Base all insights on the evidence provided."""


SYNTHESIS_USER_PROMPT = """Synthesize business context for SEO strategy.

## Business Information

**Domain:** {domain}
**Stated Goal:** {stated_goal} - {goal_description}

### Website Analysis
- Business Model: {business_model}
- Company Stage: {company_stage}
- Offerings: {offerings}
- Target Audience: {target_audience}
- Has Demo Form: {has_demo}
- Has Pricing Page: {has_pricing}
- Has Ecommerce: {has_ecommerce}
- Content Maturity: {content_maturity}

### Competitive Landscape
- Direct Competitors: {direct_competitors}
- Emerging Threats: {emerging_threats}

### Market Context
- Primary Market: {primary_market}
- Market Opportunity Score: {market_score}/100

---

Return a JSON object with this structure:
```json
{{
    "goal_validation": {{
        "goal_fits_business": true/false,
        "confidence": 0.0-1.0,
        "detected_signals": ["signal1", "signal2"],
        "suggested_goal": "traffic|leads|authority|balanced" or null,
        "suggestion_reason": "Why suggest a different goal" or null
    }},
    "success_definition": {{
        "scenario_10x": "What 10x success looks like for this business",
        "scenario_realistic_12m": "Realistic 12-month outcome",
        "scenario_minimum_viable": "Minimum acceptable outcome",
        "primary_success_metric": "The #1 metric to track",
        "secondary_metrics": ["metric1", "metric2"]
    }},
    "strategic_focus": {{
        "seo_fit": "poor|moderate|good|excellent",
        "quick_wins_potential": "low|medium|high",
        "recommended_focus": ["focus1", "focus2", "focus3"],
        "content_velocity_needed": "low|medium|high",
        "technical_priority": "low|medium|high"
    }}
}}
```

Be specific to THIS business. No generic advice."""


# =============================================================================
# BUSINESS PROFILER
# =============================================================================


class BusinessProfiler:
    """
    Synthesizes all context into comprehensive business understanding.

    This is the final step in Context Intelligence that creates
    the BusinessContext used throughout the analysis.
    """

    def __init__(self, claude_client: Optional["ClaudeClient"] = None):
        self.claude_client = claude_client

    async def profile(
        self,
        domain: str,
        stated_goal: PrimaryGoal,
        website_analysis: Optional[WebsiteAnalysis] = None,
        competitor_validation: Optional[CompetitorValidation] = None,
        market_validation: Optional[MarketValidation] = None,
    ) -> BusinessContext:
        """
        Create comprehensive business context.

        Args:
            domain: Target domain
            stated_goal: User's stated primary goal
            website_analysis: Results from website analyzer
            competitor_validation: Results from competitor discovery
            market_validation: Results from market validator

        Returns:
            BusinessContext with full business understanding
        """
        logger.info(f"Profiling business context for: {domain}")

        # Initialize context with basic info
        context = BusinessContext(
            domain=domain,
            primary_goal=stated_goal,
        )

        # Merge website analysis if available
        if website_analysis:
            context.business_model = website_analysis.business_model
            context.company_stage = website_analysis.company_stage
            context.target_audience = website_analysis.target_audience

        # Validate goal
        context.goal_validation = self._validate_goal(
            stated_goal=stated_goal,
            website_analysis=website_analysis,
        )

        # Infer buyer journey
        context.buyer_journey = self._infer_buyer_journey(
            business_model=context.business_model,
            website_analysis=website_analysis,
        )

        # If we have Claude, use AI for deeper synthesis
        if self.claude_client and website_analysis:
            ai_synthesis = await self._synthesize_with_ai(
                domain=domain,
                stated_goal=stated_goal,
                website_analysis=website_analysis,
                competitor_validation=competitor_validation,
                market_validation=market_validation,
            )

            if ai_synthesis:
                context = self._merge_ai_synthesis(context, ai_synthesis)
        else:
            # Fallback to heuristic synthesis
            context = self._heuristic_synthesis(
                context=context,
                stated_goal=stated_goal,
                website_analysis=website_analysis,
                competitor_validation=competitor_validation,
            )

        # Calculate overall confidence
        confidences = [
            context.goal_validation.confidence if context.goal_validation else 0.3,
            website_analysis.analysis_confidence if website_analysis else 0.3,
        ]
        context.context_confidence = sum(confidences) / len(confidences)

        logger.info(
            f"Business profiling complete: model={context.business_model.value}, "
            f"goal_fits={context.goal_validation.goal_fits_business if context.goal_validation else 'unknown'}"
        )

        return context

    def _validate_goal(
        self,
        stated_goal: PrimaryGoal,
        website_analysis: Optional[WebsiteAnalysis],
    ) -> GoalValidation:
        """Validate if stated goal fits the business."""
        validation = GoalValidation(
            stated_goal=stated_goal,
            goal_fits_business=True,
            confidence=0.5,
        )

        if not website_analysis:
            return validation

        # Collect signals from website analysis
        signals = []

        if website_analysis.has_demo_form:
            signals.append("has_demo_form")
        if website_analysis.has_contact_form:
            signals.append("has_contact_form")
        if website_analysis.has_pricing_page:
            signals.append("has_pricing")
        if website_analysis.has_ecommerce:
            signals.append("has_ecommerce")
        if website_analysis.has_blog:
            signals.append("has_blog")
        if website_analysis.business_model in [BusinessModel.B2B_SAAS, BusinessModel.B2B_SERVICE]:
            signals.append("b2b")
        if website_analysis.business_model == BusinessModel.PUBLISHER:
            signals.append("publisher")
        if website_analysis.content_maturity == "extensive":
            signals.append("content_extensive")

        validation.detected_signals = signals

        # Check if goal fits signals
        goal_config = GOAL_SIGNALS.get(stated_goal, GOAL_SIGNALS[PrimaryGoal.BALANCED])

        positive_matches = sum(1 for s in signals if s in goal_config["positive"])
        negative_matches = sum(1 for s in signals if s in goal_config["negative"])

        # Balanced goal always fits
        if stated_goal == PrimaryGoal.BALANCED:
            validation.goal_fits_business = True
            validation.confidence = 0.9
            return validation

        # Calculate fit
        if negative_matches > positive_matches:
            validation.goal_fits_business = False
            validation.confidence = 0.7

            # Suggest alternative goal
            best_goal = self._find_best_goal(signals)
            if best_goal != stated_goal:
                validation.suggested_goal = best_goal
                validation.suggestion_reason = self._generate_suggestion_reason(
                    stated_goal, best_goal, signals
                )
        else:
            validation.goal_fits_business = True
            validation.confidence = 0.6 + (positive_matches * 0.1)

        return validation

    def _find_best_goal(self, signals: List[str]) -> PrimaryGoal:
        """Find the goal that best fits the signals."""
        best_goal = PrimaryGoal.BALANCED
        best_score = 0

        for goal, config in GOAL_SIGNALS.items():
            if goal == PrimaryGoal.BALANCED:
                continue

            positive = sum(1 for s in signals if s in config["positive"])
            negative = sum(1 for s in signals if s in config["negative"])
            score = positive - negative

            if score > best_score:
                best_score = score
                best_goal = goal

        return best_goal

    def _generate_suggestion_reason(
        self,
        stated_goal: PrimaryGoal,
        suggested_goal: PrimaryGoal,
        signals: List[str],
    ) -> str:
        """Generate explanation for goal suggestion."""
        reasons = []

        if suggested_goal == PrimaryGoal.LEADS:
            if "has_demo_form" in signals:
                reasons.append("you have demo request forms")
            if "b2b" in signals:
                reasons.append("you're a B2B business")

        elif suggested_goal == PrimaryGoal.TRAFFIC:
            if "has_blog" in signals:
                reasons.append("you have extensive blog content")
            if "publisher" in signals:
                reasons.append("your business model is content-driven")

        if reasons:
            return f"Consider '{suggested_goal.value}' instead because {' and '.join(reasons)}."

        return f"Your business signals suggest '{suggested_goal.value}' may be more appropriate."

    def _infer_buyer_journey(
        self,
        business_model: BusinessModel,
        website_analysis: Optional[WebsiteAnalysis],
    ) -> BuyerJourney:
        """Infer the buyer journey type from business model."""
        journey_type = JOURNEY_BY_MODEL.get(business_model, BuyerJourneyType.SIMPLE_B2C)

        journey = BuyerJourney(journey_type=journey_type)

        # Set stages based on journey type
        if journey_type == BuyerJourneyType.COMPLEX_B2B:
            journey.typical_stages = ["awareness", "consideration", "evaluation", "decision"]
            journey.cycle_length = "weeks_to_months"
            journey.decision_makers = ["IT Manager", "Department Head", "Executive"]
        elif journey_type == BuyerJourneyType.SIMPLE_B2C:
            journey.typical_stages = ["awareness", "decision"]
            journey.cycle_length = "instant_to_days"
        elif journey_type == BuyerJourneyType.SUBSCRIPTION:
            journey.typical_stages = ["awareness", "trial", "conversion"]
            journey.cycle_length = "days_to_weeks"
        elif journey_type == BuyerJourneyType.RESEARCH_HEAVY:
            journey.typical_stages = ["research", "evaluation", "decision"]
            journey.cycle_length = "weeks"

        # Set content needs
        journey.content_needs_by_stage = CONTENT_BY_STAGE.get(journey_type, {})

        return journey

    async def _synthesize_with_ai(
        self,
        domain: str,
        stated_goal: PrimaryGoal,
        website_analysis: WebsiteAnalysis,
        competitor_validation: Optional[CompetitorValidation],
        market_validation: Optional[MarketValidation],
    ) -> Optional[Dict[str, Any]]:
        """Use AI for deeper business synthesis."""
        if not self.claude_client:
            return None

        # Format offerings
        offerings = ", ".join([
            o.name for o in website_analysis.offerings
        ]) if website_analysis.offerings else "Unknown"

        # Format competitors
        direct_competitors = []
        emerging_threats = 0
        if competitor_validation:
            direct_competitors = [
                c.domain for c in competitor_validation.confirmed
                if c.competitor_type.value == "direct"
            ][:5]
            emerging_threats = competitor_validation.emerging_threats

        # Format market
        primary_market = "Unknown"
        market_score = 50
        if market_validation:
            primary_market = market_validation.declared_primary
            if market_validation.validated_markets:
                market_score = market_validation.validated_markets[0].opportunity_score

        try:
            prompt = SYNTHESIS_USER_PROMPT.format(
                domain=domain,
                stated_goal=stated_goal.value,
                goal_description=GOAL_SIGNALS[stated_goal]["description"],
                business_model=website_analysis.business_model.value,
                company_stage=website_analysis.company_stage.value,
                offerings=offerings,
                target_audience=json.dumps(website_analysis.target_audience),
                has_demo=website_analysis.has_demo_form,
                has_pricing=website_analysis.has_pricing_page,
                has_ecommerce=website_analysis.has_ecommerce,
                content_maturity=website_analysis.content_maturity,
                direct_competitors=", ".join(direct_competitors) or "None identified",
                emerging_threats=emerging_threats,
                primary_market=primary_market,
                market_score=market_score,
            )

            response = await self.claude_client.analyze_with_retry(
                prompt=prompt,
                system=SYNTHESIS_SYSTEM_PROMPT,
                max_tokens=2000,
                temperature=0.3,
            )

            if response.success:
                json_match = re.search(r'\{[\s\S]*\}', response.content)
                if json_match:
                    return json.loads(json_match.group())

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI synthesis JSON: {e}")
        except Exception as e:
            logger.error(f"AI synthesis failed: {e}")

        return None

    def _merge_ai_synthesis(
        self,
        context: BusinessContext,
        ai_synthesis: Dict[str, Any],
    ) -> BusinessContext:
        """Merge AI synthesis into context."""
        # Goal validation
        gv_data = ai_synthesis.get("goal_validation", {})
        if gv_data and context.goal_validation:
            context.goal_validation.goal_fits_business = gv_data.get(
                "goal_fits_business",
                context.goal_validation.goal_fits_business
            )
            context.goal_validation.confidence = gv_data.get(
                "confidence",
                context.goal_validation.confidence
            )
            if gv_data.get("detected_signals"):
                context.goal_validation.detected_signals.extend(gv_data["detected_signals"])

            if gv_data.get("suggested_goal"):
                try:
                    context.goal_validation.suggested_goal = PrimaryGoal(gv_data["suggested_goal"])
                    context.goal_validation.suggestion_reason = gv_data.get("suggestion_reason")
                except ValueError:
                    pass

        # Success definition
        sd_data = ai_synthesis.get("success_definition", {})
        if sd_data:
            context.success_definition = SuccessDefinition(
                scenario_10x=sd_data.get("scenario_10x", ""),
                scenario_realistic_12m=sd_data.get("scenario_realistic_12m", ""),
                scenario_minimum_viable=sd_data.get("scenario_minimum_viable", ""),
                primary_success_metric=sd_data.get("primary_success_metric", ""),
                secondary_metrics=sd_data.get("secondary_metrics", []),
            )

        # Strategic focus
        sf_data = ai_synthesis.get("strategic_focus", {})
        if sf_data:
            context.seo_fit = sf_data.get("seo_fit", "unknown")
            context.quick_wins_potential = sf_data.get("quick_wins_potential", "unknown")
            context.recommended_focus = sf_data.get("recommended_focus", [])
            context.content_velocity = sf_data.get("content_velocity_needed", "unknown")

        return context

    def _heuristic_synthesis(
        self,
        context: BusinessContext,
        stated_goal: PrimaryGoal,
        website_analysis: Optional[WebsiteAnalysis],
        competitor_validation: Optional[CompetitorValidation],
    ) -> BusinessContext:
        """Fallback heuristic synthesis when AI is not available."""
        # Basic success definition
        if stated_goal == PrimaryGoal.LEADS:
            context.success_definition = SuccessDefinition(
                scenario_10x="Dominate comparison searches, 100+ qualified leads/month",
                scenario_realistic_12m="Top 3 rankings for 20 high-intent keywords",
                scenario_minimum_viable="Rank for brand terms, capture existing demand",
                primary_success_metric="Qualified leads from organic search",
                secondary_metrics=["Organic traffic", "Keyword rankings", "Conversion rate"],
            )
        elif stated_goal == PrimaryGoal.TRAFFIC:
            context.success_definition = SuccessDefinition(
                scenario_10x="1M+ monthly organic visitors",
                scenario_realistic_12m="100K monthly organic visitors",
                scenario_minimum_viable="Consistent traffic growth month-over-month",
                primary_success_metric="Monthly organic sessions",
                secondary_metrics=["Pages per session", "Bounce rate", "Time on site"],
            )
        elif stated_goal == PrimaryGoal.AUTHORITY:
            context.success_definition = SuccessDefinition(
                scenario_10x="Industry-leading domain authority, featured in major publications",
                scenario_realistic_12m="DR 50+, 500+ referring domains",
                scenario_minimum_viable="Consistent backlink acquisition",
                primary_success_metric="Domain Rating / Domain Authority",
                secondary_metrics=["Referring domains", "Brand mentions", "Citation count"],
            )
        else:  # BALANCED
            context.success_definition = SuccessDefinition(
                scenario_10x="Market leader across all SEO metrics",
                scenario_realistic_12m="Significant improvement across traffic, leads, and authority",
                scenario_minimum_viable="Positive trajectory on all key metrics",
                primary_success_metric="Composite SEO health score",
                secondary_metrics=["Organic traffic", "Lead generation", "Domain authority"],
            )

        # Basic strategic recommendations
        if website_analysis:
            if website_analysis.content_maturity == "minimal":
                context.recommended_focus = [
                    "Build foundational content",
                    "Create pillar pages for main topics",
                    "Establish content publishing cadence",
                ]
            elif website_analysis.content_maturity == "moderate":
                context.recommended_focus = [
                    "Fill content gaps vs competitors",
                    "Optimize existing high-potential content",
                    "Build topical authority clusters",
                ]
            else:
                context.recommended_focus = [
                    "Defend existing rankings",
                    "Expand into adjacent topics",
                    "Focus on competitive differentiation",
                ]

        context.seo_fit = "good"  # Default assumption
        context.quick_wins_potential = "medium"

        return context


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


async def profile_business(
    domain: str,
    stated_goal: PrimaryGoal,
    website_analysis: Optional[WebsiteAnalysis] = None,
    competitor_validation: Optional[CompetitorValidation] = None,
    market_validation: Optional[MarketValidation] = None,
    claude_client: Optional["ClaudeClient"] = None,
) -> BusinessContext:
    """
    Convenience function to create business profile.

    Args:
        domain: Target domain
        stated_goal: User's stated goal
        website_analysis: Results from website analyzer
        competitor_validation: Results from competitor discovery
        market_validation: Results from market validator
        claude_client: Claude client (optional)

    Returns:
        BusinessContext with full business understanding
    """
    profiler = BusinessProfiler(claude_client=claude_client)

    return await profiler.profile(
        domain=domain,
        stated_goal=stated_goal,
        website_analysis=website_analysis,
        competitor_validation=competitor_validation,
        market_validation=market_validation,
    )

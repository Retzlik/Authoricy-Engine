"""
Competitor Discovery Agent

Discovers and classifies competitors through multiple methods:
- SERP analysis for brand-related searches
- DataForSEO competitor suggestions
- User-provided competitor validation
- Industry research

Classifies competitors as:
- Direct: Same product/service, same market
- SEO: Ranks for same keywords but different business
- Content: Competes for attention, not customers
- Emerging: New player gaining traction
- Aspirational: Who they want to be like
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .models import (
    CompetitorEvidence,
    CompetitorType,
    CompetitorValidation,
    DiscoveryMethod,
    ThreatLevel,
    ValidatedCompetitor,
    ValidationStatus,
    WebsiteAnalysis,
)
from src.utils.domain_filter import is_excluded_domain, get_exclusion_reason

if TYPE_CHECKING:
    from src.analyzer.client import ClaudeClient
    from src.collector.client import DataForSEOClient

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================


CLASSIFICATION_SYSTEM_PROMPT = """You are an expert competitive analyst. Your task is to classify competitors based on their relationship to a target business.

## Competitor Types:

1. **DIRECT**: Same product/service, same target market
   - They solve the same problem for the same customers
   - Customers would choose between them
   - Example: Asana vs Monday.com

2. **SEO**: Ranks for same keywords but different business
   - They appear in search results but aren't actual business competitors
   - Example: Wikipedia, Reddit, news sites, educational content
   - Should be tracked for SEO but not as business threats

3. **CONTENT**: Competes for attention, not customers
   - Industry blogs, news sites, influencers
   - Potential partners rather than competitors
   - Example: Industry publications, review sites

4. **EMERGING**: New player gaining traction
   - Recently founded or recently pivoted
   - Growing fast (20%+ growth)
   - May become direct competitor soon

5. **ASPIRATIONAL**: Industry leader to learn from
   - Much larger, established market leader
   - Defines the category
   - Goal is to learn, not directly compete

6. **NOT_COMPETITOR**: Incorrectly suggested
   - No real competitive relationship
   - Should be ignored in analysis

Be precise and evidence-based in your classification."""


CLASSIFICATION_USER_PROMPT = """Classify these potential competitors for the target business.

## Target Business:
- Domain: {domain}
- Business Model: {business_model}
- Industry: {industry}
- Offerings: {offerings}
- Target Audience: {target_audience}

## Potential Competitors to Classify:

{competitors_list}

---

For EACH competitor, return a JSON object in this array:
```json
[
    {{
        "domain": "competitor1.com",
        "competitor_type": "direct|seo|content|emerging|aspirational|not_competitor",
        "threat_level": "critical|high|medium|low|none",
        "classification_reason": "Brief explanation of why this classification",
        "strengths": ["strength1", "strength2"],
        "weaknesses": ["weakness1", "weakness2"],
        "confidence": 0.0 to 1.0
    }}
]
```

Be thorough and precise. Classify EVERY competitor in the list."""


# =============================================================================
# COMPETITOR DISCOVERY QUERIES
# =============================================================================


def get_discovery_queries(domain: str, brand_name: Optional[str] = None) -> List[Dict[str, str]]:
    """Generate search queries for competitor discovery."""
    # Extract brand name from domain if not provided
    if not brand_name:
        brand_name = domain.split('.')[0].replace('-', ' ').title()

    return [
        {
            "query": f"{brand_name} alternatives",
            "purpose": "Find direct competitors customers consider",
        },
        {
            "query": f"{brand_name} vs",
            "purpose": "Find head-to-head competitors",
        },
        {
            "query": f"{brand_name} competitors",
            "purpose": "Find known competitors",
        },
        {
            "query": f"best {brand_name} alternatives 2024",
            "purpose": "Find current market alternatives",
        },
    ]


# =============================================================================
# COMPETITOR DISCOVERY
# =============================================================================


class CompetitorDiscovery:
    """
    Discovers and classifies competitors for a target domain.

    Uses multiple discovery methods:
    1. User-provided competitors (validated)
    2. DataForSEO suggested competitors (classified)
    3. SERP analysis for brand searches (discovered)
    """

    def __init__(
        self,
        claude_client: Optional["ClaudeClient"] = None,
        dataforseo_client: Optional["DataForSEOClient"] = None,
    ):
        self.claude_client = claude_client
        self.dataforseo_client = dataforseo_client

    async def discover_and_validate(
        self,
        domain: str,
        website_analysis: Optional[WebsiteAnalysis] = None,
        user_provided_competitors: Optional[List[str]] = None,
        dataforseo_competitors: Optional[List[Dict[str, Any]]] = None,
        market: str = "us",
    ) -> CompetitorValidation:
        """
        Discover and validate competitors for a domain.

        Args:
            domain: Target domain
            website_analysis: Results from website analyzer
            user_provided_competitors: Competitors provided by user
            dataforseo_competitors: Competitors suggested by DataForSEO
            market: Target market for SERP analysis

        Returns:
            CompetitorValidation with classified competitors
        """
        logger.info(f"Discovering competitors for: {domain}")

        result = CompetitorValidation(
            user_provided=user_provided_competitors or [],
        )

        # Collect all potential competitors
        all_competitors: Dict[str, Dict[str, Any]] = {}

        # 1. Add user-provided competitors (WITH PLATFORM FILTERING)
        if user_provided_competitors:
            for comp in user_provided_competitors:
                # Filter out platforms - reject with reason
                if is_excluded_domain(comp):
                    reason = get_exclusion_reason(comp) or "Platform/non-competitor"
                    result.rejected.append({
                        "domain": comp,
                        "reason": f"Excluded: {reason}",
                    })
                    logger.info(f"Rejected user-provided competitor {comp}: {reason}")
                    continue
                all_competitors[comp] = {
                    "domain": comp,
                    "source": DiscoveryMethod.USER_PROVIDED,
                    "user_provided": True,
                }

        # 2. Add DataForSEO suggested competitors (WITH PLATFORM FILTERING)
        if dataforseo_competitors:
            for comp in dataforseo_competitors[:20]:  # Limit to top 20
                comp_domain = comp.get("domain", "")
                # Filter out platforms
                if not comp_domain or is_excluded_domain(comp_domain):
                    continue
                if comp_domain not in all_competitors:
                    all_competitors[comp_domain] = {
                        "domain": comp_domain,
                        "source": DiscoveryMethod.DATAFORSEO_SUGGESTED,
                        "user_provided": False,
                        "metrics": comp,
                    }

        # 3. Discover via SERP analysis (if we have DataForSEO client)
        if self.dataforseo_client:
            discovered = await self._discover_from_serp(domain, market)
            for comp in discovered:
                comp_domain = comp.get("domain", "")
                # Filter out platforms from SERP results
                if not comp_domain or is_excluded_domain(comp_domain):
                    continue
                if comp_domain not in all_competitors:
                    all_competitors[comp_domain] = comp

        # If no competitors found, return empty result
        if not all_competitors:
            logger.warning(f"No competitors found for {domain}")
            return result

        # 4. Classify all competitors using AI
        if self.claude_client and website_analysis:
            classifications = await self._classify_competitors(
                domain=domain,
                website_analysis=website_analysis,
                competitors=list(all_competitors.values()),
            )

            # Process classifications
            for classification in classifications:
                comp_domain = classification.get("domain", "")
                if not comp_domain:
                    continue

                original_data = all_competitors.get(comp_domain, {})
                validated = self._create_validated_competitor(
                    classification=classification,
                    original_data=original_data,
                )

                # Sort into appropriate buckets
                if original_data.get("user_provided"):
                    if validated.competitor_type == CompetitorType.NOT_COMPETITOR:
                        result.rejected.append({
                            "domain": comp_domain,
                            "reason": validated.validation_notes or "Not a real competitor",
                        })
                    elif validated.competitor_type in [CompetitorType.SEO, CompetitorType.CONTENT]:
                        result.reclassified.append(validated)
                    else:
                        validated.validation_status = ValidationStatus.CONFIRMED
                        result.confirmed.append(validated)
                else:
                    if validated.competitor_type != CompetitorType.NOT_COMPETITOR:
                        result.discovered.append(validated)

        else:
            # Fallback: Accept all as unclassified
            for comp_data in all_competitors.values():
                validated = ValidatedCompetitor(
                    domain=comp_data["domain"],
                    competitor_type=CompetitorType.DIRECT,
                    threat_level=ThreatLevel.MEDIUM,
                    discovery_method=comp_data.get("source", DiscoveryMethod.DATAFORSEO_SUGGESTED),
                    user_provided=comp_data.get("user_provided", False),
                    validation_status=ValidationStatus.UNVALIDATED,
                    confidence_score=0.3,
                )

                if comp_data.get("user_provided"):
                    result.confirmed.append(validated)
                else:
                    result.discovered.append(validated)

        # Calculate summary stats
        all_validated = result.confirmed + result.discovered
        result.total_direct_competitors = sum(
            1 for c in all_validated if c.competitor_type == CompetitorType.DIRECT
        )
        result.total_seo_competitors = sum(
            1 for c in all_validated if c.competitor_type == CompetitorType.SEO
        )
        result.emerging_threats = sum(
            1 for c in all_validated if c.competitor_type == CompetitorType.EMERGING
        )

        logger.info(
            f"Competitor discovery complete: {result.total_direct_competitors} direct, "
            f"{result.total_seo_competitors} SEO, {result.emerging_threats} emerging"
        )

        return result

    async def _discover_from_serp(
        self,
        domain: str,
        market: str,
    ) -> List[Dict[str, Any]]:
        """Discover competitors from SERP analysis."""
        discovered = []

        if not self.dataforseo_client:
            return discovered

        queries = get_discovery_queries(domain)

        for query_info in queries[:2]:  # Limit queries to control API costs
            try:
                # Use DataForSEO SERP API
                serp_results = await self.dataforseo_client.get_serp_results(
                    keyword=query_info["query"],
                    location_code=self._market_to_location(market),
                    language_code=self._market_to_language(market),
                    depth=20,
                )

                if serp_results:
                    for item in serp_results.get("items", [])[:10]:
                        result_domain = item.get("domain", "")
                        # Filter: must exist, not be self, not be a platform
                        if result_domain and result_domain != domain and not is_excluded_domain(result_domain):
                            discovered.append({
                                "domain": result_domain,
                                "source": DiscoveryMethod.SERP_ANALYSIS,
                                "user_provided": False,
                                "discovered_via": query_info["query"],
                            })

            except Exception as e:
                logger.warning(f"SERP discovery failed for '{query_info['query']}': {e}")

        return discovered

    def _market_to_location(self, market: str) -> int:
        """Convert market code to DataForSEO location code."""
        market_locations = {
            "us": 2840,
            "uk": 2826,
            "se": 2752,
            "de": 2276,
            "fr": 2250,
            "no": 2578,
            "dk": 2208,
            "fi": 2246,
            "nl": 2528,
        }
        return market_locations.get(market.lower(), 2840)

    def _market_to_language(self, market: str) -> str:
        """Convert market code to language code."""
        market_languages = {
            "us": "en",
            "uk": "en",
            "se": "sv",
            "de": "de",
            "fr": "fr",
            "no": "no",
            "dk": "da",
            "fi": "fi",
            "nl": "nl",
        }
        return market_languages.get(market.lower(), "en")

    async def _classify_competitors(
        self,
        domain: str,
        website_analysis: WebsiteAnalysis,
        competitors: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use AI to classify competitors."""
        if not self.claude_client:
            return []

        # Format competitors list for prompt
        competitors_text = ""
        for i, comp in enumerate(competitors, 1):
            comp_domain = comp.get("domain", "unknown")
            source = comp.get("source", DiscoveryMethod.DATAFORSEO_SUGGESTED)
            metrics = comp.get("metrics", {})

            competitors_text += f"\n{i}. **{comp_domain}**\n"
            competitors_text += f"   - Source: {source.value if isinstance(source, DiscoveryMethod) else source}\n"

            if metrics:
                traffic = metrics.get("organic_traffic", "N/A")
                keywords = metrics.get("organic_keywords", "N/A")
                competitors_text += f"   - Traffic: {traffic}, Keywords: {keywords}\n"

        # Format offerings
        offerings_text = ", ".join([
            o.name for o in website_analysis.offerings
        ]) if website_analysis.offerings else "Unknown"

        try:
            prompt = CLASSIFICATION_USER_PROMPT.format(
                domain=domain,
                business_model=website_analysis.business_model.value,
                industry="Unknown",  # TODO: Add industry detection
                offerings=offerings_text,
                target_audience=json.dumps(website_analysis.target_audience),
                competitors_list=competitors_text,
            )

            response = await self.claude_client.analyze_with_retry(
                prompt=prompt,
                system=CLASSIFICATION_SYSTEM_PROMPT,
                max_tokens=4000,
                temperature=0.2,
            )

            if response.success:
                # Extract JSON array from response
                json_match = re.search(r'\[[\s\S]*\]', response.content)
                if json_match:
                    return json.loads(json_match.group())

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse competitor classification JSON: {e}")
        except Exception as e:
            logger.error(f"Competitor classification failed: {e}")

        return []

    def _create_validated_competitor(
        self,
        classification: Dict[str, Any],
        original_data: Dict[str, Any],
    ) -> ValidatedCompetitor:
        """Create a ValidatedCompetitor from classification data."""
        # Parse competitor type
        comp_type_str = classification.get("competitor_type", "direct")
        try:
            comp_type = CompetitorType(comp_type_str)
        except ValueError:
            comp_type = CompetitorType.DIRECT

        # Parse threat level
        threat_str = classification.get("threat_level", "medium")
        try:
            threat = ThreatLevel(threat_str)
        except ValueError:
            threat = ThreatLevel.MEDIUM

        # Get source
        source = original_data.get("source", DiscoveryMethod.DATAFORSEO_SUGGESTED)
        if isinstance(source, str):
            try:
                source = DiscoveryMethod(source)
            except ValueError:
                source = DiscoveryMethod.DATAFORSEO_SUGGESTED

        # Get metrics from original data
        metrics = original_data.get("metrics", {})

        return ValidatedCompetitor(
            domain=classification.get("domain", ""),
            competitor_type=comp_type,
            threat_level=threat,
            discovery_method=source,
            user_provided=original_data.get("user_provided", False),
            validation_status=ValidationStatus.CONFIRMED if original_data.get("user_provided") else ValidationStatus.UNVALIDATED,
            validation_notes=classification.get("classification_reason"),
            strengths=classification.get("strengths", []),
            weaknesses=classification.get("weaknesses", []),
            organic_traffic=metrics.get("organic_traffic", 0),
            organic_keywords=metrics.get("organic_keywords", 0),
            domain_rating=metrics.get("domain_rank", 0.0),
            confidence_score=classification.get("confidence", 0.5),
        )


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


async def discover_competitors(
    domain: str,
    website_analysis: Optional[WebsiteAnalysis] = None,
    user_provided_competitors: Optional[List[str]] = None,
    dataforseo_competitors: Optional[List[Dict[str, Any]]] = None,
    market: str = "us",
    claude_client: Optional["ClaudeClient"] = None,
    dataforseo_client: Optional["DataForSEOClient"] = None,
) -> CompetitorValidation:
    """
    Convenience function to discover and validate competitors.

    Args:
        domain: Target domain
        website_analysis: Results from website analyzer
        user_provided_competitors: Competitors provided by user
        dataforseo_competitors: Competitors suggested by DataForSEO
        market: Target market for SERP analysis
        claude_client: Claude client for AI classification
        dataforseo_client: DataForSEO client for SERP discovery

    Returns:
        CompetitorValidation result
    """
    discovery = CompetitorDiscovery(
        claude_client=claude_client,
        dataforseo_client=dataforseo_client,
    )

    return await discovery.discover_and_validate(
        domain=domain,
        website_analysis=website_analysis,
        user_provided_competitors=user_provided_competitors,
        dataforseo_competitors=dataforseo_competitors,
        market=market,
    )

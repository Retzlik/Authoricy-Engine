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

## Competitor Types (in order of priority):

1. **DIRECT**: Same product/service, same target market
   - They solve the SAME problem for the SAME customers
   - Customers would directly choose between them
   - Must sell similar products/services in the same market
   - Example: Asana vs Monday.com (both project management SaaS)

2. **EMERGING**: New player becoming a direct competitor
   - Similar business model, entering the same market
   - Growing fast (20%+ growth)
   - May become direct competitor soon

3. **ASPIRATIONAL**: Industry leader to learn from
   - Much larger, established market leader
   - Defines the category
   - Similar business, but different scale

4. **CONTENT**: Industry content creators
   - Industry blogs, news sites, influencers
   - Related content but don't sell competing products
   - Potential partners rather than competitors
   - Example: Review sites, industry publications

5. **SEO**: Only use this for ACTUAL SEO competitors
   - Same industry/vertical AND ranks for overlapping keywords
   - Different business model but relevant to the industry
   - Example: A B2B software company and a B2B consulting firm in same industry
   - NOT for: dictionaries, generic tools, unrelated sites

6. **NOT_COMPETITOR**: Use this LIBERALLY for unrelated sites
   - Different industry entirely
   - No product/service overlap
   - Only appears because of generic/ambiguous keywords
   - Examples that are ALWAYS not_competitor:
     * Dictionaries, language tools (synonymer.se, ordkollen.se)
     * Testing/quiz platforms (testproffs.se)
     * Government sites, news sites, Wikipedia
     * Generic utilities (weather, maps, converters)
     * Social media platforms
   - When in doubt, classify as NOT_COMPETITOR

## CRITICAL RULES:
- If the domain serves a COMPLETELY different purpose than the target business, use NOT_COMPETITOR
- Don't classify random sites as "SEO competitors" just because they might rank for some keywords
- A true SEO competitor must be in the same or adjacent industry

Be strict and conservative. When unsure, prefer NOT_COMPETITOR over SEO."""


CLASSIFICATION_USER_PROMPT = """Classify these potential competitors for the target business.

## Target Business:
- Domain: {domain}
- Business Model: {business_model}
- Industry: {industry}
- Offerings: {offerings}
- Target Audience: {target_audience}
- **Target Market: {target_market}** (this is the market/country we're analyzing)

## Potential Competitors to Classify:

{competitors_list}

---

IMPORTANT: Be STRICT about classification. Ask yourself for each domain:
1. Does this business sell similar products/services? If NO → NOT_COMPETITOR
2. Would customers consider this as an alternative? If NO → NOT_COMPETITOR
3. Is it a generic utility (dictionary, testing platform, government)? → NOT_COMPETITOR
4. Is it truly in the same industry/vertical? If NO → NOT_COMPETITOR
5. **Does this competitor actually operate in or target {target_market}?** If a competitor only operates in a completely different market (e.g., US-only competitor for UK analysis), consider lowering their threat level or marking as NOT_COMPETITOR.

Only classify as DIRECT if they genuinely compete for the same customers IN THE TARGET MARKET.
Only classify as SEO if they're in the same industry but different business model.

**Market-specific guidance:**
- Competitors with country-specific TLDs matching the target market (e.g., .co.uk for UK) are more likely to be relevant
- Global brands that operate in {target_market} should still be classified normally
- Competitors that ONLY operate in other markets should be NOT_COMPETITOR or have LOW threat level

For EACH competitor, return a JSON object in this array:
```json
[
    {{
        "domain": "competitor1.com",
        "competitor_type": "direct|seo|content|emerging|aspirational|not_competitor",
        "threat_level": "critical|high|medium|low|none",
        "classification_reason": "One sentence explaining WHY - be specific about business relationship",
        "strengths": ["strength1", "strength2"],
        "weaknesses": ["weakness1", "weakness2"],
        "confidence": 0.0 to 1.0
    }}
]
```

Be conservative. When uncertain, prefer NOT_COMPETITOR. Classify EVERY competitor in the list."""


# =============================================================================
# COMPETITOR DISCOVERY QUERIES
# =============================================================================


def get_discovery_queries(
    domain: str,
    brand_name: Optional[str] = None,
    industry: Optional[str] = None,
    offerings: Optional[List[str]] = None,
    language: str = "en",
    market: str = "us",
) -> List[Dict[str, str]]:
    """
    Generate search queries for competitor discovery.

    Uses industry-aware, localized queries for better results.

    Args:
        domain: Target domain
        brand_name: Brand/company name
        industry: Business industry/category
        offerings: Main products/services offered
        language: Primary language (sv, en, de, etc.)
        market: Primary market (se, us, uk, etc.)
    """
    # Extract brand name from domain if not provided
    if not brand_name:
        brand_name = domain.split('.')[0].replace('-', ' ').title()

    queries = []

    # Localized query templates by language
    QUERY_TEMPLATES = {
        "en": {
            "alternatives": f"{brand_name} alternatives",
            "vs": f"{brand_name} vs",
            "competitors": f"{brand_name} competitors",
            "best_alternatives": f"best {brand_name} alternatives 2024",
            "industry_products": "best {industry} products",
            "buy_product": "buy {product} online",
            "product_reviews": "{product} reviews comparison",
        },
        "sv": {
            "alternatives": f"{brand_name} alternativ",
            "vs": f"{brand_name} vs",
            "competitors": f"{brand_name} konkurrenter",
            "best_alternatives": f"bästa alternativ till {brand_name}",
            "industry_products": "bästa {industry} produkter Sverige",
            "buy_product": "köpa {product}",
            "product_reviews": "jämför {product}",
        },
        "de": {
            "alternatives": f"{brand_name} Alternativen",
            "vs": f"{brand_name} vs",
            "competitors": f"{brand_name} Konkurrenten",
            "best_alternatives": f"beste {brand_name} Alternativen",
            "industry_products": "beste {industry} Produkte",
            "buy_product": "{product} kaufen",
            "product_reviews": "{product} Vergleich",
        },
        "no": {
            "alternatives": f"{brand_name} alternativer",
            "vs": f"{brand_name} vs",
            "competitors": f"{brand_name} konkurrenter",
            "best_alternatives": f"beste alternativ til {brand_name}",
            "industry_products": "beste {industry} produkter Norge",
            "buy_product": "kjøp {product}",
            "product_reviews": "sammenlign {product}",
        },
        "da": {
            "alternatives": f"{brand_name} alternativer",
            "vs": f"{brand_name} vs",
            "competitors": f"{brand_name} konkurrenter",
            "best_alternatives": f"bedste alternativ til {brand_name}",
            "industry_products": "bedste {industry} produkter Danmark",
            "buy_product": "køb {product}",
            "product_reviews": "sammenlign {product}",
        },
        "fi": {
            "alternatives": f"{brand_name} vaihtoehtoja",
            "vs": f"{brand_name} vs",
            "competitors": f"{brand_name} kilpailijat",
            "best_alternatives": f"parhaat {brand_name} vaihtoehdot",
            "industry_products": "parhaat {industry} tuotteet Suomi",
            "buy_product": "osta {product}",
            "product_reviews": "vertaile {product}",
        },
    }

    # Get templates for the language, fallback to English
    templates = QUERY_TEMPLATES.get(language, QUERY_TEMPLATES["en"])

    # Core brand queries (always include)
    queries.extend([
        {"query": templates["alternatives"], "purpose": "Find direct competitor alternatives"},
        {"query": templates["vs"], "purpose": "Find head-to-head competitors"},
        {"query": templates["competitors"], "purpose": "Find known competitors"},
    ])

    # Industry-specific queries (if industry known)
    if industry:
        # Clean industry for search
        industry_clean = industry.lower().replace("_", " ")
        queries.append({
            "query": templates["industry_products"].format(industry=industry_clean),
            "purpose": f"Find top {industry} products/services"
        })

    # Product-specific queries (if offerings known)
    if offerings:
        # Use top 2 offerings for discovery
        for product in offerings[:2]:
            product_clean = product.lower()
            queries.append({
                "query": templates["buy_product"].format(product=product_clean),
                "purpose": f"Find competitors selling {product}"
            })

    # Add English fallback queries if primary language is not English
    if language != "en":
        en_templates = QUERY_TEMPLATES["en"]
        queries.extend([
            {"query": en_templates["alternatives"], "purpose": "Find global alternatives (English)"},
            {"query": en_templates["competitors"], "purpose": "Find global competitors (English)"},
        ])

    return queries


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
            discovered = await self._discover_from_serp(
                domain=domain,
                market=market,
                website_analysis=website_analysis,
            )
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

        # 4. Classify all competitors using AI (with market context)
        if self.claude_client and website_analysis:
            classifications = await self._classify_competitors(
                domain=domain,
                website_analysis=website_analysis,
                competitors=list(all_competitors.values()),
                market=market,
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
        website_analysis: Optional[WebsiteAnalysis] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover competitors from SERP analysis.

        Uses industry-aware, localized queries based on website analysis.
        """
        discovered = []

        if not self.dataforseo_client:
            return discovered

        # Extract context from website analysis for smarter queries
        brand_name = None
        industry = None
        offerings = None
        language = self._market_to_language(market)

        if website_analysis:
            brand_name = domain.split('.')[0].replace('-', ' ').title()
            industry = website_analysis.business_model.value if website_analysis.business_model else None
            offerings = [o.name for o in website_analysis.offerings[:3]] if website_analysis.offerings else None
            if website_analysis.primary_language and website_analysis.primary_language != "unknown":
                language = website_analysis.primary_language

        # Generate industry-aware, localized queries
        queries = get_discovery_queries(
            domain=domain,
            brand_name=brand_name,
            industry=industry,
            offerings=offerings,
            language=language,
            market=market,
        )

        logger.info(f"SERP discovery using {len(queries)} queries (language={language}, market={market})")

        # Run up to 4 queries for better coverage (was 2)
        for query_info in queries[:4]:
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

    def _get_market_tld_hint(self, domain: str, market: str) -> str:
        """Get market relevance hint based on TLD."""
        # TLDs that indicate specific markets
        market_tlds = {
            "uk": [".co.uk", ".uk"],
            "us": [".com", ".us"],
            "se": [".se"],
            "de": [".de"],
            "fr": [".fr"],
            "no": [".no"],
            "dk": [".dk"],
            "fi": [".fi"],
            "nl": [".nl"],
            "au": [".com.au", ".au"],
            "ca": [".ca"],
        }

        domain_lower = domain.lower()
        target_tlds = market_tlds.get(market.lower(), [])

        # Check if TLD matches target market
        for tld in target_tlds:
            if domain_lower.endswith(tld):
                return f"[LOCAL to {market.upper()}]"

        # Check if TLD suggests a DIFFERENT market
        for other_market, other_tlds in market_tlds.items():
            if other_market != market.lower():
                for tld in other_tlds:
                    if domain_lower.endswith(tld) and tld != ".com":
                        return f"[TLD suggests {other_market.upper()}, not {market.upper()}]"

        # .com is global/neutral
        if domain_lower.endswith(".com"):
            return "[GLOBAL - .com]"

        return ""

    async def _classify_competitors(
        self,
        domain: str,
        website_analysis: WebsiteAnalysis,
        competitors: List[Dict[str, Any]],
        market: str = "us",
    ) -> List[Dict[str, Any]]:
        """Use AI to classify competitors with market context."""
        if not self.claude_client:
            return []

        # Format competitors list for prompt with market hints
        competitors_text = ""
        for i, comp in enumerate(competitors, 1):
            comp_domain = comp.get("domain", "unknown")
            source = comp.get("source", DiscoveryMethod.DATAFORSEO_SUGGESTED)
            metrics = comp.get("metrics", {})

            # Add market relevance hint based on TLD
            market_hint = self._get_market_tld_hint(comp_domain, market)

            competitors_text += f"\n{i}. **{comp_domain}** {market_hint}\n"
            competitors_text += f"   - Source: {source.value if isinstance(source, DiscoveryMethod) else source}\n"

            if metrics:
                traffic = metrics.get("organic_traffic", "N/A")
                keywords = metrics.get("organic_keywords", "N/A")
                competitors_text += f"   - Traffic: {traffic}, Keywords: {keywords}\n"

        # Format offerings
        offerings_text = ", ".join([
            o.name for o in website_analysis.offerings
        ]) if website_analysis.offerings else "Unknown"

        # Convert market code to readable name
        market_names = {
            "us": "United States", "uk": "United Kingdom", "se": "Sweden",
            "de": "Germany", "fr": "France", "no": "Norway", "dk": "Denmark",
            "fi": "Finland", "nl": "Netherlands", "au": "Australia", "ca": "Canada",
        }
        target_market_name = market_names.get(market.lower(), market)

        try:
            prompt = CLASSIFICATION_USER_PROMPT.format(
                domain=domain,
                business_model=website_analysis.business_model.value,
                industry="Unknown",  # TODO: Add industry detection
                offerings=offerings_text,
                target_audience=json.dumps(website_analysis.target_audience),
                competitors_list=competitors_text,
                target_market=target_market_name,
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

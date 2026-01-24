"""
Website Analyzer Agent

Analyzes the target website to understand:
- Business model (B2B SaaS, ecommerce, local service, etc.)
- Company stage (startup, growth, mature)
- Offerings (products, services, pricing)
- Target audience
- Content maturity
- Technical sophistication
- Monetization model

Uses sitemap-first discovery for efficient page finding,
with fallback to localized URL patterns.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from .models import (
    BusinessModel,
    CompanyStage,
    DetectedOffering,
    WebsiteAnalysis,
)
from .sitemap_parser import SitemapParser, SitemapResult

if TYPE_CHECKING:
    from src.analyzer.client import ClaudeClient

logger = logging.getLogger(__name__)


# =============================================================================
# LOCALIZED URL PATTERNS (Fallback when no sitemap)
# =============================================================================

LOCALIZED_PATHS = {
    "about": {
        "en": ["/about", "/about-us", "/company", "/who-we-are"],
        "sv": ["/om-oss", "/om", "/foretaget", "/om-foretaget", "/about"],
        "de": ["/uber-uns", "/ueber-uns", "/unternehmen", "/about"],
        "fr": ["/a-propos", "/qui-sommes-nous", "/about"],
        "no": ["/om-oss", "/om", "/bedrift", "/about"],
        "da": ["/om-os", "/virksomhed", "/om", "/about"],
        "fi": ["/tietoa-meista", "/yritys", "/meista", "/about"],
        "nl": ["/over-ons", "/bedrijf", "/about"],
    },
    "pricing": {
        "en": ["/pricing", "/prices", "/plans", "/packages"],
        "sv": ["/priser", "/prislistor", "/prislista", "/paket", "/pricing"],
        "de": ["/preise", "/preisliste", "/pakete", "/pricing"],
        "fr": ["/tarifs", "/prix", "/forfaits", "/pricing"],
        "no": ["/priser", "/prisliste", "/pakker", "/pricing"],
        "da": ["/priser", "/prisliste", "/pakker", "/pricing"],
        "fi": ["/hinnat", "/hinnasto", "/paketit", "/pricing"],
        "nl": ["/prijzen", "/tarieven", "/pakketten", "/pricing"],
    },
    "products": {
        "en": ["/products", "/services", "/solutions", "/offerings"],
        "sv": ["/produkter", "/tjanster", "/losningar", "/sortiment"],
        "de": ["/produkte", "/dienstleistungen", "/loesungen"],
        "fr": ["/produits", "/services", "/solutions"],
        "no": ["/produkter", "/tjenester", "/losninger"],
        "da": ["/produkter", "/services", "/loesninger"],
        "fi": ["/tuotteet", "/palvelut", "/ratkaisut"],
        "nl": ["/producten", "/diensten", "/oplossingen"],
    },
    "contact": {
        "en": ["/contact", "/contact-us", "/get-in-touch"],
        "sv": ["/kontakt", "/kontakta-oss", "/contact"],
        "de": ["/kontakt", "/kontaktieren-sie-uns", "/contact"],
        "fr": ["/contact", "/contactez-nous"],
        "no": ["/kontakt", "/kontakt-oss", "/contact"],
        "da": ["/kontakt", "/contact"],
        "fi": ["/yhteystiedot", "/ota-yhteytta", "/contact"],
        "nl": ["/contact", "/neem-contact-op"],
    },
}


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================


ANALYSIS_SYSTEM_PROMPT = """You are an expert business analyst. Given website content, you extract structured business intelligence.

Your task is to analyze website content and determine:
1. Business model (what type of business is this?)
2. Company stage (startup, growth, mature?)
3. Products/services offered
4. Target audience
5. Value proposition
6. Content maturity
7. Technical sophistication

Be precise and evidence-based. Only report what you can infer from the content.
If something is unclear, say "unknown" rather than guessing."""


ANALYSIS_USER_PROMPT = """Analyze this website content and extract business intelligence.

## Website: {domain}

## Homepage Content:
{homepage_content}

## About Page Content:
{about_content}

## Pricing Page Content:
{pricing_content}

## Other Signals:
- Has blog: {has_blog}
- Has contact form: {has_contact}
- Has demo/trial form: {has_demo}
- Detected languages: {languages}

---

Return a JSON object with this EXACT structure:
```json
{{
    "business_model": "b2b_saas|b2b_service|b2c_ecommerce|b2c_subscription|marketplace|publisher|local_service|nonprofit|unknown",
    "company_stage": "startup|growth|mature|declining|unknown",
    "offerings": [
        {{
            "name": "Product/Service name",
            "type": "software|service|product|subscription",
            "description": "Brief description",
            "pricing_model": "subscription|one_time|freemium|custom|unknown"
        }}
    ],
    "value_proposition": "One sentence describing their core value",
    "target_audience": {{
        "primary": "Primary customer type",
        "secondary": "Secondary customer type or null",
        "industry_focus": ["industry1", "industry2"] or [],
        "company_size_focus": "startup|smb|enterprise|all" or null
    }},
    "content_maturity": "none|minimal|moderate|extensive",
    "technical_sophistication": "basic|moderate|high",
    "monetization_model": "subscription|one_time|advertising|lead_gen|marketplace_fees|unknown",
    "confidence_score": 0.0 to 1.0
}}
```

Be precise. If you cannot determine something, use "unknown" or null."""


# =============================================================================
# WEBSITE FETCHER
# =============================================================================


class WebsiteFetcher:
    """Fetches and extracts content from websites."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AuthoricyBot/1.0; +https://authoricy.ai)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page and extract text content."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()

            html = response.text
            # Basic HTML to text extraction
            text = self._extract_text(html)
            return text[:15000]  # Limit content size

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.warning(f"Request error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def _extract_text(self, html: str) -> str:
        """Extract readable text from HTML."""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    async def detect_page_features(self, url: str) -> Dict[str, bool]:
        """Detect features on a page (forms, pricing, etc.)."""
        try:
            response = await self.client.get(url)
            html = response.text.lower()

            return {
                "has_contact_form": any(x in html for x in [
                    'type="email"', "contact us", "get in touch", "contact form"
                ]),
                "has_demo_form": any(x in html for x in [
                    "request demo", "book a demo", "schedule demo", "free trial",
                    "start trial", "try for free", "get started free"
                ]),
                "has_pricing": any(x in html for x in [
                    "/pricing", "pricing", "plans", "subscription", "per month",
                    "/month", "$/mo", "€/mo"
                ]),
                "has_blog": any(x in html for x in [
                    "/blog", "/articles", "/news", "/resources", "/insights"
                ]),
                "has_ecommerce": any(x in html for x in [
                    "add to cart", "buy now", "shop now", "checkout",
                    "shopping cart", "product"
                ]),
            }
        except Exception:
            return {
                "has_contact_form": False,
                "has_demo_form": False,
                "has_pricing": False,
                "has_blog": False,
                "has_ecommerce": False,
            }

    async def detect_languages(self, url: str) -> List[str]:
        """Detect languages available on the site."""
        try:
            response = await self.client.get(url)
            html = response.text.lower()

            languages = []

            # Check for language switcher patterns
            lang_patterns = {
                "en": ["/en/", "/en-", "lang=en", "english"],
                "sv": ["/sv/", "/se/", "lang=sv", "svenska", "swedish"],
                "de": ["/de/", "lang=de", "deutsch", "german"],
                "fr": ["/fr/", "lang=fr", "français", "french"],
                "es": ["/es/", "lang=es", "español", "spanish"],
                "no": ["/no/", "lang=no", "norsk", "norwegian"],
                "da": ["/da/", "/dk/", "lang=da", "dansk", "danish"],
                "fi": ["/fi/", "lang=fi", "suomi", "finnish"],
                "nl": ["/nl/", "lang=nl", "nederlands", "dutch"],
                "it": ["/it/", "lang=it", "italiano", "italian"],
            }

            for lang, patterns in lang_patterns.items():
                if any(p in html for p in patterns):
                    languages.append(lang)

            # Check html lang attribute
            lang_match = re.search(r'<html[^>]*lang=["\']([a-z]{2})', html)
            if lang_match:
                detected_lang = lang_match.group(1)
                if detected_lang not in languages:
                    languages.insert(0, detected_lang)

            return languages if languages else ["unknown"]

        except Exception:
            return ["unknown"]


# =============================================================================
# WEBSITE ANALYZER
# =============================================================================


class WebsiteAnalyzer:
    """
    Analyzes a target website to extract business intelligence.

    This is the first step in Context Intelligence - understanding
    what the business actually is before analyzing its SEO.

    Uses sitemap-first discovery for efficient page finding,
    with fallback to localized URL patterns.
    """

    def __init__(self, claude_client: Optional["ClaudeClient"] = None):
        self.claude_client = claude_client
        self.fetcher = WebsiteFetcher()
        self.sitemap_parser = SitemapParser()
        self._sitemap_result: Optional[SitemapResult] = None

    async def analyze(self, domain: str) -> WebsiteAnalysis:
        """
        Analyze a website and extract business intelligence.

        Uses sitemap-first discovery:
        1. Try to fetch and parse sitemap.xml
        2. Extract page URLs from sitemap
        3. Fallback to localized URL guessing if no sitemap

        Args:
            domain: The domain to analyze (e.g., "example.com")

        Returns:
            WebsiteAnalysis with extracted intelligence
        """
        logger.info(f"Analyzing website: {domain}")

        # Ensure domain has protocol
        if not domain.startswith(("http://", "https://")):
            base_url = f"https://{domain}"
        else:
            base_url = domain
            domain = urlparse(domain).netloc

        # Initialize result
        result = WebsiteAnalysis(domain=domain)

        try:
            # Step 1: Discover pages via sitemap (efficient, comprehensive)
            self._sitemap_result = await self.sitemap_parser.parse(base_url)

            if self._sitemap_result.sitemap_found:
                logger.info(
                    f"Sitemap found for {domain}: {self._sitemap_result.total_pages} pages, "
                    f"about={len(self._sitemap_result.about_pages)}, "
                    f"pricing={len(self._sitemap_result.pricing_pages)}, "
                    f"products={len(self._sitemap_result.product_pages)}"
                )

                # Use sitemap data to enrich result
                result.has_blog = self._sitemap_result.has_blog
                result.has_ecommerce = self._sitemap_result.has_shop

                # Use detected languages from sitemap
                if self._sitemap_result.detected_languages:
                    result.detected_languages = list(self._sitemap_result.detected_languages)
                    result.primary_language = result.detected_languages[0]
            else:
                logger.info(f"No sitemap found for {domain}, using URL pattern fallback")

            # Step 2: Fetch key pages content
            homepage_content = await self.fetcher.fetch_page(base_url)

            # Detect primary language from homepage for fallback paths
            if not result.detected_languages or result.detected_languages == ["unknown"]:
                languages = await self.fetcher.detect_languages(base_url)
                result.detected_languages = languages
                result.primary_language = languages[0] if languages else "en"

            # Fetch about and pricing pages using sitemap or fallback
            about_content = await self._fetch_page_smart("about", base_url, result.primary_language)
            pricing_content = await self._fetch_page_smart("pricing", base_url, result.primary_language)

            # Detect additional features from homepage
            features = await self.fetcher.detect_page_features(base_url)
            result.has_blog = result.has_blog or features.get("has_blog", False)
            result.has_pricing_page = bool(pricing_content) or features.get("has_pricing", False)
            result.has_demo_form = features.get("has_demo_form", False)
            result.has_contact_form = features.get("has_contact_form", False)
            result.has_ecommerce = result.has_ecommerce or features.get("has_ecommerce", False)

            # Step 3: AI analysis of content
            if self.claude_client and homepage_content:
                ai_analysis = await self._analyze_with_ai(
                    domain=domain,
                    homepage_content=homepage_content,
                    about_content=about_content,
                    pricing_content=pricing_content,
                    features=features,
                    languages=result.detected_languages,
                    sitemap_insights=self._get_sitemap_insights(),
                )

                if ai_analysis:
                    result = self._merge_ai_analysis(result, ai_analysis)
            else:
                # Fallback to heuristic analysis
                result = self._heuristic_analysis(result, homepage_content or "", features)

        except Exception as e:
            logger.error(f"Error analyzing website {domain}: {e}")
            result.analysis_confidence = 0.1

        finally:
            await self.fetcher.close()
            await self.sitemap_parser.close()

        return result

    async def _fetch_page_smart(
        self,
        page_type: str,
        base_url: str,
        language: str
    ) -> Optional[str]:
        """
        Fetch a page using sitemap first, then fallback to localized paths.

        Args:
            page_type: Type of page ("about", "pricing", "products", "contact")
            base_url: Base URL of the site
            language: Primary language for fallback paths

        Returns:
            Page content or None
        """
        # Strategy 1: Use sitemap URLs if available
        if self._sitemap_result and self._sitemap_result.sitemap_found:
            sitemap_pages = getattr(self._sitemap_result, f"{page_type}_pages", [])
            if sitemap_pages:
                # Try the first matching page from sitemap
                for url in sitemap_pages[:2]:  # Try up to 2 pages
                    content = await self.fetcher.fetch_page(url)
                    if content and len(content) > 200:
                        logger.debug(f"Found {page_type} page from sitemap: {url}")
                        return content

        # Strategy 2: Fallback to localized URL patterns
        localized_paths = LOCALIZED_PATHS.get(page_type, {})

        # Try primary language paths first
        paths_to_try = localized_paths.get(language, [])

        # Add English as fallback if not already primary
        if language != "en":
            paths_to_try = paths_to_try + localized_paths.get("en", [])

        # Deduplicate while preserving order
        seen = set()
        unique_paths = []
        for path in paths_to_try:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)

        for path in unique_paths:
            content = await self.fetcher.fetch_page(f"{base_url}{path}")
            if content and len(content) > 200:
                logger.debug(f"Found {page_type} page from fallback: {path}")
                return content

        return None

    def _get_sitemap_insights(self) -> Dict[str, Any]:
        """Extract insights from sitemap for AI analysis."""
        if not self._sitemap_result or not self._sitemap_result.sitemap_found:
            return {}

        return {
            "total_pages": self._sitemap_result.total_pages,
            "has_blog": self._sitemap_result.has_blog,
            "has_shop": self._sitemap_result.has_shop,
            "has_multilingual": self._sitemap_result.has_multilingual,
            "detected_languages": list(self._sitemap_result.detected_languages),
            "product_page_count": len(self._sitemap_result.product_pages),
            "blog_page_count": len(self._sitemap_result.blog_pages),
            "category_count": len(self._sitemap_result.category_pages),
        }

    async def _analyze_with_ai(
        self,
        domain: str,
        homepage_content: str,
        about_content: Optional[str],
        pricing_content: Optional[str],
        features: Dict[str, bool],
        languages: List[str],
        sitemap_insights: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Use Claude to analyze website content."""
        try:
            # Format sitemap insights for the prompt
            sitemap_info = ""
            if sitemap_insights:
                sitemap_info = f"""
## Sitemap Analysis:
- Total indexed pages: {sitemap_insights.get('total_pages', 'Unknown')}
- Product pages: {sitemap_insights.get('product_page_count', 0)}
- Blog posts: {sitemap_insights.get('blog_page_count', 0)}
- Category pages: {sitemap_insights.get('category_count', 0)}
- Multilingual: {sitemap_insights.get('has_multilingual', False)}
- Detected languages: {', '.join(sitemap_insights.get('detected_languages', []))}
"""

            prompt = ANALYSIS_USER_PROMPT.format(
                domain=domain,
                homepage_content=homepage_content[:8000],
                about_content=(about_content or "Not found")[:4000],
                pricing_content=(pricing_content or "Not found")[:4000],
                has_blog=features.get("has_blog", False),
                has_contact=features.get("has_contact_form", False),
                has_demo=features.get("has_demo_form", False),
                languages=", ".join(languages),
            )

            # Add sitemap insights to the prompt
            if sitemap_info:
                prompt = prompt.replace("## Other Signals:", f"{sitemap_info}\n## Other Signals:")

            response = await self.claude_client.analyze_with_retry(
                prompt=prompt,
                system=ANALYSIS_SYSTEM_PROMPT,
                max_tokens=2000,
                temperature=0.2,
            )

            if response.success:
                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', response.content)
                if json_match:
                    return json.loads(json_match.group())

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI analysis JSON: {e}")
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")

        return None

    def _merge_ai_analysis(
        self,
        result: WebsiteAnalysis,
        ai_analysis: Dict[str, Any],
    ) -> WebsiteAnalysis:
        """Merge AI analysis into the result."""
        # Business model
        business_model_str = ai_analysis.get("business_model", "unknown")
        try:
            result.business_model = BusinessModel(business_model_str)
        except ValueError:
            result.business_model = BusinessModel.UNKNOWN

        # Company stage
        stage_str = ai_analysis.get("company_stage", "unknown")
        try:
            result.company_stage = CompanyStage(stage_str)
        except ValueError:
            result.company_stage = CompanyStage.UNKNOWN

        # Offerings
        offerings_data = ai_analysis.get("offerings", [])
        for offering in offerings_data:
            if isinstance(offering, dict):
                result.offerings.append(DetectedOffering(
                    name=offering.get("name", "Unknown"),
                    type=offering.get("type", "unknown"),
                    description=offering.get("description"),
                    pricing_model=offering.get("pricing_model"),
                    confidence=ai_analysis.get("confidence_score", 0.5),
                ))

        # Value proposition
        result.value_proposition = ai_analysis.get("value_proposition")

        # Target audience
        result.target_audience = ai_analysis.get("target_audience", {})

        # Content maturity
        result.content_maturity = ai_analysis.get("content_maturity", "unknown")

        # Technical sophistication
        result.technical_sophistication = ai_analysis.get("technical_sophistication", "unknown")

        # Monetization
        result.monetization_model = ai_analysis.get("monetization_model")

        # Confidence
        result.analysis_confidence = ai_analysis.get("confidence_score", 0.5)

        return result

    def _heuristic_analysis(
        self,
        result: WebsiteAnalysis,
        content: str,
        features: Dict[str, bool],
    ) -> WebsiteAnalysis:
        """Fallback heuristic analysis when AI is not available."""
        content_lower = content.lower()

        # Detect business model from signals
        if features.get("has_ecommerce"):
            result.business_model = BusinessModel.B2C_ECOMMERCE
        elif features.get("has_demo_form") and features.get("has_pricing"):
            result.business_model = BusinessModel.B2B_SAAS
        elif any(x in content_lower for x in ["local", "near me", "our location"]):
            result.business_model = BusinessModel.LOCAL_SERVICE
        elif features.get("has_blog") and not features.get("has_pricing"):
            result.business_model = BusinessModel.PUBLISHER

        # Detect content maturity
        if features.get("has_blog"):
            result.content_maturity = "moderate"
        else:
            result.content_maturity = "minimal"

        # Low confidence for heuristic analysis
        result.analysis_confidence = 0.3

        return result


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


async def analyze_website(
    domain: str,
    claude_client: Optional["ClaudeClient"] = None,
) -> WebsiteAnalysis:
    """
    Convenience function to analyze a website.

    Args:
        domain: Domain to analyze
        claude_client: Optional Claude client for AI analysis

    Returns:
        WebsiteAnalysis result
    """
    analyzer = WebsiteAnalyzer(claude_client)
    return await analyzer.analyze(domain)

"""
Greenfield Intelligence Service

Orchestrates the greenfield analysis workflow:
1. Domain maturity detection
2. Website context acquisition (Firecrawl)
3. Competitor discovery and curation
4. Keyword collection and winnability scoring
5. Market opportunity calculation
6. Beachhead selection and roadmap generation
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from src.database import repository
from src.database.session import get_db_context
from src.database.models import Domain, AnalysisRun, AnalysisStatus
from src.scoring.greenfield import (
    DomainMaturity,
    DomainMetrics,
    classify_domain_maturity,
    calculate_market_opportunity,
    select_beachhead_keywords,
    project_traffic_scenarios,
)

logger = logging.getLogger(__name__)


# Business context extraction patterns - comprehensive competitor detection
COMPETITOR_PATTERNS = [
    # Direct comparison patterns
    r"compared to (\w+(?:\.\w+)?)",
    r"alternative to (\w+(?:\.\w+)?)",
    r"vs\.?\s+(\w+(?:\.\w+)?)",
    r"versus (\w+(?:\.\w+)?)",
    r"unlike (\w+(?:\.\w+)?)",
    r"better than (\w+(?:\.\w+)?)",
    r"faster than (\w+(?:\.\w+)?)",
    r"cheaper than (\w+(?:\.\w+)?)",
    r"more powerful than (\w+(?:\.\w+)?)",
    # Migration/switching patterns
    r"switch(?:ing)? from (\w+(?:\.\w+)?)",
    r"migrat(?:e|ing) from (\w+(?:\.\w+)?)",
    r"moving from (\w+(?:\.\w+)?)",
    r"replac(?:e|ing) (\w+(?:\.\w+)?)",
    r"instead of (\w+(?:\.\w+)?)",
    # Similar/competitor patterns
    r"(?:similar|like) (\w+(?:\.\w+)?)",
    r"competitors? (?:like|such as|including) (\w+(?:\.\w+)?)",
    r"(?:tools?|products?|solutions?) like (\w+(?:\.\w+)?)",
    # Integration patterns (often mention related tools)
    r"integrates? with (\w+(?:\.\w+)?)",
    r"works? with (\w+(?:\.\w+)?)",
    r"connects? to (\w+(?:\.\w+)?)",
]

# Known competitor brand names to look for (common SaaS/tech brands)
KNOWN_COMPETITOR_BRANDS = {
    "hubspot", "salesforce", "zendesk", "intercom", "drift", "mailchimp",
    "ahrefs", "semrush", "moz", "screaming frog", "majestic",
    "slack", "asana", "monday", "trello", "notion", "clickup", "jira",
    "shopify", "woocommerce", "bigcommerce", "magento", "squarespace", "wix",
    "stripe", "paypal", "square", "braintree",
    "zapier", "make", "automate.io", "integromat", "n8n",
    "datadog", "newrelic", "splunk", "grafana", "prometheus",
    "aws", "azure", "google cloud", "digitalocean", "heroku", "vercel",
    "segment", "amplitude", "mixpanel", "heap", "fullstory", "hotjar",
    "figma", "sketch", "adobe xd", "invision", "canva",
    "github", "gitlab", "bitbucket", "sourcegraph",
}

PRICE_PATTERNS = [
    r"\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:/|per)?\s*(?:mo|month|monthly)",
    r"(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|EUR|GBP)\s*(?:/|per)?\s*(?:mo|month|monthly)",
    r"starting at \$?(\d+)",
]

# Common TLDs for domain validation
VALID_TLDS = {
    "com", "io", "co", "ai", "app", "dev", "org", "net", "edu", "gov",
    "us", "uk", "de", "fr", "ca", "au", "in", "jp", "cn", "br",
}


class GreenfieldService:
    """Service for greenfield analysis operations."""

    def __init__(
        self,
        dataforseo_client=None,
        perplexity_client=None,
        firecrawl_client=None,
        external_api_clients=None,
    ):
        """
        Initialize greenfield service.

        Args:
            dataforseo_client: Optional DataForSEO client for API calls
            perplexity_client: Optional PerplexityClient for AI discovery
            firecrawl_client: Optional FirecrawlClient for website scraping
            external_api_clients: Optional ExternalAPIClients (provides both)
        """
        self.client = dataforseo_client

        # External API clients for enhanced competitor discovery
        if external_api_clients:
            self.perplexity_client = external_api_clients.perplexity
            self.firecrawl_client = external_api_clients.firecrawl
        else:
            self.perplexity_client = perplexity_client
            self.firecrawl_client = firecrawl_client

    async def check_domain_maturity(self, domain: str) -> Dict[str, Any]:
        """
        Check domain maturity to determine analysis mode.

        Returns domain metrics and maturity classification.
        """
        metrics = DomainMetrics(
            domain_rating=0,
            organic_keywords=0,
            organic_traffic=0,
            referring_domains=0,
        )

        # Fetch real metrics if client available
        if self.client:
            try:
                overview = await self.client.get_domain_overview(domain=domain)

                # Domain Rating (DR) comes from backlinks/summary API, NOT domain_overview
                # The domain_rank_overview API returns pos_1 (keywords in position 1), not DR
                backlink_summary = await self.client.get_backlink_summary(domain=domain)
                domain_rating = backlink_summary.get("domain_rank", 0) if backlink_summary else 0

                metrics = DomainMetrics(
                    domain_rating=domain_rating,
                    organic_keywords=overview.get("organic_keywords", 0),
                    organic_traffic=overview.get("organic_traffic", 0),
                    referring_domains=backlink_summary.get("referring_domains", 0) if backlink_summary else 0,
                )
            except Exception as e:
                logger.warning(f"Failed to fetch domain metrics for {domain}: {e}")

        maturity = classify_domain_maturity(metrics)

        return {
            "domain": domain,
            "maturity": maturity.value,
            "domain_rating": metrics.domain_rating,
            "organic_keywords": metrics.organic_keywords,
            "organic_traffic": metrics.organic_traffic,
            "referring_domains": metrics.referring_domains,
            "requires_greenfield": maturity == DomainMaturity.GREENFIELD,
            "message": self._get_maturity_message(maturity),
        }

    def _get_maturity_message(self, maturity: DomainMaturity) -> str:
        """Get user-friendly message for maturity level."""
        messages = {
            DomainMaturity.GREENFIELD: (
                "Your domain has limited SEO data. We'll use competitor-first analysis "
                "to identify market opportunities and beachhead keywords."
            ),
            DomainMaturity.EMERGING: (
                "Your domain has some SEO data. We'll combine your existing data "
                "with competitor analysis for a comprehensive view."
            ),
            DomainMaturity.ESTABLISHED: (
                "Your domain has established SEO data. We'll perform standard "
                "analysis with competitive benchmarking."
            ),
        }
        return messages.get(maturity, "Unknown maturity level.")

    async def acquire_website_context(
        self,
        domain: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Acquire business context by scraping target domain with Firecrawl.

        This is Phase 1 of competitor intelligence - understanding what the
        target business does before finding competitors.

        Args:
            domain: Domain to scrape
            user_context: User-provided context to enhance

        Returns:
            Enhanced business context with scraped data
        """
        context = user_context.copy() if user_context else {}

        if not self.firecrawl_client:
            logger.info("Firecrawl not configured, using user-provided context only")
            return context

        try:
            from src.integrations.firecrawl import WebsiteScraper

            scraper = WebsiteScraper(client=self.firecrawl_client)

            logger.info(f"Scraping website context from {domain}")

            # Scrape key business pages
            scraped_data = await scraper.scrape_business_pages(
                domain=domain,
                max_pages=8,
            )

            # Extract insights from scraped content
            scraped_insights = self._extract_context_from_scraped(scraped_data)

            # Merge with user context (user context takes priority)
            enhanced_context = self._merge_contexts(scraped_insights, context)

            # Update session with website context
            logger.info(
                f"Acquired website context from {domain}: "
                f"{scraped_data['success_count']}/{scraped_data['total_pages']} pages scraped"
            )

            return enhanced_context

        except Exception as e:
            logger.warning(f"Website context acquisition failed for {domain}: {e}")
            return context

    def _extract_context_from_scraped(
        self,
        scraped_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract structured business context from scraped website data.

        Analyzes homepage, about, pricing, and product pages to understand:
        - What the company does
        - Who they serve
        - Pricing model
        - Competitors they mention
        """
        context = {
            "scraped_from_website": True,
            "scraped_pages": scraped_data.get("success_count", 0),
        }

        combined_content = scraped_data.get("combined_content", "").lower()
        pages = scraped_data.get("pages", {})

        # Extract from homepage metadata
        homepage = pages.get("/", {})
        if homepage.get("title"):
            context["detected_title"] = homepage["title"]
        if homepage.get("description"):
            context["detected_description"] = homepage["description"]

        # Extract business description from about page
        about_page = pages.get("/about", {}) or pages.get("/about-us", {})
        if about_page.get("content"):
            # Get first meaningful paragraph (skip headers)
            about_content = about_page["content"][:2000]
            context["detected_about"] = about_content

        # Extract pricing information
        pricing_page = pages.get("/pricing", {})
        if pricing_page.get("content"):
            pricing_content = pricing_page["content"]
            prices_found = []
            for pattern in PRICE_PATTERNS:
                matches = re.findall(pattern, pricing_content, re.IGNORECASE)
                prices_found.extend(matches)

            if prices_found:
                context["detected_prices"] = prices_found[:5]

            # Detect pricing model
            pricing_lower = pricing_content.lower()
            if "free" in pricing_lower and ("trial" in pricing_lower or "tier" in pricing_lower):
                context["detected_pricing_model"] = "freemium"
            elif "per user" in pricing_lower or "per seat" in pricing_lower:
                context["detected_pricing_model"] = "per_seat"
            elif "usage" in pricing_lower or "pay as you go" in pricing_lower:
                context["detected_pricing_model"] = "usage_based"
            elif "monthly" in pricing_lower or "annual" in pricing_lower:
                context["detected_pricing_model"] = "subscription"

        # Extract mentioned competitors from all content
        mentioned_competitors = set()

        # Method 1: Pattern-based extraction (e.g., "compared to X", "vs X")
        for pattern in COMPETITOR_PATTERNS:
            matches = re.findall(pattern, combined_content, re.IGNORECASE)
            for match in matches:
                comp = match.strip().lower()
                if self._is_valid_competitor_name(comp):
                    mentioned_competitors.add(comp)

        # Method 2: Known brand detection (direct mentions of known competitors)
        for brand in KNOWN_COMPETITOR_BRANDS:
            # Look for brand mentions with word boundaries
            if re.search(rf"\b{re.escape(brand)}\b", combined_content):
                mentioned_competitors.add(brand)

        # Method 3: Extract explicit domain mentions (e.g., "ahrefs.com")
        domain_pattern = r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(?:com|io|co|ai|app|org|net))\b"
        domain_matches = re.findall(domain_pattern, combined_content)
        for domain in domain_matches:
            # Filter out generic domains
            if domain not in {"example.com", "domain.com", "yoursite.com", "website.com"}:
                mentioned_competitors.add(domain)

        if mentioned_competitors:
            # Sort by length (longer = more specific = higher quality)
            sorted_competitors = sorted(mentioned_competitors, key=len, reverse=True)
            context["self_mentioned_competitors"] = sorted_competitors[:15]
            logger.info(f"Extracted {len(sorted_competitors)} competitor mentions from website")

        # Detect business model indicators
        if "saas" in combined_content or "software as a service" in combined_content:
            context["detected_business_model"] = "saas"
        elif "ecommerce" in combined_content or "e-commerce" in combined_content or "shop" in combined_content:
            context["detected_business_model"] = "ecommerce"
        elif "marketplace" in combined_content:
            context["detected_business_model"] = "marketplace"
        elif "agency" in combined_content or "consulting" in combined_content:
            context["detected_business_model"] = "services"

        # Detect target audience
        if "enterprise" in combined_content:
            context["detected_target_size"] = "enterprise"
        elif "small business" in combined_content or "smb" in combined_content:
            context["detected_target_size"] = "smb"
        elif "startup" in combined_content:
            context["detected_target_size"] = "startup"

        if "b2b" in combined_content:
            context["detected_customer_type"] = "b2b"
        elif "b2c" in combined_content or "consumer" in combined_content:
            context["detected_customer_type"] = "b2c"

        # Extract features from features page
        features_page = pages.get("/features", {}) or pages.get("/product", {})
        if features_page.get("content"):
            context["has_features_page"] = True

        return context

    def _merge_contexts(
        self,
        scraped_context: Dict[str, Any],
        user_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge scraped context with user-provided context.

        User-provided values always take priority. Scraped values fill in gaps.
        """
        merged = scraped_context.copy()

        # User context overrides scraped
        for key, value in user_context.items():
            if value:  # Only override if user provided a non-empty value
                merged[key] = value

        # Add scraped competitors to known_competitors if not duplicated
        if "self_mentioned_competitors" in scraped_context:
            user_competitors = set(
                c.lower() for c in user_context.get("known_competitors", [])
            )
            scraped_competitors = scraped_context["self_mentioned_competitors"]

            new_competitors = [
                c for c in scraped_competitors
                if c.lower() not in user_competitors
            ]

            if new_competitors:
                merged["website_discovered_competitors"] = new_competitors
                logger.info(
                    f"Found {len(new_competitors)} competitors mentioned on website: "
                    f"{new_competitors}"
                )

        return merged

    def _is_valid_competitor_name(self, name: str) -> bool:
        """
        Validate if extracted text is likely a valid competitor name.

        Filters out common false positives like generic words.
        """
        if not name or len(name) < 3:
            return False

        # Filter out generic/stop words that often get matched
        stop_words = {
            "the", "and", "for", "with", "your", "our", "this", "that",
            "from", "into", "than", "other", "more", "less", "most",
            "best", "top", "new", "old", "big", "small", "fast", "slow",
            "free", "paid", "premium", "basic", "pro", "plus", "lite",
            "software", "platform", "tool", "service", "solution", "app",
            "data", "cloud", "web", "api", "system", "product", "company",
            "team", "user", "customer", "client", "business", "enterprise",
        }

        name_lower = name.lower()
        if name_lower in stop_words:
            return False

        # If it looks like a domain, validate the TLD
        if "." in name:
            parts = name.split(".")
            tld = parts[-1].lower()
            if tld in VALID_TLDS:
                return True
            # Unknown TLD but has domain-like structure
            return len(parts) == 2 and len(parts[0]) >= 2

        # Brand name (no dot) - must be substantial
        # Known brands are always valid
        if name_lower in KNOWN_COMPETITOR_BRANDS:
            return True

        # Unknown brand - be stricter (min 4 chars, no numbers only)
        if len(name) >= 4 and not name.isdigit():
            return True

        return False

    def start_greenfield_analysis(
        self,
        domain: str,
        greenfield_context: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> Tuple[UUID, UUID]:
        """
        Start a greenfield analysis.

        Creates analysis run and competitor intelligence session.

        Args:
            domain: Domain to analyze
            greenfield_context: User-provided business context
            user_id: Optional user ID to associate with the domain

        Returns:
            Tuple of (analysis_run_id, session_id)
        """
        # Create analysis run
        analysis_run_id = repository.create_greenfield_analysis_run(
            domain=domain,
            greenfield_context=greenfield_context,
            config={"mode": "greenfield"},
            user_id=user_id,
        )

        # Get domain ID
        with get_db_context() as db:
            domain_obj = db.query(Domain).filter(Domain.domain == domain).first()
            domain_id = domain_obj.id if domain_obj else None

        if not domain_id:
            raise ValueError(f"Domain not found: {domain}")

        # Create competitor session
        session_id = repository.create_competitor_intelligence_session(
            analysis_run_id=analysis_run_id,
            domain_id=domain_id,
            user_provided_competitors=greenfield_context.get("known_competitors", []),
        )

        logger.info(
            f"Started greenfield analysis for {domain}: "
            f"run_id={analysis_run_id}, session_id={session_id}"
        )

        return analysis_run_id, session_id

    def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get competitor intelligence session."""
        session = repository.get_competitor_session(session_id)
        if not session:
            return None

        # Calculate curation requirements
        candidates = session.get("candidate_competitors", [])
        required_removals = max(0, len(candidates) - 10)

        return {
            **session,
            # Frontend expects "candidates" not "candidate_competitors"
            "candidates": candidates,
            "candidates_count": len(candidates),
            "required_removals": required_removals,
            "min_final_count": 8,
            "max_final_count": 10,
        }

    async def discover_competitors(
        self,
        session_id: UUID,
        seed_keywords: List[str],
        known_competitors: List[str],
        market: str = "us",
        business_context: Optional[Dict[str, Any]] = None,
        target_domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Discover competitors for a session.

        Aggregates competitors from multiple sources and updates session.
        Sources:
        1. Website scraping (Firecrawl) - discovers competitors mentioned on target site
        2. User-provided competitors
        3. Perplexity AI discovery (intelligent, context-aware)
        4. SERP analysis for seed keywords

        Args:
            session_id: Competitor intelligence session ID
            seed_keywords: Keywords to use for SERP discovery
            known_competitors: User-provided competitor domains
            market: Target market (default: us)
            business_context: User-provided business context
            target_domain: Target domain to scrape for additional context
        """
        candidates = []
        seen_domains = set()

        # Phase 1: Website Context Acquisition (Firecrawl)
        enhanced_context = business_context or {}
        if target_domain and self.firecrawl_client:
            logger.info(f"Phase 1: Acquiring website context from {target_domain}")
            enhanced_context = await self.acquire_website_context(
                domain=target_domain,
                user_context=business_context,
            )

            # Add website-discovered competitors
            website_competitors = enhanced_context.get("website_discovered_competitors", [])
            for comp_domain in website_competitors:
                comp_domain = comp_domain.lower().strip()
                if comp_domain and comp_domain not in seen_domains:
                    candidates.append({
                        "domain": comp_domain,
                        "discovery_source": "website_scrape",
                        "discovery_reason": f"Mentioned on {target_domain}'s website",
                        "domain_rating": 0,
                        "organic_traffic": 0,
                        "organic_keywords": 0,
                        "relevance_score": 0.85,
                        "suggested_purpose": "benchmark_peer",
                    })
                    seen_domains.add(comp_domain)

            if website_competitors:
                logger.info(f"Website scrape discovered {len(website_competitors)} competitors")

        # Phase 2: Add user-provided competitors
        for domain in known_competitors:
            domain = domain.lower().strip()
            if domain and domain not in seen_domains:
                candidates.append({
                    "domain": domain,
                    "discovery_source": "user_provided",
                    "discovery_reason": "User-provided competitor",
                    "domain_rating": 0,
                    "organic_traffic": 0,
                    "organic_keywords": 0,
                    "relevance_score": 0.9,
                    "suggested_purpose": "benchmark_peer",
                })
                seen_domains.add(domain)

        # Phase 3: Discover from Perplexity AI (intelligent, context-aware discovery)
        if self.perplexity_client and enhanced_context:
            try:
                logger.info("Starting Perplexity AI competitor discovery...")
                perplexity_competitors = await self._discover_from_perplexity(
                    business_context=enhanced_context,
                )
                for comp in perplexity_competitors:
                    domain = comp.get("domain", "").lower()
                    if domain and domain not in seen_domains:
                        candidates.append(comp)
                        seen_domains.add(domain)
                logger.info(f"Perplexity discovered {len(perplexity_competitors)} candidates")
            except Exception as e:
                logger.error(f"Perplexity discovery FAILED: {e}", exc_info=True)
        else:
            if not self.perplexity_client:
                logger.error(
                    "PERPLEXITY DISCOVERY DISABLED: No Perplexity client configured! "
                    "Set PERPLEXITY_API_KEY environment variable to enable AI-powered competitor discovery."
                )
            elif not enhanced_context:
                logger.warning("PERPLEXITY DISCOVERY SKIPPED: No business context provided")

        # Phase 4: Discover from SERPs if DataForSEO client available
        if self.client and seed_keywords:
            try:
                logger.info("Starting SERP-based competitor discovery...")
                serp_competitors = await self._discover_from_serps(
                    seed_keywords[:5],
                    market,
                )
                for comp in serp_competitors:
                    domain = comp.get("domain", "").lower()
                    if domain and domain not in seen_domains:
                        candidates.append(comp)
                        seen_domains.add(domain)
                logger.info(f"SERP analysis discovered {len(serp_competitors)} candidates")
            except Exception as e:
                logger.error(f"SERP discovery FAILED: {e}", exc_info=True)
        else:
            if not self.client:
                logger.error(
                    "SERP DISCOVERY DISABLED: No DataForSEO client configured! "
                    "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD environment variables."
                )
            elif not seed_keywords:
                logger.warning("SERP DISCOVERY SKIPPED: No seed keywords provided")

        # Deduplicate
        seen = set()
        unique_candidates = []
        for c in candidates:
            domain = c.get("domain", "").lower()
            if domain and domain not in seen:
                seen.add(domain)
                unique_candidates.append(c)

        # Phase 5: Validate and enrich with metrics
        if self.client:
            unique_candidates = await self._enrich_candidates(unique_candidates, market)

        # Prepare website context for storage (only relevant fields)
        website_context_to_store = None
        if enhanced_context.get("scraped_from_website"):
            website_context_to_store = {
                "scraped_pages": enhanced_context.get("scraped_pages", 0),
                "detected_title": enhanced_context.get("detected_title"),
                "detected_description": enhanced_context.get("detected_description"),
                "detected_about": enhanced_context.get("detected_about"),
                "detected_pricing_model": enhanced_context.get("detected_pricing_model"),
                "detected_business_model": enhanced_context.get("detected_business_model"),
                "detected_target_size": enhanced_context.get("detected_target_size"),
                "detected_customer_type": enhanced_context.get("detected_customer_type"),
                "self_mentioned_competitors": enhanced_context.get("self_mentioned_competitors", []),
                "has_features_page": enhanced_context.get("has_features_page", False),
            }

        # Update session with candidates and website context
        repository.update_session_candidates(
            session_id,
            unique_candidates,
            website_context=website_context_to_store,
        )

        # Log discovery summary
        logger.info(
            f"Competitor discovery complete: {len(unique_candidates)} total candidates "
            f"(website: {len(enhanced_context.get('website_discovered_competitors', []))}, "
            f"user: {len(known_competitors)}, AI+SERP: remaining)"
        )

        return {
            "session_id": str(session_id),
            "status": "awaiting_curation",
            "candidates": unique_candidates,
            "candidates_count": len(unique_candidates),
            "required_removals": max(0, len(unique_candidates) - 10),
            "website_context_acquired": enhanced_context.get("scraped_from_website", False),
            "pages_scraped": enhanced_context.get("scraped_pages", 0),
        }

    async def _discover_from_serps(
        self,
        seed_keywords: List[str],
        market: str,
    ) -> List[Dict[str, Any]]:
        """Discover competitors from SERP analysis."""
        competitors = []
        domain_counts = {}

        for keyword in seed_keywords:
            try:
                serp_results = await self.client.get_serp_results(
                    keyword=keyword,
                    location=market,
                    depth=10,
                )

                for result in serp_results.get("items", []):
                    domain = result.get("domain", "")
                    if domain:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1

            except Exception as e:
                logger.warning(f"SERP analysis for '{keyword}' failed: {e}")

        # Convert to candidates (domains appearing 2+ times)
        for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
            if count >= 2:
                competitors.append({
                    "domain": domain,
                    "discovery_source": "serp",
                    "discovery_reason": f"Ranks for {count} of your seed keywords",
                    "relevance_score": min(0.95, 0.5 + count * 0.1),
                    "suggested_purpose": "keyword_source",
                })

        return competitors[:15]

    async def _discover_from_perplexity(
        self,
        business_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Discover competitors using Perplexity AI search.

        Perplexity provides intelligent, context-aware competitor discovery
        that can find competitors DataForSEO might miss.
        """
        from src.integrations.perplexity import PerplexityDiscovery

        # Create discovery instance if needed
        if hasattr(self.perplexity_client, 'discover_competitors'):
            discovery = self.perplexity_client
        else:
            discovery = PerplexityDiscovery(self.perplexity_client)

        # Extract context fields with better defaults
        company_name = business_context.get("business_name", "the company")
        category = business_context.get("industry_vertical") or business_context.get("primary_offering", "software")
        offering = business_context.get("business_description") or business_context.get("primary_offering", category)
        customer_type = business_context.get("target_audience") or "B2B companies"
        seed_keywords = business_context.get("seed_keywords", [])

        # Log context for debugging
        logger.info(
            f"Perplexity discovery context: company='{company_name}', "
            f"category='{category}', offering='{offering[:50] if offering else None}...', "
            f"customer='{customer_type}', keywords={seed_keywords[:5] if seed_keywords else []}"
        )

        if not seed_keywords:
            logger.warning("No seed_keywords provided for Perplexity discovery - results may be poor")

        # Run discovery with full context
        discovered = await discovery.discover_competitors(
            company_name=company_name,
            category=category,
            offering=offering,
            customer_type=customer_type,
            seed_keywords=seed_keywords,
        )

        logger.info(f"Perplexity discovered {len(discovered)} unique competitors")

        # Convert to dict format - track how many have domains
        competitors = []
        without_domain = 0
        for disc in discovered:
            if disc.domain:
                competitors.append({
                    "domain": disc.domain,
                    "discovery_source": disc.discovery_source,
                    "discovery_reason": disc.discovery_reason or f"AI discovery: {disc.name}",
                    "domain_rating": 0,  # Will be enriched later
                    "organic_traffic": 0,
                    "organic_keywords": 0,
                    "relevance_score": disc.confidence,
                    "suggested_purpose": "keyword_source",
                })
            else:
                without_domain += 1
                logger.debug(f"Competitor '{disc.name}' has no domain - skipped")

        if without_domain > 0:
            logger.warning(
                f"Perplexity: {without_domain}/{len(discovered)} competitors had no domain and were skipped. "
                f"Only {len(competitors)} competitors with domains will be used."
            )

        return competitors

    async def _enrich_candidates(
        self,
        candidates: List[Dict[str, Any]],
        market: str,
    ) -> List[Dict[str, Any]]:
        """Enrich candidates with domain metrics."""
        for candidate in candidates:
            try:
                overview = await self.client.get_domain_overview(
                    domain=candidate["domain"],
                    location=market,
                )

                # Domain Rating (DR) comes from backlinks/summary API, NOT domain_overview
                # The domain_rank_overview API returns pos_1 (keywords in position 1), not DR
                backlink_summary = await self.client.get_backlink_summary(domain=candidate["domain"])

                candidate["domain_rating"] = backlink_summary.get("domain_rank", 0) if backlink_summary else 0
                candidate["organic_traffic"] = overview.get("organic_traffic", 0)
                candidate["organic_keywords"] = overview.get("organic_keywords", 0)
                candidate["referring_domains"] = backlink_summary.get("referring_domains", 0) if backlink_summary else 0

            except Exception as e:
                logger.warning(f"Failed to enrich {candidate['domain']}: {e}")

        return candidates

    def submit_curation(
        self,
        session_id: UUID,
        removals: List[Dict[str, Any]],
        additions: List[Dict[str, Any]],
        purpose_overrides: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Submit curation decisions and finalize competitor set.

        Validates curation and returns final competitor set.
        """
        session = repository.get_competitor_session(session_id)
        if not session:
            return None

        candidates = session.get("candidate_competitors", [])
        required_removals = max(0, len(candidates) - 10)

        # Validate removal count
        if len(removals) < required_removals:
            raise ValueError(
                f"Must remove at least {required_removals} competitors "
                f"(removed {len(removals)})"
            )

        # Validate final count
        final_count = len(candidates) - len(removals) + len(additions)
        if final_count < 8 or final_count > 10:
            raise ValueError(
                f"Final competitor count must be 8-10 (got {final_count})"
            )

        return repository.submit_curation(
            session_id=session_id,
            removals=removals,
            additions=additions,
            purpose_overrides=purpose_overrides,
        )

    def update_competitors(
        self,
        session_id: UUID,
        removals: List[Dict[str, Any]] = None,
        additions: List[Dict[str, Any]] = None,
        purpose_overrides: List[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update competitors after initial curation."""
        return repository.update_competitors_post_curation(
            session_id=session_id,
            removals=removals,
            additions=additions,
            purpose_overrides=purpose_overrides,
        )

    def get_dashboard(self, analysis_run_id: UUID) -> Optional[Dict[str, Any]]:
        """Get complete greenfield dashboard data."""
        return repository.get_greenfield_dashboard(analysis_run_id)

    def get_beachheads(
        self,
        analysis_run_id: UUID,
        phase: Optional[int] = None,
        min_winnability: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Get beachhead keywords with optional filters."""
        return repository.get_beachhead_keywords(
            analysis_run_id=analysis_run_id,
            phase=phase,
            min_winnability=min_winnability,
        )

    def update_keyword_phase(self, keyword_id: UUID, phase: int) -> bool:
        """Update keyword growth phase assignment."""
        if phase not in [1, 2, 3]:
            raise ValueError("Phase must be 1, 2, or 3")
        return repository.update_keyword_phase(keyword_id, phase)

    def save_analysis_results(
        self,
        analysis_run_id: UUID,
        domain_id: UUID,
        market_opportunity: Dict[str, Any],
        beachhead_keywords: List[Dict[str, Any]],
        projections: Dict[str, Any],
        growth_roadmap: List[Dict[str, Any]],
    ) -> UUID:
        """
        Save complete greenfield analysis results.

        Returns the greenfield analysis ID.
        """
        # Save beachhead keywords
        beachhead_count = repository.save_beachhead_keywords(
            analysis_run_id=analysis_run_id,
            beachhead_keywords=beachhead_keywords,
        )

        # Calculate summary
        beachhead_summary = {
            "count": len(beachhead_keywords),
            "total_volume": sum(bh.get("search_volume", 0) for bh in beachhead_keywords),
            "avg_winnability": (
                sum(bh.get("winnability_score", 0) for bh in beachhead_keywords) / len(beachhead_keywords)
                if beachhead_keywords else 0
            ),
            "keywords": beachhead_keywords[:20],
        }

        # Save greenfield analysis
        analysis_id = repository.save_greenfield_analysis(
            analysis_run_id=analysis_run_id,
            domain_id=domain_id,
            market_opportunity=market_opportunity,
            beachhead_summary=beachhead_summary,
            projections=projections,
            growth_roadmap=growth_roadmap,
        )

        # Update analysis run status
        repository.update_run_status(
            run_id=analysis_run_id,
            status=AnalysisStatus.COMPLETED,
            progress=100,
        )

        logger.info(
            f"Saved greenfield analysis results: "
            f"analysis_id={analysis_id}, beachheads={beachhead_count}"
        )

        return analysis_id

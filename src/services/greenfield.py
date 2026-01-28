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
from typing import Any, Dict, List, Optional, Tuple, Union
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
from src.utils.domain_filter import is_excluded_domain, get_exclusion_reason

logger = logging.getLogger(__name__)


# IMPORTANT: Firecrawl is used ONLY for business context extraction, NOT competitor discovery.
# Competitors should come from: User input, Perplexity AI, and SERP analysis.
# Scraping the target's own website will only find tools they USE, not competitors.

# These are NON-COMPETITOR tools/services that should be EXCLUDED if found
# (payment processors, infrastructure, analytics, etc.)
NON_COMPETITOR_TOOLS = {
    # Payment/Financial
    "stripe", "paypal", "square", "braintree", "plaid", "wise",
    # Infrastructure/Hosting
    "aws", "azure", "google cloud", "digitalocean", "heroku", "vercel",
    "cloudflare", "fastly", "netlify", "railway",
    # Analytics/Monitoring
    "segment", "amplitude", "mixpanel", "heap", "fullstory", "hotjar",
    "datadog", "newrelic", "splunk", "grafana", "prometheus", "sentry",
    "google analytics", "plausible",
    # Dev Tools
    "github", "gitlab", "bitbucket", "sourcegraph", "linear", "jira",
    # Communication/Scheduling
    "slack", "discord", "intercom", "zendesk", "calendly", "cal.com",
    "cal", "zoom", "loom", "crisp",
    # Automation/Integration
    "zapier", "make", "automate.io", "integromat", "n8n", "pipedream",
    # Auth/Identity
    "auth0", "okta", "clerk", "supabase",
    # Email
    "sendgrid", "mailgun", "postmark", "mailchimp", "convertkit",
    # Storage/CDN
    "cloudinary", "imgix", "uploadthing",
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

        # NOTE: We do NOT extract "competitors" from the target's website.
        # Scraping your own site finds TOOLS you use (Stripe, Cal.com, Cloudflare), NOT competitors.
        # Competitors should come from: Perplexity AI, SERP analysis, and user input.

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
        Merge scraped BUSINESS context with user-provided context.

        User-provided values always take priority. Scraped values fill in gaps.
        NOTE: We do NOT merge "competitors" from website scraping - only business context.
        """
        merged = scraped_context.copy()

        # User context overrides scraped
        for key, value in user_context.items():
            if value:  # Only override if user provided a non-empty value
                merged[key] = value

        return merged

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
        """Get competitor intelligence session with tiered data."""
        session = repository.get_competitor_session(session_id)
        if not session:
            return None

        # Calculate curation guidance based on tiers
        candidates = session.get("candidate_competitors", [])
        benchmarks = session.get("benchmarks", [])
        keyword_sources = session.get("keyword_sources", [])
        market_intel = session.get("market_intel", [])
        rejected = session.get("rejected", [])

        total_presented = len(benchmarks) + len(keyword_sources) + len(market_intel)

        # Generate summary message
        if total_presented > 0:
            summary_message = (
                f"Found {len(benchmarks) + len(keyword_sources) + len(market_intel) + len(rejected)} competitors. "
                f"Auto-filtered {len(rejected)} (platforms, tools, irrelevant). "
                f"Presenting {total_presented} ranked by strategic value: "
                f"{len(benchmarks)} benchmarks, {len(keyword_sources)} keyword sources, "
                f"{len(market_intel)} market intelligence."
            )
        else:
            summary_message = f"Found {len(candidates)} candidates for review."

        return {
            **session,
            # Frontend expects "candidates" for backward compatibility
            "candidates": candidates,
            "candidates_count": len(candidates),
            # New tiered curation guidance
            "tier_counts": {
                "benchmarks": len(benchmarks),
                "keyword_sources": len(keyword_sources),
                "market_intel": len(market_intel),
                "rejected": len(rejected),
            },
            "tier_limits": {
                "max_benchmarks": 5,
                "max_keyword_sources": 15,
                "max_market_intel": 15,
            },
            "curation_guidance": {
                "total_presented": total_presented,
                "summary_message": summary_message,
                "instructions": (
                    "Review our tiered recommendations. Benchmarks are your closest competitors "
                    "for gap analysis. Keyword sources are where to mine opportunities. "
                    "Adjust tiers or remove competitors as needed, then confirm."
                ),
            },
            # Legacy fields for backward compatibility
            "required_removals": 0,  # No longer required with auto-curation
            "min_final_count": 8,
            "max_final_count": 35,  # Total across all tiers
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
        # NOTE: Firecrawl is ONLY used to extract BUSINESS CONTEXT (what the company does),
        # NOT to discover competitors. Scraping your own website finds tools you USE
        # (Stripe, Cal.com, Cloudflare), not your competitors.
        enhanced_context = business_context or {}
        if target_domain and self.firecrawl_client:
            logger.info(f"Phase 1: Acquiring website context from {target_domain}")
            enhanced_context = await self.acquire_website_context(
                domain=target_domain,
                user_context=business_context,
            )
            logger.info(f"Website context acquired: {enhanced_context.get('scraped_pages', 0)} pages scraped")

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

        # Phase 5: Use DataForSEO Competitors API if we have user-provided competitors
        if self.client and known_competitors:
            try:
                logger.info("Starting DataForSEO competitors API discovery...")
                for known_comp in known_competitors[:3]:  # Check first 3 user competitors
                    api_competitors = await self.client.get_domain_competitors(
                        domain=known_comp,
                        limit=10,
                    )
                    if api_competitors:
                        for comp in api_competitors:
                            domain = comp.get("domain", "").lower()
                            if domain and domain not in seen_domains:
                                candidates.append({
                                    "domain": domain,
                                    "discovery_source": "dataforseo_competitors",
                                    "discovery_reason": f"Competes with {known_comp} for keywords",
                                    "domain_rating": 0,
                                    "organic_traffic": comp.get("organic_traffic", 0),
                                    "organic_keywords": comp.get("organic_keywords", 0),
                                    "relevance_score": 0.85,
                                    "suggested_purpose": "keyword_source",
                                })
                                seen_domains.add(domain)
                        logger.info(f"DataForSEO found {len(api_competitors)} competitors for {known_comp}")
            except Exception as e:
                logger.error(f"DataForSEO competitors API FAILED: {e}", exc_info=True)

        # Deduplicate AND filter out non-competitors (tools, services, infrastructure)
        # Track rejected domains WITH reasons for transparency
        seen = set()
        unique_candidates = []
        rejected_domains = []  # Track rejections with reasons

        for c in candidates:
            domain = c.get("domain", "").lower()
            if not domain or domain in seen:
                continue

            # Validate this is an actual competitor, not a tool/service
            is_valid, rejection_reason = self._is_valid_competitor(
                domain, target_domain, return_reason=True
            )

            if not is_valid:
                rejected_domains.append({
                    "domain": domain,
                    "rejection_gate": "hard_exclusion",
                    "rejection_reason": rejection_reason or "Invalid competitor",
                    "discovery_source": c.get("discovery_source", ""),
                })
                continue

            seen.add(domain)
            unique_candidates.append(c)

        if rejected_domains:
            logger.info(
                f"Filtered out {len(rejected_domains)} non-competitors. "
                f"Examples: {[r['domain'] for r in rejected_domains[:5]]}"
            )

        # Phase 5: Validate and enrich with metrics from DataForSEO
        if self.client:
            logger.info(f"Enriching {len(unique_candidates)} candidates with metrics...")
            unique_candidates = await self._enrich_candidates(unique_candidates, market)
        else:
            logger.warning(
                "METRIC ENRICHMENT SKIPPED: No DataForSEO client. "
                "DR, Traffic, and Keywords will be empty. "
                "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD to enable."
            )

        # Phase 6: Get target domain DR for scoring comparison
        target_dr = 0
        if self.client and target_domain:
            try:
                backlink_summary = await self.client.get_backlink_summary(target_domain)
                if backlink_summary:
                    target_dr = backlink_summary.get("domain_rank", 0)
                    logger.info(f"Target domain {target_domain} DR: {target_dr}")
            except Exception as e:
                logger.warning(f"Could not fetch target domain DR: {e}")

        # Phase 7: Score and tier all candidates
        from src.scoring.competitor_scoring import (
            score_and_tier_competitors,
            get_tier_summary,
        )

        tiered_set = score_and_tier_competitors(
            candidates=unique_candidates,
            target_dr=target_dr,
            rejected_domains=rejected_domains,
        )

        logger.info(get_tier_summary(tiered_set))

        # Prepare website context for storage (business context only - NO competitor data)
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
                "has_features_page": enhanced_context.get("has_features_page", False),
            }

        # Update session with tiered candidates and website context
        # Convert tiered set to storage format
        all_candidates_for_storage = []

        # Benchmarks first (highest priority)
        for comp in tiered_set.benchmarks:
            all_candidates_for_storage.append({
                **comp.to_dict(),
                "suggested_purpose": "benchmark_peer",
            })

        # Then keyword sources
        for comp in tiered_set.keyword_sources:
            all_candidates_for_storage.append({
                **comp.to_dict(),
                "suggested_purpose": "keyword_source",
            })

        # Then market intel
        for comp in tiered_set.market_intel:
            all_candidates_for_storage.append({
                **comp.to_dict(),
                "suggested_purpose": "market_intel",
            })

        repository.update_session_candidates(
            session_id,
            all_candidates_for_storage,
            website_context=website_context_to_store,
            tiered_data=tiered_set.to_dict(),  # Store full tiered data
        )

        # Log discovery summary
        sources = {}
        for c in unique_candidates:
            src = c.get("discovery_source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        logger.info(
            f"Competitor discovery complete: {len(unique_candidates)} scored, "
            f"{tiered_set.total_after_filtering} tiered, "
            f"{len(tiered_set.rejected)} rejected. Sources: {sources}"
        )

        return {
            "session_id": str(session_id),
            "status": "awaiting_curation",
            "discovery_summary": {
                "total_discovered": tiered_set.total_discovered,
                "total_after_filtering": tiered_set.total_after_filtering,
                "rejected_count": len(tiered_set.rejected),
                "message": get_tier_summary(tiered_set),
            },
            "target_dr": target_dr,
            "benchmarks": [c.to_dict() for c in tiered_set.benchmarks],
            "keyword_sources": [c.to_dict() for c in tiered_set.keyword_sources],
            "market_intel": [c.to_dict() for c in tiered_set.market_intel],
            "rejected": [r.to_dict() for r in tiered_set.rejected],
            "tier_limits": {
                "max_benchmarks": 5,
                "max_keyword_sources": 15,
                "max_market_intel": 15,
            },
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

        # Convert market string to location code
        # DataForSEO location codes: https://docs.dataforseo.com/v3/appendix/locations
        MARKET_TO_LOCATION_CODE = {
            "us": 2840,
            "united states": 2840,
            "uk": 2826,
            "united kingdom": 2826,
            "ca": 2124,
            "canada": 2124,
            "au": 2036,
            "australia": 2036,
            "de": 2276,
            "germany": 2276,
            "fr": 2250,
            "france": 2250,
            "se": 2752,
            "sweden": 2752,
        }
        location_code = MARKET_TO_LOCATION_CODE.get(market.lower(), 2840)  # Default to US

        logger.info(f"SERP discovery: {len(seed_keywords)} keywords, location_code={location_code}")

        for keyword in seed_keywords:
            try:
                logger.debug(f"Querying SERP for keyword: {keyword}")
                serp_results = await self.client.get_serp_results(
                    keyword=keyword,
                    location_code=location_code,  # FIXED: was passing wrong param name
                    depth=10,
                )

                # Handle None response
                if not serp_results:
                    logger.warning(f"SERP returned no results for '{keyword}'")
                    continue

                items = serp_results.get("items", [])
                logger.debug(f"SERP for '{keyword}': {len(items)} results")

                for result in items:
                    domain = result.get("domain", "")
                    if domain:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1

            except Exception as e:
                logger.error(f"SERP analysis for '{keyword}' failed: {e}", exc_info=True)

        logger.info(f"SERP found {len(domain_counts)} unique domains across all keywords")

        # Convert to candidates - domains appearing in ANY keyword (removed 2+ requirement)
        # Sort by count (most appearances first)
        for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
            competitors.append({
                "domain": domain,
                "discovery_source": "serp",
                "discovery_reason": f"Ranks for {count} of your seed keywords",
                "relevance_score": min(0.95, 0.5 + count * 0.15),
                "suggested_purpose": "keyword_source",
            })

        logger.info(f"SERP discovery returning {len(competitors[:20])} competitors")
        return competitors[:20]  # Return top 20

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

    def _is_valid_competitor(
        self,
        domain: str,
        target_domain: Optional[str] = None,
        return_reason: bool = False,
    ) -> Union[bool, Tuple[bool, Optional[str]]]:
        """
        Validate that a domain is a legitimate competitor.

        Multi-gate filtering:
        - Gate 1: Platform exclusions (social media, tech giants, news, gov, etc.)
        - Gate 2: Tool/service exclusions (payment, hosting, analytics)
        - Gate 3: Valid TLD check
        - Gate 4: Not the target domain itself

        Args:
            domain: Domain to validate
            target_domain: The user's domain (should not compete with self)
            return_reason: If True, returns (is_valid, rejection_reason) tuple

        Returns:
            bool if return_reason=False, (bool, str|None) if return_reason=True
        """
        if not domain:
            return (False, "Empty domain") if return_reason else False

        domain_lower = domain.lower().strip()

        # Remove www. prefix if present
        if domain_lower.startswith("www."):
            domain_lower = domain_lower[4:]

        # Gate 1: Check against comprehensive platform exclusions
        # This catches: Facebook, X, YouTube, tech giants, news sites, gov, etc.
        if is_excluded_domain(domain_lower):
            reason = get_exclusion_reason(domain_lower) or "Excluded platform"
            logger.debug(f"Filtering out {domain}: {reason}")
            return (False, reason) if return_reason else False

        # Gate 2: Check against known non-competitor tools/services
        domain_parts = domain_lower.split(".")
        domain_name = domain_parts[0] if domain_parts else domain_lower

        if domain_name in NON_COMPETITOR_TOOLS:
            reason = f"Infrastructure/tool service ({domain_name})"
            logger.debug(f"Filtering out {domain}: {reason}")
            return (False, reason) if return_reason else False

        # Also check full domain (for cases like "cal.com")
        base_domain = domain_lower.rstrip(".com").rstrip(".io").rstrip(".app")
        if base_domain in NON_COMPETITOR_TOOLS:
            reason = f"Infrastructure/tool service ({base_domain})"
            logger.debug(f"Filtering out {domain}: {reason}")
            return (False, reason) if return_reason else False

        # Gate 3: Validate TLD
        tld = domain_parts[-1] if len(domain_parts) > 1 else None
        if tld and tld not in VALID_TLDS:
            reason = f"Invalid TLD (.{tld})"
            logger.debug(f"Filtering out {domain}: {reason}")
            return (False, reason) if return_reason else False

        # Gate 4: Skip if it's the target domain
        if target_domain and domain_lower == target_domain.lower().strip():
            reason = "Target domain (self)"
            logger.debug(f"Filtering out {domain}: {reason}")
            return (False, reason) if return_reason else False

        return (True, None) if return_reason else True

    async def _enrich_candidates(
        self,
        candidates: List[Dict[str, Any]],
        market: str,
    ) -> List[Dict[str, Any]]:
        """
        Enrich candidates with domain metrics from DataForSEO.

        Fetches:
        - Domain Rating (DR) from Backlinks Summary API
        - Organic Traffic from Domain Rank Overview API
        - Organic Keywords from Domain Rank Overview API
        - Referring Domains from Backlinks Summary API
        """
        enriched = []
        success_count = 0
        fail_count = 0

        logger.info(f"Starting enrichment for {len(candidates)} candidates...")

        for candidate in candidates:
            domain = candidate.get("domain", "")
            try:
                # Fetch domain overview (organic metrics)
                overview = await self.client.get_domain_overview(domain=domain)
                logger.debug(f"Domain overview for {domain}: {overview}")

                # Fetch backlink summary (DR, referring domains)
                backlink_summary = await self.client.get_backlink_summary(domain=domain)
                logger.debug(f"Backlink summary for {domain}: {backlink_summary}")

                # Update candidate with metrics (handle None responses)
                candidate["domain_rating"] = (
                    backlink_summary.get("domain_rank", 0) if backlink_summary else 0
                )
                candidate["organic_traffic"] = (
                    overview.get("organic_traffic", 0) if overview else 0
                )
                candidate["organic_keywords"] = (
                    overview.get("organic_keywords", 0) if overview else 0
                )
                candidate["referring_domains"] = (
                    backlink_summary.get("referring_domains", 0) if backlink_summary else 0
                )

                # Log at INFO level for first few to help debug
                if success_count < 3:
                    logger.info(
                        f"Enriched {domain}: DR={candidate['domain_rating']}, "
                        f"traffic={candidate['organic_traffic']}, "
                        f"keywords={candidate['organic_keywords']}, "
                        f"referring_domains={candidate['referring_domains']}"
                    )

                success_count += 1

            except Exception as e:
                logger.error(f"Failed to enrich {domain}: {e}", exc_info=True)
                fail_count += 1
                # Keep the candidate but with default metrics
                candidate["domain_rating"] = 0
                candidate["organic_traffic"] = 0
                candidate["organic_keywords"] = 0
                candidate["referring_domains"] = 0

            enriched.append(candidate)

        return enriched

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

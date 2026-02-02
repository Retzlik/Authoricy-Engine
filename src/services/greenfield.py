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
    WinnabilityAnalysis,
    classify_domain_maturity,
    calculate_market_opportunity,
    calculate_winnability_full,
    calculate_personalized_difficulty_greenfield,
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
            # Curation limits (flexible: 3-15 competitors)
            "required_removals": 0,  # No longer required with auto-curation
            "min_final_count": 3,  # Minimum competitors needed
            "max_final_count": 15,  # Maximum competitors allowed
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
        # SMART AUTO-CURATION: Limit candidates presented to user
        # - Max 5 benchmarks (most important)
        # - Max 7 keyword sources (high value for mining)
        # - Max 3 market intel (awareness only)
        # Total max: 15 candidates (down from potentially 35+)

        all_candidates_for_storage = []

        # Benchmarks first (highest priority) - max 5
        for comp in tiered_set.benchmarks[:5]:
            all_candidates_for_storage.append({
                **comp.to_dict(),
                "suggested_purpose": "benchmark_peer",
                "auto_selected": True,
            })

        # Then keyword sources - max 7
        for comp in tiered_set.keyword_sources[:7]:
            all_candidates_for_storage.append({
                **comp.to_dict(),
                "suggested_purpose": "keyword_source",
                "auto_selected": True,
            })

        # Then market intel - max 3
        for comp in tiered_set.market_intel[:3]:
            all_candidates_for_storage.append({
                **comp.to_dict(),
                "suggested_purpose": "market_intel",
                "auto_selected": False,  # Optional - user can remove
            })

        # Log what was auto-filtered
        auto_filtered_count = (
            max(0, len(tiered_set.benchmarks) - 5) +
            max(0, len(tiered_set.keyword_sources) - 7) +
            max(0, len(tiered_set.market_intel) - 3)
        )
        if auto_filtered_count > 0:
            logger.info(
                f"Smart auto-curation: Filtered {auto_filtered_count} lower-scored "
                f"competitors to present {len(all_candidates_for_storage)} candidates"
            )

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

        # Validate final count (flexible limits: 3-15 competitors)
        final_count = len(candidates) - len(removals) + len(additions)
        if final_count < 3:
            raise ValueError(
                f"Must have at least 3 competitors (got {final_count})"
            )
        if final_count > 15:
            raise ValueError(
                f"Maximum 15 competitors allowed (got {final_count}). "
                f"Please remove {final_count - 15} more."
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

    async def run_deep_analysis(
        self,
        session_id: UUID,
        analysis_run_id: UUID,
        domain_id: UUID,
        domain: str,
        final_competitors: List[Dict[str, Any]],
        greenfield_context: Dict[str, Any],
        market: str = "United States",
    ) -> Dict[str, Any]:
        """
        Run deep analysis (G2-G5) after competitor curation.

        This is the critical step that mines keywords, analyzes SERPs,
        calculates market opportunity, and selects beachhead keywords.

        Args:
            session_id: Competitor intelligence session ID
            analysis_run_id: Analysis run ID
            domain_id: Domain ID
            domain: Domain name
            final_competitors: Finalized competitor list from curation
            greenfield_context: User-provided business context
            market: Target market (full name, e.g. "United States")

        Returns:
            Dict with success status, keyword counts, and market opportunity
        """
        from src.scoring.greenfield import (
            DomainMaturity,
            WinnabilityAnalysis,
            calculate_market_opportunity,
            project_traffic_scenarios,
            select_beachhead_keywords,
            get_industry_from_string,
        )
        from src.database.models import DataQualityLevel
        from src.collector.client import safe_get_result

        errors = []
        warnings = []

        logger.info(
            f"Starting deep analysis for session {session_id}: "
            f"{len(final_competitors)} competitors, domain={domain}"
        )

        # Extract competitor domains
        competitor_domains = [c.get("domain", "") for c in final_competitors if c.get("domain")]

        if not competitor_domains:
            return {
                "success": False,
                "error": "No valid competitor domains found",
                "errors": ["No competitor domains to analyze"],
            }

        industry = get_industry_from_string(greenfield_context.get("industry_vertical", "saas"))

        # Get target domain DR for winnability calculations
        target_dr = 10  # Default for greenfield
        if self.client:
            try:
                backlink_summary = await self.client.get_backlink_summary(domain=domain)
                target_dr = backlink_summary.get("domain_rank", 10) if backlink_summary else 10
            except Exception as e:
                logger.warning(f"Failed to get target DR: {e}")

        # =========================================================================
        # G2: Keyword Universe Construction
        # =========================================================================
        logger.info("G2: Building keyword universe from competitors...")
        repository.update_run_status(
            analysis_run_id,
            AnalysisStatus.ANALYZING,
            phase="keyword_mining",
            progress=20,
        )

        keyword_universe = []
        seed_keywords = greenfield_context.get("seed_keywords", [])

        try:
            if self.client:
                # Mine keywords from each competitor using direct API calls
                for comp_domain in competitor_domains[:10]:  # Limit to top 10
                    try:
                        # Get competitor's ranked keywords via DataForSEO API
                        result = await self.client.post(
                            "dataforseo_labs/google/ranked_keywords/live",
                            [{
                                "target": comp_domain,
                                "location_name": market,
                                "language_name": "English",
                                "limit": 500,
                                "include_subdomains": True,
                            }]
                        )

                        items = safe_get_result(result, get_items=True)

                        for item in items:
                            kw_data = item.get("keyword_data") or {}
                            kw_info = kw_data.get("keyword_info") or {}
                            serp_item = (item.get("ranked_serp_element") or {}).get("serp_item") or {}

                            keyword_universe.append({
                                "keyword": kw_data.get("keyword", ""),
                                "search_volume": kw_info.get("search_volume") or 0,
                                "keyword_difficulty": kw_info.get("keyword_difficulty") or 0,
                                "cpc": kw_info.get("cpc") or 0,
                                "source_competitor": comp_domain,
                                "competitor_position": serp_item.get("rank_group", 0),
                                "search_intent": "informational",
                                "business_relevance": 0.7,
                            })

                        logger.info(f"Mined {len(items)} keywords from {comp_domain}")

                    except Exception as e:
                        logger.warning(f"Failed to mine keywords from {comp_domain}: {e}")
                        warnings.append(f"Keyword mining failed for {comp_domain}")

                # Also expand from seed keywords using keyword ideas API
                for seed in seed_keywords[:5]:
                    try:
                        result = await self.client.post(
                            "dataforseo_labs/google/keyword_ideas/live",
                            [{
                                "keyword": seed,
                                "location_name": market,
                                "language_name": "English",
                                "limit": 100,
                            }]
                        )

                        items = safe_get_result(result, get_items=True)

                        for item in items:
                            kw_info = item.get("keyword_info") or item
                            keyword_universe.append({
                                "keyword": item.get("keyword", ""),
                                "search_volume": kw_info.get("search_volume") or item.get("search_volume") or 0,
                                "keyword_difficulty": kw_info.get("keyword_difficulty") or item.get("keyword_difficulty") or 0,
                                "cpc": kw_info.get("cpc") or item.get("cpc") or 0,
                                "source_competitor": f"seed:{seed}",
                                "search_intent": "informational",
                                "business_relevance": 0.8,
                            })
                    except Exception as e:
                        logger.warning(f"Failed to expand seed keyword {seed}: {e}")

            # Deduplicate keywords
            seen_keywords = set()
            unique_keywords = []
            for kw in keyword_universe:
                kw_text = kw.get("keyword", "").lower().strip()
                if kw_text and kw_text not in seen_keywords:
                    seen_keywords.add(kw_text)
                    unique_keywords.append(kw)

            keyword_universe = unique_keywords
            logger.info(f"G2 complete: {len(keyword_universe)} unique keywords")

        except Exception as e:
            logger.error(f"G2 failed: {e}")
            errors.append(f"Keyword universe construction failed: {str(e)}")

        # =========================================================================
        # G3: SERP Analysis & Winnability Scoring
        # =========================================================================
        logger.info("G3: Analyzing SERPs and calculating winnability...")
        repository.update_run_status(
            analysis_run_id,
            AnalysisStatus.ANALYZING,
            phase="serp_analysis",
            progress=40,
        )

        winnability_analyses = {}

        try:
            if self.client:
                # Analyze top keywords by volume
                keywords_to_analyze = sorted(
                    keyword_universe,
                    key=lambda k: k.get("search_volume", 0),
                    reverse=True
                )[:200]

                for kw in keywords_to_analyze:
                    keyword_text = kw.get("keyword", "")
                    try:
                        # Get SERP for this keyword using direct API call
                        result = await self.client.post(
                            "serp/google/organic/live/regular",
                            [{
                                "keyword": keyword_text,
                                "location_name": market,
                                "language_name": "English",
                                "device": "desktop",
                                "depth": 10,
                            }]
                        )

                        task_result = safe_get_result(result, get_items=False)
                        serp_result = task_result.get("items") or [] if task_result else []

                        if serp_result:
                            # Extract organic results with their metrics
                            organic_results = [
                                item for item in serp_result
                                if item.get("type") == "organic"
                            ]

                            # Build SERP data structure for proper winnability calculation
                            serp_data = {
                                "results": [
                                    {
                                        "domain": r.get("domain", ""),
                                        "domain_rating": r.get("rank_info", {}).get("main_domain_rank", 50) if r.get("rank_info") else 50,
                                        "position": r.get("rank_absolute", i + 1),
                                        "url": r.get("url", ""),
                                        "title": r.get("title", ""),
                                        # Content signals
                                        "word_count": r.get("description", "").split().__len__() * 10 if r.get("description") else 0,
                                        "is_forum": any(f in r.get("domain", "").lower() for f in ["reddit", "quora", "forum", "community"]),
                                        "is_ugc": any(u in r.get("domain", "").lower() for u in ["medium.com", "substack", "wordpress.com"]),
                                    }
                                    for i, r in enumerate(organic_results[:10])
                                ],
                                # Check for SERP features
                                "ai_overview": next((item for item in serp_result if item.get("type") == "ai_overview"), None),
                                "featured_snippet": next((item for item in serp_result if item.get("type") == "featured_snippet"), None),
                                "people_also_ask": [item for item in serp_result if item.get("type") == "people_also_ask"],
                                "video_carousel": next((item for item in serp_result if item.get("type") == "video"), None),
                            }

                            # Use the CORRECT winnability calculation function
                            # This uses real SERP DR analysis, industry coefficients, etc.
                            industry = greenfield_context.get("industry_vertical", "saas")

                            analysis = calculate_winnability_full(
                                keyword=kw,
                                target_dr=target_dr,
                                serp_data=serp_data,
                                industry=industry,
                            )

                            # Store the complete analysis
                            winnability_analyses[keyword_text] = analysis

                            # Update keyword with REAL winnability data
                            kw["winnability_score"] = analysis.winnability_score
                            kw["personalized_difficulty"] = analysis.personalized_difficulty
                            kw["serp_analyzed"] = True
                            kw["avg_serp_dr"] = analysis.avg_serp_dr
                            kw["min_serp_dr"] = analysis.min_serp_dr
                            kw["has_ai_overview"] = analysis.has_ai_overview
                            kw["has_low_dr_rankings"] = analysis.has_low_dr_rankings
                            kw["weak_content_signals"] = analysis.weak_content_signals
                            kw["is_beachhead_candidate"] = analysis.is_beachhead_candidate
                            kw["estimated_time_to_rank_weeks"] = analysis.estimated_time_to_rank_weeks

                    except Exception as e:
                        logger.debug(f"SERP analysis failed for '{keyword_text}': {e}")

                logger.info(f"G3 complete: Analyzed {len(winnability_analyses)} SERPs")

        except Exception as e:
            logger.error(f"G3 failed: {e}")
            errors.append(f"SERP analysis failed: {str(e)}")

        # =========================================================================
        # G4: Market Sizing
        # =========================================================================
        logger.info("G4: Calculating market opportunity...")
        repository.update_run_status(
            analysis_run_id,
            AnalysisStatus.ANALYZING,
            phase="market_sizing",
            progress=60,
        )

        market_opportunity = None

        try:
            competitors_for_scoring = [
                {
                    "domain": c.get("domain", ""),
                    "organic_traffic": c.get("organic_traffic", 0),
                    "organic_keywords": c.get("organic_keywords", 0),
                }
                for c in final_competitors
            ]

            market_opportunity = calculate_market_opportunity(
                keywords=keyword_universe,
                winnability_analyses=winnability_analyses,
                competitors=competitors_for_scoring,
            )

            logger.info(
                f"G4 complete: TAM={market_opportunity.tam_volume:,}, "
                f"SAM={market_opportunity.sam_volume:,}, "
                f"SOM={market_opportunity.som_volume:,}"
            )

        except Exception as e:
            logger.error(f"G4 failed: {e}")
            errors.append(f"Market sizing failed: {str(e)}")

        # =========================================================================
        # G5: Beachhead Selection & Roadmap
        # =========================================================================
        logger.info("G5: Selecting beachhead keywords...")
        repository.update_run_status(
            analysis_run_id,
            AnalysisStatus.ANALYZING,
            phase="beachhead_selection",
            progress=80,
        )

        beachhead_keywords = []
        traffic_projections = None
        growth_roadmap = []

        try:
            # Select beachhead keywords
            keywords_for_beachhead = [
                kw for kw in keyword_universe
                if kw.get("serp_analyzed", False)
            ]

            beachhead_keywords = select_beachhead_keywords(
                keywords=keywords_for_beachhead,
                winnability_analyses=winnability_analyses,
                target_count=20,
                max_kd=35,
                min_volume=50,
                min_winnability=55.0,
            )

            logger.info(f"Selected {len(beachhead_keywords)} beachhead keywords")

            # Generate traffic projections
            growth_keywords = [
                kw for kw in keywords_for_beachhead
                if kw.get("keyword") not in [bh.keyword for bh in beachhead_keywords]
            ][:50]

            traffic_projections = project_traffic_scenarios(
                beachhead_keywords=beachhead_keywords,
                growth_keywords=growth_keywords,
                winnability_analyses=winnability_analyses,
                domain_maturity=DomainMaturity.GREENFIELD,
            )

            # Build growth roadmap
            growth_roadmap = self._build_growth_roadmap(
                beachhead_keywords=beachhead_keywords,
                keyword_universe=keyword_universe,
            )

        except Exception as e:
            logger.error(f"G5 failed: {e}")
            errors.append(f"Beachhead selection failed: {str(e)}")

        # =========================================================================
        # Save Results
        # =========================================================================
        logger.info("Saving analysis results...")
        repository.update_run_status(
            analysis_run_id,
            AnalysisStatus.ANALYZING,
            phase="saving_results",
            progress=90,
        )

        try:
            # Save keywords to database
            keywords_for_db = [
                {
                    "keyword": kw.get("keyword", ""),
                    "search_volume": kw.get("search_volume", 0),
                    "keyword_difficulty": kw.get("keyword_difficulty", 0),
                    "cpc": kw.get("cpc", 0),
                    "intent": kw.get("search_intent", "informational"),
                    "opportunity_score": kw.get("winnability_score", 0),
                }
                for kw in keyword_universe
            ]

            keywords_count = repository.store_keywords(
                run_id=analysis_run_id,
                domain_id=domain_id,
                keywords=keywords_for_db,
                source="greenfield_competitor_mining",
            )

            logger.info(f"Stored {keywords_count} keywords")

            # Save beachhead keywords
            beachhead_dicts = [
                {
                    "keyword": bh.keyword,
                    "search_volume": bh.search_volume,
                    "winnability_score": bh.winnability_score,
                    "personalized_difficulty": bh.personalized_difficulty,
                    "keyword_difficulty": bh.keyword_difficulty,
                    "beachhead_priority": bh.beachhead_priority,
                    "beachhead_score": bh.beachhead_score,
                    "avg_serp_dr": bh.avg_serp_dr,
                    "has_ai_overview": bh.has_ai_overview,
                    "growth_phase": 1,  # Default to phase 1
                }
                for bh in beachhead_keywords
            ]

            beachhead_count = repository.save_beachhead_keywords(
                analysis_run_id=analysis_run_id,
                beachhead_keywords=beachhead_dicts,
            )

            logger.info(f"Marked {beachhead_count} beachhead keywords")

            # Prepare market opportunity dict
            market_opp_dict = {}
            if market_opportunity:
                # Calculate derived metrics
                opportunity_score = (
                    (market_opportunity.som_volume / max(1, market_opportunity.tam_volume)) * 100
                    if market_opportunity.tam_volume > 0 else 0
                )
                competition_intensity = (
                    1 - (market_opportunity.som_keywords / max(1, market_opportunity.sam_keywords))
                    if market_opportunity.sam_keywords > 0 else 0.5
                )

                market_opp_dict = {
                    "tam_volume": market_opportunity.tam_volume,
                    "sam_volume": market_opportunity.sam_volume,
                    "som_volume": market_opportunity.som_volume,
                    "tam_keywords": market_opportunity.tam_keywords,
                    "sam_keywords": market_opportunity.sam_keywords,
                    "som_keywords": market_opportunity.som_keywords,
                    "opportunity_score": round(opportunity_score, 1),
                    "competition_intensity": round(competition_intensity, 2),
                }

            # Prepare projections dict
            projections_dict = {}
            if traffic_projections:
                projections_dict = {
                    "conservative": {
                        "month_3": traffic_projections.conservative.traffic_by_month.get(3, 0),
                        "month_6": traffic_projections.conservative.traffic_by_month.get(6, 0),
                        "month_12": traffic_projections.conservative.traffic_by_month.get(12, 0),
                        "month_18": traffic_projections.conservative.traffic_by_month.get(18, 0),
                        "month_24": traffic_projections.conservative.traffic_by_month.get(24, 0),
                    },
                    "expected": {
                        "month_3": traffic_projections.expected.traffic_by_month.get(3, 0),
                        "month_6": traffic_projections.expected.traffic_by_month.get(6, 0),
                        "month_12": traffic_projections.expected.traffic_by_month.get(12, 0),
                        "month_18": traffic_projections.expected.traffic_by_month.get(18, 0),
                        "month_24": traffic_projections.expected.traffic_by_month.get(24, 0),
                    },
                    "aggressive": {
                        "month_3": traffic_projections.aggressive.traffic_by_month.get(3, 0),
                        "month_6": traffic_projections.aggressive.traffic_by_month.get(6, 0),
                        "month_12": traffic_projections.aggressive.traffic_by_month.get(12, 0),
                        "month_18": traffic_projections.aggressive.traffic_by_month.get(18, 0),
                        "month_24": traffic_projections.aggressive.traffic_by_month.get(24, 0),
                    },
                }

            # Prepare beachhead summary
            beachhead_summary = {
                "count": len(beachhead_keywords),
                "total_volume": sum(bh.search_volume for bh in beachhead_keywords),
                "avg_winnability": (
                    sum(bh.winnability_score for bh in beachhead_keywords) / len(beachhead_keywords)
                    if beachhead_keywords else 0
                ),
                "keywords": beachhead_dicts[:20],
            }

            # Save greenfield analysis
            analysis_id = repository.save_greenfield_analysis(
                analysis_run_id=analysis_run_id,
                domain_id=domain_id,
                market_opportunity=market_opp_dict,
                beachhead_summary=beachhead_summary,
                projections=projections_dict,
                growth_roadmap=growth_roadmap,
            )

            # Mark analysis as complete
            quality_score = 80.0 if len(keyword_universe) > 100 else 60.0
            if errors:
                quality_score -= len(errors) * 10

            repository.complete_run(
                run_id=analysis_run_id,
                quality_level=DataQualityLevel.GOOD if quality_score >= 70 else DataQualityLevel.FAIR,
                quality_score=max(0, quality_score),
                quality_issues=[{"error": e} for e in errors],
            )

            # Update domain metrics
            self._update_domain_metrics(domain_id, analysis_run_id)

            logger.info(
                f"Deep analysis complete: {keywords_count} keywords, "
                f"{len(beachhead_keywords)} beachheads"
            )

            return {
                "success": True,
                "keywords_count": keywords_count,
                "beachheads_count": len(beachhead_keywords),
                "market_opportunity": market_opp_dict,
                "errors": errors,
                "warnings": warnings,
            }

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            errors.append(f"Failed to save results: {str(e)}")
            repository.fail_run(analysis_run_id, str(e))
            return {
                "success": False,
                "error": str(e),
                "errors": errors,
            }

    def _build_growth_roadmap(
        self,
        beachhead_keywords: List[Any],
        keyword_universe: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build growth roadmap from beachhead keywords."""
        # Phase 1: Foundation (months 1-3) - easiest beachheads
        # Phase 2: Traction (months 4-6) - medium difficulty
        # Phase 3: Authority (months 7-12) - harder keywords

        roadmap = []

        # Sort beachheads by winnability
        sorted_beachheads = sorted(
            beachhead_keywords,
            key=lambda bh: bh.winnability_score,
            reverse=True,
        )

        # Phase 1: Top easiest
        phase1_kws = sorted_beachheads[:7]
        roadmap.append({
            "phase": "Foundation",
            "phase_number": 1,
            "months": "1-3",
            "focus": "Quick wins and establishing presence",
            "strategy": "Target high-winnability keywords with low competition",
            "keyword_count": len(phase1_kws),
            "total_volume": sum(bh.search_volume for bh in phase1_kws),
            "expected_traffic": sum(bh.search_volume for bh in phase1_kws) // 10,
        })

        # Phase 2: Medium difficulty
        phase2_kws = sorted_beachheads[7:14]
        roadmap.append({
            "phase": "Traction",
            "phase_number": 2,
            "months": "4-6",
            "focus": "Building authority and expanding reach",
            "strategy": "Target medium-difficulty keywords as domain strengthens",
            "keyword_count": len(phase2_kws),
            "total_volume": sum(bh.search_volume for bh in phase2_kws),
            "expected_traffic": sum(bh.search_volume for bh in phase2_kws) // 8,
        })

        # Phase 3: Harder keywords
        phase3_kws = sorted_beachheads[14:]
        roadmap.append({
            "phase": "Authority",
            "phase_number": 3,
            "months": "7-12",
            "focus": "Competing for higher-value keywords",
            "strategy": "Leverage established authority for competitive terms",
            "keyword_count": len(phase3_kws),
            "total_volume": sum(bh.search_volume for bh in phase3_kws),
            "expected_traffic": sum(bh.search_volume for bh in phase3_kws) // 6,
        })

        return roadmap

    def _update_domain_metrics(self, domain_id: UUID, analysis_run_id: UUID):
        """Update domain metrics after analysis completion."""
        try:
            with get_db_context() as db:
                domain = db.query(Domain).get(domain_id)
                if domain:
                    domain.last_analyzed_at = datetime.utcnow()
                    domain.analysis_count = (domain.analysis_count or 0) + 1
                    if not domain.first_analyzed_at:
                        domain.first_analyzed_at = datetime.utcnow()
                    logger.info(f"Updated domain metrics for {domain.domain}")
        except Exception as e:
            logger.warning(f"Failed to update domain metrics: {e}")

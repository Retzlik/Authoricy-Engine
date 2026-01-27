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


# Business context extraction patterns
COMPETITOR_PATTERNS = [
    r"compared to (\w+(?:\.\w+)?)",
    r"alternative to (\w+(?:\.\w+)?)",
    r"vs\.? (\w+(?:\.\w+)?)",
    r"unlike (\w+(?:\.\w+)?)",
    r"better than (\w+(?:\.\w+)?)",
    r"switch from (\w+(?:\.\w+)?)",
]

PRICE_PATTERNS = [
    r"\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:/|per)?\s*(?:mo|month|monthly)",
    r"(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|EUR|GBP)\s*(?:/|per)?\s*(?:mo|month|monthly)",
    r"starting at \$?(\d+)",
]


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
        for pattern in COMPETITOR_PATTERNS:
            matches = re.findall(pattern, combined_content, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                comp = match.strip().lower()
                if comp and len(comp) > 2 and "." in comp or len(comp) > 4:
                    mentioned_competitors.add(comp)

        if mentioned_competitors:
            context["self_mentioned_competitors"] = list(mentioned_competitors)[:10]

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
                logger.warning(f"Perplexity discovery failed: {e}")

        # Phase 4: Discover from SERPs if client available
        if self.client and seed_keywords:
            try:
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
                logger.warning(f"SERP discovery failed: {e}")

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

        # Update session with candidates and website context
        repository.update_session_candidates(session_id, unique_candidates)

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
        offering = business_context.get("business_description", category)
        customer_type = business_context.get("target_audience") or "B2B companies"
        seed_keywords = business_context.get("seed_keywords", [])

        logger.info(
            f"Perplexity discovery for {company_name}: "
            f"category={category}, keywords={len(seed_keywords)}"
        )

        # Run discovery with full context
        discovered = await discovery.discover_competitors(
            company_name=company_name,
            category=category,
            offering=offering,
            customer_type=customer_type,
            seed_keywords=seed_keywords,
        )

        logger.info(f"Perplexity discovered {len(discovered)} unique competitors")

        # Convert to dict format
        competitors = []
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

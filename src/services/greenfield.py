"""
Greenfield Intelligence Service

Orchestrates the greenfield analysis workflow:
1. Domain maturity detection
2. Competitor discovery and curation
3. Keyword collection and winnability scoring
4. Market opportunity calculation
5. Beachhead selection and roadmap generation
"""

import logging
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
                metrics = DomainMetrics(
                    domain_rating=overview.get("rank", 0),
                    organic_keywords=overview.get("organic_keywords", 0),
                    organic_traffic=overview.get("organic_traffic", 0),
                    referring_domains=overview.get("referring_domains", 0),
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

    def start_greenfield_analysis(
        self,
        domain: str,
        greenfield_context: Dict[str, Any],
    ) -> Tuple[UUID, UUID]:
        """
        Start a greenfield analysis.

        Creates analysis run and competitor intelligence session.

        Args:
            domain: Domain to analyze
            greenfield_context: User-provided business context

        Returns:
            Tuple of (analysis_run_id, session_id)
        """
        # Create analysis run
        analysis_run_id = repository.create_greenfield_analysis_run(
            domain=domain,
            greenfield_context=greenfield_context,
            config={"mode": "greenfield"},
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
    ) -> Dict[str, Any]:
        """
        Discover competitors for a session.

        Aggregates competitors from multiple sources and updates session.
        Sources:
        1. User-provided competitors
        2. Perplexity AI discovery (if available)
        3. SERP analysis for seed keywords
        """
        candidates = []
        seen_domains = set()

        # Add user-provided competitors
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

        # Discover from Perplexity AI (intelligent, context-aware discovery)
        if self.perplexity_client and business_context:
            try:
                perplexity_competitors = await self._discover_from_perplexity(
                    business_context=business_context,
                )
                for comp in perplexity_competitors:
                    domain = comp.get("domain", "").lower()
                    if domain and domain not in seen_domains:
                        candidates.append(comp)
                        seen_domains.add(domain)
                logger.info(f"Perplexity discovered {len(perplexity_competitors)} candidates")
            except Exception as e:
                logger.warning(f"Perplexity discovery failed: {e}")

        # Discover from SERPs if client available
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

        # Validate and enrich with metrics
        if self.client:
            unique_candidates = await self._enrich_candidates(unique_candidates, market)

        # Update session
        repository.update_session_candidates(session_id, unique_candidates)

        return {
            "session_id": str(session_id),
            "status": "awaiting_curation",
            "candidates": unique_candidates,
            "candidates_count": len(unique_candidates),
            "required_removals": max(0, len(unique_candidates) - 10),
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

        # Extract context fields
        company_name = business_context.get("business_name", "the company")
        category = business_context.get("primary_offering", "software")
        offering = business_context.get("business_description", category)
        customer_type = business_context.get("target_audience", "businesses")

        # Run discovery
        discovered = await discovery.discover_competitors(
            company_name=company_name,
            category=category,
            offering=offering,
            customer_type=customer_type,
        )

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

                candidate["domain_rating"] = overview.get("rank", 0)
                candidate["organic_traffic"] = overview.get("organic_traffic", 0)
                candidate["organic_keywords"] = overview.get("organic_keywords", 0)

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

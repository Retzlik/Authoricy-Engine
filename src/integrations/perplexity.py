"""
Perplexity API Client

AI-powered search for intelligent competitor discovery.

Perplexity provides:
- Real-time web search with AI understanding
- Contextual answers about competitors
- Citation tracking for sources

API: https://docs.perplexity.ai/
Pricing: ~$5/1000 queries (sonar model)
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class PerplexityError(Exception):
    """Custom exception for Perplexity API errors."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)


@dataclass
class DiscoveredCompetitor:
    """Competitor discovered from Perplexity response."""

    name: str
    domain: Optional[str] = None
    description: str = ""
    discovery_source: str = "perplexity"
    discovery_reason: str = ""
    confidence: float = 0.7
    raw_mention: str = ""


@dataclass
class PerplexityResult:
    """Result from a Perplexity query."""

    answer: str
    citations: List[str] = field(default_factory=list)
    competitors: List[DiscoveredCompetitor] = field(default_factory=list)
    query: str = ""
    model: str = ""
    tokens_used: int = 0


class PerplexityClient:
    """
    Async client for Perplexity API.

    Usage:
        client = PerplexityClient(api_key="your_api_key")

        result = await client.query("Who are the main competitors to Notion?")
        # result.answer = "The main competitors to Notion include..."
        # result.citations = ["https://...", ...]

        await client.close()
    """

    BASE_URL = "https://api.perplexity.ai"

    # Available models
    MODELS = {
        "sonar": "llama-3.1-sonar-small-128k-online",  # Fast, cheaper
        "sonar-pro": "llama-3.1-sonar-large-128k-online",  # More capable
        "sonar-huge": "llama-3.1-sonar-huge-128k-online",  # Most capable
    }

    def __init__(
        self,
        api_key: str,
        retry_config: Optional[RetryConfig] = None,
        default_model: str = "sonar",
        timeout: float = 60.0,
    ):
        """
        Initialize Perplexity client.

        Args:
            api_key: Perplexity API key
            retry_config: Retry configuration (optional)
            default_model: Default model to use (sonar, sonar-pro, sonar-huge)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.retry_config = retry_config or RetryConfig()
        self.default_model = self.MODELS.get(default_model, default_model)

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )
        self._closed = False

    async def query(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        return_citations: bool = True,
        return_images: bool = False,
        search_recency_filter: Optional[str] = None,
    ) -> PerplexityResult:
        """
        Query Perplexity with a question.

        Args:
            question: The question to ask
            system_prompt: Optional system prompt for context
            model: Model to use (overrides default)
            temperature: Response temperature (0-1)
            max_tokens: Maximum tokens in response
            return_citations: Include source citations
            return_images: Include relevant images
            search_recency_filter: Filter by recency (day, week, month, year)

        Returns:
            PerplexityResult with answer, citations, and extracted competitors
        """
        if self._closed:
            raise PerplexityError("Client has been closed")

        model_name = model or self.default_model
        if model_name in self.MODELS:
            model_name = self.MODELS[model_name]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "return_citations": return_citations,
            "return_images": return_images,
        }

        if search_recency_filter:
            payload["search_recency_filter"] = search_recency_filter

        response = await self._request_with_retry(payload)

        # Extract answer and citations
        choices = response.get("choices", [])
        answer = ""
        if choices:
            answer = choices[0].get("message", {}).get("content", "")

        citations = response.get("citations", [])

        # Calculate tokens
        usage = response.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)

        return PerplexityResult(
            answer=answer,
            citations=citations,
            query=question,
            model=model_name,
            tokens_used=tokens_used,
        )

    async def query_for_competitors(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> PerplexityResult:
        """
        Query Perplexity and extract competitor information.

        This method adds competitor extraction to the standard query.

        Args:
            question: Question about competitors
            system_prompt: Optional system prompt
            **kwargs: Additional arguments passed to query()

        Returns:
            PerplexityResult with extracted competitors
        """
        # Add competitor-focused system prompt if not provided
        if not system_prompt:
            system_prompt = (
                "You are a business intelligence analyst helping identify competitors. "
                "When listing competitors, always include their company name and website domain "
                "in parentheses if known. Be specific and factual. Focus on direct competitors "
                "in the same market segment."
            )

        result = await self.query(question, system_prompt=system_prompt, **kwargs)

        # Extract competitors from the answer
        result.competitors = self._extract_competitors(result.answer)

        return result

    def _extract_competitors(self, text: str) -> List[DiscoveredCompetitor]:
        """
        Extract competitor names and domains from Perplexity response text.

        Uses multiple patterns to find company mentions:
        - Company Name (domain.com)
        - Company Name - domain.com
        - Numbered lists with company names
        - Bold/emphasized company names
        """
        competitors = []
        seen_names = set()

        # Pattern 1: Company (domain.com) or Company [domain.com]
        pattern1 = r"([A-Z][a-zA-Z0-9\s&\-\.]+?)\s*[\(\[]([a-zA-Z0-9\-]+\.[a-zA-Z]{2,})[^\)]*[\)\]]"
        for match in re.finditer(pattern1, text):
            name = match.group(1).strip()
            domain = match.group(2).lower()
            if name.lower() not in seen_names and len(name) > 2:
                seen_names.add(name.lower())
                competitors.append(
                    DiscoveredCompetitor(
                        name=name,
                        domain=domain,
                        raw_mention=match.group(0),
                        confidence=0.9,
                    )
                )

        # Pattern 2: **Company Name** (bold markdown)
        pattern2 = r"\*\*([A-Z][a-zA-Z0-9\s&\-\.]+?)\*\*"
        for match in re.finditer(pattern2, text):
            name = match.group(1).strip()
            if name.lower() not in seen_names and len(name) > 2:
                # Try to find domain nearby
                domain = self._find_nearby_domain(text, match.start(), match.end())
                seen_names.add(name.lower())
                competitors.append(
                    DiscoveredCompetitor(
                        name=name,
                        domain=domain,
                        raw_mention=match.group(0),
                        confidence=0.7 if domain else 0.5,
                    )
                )

        # Pattern 3: Numbered list items "1. Company Name" or "- Company Name"
        pattern3 = r"(?:^|\n)[\d\-\*\.]+\s*([A-Z][a-zA-Z0-9\s&\-\.]+?)(?:\s*[\-\:]\s*|\s*$)"
        for match in re.finditer(pattern3, text):
            name = match.group(1).strip()
            # Clean up common suffixes
            name = re.sub(r"\s*(is|are|has|offers|provides).*$", "", name, flags=re.IGNORECASE)
            if name.lower() not in seen_names and len(name) > 2 and len(name) < 50:
                domain = self._find_nearby_domain(text, match.start(), match.end())
                seen_names.add(name.lower())
                competitors.append(
                    DiscoveredCompetitor(
                        name=name,
                        domain=domain,
                        raw_mention=match.group(0).strip(),
                        confidence=0.6 if domain else 0.4,
                    )
                )

        # Sort by confidence
        competitors.sort(key=lambda c: c.confidence, reverse=True)

        return competitors

    def _find_nearby_domain(
        self,
        text: str,
        start: int,
        end: int,
        search_range: int = 100,
    ) -> Optional[str]:
        """Find a domain mention near a position in text."""
        search_text = text[max(0, start - 20) : min(len(text), end + search_range)]
        domain_pattern = r"([a-zA-Z0-9\-]+\.(?:com|io|co|org|net|ai|app|dev))"
        match = re.search(domain_pattern, search_text)
        return match.group(1).lower() if match else None

    async def _request_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make request with retry logic."""
        config = self.retry_config
        last_exception = None

        for attempt in range(config.max_retries + 1):
            try:
                response = await self._client.post("/chat/completions", json=payload)

                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}

                    if response.status_code in config.retryable_status_codes:
                        last_exception = PerplexityError(
                            f"API error: {response.status_code}",
                            status_code=response.status_code,
                            response=error_data,
                        )
                    else:
                        raise PerplexityError(
                            f"API error: {error_data.get('error', {}).get('message', response.status_code)}",
                            status_code=response.status_code,
                            response=error_data,
                        )
                else:
                    return response.json()

            except httpx.TimeoutException as e:
                last_exception = PerplexityError(f"Request timed out: {e}")
            except httpx.RequestError as e:
                last_exception = PerplexityError(f"Request failed: {e}")

            if attempt < config.max_retries:
                delay = min(
                    config.initial_delay * (config.exponential_base**attempt),
                    config.max_delay,
                )
                logger.warning(
                    f"Perplexity request failed, retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{config.max_retries + 1})"
                )
                await asyncio.sleep(delay)

        raise last_exception

    async def close(self):
        """Close the HTTP client."""
        if not self._closed:
            await self._client.aclose()
            self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class PerplexityDiscovery:
    """
    Competitor discovery using Perplexity AI search.

    Executes multiple targeted queries to find competitors:
    1. Direct competitors by company name
    2. Alternative products/services
    3. Market leaders in the category
    4. Emerging players/startups
    """

    # Query templates for competitor discovery
    QUERY_TEMPLATES = {
        "direct": (
            "Who are the main direct competitors to {company_name} "
            "in the {category} market? List specific company names and their websites."
        ),
        "alternatives": (
            "What are the best alternatives to {company_name} for {offering}? "
            "Include both direct competitors and similar tools with their domains."
        ),
        "market_leaders": (
            "Who are the leading companies in the {category} market "
            "for {customer_type} in 2024-2025? List company names and websites."
        ),
        "emerging": (
            "What are the fastest growing startups or new companies "
            "in the {category} space? Include their websites."
        ),
    }

    def __init__(
        self,
        client: PerplexityClient,
        max_queries: int = 4,
    ):
        """
        Initialize Perplexity discovery.

        Args:
            client: PerplexityClient instance
            max_queries: Maximum number of queries to run
        """
        self.client = client
        self.max_queries = max_queries

    async def discover_competitors(
        self,
        company_name: str,
        category: str,
        offering: str,
        customer_type: str = "businesses",
        additional_context: str = "",
    ) -> List[DiscoveredCompetitor]:
        """
        Discover competitors using multiple Perplexity queries.

        Args:
            company_name: Name of the company to find competitors for
            category: Product/service category (e.g., "project management software")
            offering: Specific offering description
            customer_type: Target customer type
            additional_context: Extra context to include in queries

        Returns:
            List of discovered competitors, deduplicated and ranked
        """
        all_competitors = []
        query_vars = {
            "company_name": company_name,
            "category": category,
            "offering": offering,
            "customer_type": customer_type,
        }

        queries_to_run = list(self.QUERY_TEMPLATES.items())[: self.max_queries]

        for query_type, template in queries_to_run:
            try:
                question = template.format(**query_vars)
                if additional_context:
                    question += f" Context: {additional_context}"

                logger.info(f"Running Perplexity query: {query_type}")

                result = await self.client.query_for_competitors(
                    question,
                    search_recency_filter="year",  # Focus on recent info
                )

                # Tag competitors with discovery source
                for comp in result.competitors:
                    comp.discovery_source = f"perplexity_{query_type}"
                    comp.discovery_reason = f"Found via {query_type} query"

                all_competitors.extend(result.competitors)

                # Small delay between queries
                await asyncio.sleep(0.5)

            except PerplexityError as e:
                logger.warning(f"Perplexity query '{query_type}' failed: {e}")

        # Deduplicate and merge
        return self._deduplicate_competitors(all_competitors)

    def _deduplicate_competitors(
        self,
        competitors: List[DiscoveredCompetitor],
    ) -> List[DiscoveredCompetitor]:
        """
        Deduplicate competitors by name/domain, keeping highest confidence.
        """
        seen = {}  # domain or name -> competitor

        for comp in competitors:
            key = comp.domain or comp.name.lower()

            if key in seen:
                # Keep higher confidence
                if comp.confidence > seen[key].confidence:
                    seen[key] = comp
                # Merge domain if missing
                elif comp.domain and not seen[key].domain:
                    seen[key].domain = comp.domain
            else:
                seen[key] = comp

        # Sort by confidence
        result = list(seen.values())
        result.sort(key=lambda c: c.confidence, reverse=True)

        return result

    async def quick_discover(
        self,
        company_name: str,
        category: str,
    ) -> List[DiscoveredCompetitor]:
        """
        Quick competitor discovery with a single query.

        Good for fast results when you don't need comprehensive coverage.
        """
        question = (
            f"List the top 10 competitors to {company_name} in the {category} market. "
            f"For each competitor, provide the company name and website domain."
        )

        result = await self.client.query_for_competitors(question)

        for comp in result.competitors:
            comp.discovery_source = "perplexity_quick"
            comp.discovery_reason = "Found via quick discovery"

        return result.competitors

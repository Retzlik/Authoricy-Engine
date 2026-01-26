"""
Firecrawl API Client

Website scraping service for context acquisition in competitor intelligence.

Firecrawl handles:
- JavaScript rendering
- Anti-bot bypass
- Clean markdown output

API: https://firecrawl.dev
Pricing: ~$0.001/page
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class FirecrawlError(Exception):
    """Custom exception for Firecrawl API errors."""

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


class FirecrawlClient:
    """
    Async client for Firecrawl API.

    Usage:
        client = FirecrawlClient(api_key="your_api_key")

        result = await client.scrape_url("https://example.com")
        # result = {"success": True, "data": {"markdown": "...", "metadata": {...}}}

        await client.close()
    """

    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(
        self,
        api_key: str,
        retry_config: Optional[RetryConfig] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize Firecrawl client.

        Args:
            api_key: Firecrawl API key
            retry_config: Retry configuration (optional)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.retry_config = retry_config or RetryConfig()

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )
        self._closed = False

    async def scrape_url(
        self,
        url: str,
        formats: List[str] = None,
        include_tags: List[str] = None,
        exclude_tags: List[str] = None,
        only_main_content: bool = True,
        wait_for: int = None,
    ) -> Dict[str, Any]:
        """
        Scrape a single URL.

        Args:
            url: URL to scrape
            formats: Output formats (markdown, html, rawHtml, links, screenshot)
            include_tags: HTML tags to include
            exclude_tags: HTML tags to exclude
            only_main_content: Extract only main content (no nav/footer)
            wait_for: Wait time in ms for JS rendering

        Returns:
            {
                "success": bool,
                "data": {
                    "markdown": "...",
                    "html": "...",
                    "metadata": {
                        "title": "...",
                        "description": "...",
                        "language": "...",
                        "sourceURL": "...",
                    }
                }
            }
        """
        if self._closed:
            raise FirecrawlError("Client has been closed")

        payload = {
            "url": url,
            "formats": formats or ["markdown"],
            "onlyMainContent": only_main_content,
        }

        if include_tags:
            payload["includeTags"] = include_tags
        if exclude_tags:
            payload["excludeTags"] = exclude_tags
        if wait_for:
            payload["waitFor"] = wait_for

        return await self._request_with_retry("POST", "/scrape", payload)

    async def crawl_url(
        self,
        url: str,
        max_depth: int = 2,
        limit: int = 10,
        include_paths: List[str] = None,
        exclude_paths: List[str] = None,
        allow_external_links: bool = False,
    ) -> Dict[str, Any]:
        """
        Crawl a website starting from a URL.

        Args:
            url: Starting URL
            max_depth: Maximum crawl depth
            limit: Maximum number of pages
            include_paths: URL patterns to include
            exclude_paths: URL patterns to exclude
            allow_external_links: Follow external links

        Returns:
            {
                "success": bool,
                "id": "crawl_id",
                "url": "status_url"
            }
        """
        if self._closed:
            raise FirecrawlError("Client has been closed")

        payload = {
            "url": url,
            "maxDepth": max_depth,
            "limit": limit,
            "allowExternalLinks": allow_external_links,
        }

        if include_paths:
            payload["includePaths"] = include_paths
        if exclude_paths:
            payload["excludePaths"] = exclude_paths

        return await self._request_with_retry("POST", "/crawl", payload)

    async def get_crawl_status(self, crawl_id: str) -> Dict[str, Any]:
        """
        Get status of a crawl job.

        Args:
            crawl_id: Crawl job ID

        Returns:
            {
                "status": "scraping|completed|failed",
                "completed": int,
                "total": int,
                "data": [...]  # When completed
            }
        """
        if self._closed:
            raise FirecrawlError("Client has been closed")

        return await self._request_with_retry("GET", f"/crawl/{crawl_id}", None)

    async def scrape_multiple(
        self,
        urls: List[str],
        concurrency: int = 3,
        **scrape_kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs with concurrency control.

        Args:
            urls: List of URLs to scrape
            concurrency: Maximum concurrent requests
            **scrape_kwargs: Arguments passed to scrape_url

        Returns:
            List of scrape results in same order as input URLs
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self.scrape_url(url, **scrape_kwargs)
                except Exception as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
                    return {"success": False, "error": str(e), "url": url}

        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Make request with retry logic."""
        config = self.retry_config
        last_exception = None

        for attempt in range(config.max_retries + 1):
            try:
                if method == "POST":
                    response = await self._client.post(endpoint, json=payload)
                elif method == "GET":
                    response = await self._client.get(endpoint)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                # Check for errors
                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}

                    if response.status_code in config.retryable_status_codes:
                        last_exception = FirecrawlError(
                            f"API error: {response.status_code}",
                            status_code=response.status_code,
                            response=error_data,
                        )
                        # Will retry
                    else:
                        raise FirecrawlError(
                            f"API error: {error_data.get('error', response.status_code)}",
                            status_code=response.status_code,
                            response=error_data,
                        )
                else:
                    return response.json()

            except httpx.TimeoutException as e:
                last_exception = FirecrawlError(f"Request timed out: {e}")
            except httpx.RequestError as e:
                last_exception = FirecrawlError(f"Request failed: {e}")

            # Retry delay
            if attempt < config.max_retries:
                delay = min(
                    config.initial_delay * (config.exponential_base**attempt),
                    config.max_delay,
                )
                logger.warning(
                    f"Firecrawl request failed, retrying in {delay:.1f}s "
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


class WebsiteScraper:
    """
    High-level scraper for business context acquisition.

    Scrapes key business pages to understand:
    - What the company does
    - Their products/services
    - Pricing model
    - Target customers
    - Positioning
    """

    BUSINESS_PAGES = [
        "/",
        "/about",
        "/about-us",
        "/pricing",
        "/product",
        "/products",
        "/features",
        "/solutions",
        "/services",
        "/customers",
        "/case-studies",
        "/industries",
    ]

    def __init__(self, client: FirecrawlClient):
        """
        Initialize website scraper.

        Args:
            client: FirecrawlClient instance
        """
        self.client = client

    async def scrape_business_pages(
        self,
        domain: str,
        pages: Optional[List[str]] = None,
        max_pages: int = 8,
    ) -> Dict[str, Any]:
        """
        Scrape key business pages from a domain.

        Args:
            domain: Domain to scrape (without protocol)
            pages: Custom list of page paths (optional)
            max_pages: Maximum pages to scrape

        Returns:
            {
                "domain": "example.com",
                "pages": {
                    "/": {"content": "...", "metadata": {...}},
                    "/about": {"content": "...", "metadata": {...}},
                    ...
                },
                "success_count": 5,
                "total_pages": 8,
                "combined_content": "..."  # All content combined
            }
        """
        pages = pages or self.BUSINESS_PAGES[:max_pages]
        base_url = f"https://{domain}"

        urls_to_scrape = []
        for page in pages:
            url = f"{base_url}{page}" if page != "/" else base_url
            urls_to_scrape.append(url)

        logger.info(f"Scraping {len(urls_to_scrape)} pages from {domain}")

        results = await self.client.scrape_multiple(
            urls_to_scrape,
            concurrency=3,
            only_main_content=True,
        )

        # Organize results
        scraped_data = {
            "domain": domain,
            "pages": {},
            "success_count": 0,
            "total_pages": len(urls_to_scrape),
            "combined_content": "",
        }

        combined_parts = []

        for url, result in zip(urls_to_scrape, results):
            page_path = url.replace(base_url, "") or "/"

            if result.get("success"):
                data = result.get("data", {})
                content = data.get("markdown", "")
                metadata = data.get("metadata", {})

                scraped_data["pages"][page_path] = {
                    "content": content,
                    "metadata": metadata,
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", ""),
                }
                scraped_data["success_count"] += 1

                # Add to combined content
                if content:
                    combined_parts.append(f"## {page_path}\n\n{content}")
            else:
                scraped_data["pages"][page_path] = {
                    "error": result.get("error", "Unknown error"),
                }

        scraped_data["combined_content"] = "\n\n---\n\n".join(combined_parts)

        logger.info(
            f"Scraped {scraped_data['success_count']}/{scraped_data['total_pages']} "
            f"pages from {domain}"
        )

        return scraped_data

    async def extract_business_context(
        self,
        domain: str,
    ) -> Dict[str, Any]:
        """
        Extract structured business context from a domain.

        Returns:
            {
                "domain": "example.com",
                "raw_content": "...",
                "metadata": {
                    "title": "...",
                    "description": "...",
                },
                "detected_pages": ["pricing", "features", ...],
                "content_summary": {
                    "homepage": "...",
                    "about": "...",
                    "pricing": "...",
                }
            }
        """
        scraped = await self.scrape_business_pages(domain)

        # Extract key information
        context = {
            "domain": domain,
            "raw_content": scraped["combined_content"],
            "metadata": {},
            "detected_pages": [],
            "content_summary": {},
        }

        # Get metadata from homepage
        if "/" in scraped["pages"] and "content" in scraped["pages"]["/"]:
            homepage = scraped["pages"]["/"]
            context["metadata"] = {
                "title": homepage.get("title", ""),
                "description": homepage.get("description", ""),
            }

        # List successfully scraped pages
        for page_path, page_data in scraped["pages"].items():
            if "content" in page_data and page_data["content"]:
                context["detected_pages"].append(page_path)
                # Truncate content for summary
                content = page_data["content"][:2000]
                context["content_summary"][page_path] = content

        return context

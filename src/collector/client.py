"""
DataForSEO API Client

Async HTTP client with:
- Connection pooling (50 concurrent connections)
- Automatic retry with exponential backoff
- Graceful error handling
- Request/response logging
"""

import asyncio
import httpx
import base64
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def safe_get_result(response: Dict, get_items: bool = True) -> Any:
    """
    Safely extract result data from DataForSEO API response.

    Handles cases where result is None, empty, or malformed.

    Args:
        response: Raw API response dict
        get_items: If True, returns items list. If False, returns first result object.

    Returns:
        List of items, result dict, or empty list/dict on failure
    """
    try:
        tasks = response.get("tasks")
        if not tasks or not isinstance(tasks, list):
            return [] if get_items else {}

        task = tasks[0] if tasks else {}
        result = task.get("result")

        if not result or not isinstance(result, list):
            return [] if get_items else {}

        first_result = result[0] if result else {}
        if not first_result or not isinstance(first_result, dict):
            return [] if get_items else {}

        if get_items:
            items = first_result.get("items")
            return items if items and isinstance(items, list) else []
        else:
            return first_result
    except (TypeError, IndexError, KeyError) as e:
        logger.debug(f"Safe result extraction failed: {e}")
        return [] if get_items else {}


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)


class DataForSEOError(Exception):
    """Custom exception for DataForSEO API errors."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class DataForSEOClient:
    """
    Async client for DataForSEO API.
    
    Usage:
        client = DataForSEOClient(login="your_login", password="your_password")
        
        result = await client.post("dataforseo_labs/google/ranked_keywords/live", [{
            "target": "example.com",
            "location_name": "Sweden",
            "language_code": "sv",
        }])
        
        await client.close()
    """
    
    BASE_URL = "https://api.dataforseo.com/v3"
    
    def __init__(
        self,
        login: str,
        password: str,
        retry_config: Optional[RetryConfig] = None,
        max_connections: int = 50,
        timeout: float = 60.0,
    ):
        """
        Initialize DataForSEO client.
        
        Args:
            login: DataForSEO login email
            password: DataForSEO API password
            retry_config: Retry configuration (optional)
            max_connections: Maximum concurrent connections
            timeout: Request timeout in seconds
        """
        self.login = login
        self.password = password
        self.retry_config = retry_config or RetryConfig()
        
        # Create auth header
        credentials = f"{login}:{password}"
        auth_token = base64.b64encode(credentials.encode()).decode()
        
        # Configure HTTP client with connection pooling
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Basic {auth_token}",
                "Content-Type": "application/json",
            },
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_connections // 2,
            ),
            timeout=httpx.Timeout(timeout),
        )
        
        self._closed = False
    
    async def post(
        self,
        endpoint: str,
        data: List[Dict[str, Any]],
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Make POST request to DataForSEO API.
        
        Args:
            endpoint: API endpoint path (e.g., "dataforseo_labs/google/ranked_keywords/live")
            data: Request payload (list of task objects)
            retry: Whether to retry on failure
        
        Returns:
            API response as dictionary
        
        Raises:
            DataForSEOError: On API error
        """
        if self._closed:
            raise DataForSEOError("Client is closed")
        
        url = f"/{endpoint}"
        
        if retry:
            return await self._request_with_retry(url, data)
        else:
            return await self._make_request(url, data)
    
    async def _make_request(self, url: str, data: List[Dict]) -> Dict[str, Any]:
        """Make a single HTTP request."""
        logger.debug(f"POST {url}")
        
        response = await self._client.post(url, json=data)
        
        if response.status_code != 200:
            raise DataForSEOError(
                f"API request failed: {response.status_code}",
                status_code=response.status_code,
                response=response.json() if response.content else None,
            )
        
        result = response.json()

        # Check for API-level errors
        if result.get("status_code") != 20000:
            error_msg = result.get("status_message", "Unknown error")
            raise DataForSEOError(
                f"API error: {error_msg}",
                status_code=result.get("status_code"),
                response=result,
            )

        # Check task-level errors and log them clearly
        tasks = result.get("tasks", [])
        for task in tasks:
            task_status = task.get("status_code")
            if task_status not in [20000, 20100]:
                error_msg = task.get("status_message", "Task error")
                # Log at ERROR level with full details for debugging
                logger.error(
                    f"DataForSEO task error in {url}: {error_msg} (status: {task_status}). "
                    f"This may cause empty data in the report."
                )

        return result
    
    async def _request_with_retry(self, url: str, data: List[Dict]) -> Dict[str, Any]:
        """Make request with automatic retry on failure."""
        last_exception = None
        delay = self.retry_config.initial_delay
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                return await self._make_request(url, data)
            
            except DataForSEOError as e:
                last_exception = e
                
                # Don't retry client errors (4xx except 429)
                if e.status_code and 400 <= e.status_code < 500 and e.status_code != 429:
                    raise
                
                # Check if we should retry
                if attempt < self.retry_config.max_retries:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )
            
            except httpx.TimeoutException as e:
                last_exception = DataForSEOError(f"Request timed out: {e}")
                
                if attempt < self.retry_config.max_retries:
                    logger.warning(
                        f"Timeout (attempt {attempt + 1}). Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )
            
            except httpx.HTTPError as e:
                last_exception = DataForSEOError(f"HTTP error: {e}")
                
                if attempt < self.retry_config.max_retries:
                    logger.warning(
                        f"HTTP error (attempt {attempt + 1}). Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )
        
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

    # ========================================================================
    # CONTEXT INTELLIGENCE HELPER METHODS
    # ========================================================================

    async def get_serp_results(
        self,
        keyword: str,
        location_code: int = 2840,
        language_code: str = "en",
        depth: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        Get SERP results for a keyword.

        Used by Context Intelligence for competitor discovery.

        Args:
            keyword: Search query
            location_code: DataForSEO location code (default: 2840 = US)
            language_code: Language code (default: "en")
            depth: Number of results to return (default: 20)

        Returns:
            SERP results with items list, or None on error
        """
        try:
            result = await self.post(
                "serp/google/organic/live/regular",
                [{
                    "keyword": keyword,
                    "location_code": location_code,
                    "language_code": language_code,
                    "depth": depth,
                }]
            )

            tasks = result.get("tasks", [])
            if tasks and tasks[0].get("result"):
                task_result = tasks[0]["result"]
                if task_result and len(task_result) > 0:
                    return task_result[0]

            return None

        except DataForSEOError as e:
            logger.warning(f"SERP query failed for '{keyword}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in SERP query: {e}")
            return None

    async def get_keywords_data(
        self,
        keywords: List[str],
        location_code: int = 2840,
        language_name: str = "English",
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get search volume and competition data for keywords.

        Used by Context Intelligence for market validation.

        Args:
            keywords: List of keywords to analyze
            location_code: DataForSEO location code
            language_name: Language name (e.g., "English", "Swedish") - Labs API uses language_name

        Returns:
            List of keyword data dicts with search_volume, competition, etc.
            Returns None on error.
        """
        if not keywords:
            return None

        try:
            result = await self.post(
                "dataforseo_labs/google/bulk_keyword_difficulty/live",
                [{
                    "keywords": keywords[:1000],  # API limit
                    "location_code": location_code,
                    "language_name": language_name,  # Labs API uses language_name, not language_code
                }]
            )

            tasks = result.get("tasks", [])
            if tasks and tasks[0].get("result"):
                task_result = tasks[0]["result"]
                if task_result:
                    # Return normalized keyword data
                    return [
                        {
                            "keyword": item.get("keyword", ""),
                            "search_volume": item.get("search_volume", 0),
                            "competition": item.get("keyword_difficulty", 50) / 100,  # Normalize to 0-1
                            "cpc": item.get("cpc", 0),
                        }
                        for item in task_result
                        if item
                    ]

            return None

        except DataForSEOError as e:
            logger.warning(f"Keywords data query failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in keywords data query: {e}")
            return None

    async def get_domain_overview(
        self,
        domain: str,
        location_code: int = 2840,
        language_name: str = "English",
        location: str = None,  # Legacy parameter name for compatibility
    ) -> Optional[Dict[str, Any]]:
        """
        Get domain overview with organic traffic and keyword metrics.

        Uses DataForSEO Labs Domain Rank Overview API.

        Args:
            domain: Target domain
            location_code: DataForSEO location code (default: 2840 = US)
            language_name: Language name (e.g., "English")
            location: Legacy parameter (ignored, use location_code)

        Returns:
            Dict with organic_traffic, organic_keywords, etc. or None on error
        """
        try:
            result = await self.post(
                "dataforseo_labs/google/domain_rank_overview/live",
                [{
                    "target": domain,
                    "location_code": location_code,
                    "language_name": language_name,
                }]
            )

            tasks = result.get("tasks", [])
            if tasks and tasks[0].get("result"):
                task_result = tasks[0]["result"]
                if task_result and len(task_result) > 0:
                    item = task_result[0]
                    # Extract organic metrics from the response
                    metrics = item.get("metrics", {}).get("organic", {})
                    return {
                        "organic_traffic": metrics.get("etv", 0),  # Estimated Traffic Value
                        "organic_keywords": metrics.get("count", 0),  # Keyword count
                        "pos_1": metrics.get("pos_1", 0),  # Keywords in position 1
                        "pos_2_3": metrics.get("pos_2_3", 0),  # Keywords in positions 2-3
                        "pos_4_10": metrics.get("pos_4_10", 0),  # Keywords in positions 4-10
                    }

            logger.warning(f"No domain overview data for {domain}")
            return None

        except DataForSEOError as e:
            logger.warning(f"Domain overview query failed for '{domain}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in domain overview query for '{domain}': {e}")
            return None

    async def get_backlink_summary(
        self,
        domain: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get backlink summary with domain rating and referring domains.

        Uses DataForSEO Backlinks Summary API.

        Args:
            domain: Target domain

        Returns:
            Dict with domain_rank (DR), referring_domains, backlinks, etc. or None on error
        """
        try:
            result = await self.post(
                "backlinks/summary/live",
                [{
                    "target": domain,
                    "internal_list_limit": 0,  # We don't need internal links
                    "backlinks_status_type": "all",
                }]
            )

            tasks = result.get("tasks", [])
            if tasks and tasks[0].get("result"):
                task_result = tasks[0]["result"]
                if task_result and len(task_result) > 0:
                    item = task_result[0]
                    return {
                        "domain_rank": item.get("rank", 0),  # Domain Rating
                        "referring_domains": item.get("referring_domains", 0),
                        "backlinks": item.get("backlinks", 0),
                        "referring_main_domains": item.get("referring_main_domains", 0),
                        "referring_ips": item.get("referring_ips", 0),
                    }

            logger.warning(f"No backlink summary data for {domain}")
            return None

        except DataForSEOError as e:
            logger.warning(f"Backlink summary query failed for '{domain}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in backlink summary query for '{domain}': {e}")
            return None

    async def get_domain_competitors(
        self,
        domain: str,
        location_code: int = 2840,
        language_name: str = "English",
        limit: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get competitor domains for a target domain.

        Used by Context Intelligence for competitor discovery.

        Args:
            domain: Target domain
            location_code: DataForSEO location code
            language_name: Language name (e.g., "English", "Swedish") - Labs API uses language_name
            limit: Max competitors to return

        Returns:
            List of competitor dicts with domain, metrics, etc.
        """
        try:
            result = await self.post(
                "dataforseo_labs/google/competitors_domain/live",
                [{
                    "target": domain,
                    "location_code": location_code,
                    "language_name": language_name,  # Labs API uses language_name, not language_code
                    "limit": limit,
                }]
            )

            tasks = result.get("tasks", [])
            if tasks and tasks[0].get("result"):
                task_result = tasks[0]["result"]
                if task_result and len(task_result) > 0:
                    items = task_result[0].get("items", [])
                    return [
                        {
                            "domain": item.get("domain", ""),
                            "organic_traffic": item.get("metrics", {}).get("organic", {}).get("etv", 0),
                            "organic_keywords": item.get("metrics", {}).get("organic", {}).get("count", 0),
                            "domain_rank": item.get("avg_position", 0),
                            "intersection_count": item.get("full_domain_metrics", {}).get("organic", {}).get("intersections", 0),
                        }
                        for item in items
                    ]

            return None

        except DataForSEOError as e:
            logger.warning(f"Competitors query failed for '{domain}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in competitors query: {e}")
            return None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def create_client(login: str, password: str) -> DataForSEOClient:
    """Create and return a DataForSEO client."""
    return DataForSEOClient(login=login, password=password)


# ============================================================================
# TESTING
# ============================================================================

async def test_client():
    """Test the client with a simple request."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    
    if not login or not password:
        print("Missing DATAFORSEO_LOGIN or DATAFORSEO_PASSWORD")
        return
    
    async with DataForSEOClient(login=login, password=password) as client:
        # Test with a simple endpoint (Labs API uses language_name, not language_code)
        result = await client.post(
            "dataforseo_labs/google/domain_rank_overview/live",
            [{
                "target": "example.com",
                "location_name": "United States",
                "language_name": "English",  # FIXED: was language_code
            }]
        )
        
        print(f"Status: {result.get('status_code')}")
        print(f"Tasks: {len(result.get('tasks', []))}")
        
        task = result.get("tasks", [{}])[0]
        print(f"Task status: {task.get('status_code')}")


if __name__ == "__main__":
    asyncio.run(test_client())

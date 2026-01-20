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
        
        # Check task-level errors
        tasks = result.get("tasks", [])
        for task in tasks:
            if task.get("status_code") not in [20000, 20100]:
                error_msg = task.get("status_message", "Task error")
                logger.warning(f"Task error in {url}: {error_msg}")
        
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
        # Test with a simple endpoint
        result = await client.post(
            "dataforseo_labs/google/domain_rank_overview/live",
            [{
                "target": "example.com",
                "location_name": "United States",
                "language_code": "en",
            }]
        )
        
        print(f"Status: {result.get('status_code')}")
        print(f"Tasks: {len(result.get('tasks', []))}")
        
        task = result.get("tasks", [{}])[0]
        print(f"Task status: {task.get('status_code')}")


if __name__ == "__main__":
    asyncio.run(test_client())

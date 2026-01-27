"""
External API Configuration

Configuration and factory functions for external API clients.
Loads credentials from environment variables.

Required environment variables:
- PERPLEXITY_API_KEY: Perplexity API key
- FIRECRAWL_API_KEY: Firecrawl API key

Optional:
- PERPLEXITY_MODEL: Model to use (default: sonar)
- PERPLEXITY_ENABLED: Enable Perplexity (default: true)
- FIRECRAWL_ENABLED: Enable Firecrawl (default: true)
"""

import os
import logging
from typing import Optional

from .firecrawl import FirecrawlClient
from .perplexity import PerplexityClient, PerplexityDiscovery

logger = logging.getLogger(__name__)


def get_env_bool(key: str, default: bool = True) -> bool:
    """Get boolean from environment variable."""
    val = os.environ.get(key, "").lower()
    if val in ("false", "0", "no", "off"):
        return False
    if val in ("true", "1", "yes", "on"):
        return True
    return default


class ExternalAPIConfig:
    """Configuration for external APIs."""

    def __init__(
        self,
        perplexity_api_key: Optional[str] = None,
        firecrawl_api_key: Optional[str] = None,
        perplexity_model: str = "sonar",
        perplexity_enabled: bool = True,
        firecrawl_enabled: bool = True,
    ):
        """
        Initialize external API configuration.

        Args:
            perplexity_api_key: Perplexity API key (or from env)
            firecrawl_api_key: Firecrawl API key (or from env)
            perplexity_model: Perplexity model to use
            perplexity_enabled: Whether Perplexity is enabled
            firecrawl_enabled: Whether Firecrawl is enabled
        """
        self.perplexity_api_key = perplexity_api_key or os.environ.get("PERPLEXITY_API_KEY")
        self.firecrawl_api_key = firecrawl_api_key or os.environ.get("FIRECRAWL_API_KEY")
        self.perplexity_model = perplexity_model or os.environ.get("PERPLEXITY_MODEL", "sonar")
        self.perplexity_enabled = perplexity_enabled and get_env_bool("PERPLEXITY_ENABLED", True)
        self.firecrawl_enabled = firecrawl_enabled and get_env_bool("FIRECRAWL_ENABLED", True)

    @property
    def has_perplexity(self) -> bool:
        """Check if Perplexity is configured and enabled."""
        return self.perplexity_enabled and bool(self.perplexity_api_key)

    @property
    def has_firecrawl(self) -> bool:
        """Check if Firecrawl is configured and enabled."""
        return self.firecrawl_enabled and bool(self.firecrawl_api_key)

    def log_status(self):
        """Log configuration status."""
        logger.info(
            f"External API status: "
            f"Perplexity={'enabled' if self.has_perplexity else 'disabled'}, "
            f"Firecrawl={'enabled' if self.has_firecrawl else 'disabled'}"
        )


class ExternalAPIClients:
    """
    Factory and manager for external API clients.

    Usage:
        config = ExternalAPIConfig()
        clients = ExternalAPIClients(config)

        # Use clients
        if clients.perplexity:
            result = await clients.perplexity.query("...")

        # Cleanup
        await clients.close()
    """

    def __init__(self, config: Optional[ExternalAPIConfig] = None):
        """
        Initialize external API clients.

        Args:
            config: API configuration (defaults to env-based config)
        """
        self.config = config or ExternalAPIConfig()
        self._perplexity: Optional[PerplexityClient] = None
        self._firecrawl: Optional[FirecrawlClient] = None
        self._perplexity_discovery: Optional[PerplexityDiscovery] = None

    @property
    def perplexity(self) -> Optional[PerplexityClient]:
        """Get or create Perplexity client."""
        if not self.config.has_perplexity:
            return None

        if self._perplexity is None:
            self._perplexity = PerplexityClient(
                api_key=self.config.perplexity_api_key,
                default_model=self.config.perplexity_model,
            )
            logger.info("Initialized Perplexity client")

        return self._perplexity

    @property
    def perplexity_discovery(self) -> Optional[PerplexityDiscovery]:
        """Get or create Perplexity discovery service."""
        if not self.perplexity:
            return None

        if self._perplexity_discovery is None:
            self._perplexity_discovery = PerplexityDiscovery(self.perplexity)
            logger.info("Initialized Perplexity discovery service")

        return self._perplexity_discovery

    @property
    def firecrawl(self) -> Optional[FirecrawlClient]:
        """Get or create Firecrawl client."""
        if not self.config.has_firecrawl:
            return None

        if self._firecrawl is None:
            self._firecrawl = FirecrawlClient(
                api_key=self.config.firecrawl_api_key,
            )
            logger.info("Initialized Firecrawl client")

        return self._firecrawl

    async def close(self):
        """Close all clients."""
        if self._perplexity:
            await self._perplexity.close()
            self._perplexity = None

        if self._firecrawl:
            await self._firecrawl.close()
            self._firecrawl = None

        logger.info("Closed external API clients")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions

def create_perplexity_client(
    api_key: Optional[str] = None,
    model: str = "sonar",
) -> Optional[PerplexityClient]:
    """
    Create a Perplexity client.

    Args:
        api_key: API key (defaults to PERPLEXITY_API_KEY env var)
        model: Model to use

    Returns:
        PerplexityClient or None if not configured
    """
    key = api_key or os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        logger.warning("Perplexity API key not configured")
        return None

    return PerplexityClient(api_key=key, default_model=model)


def create_firecrawl_client(
    api_key: Optional[str] = None,
) -> Optional[FirecrawlClient]:
    """
    Create a Firecrawl client.

    Args:
        api_key: API key (defaults to FIRECRAWL_API_KEY env var)

    Returns:
        FirecrawlClient or None if not configured
    """
    key = api_key or os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        logger.warning("Firecrawl API key not configured")
        return None

    return FirecrawlClient(api_key=key)

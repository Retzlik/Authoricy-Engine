"""
External API Integrations

Clients for third-party APIs used in competitor intelligence:
- Firecrawl: Website scraping for context acquisition
- Perplexity: AI-powered competitor discovery
- Config: Unified configuration and client management
"""

from .firecrawl import FirecrawlClient, FirecrawlError, WebsiteScraper
from .perplexity import (
    PerplexityClient,
    PerplexityError,
    PerplexityDiscovery,
    PerplexityResult,
    DiscoveredCompetitor,
)
from .config import (
    ExternalAPIConfig,
    ExternalAPIClients,
    create_perplexity_client,
    create_firecrawl_client,
)

__all__ = [
    # Firecrawl
    "FirecrawlClient",
    "FirecrawlError",
    "WebsiteScraper",
    # Perplexity
    "PerplexityClient",
    "PerplexityError",
    "PerplexityDiscovery",
    "PerplexityResult",
    "DiscoveredCompetitor",
    # Config
    "ExternalAPIConfig",
    "ExternalAPIClients",
    "create_perplexity_client",
    "create_firecrawl_client",
]

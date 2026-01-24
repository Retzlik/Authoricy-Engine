"""
Sitemap Parser for Context Intelligence

Fetches and parses XML sitemaps to discover all pages on a website.
This provides comprehensive page discovery instead of guessing URLs.

Supports:
- Standard sitemap.xml
- Sitemap index files (sitemap_index.xml)
- Robots.txt sitemap directives
- Compressed sitemaps (.gz)
"""

import gzip
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SitemapUrl:
    """Represents a URL from a sitemap."""
    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None

    @property
    def path(self) -> str:
        """Extract the path from the URL."""
        return urlparse(self.loc).path

    @property
    def is_homepage(self) -> bool:
        """Check if this is the homepage."""
        path = self.path.rstrip("/")
        return path == "" or path == "/"


@dataclass
class SitemapResult:
    """Result of sitemap parsing."""
    urls: List[SitemapUrl] = field(default_factory=list)
    sitemap_found: bool = False
    sitemap_location: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    # Categorized URLs for easy access
    about_pages: List[str] = field(default_factory=list)
    pricing_pages: List[str] = field(default_factory=list)
    product_pages: List[str] = field(default_factory=list)
    blog_pages: List[str] = field(default_factory=list)
    contact_pages: List[str] = field(default_factory=list)
    category_pages: List[str] = field(default_factory=list)

    # Detected patterns
    detected_languages: Set[str] = field(default_factory=set)
    has_blog: bool = False
    has_shop: bool = False
    has_multilingual: bool = False

    @property
    def total_pages(self) -> int:
        return len(self.urls)


# URL categorization patterns - supports multiple languages
URL_PATTERNS = {
    "about": [
        r"/about/?$", r"/about-us/?$", r"/company/?$", r"/who-we-are/?$",
        r"/om-oss/?$", r"/om/?$", r"/foretaget/?$", r"/om-foretaget/?$",  # Swedish
        r"/uber-uns/?$", r"/ueber-uns/?$", r"/unternehmen/?$",  # German
        r"/a-propos/?$", r"/qui-sommes-nous/?$",  # French
        r"/om-os/?$", r"/virksomhed/?$",  # Danish
        r"/om-oss/?$", r"/bedrift/?$",  # Norwegian
        r"/tietoa-meista/?$", r"/yritys/?$",  # Finnish
    ],
    "pricing": [
        r"/pricing/?$", r"/plans/?$", r"/prices/?$",
        r"/priser/?$", r"/prislistor/?$", r"/prislista/?$",  # Swedish
        r"/preise/?$", r"/preisliste/?$",  # German
        r"/tarifs/?$", r"/prix/?$",  # French
        r"/priser/?$",  # Danish/Norwegian
        r"/hinnat/?$", r"/hinnasto/?$",  # Finnish
    ],
    "product": [
        r"/product", r"/products", r"/shop", r"/store",
        r"/produkt", r"/produkter", r"/butik",  # Swedish
        r"/produkte", r"/laden",  # German
        r"/produit", r"/boutique",  # French
        r"/tuotteet", r"/kauppa",  # Finnish
    ],
    "blog": [
        r"/blog", r"/articles", r"/news", r"/insights", r"/resources",
        r"/blogg", r"/artiklar", r"/nyheter",  # Swedish
        r"/artikel", r"/nachrichten",  # German
        r"/actualites", r"/nouvelles",  # French
    ],
    "contact": [
        r"/contact/?$", r"/contact-us/?$",
        r"/kontakt/?$", r"/kontakta-oss/?$",  # Swedish
        r"/kontakt/?$",  # German
        r"/yhteystiedot/?$", r"/ota-yhteytta/?$",  # Finnish
    ],
    "category": [
        r"/category/", r"/categories/", r"/cat/",
        r"/kategori/", r"/kategorier/",  # Swedish
        r"/kategorie/",  # German
    ],
}

# Language detection from URL patterns
LANGUAGE_PATTERNS = {
    "sv": [r"^/sv/", r"^/se/", r"/sv-se/", r"\.se/"],
    "en": [r"^/en/", r"^/en-", r"/en-us/", r"/en-gb/"],
    "de": [r"^/de/", r"^/de-", r"/de-de/", r"/de-at/", r"/de-ch/"],
    "fr": [r"^/fr/", r"^/fr-", r"/fr-fr/", r"/fr-ca/"],
    "no": [r"^/no/", r"^/nb/", r"/no-no/", r"/nb-no/"],
    "da": [r"^/da/", r"^/dk/", r"/da-dk/"],
    "fi": [r"^/fi/", r"/fi-fi/"],
    "nl": [r"^/nl/", r"/nl-nl/", r"/nl-be/"],
    "es": [r"^/es/", r"/es-es/"],
    "it": [r"^/it/", r"/it-it/"],
}


class SitemapParser:
    """
    Parses XML sitemaps to discover all pages on a website.

    Usage:
        parser = SitemapParser()
        result = await parser.parse("https://example.com")
        print(f"Found {result.total_pages} pages")
        print(f"About pages: {result.about_pages}")
    """

    def __init__(self, timeout: float = 15.0, max_urls: int = 5000):
        self.timeout = timeout
        self.max_urls = max_urls
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AuthoricyBot/1.0; +https://authoricy.ai)",
                "Accept": "application/xml,text/xml,*/*",
            },
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def parse(self, base_url: str) -> SitemapResult:
        """
        Parse sitemap for a domain.

        Tries multiple strategies:
        1. /sitemap.xml
        2. /sitemap_index.xml
        3. Check robots.txt for sitemap location

        Args:
            base_url: Base URL of the site (e.g., "https://example.com")

        Returns:
            SitemapResult with all discovered URLs
        """
        result = SitemapResult()

        # Normalize base URL
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        base_url = base_url.rstrip("/")

        # Strategy 1: Try standard sitemap.xml
        sitemap_url = f"{base_url}/sitemap.xml"
        urls = await self._fetch_and_parse_sitemap(sitemap_url, result)

        if urls:
            result.sitemap_found = True
            result.sitemap_location = sitemap_url
            result.urls = urls
            self._categorize_urls(result)
            logger.info(f"Found sitemap at {sitemap_url} with {len(urls)} URLs")
            return result

        # Strategy 2: Try sitemap_index.xml
        sitemap_url = f"{base_url}/sitemap_index.xml"
        urls = await self._fetch_and_parse_sitemap(sitemap_url, result)

        if urls:
            result.sitemap_found = True
            result.sitemap_location = sitemap_url
            result.urls = urls
            self._categorize_urls(result)
            logger.info(f"Found sitemap index at {sitemap_url} with {len(urls)} URLs")
            return result

        # Strategy 3: Check robots.txt
        robots_url = f"{base_url}/robots.txt"
        sitemap_from_robots = await self._find_sitemap_in_robots(robots_url)

        if sitemap_from_robots:
            urls = await self._fetch_and_parse_sitemap(sitemap_from_robots, result)
            if urls:
                result.sitemap_found = True
                result.sitemap_location = sitemap_from_robots
                result.urls = urls
                self._categorize_urls(result)
                logger.info(f"Found sitemap from robots.txt: {sitemap_from_robots} with {len(urls)} URLs")
                return result

        # No sitemap found
        logger.warning(f"No sitemap found for {base_url}")
        result.errors.append("No sitemap found")
        return result

    async def _fetch_and_parse_sitemap(
        self,
        url: str,
        result: SitemapResult
    ) -> List[SitemapUrl]:
        """Fetch and parse a sitemap URL."""
        try:
            response = await self.client.get(url)

            if response.status_code != 200:
                return []

            content = response.content

            # Handle gzipped content
            if url.endswith(".gz") or response.headers.get("content-encoding") == "gzip":
                try:
                    content = gzip.decompress(content)
                except Exception:
                    pass  # Not actually gzipped

            # Parse XML
            return await self._parse_sitemap_xml(content.decode("utf-8", errors="ignore"), result)

        except httpx.RequestError as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error parsing sitemap {url}: {e}")
            return []

    async def _parse_sitemap_xml(
        self,
        xml_content: str,
        result: SitemapResult
    ) -> List[SitemapUrl]:
        """Parse sitemap XML content."""
        urls = []

        try:
            # Remove XML namespace for easier parsing
            xml_content = re.sub(r'\sxmlns="[^"]+"', '', xml_content)
            root = ET.fromstring(xml_content)

            # Check if this is a sitemap index
            if root.tag == "sitemapindex" or root.find(".//sitemap") is not None:
                # This is an index - recursively fetch child sitemaps
                for sitemap_elem in root.findall(".//sitemap"):
                    loc_elem = sitemap_elem.find("loc")
                    if loc_elem is not None and loc_elem.text:
                        child_urls = await self._fetch_and_parse_sitemap(
                            loc_elem.text.strip(),
                            result
                        )
                        urls.extend(child_urls)

                        # Respect max URLs limit
                        if len(urls) >= self.max_urls:
                            break
            else:
                # This is a regular sitemap
                for url_elem in root.findall(".//url"):
                    if len(urls) >= self.max_urls:
                        break

                    loc_elem = url_elem.find("loc")
                    if loc_elem is None or not loc_elem.text:
                        continue

                    sitemap_url = SitemapUrl(loc=loc_elem.text.strip())

                    # Extract optional fields
                    lastmod_elem = url_elem.find("lastmod")
                    if lastmod_elem is not None and lastmod_elem.text:
                        sitemap_url.lastmod = lastmod_elem.text.strip()

                    changefreq_elem = url_elem.find("changefreq")
                    if changefreq_elem is not None and changefreq_elem.text:
                        sitemap_url.changefreq = changefreq_elem.text.strip()

                    priority_elem = url_elem.find("priority")
                    if priority_elem is not None and priority_elem.text:
                        try:
                            sitemap_url.priority = float(priority_elem.text.strip())
                        except ValueError:
                            pass

                    urls.append(sitemap_url)

        except ET.ParseError as e:
            logger.warning(f"XML parse error: {e}")
            result.errors.append(f"XML parse error: {e}")

        return urls

    async def _find_sitemap_in_robots(self, robots_url: str) -> Optional[str]:
        """Find sitemap URL from robots.txt."""
        try:
            response = await self.client.get(robots_url)

            if response.status_code != 200:
                return None

            content = response.text

            # Look for Sitemap: directive
            for line in content.split("\n"):
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    if sitemap_url.startswith("http"):
                        return sitemap_url

            return None

        except Exception:
            return None

    def _categorize_urls(self, result: SitemapResult):
        """Categorize URLs by type and detect patterns."""
        for sitemap_url in result.urls:
            path = sitemap_url.path.lower()

            # Categorize by page type
            for category, patterns in URL_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, path, re.IGNORECASE):
                        category_list = getattr(result, f"{category}_pages", None)
                        if category_list is not None:
                            category_list.append(sitemap_url.loc)
                        break

            # Detect languages
            for lang, patterns in LANGUAGE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, path):
                        result.detected_languages.add(lang)
                        break

        # Set flags
        result.has_blog = len(result.blog_pages) > 0
        result.has_shop = len(result.product_pages) > 10
        result.has_multilingual = len(result.detected_languages) > 1

        # Sort pages by priority (highest first)
        result.urls.sort(
            key=lambda u: (u.priority or 0.5, u.is_homepage),
            reverse=True
        )


async def discover_site_pages(domain: str) -> SitemapResult:
    """
    Convenience function to discover all pages on a site.

    Args:
        domain: Domain to analyze (e.g., "example.com")

    Returns:
        SitemapResult with categorized URLs
    """
    parser = SitemapParser()
    try:
        return await parser.parse(domain)
    finally:
        await parser.close()

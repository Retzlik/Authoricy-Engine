"""
Domain Filtering Utilities

Shared domain exclusion logic used across all competitor identification paths:
- Phase 1 data collection
- Context Intelligence discovery
- SERP analysis
- User-provided competitors

This ensures platforms like Facebook, YouTube, etc. are NEVER included as competitors
regardless of how they were discovered.
"""

import re
from typing import Set, Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# EXCLUDED DOMAINS - Comprehensive list of non-competitor platforms
# =============================================================================

# Social Media Platforms
SOCIAL_MEDIA = {
    "facebook.com", "fb.com", "fb.me",
    "twitter.com", "x.com", "t.co",
    "instagram.com", "instagr.am",
    "linkedin.com", "lnkd.in",
    "tiktok.com",
    "pinterest.com", "pin.it",
    "reddit.com", "redd.it",
    "tumblr.com",
    "snapchat.com",
    "threads.net",
    "mastodon.social",
    "discord.com", "discord.gg",
    "whatsapp.com",
    "telegram.org", "t.me",
    "wechat.com", "weixin.qq.com",
}

# Video & Media Platforms
VIDEO_PLATFORMS = {
    "youtube.com", "youtu.be",
    "vimeo.com",
    "dailymotion.com",
    "twitch.tv",
    "tiktok.com",
    "rumble.com",
    "bitchute.com",
}

# Tech Giants & General Platforms
TECH_GIANTS = {
    "google.com", "google.se", "google.co.uk", "google.de", "google.fr",
    "googleapis.com", "googleusercontent.com",
    "apple.com", "icloud.com",
    "microsoft.com", "live.com", "outlook.com", "bing.com",
    "amazon.com", "amazon.se", "amazon.co.uk", "amazon.de", "aws.amazon.com",
    "meta.com",
    "oracle.com",
    "salesforce.com",
    "adobe.com",
}

# E-commerce Marketplaces (generic, not niche competitors)
MARKETPLACES = {
    "ebay.com", "ebay.se", "ebay.co.uk", "ebay.de",
    "etsy.com",
    "aliexpress.com", "alibaba.com",
    "wish.com",
    "walmart.com",
    "target.com",
    "bestbuy.com",
}

# Reference & Educational Sites
REFERENCE_SITES = {
    "wikipedia.org", "wikimedia.org", "wiktionary.org", "wikihow.com",
    "britannica.com",
    "quora.com",
    "stackoverflow.com", "stackexchange.com",
    "github.com", "gitlab.com", "bitbucket.org",
    "medium.com",
    "substack.com",
}

# News & Media Organizations
NEWS_MEDIA = {
    # International
    "bbc.com", "bbc.co.uk",
    "cnn.com",
    "nytimes.com",
    "theguardian.com",
    "reuters.com",
    "bloomberg.com",
    "forbes.com",
    "huffpost.com",
    "washingtonpost.com",
    "wsj.com",
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "mashable.com",
    # Swedish News & Media
    "aftonbladet.se",
    "expressen.se",
    "dn.se", "dagensnyheter.se",
    "svd.se", "svenskadagbladet.se",
    "svt.se",  # Swedish public TV
    "sverigesradio.se", "sr.se",  # Swedish public radio
    "tv4.se",
    "omni.se",
    "nyheter24.se",
    "metro.se",
    # Norwegian News
    "vg.no",
    "dagbladet.no",
    "nrk.no",  # Norwegian public broadcasting
    "aftenposten.no",
    # Danish News
    "dr.dk",  # Danish public broadcasting
    "politiken.dk",
    "berlingske.dk",
    "bt.dk",
    # Finnish News
    "yle.fi",  # Finnish public broadcasting
    "hs.fi", "helsinkisanomat.fi",
    "iltalehti.fi",
    # German News
    "spiegel.de",
    "bild.de",
    "zeit.de",
    "sueddeutsche.de",
    "faz.net",
    "tagesschau.de",  # German public news
}

# Swedish/Nordic Government & Official Sites
NORDIC_GOVERNMENT = {
    # Swedish Government
    "krisinformation.se",  # Swedish crisis information
    "msb.se",  # Swedish Civil Contingencies Agency
    "regeringen.se",  # Swedish government
    "riksdagen.se",  # Swedish parliament
    "folkhalsomyndigheten.se",  # Public Health Agency
    "forsakringskassan.se",  # Social insurance
    "skatteverket.se",  # Tax agency
    "arbetsformedlingen.se",  # Employment agency
    "polisen.se",  # Police
    "transportstyrelsen.se",  # Transport agency
    "naturvardsverket.se",  # Environmental agency
    "livsmedelsverket.se",  # Food agency
    "socialstyrelsen.se",  # Health/social affairs
    "konsumentverket.se",  # Consumer agency
    "1177.se",  # Healthcare info
    # Norwegian Government
    "regjeringen.no",
    "stortinget.no",
    "nav.no",
    "helsedirektoratet.no",
    # Danish Government
    "borger.dk",
    "retsinformation.dk",
    "sst.dk",
    # Finnish Government
    "suomi.fi",
    "finlex.fi",
}

# Government & Official Sites (patterns)
GOVERNMENT_PATTERNS = {
    ".gov",
    ".gov.",
    ".edu",
    ".mil",
    ".org.uk",  # Many UK government sites
}

# Review & Directory Sites
REVIEW_DIRECTORIES = {
    "yelp.com",
    "tripadvisor.com",
    "trustpilot.com",
    "g2.com", "g2crowd.com",
    "capterra.com",
    "glassdoor.com",
    "indeed.com",
    "yellowpages.com",
    "crunchbase.com",
}

# Combine all into master set
EXCLUDED_DOMAINS: Set[str] = (
    SOCIAL_MEDIA |
    VIDEO_PLATFORMS |
    TECH_GIANTS |
    MARKETPLACES |
    REFERENCE_SITES |
    NEWS_MEDIA |
    NORDIC_GOVERNMENT |
    REVIEW_DIRECTORIES
)


def is_excluded_domain(domain: Optional[str]) -> bool:
    """
    Check if a domain should be excluded from competitor analysis.

    Uses multiple matching strategies:
    1. Exact match against known domains
    2. Subdomain matching (business.facebook.com -> facebook.com)
    3. Government/educational TLD patterns

    Args:
        domain: Domain name to check (e.g., "facebook.com", "business.facebook.com")

    Returns:
        True if domain should be excluded, False if it's a valid competitor candidate
    """
    if not domain:
        return True

    domain_lower = domain.lower().strip()

    # Remove www. prefix if present
    if domain_lower.startswith("www."):
        domain_lower = domain_lower[4:]

    # Strategy 1: Exact match
    if domain_lower in EXCLUDED_DOMAINS:
        return True

    # Strategy 2: Check if it's a subdomain of an excluded domain
    # e.g., "business.facebook.com" contains "facebook.com"
    for excluded in EXCLUDED_DOMAINS:
        # Check if domain ends with .excluded (subdomain match)
        if domain_lower.endswith("." + excluded):
            return True
        # Check if the base domain matches
        if domain_lower == excluded:
            return True

    # Strategy 3: Government/educational TLD patterns
    for pattern in GOVERNMENT_PATTERNS:
        if pattern in domain_lower:
            return True

    # Strategy 4: Check for common platform indicators in domain
    platform_indicators = [
        "facebook", "youtube", "twitter", "instagram", "linkedin",
        "tiktok", "pinterest", "reddit", "tumblr", "snapchat",
        "wikipedia", "google", "amazon", "microsoft", "apple",
    ]

    # Extract base domain name (without TLD)
    domain_parts = domain_lower.split(".")
    if len(domain_parts) >= 2:
        base_name = domain_parts[-2]  # e.g., "facebook" from "facebook.com"
        if base_name in platform_indicators:
            return True

    return False


def filter_competitor_domains(domains: list, source: str = "unknown") -> list:
    """
    Filter a list of competitor domains, removing excluded platforms.

    Args:
        domains: List of domain strings or dicts with 'domain' key
        source: Description of where these domains came from (for logging)

    Returns:
        Filtered list with excluded domains removed
    """
    filtered = []
    excluded_count = 0

    for item in domains:
        # Handle both string domains and dict items
        if isinstance(item, str):
            domain = item
        elif isinstance(item, dict):
            domain = item.get("domain", "")
        else:
            continue

        if is_excluded_domain(domain):
            excluded_count += 1
            logger.debug(f"Excluded platform domain from {source}: {domain}")
        else:
            filtered.append(item)

    if excluded_count > 0:
        logger.info(f"Filtered {excluded_count} platform domains from {source}")

    return filtered


def get_exclusion_reason(domain: str) -> Optional[str]:
    """
    Get the reason why a domain is excluded.

    Useful for user feedback on why their provided competitor was rejected.

    Args:
        domain: Domain to check

    Returns:
        Reason string if excluded, None if valid competitor
    """
    if not domain:
        return "Empty domain"

    domain_lower = domain.lower().strip()
    if domain_lower.startswith("www."):
        domain_lower = domain_lower[4:]

    # Check categories
    if domain_lower in SOCIAL_MEDIA or any(domain_lower.endswith("." + d) for d in SOCIAL_MEDIA):
        return "Social media platform"

    if domain_lower in VIDEO_PLATFORMS or any(domain_lower.endswith("." + d) for d in VIDEO_PLATFORMS):
        return "Video/media platform"

    if domain_lower in TECH_GIANTS or any(domain_lower.endswith("." + d) for d in TECH_GIANTS):
        return "Technology platform"

    if domain_lower in MARKETPLACES or any(domain_lower.endswith("." + d) for d in MARKETPLACES):
        return "E-commerce marketplace"

    if domain_lower in REFERENCE_SITES or any(domain_lower.endswith("." + d) for d in REFERENCE_SITES):
        return "Reference/educational site"

    if domain_lower in NEWS_MEDIA or any(domain_lower.endswith("." + d) for d in NEWS_MEDIA):
        return "News/media organization"

    if domain_lower in NORDIC_GOVERNMENT or any(domain_lower.endswith("." + d) for d in NORDIC_GOVERNMENT):
        return "Government/official site"

    if domain_lower in REVIEW_DIRECTORIES or any(domain_lower.endswith("." + d) for d in REVIEW_DIRECTORIES):
        return "Review/directory site"

    for pattern in GOVERNMENT_PATTERNS:
        if pattern in domain_lower:
            return "Government/official site"

    return None

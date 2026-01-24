"""
Market Detection Module

Detects target market(s) from website signals, not assumptions.

Philosophy:
- Detect + Confirm > Ask
- Structured signals > Guessing
- On-site evidence > Modeled traffic
- User override > Everything else

Signal sources (in order of weight):
1. Schema.org Organization.address.addressCountry (0.85)
2. Shipping/delivery page country mentions (0.75)
3. hreflang tags (0.70)
4. TLD for ccTLDs like .co.uk, .de (0.65)
5. Phone country codes (0.50)
6. VAT/tax mentions (0.50)
7. Store selector presence (0.45)
8. Currency symbols (0.40)
9. Language alone (0.25)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# MARKET CONFIGURATION
# =============================================================================

# Full market configuration with DataForSEO codes
MARKET_CONFIG = {
    "us": {
        "name": "United States",
        "location_code": 2840,
        "language_code": "en",
        "language_name": "English",
        "currency": "$",
        "currency_code": "USD",
        "phone_prefix": "+1",
        "tlds": [".com", ".us"],
        "vat_terms": [],
    },
    "uk": {
        "name": "United Kingdom",
        "location_code": 2826,
        "language_code": "en",
        "language_name": "English",
        "currency": "£",
        "currency_code": "GBP",
        "phone_prefix": "+44",
        "tlds": [".co.uk", ".uk"],
        "vat_terms": ["vat", "inc. vat", "excl. vat", "plus vat"],
    },
    "se": {
        "name": "Sweden",
        "location_code": 2752,
        "language_code": "sv",
        "language_name": "Swedish",
        "currency": "kr",
        "currency_code": "SEK",
        "phone_prefix": "+46",
        "tlds": [".se"],
        "vat_terms": ["moms", "inkl. moms", "exkl. moms"],
    },
    "de": {
        "name": "Germany",
        "location_code": 2276,
        "language_code": "de",
        "language_name": "German",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+49",
        "tlds": [".de"],
        "vat_terms": ["mwst", "inkl. mwst", "zzgl. mwst", "ust"],
    },
    "fr": {
        "name": "France",
        "location_code": 2250,
        "language_code": "fr",
        "language_name": "French",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+33",
        "tlds": [".fr"],
        "vat_terms": ["tva", "ttc", "ht"],
    },
    "no": {
        "name": "Norway",
        "location_code": 2578,
        "language_code": "no",
        "language_name": "Norwegian",
        "currency": "kr",
        "currency_code": "NOK",
        "phone_prefix": "+47",
        "tlds": [".no"],
        "vat_terms": ["mva", "inkl. mva"],
    },
    "dk": {
        "name": "Denmark",
        "location_code": 2208,
        "language_code": "da",
        "language_name": "Danish",
        "currency": "kr",
        "currency_code": "DKK",
        "phone_prefix": "+45",
        "tlds": [".dk"],
        "vat_terms": ["moms", "inkl. moms"],
    },
    "fi": {
        "name": "Finland",
        "location_code": 2246,
        "language_code": "fi",
        "language_name": "Finnish",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+358",
        "tlds": [".fi"],
        "vat_terms": ["alv", "sis. alv"],
    },
    "nl": {
        "name": "Netherlands",
        "location_code": 2528,
        "language_code": "nl",
        "language_name": "Dutch",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+31",
        "tlds": [".nl"],
        "vat_terms": ["btw", "incl. btw", "excl. btw"],
    },
    "es": {
        "name": "Spain",
        "location_code": 2724,
        "language_code": "es",
        "language_name": "Spanish",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+34",
        "tlds": [".es"],
        "vat_terms": ["iva", "incl. iva"],
    },
    "it": {
        "name": "Italy",
        "location_code": 2380,
        "language_code": "it",
        "language_name": "Italian",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+39",
        "tlds": [".it"],
        "vat_terms": ["iva", "incl. iva"],
    },
    "au": {
        "name": "Australia",
        "location_code": 2036,
        "language_code": "en",
        "language_name": "English",
        "currency": "$",
        "currency_code": "AUD",
        "phone_prefix": "+61",
        "tlds": [".com.au", ".au"],
        "vat_terms": ["gst", "incl. gst"],
    },
    "ca": {
        "name": "Canada",
        "location_code": 2124,
        "language_code": "en",
        "language_name": "English",
        "currency": "$",
        "currency_code": "CAD",
        "phone_prefix": "+1",
        "tlds": [".ca"],
        "vat_terms": ["gst", "hst", "pst"],
    },
    "ie": {
        "name": "Ireland",
        "location_code": 2372,
        "language_code": "en",
        "language_name": "English",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+353",
        "tlds": [".ie"],
        "vat_terms": ["vat", "incl. vat"],
    },
    "at": {
        "name": "Austria",
        "location_code": 2040,
        "language_code": "de",
        "language_name": "German",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+43",
        "tlds": [".at"],
        "vat_terms": ["mwst", "ust", "inkl. mwst"],
    },
    "ch": {
        "name": "Switzerland",
        "location_code": 2756,
        "language_code": "de",
        "language_name": "German",
        "currency": "CHF",
        "currency_code": "CHF",
        "phone_prefix": "+41",
        "tlds": [".ch"],
        "vat_terms": ["mwst", "tva", "iva"],
    },
    "be": {
        "name": "Belgium",
        "location_code": 2056,
        "language_code": "nl",
        "language_name": "Dutch",
        "currency": "€",
        "currency_code": "EUR",
        "phone_prefix": "+32",
        "tlds": [".be"],
        "vat_terms": ["btw", "tva"],
    },
    "nz": {
        "name": "New Zealand",
        "location_code": 2554,
        "language_code": "en",
        "language_name": "English",
        "currency": "$",
        "currency_code": "NZD",
        "phone_prefix": "+64",
        "tlds": [".nz", ".co.nz"],
        "vat_terms": ["gst", "incl. gst"],
    },
}

# TLD to market mapping (ccTLDs only)
TLD_TO_MARKET = {}
for market_code, config in MARKET_CONFIG.items():
    for tld in config.get("tlds", []):
        if tld not in [".com"]:  # .com is not country-specific
            TLD_TO_MARKET[tld] = market_code

# Phone prefix to market
PHONE_PREFIX_TO_MARKET = {
    config["phone_prefix"]: market_code
    for market_code, config in MARKET_CONFIG.items()
}

# hreflang region code to market
HREFLANG_TO_MARKET = {
    "gb": "uk", "uk": "uk",
    "us": "us",
    "se": "se",
    "de": "de",
    "fr": "fr",
    "no": "no",
    "dk": "dk",
    "fi": "fi",
    "nl": "nl",
    "es": "es",
    "it": "it",
    "au": "au",
    "ca": "ca",
    "ie": "ie",
    "at": "at",
    "ch": "ch",
    "be": "be",
    "nz": "nz",
}


# =============================================================================
# SIGNAL MODELS
# =============================================================================


class SignalKind(str, Enum):
    """Types of market signals we can detect."""
    TLD = "tld"
    HREFLANG = "hreflang"
    SCHEMA_ORG = "schema_org"
    CURRENCY = "currency"
    PHONE = "phone"
    SHIPPING = "shipping"
    VAT = "vat"
    ADDRESS = "address"
    STORE_SELECTOR = "store_selector"
    GEO_BANNER = "geo_banner"
    LANGUAGE = "language"


# Signal weights - calibrated based on reliability
SIGNAL_WEIGHTS = {
    SignalKind.SCHEMA_ORG: 0.85,    # Very reliable, explicit
    SignalKind.SHIPPING: 0.75,      # Strong commercial intent
    SignalKind.HREFLANG: 0.70,      # Explicit SEO config
    SignalKind.TLD: 0.65,           # Strong but can be legacy
    SignalKind.ADDRESS: 0.60,       # Physical location
    SignalKind.PHONE: 0.50,         # Moderate signal
    SignalKind.VAT: 0.50,           # Tax jurisdiction
    SignalKind.STORE_SELECTOR: 0.45, # Multi-market indicator
    SignalKind.CURRENCY: 0.40,      # Weak alone ($ used globally)
    SignalKind.GEO_BANNER: 0.40,    # Usually multi-market
    SignalKind.LANGUAGE: 0.25,      # Weakest (English everywhere)
}


@dataclass
class MarketSignal:
    """
    A single market signal with full evidence trail.

    This structured format enables:
    - Explainability: "We detected UK because..."
    - Debugging: Trace why a detection was wrong
    - Auditing: Store with analysis for reference
    """
    kind: SignalKind
    market_code: str          # "uk", "us", etc.
    value: str                # The raw value found ("+44", "GBP", etc.)
    weight: float             # Signal weight (from SIGNAL_WEIGHTS)
    evidence: str             # HTML snippet or extracted text
    source_url: str           # Page where found
    confidence: float = 1.0   # Optional confidence modifier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "market_code": self.market_code,
            "value": self.value,
            "weight": self.weight,
            "evidence": self.evidence[:200] if self.evidence else "",
            "source_url": self.source_url,
            "confidence": self.confidence,
        }


@dataclass
class DetectedMarket:
    """
    A market detected from website signals.

    Includes full evidence trail for explainability.
    """
    code: str                 # "uk"
    name: str                 # "United Kingdom"
    confidence: float         # 0.0-1.0
    signals: List[MarketSignal] = field(default_factory=list)

    # DataForSEO parameters (resolved from MARKET_CONFIG)
    location_code: int = 0
    language_code: str = ""
    language_name: str = ""

    def __post_init__(self):
        """Fill in DataForSEO params from config."""
        if self.code in MARKET_CONFIG:
            config = MARKET_CONFIG[self.code]
            self.location_code = config["location_code"]
            self.language_code = config["language_code"]
            self.language_name = config["language_name"]
            if not self.name:
                self.name = config["name"]

    @property
    def top_signals(self) -> List[MarketSignal]:
        """Top 3 signals by weight."""
        return sorted(self.signals, key=lambda s: s.weight, reverse=True)[:3]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "confidence": self.confidence,
            "location_code": self.location_code,
            "language_code": self.language_code,
            "language_name": self.language_name,
            "signals": [s.to_dict() for s in self.signals],
        }


@dataclass
class MarketDetectionResult:
    """
    Complete result of market detection.

    Contains:
    - primary: Best detected market
    - candidates: Other possible markets (ranked by confidence)
    - needs_confirmation: Whether UI should ask user
    - is_multi_market_site: True if site targets multiple markets
    - all_signals: Full evidence for debugging
    """
    # Primary detection
    primary: DetectedMarket

    # Other candidates (ranked by confidence)
    candidates: List[DetectedMarket] = field(default_factory=list)

    # Confirmation flags
    needs_confirmation: bool = False
    confirmation_reason: str = ""

    # Multi-market detection
    is_multi_market_site: bool = False
    hreflang_markets: List[str] = field(default_factory=list)

    # Full evidence trail
    all_signals: List[MarketSignal] = field(default_factory=list)
    pages_checked: List[str] = field(default_factory=list)

    # Conflicts detected
    has_conflicts: bool = False
    conflict_description: str = ""

    # Metadata
    detection_time_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary.to_dict(),
            "candidates": [c.to_dict() for c in self.candidates],
            "needs_confirmation": self.needs_confirmation,
            "confirmation_reason": self.confirmation_reason,
            "is_multi_market_site": self.is_multi_market_site,
            "hreflang_markets": self.hreflang_markets,
            "pages_checked": self.pages_checked,
            "has_conflicts": self.has_conflicts,
            "conflict_description": self.conflict_description,
            "detection_time_ms": self.detection_time_ms,
            "signal_count": len(self.all_signals),
        }

    def get_explanation(self) -> str:
        """Generate human-readable explanation of detection."""
        if not self.primary.signals:
            return f"Detected {self.primary.name} with low confidence (no strong signals found)."

        lines = [f"Detected {self.primary.name} ({self.primary.confidence:.0%} confidence)"]
        lines.append("\nEvidence:")

        for signal in self.primary.top_signals:
            kind_name = signal.kind.value.replace("_", " ").title()
            lines.append(f"  - {kind_name}: {signal.value}")

        if self.is_multi_market_site:
            lines.append(f"\nNote: Multi-market site detected ({len(self.hreflang_markets)} markets)")

        if self.has_conflicts:
            lines.append(f"\nWarning: {self.conflict_description}")

        return "\n".join(lines)


# =============================================================================
# SIGNAL EXTRACTORS
# =============================================================================


def extract_tld(domain: str) -> Optional[Tuple[str, str]]:
    """
    Extract TLD and map to market.

    Returns (market_code, tld) or None.
    """
    domain = domain.lower().strip()

    # Check longest TLDs first (e.g., .co.uk before .uk)
    for tld in sorted(TLD_TO_MARKET.keys(), key=len, reverse=True):
        if domain.endswith(tld):
            return (TLD_TO_MARKET[tld], tld)

    return None


def extract_hreflang_tags(html: str) -> List[Tuple[str, str, str]]:
    """
    Extract hreflang tags from HTML.

    Returns list of (language, region, href) tuples.
    E.g., [("en", "gb", "https://example.co.uk"), ("en", "us", "https://example.com")]
    """
    results = []

    # Pattern: <link rel="alternate" hreflang="en-GB" href="...">
    pattern = r'<link[^>]*hreflang=["\']([^"\']+)["\'][^>]*href=["\']([^"\']+)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)

    # Also try href before hreflang
    pattern2 = r'<link[^>]*href=["\']([^"\']+)["\'][^>]*hreflang=["\']([^"\']+)["\']'
    matches2 = re.findall(pattern2, html, re.IGNORECASE)

    for hreflang, href in matches:
        lang, region = _parse_hreflang(hreflang)
        if region:
            results.append((lang, region.lower(), href))

    for href, hreflang in matches2:
        lang, region = _parse_hreflang(hreflang)
        if region:
            results.append((lang, region.lower(), href))

    return results


def _parse_hreflang(hreflang: str) -> Tuple[str, Optional[str]]:
    """Parse hreflang value into (language, region)."""
    hreflang = hreflang.lower().strip()

    if hreflang == "x-default":
        return ("x-default", None)

    parts = re.split(r'[-_]', hreflang)

    if len(parts) >= 2:
        return (parts[0], parts[1])
    elif len(parts) == 1:
        return (parts[0], None)

    return ("", None)


def extract_schema_org_address(html: str) -> List[Tuple[str, str]]:
    """
    Extract addressCountry from Schema.org JSON-LD.

    Returns list of (country_code, evidence) tuples.
    """
    results = []

    # Find JSON-LD blocks
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

    for match in matches:
        try:
            data = json.loads(match)
            countries = _extract_countries_from_schema(data)
            for country, evidence in countries:
                results.append((country, evidence))
        except json.JSONDecodeError:
            continue

    return results


def _extract_countries_from_schema(data: Any, path: str = "") -> List[Tuple[str, str]]:
    """Recursively extract addressCountry from schema data."""
    results = []

    if isinstance(data, dict):
        # Check for addressCountry
        if "addressCountry" in data:
            country = data["addressCountry"]
            if isinstance(country, str):
                results.append((country, f"Schema.org {path}.addressCountry"))
            elif isinstance(country, dict) and "name" in country:
                results.append((country["name"], f"Schema.org {path}.addressCountry.name"))

        # Recurse into nested objects
        for key, value in data.items():
            results.extend(_extract_countries_from_schema(value, f"{path}.{key}"))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(_extract_countries_from_schema(item, f"{path}[{i}]"))

    return results


def extract_currencies(html: str) -> List[Tuple[str, str, str]]:
    """
    Extract currency symbols and codes from HTML.

    Returns list of (currency_symbol, market_code, evidence) tuples.
    """
    results = []

    # Currency patterns
    patterns = [
        # Price with symbol: £29.99, $19.99, €15,00
        (r'[£][\d,]+\.?\d*', "uk", "£"),
        (r'[€][\d,]+[.,]?\d*', None, "€"),  # Euro needs context
        (r'(?<![A-Z])SEK\s*[\d,]+', "se", "SEK"),
        (r'(?<![A-Z])NOK\s*[\d,]+', "no", "NOK"),
        (r'(?<![A-Z])DKK\s*[\d,]+', "dk", "DKK"),
        (r'(?<![A-Z])CHF\s*[\d,]+', "ch", "CHF"),
        (r'(?<![A-Z])GBP\s*[\d,]+', "uk", "GBP"),
        (r'(?<![A-Z])AUD\s*[\d,]+', "au", "AUD"),
        (r'(?<![A-Z])CAD\s*[\d,]+', "ca", "CAD"),
        (r'(?<![A-Z])NZD\s*[\d,]+', "nz", "NZD"),
        # Swedish krona with space: 299 kr
        (r'\d+\s*kr(?:\s|$|\.)', None, "kr"),  # Could be SE, NO, DK
    ]

    for pattern, market, symbol in patterns:
        if re.search(pattern, html, re.IGNORECASE):
            if market:
                # Extract actual match for evidence
                match = re.search(pattern, html, re.IGNORECASE)
                evidence = match.group(0) if match else symbol
                results.append((symbol, market, evidence[:50]))

    return results


def extract_phone_numbers(html: str) -> List[Tuple[str, str, str]]:
    """
    Extract phone numbers and map to countries.

    Returns list of (country_code, market_code, evidence) tuples.
    """
    results = []

    # International format: +44 1234 567890
    pattern = r'\+(\d{1,3})[\s.-]?\d'
    matches = re.findall(pattern, html)

    for country_code in matches:
        prefix = f"+{country_code}"
        # Find the market for this prefix
        for market_prefix, market_code in PHONE_PREFIX_TO_MARKET.items():
            if market_prefix == prefix or market_prefix.startswith(prefix):
                # Get more context for evidence
                full_pattern = rf'\+{country_code}[\s.-]?\d[\d\s.-]{{6,15}}'
                match = re.search(full_pattern, html)
                evidence = match.group(0) if match else prefix
                results.append((prefix, market_code, evidence))
                break

    return results


def extract_shipping_countries(html: str) -> List[Tuple[str, str]]:
    """
    Extract shipping destination countries from shipping page.

    Returns list of (market_code, evidence) tuples.
    """
    results = []
    html_lower = html.lower()

    # Shipping patterns
    patterns = [
        # "UK delivery", "Delivery to UK"
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?uk\b', "uk"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?united\s+kingdom', "uk"),
        (r'uk\s+(?:ship|deliver)', "uk"),

        # "US shipping", "Ships to USA"
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?us\b', "us"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?usa\b', "us"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?united\s+states', "us"),

        # European countries
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?germany', "de"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?france', "fr"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?sweden', "se"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?norway', "no"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?denmark', "dk"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?netherlands', "nl"),
        (r'(?:ship|deliver)[a-z]*\s+(?:to\s+)?(?:the\s+)?finland', "fi"),

        # "Free UK shipping"
        (r'free\s+uk\s+(?:ship|deliver)', "uk"),
        (r'free\s+(?:ship|deliver)[a-z]*\s+(?:to\s+)?uk', "uk"),

        # "Royal Mail" (UK specific)
        (r'royal\s+mail', "uk"),

        # Country-specific carriers
        (r'postnord', "se"),  # Could also be DK, NO
        (r'hermes\s+(?:uk|delivery)', "uk"),
        (r'dpd\s+(?:uk|local)', "uk"),
    ]

    for pattern, market in patterns:
        match = re.search(pattern, html_lower)
        if match:
            results.append((market, match.group(0)))

    return results


def extract_vat_mentions(html: str) -> List[Tuple[str, str]]:
    """
    Extract VAT/tax mentions that indicate jurisdiction.

    Returns list of (market_code, evidence) tuples.
    """
    results = []
    html_lower = html.lower()

    for market_code, config in MARKET_CONFIG.items():
        for term in config.get("vat_terms", []):
            if term in html_lower:
                # Get context around the match
                idx = html_lower.find(term)
                start = max(0, idx - 20)
                end = min(len(html_lower), idx + len(term) + 20)
                evidence = html[start:end].strip()
                results.append((market_code, evidence))
                break  # One match per market is enough

    return results


def extract_addresses(html: str) -> List[Tuple[str, str]]:
    """
    Extract physical addresses and identify country.

    Returns list of (market_code, evidence) tuples.
    """
    results = []

    # UK postcode pattern
    uk_postcode = r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b'
    if re.search(uk_postcode, html, re.IGNORECASE):
        match = re.search(uk_postcode, html, re.IGNORECASE)
        results.append(("uk", match.group(0)))

    # US ZIP code pattern (5 digits or 5+4)
    us_zip = r'\b\d{5}(?:-\d{4})?\b'
    # Only count as US if there's supporting context
    if re.search(r'(?:usa|united states|,\s*[A-Z]{2}\s+)' + us_zip, html, re.IGNORECASE):
        match = re.search(r'(?:usa|united states|,\s*[A-Z]{2}\s+)\d{5}', html, re.IGNORECASE)
        if match:
            results.append(("us", match.group(0)))

    # German postcode (5 digits with German context)
    if re.search(r'(?:deutschland|germany|münchen|berlin|hamburg)\s*\d{5}', html, re.IGNORECASE):
        results.append(("de", "German postcode detected"))

    # Swedish postcode (3 digits + 2 digits with Swedish context)
    if re.search(r'(?:sverige|sweden|stockholm|göteborg)\s*\d{3}\s*\d{2}', html, re.IGNORECASE):
        results.append(("se", "Swedish postcode detected"))

    return results


def extract_store_selector(html: str) -> bool:
    """
    Detect if page has a country/store selector.

    Returns True if multi-market selector found.
    """
    patterns = [
        r'select[^>]*(?:country|region|location)',
        r'(?:choose|select)\s+(?:your\s+)?(?:country|region|location)',
        r'country-selector',
        r'region-selector',
        r'store-switcher',
        r'geo-redirect',
        r'locale-switcher',
    ]

    for pattern in patterns:
        if re.search(pattern, html, re.IGNORECASE):
            return True

    return False


def extract_geo_banner(html: str) -> Optional[str]:
    """
    Detect geo-redirect or location banners.

    Returns banner text if found.
    """
    patterns = [
        r"you(?:'re| are)\s+(?:in|viewing from)\s+([A-Za-z]+)",
        r"switch\s+to\s+(?:the\s+)?([A-Za-z]+)\s+(?:store|site)",
        r"visiting\s+from\s+([A-Za-z]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(0)

    return None


# =============================================================================
# MARKET DETECTOR
# =============================================================================


class MarketDetector:
    """
    Detects target market(s) from website signals.

    Usage:
        detector = MarketDetector()
        result = await detector.detect("example.com")

        print(f"Primary market: {result.primary.name}")
        print(f"Confidence: {result.primary.confidence:.0%}")
        print(f"Needs confirmation: {result.needs_confirmation}")
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.client = None

    async def detect(
        self,
        domain: str,
        pages: Optional[Dict[str, str]] = None,
    ) -> MarketDetectionResult:
        """
        Detect market from website signals.

        Args:
            domain: Target domain
            pages: Optional pre-fetched pages {url: html}
                   If not provided, fetches key pages automatically.

        Returns:
            MarketDetectionResult with primary market, candidates, and evidence.
        """
        import time
        start_time = time.time()

        logger.info(f"Starting market detection for: {domain}")

        # Fetch pages if not provided
        if pages is None:
            pages = await self._fetch_pages(domain)

        all_signals: List[MarketSignal] = []
        pages_checked = list(pages.keys())

        # Extract signals from each page
        for url, html in pages.items():
            if not html:
                continue

            signals = self._extract_all_signals(domain, url, html)
            all_signals.extend(signals)

        # Also extract TLD signal (doesn't need HTML)
        tld_result = extract_tld(domain)
        if tld_result:
            market_code, tld = tld_result
            all_signals.append(MarketSignal(
                kind=SignalKind.TLD,
                market_code=market_code,
                value=tld,
                weight=SIGNAL_WEIGHTS[SignalKind.TLD],
                evidence=f"Domain ends with {tld}",
                source_url=domain,
            ))

        # Aggregate signals by market
        market_scores = self._aggregate_signals(all_signals)

        # Detect conflicts
        has_conflicts, conflict_desc = self._detect_conflicts(all_signals, market_scores)

        # Build detected markets
        detected_markets = self._build_detected_markets(market_scores, all_signals)

        if not detected_markets:
            # Fallback to US if no signals
            logger.warning(f"No market signals found for {domain}, defaulting to US")
            detected_markets = [DetectedMarket(
                code="us",
                name="United States",
                confidence=0.3,
                signals=[],
            )]

        # Primary is highest confidence
        primary = detected_markets[0]
        candidates = detected_markets[1:]

        # Determine if confirmation needed
        needs_confirmation, reason = self._check_needs_confirmation(
            primary, candidates, all_signals, has_conflicts
        )

        # Detect multi-market site
        hreflang_markets = self._get_hreflang_markets(all_signals)
        is_multi_market = len(hreflang_markets) > 1

        detection_time = (time.time() - start_time) * 1000

        result = MarketDetectionResult(
            primary=primary,
            candidates=candidates,
            needs_confirmation=needs_confirmation,
            confirmation_reason=reason,
            is_multi_market_site=is_multi_market,
            hreflang_markets=hreflang_markets,
            all_signals=all_signals,
            pages_checked=pages_checked,
            has_conflicts=has_conflicts,
            conflict_description=conflict_desc,
            detection_time_ms=detection_time,
        )

        logger.info(
            f"Market detection complete: {primary.name} ({primary.confidence:.0%}), "
            f"{len(all_signals)} signals, {len(candidates)} candidates, "
            f"needs_confirmation={needs_confirmation}"
        )

        return result

    async def _fetch_pages(self, domain: str) -> Dict[str, str]:
        """Fetch key pages for signal extraction."""
        pages = {}
        base_url = f"https://{domain}"

        # Pages to check in priority order
        page_paths = [
            "/",  # Always fetch homepage
            "/shipping",
            "/delivery",
            "/shipping-policy",
            "/delivery-information",
            "/contact",
            "/contact-us",
            "/about",
            "/about-us",
        ]

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AuthoricyBot/1.0)"}
        ) as client:
            # Fetch homepage first (required)
            try:
                resp = await client.get(base_url)
                if resp.status_code == 200:
                    pages[base_url] = resp.text
            except Exception as e:
                logger.warning(f"Failed to fetch homepage for {domain}: {e}")

            # Fetch other pages (stop early if we have strong signals)
            for path in page_paths[1:]:
                url = f"{base_url}{path}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        pages[url] = resp.text
                        # If we found a shipping page, that's usually enough
                        if "shipping" in path or "delivery" in path:
                            break
                except Exception:
                    continue

        return pages

    def _extract_all_signals(
        self,
        domain: str,
        url: str,
        html: str,
    ) -> List[MarketSignal]:
        """Extract all market signals from a page."""
        signals = []

        # hreflang tags
        hreflangs = extract_hreflang_tags(html)
        for lang, region, href in hreflangs:
            if region in HREFLANG_TO_MARKET:
                market_code = HREFLANG_TO_MARKET[region]
                signals.append(MarketSignal(
                    kind=SignalKind.HREFLANG,
                    market_code=market_code,
                    value=f"{lang}-{region}",
                    weight=SIGNAL_WEIGHTS[SignalKind.HREFLANG],
                    evidence=f'hreflang="{lang}-{region}" href="{href}"',
                    source_url=url,
                ))

        # Schema.org address
        schema_countries = extract_schema_org_address(html)
        for country, evidence in schema_countries:
            market_code = self._country_to_market(country)
            if market_code:
                signals.append(MarketSignal(
                    kind=SignalKind.SCHEMA_ORG,
                    market_code=market_code,
                    value=country,
                    weight=SIGNAL_WEIGHTS[SignalKind.SCHEMA_ORG],
                    evidence=evidence,
                    source_url=url,
                ))

        # Currencies
        currencies = extract_currencies(html)
        for symbol, market_code, evidence in currencies:
            if market_code:
                signals.append(MarketSignal(
                    kind=SignalKind.CURRENCY,
                    market_code=market_code,
                    value=symbol,
                    weight=SIGNAL_WEIGHTS[SignalKind.CURRENCY],
                    evidence=evidence,
                    source_url=url,
                ))

        # Phone numbers
        phones = extract_phone_numbers(html)
        for prefix, market_code, evidence in phones:
            signals.append(MarketSignal(
                kind=SignalKind.PHONE,
                market_code=market_code,
                value=prefix,
                weight=SIGNAL_WEIGHTS[SignalKind.PHONE],
                evidence=evidence,
                source_url=url,
            ))

        # Shipping countries (high weight for shipping/delivery pages)
        if "shipping" in url.lower() or "delivery" in url.lower():
            shipping = extract_shipping_countries(html)
            for market_code, evidence in shipping:
                signals.append(MarketSignal(
                    kind=SignalKind.SHIPPING,
                    market_code=market_code,
                    value=MARKET_CONFIG.get(market_code, {}).get("name", market_code),
                    weight=SIGNAL_WEIGHTS[SignalKind.SHIPPING],
                    evidence=evidence,
                    source_url=url,
                ))

        # VAT mentions
        vat = extract_vat_mentions(html)
        for market_code, evidence in vat:
            signals.append(MarketSignal(
                kind=SignalKind.VAT,
                market_code=market_code,
                value=evidence[:30],
                weight=SIGNAL_WEIGHTS[SignalKind.VAT],
                evidence=evidence,
                source_url=url,
            ))

        # Addresses
        addresses = extract_addresses(html)
        for market_code, evidence in addresses:
            signals.append(MarketSignal(
                kind=SignalKind.ADDRESS,
                market_code=market_code,
                value=evidence[:30],
                weight=SIGNAL_WEIGHTS[SignalKind.ADDRESS],
                evidence=evidence,
                source_url=url,
            ))

        # Store selector (multi-market indicator)
        if extract_store_selector(html):
            signals.append(MarketSignal(
                kind=SignalKind.STORE_SELECTOR,
                market_code="multi",
                value="Country selector found",
                weight=SIGNAL_WEIGHTS[SignalKind.STORE_SELECTOR],
                evidence="Store/country selector detected",
                source_url=url,
            ))

        # Geo banner
        geo_banner = extract_geo_banner(html)
        if geo_banner:
            signals.append(MarketSignal(
                kind=SignalKind.GEO_BANNER,
                market_code="multi",
                value=geo_banner[:50],
                weight=SIGNAL_WEIGHTS[SignalKind.GEO_BANNER],
                evidence=geo_banner,
                source_url=url,
            ))

        return signals

    def _country_to_market(self, country: str) -> Optional[str]:
        """Convert country name/code to market code."""
        country = country.lower().strip()

        # Direct mappings
        mappings = {
            "gb": "uk", "united kingdom": "uk", "uk": "uk", "britain": "uk",
            "us": "us", "usa": "us", "united states": "us", "america": "us",
            "se": "se", "sweden": "se", "sverige": "se",
            "de": "de", "germany": "de", "deutschland": "de",
            "fr": "fr", "france": "fr",
            "no": "no", "norway": "no", "norge": "no",
            "dk": "dk", "denmark": "dk", "danmark": "dk",
            "fi": "fi", "finland": "fi", "suomi": "fi",
            "nl": "nl", "netherlands": "nl", "holland": "nl",
            "es": "es", "spain": "es", "españa": "es",
            "it": "it", "italy": "it", "italia": "it",
            "au": "au", "australia": "au",
            "ca": "ca", "canada": "ca",
            "ie": "ie", "ireland": "ie",
            "at": "at", "austria": "at", "österreich": "at",
            "ch": "ch", "switzerland": "ch", "schweiz": "ch",
            "be": "be", "belgium": "be",
            "nz": "nz", "new zealand": "nz",
        }

        return mappings.get(country)

    def _aggregate_signals(
        self,
        signals: List[MarketSignal],
    ) -> Dict[str, float]:
        """Aggregate signal weights by market."""
        market_scores: Dict[str, float] = {}

        for signal in signals:
            market = signal.market_code
            if market == "multi":
                continue  # Skip multi-market indicators

            score = signal.weight * signal.confidence
            market_scores[market] = market_scores.get(market, 0) + score

        return market_scores

    def _detect_conflicts(
        self,
        signals: List[MarketSignal],
        market_scores: Dict[str, float],
    ) -> Tuple[bool, str]:
        """Detect conflicting signals."""
        if len(market_scores) < 2:
            return False, ""

        # Get top 2 markets
        sorted_markets = sorted(market_scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_markets) < 2:
            return False, ""

        top_market, top_score = sorted_markets[0]
        second_market, second_score = sorted_markets[1]

        # Conflict if second is close to top
        if second_score > top_score * 0.7:
            # Check for specific signal conflicts
            tld_market = None
            schema_market = None

            for s in signals:
                if s.kind == SignalKind.TLD:
                    tld_market = s.market_code
                elif s.kind == SignalKind.SCHEMA_ORG:
                    schema_market = s.market_code

            if tld_market and schema_market and tld_market != schema_market:
                return True, f"TLD suggests {tld_market.upper()}, but Schema.org address says {schema_market.upper()}"

            return True, f"Competing signals for {top_market.upper()} and {second_market.upper()}"

        return False, ""

    def _build_detected_markets(
        self,
        market_scores: Dict[str, float],
        signals: List[MarketSignal],
    ) -> List[DetectedMarket]:
        """Build DetectedMarket objects from scores."""
        if not market_scores:
            return []

        # Normalize scores to 0-1
        max_score = max(market_scores.values()) if market_scores else 1

        markets = []
        for market_code, score in sorted(market_scores.items(), key=lambda x: x[1], reverse=True):
            confidence = min(1.0, score / max(max_score, 1.5))  # Cap at 1.0

            # Get signals for this market
            market_signals = [s for s in signals if s.market_code == market_code]

            config = MARKET_CONFIG.get(market_code, {})

            markets.append(DetectedMarket(
                code=market_code,
                name=config.get("name", market_code.upper()),
                confidence=confidence,
                signals=market_signals,
            ))

        return markets

    def _check_needs_confirmation(
        self,
        primary: DetectedMarket,
        candidates: List[DetectedMarket],
        signals: List[MarketSignal],
        has_conflicts: bool,
    ) -> Tuple[bool, str]:
        """Determine if user confirmation is needed."""
        # Always confirm if conflicts
        if has_conflicts:
            return True, "Conflicting signals detected"

        # Confirm if confidence is low
        if primary.confidence < 0.75:
            return True, f"Low confidence ({primary.confidence:.0%})"

        # Confirm if many hreflang markets (multi-market site)
        hreflang_count = sum(1 for s in signals if s.kind == SignalKind.HREFLANG)
        if hreflang_count >= 4:
            return True, f"Multi-market site detected ({hreflang_count} hreflang tags)"

        # Confirm if store selector present
        has_store_selector = any(s.kind == SignalKind.STORE_SELECTOR for s in signals)
        if has_store_selector:
            return True, "Country/store selector detected (multi-market)"

        # High confidence, no issues - no confirmation needed
        return False, ""

    def _get_hreflang_markets(self, signals: List[MarketSignal]) -> List[str]:
        """Get list of markets from hreflang tags."""
        markets = []
        for signal in signals:
            if signal.kind == SignalKind.HREFLANG:
                if signal.market_code not in markets:
                    markets.append(signal.market_code)
        return markets


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


async def detect_market(
    domain: str,
    pages: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
) -> MarketDetectionResult:
    """
    Convenience function to detect market for a domain.

    Args:
        domain: Target domain (without protocol)
        pages: Optional pre-fetched pages {url: html}
        timeout: HTTP timeout in seconds

    Returns:
        MarketDetectionResult with detected market and evidence.

    Example:
        result = await detect_market("thrivepetfoods.com")
        print(f"Detected: {result.primary.name} ({result.primary.confidence:.0%})")

        if result.needs_confirmation:
            print(f"Please confirm: {result.confirmation_reason}")
    """
    detector = MarketDetector(timeout=timeout)
    return await detector.detect(domain, pages)

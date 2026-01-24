"""
Market Resolution System (Phase 2)

Resolves the final market to use for data collection by merging:
1. User-provided market (highest priority)
2. Detected market from website signals
3. Default fallback (US)

This module gates the entire pipeline - all downstream data collection
uses the resolved market to ensure consistency.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

from .market_detection import (
    MarketDetectionResult,
    DetectedMarket,
    MARKET_CONFIG,
)

logger = logging.getLogger(__name__)


class ResolutionSource(str, Enum):
    """How the market was resolved."""
    USER_PROVIDED = "user_provided"      # User explicitly specified
    USER_CONFIRMED = "user_confirmed"    # User confirmed detection
    AUTO_DETECTED = "auto_detected"      # High-confidence detection, no user input
    DEFAULT_FALLBACK = "default"         # No detection, no user input


class ResolutionConfidence(str, Enum):
    """Confidence level in the resolution."""
    HIGH = "high"        # User provided or confirmed, or detection > 0.85
    MEDIUM = "medium"    # Detection 0.6-0.85, or user provided without validation
    LOW = "low"          # Detection < 0.6, or default fallback
    CONFLICT = "conflict"  # User and detection disagree significantly


@dataclass
class ResolvedMarket:
    """
    The final resolved market for data collection.

    This is the single source of truth for market parameters
    throughout the entire pipeline.
    """
    # Core identification
    code: str                    # "uk", "us", "se", etc.
    name: str                    # "United Kingdom", "United States", etc.

    # DataForSEO API parameters (ready to use)
    location_code: int           # 2826 for UK, 2840 for US, etc.
    location_name: str           # "United Kingdom" (for API calls)
    language_code: str           # "en", "sv", etc.
    language_name: str           # "English", "Swedish", etc.

    # Resolution metadata
    source: ResolutionSource = ResolutionSource.DEFAULT_FALLBACK
    confidence: ResolutionConfidence = ResolutionConfidence.LOW
    detection_confidence: float = 0.0  # Original detection confidence (0-1)

    # Conflict information
    has_conflict: bool = False
    conflict_details: str = ""
    user_provided_market: Optional[str] = None  # What user originally said
    detected_market: Optional[str] = None       # What detection found

    # Multi-market info (for future phases)
    is_multi_market_site: bool = False
    additional_markets: List[str] = field(default_factory=list)

    # Explanation for debugging/UI
    resolution_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "code": self.code,
            "name": self.name,
            "location_code": self.location_code,
            "location_name": self.location_name,
            "language_code": self.language_code,
            "language_name": self.language_name,
            "source": self.source.value,
            "confidence": self.confidence.value,
            "detection_confidence": self.detection_confidence,
            "has_conflict": self.has_conflict,
            "conflict_details": self.conflict_details,
            "user_provided_market": self.user_provided_market,
            "detected_market": self.detected_market,
            "is_multi_market_site": self.is_multi_market_site,
            "additional_markets": self.additional_markets,
            "resolution_explanation": self.resolution_explanation,
        }

    @classmethod
    def from_code(cls, code: str, source: ResolutionSource = ResolutionSource.DEFAULT_FALLBACK) -> "ResolvedMarket":
        """Create a ResolvedMarket from just a market code."""
        code = code.lower().strip()
        config = MARKET_CONFIG.get(code, MARKET_CONFIG["us"])

        return cls(
            code=code,
            name=config["name"],
            location_code=config["location_code"],
            location_name=config["name"],
            language_code=config["language_code"],
            language_name=config["language_name"],
            source=source,
            confidence=ResolutionConfidence.LOW if source == ResolutionSource.DEFAULT_FALLBACK else ResolutionConfidence.MEDIUM,
        )


# Market code normalization (handles various input formats)
MARKET_NAME_TO_CODE = {
    # United States
    "united states": "us", "usa": "us", "america": "us", "us": "us",
    # United Kingdom
    "united kingdom": "uk", "britain": "uk", "great britain": "uk",
    "england": "uk", "uk": "uk", "gb": "uk",
    # Sweden
    "sweden": "se", "sverige": "se", "se": "se",
    # Germany
    "germany": "de", "deutschland": "de", "de": "de",
    # France
    "france": "fr", "fr": "fr",
    # Norway
    "norway": "no", "norge": "no", "no": "no",
    # Denmark
    "denmark": "dk", "danmark": "dk", "dk": "dk",
    # Finland
    "finland": "fi", "suomi": "fi", "fi": "fi",
    # Netherlands
    "netherlands": "nl", "holland": "nl", "nl": "nl",
    # Spain
    "spain": "es", "españa": "es", "es": "es",
    # Italy
    "italy": "it", "italia": "it", "it": "it",
    # Australia
    "australia": "au", "au": "au",
    # Canada
    "canada": "ca", "ca": "ca",
    # Ireland
    "ireland": "ie", "ie": "ie",
    # New Zealand
    "new zealand": "nz", "nz": "nz",
}

VALID_MARKET_CODES = set(MARKET_CONFIG.keys())


def normalize_market_input(market: Optional[str]) -> Optional[str]:
    """
    Normalize market input to a standard code.

    Handles:
    - Market codes: "uk", "us", "se"
    - Full names: "United Kingdom", "Sweden"
    - Variants: "Britain", "Sverige", "USA"

    Returns None if input is None/empty/invalid.
    """
    if not market:
        return None

    normalized = market.lower().strip()

    # Direct code match
    if normalized in VALID_MARKET_CODES:
        return normalized

    # Name/variant mapping
    if normalized in MARKET_NAME_TO_CODE:
        return MARKET_NAME_TO_CODE[normalized]

    # Try partial match (e.g., "united" -> None, but "united kingdom" -> "uk")
    # Be strict here to avoid false matches
    return None


class MarketResolver:
    """
    Resolves the market to use for data collection.

    Resolution priority:
    1. User-provided market (if valid)
    2. High-confidence detection (>= 0.75)
    3. Medium-confidence detection with user confirmation
    4. Default (US)

    The resolver also:
    - Detects conflicts between user input and detection
    - Tracks multi-market sites for future expansion
    - Provides explanations for debugging
    """

    # Thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.75
    MEDIUM_CONFIDENCE_THRESHOLD = 0.50
    CONFLICT_THRESHOLD = 0.70  # Detection must be this confident to flag conflict

    def resolve(
        self,
        user_market: Optional[str] = None,
        detection_result: Optional[MarketDetectionResult] = None,
        user_confirmed: bool = False,
        default_market: str = "us",
    ) -> ResolvedMarket:
        """
        Resolve the market to use for data collection.

        Args:
            user_market: Market provided by user (code or name)
            detection_result: Result from MarketDetector
            user_confirmed: Whether user confirmed the detection
            default_market: Fallback market if nothing else works

        Returns:
            ResolvedMarket with all parameters for data collection
        """
        # Normalize user input
        user_code = normalize_market_input(user_market)

        # Get detection info
        detected_code = None
        detected_confidence = 0.0
        is_multi_market = False
        additional_markets = []

        if detection_result and detection_result.primary:
            detected_code = detection_result.primary.code
            detected_confidence = detection_result.primary.confidence
            is_multi_market = detection_result.is_multi_market_site
            additional_markets = detection_result.hreflang_markets[:5]  # Top 5

        # Resolution logic
        resolved = self._apply_resolution_logic(
            user_code=user_code,
            detected_code=detected_code,
            detected_confidence=detected_confidence,
            user_confirmed=user_confirmed,
            default_market=default_market,
        )

        # Add multi-market info
        resolved.is_multi_market_site = is_multi_market
        resolved.additional_markets = additional_markets
        resolved.user_provided_market = user_market
        resolved.detected_market = detected_code
        resolved.detection_confidence = detected_confidence

        # Log resolution
        logger.info(
            f"Market resolved: {resolved.code} ({resolved.name}) "
            f"[source={resolved.source.value}, confidence={resolved.confidence.value}]"
        )
        if resolved.has_conflict:
            logger.warning(f"Market conflict: {resolved.conflict_details}")

        return resolved

    def _apply_resolution_logic(
        self,
        user_code: Optional[str],
        detected_code: Optional[str],
        detected_confidence: float,
        user_confirmed: bool,
        default_market: str,
    ) -> ResolvedMarket:
        """Apply the priority-based resolution logic."""

        # Case 1: User confirmed detection
        if user_confirmed and detected_code:
            return self._create_resolved(
                code=detected_code,
                source=ResolutionSource.USER_CONFIRMED,
                confidence=ResolutionConfidence.HIGH,
                explanation=f"User confirmed detected market ({detected_code})",
            )

        # Case 2: User provided market
        if user_code:
            # Check for conflict with detection
            conflict = self._check_conflict(user_code, detected_code, detected_confidence)

            resolved = self._create_resolved(
                code=user_code,
                source=ResolutionSource.USER_PROVIDED,
                confidence=ResolutionConfidence.HIGH if not conflict else ResolutionConfidence.CONFLICT,
                explanation=f"User specified market: {user_code}",
            )

            if conflict:
                resolved.has_conflict = True
                resolved.conflict_details = conflict
                resolved.confidence = ResolutionConfidence.CONFLICT

            return resolved

        # Case 3: High-confidence detection (no user input)
        if detected_code and detected_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return self._create_resolved(
                code=detected_code,
                source=ResolutionSource.AUTO_DETECTED,
                confidence=ResolutionConfidence.HIGH,
                explanation=f"High-confidence detection: {detected_code} ({detected_confidence:.0%})",
            )

        # Case 4: Medium-confidence detection
        if detected_code and detected_confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return self._create_resolved(
                code=detected_code,
                source=ResolutionSource.AUTO_DETECTED,
                confidence=ResolutionConfidence.MEDIUM,
                explanation=f"Medium-confidence detection: {detected_code} ({detected_confidence:.0%}). Consider confirming.",
            )

        # Case 5: Low-confidence detection
        if detected_code and detected_confidence > 0:
            return self._create_resolved(
                code=detected_code,
                source=ResolutionSource.AUTO_DETECTED,
                confidence=ResolutionConfidence.LOW,
                explanation=f"Low-confidence detection: {detected_code} ({detected_confidence:.0%}). May need verification.",
            )

        # Case 6: Default fallback
        return self._create_resolved(
            code=default_market,
            source=ResolutionSource.DEFAULT_FALLBACK,
            confidence=ResolutionConfidence.LOW,
            explanation=f"No market detected or provided. Using default: {default_market}",
        )

    def _create_resolved(
        self,
        code: str,
        source: ResolutionSource,
        confidence: ResolutionConfidence,
        explanation: str,
    ) -> ResolvedMarket:
        """Create a ResolvedMarket from a code with full DataForSEO params."""
        config = MARKET_CONFIG.get(code, MARKET_CONFIG["us"])

        return ResolvedMarket(
            code=code,
            name=config["name"],
            location_code=config["location_code"],
            location_name=config["name"],
            language_code=config["language_code"],
            language_name=config["language_name"],
            source=source,
            confidence=confidence,
            resolution_explanation=explanation,
        )

    def _check_conflict(
        self,
        user_code: str,
        detected_code: Optional[str],
        detected_confidence: float,
    ) -> Optional[str]:
        """
        Check if user input conflicts with detection.

        Returns conflict description if there's a significant conflict,
        None otherwise.
        """
        if not detected_code:
            return None

        if user_code == detected_code:
            return None

        # Only flag conflict if detection is reasonably confident
        if detected_confidence < self.CONFLICT_THRESHOLD:
            return None

        user_name = MARKET_CONFIG.get(user_code, {}).get("name", user_code)
        detected_name = MARKET_CONFIG.get(detected_code, {}).get("name", detected_code)

        return (
            f"User specified '{user_name}' but website signals suggest '{detected_name}' "
            f"(detection confidence: {detected_confidence:.0%}). "
            f"Using user's choice, but data accuracy may be affected."
        )


def resolve_market(
    user_market: Optional[str] = None,
    detection_result: Optional[MarketDetectionResult] = None,
    user_confirmed: bool = False,
    default_market: str = "us",
) -> ResolvedMarket:
    """
    Convenience function to resolve market without instantiating resolver.

    Args:
        user_market: Market provided by user (code or name)
        detection_result: Result from MarketDetector
        user_confirmed: Whether user confirmed the detection
        default_market: Fallback market if nothing else works

    Returns:
        ResolvedMarket with all parameters for data collection
    """
    resolver = MarketResolver()
    return resolver.resolve(
        user_market=user_market,
        detection_result=detection_result,
        user_confirmed=user_confirmed,
        default_market=default_market,
    )

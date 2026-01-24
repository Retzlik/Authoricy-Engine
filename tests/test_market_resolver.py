"""
Tests for Market Resolver (Phase 2)
"""

import pytest
from src.context.market_resolver import (
    MarketResolver,
    ResolvedMarket,
    ResolutionSource,
    ResolutionConfidence,
    normalize_market_input,
    resolve_market,
)
from src.context.market_detection import (
    MarketDetectionResult,
    DetectedMarket,
    MarketSignal,
    SignalKind,
)


class TestNormalizeMarketInput:
    """Test market input normalization."""

    def test_code_lowercase(self):
        assert normalize_market_input("uk") == "uk"
        assert normalize_market_input("us") == "us"
        assert normalize_market_input("se") == "se"

    def test_code_uppercase(self):
        assert normalize_market_input("UK") == "uk"
        assert normalize_market_input("US") == "us"

    def test_full_name(self):
        assert normalize_market_input("United Kingdom") == "uk"
        assert normalize_market_input("United States") == "us"
        assert normalize_market_input("Sweden") == "se"

    def test_variants(self):
        assert normalize_market_input("Britain") == "uk"
        assert normalize_market_input("England") == "uk"
        assert normalize_market_input("USA") == "us"
        assert normalize_market_input("America") == "us"
        assert normalize_market_input("Sverige") == "se"
        assert normalize_market_input("Deutschland") == "de"

    def test_case_insensitive(self):
        assert normalize_market_input("UNITED KINGDOM") == "uk"
        assert normalize_market_input("sweden") == "se"

    def test_whitespace(self):
        assert normalize_market_input("  uk  ") == "uk"
        assert normalize_market_input(" United Kingdom ") == "uk"

    def test_none_empty(self):
        assert normalize_market_input(None) is None
        assert normalize_market_input("") is None
        assert normalize_market_input("   ") is None

    def test_invalid(self):
        assert normalize_market_input("invalid") is None
        assert normalize_market_input("xyz") is None


class TestResolvedMarket:
    """Test ResolvedMarket dataclass."""

    def test_from_code_uk(self):
        resolved = ResolvedMarket.from_code("uk")
        assert resolved.code == "uk"
        assert resolved.name == "United Kingdom"
        assert resolved.location_code == 2826
        assert resolved.language_code == "en"
        assert resolved.language_name == "English"

    def test_from_code_se(self):
        resolved = ResolvedMarket.from_code("se")
        assert resolved.code == "se"
        assert resolved.name == "Sweden"
        assert resolved.location_code == 2752
        assert resolved.language_code == "sv"
        assert resolved.language_name == "Swedish"

    def test_from_code_with_source(self):
        resolved = ResolvedMarket.from_code("us", ResolutionSource.USER_PROVIDED)
        assert resolved.source == ResolutionSource.USER_PROVIDED
        assert resolved.confidence == ResolutionConfidence.MEDIUM

    def test_to_dict(self):
        resolved = ResolvedMarket.from_code("uk")
        d = resolved.to_dict()
        assert d["code"] == "uk"
        assert d["name"] == "United Kingdom"
        assert d["location_code"] == 2826
        assert "source" in d
        assert "confidence" in d


class TestMarketResolver:
    """Test MarketResolver resolution logic."""

    @pytest.fixture
    def resolver(self):
        return MarketResolver()

    def test_user_provided_takes_priority(self, resolver):
        """User-provided market should always win."""
        # Even with high-confidence detection of different market
        detection = self._create_detection("se", confidence=0.95)

        resolved = resolver.resolve(
            user_market="uk",
            detection_result=detection,
        )

        assert resolved.code == "uk"
        assert resolved.source == ResolutionSource.USER_PROVIDED
        assert resolved.has_conflict  # Should flag the conflict
        assert "Sweden" in resolved.conflict_details

    def test_user_confirmed_detection(self, resolver):
        """User confirming detection should use detected market."""
        detection = self._create_detection("uk", confidence=0.85)

        resolved = resolver.resolve(
            detection_result=detection,
            user_confirmed=True,
        )

        assert resolved.code == "uk"
        assert resolved.source == ResolutionSource.USER_CONFIRMED
        assert resolved.confidence == ResolutionConfidence.HIGH

    def test_high_confidence_detection_no_user(self, resolver):
        """High-confidence detection without user input."""
        detection = self._create_detection("uk", confidence=0.85)

        resolved = resolver.resolve(detection_result=detection)

        assert resolved.code == "uk"
        assert resolved.source == ResolutionSource.AUTO_DETECTED
        assert resolved.confidence == ResolutionConfidence.HIGH

    def test_medium_confidence_detection(self, resolver):
        """Medium-confidence detection should still be used."""
        detection = self._create_detection("uk", confidence=0.65)

        resolved = resolver.resolve(detection_result=detection)

        assert resolved.code == "uk"
        assert resolved.source == ResolutionSource.AUTO_DETECTED
        assert resolved.confidence == ResolutionConfidence.MEDIUM

    def test_low_confidence_detection(self, resolver):
        """Low-confidence detection should still be used but flagged."""
        detection = self._create_detection("uk", confidence=0.35)

        resolved = resolver.resolve(detection_result=detection)

        assert resolved.code == "uk"
        assert resolved.source == ResolutionSource.AUTO_DETECTED
        assert resolved.confidence == ResolutionConfidence.LOW

    def test_no_detection_no_user_defaults(self, resolver):
        """No input defaults to US."""
        resolved = resolver.resolve()

        assert resolved.code == "us"
        assert resolved.source == ResolutionSource.DEFAULT_FALLBACK
        assert resolved.confidence == ResolutionConfidence.LOW

    def test_custom_default_market(self, resolver):
        """Custom default market."""
        resolved = resolver.resolve(default_market="de")

        assert resolved.code == "de"
        assert resolved.source == ResolutionSource.DEFAULT_FALLBACK

    def test_user_matches_detection_no_conflict(self, resolver):
        """No conflict when user and detection agree."""
        detection = self._create_detection("uk", confidence=0.90)

        resolved = resolver.resolve(
            user_market="uk",
            detection_result=detection,
        )

        assert resolved.code == "uk"
        assert not resolved.has_conflict

    def test_low_confidence_detection_no_conflict(self, resolver):
        """Low-confidence detection shouldn't trigger conflict."""
        detection = self._create_detection("se", confidence=0.50)

        resolved = resolver.resolve(
            user_market="uk",
            detection_result=detection,
        )

        assert resolved.code == "uk"
        assert not resolved.has_conflict  # Confidence too low to flag

    def test_multi_market_info_preserved(self, resolver):
        """Multi-market info should be preserved in resolution."""
        detection = self._create_detection(
            "uk",
            confidence=0.80,
            is_multi_market=True,
            hreflang_markets=["uk", "us", "de", "fr"],
        )

        resolved = resolver.resolve(detection_result=detection)

        assert resolved.is_multi_market_site
        assert "uk" in resolved.additional_markets
        assert "us" in resolved.additional_markets

    def test_dataforseo_params_correct(self, resolver):
        """DataForSEO parameters should be correctly set."""
        resolved = resolver.resolve(user_market="uk")

        assert resolved.location_code == 2826
        assert resolved.location_name == "United Kingdom"
        assert resolved.language_code == "en"
        assert resolved.language_name == "English"

    def test_explanation_provided(self, resolver):
        """Resolution should include explanation."""
        resolved = resolver.resolve(user_market="uk")
        assert resolved.resolution_explanation
        assert "uk" in resolved.resolution_explanation.lower()

    def _create_detection(
        self,
        market_code: str,
        confidence: float = 0.80,
        is_multi_market: bool = False,
        hreflang_markets: list = None,
    ) -> MarketDetectionResult:
        """Helper to create a detection result."""
        from src.context.market_detection import MARKET_CONFIG

        config = MARKET_CONFIG.get(market_code, MARKET_CONFIG["us"])

        primary = DetectedMarket(
            code=market_code,
            name=config["name"],
            confidence=confidence,
            location_code=config["location_code"],
            language_code=config["language_code"],
            language_name=config["language_name"],
        )

        return MarketDetectionResult(
            primary=primary,
            is_multi_market_site=is_multi_market,
            hreflang_markets=hreflang_markets or [],
        )


class TestResolveMarketFunction:
    """Test convenience function."""

    def test_basic_resolution(self):
        resolved = resolve_market(user_market="uk")
        assert resolved.code == "uk"
        assert resolved.source == ResolutionSource.USER_PROVIDED

    def test_default_resolution(self):
        resolved = resolve_market()
        assert resolved.code == "us"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_user_market_uses_detection(self):
        """Invalid user market should fall back to detection."""
        resolver = MarketResolver()
        detection = MarketDetectionResult(
            primary=DetectedMarket(
                code="uk",
                name="United Kingdom",
                confidence=0.80,
            )
        )

        resolved = resolver.resolve(
            user_market="invalid_market",
            detection_result=detection,
        )

        # Should use detection since user input was invalid
        assert resolved.code == "uk"
        assert resolved.source == ResolutionSource.AUTO_DETECTED

    def test_empty_detection_result(self):
        """Empty detection result should be handled."""
        resolver = MarketResolver()
        detection = MarketDetectionResult(primary=None)

        resolved = resolver.resolve(detection_result=detection)

        assert resolved.code == "us"  # Default
        assert resolved.source == ResolutionSource.DEFAULT_FALLBACK

    def test_resolution_with_full_name_input(self):
        """User providing full name should work."""
        resolved = resolve_market(user_market="United Kingdom")
        assert resolved.code == "uk"
        assert resolved.name == "United Kingdom"

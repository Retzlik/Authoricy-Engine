"""
Tests for Market Detection Module

Tests each signal extractor and the overall market detection logic.
"""

import pytest
from src.context.market_detection import (
    extract_tld,
    extract_hreflang_tags,
    extract_schema_org_address,
    extract_currencies,
    extract_phone_numbers,
    extract_shipping_countries,
    extract_vat_mentions,
    extract_addresses,
    extract_store_selector,
    MarketDetector,
    MarketSignal,
    SignalKind,
    SIGNAL_WEIGHTS,
)


# =============================================================================
# TLD EXTRACTION TESTS
# =============================================================================


class TestTLDExtraction:
    """Tests for TLD-based market detection."""

    def test_uk_tld(self):
        result = extract_tld("example.co.uk")
        assert result is not None
        assert result[0] == "uk"
        assert result[1] == ".co.uk"

    def test_uk_tld_short(self):
        result = extract_tld("example.uk")
        assert result is not None
        assert result[0] == "uk"

    def test_de_tld(self):
        result = extract_tld("example.de")
        assert result is not None
        assert result[0] == "de"

    def test_se_tld(self):
        result = extract_tld("example.se")
        assert result is not None
        assert result[0] == "se"

    def test_au_tld(self):
        result = extract_tld("example.com.au")
        assert result is not None
        assert result[0] == "au"

    def test_com_tld_no_market(self):
        """Generic .com should not map to a specific market."""
        result = extract_tld("example.com")
        assert result is None

    def test_tld_case_insensitive(self):
        result = extract_tld("EXAMPLE.CO.UK")
        assert result is not None
        assert result[0] == "uk"


# =============================================================================
# HREFLANG EXTRACTION TESTS
# =============================================================================


class TestHreflangExtraction:
    """Tests for hreflang tag extraction."""

    def test_simple_hreflang(self):
        html = '''
        <html>
        <head>
            <link rel="alternate" hreflang="en-GB" href="https://example.co.uk">
            <link rel="alternate" hreflang="en-US" href="https://example.com">
        </head>
        </html>
        '''
        results = extract_hreflang_tags(html)
        assert len(results) == 2
        assert ("en", "gb", "https://example.co.uk") in results
        assert ("en", "us", "https://example.com") in results

    def test_hreflang_with_x_default(self):
        html = '''
        <link rel="alternate" hreflang="x-default" href="https://example.com">
        <link rel="alternate" hreflang="sv-SE" href="https://example.se">
        '''
        results = extract_hreflang_tags(html)
        # x-default should be skipped (no region)
        assert len(results) == 1
        assert ("sv", "se", "https://example.se") in results

    def test_hreflang_different_formats(self):
        html = '''
        <link hreflang="de-DE" href="https://example.de" rel="alternate">
        <link rel="alternate" href="https://example.fr" hreflang="fr-FR">
        '''
        results = extract_hreflang_tags(html)
        assert len(results) == 2

    def test_no_hreflang(self):
        html = '<html><head><title>Test</title></head></html>'
        results = extract_hreflang_tags(html)
        assert len(results) == 0


# =============================================================================
# SCHEMA.ORG EXTRACTION TESTS
# =============================================================================


class TestSchemaOrgExtraction:
    """Tests for Schema.org address extraction."""

    def test_organization_address(self):
        html = '''
        <script type="application/ld+json">
        {
            "@type": "Organization",
            "name": "Test Company",
            "address": {
                "@type": "PostalAddress",
                "addressCountry": "GB"
            }
        }
        </script>
        '''
        results = extract_schema_org_address(html)
        assert len(results) >= 1
        assert any("GB" in r[0] for r in results)

    def test_nested_address(self):
        html = '''
        <script type="application/ld+json">
        {
            "@type": "LocalBusiness",
            "address": {
                "addressCountry": "United Kingdom"
            }
        }
        </script>
        '''
        results = extract_schema_org_address(html)
        assert len(results) >= 1
        assert any("United Kingdom" in r[0] for r in results)

    def test_multiple_schemas(self):
        html = '''
        <script type="application/ld+json">
        {"@type": "Organization", "address": {"addressCountry": "SE"}}
        </script>
        <script type="application/ld+json">
        {"@type": "Store", "address": {"addressCountry": "Sweden"}}
        </script>
        '''
        results = extract_schema_org_address(html)
        assert len(results) >= 2

    def test_no_schema(self):
        html = '<html><body>No schema here</body></html>'
        results = extract_schema_org_address(html)
        assert len(results) == 0


# =============================================================================
# CURRENCY EXTRACTION TESTS
# =============================================================================


class TestCurrencyExtraction:
    """Tests for currency detection."""

    def test_gbp_symbol(self):
        html = '<span class="price">£29.99</span>'
        results = extract_currencies(html)
        assert any(r[1] == "uk" for r in results)

    def test_gbp_code(self):
        html = '<span>Price: GBP 50.00</span>'
        results = extract_currencies(html)
        assert any(r[1] == "uk" for r in results)

    def test_sek_code(self):
        html = '<span>Pris: SEK 299</span>'
        results = extract_currencies(html)
        assert any(r[1] == "se" for r in results)

    def test_aud_code(self):
        html = '<span>Price: AUD 45.00</span>'
        results = extract_currencies(html)
        assert any(r[1] == "au" for r in results)

    def test_no_currency(self):
        html = '<p>Contact us for pricing</p>'
        results = extract_currencies(html)
        assert len(results) == 0


# =============================================================================
# PHONE NUMBER EXTRACTION TESTS
# =============================================================================


class TestPhoneExtraction:
    """Tests for phone number country detection."""

    def test_uk_phone(self):
        html = '<p>Call us: +44 20 1234 5678</p>'
        results = extract_phone_numbers(html)
        assert any(r[1] == "uk" for r in results)

    def test_us_phone(self):
        html = '<p>Phone: +1 555 123 4567</p>'
        results = extract_phone_numbers(html)
        assert any(r[1] == "us" or r[1] == "ca" for r in results)  # +1 is US/CA

    def test_se_phone(self):
        html = '<p>Telefon: +46 8 123 456</p>'
        results = extract_phone_numbers(html)
        assert any(r[1] == "se" for r in results)

    def test_de_phone(self):
        html = '<p>Telefon: +49 30 12345678</p>'
        results = extract_phone_numbers(html)
        assert any(r[1] == "de" for r in results)

    def test_no_phone(self):
        html = '<p>Email us at hello@example.com</p>'
        results = extract_phone_numbers(html)
        assert len(results) == 0


# =============================================================================
# SHIPPING PAGE EXTRACTION TESTS
# =============================================================================


class TestShippingExtraction:
    """Tests for shipping country detection."""

    def test_uk_shipping(self):
        html = '<p>We offer free UK delivery on orders over £50.</p>'
        results = extract_shipping_countries(html)
        assert any(r[0] == "uk" for r in results)

    def test_united_kingdom_shipping(self):
        html = '<p>Shipping to United Kingdom takes 2-3 days.</p>'
        results = extract_shipping_countries(html)
        assert any(r[0] == "uk" for r in results)

    def test_royal_mail(self):
        html = '<p>We ship via Royal Mail.</p>'
        results = extract_shipping_countries(html)
        assert any(r[0] == "uk" for r in results)

    def test_us_shipping(self):
        html = '<p>Free shipping to USA on orders over $50.</p>'
        results = extract_shipping_countries(html)
        assert any(r[0] == "us" for r in results)

    def test_sweden_shipping(self):
        html = '<p>Delivers to Sweden within 1-2 days.</p>'
        results = extract_shipping_countries(html)
        assert any(r[0] == "se" for r in results)

    def test_no_shipping_mention(self):
        html = '<p>See our FAQ for more information.</p>'
        results = extract_shipping_countries(html)
        assert len(results) == 0


# =============================================================================
# VAT EXTRACTION TESTS
# =============================================================================


class TestVATExtraction:
    """Tests for VAT/tax mention detection."""

    def test_uk_vat(self):
        html = '<p>All prices include VAT.</p>'
        results = extract_vat_mentions(html)
        assert any(r[0] == "uk" for r in results)

    def test_swedish_moms(self):
        html = '<p>Alla priser är inkl. moms.</p>'
        results = extract_vat_mentions(html)
        assert any(r[0] == "se" for r in results)

    def test_german_mwst(self):
        html = '<p>Preise inkl. MwSt.</p>'
        results = extract_vat_mentions(html)
        assert any(r[0] == "de" for r in results)

    def test_dutch_btw(self):
        html = '<p>Prijzen zijn incl. BTW.</p>'
        results = extract_vat_mentions(html)
        assert any(r[0] == "nl" for r in results)


# =============================================================================
# ADDRESS EXTRACTION TESTS
# =============================================================================


class TestAddressExtraction:
    """Tests for physical address detection."""

    def test_uk_postcode(self):
        html = '<p>London, SW1A 1AA</p>'
        results = extract_addresses(html)
        assert any(r[0] == "uk" for r in results)

    def test_uk_postcode_format2(self):
        html = '<p>Manchester M1 1AE</p>'
        results = extract_addresses(html)
        assert any(r[0] == "uk" for r in results)

    def test_us_zip(self):
        html = '<p>New York, NY 10001, USA</p>'
        results = extract_addresses(html)
        assert any(r[0] == "us" for r in results)


# =============================================================================
# STORE SELECTOR TESTS
# =============================================================================


class TestStoreSelector:
    """Tests for store/country selector detection."""

    def test_country_select(self):
        html = '<select id="country-selector">...</select>'
        assert extract_store_selector(html) is True

    def test_choose_country(self):
        html = '<p>Choose your country:</p>'
        assert extract_store_selector(html) is True

    def test_store_switcher(self):
        html = '<div class="store-switcher">...</div>'
        assert extract_store_selector(html) is True

    def test_no_selector(self):
        html = '<p>Welcome to our store</p>'
        assert extract_store_selector(html) is False


# =============================================================================
# SIGNAL WEIGHT TESTS
# =============================================================================


class TestSignalWeights:
    """Tests to verify signal weights are properly configured."""

    def test_all_weights_defined(self):
        """All signal kinds should have weights."""
        for kind in SignalKind:
            assert kind in SIGNAL_WEIGHTS, f"Missing weight for {kind}"

    def test_weights_in_range(self):
        """All weights should be between 0 and 1."""
        for kind, weight in SIGNAL_WEIGHTS.items():
            assert 0 <= weight <= 1, f"Weight for {kind} out of range: {weight}"

    def test_schema_org_highest(self):
        """Schema.org should be highest weight."""
        assert SIGNAL_WEIGHTS[SignalKind.SCHEMA_ORG] >= max(
            w for k, w in SIGNAL_WEIGHTS.items() if k != SignalKind.SCHEMA_ORG
        )

    def test_language_lowest(self):
        """Language alone should be lowest weight."""
        assert SIGNAL_WEIGHTS[SignalKind.LANGUAGE] <= min(
            w for k, w in SIGNAL_WEIGHTS.items() if k != SignalKind.LANGUAGE
        )


# =============================================================================
# MARKET DETECTOR INTEGRATION TESTS
# =============================================================================


class TestMarketDetector:
    """Integration tests for MarketDetector."""

    @pytest.fixture
    def detector(self):
        return MarketDetector(timeout=5.0)

    def test_uk_site_detection(self, detector):
        """Test detection of a UK-focused site."""
        pages = {
            "https://example.co.uk": '''
                <html>
                <head>
                    <link rel="alternate" hreflang="en-GB" href="https://example.co.uk">
                </head>
                <body>
                    <script type="application/ld+json">
                    {"@type": "Organization", "address": {"addressCountry": "GB"}}
                    </script>
                    <p>Prices from £29.99. Free UK delivery.</p>
                    <p>Call us: +44 20 1234 5678</p>
                </body>
                </html>
            ''',
        }

        import asyncio
        result = asyncio.run(detector.detect("example.co.uk", pages))

        assert result.primary.code == "uk"
        assert result.primary.confidence >= 0.7
        assert not result.needs_confirmation  # High confidence

    def test_multi_market_site(self, detector):
        """Test detection of a multi-market site."""
        pages = {
            "https://example.com": '''
                <html>
                <head>
                    <link rel="alternate" hreflang="en-GB" href="https://example.co.uk">
                    <link rel="alternate" hreflang="en-US" href="https://example.com">
                    <link rel="alternate" hreflang="de-DE" href="https://example.de">
                    <link rel="alternate" hreflang="fr-FR" href="https://example.fr">
                    <link rel="alternate" hreflang="x-default" href="https://example.com">
                </head>
                <body>
                    <div class="store-switcher">Select your country</div>
                </body>
                </html>
            ''',
        }

        import asyncio
        result = asyncio.run(detector.detect("example.com", pages))

        assert result.is_multi_market_site
        assert len(result.hreflang_markets) >= 3
        assert result.needs_confirmation  # Multi-market needs confirmation

    def test_conflicting_signals(self, detector):
        """Test detection with conflicting signals."""
        pages = {
            "https://example.co.uk": '''
                <html>
                <body>
                    <script type="application/ld+json">
                    {"@type": "Organization", "address": {"addressCountry": "US"}}
                    </script>
                    <p>Prices in $. Ships to USA only.</p>
                </body>
                </html>
            ''',
        }

        import asyncio
        result = asyncio.run(detector.detect("example.co.uk", pages))

        # Should have conflicts (TLD says UK, content says US)
        assert result.has_conflicts or result.needs_confirmation

    def test_no_signals_fallback(self, detector):
        """Test fallback when no signals found."""
        pages = {
            "https://example.com": '''
                <html>
                <body>
                    <p>Welcome to our website.</p>
                </body>
                </html>
            ''',
        }

        import asyncio
        result = asyncio.run(detector.detect("example.com", pages))

        # Should fallback to US with low confidence
        assert result.primary is not None
        assert result.primary.confidence < 0.5
        assert result.needs_confirmation

    def test_explanation_generation(self, detector):
        """Test that explanation is generated correctly."""
        pages = {
            "https://example.co.uk": '''
                <html>
                <body>
                    <p>£29.99</p>
                    <p>+44 20 1234 5678</p>
                </body>
                </html>
            ''',
        }

        import asyncio
        result = asyncio.run(detector.detect("example.co.uk", pages))

        explanation = result.get_explanation()
        assert "United Kingdom" in explanation
        assert "Evidence:" in explanation


# =============================================================================
# DETECTED MARKET MODEL TESTS
# =============================================================================


class TestDetectedMarket:
    """Tests for DetectedMarket model."""

    def test_auto_fills_from_config(self):
        from src.context.market_detection import DetectedMarket

        market = DetectedMarket(code="uk", name="", confidence=0.9)

        assert market.name == "United Kingdom"
        assert market.location_code == 2826
        assert market.language_code == "en"
        assert market.language_name == "English"

    def test_to_dict(self):
        from src.context.market_detection import DetectedMarket

        market = DetectedMarket(code="se", name="Sweden", confidence=0.85)
        data = market.to_dict()

        assert data["code"] == "se"
        assert data["name"] == "Sweden"
        assert data["confidence"] == 0.85
        assert data["location_code"] == 2752

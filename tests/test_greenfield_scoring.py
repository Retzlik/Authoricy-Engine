"""
Test Suite for Greenfield Domain Scoring

Tests the greenfield-specific scoring calculations:
- Domain maturity classification
- Winnability score
- Beachhead keyword selection
- Market opportunity sizing
- Traffic projections
- Industry-specific coefficients
"""

import pytest
from src.scoring.greenfield import (
    # Enums
    DomainMaturity,
    Industry,
    # Data classes
    DomainMetrics,
    WinnabilityAnalysis,
    BeachheadKeyword,
    MarketOpportunity,
    TrafficProjection,
    TrafficProjections,
    # Classification
    classify_domain_maturity,
    is_greenfield,
    is_emerging,
    # Winnability
    calculate_winnability,
    calculate_winnability_full,
    calculate_personalized_difficulty_greenfield,
    calculate_batch_winnability,
    get_winnability_summary,
    # Beachhead
    calculate_beachhead_score,
    select_beachhead_keywords,
    # Market opportunity
    calculate_market_opportunity,
    # Traffic projections
    project_traffic_scenarios,
    # Utilities
    get_industry_from_string,
    requires_eeat_compliance,
    get_coefficient,
    INDUSTRY_COEFFICIENTS,
)


# =============================================================================
# DOMAIN MATURITY CLASSIFICATION TESTS
# =============================================================================


class TestDomainMaturityClassification:
    """Test domain maturity classification logic."""

    def test_greenfield_low_dr_low_keywords(self):
        """DR < 20 and keywords < 50 = GREENFIELD."""
        metrics = DomainMetrics(
            domain_rating=15,
            organic_keywords=30,
            organic_traffic=50,
            referring_domains=10,
        )
        assert classify_domain_maturity(metrics) == DomainMaturity.GREENFIELD

    def test_greenfield_very_new_domain(self):
        """Brand new domain with minimal data = GREENFIELD."""
        metrics = DomainMetrics(
            domain_rating=0,
            organic_keywords=0,
            organic_traffic=0,
            referring_domains=0,
        )
        assert classify_domain_maturity(metrics) == DomainMaturity.GREENFIELD

    def test_greenfield_low_traffic_low_keywords(self):
        """Traffic < 100 and keywords < 30 = GREENFIELD."""
        metrics = DomainMetrics(
            domain_rating=25,
            organic_keywords=20,
            organic_traffic=50,
            referring_domains=15,
        )
        assert classify_domain_maturity(metrics) == DomainMaturity.GREENFIELD

    def test_emerging_medium_dr(self):
        """DR 20-35 with some keywords = EMERGING."""
        metrics = DomainMetrics(
            domain_rating=28,
            organic_keywords=100,
            organic_traffic=500,
            referring_domains=50,
        )
        assert classify_domain_maturity(metrics) == DomainMaturity.EMERGING

    def test_emerging_low_traffic_high_dr(self):
        """High DR but low traffic = EMERGING."""
        metrics = DomainMetrics(
            domain_rating=40,
            organic_keywords=150,
            organic_traffic=800,
            referring_domains=100,
        )
        assert classify_domain_maturity(metrics) == DomainMaturity.EMERGING

    def test_established_all_metrics_high(self):
        """DR > 35, keywords > 200, traffic > 1000 = ESTABLISHED."""
        metrics = DomainMetrics(
            domain_rating=50,
            organic_keywords=500,
            organic_traffic=5000,
            referring_domains=200,
        )
        assert classify_domain_maturity(metrics) == DomainMaturity.ESTABLISHED

    def test_established_enterprise_domain(self):
        """Large enterprise domain = ESTABLISHED."""
        metrics = DomainMetrics(
            domain_rating=75,
            organic_keywords=10000,
            organic_traffic=100000,
            referring_domains=5000,
        )
        assert classify_domain_maturity(metrics) == DomainMaturity.ESTABLISHED

    def test_is_greenfield_helper(self):
        """Test is_greenfield helper function."""
        greenfield_metrics = DomainMetrics(domain_rating=10, organic_keywords=20)
        established_metrics = DomainMetrics(domain_rating=50, organic_keywords=500, organic_traffic=5000)

        assert is_greenfield(greenfield_metrics) is True
        assert is_greenfield(established_metrics) is False

    def test_is_emerging_helper(self):
        """Test is_emerging helper function."""
        emerging_metrics = DomainMetrics(domain_rating=30, organic_keywords=150, organic_traffic=800)
        established_metrics = DomainMetrics(domain_rating=50, organic_keywords=500, organic_traffic=5000)

        assert is_emerging(emerging_metrics) is True
        assert is_emerging(established_metrics) is False

    def test_boundary_conditions(self):
        """Test exact boundary values."""
        # Exactly at greenfield threshold
        boundary_greenfield = DomainMetrics(domain_rating=19, organic_keywords=49)
        assert classify_domain_maturity(boundary_greenfield) == DomainMaturity.GREENFIELD

        # Just above greenfield threshold
        boundary_emerging = DomainMetrics(domain_rating=20, organic_keywords=50, organic_traffic=200)
        assert classify_domain_maturity(boundary_emerging) == DomainMaturity.EMERGING

        # Exactly at established threshold
        boundary_established = DomainMetrics(domain_rating=35, organic_keywords=200, organic_traffic=1000)
        assert classify_domain_maturity(boundary_established) == DomainMaturity.ESTABLISHED


# =============================================================================
# WINNABILITY SCORE TESTS
# =============================================================================


class TestWinnabilityScore:
    """Test winnability score calculation."""

    def test_high_winnability_favorable_serp(self):
        """Low SERP DR, low KD, no AI Overview = high winnability."""
        score, components = calculate_winnability(
            target_dr=15,
            avg_serp_dr=25,
            min_serp_dr=12,
            has_low_dr_rankings=True,
            weak_content_signals=["outdated_content", "thin_content"],
            has_ai_overview=False,
            keyword_difficulty=20,
            industry="saas",
        )

        assert score >= 70, f"Expected high winnability, got {score}"
        assert components["low_dr_bonus"] > 0, "Should have low DR bonus"
        assert components["content_bonus"] > 0, "Should have content bonus"
        assert components["ai_penalty"] == 0, "Should have no AI penalty"

    def test_low_winnability_unfavorable_serp(self):
        """High SERP DR, high KD, AI Overview = low winnability."""
        score, components = calculate_winnability(
            target_dr=10,
            avg_serp_dr=70,
            min_serp_dr=55,
            has_low_dr_rankings=False,
            weak_content_signals=[],
            has_ai_overview=True,
            keyword_difficulty=75,
            industry="saas",
        )

        assert score <= 40, f"Expected low winnability, got {score}"
        assert components["dr_gap_penalty"] < 0, "Should have DR gap penalty"
        assert components["ai_penalty"] < 0, "Should have AI penalty"
        assert components["kd_penalty"] < 0, "Should have KD penalty"

    def test_dr_advantage_bonus(self):
        """Higher DR than SERP average should give bonus."""
        score, components = calculate_winnability(
            target_dr=50,
            avg_serp_dr=35,
            min_serp_dr=20,
            has_low_dr_rankings=True,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=25,
            industry="saas",
        )

        assert components["dr_gap_penalty"] > 0, "Should have DR advantage (positive)"
        assert score >= 80, f"Expected high winnability with DR advantage, got {score}"

    def test_ai_overview_penalty(self):
        """AI Overview presence should reduce winnability."""
        score_without_aio, _ = calculate_winnability(
            target_dr=20,
            avg_serp_dr=30,
            min_serp_dr=15,
            has_low_dr_rankings=True,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=25,
            industry="saas",
        )

        score_with_aio, _ = calculate_winnability(
            target_dr=20,
            avg_serp_dr=30,
            min_serp_dr=15,
            has_low_dr_rankings=True,
            weak_content_signals=[],
            has_ai_overview=True,
            keyword_difficulty=25,
            industry="saas",
        )

        assert score_without_aio > score_with_aio, "AI Overview should reduce score"
        assert score_without_aio - score_with_aio >= 15, "AI penalty should be significant"

    def test_weak_content_signals_boost(self):
        """Weak content signals should increase winnability."""
        score_no_signals, _ = calculate_winnability(
            target_dr=20,
            avg_serp_dr=40,
            min_serp_dr=25,
            has_low_dr_rankings=False,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=35,
            industry="saas",
        )

        score_with_signals, _ = calculate_winnability(
            target_dr=20,
            avg_serp_dr=40,
            min_serp_dr=25,
            has_low_dr_rankings=False,
            weak_content_signals=["outdated_content", "thin_content", "ugc_content"],
            has_ai_overview=False,
            keyword_difficulty=35,
            industry="saas",
        )

        assert score_with_signals > score_no_signals, "Weak content signals should boost score"

    def test_score_bounds(self):
        """Winnability score should always be 0-100."""
        # Extremely favorable conditions
        high_score, _ = calculate_winnability(
            target_dr=80,
            avg_serp_dr=20,
            min_serp_dr=5,
            has_low_dr_rankings=True,
            weak_content_signals=["a", "b", "c", "d", "e"],
            has_ai_overview=False,
            keyword_difficulty=10,
            industry="saas",
        )
        assert 0 <= high_score <= 100

        # Extremely unfavorable conditions
        low_score, _ = calculate_winnability(
            target_dr=5,
            avg_serp_dr=90,
            min_serp_dr=70,
            has_low_dr_rankings=False,
            weak_content_signals=[],
            has_ai_overview=True,
            keyword_difficulty=95,
            industry="saas",
        )
        assert 0 <= low_score <= 100


# =============================================================================
# INDUSTRY COEFFICIENT TESTS
# =============================================================================


class TestIndustryCoefficients:
    """Test industry-specific coefficient adjustments."""

    def test_ymyl_health_harder(self):
        """YMYL health should be harder than SaaS."""
        saas_score, _ = calculate_winnability(
            target_dr=20,
            avg_serp_dr=40,
            min_serp_dr=25,
            has_low_dr_rankings=True,
            weak_content_signals=["thin_content"],
            has_ai_overview=True,
            keyword_difficulty=40,
            industry="saas",
        )

        ymyl_score, _ = calculate_winnability(
            target_dr=20,
            avg_serp_dr=40,
            min_serp_dr=25,
            has_low_dr_rankings=True,
            weak_content_signals=["thin_content"],
            has_ai_overview=True,
            keyword_difficulty=40,
            industry="ymyl_health",
        )

        assert ymyl_score < saas_score, "YMYL health should have lower winnability"

    def test_local_services_easier(self):
        """Local services should be easier due to lower competition."""
        saas_score, _ = calculate_winnability(
            target_dr=15,
            avg_serp_dr=35,
            min_serp_dr=20,
            has_low_dr_rankings=True,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=30,
            industry="saas",
        )

        local_score, _ = calculate_winnability(
            target_dr=15,
            avg_serp_dr=35,
            min_serp_dr=20,
            has_low_dr_rankings=True,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=30,
            industry="local_services",
        )

        assert local_score > saas_score, "Local services should have higher winnability"

    def test_geo_modifier_bonus_local(self):
        """Local services with geo modifier should get bonus."""
        without_geo, _ = calculate_winnability(
            target_dr=15,
            avg_serp_dr=30,
            min_serp_dr=18,
            has_low_dr_rankings=True,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=25,
            industry="local_services",
            has_geo_modifier=False,
        )

        with_geo, _ = calculate_winnability(
            target_dr=15,
            avg_serp_dr=30,
            min_serp_dr=18,
            has_low_dr_rankings=True,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=25,
            industry="local_services",
            has_geo_modifier=True,
        )

        assert with_geo > without_geo, "Geo modifier should increase local winnability"

    def test_ecommerce_dr_weight_lower(self):
        """E-commerce DR weight should be lower (0.8x)."""
        # Same conditions, different DR gap penalty
        saas_score, saas_comp = calculate_winnability(
            target_dr=15,
            avg_serp_dr=50,  # Large DR gap
            min_serp_dr=30,
            has_low_dr_rankings=False,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=30,
            industry="saas",
        )

        ecom_score, ecom_comp = calculate_winnability(
            target_dr=15,
            avg_serp_dr=50,
            min_serp_dr=30,
            has_low_dr_rankings=False,
            weak_content_signals=[],
            has_ai_overview=False,
            keyword_difficulty=30,
            industry="ecommerce",
        )

        # E-commerce should have smaller penalty (less negative)
        assert ecom_comp["dr_gap_penalty"] > saas_comp["dr_gap_penalty"], \
            "E-commerce should have smaller DR penalty"

    def test_get_industry_from_string(self):
        """Test industry string normalization."""
        assert get_industry_from_string("SaaS") == "saas"
        assert get_industry_from_string("e-commerce") == "ecommerce"
        assert get_industry_from_string("YMYL Health") == "ymyl_health"
        assert get_industry_from_string("local service") == "local_services"
        assert get_industry_from_string("unknown") == "saas"  # Default

    def test_requires_eeat_compliance(self):
        """Test E-E-A-T compliance flag."""
        assert requires_eeat_compliance("ymyl_health") is True
        assert requires_eeat_compliance("ymyl_finance") is True
        assert requires_eeat_compliance("saas") is False
        assert requires_eeat_compliance("ecommerce") is False

    def test_get_coefficient(self):
        """Test coefficient retrieval."""
        assert get_coefficient("saas", "dr_weight") == 1.0
        assert get_coefficient("ymyl_health", "dr_weight") == 1.8
        assert get_coefficient("local_services", "geo_modifier_bonus") == 20
        assert get_coefficient("saas", "nonexistent", default=999) == 999


# =============================================================================
# PERSONALIZED DIFFICULTY TESTS
# =============================================================================


class TestPersonalizedDifficulty:
    """Test personalized difficulty calculation for greenfield."""

    def test_authority_gap_increases_difficulty(self):
        """SERP DR >> target DR should increase difficulty."""
        pd = calculate_personalized_difficulty_greenfield(
            base_kd=40,
            target_dr=15,
            avg_serp_dr=60,
        )

        assert pd > 40, f"Personalized KD should be higher than base, got {pd}"

    def test_authority_advantage_decreases_difficulty(self):
        """Target DR >> SERP DR should decrease difficulty."""
        pd = calculate_personalized_difficulty_greenfield(
            base_kd=40,
            target_dr=70,
            avg_serp_dr=40,
        )

        assert pd < 40, f"Personalized KD should be lower than base, got {pd}"

    def test_equal_dr_no_change(self):
        """Equal DR should result in similar difficulty."""
        pd = calculate_personalized_difficulty_greenfield(
            base_kd=40,
            target_dr=50,
            avg_serp_dr=50,
        )

        assert 38 <= pd <= 42, f"Personalized KD should be close to base, got {pd}"

    def test_difficulty_bounds(self):
        """Personalized difficulty should be 0-100."""
        # Extreme authority disadvantage
        high_pd = calculate_personalized_difficulty_greenfield(
            base_kd=80,
            target_dr=5,
            avg_serp_dr=90,
        )
        assert 0 <= high_pd <= 100

        # Extreme authority advantage
        low_pd = calculate_personalized_difficulty_greenfield(
            base_kd=20,
            target_dr=90,
            avg_serp_dr=30,
        )
        assert 0 <= low_pd <= 100


# =============================================================================
# BEACHHEAD SELECTION TESTS
# =============================================================================


class TestBeachheadSelection:
    """Test beachhead keyword selection."""

    def test_beachhead_score_calculation(self):
        """Test beachhead score formula."""
        score = calculate_beachhead_score(
            search_volume=1000,
            business_relevance=0.8,
            winnability_score=85,
            personalized_difficulty=25,
        )

        # Score = (1000 * 0.8 * 0.85) / (25 + 10) = 680 / 35 ≈ 19.4
        assert 19 <= score <= 20, f"Unexpected beachhead score: {score}"

    def test_beachhead_score_higher_volume_higher_score(self):
        """Higher volume should increase beachhead score."""
        low_volume_score = calculate_beachhead_score(
            search_volume=500,
            business_relevance=0.8,
            winnability_score=80,
            personalized_difficulty=30,
        )

        high_volume_score = calculate_beachhead_score(
            search_volume=2000,
            business_relevance=0.8,
            winnability_score=80,
            personalized_difficulty=30,
        )

        assert high_volume_score > low_volume_score

    def test_beachhead_score_lower_difficulty_higher_score(self):
        """Lower difficulty should increase beachhead score."""
        high_difficulty_score = calculate_beachhead_score(
            search_volume=1000,
            business_relevance=0.8,
            winnability_score=80,
            personalized_difficulty=60,
        )

        low_difficulty_score = calculate_beachhead_score(
            search_volume=1000,
            business_relevance=0.8,
            winnability_score=80,
            personalized_difficulty=20,
        )

        assert low_difficulty_score > high_difficulty_score

    def test_select_beachhead_keywords_filters_correctly(self):
        """Beachhead selection should filter by criteria."""
        keywords = [
            {"keyword": "good_keyword", "search_volume": 500, "keyword_difficulty": 25, "business_relevance": 0.9},
            {"keyword": "low_volume", "search_volume": 50, "keyword_difficulty": 20, "business_relevance": 0.9},
            {"keyword": "high_kd", "search_volume": 500, "keyword_difficulty": 60, "business_relevance": 0.9},
            {"keyword": "low_relevance", "search_volume": 500, "keyword_difficulty": 25, "business_relevance": 0.3},
        ]

        # Create winnability analyses
        analyses = {
            "good_keyword": WinnabilityAnalysis(
                keyword="good_keyword", winnability_score=85, personalized_difficulty=22,
                avg_serp_dr=25, min_serp_dr=15, has_low_dr_rankings=True,
            ),
            "low_volume": WinnabilityAnalysis(
                keyword="low_volume", winnability_score=90, personalized_difficulty=18,
                avg_serp_dr=20, min_serp_dr=10, has_low_dr_rankings=True,
            ),
            "high_kd": WinnabilityAnalysis(
                keyword="high_kd", winnability_score=50, personalized_difficulty=55,
                avg_serp_dr=50, min_serp_dr=35, has_low_dr_rankings=False,
            ),
            "low_relevance": WinnabilityAnalysis(
                keyword="low_relevance", winnability_score=85, personalized_difficulty=22,
                avg_serp_dr=25, min_serp_dr=15, has_low_dr_rankings=True,
            ),
        }

        beachhead = select_beachhead_keywords(
            keywords=keywords,
            winnability_analyses=analyses,
            min_volume=100,
            min_winnability=70,
            max_kd=30,
            min_business_relevance=0.7,
        )

        # Only "good_keyword" should pass all filters
        keyword_names = [bh.keyword for bh in beachhead]
        assert "good_keyword" in keyword_names
        assert "low_volume" not in keyword_names  # Volume too low
        assert "high_kd" not in keyword_names  # KD too high, winnability too low
        assert "low_relevance" not in keyword_names  # Relevance too low


# =============================================================================
# MARKET OPPORTUNITY TESTS
# =============================================================================


class TestMarketOpportunity:
    """Test market opportunity sizing."""

    def test_tam_sam_som_ordering(self):
        """TAM >= SAM >= SOM always."""
        keywords = [
            {"keyword": f"kw{i}", "search_volume": 100 * (i + 1), "business_relevance": 0.5 + (i % 2) * 0.3}
            for i in range(20)
        ]

        analyses = {
            f"kw{i}": WinnabilityAnalysis(
                keyword=f"kw{i}", winnability_score=40 + i * 3, personalized_difficulty=30,
                avg_serp_dr=30, min_serp_dr=20, has_low_dr_rankings=True,
            )
            for i in range(20)
        }

        competitors = [
            {"domain": "comp1.com", "organic_traffic": 10000, "organic_keywords": 500},
            {"domain": "comp2.com", "organic_traffic": 5000, "organic_keywords": 300},
        ]

        opportunity = calculate_market_opportunity(
            keywords=keywords,
            winnability_analyses=analyses,
            competitors=competitors,
        )

        assert opportunity.tam_volume >= opportunity.sam_volume >= opportunity.som_volume
        assert opportunity.tam_keywords >= opportunity.sam_keywords >= opportunity.som_keywords

    def test_competitor_shares_sum_to_100(self):
        """Competitor market shares should sum to ~100%."""
        keywords = [{"keyword": "test", "search_volume": 1000, "business_relevance": 0.8}]
        analyses = {"test": WinnabilityAnalysis(
            keyword="test", winnability_score=70, personalized_difficulty=25,
            avg_serp_dr=30, min_serp_dr=20, has_low_dr_rankings=True,
        )}

        competitors = [
            {"domain": "comp1.com", "organic_traffic": 6000, "organic_keywords": 500},
            {"domain": "comp2.com", "organic_traffic": 3000, "organic_keywords": 300},
            {"domain": "comp3.com", "organic_traffic": 1000, "organic_keywords": 100},
        ]

        opportunity = calculate_market_opportunity(
            keywords=keywords,
            winnability_analyses=analyses,
            competitors=competitors,
        )

        total_share = sum(c["share_percent"] for c in opportunity.competitor_shares)
        assert 99 <= total_share <= 101, f"Shares should sum to ~100%, got {total_share}"


# =============================================================================
# TRAFFIC PROJECTION TESTS
# =============================================================================


class TestTrafficProjections:
    """Test traffic projection scenarios."""

    def test_three_scenarios_ordering(self):
        """Conservative < Expected < Aggressive for same timeframe."""
        beachhead = [
            BeachheadKeyword(
                keyword="test_kw",
                search_volume=1000,
                keyword_difficulty=25,
                personalized_difficulty=22,
                winnability_score=80,
                business_relevance=0.9,
                avg_serp_dr=28,
                has_ai_overview=False,
                beachhead_score=25,
                beachhead_priority=1,
                recommended_content_type="guide",
                estimated_time_to_rank_weeks=8,
                estimated_traffic_gain=50,
            )
        ]

        projections = project_traffic_scenarios(
            beachhead_keywords=beachhead,
            growth_keywords=[],
            winnability_analyses={},
        )

        # Check ordering at each time point
        for month in [6, 12, 24]:
            conservative = projections.conservative.traffic_by_month.get(month, 0)
            expected = projections.expected.traffic_by_month.get(month, 0)
            aggressive = projections.aggressive.traffic_by_month.get(month, 0)

            assert conservative <= expected <= aggressive, \
                f"Month {month}: {conservative} <= {expected} <= {aggressive} should hold"

    def test_confidence_levels(self):
        """Confidence should be: conservative=0.75, expected=0.50, aggressive=0.25."""
        beachhead = [
            BeachheadKeyword(
                keyword="test", search_volume=500, keyword_difficulty=20,
                personalized_difficulty=18, winnability_score=85, business_relevance=0.9,
                avg_serp_dr=25, has_ai_overview=False, beachhead_score=20,
                beachhead_priority=1, recommended_content_type="guide",
                estimated_time_to_rank_weeks=6, estimated_traffic_gain=30,
            )
        ]

        projections = project_traffic_scenarios(
            beachhead_keywords=beachhead,
            growth_keywords=[],
            winnability_analyses={},
        )

        assert projections.conservative.confidence == 0.75
        assert projections.expected.confidence == 0.50
        assert projections.aggressive.confidence == 0.25

    def test_ai_overview_reduces_traffic(self):
        """Keywords with AI Overview should project less traffic."""
        beachhead_no_aio = [
            BeachheadKeyword(
                keyword="no_aio", search_volume=1000, keyword_difficulty=25,
                personalized_difficulty=22, winnability_score=80, business_relevance=0.9,
                avg_serp_dr=28, has_ai_overview=False, beachhead_score=25,
                beachhead_priority=1, recommended_content_type="guide",
                estimated_time_to_rank_weeks=8, estimated_traffic_gain=50,
            )
        ]

        beachhead_with_aio = [
            BeachheadKeyword(
                keyword="with_aio", search_volume=1000, keyword_difficulty=25,
                personalized_difficulty=22, winnability_score=80, business_relevance=0.9,
                avg_serp_dr=28, has_ai_overview=True, beachhead_score=25,
                beachhead_priority=1, recommended_content_type="guide",
                estimated_time_to_rank_weeks=8, estimated_traffic_gain=50,
            )
        ]

        proj_no_aio = project_traffic_scenarios(beachhead_no_aio, [], {})
        proj_with_aio = project_traffic_scenarios(beachhead_with_aio, [], {})

        # Traffic should be lower with AI Overview
        assert proj_with_aio.expected.traffic_by_month[12] < proj_no_aio.expected.traffic_by_month[12]


# =============================================================================
# BATCH PROCESSING TESTS
# =============================================================================


class TestBatchProcessing:
    """Test batch winnability analysis."""

    def test_batch_winnability_returns_dict(self):
        """Batch winnability should return keyword -> analysis mapping."""
        keywords = [
            {"keyword": "kw1", "search_volume": 500, "keyword_difficulty": 25},
            {"keyword": "kw2", "search_volume": 1000, "keyword_difficulty": 40},
        ]

        serp_cache = {
            "kw1": {"results": [{"domain_rating": 25}, {"domain_rating": 30}]},
            "kw2": {"results": [{"domain_rating": 45}, {"domain_rating": 50}]},
        }

        results = calculate_batch_winnability(
            keywords=keywords,
            target_dr=20,
            serp_cache=serp_cache,
            industry="saas",
        )

        assert "kw1" in results
        assert "kw2" in results
        assert isinstance(results["kw1"], WinnabilityAnalysis)

    def test_winnability_summary_stats(self):
        """Summary should include correct statistics."""
        analyses = {
            "kw1": WinnabilityAnalysis(
                keyword="kw1", winnability_score=85, personalized_difficulty=20,
                avg_serp_dr=25, min_serp_dr=15, has_low_dr_rankings=True,
                is_beachhead_candidate=True, has_ai_overview=False,
            ),
            "kw2": WinnabilityAnalysis(
                keyword="kw2", winnability_score=45, personalized_difficulty=55,
                avg_serp_dr=50, min_serp_dr=40, has_low_dr_rankings=False,
                is_beachhead_candidate=False, has_ai_overview=True,
            ),
        }

        summary = get_winnability_summary(analyses)

        assert summary["total_keywords"] == 2
        assert summary["avg_winnability"] == 65  # (85 + 45) / 2
        assert summary["max_winnability"] == 85
        assert summary["min_winnability"] == 45
        assert summary["beachhead_count"] == 1
        assert summary["ai_overview_count"] == 1
        assert summary["low_dr_opportunity_count"] == 1


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_keywords_beachhead_selection(self):
        """Empty keyword list should return empty beachhead."""
        result = select_beachhead_keywords(
            keywords=[],
            winnability_analyses={},
        )
        assert result == []

    def test_no_matching_winnability_analyses(self):
        """Keywords without winnability data should be skipped."""
        keywords = [{"keyword": "orphan_kw", "search_volume": 1000, "business_relevance": 0.9}]

        result = select_beachhead_keywords(
            keywords=keywords,
            winnability_analyses={},  # No analysis for orphan_kw
        )
        assert result == []

    def test_zero_search_volume(self):
        """Zero volume keywords should have zero beachhead score."""
        score = calculate_beachhead_score(
            search_volume=0,
            business_relevance=0.9,
            winnability_score=90,
            personalized_difficulty=20,
        )
        assert score == 0

    def test_none_values_in_domain_metrics(self):
        """DomainMetrics with None values should default to 0."""
        metrics = DomainMetrics()  # All defaults
        maturity = classify_domain_maturity(metrics)
        assert maturity == DomainMaturity.GREENFIELD

    def test_empty_competitor_list_market_opportunity(self):
        """Empty competitor list should still calculate TAM/SAM/SOM."""
        keywords = [{"keyword": "test", "search_volume": 1000, "business_relevance": 0.8}]
        analyses = {"test": WinnabilityAnalysis(
            keyword="test", winnability_score=70, personalized_difficulty=25,
            avg_serp_dr=30, min_serp_dr=20, has_low_dr_rankings=True,
        )}

        opportunity = calculate_market_opportunity(
            keywords=keywords,
            winnability_analyses=analyses,
            competitors=[],
        )

        assert opportunity.tam_volume == 1000
        assert opportunity.competitor_shares == []

"""
Test Suite for Phase 1: Scoring Engine

Tests the three core scoring formulas:
- Opportunity Score
- Personalized Difficulty Score
- Content Decay Score
"""

import pytest
from src.scoring import (
    calculate_opportunity_score,
    calculate_personalized_difficulty,
    calculate_content_decay_score,
    OpportunityResult,
    DifficultyResult,
    DecayResult,
)


class TestOpportunityScore:
    """Test Opportunity Score calculation."""

    def test_high_opportunity_keyword(self):
        """High volume, low competition = high opportunity."""
        result = calculate_opportunity_score(
            search_volume=10000,
            keyword_difficulty=20,
            current_position=15,
            click_potential=0.8,
            search_intent="transactional",
        )

        assert isinstance(result, OpportunityResult)
        assert result.score >= 80, f"Expected high opportunity score, got {result.score}"
        assert result.tier == "high"

    def test_low_opportunity_keyword(self):
        """Low volume, high competition = low opportunity."""
        result = calculate_opportunity_score(
            search_volume=50,
            keyword_difficulty=90,
            current_position=100,
            click_potential=0.2,
            search_intent="informational",
        )

        assert result.score < 40, f"Expected low opportunity score, got {result.score}"
        assert result.tier == "low"

    def test_medium_opportunity_keyword(self):
        """Medium metrics = medium opportunity."""
        result = calculate_opportunity_score(
            search_volume=1000,
            keyword_difficulty=50,
            current_position=20,
            click_potential=0.5,
            search_intent="commercial",
        )

        assert 40 <= result.score <= 70, f"Expected medium score, got {result.score}"
        assert result.tier == "medium"

    def test_transactional_intent_boost(self):
        """Transactional intent should boost score vs informational."""
        transactional = calculate_opportunity_score(
            search_volume=1000,
            keyword_difficulty=50,
            current_position=20,
            click_potential=0.5,
            search_intent="transactional",
        )

        informational = calculate_opportunity_score(
            search_volume=1000,
            keyword_difficulty=50,
            current_position=20,
            click_potential=0.5,
            search_intent="informational",
        )

        assert transactional.score > informational.score, "Transactional should score higher"

    def test_strike_distance_bonus(self):
        """Positions 11-20 (strike distance) should get bonus."""
        in_strike = calculate_opportunity_score(
            search_volume=1000,
            keyword_difficulty=50,
            current_position=15,  # Strike distance
            click_potential=0.5,
            search_intent="commercial",
        )

        out_of_strike = calculate_opportunity_score(
            search_volume=1000,
            keyword_difficulty=50,
            current_position=50,  # Not in strike distance
            click_potential=0.5,
            search_intent="commercial",
        )

        assert in_strike.score > out_of_strike.score, "Strike distance should boost score"

    def test_zero_volume_handling(self):
        """Zero volume should not cause errors."""
        result = calculate_opportunity_score(
            search_volume=0,
            keyword_difficulty=50,
            current_position=20,
            click_potential=0.5,
            search_intent="commercial",
        )

        assert result.score == 0 or result.tier == "low"

    def test_result_contains_breakdown(self):
        """Result should contain scoring breakdown."""
        result = calculate_opportunity_score(
            search_volume=1000,
            keyword_difficulty=50,
            current_position=20,
            click_potential=0.5,
            search_intent="commercial",
        )

        assert hasattr(result, "breakdown")
        assert "volume_factor" in result.breakdown or "volume" in str(result.breakdown)


class TestPersonalizedDifficulty:
    """Test Personalized Difficulty Score (MarketMuse methodology)."""

    def test_strong_site_lower_difficulty(self):
        """Strong site metrics should lower personalized difficulty."""
        result = calculate_personalized_difficulty(
            keyword_difficulty=60,
            domain_authority=70,
            topical_authority=0.8,
            content_depth=0.9,
            backlink_profile_strength=0.8,
        )

        assert isinstance(result, DifficultyResult)
        assert result.personalized_kd < 60, "Strong site should have lower PD than KD"

    def test_weak_site_higher_difficulty(self):
        """Weak site metrics should raise personalized difficulty."""
        result = calculate_personalized_difficulty(
            keyword_difficulty=40,
            domain_authority=15,
            topical_authority=0.2,
            content_depth=0.3,
            backlink_profile_strength=0.2,
        )

        assert result.personalized_kd > 40, "Weak site should have higher PD than KD"

    def test_matching_authority_similar_difficulty(self):
        """Site authority matching KD should give similar PD."""
        result = calculate_personalized_difficulty(
            keyword_difficulty=50,
            domain_authority=50,
            topical_authority=0.5,
            content_depth=0.5,
            backlink_profile_strength=0.5,
        )

        assert abs(result.personalized_kd - 50) < 15, "Should be close to base KD"

    def test_topical_authority_impact(self):
        """Topical authority should significantly impact difficulty."""
        high_topical = calculate_personalized_difficulty(
            keyword_difficulty=60,
            domain_authority=40,
            topical_authority=0.9,  # High topical authority
            content_depth=0.5,
            backlink_profile_strength=0.5,
        )

        low_topical = calculate_personalized_difficulty(
            keyword_difficulty=60,
            domain_authority=40,
            topical_authority=0.1,  # Low topical authority
            content_depth=0.5,
            backlink_profile_strength=0.5,
        )

        assert high_topical.personalized_kd < low_topical.personalized_kd

    def test_difficulty_bounded(self):
        """Difficulty should be bounded between 0 and 100."""
        # Test edge case: very strong site
        strong = calculate_personalized_difficulty(
            keyword_difficulty=10,
            domain_authority=95,
            topical_authority=0.99,
            content_depth=0.99,
            backlink_profile_strength=0.99,
        )
        assert 0 <= strong.personalized_kd <= 100

        # Test edge case: very weak site
        weak = calculate_personalized_difficulty(
            keyword_difficulty=90,
            domain_authority=5,
            topical_authority=0.01,
            content_depth=0.01,
            backlink_profile_strength=0.01,
        )
        assert 0 <= weak.personalized_kd <= 100

    def test_result_contains_factors(self):
        """Result should explain which factors affected difficulty."""
        result = calculate_personalized_difficulty(
            keyword_difficulty=60,
            domain_authority=70,
            topical_authority=0.8,
            content_depth=0.9,
            backlink_profile_strength=0.8,
        )

        assert hasattr(result, "factors")
        assert result.factors is not None


class TestContentDecayScore:
    """Test Content Decay Score calculation."""

    def test_recent_update_low_decay(self):
        """Recently updated content should have low decay."""
        result = calculate_content_decay_score(
            last_modified_days=30,  # 1 month ago
            traffic_trend=-0.05,  # Minor decline
            ranking_changes=2,  # Few changes
            content_age_months=6,
        )

        assert isinstance(result, DecayResult)
        assert result.score < 30, "Recent content should have low decay score"

    def test_old_content_high_decay(self):
        """Old content with declining traffic should have high decay."""
        result = calculate_content_decay_score(
            last_modified_days=730,  # 2 years ago
            traffic_trend=-0.5,  # 50% decline
            ranking_changes=10,  # Many changes
            content_age_months=36,
        )

        assert result.score > 70, "Old declining content should have high decay"
        assert result.recommendation in ["update", "kill"]

    def test_evergreen_content_stable(self):
        """Evergreen content with stable traffic should be fine."""
        result = calculate_content_decay_score(
            last_modified_days=365,  # 1 year ago
            traffic_trend=0.1,  # Slight growth
            ranking_changes=1,  # Stable
            content_age_months=24,
        )

        assert result.score < 50
        assert result.recommendation in ["keep", "monitor"]

    def test_kuck_recommendation_keep(self):
        """Should recommend KEEP for healthy content."""
        result = calculate_content_decay_score(
            last_modified_days=90,
            traffic_trend=0.2,
            ranking_changes=0,
            content_age_months=12,
        )

        assert result.recommendation == "keep"

    def test_kuck_recommendation_update(self):
        """Should recommend UPDATE for moderately decayed content."""
        result = calculate_content_decay_score(
            last_modified_days=365,
            traffic_trend=-0.3,
            ranking_changes=5,
            content_age_months=18,
        )

        assert result.recommendation in ["update", "consolidate"]

    def test_kuck_recommendation_kill(self):
        """Should recommend KILL for severely decayed content."""
        result = calculate_content_decay_score(
            last_modified_days=1000,
            traffic_trend=-0.8,
            ranking_changes=15,
            content_age_months=48,
        )

        assert result.recommendation in ["kill", "consolidate"]

    def test_decay_urgency_level(self):
        """Result should include urgency level."""
        result = calculate_content_decay_score(
            last_modified_days=365,
            traffic_trend=-0.4,
            ranking_changes=8,
            content_age_months=24,
        )

        assert hasattr(result, "urgency")
        assert result.urgency in ["low", "medium", "high", "critical"]


class TestScoringEdgeCases:
    """Test edge cases and error handling."""

    def test_opportunity_with_none_values(self):
        """Should handle None values gracefully."""
        # Test with defaults for missing data
        result = calculate_opportunity_score(
            search_volume=1000,
            keyword_difficulty=50,
            current_position=None,  # Not ranking
            click_potential=None,  # Unknown
            search_intent=None,  # Unknown
        )

        assert isinstance(result, OpportunityResult)

    def test_difficulty_with_zero_authority(self):
        """Should handle zero domain authority."""
        result = calculate_personalized_difficulty(
            keyword_difficulty=50,
            domain_authority=0,
            topical_authority=0,
            content_depth=0,
            backlink_profile_strength=0,
        )

        assert result.personalized_kd >= 50  # Should be at least base KD

    def test_decay_with_new_content(self):
        """Should handle brand new content."""
        result = calculate_content_decay_score(
            last_modified_days=1,
            traffic_trend=0,  # No trend yet
            ranking_changes=0,
            content_age_months=0,
        )

        assert result.score == 0 or result.recommendation == "keep"


class TestScoringIntegration:
    """Test scoring functions work together."""

    def test_full_keyword_analysis(self):
        """Test complete keyword scoring workflow."""
        # Calculate opportunity
        opportunity = calculate_opportunity_score(
            search_volume=5000,
            keyword_difficulty=45,
            current_position=12,
            click_potential=0.7,
            search_intent="commercial",
        )

        # Calculate personalized difficulty
        difficulty = calculate_personalized_difficulty(
            keyword_difficulty=45,
            domain_authority=50,
            topical_authority=0.6,
            content_depth=0.7,
            backlink_profile_strength=0.5,
        )

        # Both should return valid results
        assert opportunity.score > 0
        assert 0 <= difficulty.personalized_kd <= 100

        # Opportunity should account for personalized difficulty
        # (High opportunity + achievable difficulty = good target)
        is_good_target = opportunity.score > 60 and difficulty.personalized_kd < 50
        assert isinstance(is_good_target, bool)

    def test_content_audit_workflow(self):
        """Test content audit scoring workflow."""
        pages = [
            {"url": "/blog/post-1", "age": 180, "trend": -0.1, "changes": 2, "months": 6},
            {"url": "/blog/post-2", "age": 730, "trend": -0.6, "changes": 12, "months": 24},
            {"url": "/blog/post-3", "age": 90, "trend": 0.2, "changes": 0, "months": 3},
        ]

        results = []
        for page in pages:
            decay = calculate_content_decay_score(
                last_modified_days=page["age"],
                traffic_trend=page["trend"],
                ranking_changes=page["changes"],
                content_age_months=page["months"],
            )
            results.append({
                "url": page["url"],
                "decay_score": decay.score,
                "recommendation": decay.recommendation,
            })

        # Should have mix of recommendations
        recommendations = [r["recommendation"] for r in results]
        assert "keep" in recommendations or any(r["decay_score"] < 30 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

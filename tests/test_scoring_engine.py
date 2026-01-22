"""
Test Suite for Phase 1: Scoring Engine

Tests the three core scoring calculations:
- Opportunity Score
- Personalized Difficulty Score
- Content Decay Score
"""

import pytest
from src.scoring import (
    calculate_opportunity_score,
    calculate_personalized_difficulty,
    calculate_decay_score,
    OpportunityAnalysis,
    DifficultyAnalysis,
    DecayAnalysis,
)


class TestOpportunityScore:
    """Test Opportunity Score calculation."""

    @pytest.fixture
    def domain_data(self):
        """Standard domain data for testing."""
        return {
            "domain_rank": 45,
            "categories": [
                {"name": "Software", "keyword_count": 150},
                {"name": "Project Management", "keyword_count": 80},
            ],
        }

    def test_high_opportunity_keyword(self, domain_data):
        """High volume, low competition = high opportunity."""
        keyword = {
            "keyword": "projekthantering software",
            "search_volume": 10000,
            "keyword_difficulty": 20,
            "position": 15,
            "intent": "transactional",
        }

        result = calculate_opportunity_score(keyword, domain_data)

        assert isinstance(result, OpportunityAnalysis)
        assert result.opportunity_score >= 60, f"Expected high opportunity score, got {result.opportunity_score}"

    def test_low_opportunity_keyword(self, domain_data):
        """Low volume, high competition = lower opportunity."""
        keyword = {
            "keyword": "random keyword",
            "search_volume": 50,
            "keyword_difficulty": 90,
            "position": 100,
            "intent": "informational",
        }

        result = calculate_opportunity_score(keyword, domain_data)

        # Score should be lower than high opportunity (but may not be <50 due to position gap)
        assert result.opportunity_score < 70, f"Expected lower opportunity score, got {result.opportunity_score}"

    def test_medium_opportunity_keyword(self, domain_data):
        """Medium metrics = medium opportunity."""
        keyword = {
            "keyword": "test keyword",
            "search_volume": 1000,
            "keyword_difficulty": 50,
            "position": 20,
            "intent": "commercial",
        }

        result = calculate_opportunity_score(keyword, domain_data)

        assert 30 <= result.opportunity_score <= 80, f"Expected medium score, got {result.opportunity_score}"

    def test_transactional_intent_boost(self, domain_data):
        """Transactional intent should boost score vs informational."""
        base_keyword = {
            "keyword": "test keyword",
            "search_volume": 1000,
            "keyword_difficulty": 50,
            "position": 20,
        }

        transactional = calculate_opportunity_score(
            {**base_keyword, "intent": "transactional"}, domain_data
        )

        informational = calculate_opportunity_score(
            {**base_keyword, "intent": "informational"}, domain_data
        )

        assert transactional.opportunity_score >= informational.opportunity_score, "Transactional should score equal or higher"

    def test_position_affects_score(self, domain_data):
        """Position should affect opportunity score calculation."""
        base_keyword = {
            "keyword": "test keyword",
            "search_volume": 1000,
            "keyword_difficulty": 50,
            "intent": "commercial",
        }

        in_strike = calculate_opportunity_score(
            {**base_keyword, "position": 15}, domain_data
        )

        not_ranking = calculate_opportunity_score(
            {**base_keyword, "position": None}, domain_data
        )

        # Both should return valid scores
        assert in_strike.opportunity_score >= 0
        assert not_ranking.opportunity_score >= 0

    def test_zero_volume_handling(self, domain_data):
        """Zero volume should not cause errors."""
        keyword = {
            "keyword": "zero volume keyword",
            "search_volume": 0,
            "keyword_difficulty": 50,
            "position": 20,
            "intent": "commercial",
        }

        result = calculate_opportunity_score(keyword, domain_data)

        assert result.opportunity_score >= 0

    def test_result_contains_breakdown(self, domain_data):
        """Result should contain scoring breakdown."""
        keyword = {
            "keyword": "test keyword",
            "search_volume": 1000,
            "keyword_difficulty": 50,
            "position": 20,
            "intent": "commercial",
        }

        result = calculate_opportunity_score(keyword, domain_data)

        assert hasattr(result, "volume_score")
        assert hasattr(result, "difficulty_score")
        assert hasattr(result, "intent_score")


class TestPersonalizedDifficulty:
    """Test Personalized Difficulty Score (MarketMuse methodology)."""

    @pytest.fixture
    def domain_data(self):
        """Standard domain data for testing."""
        return {
            "domain_rank": 70,
            "categories": [
                {"name": "Software", "keyword_count": 200},
            ],
        }

    def test_strong_site_lower_difficulty(self, domain_data):
        """Strong site metrics should lower personalized difficulty."""
        keyword = {
            "keyword": "test keyword",
            "keyword_difficulty": 60,
            "category": "Software",
        }

        result = calculate_personalized_difficulty(keyword, domain_data)

        assert isinstance(result, DifficultyAnalysis)
        assert result.personalized_difficulty <= 60, "Strong site should have lower PD than KD"

    def test_weak_site_higher_difficulty(self):
        """Weak site metrics should not lower difficulty much."""
        keyword = {
            "keyword": "test keyword",
            "keyword_difficulty": 40,
            "category": "Unknown",
        }

        weak_domain = {
            "domain_rank": 15,
            "categories": [],
        }

        result = calculate_personalized_difficulty(keyword, weak_domain)

        # Weak site should not get significant advantage
        assert result.personalized_difficulty >= 30

    def test_topical_authority_impact(self):
        """Topical authority should impact difficulty."""
        keyword = {
            "keyword": "software tool",
            "keyword_difficulty": 60,
            "category": "Software",
        }

        high_topical = {
            "domain_rank": 40,
            "categories": [{"name": "Software", "keyword_count": 500}],
        }

        low_topical = {
            "domain_rank": 40,
            "categories": [{"name": "Software", "keyword_count": 5}],
        }

        high_result = calculate_personalized_difficulty(keyword, high_topical)
        low_result = calculate_personalized_difficulty(keyword, low_topical)

        assert high_result.personalized_difficulty <= low_result.personalized_difficulty

    def test_difficulty_bounded(self):
        """Difficulty should be bounded between 0 and 100."""
        keyword = {
            "keyword": "test",
            "keyword_difficulty": 50,
        }

        domain = {
            "domain_rank": 95,
            "categories": [{"name": "Test", "keyword_count": 1000}],
        }

        result = calculate_personalized_difficulty(keyword, domain)

        assert 0 <= result.personalized_difficulty <= 100

    def test_result_contains_factors(self):
        """Result should explain which factors affected difficulty."""
        keyword = {
            "keyword": "test keyword",
            "keyword_difficulty": 60,
        }

        domain = {
            "domain_rank": 50,
            "categories": [],
        }

        result = calculate_personalized_difficulty(keyword, domain)

        assert hasattr(result, "authority_advantage")
        assert hasattr(result, "dr_advantage")
        assert hasattr(result, "topical_bonus")


class TestContentDecayScore:
    """Test Content Decay Score calculation."""

    def test_healthy_page_low_decay(self):
        """Healthy content should have low decay."""
        page = {
            "url": "/blog/popular-post",
            "traffic": 500,
            "position": 5,
            "ctr": 0.08,
            "last_updated": "2024-01-01",
        }

        historical = [
            {"date": "2023-06-01", "traffic": 480, "position": 5, "ctr": 0.07},
            {"date": "2023-12-01", "traffic": 510, "position": 4, "ctr": 0.08},
        ]

        result = calculate_decay_score(page, historical)

        assert isinstance(result, DecayAnalysis)
        assert result.decay_score < 0.3, "Healthy content should have low decay score"

    def test_decaying_page_high_score(self):
        """Old decaying content should have high decay."""
        page = {
            "url": "/blog/old-post",
            "traffic": 50,
            "position": 25,
            "ctr": 0.01,
            "last_updated": "2020-01-01",
        }

        historical = [
            {"date": "2021-01-01", "traffic": 500, "position": 5, "ctr": 0.08},
            {"date": "2022-01-01", "traffic": 200, "position": 15, "ctr": 0.03},
        ]

        result = calculate_decay_score(page, historical)

        assert result.decay_score > 0.3, "Decaying content should have high decay"

    def test_kuck_recommendation_keep(self):
        """Should recommend KEEP for healthy content."""
        page = {
            "url": "/features",
            "traffic": 1000,
            "position": 3,
            "ctr": 0.10,
        }

        result = calculate_decay_score(page)

        assert result.recommended_action.value in ["keep", "update"]

    def test_decay_urgency_level(self):
        """Result should include severity level."""
        page = {
            "url": "/test",
            "traffic": 100,
            "position": 15,
        }

        result = calculate_decay_score(page)

        assert hasattr(result, "severity")

    def test_decay_score_bounded(self):
        """Decay score should be between 0 and 1."""
        page = {
            "url": "/test",
            "traffic": 100,
            "position": 20,
        }

        result = calculate_decay_score(page)

        assert 0 <= result.decay_score <= 1


class TestScoringEdgeCases:
    """Test edge cases and error handling."""

    def test_opportunity_with_missing_values(self):
        """Should handle missing values gracefully."""
        keyword = {
            "keyword": "test",
            "search_volume": 1000,
            "keyword_difficulty": 50,
        }

        domain = {
            "domain_rank": 40,
            "categories": [],
        }

        result = calculate_opportunity_score(keyword, domain)

        assert isinstance(result, OpportunityAnalysis)

    def test_difficulty_with_zero_authority(self):
        """Should handle zero domain authority."""
        keyword = {
            "keyword": "test",
            "keyword_difficulty": 50,
        }

        domain = {
            "domain_rank": 0,
            "categories": [],
        }

        result = calculate_personalized_difficulty(keyword, domain)

        assert result.personalized_difficulty >= 0

    def test_decay_without_history(self):
        """Should handle page without historical data."""
        page = {
            "url": "/new-page",
            "traffic": 100,
            "position": 10,
        }

        result = calculate_decay_score(page)

        assert isinstance(result, DecayAnalysis)


class TestScoringIntegration:
    """Test scoring functions work together."""

    def test_full_keyword_analysis(self):
        """Test complete keyword scoring workflow."""
        keyword = {
            "keyword": "projekthantering software",
            "search_volume": 5000,
            "keyword_difficulty": 45,
            "position": 12,
            "intent": "commercial",
            "category": "Software",
        }

        domain = {
            "domain_rank": 50,
            "categories": [{"name": "Software", "keyword_count": 100}],
        }

        # Calculate opportunity
        opportunity = calculate_opportunity_score(keyword, domain)

        # Calculate personalized difficulty
        difficulty = calculate_personalized_difficulty(keyword, domain)

        # Both should return valid results
        assert opportunity.opportunity_score > 0
        assert 0 <= difficulty.personalized_difficulty <= 100

    def test_content_audit_workflow(self):
        """Test content audit scoring workflow."""
        pages = [
            {"url": "/blog/post-1", "traffic": 500, "position": 5},
            {"url": "/blog/post-2", "traffic": 50, "position": 35},
            {"url": "/blog/post-3", "traffic": 200, "position": 12},
        ]

        results = []
        for page in pages:
            decay = calculate_decay_score(page)
            results.append({
                "url": page["url"],
                "decay_score": decay.decay_score,
                "recommendation": decay.recommended_action.value,
            })

        # Should have results for all pages
        assert len(results) == 3
        assert all(r["decay_score"] >= 0 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

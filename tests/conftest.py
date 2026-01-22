"""
Pytest Configuration and Shared Fixtures

Provides common fixtures and configuration for all test modules.
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch


# ============================================================================
# Async Support
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def mock_collected_data() -> Dict[str, Any]:
    """Standard mock collected data for testing."""
    return {
        "metadata": {
            "domain": "example.se",
            "analysis_date": datetime.now().isoformat(),
            "collection_duration": 45.2,
        },
        "summary": {
            "total_organic_keywords": 1247,
            "total_organic_traffic": 8500,
            "domain_rank": 45,
            "competitor_count": 12,
            "has_local_presence": False,
        },
        "phase1_foundation": {
            "domain_overview": {
                "organic_keywords": 1247,
                "organic_traffic": 8500,
                "domain_rank": 45,
            },
            "technologies": [
                {"name": "WordPress"},
                {"name": "WooCommerce"},
            ],
            "technical_baseline": {
                "performance_score": 0.65,
                "accessibility_score": 0.82,
                "best_practices_score": 0.78,
                "seo_score": 0.71,
            },
        },
        "phase2_keywords": {
            "ranked_keywords": [
                {"keyword": "projekthantering", "position": 15, "volume": 2400},
                {"keyword": "projektverktyg", "position": 23, "volume": 1800},
            ],
            "keyword_suggestions": [
                {"keyword": "gratis projekthantering", "volume": 1200, "difficulty": 35},
            ],
        },
        "phase3_competitive": {
            "organic_competitors": [
                {"domain": "competitor1.se", "common_keywords": 450},
                {"domain": "competitor2.se", "common_keywords": 320},
            ],
            "backlink_profile": {
                "referring_domains": 2340,
                "total_backlinks": 12500,
            },
        },
        "phase4_content": {
            "indexed_pages": 450,
            "content_performance": [
                {"url": "/blog/post-1", "traffic": 500, "keywords": 25},
            ],
        },
    }


@pytest.fixture
def mock_local_data(mock_collected_data) -> Dict[str, Any]:
    """Mock data with local business presence."""
    data = dict(mock_collected_data)
    data["summary"] = dict(data["summary"])
    data["summary"]["has_local_presence"] = True
    data["phase1_foundation"] = dict(data["phase1_foundation"])
    data["phase1_foundation"]["gbp_info"] = {
        "name": "Example Business",
        "address": "Stockholm, Sweden",
        "rating": 4.5,
        "reviews": 127,
    }
    return data


@pytest.fixture
def mock_agent_outputs() -> Dict[str, Dict[str, Any]]:
    """Mock outputs from all agents."""
    return {
        "keyword_intelligence": {
            "executive_summary": "23 high-priority keyword opportunities identified.",
            "priority_stack": [
                {
                    "term": "projekthantering software",
                    "volume": 2400,
                    "difficulty": 42,
                    "personalized_difficulty": 35,
                    "opportunity_score": 89,
                    "current_position": 15,
                    "intent": "commercial",
                    "recommended_action": "Create dedicated landing page",
                    "effort": "Medium - 2-3 weeks",
                    "impact": "High - 500+ monthly visits",
                },
            ],
            "quick_wins": [
                {"term": "projekthantering gratis", "position": 11, "action": "Add FAQ"},
            ],
            "total_opportunity_volume": 45000,
        },
        "backlink_intelligence": {
            "executive_summary": "2,340 referring domains vs competitor average of 5,600.",
            "link_gap": {"total_gap": 3260},
            "prospect_tiers": {"tier1": [{"domain": "techblog.se", "dr": 72}]},
        },
        "technical_seo": {
            "executive_summary": "12 critical issues affecting visibility.",
            "critical_issues": [
                {"type": "CWV", "metric": "LCP", "current": "4.2s", "target": "2.5s"},
            ],
            "cwv_scores": {"lcp": 4.2, "fid": 89, "cls": 0.15},
        },
        "content_analysis": {
            "executive_summary": "15 pages for update, 8 for consolidation.",
            "kuck_recommendations": {
                "keep": ["/features"],
                "update": ["/blog/old-post"],
                "consolidate": [],
                "kill": ["/outdated"],
            },
        },
        "semantic_architecture": {
            "executive_summary": "5 hub opportunities identified.",
            "topic_clusters": [
                {"hub": "Project Management", "spokes": ["agile", "scrum"]},
            ],
        },
        "ai_visibility": {
            "executive_summary": "23% of keywords trigger AI Overviews.",
            "geo_score": 45,
        },
        "serp_analysis": {
            "executive_summary": "3 featured snippet opportunities.",
            "serp_features": {"featured_snippets": 3, "paa": 12},
        },
        "master_strategy": {
            "executive_summary": "Technical fixes prioritized, then content.",
            "overall_seo_score": 62,
            "roadmap_90_days": {
                "month1": ["Fix LCP"],
                "month2": ["Create landing pages"],
                "month3": ["Link building"],
            },
        },
    }


# ============================================================================
# Sample XML Outputs
# ============================================================================

@pytest.fixture
def sample_keyword_xml() -> str:
    """Sample XML output from keyword agent."""
    return """
    <analysis>
    <executive_summary>
    23 high-priority keyword opportunities totaling 45,000 monthly searches.
    </executive_summary>
    <priority_stack>
    <keyword priority="1">
    <term>projekthantering software</term>
    <volume>2400</volume>
    <difficulty>42</difficulty>
    <opportunity_score>89</opportunity_score>
    </keyword>
    </priority_stack>
    </analysis>
    """


@pytest.fixture
def sample_technical_xml() -> str:
    """Sample XML output from technical agent."""
    return """
    <technical_analysis>
    <critical_issues>
    <issue severity="critical">
    <type>Core Web Vitals</type>
    <metric>LCP</metric>
    <current_value>4.2s</current_value>
    <target_value>2.5s</target_value>
    </issue>
    </critical_issues>
    </technical_analysis>
    """


# ============================================================================
# Mock API Client
# ============================================================================

@pytest.fixture
def mock_claude_client():
    """Mock Claude API client."""
    client = MagicMock()
    client.complete = AsyncMock(return_value="<analysis>Test response</analysis>")
    client.get_usage_summary = MagicMock(return_value={
        "total_tokens": 10000,
        "estimated_cost": 0.50,
    })
    return client


# ============================================================================
# Quality Check Fixtures
# ============================================================================

@pytest.fixture
def good_quality_output() -> str:
    """Output that passes quality checks."""
    return """
    <analysis>
    <executive_summary>
    Analysis of example.se reveals 23 high-priority keyword opportunities.
    Top opportunity: "projekthantering software" (2,400 vol, KD 42, current #15).
    </executive_summary>
    <priority_stack>
    <keyword priority="1">
    <term>projekthantering software</term>
    <volume>2400</volume>
    <difficulty>42</difficulty>
    <personalized_difficulty>35</personalized_difficulty>
    <opportunity_score>89</opportunity_score>
    <recommended_action>Create dedicated landing page at /projekthantering-software</recommended_action>
    <effort>Medium - 2-3 weeks</effort>
    <impact>High - 500+ monthly visits, €2,400/month value</impact>
    </keyword>
    </priority_stack>
    </analysis>
    """


@pytest.fixture
def poor_quality_output() -> str:
    """Output that fails quality checks."""
    return """
    Based on comprehensive analysis of the website, we recommend:
    - Optimize existing content
    - Build quality backlinks
    - Improve technical SEO
    These improvements will help increase organic traffic.
    """


# ============================================================================
# Scoring Test Fixtures
# ============================================================================

@pytest.fixture
def high_opportunity_keyword() -> Dict[str, Any]:
    """Keyword with high opportunity score."""
    return {
        "term": "projekthantering software",
        "search_volume": 10000,
        "keyword_difficulty": 20,
        "current_position": 15,
        "click_potential": 0.8,
        "search_intent": "transactional",
    }


@pytest.fixture
def low_opportunity_keyword() -> Dict[str, Any]:
    """Keyword with low opportunity score."""
    return {
        "term": "random keyword",
        "search_volume": 50,
        "keyword_difficulty": 90,
        "current_position": 100,
        "click_potential": 0.2,
        "search_intent": "informational",
    }


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )

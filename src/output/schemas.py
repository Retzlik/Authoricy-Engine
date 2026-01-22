"""
Output Schemas for Agent Responses

Defines the expected output structure for each of the 9 specialized agents.
Used for validation and documentation of agent outputs.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


# ============================================================================
# BASE SCHEMA COMPONENTS
# ============================================================================

FINDING_SCHEMA = {
    "title": "str - Specific, data-driven title",
    "description": "str - Detailed explanation with evidence",
    "evidence": "str - Specific data points supporting the finding",
    "impact": "str - Business impact statement",
    "confidence": "float - 0.0-1.0 confidence level",
    "priority": "int - 1 (highest) to 5 (lowest)",
    "category": "str - Finding category",
    "data_sources": "List[str] - Data sources used",
    "metrics": "Dict - Related metrics",
}

RECOMMENDATION_SCHEMA = {
    "action": "str - Specific action to take",
    "rationale": "str - Why this action matters",
    "priority": "int - P1 (critical), P2 (high), P3 (medium)",
    "effort": "str - Low/Medium/High",
    "impact": "str - Low/Medium/High",
    "timeline": "str - Expected timeline (e.g., '2-4 weeks')",
    "dependencies": "List[str] - Prerequisites",
    "success_metrics": "List[str] - How to measure success",
    "owner": "str - Suggested owner/role",
    "confidence": "float - 0.0-1.0 confidence level",
}


# ============================================================================
# KEYWORD INTELLIGENCE AGENT SCHEMA
# ============================================================================

KEYWORD_INTELLIGENCE_SCHEMA = {
    "agent": "keyword_intelligence",
    "description": "Keyword portfolio analysis and opportunity identification",

    "metrics": {
        "keyword_health_score": "float - Overall keyword portfolio health (0-100)",
        "total_ranking_keywords": "int - Total keywords ranking",
        "top_3_keywords": "int - Keywords in positions 1-3",
        "top_10_keywords": "int - Keywords in positions 1-10",
        "top_50_keywords": "int - Keywords in positions 1-50",
        "keyword_gap_count": "int - Keywords competitors rank for but you don't",
        "quick_win_count": "int - High opportunity, low difficulty keywords",
        "estimated_traffic_opportunity": "int - Monthly traffic potential",
    },

    "findings": [
        {
            "type": "portfolio_health",
            "content": {
                "position_distribution": {
                    "top_3": "int",
                    "4_10": "int",
                    "11_20": "int",
                    "21_50": "int",
                    "51_100": "int",
                },
                "intent_distribution": {
                    "transactional": "int",
                    "commercial": "int",
                    "informational": "int",
                    "navigational": "int",
                },
                "trend": "str - improving/stable/declining",
            },
        },
        {
            "type": "competitor_gap",
            "content": {
                "total_gap_keywords": "int",
                "high_value_gaps": "List[keyword objects]",
                "easy_win_gaps": "List[keyword objects]",
            },
        },
    ],

    "recommendations": [
        {
            "type": "quick_win",
            "keywords": [
                {
                    "keyword": "str",
                    "volume": "int",
                    "current_position": "int or None",
                    "personalized_difficulty": "int",
                    "opportunity_score": "int",
                    "recommended_action": "str",
                    "target_url": "str",
                    "expected_traffic": "int",
                }
            ],
        },
        {
            "type": "strategic_target",
            "keywords": "List[keyword objects]",
        },
        {
            "type": "defend",
            "keywords": "List[keyword objects] - Keywords at risk of losing",
        },
    ],
}


# ============================================================================
# BACKLINK INTELLIGENCE AGENT SCHEMA
# ============================================================================

BACKLINK_INTELLIGENCE_SCHEMA = {
    "agent": "backlink_intelligence",
    "description": "Backlink analysis and link building strategy",

    "metrics": {
        "domain_rating": "int - Current DR",
        "total_backlinks": "int - Total backlink count",
        "referring_domains": "int - Unique referring domains",
        "link_velocity": "float - Monthly link acquisition rate",
        "toxic_link_percentage": "float - Percentage of potentially harmful links",
        "competitor_link_gap": "int - Links competitors have that you don't",
        "dofollow_ratio": "float - Percentage of dofollow links",
    },

    "findings": [
        {
            "type": "link_profile_health",
            "content": {
                "dr_trend": "str - improving/stable/declining",
                "anchor_distribution": {
                    "branded": "float - percentage",
                    "exact_match": "float",
                    "partial_match": "float",
                    "generic": "float",
                    "naked_url": "float",
                },
                "link_type_distribution": {
                    "editorial": "float",
                    "guest_post": "float",
                    "directory": "float",
                    "forum": "float",
                    "other": "float",
                },
            },
        },
        {
            "type": "competitor_analysis",
            "content": {
                "dr_comparison": "Dict[competitor -> DR]",
                "link_gap_opportunities": "List[domain objects]",
                "common_linking_domains": "List[domain objects]",
            },
        },
    ],

    "recommendations": [
        {
            "type": "link_building_strategy",
            "strategy": "str - digital_pr/haro/guest_posting/resource_links/etc",
            "target_domains": "List[domain objects with contact info]",
            "expected_dr_gain": "int",
            "timeline": "str",
        },
        {
            "type": "toxic_link_cleanup",
            "domains_to_disavow": "List[domain objects]",
            "priority": "int",
        },
    ],
}


# ============================================================================
# TECHNICAL SEO AGENT SCHEMA
# ============================================================================

TECHNICAL_SEO_SCHEMA = {
    "agent": "technical_seo",
    "description": "Technical SEO audit and Core Web Vitals analysis",

    "metrics": {
        "technical_health_score": "float - Overall technical health (0-100)",
        "lcp_score": "float - Largest Contentful Paint (seconds)",
        "inp_score": "float - Interaction to Next Paint (ms)",
        "cls_score": "float - Cumulative Layout Shift",
        "mobile_usability_score": "float - Mobile-friendliness (0-100)",
        "crawlability_score": "float - How well site can be crawled (0-100)",
        "indexability_score": "float - Percentage of pages indexed",
        "critical_issues_count": "int - Number of critical issues",
    },

    "findings": [
        {
            "type": "core_web_vitals",
            "content": {
                "lcp": {
                    "value": "float",
                    "status": "str - good/needs_improvement/poor",
                    "threshold": "float - 2.5s",
                    "pages_affected": "int",
                },
                "inp": {
                    "value": "float",
                    "status": "str",
                    "threshold": "float - 200ms",
                    "pages_affected": "int",
                },
                "cls": {
                    "value": "float",
                    "status": "str",
                    "threshold": "float - 0.1",
                    "pages_affected": "int",
                },
            },
        },
        {
            "type": "crawl_issues",
            "content": {
                "blocked_resources": "List[url objects]",
                "broken_links": "List[url objects]",
                "redirect_chains": "List[chain objects]",
                "orphan_pages": "List[url objects]",
            },
        },
        {
            "type": "indexation",
            "content": {
                "indexed_pages": "int",
                "non_indexed_pages": "int",
                "reasons_for_non_indexation": "Dict[reason -> count]",
            },
        },
    ],

    "recommendations": [
        {
            "type": "critical_fix",
            "issue": "str - Issue description",
            "affected_urls": "List[str]",
            "fix_instructions": "str - How to fix",
            "expected_impact": "str",
        },
        {
            "type": "performance_optimization",
            "area": "str - LCP/INP/CLS",
            "recommendations": "List[specific actions]",
        },
    ],
}


# ============================================================================
# CONTENT ANALYSIS AGENT SCHEMA
# ============================================================================

CONTENT_ANALYSIS_SCHEMA = {
    "agent": "content_analysis",
    "description": "Content inventory analysis and decay detection",

    "metrics": {
        "total_pages_analyzed": "int",
        "content_health_score": "float - Overall content health (0-100)",
        "pages_needing_refresh": "int",
        "pages_to_consolidate": "int",
        "pages_to_remove": "int",
        "total_decay_traffic_loss": "int - Monthly traffic lost to decay",
        "recovery_potential": "int - Traffic recoverable with updates",
    },

    "findings": [
        {
            "type": "content_inventory",
            "content": {
                "total_pages": "int",
                "by_type": {
                    "blog_posts": "int",
                    "landing_pages": "int",
                    "product_pages": "int",
                    "category_pages": "int",
                    "other": "int",
                },
                "avg_word_count": "int",
                "avg_age_months": "float",
            },
        },
        {
            "type": "decay_analysis",
            "content": {
                "critical_decay": "List[page objects with decay_score > 0.5]",
                "major_decay": "List[page objects with decay_score 0.3-0.5]",
                "light_decay": "List[page objects with decay_score 0.1-0.3]",
            },
        },
        {
            "type": "thin_content",
            "content": {
                "thin_pages": "List[page objects with < 300 words]",
                "duplicate_content": "List[page pairs]",
                "cannibalization": "List[keyword -> competing pages]",
            },
        },
    ],

    "recommendations": [
        {
            "type": "content_action",
            "action": "str - keep/update/consolidate/kill",
            "pages": [
                {
                    "url": "str",
                    "current_traffic": "int",
                    "peak_traffic": "int",
                    "decay_score": "float",
                    "specific_updates": "List[str] - What to update",
                    "merge_target": "str - URL to merge into (if consolidate)",
                }
            ],
        },
        {
            "type": "content_calendar",
            "month": "str",
            "actions": "List[content action objects]",
        },
    ],
}


# ============================================================================
# SEMANTIC ARCHITECTURE AGENT SCHEMA
# ============================================================================

SEMANTIC_ARCHITECTURE_SCHEMA = {
    "agent": "semantic_architecture",
    "description": "Topical authority and site structure analysis",

    "metrics": {
        "topical_authority_score": "float - Overall topical authority (0-100)",
        "topic_clusters_identified": "int",
        "orphan_content_count": "int",
        "internal_link_score": "float - Internal linking health (0-100)",
        "topic_coverage_gaps": "int",
    },

    "findings": [
        {
            "type": "topic_clusters",
            "content": {
                "clusters": [
                    {
                        "topic": "str",
                        "pillar_page": "str - URL or 'missing'",
                        "cluster_pages": "List[url]",
                        "keyword_coverage": "float - percentage",
                        "authority_score": "float",
                        "gaps": "List[subtopic strings]",
                    }
                ],
            },
        },
        {
            "type": "internal_linking",
            "content": {
                "avg_internal_links_per_page": "float",
                "pages_with_no_internal_links": "int",
                "broken_internal_links": "int",
                "recommended_links": "List[source -> target pairs]",
            },
        },
    ],

    "recommendations": [
        {
            "type": "pillar_page",
            "topic": "str",
            "recommended_url": "str",
            "target_keywords": "List[str]",
            "cluster_pages_to_link": "List[str]",
        },
        {
            "type": "internal_link_additions",
            "links": [
                {
                    "source_url": "str",
                    "target_url": "str",
                    "anchor_text": "str",
                    "context": "str - Where in the page to add",
                }
            ],
        },
    ],
}


# ============================================================================
# AI VISIBILITY AGENT SCHEMA
# ============================================================================

AI_VISIBILITY_SCHEMA = {
    "agent": "ai_visibility",
    "description": "AI Overview presence and GEO optimization",

    "metrics": {
        "ai_visibility_score": "float - Overall AI visibility (0-100)",
        "ai_overview_presence": "float - Percentage of keywords with AI overview presence",
        "citation_count": "int - Times cited in AI responses",
        "geo_readiness_score": "float - Readiness for generative engine optimization",
    },

    "findings": [
        {
            "type": "ai_overview_analysis",
            "content": {
                "keywords_with_ai_overview": "int",
                "your_presence_in_overviews": "int",
                "competitor_presence": "Dict[competitor -> count]",
                "citation_sources": "List[source analysis objects]",
            },
        },
        {
            "type": "geo_readiness",
            "content": {
                "structured_data_coverage": "float",
                "faq_presence": "float",
                "entity_recognition": "float",
                "citation_worthiness": "float",
            },
        },
    ],

    "recommendations": [
        {
            "type": "geo_optimization",
            "page": "str - URL",
            "optimizations": [
                {
                    "type": "str - schema/faq/entity/format",
                    "specific_action": "str",
                    "expected_impact": "str",
                }
            ],
        },
        {
            "type": "citation_opportunity",
            "topic": "str",
            "current_cited_source": "str",
            "your_competing_page": "str",
            "gap_to_close": "str - What's missing",
        },
    ],
}


# ============================================================================
# SERP ANALYSIS AGENT SCHEMA
# ============================================================================

SERP_ANALYSIS_SCHEMA = {
    "agent": "serp_analysis",
    "description": "SERP feature and content format analysis",

    "metrics": {
        "serp_feature_opportunity_score": "float - SERP feature opportunity (0-100)",
        "featured_snippet_opportunities": "int",
        "people_also_ask_opportunities": "int",
        "local_pack_opportunities": "int",
        "image_pack_opportunities": "int",
    },

    "findings": [
        {
            "type": "serp_features",
            "content": {
                "feature_distribution": {
                    "featured_snippet": "int - keywords with this feature",
                    "people_also_ask": "int",
                    "local_pack": "int",
                    "image_pack": "int",
                    "video_carousel": "int",
                    "knowledge_panel": "int",
                },
                "your_feature_presence": "Dict[feature -> count]",
            },
        },
        {
            "type": "content_format_analysis",
            "content": {
                "winning_formats": {
                    "keyword_group": "str",
                    "dominant_format": "str - listicle/how-to/comparison/etc",
                    "avg_word_count": "int",
                    "common_elements": "List[str]",
                },
            },
        },
    ],

    "recommendations": [
        {
            "type": "featured_snippet_target",
            "keyword": "str",
            "current_snippet_holder": "str",
            "your_page": "str",
            "optimization_needed": "str - specific format/content changes",
        },
        {
            "type": "content_format_recommendation",
            "keyword_group": "str",
            "recommended_format": "str",
            "required_elements": "List[str]",
            "word_count_target": "int",
        },
    ],
}


# ============================================================================
# LOCAL SEO AGENT SCHEMA (CONDITIONAL)
# ============================================================================

LOCAL_SEO_SCHEMA = {
    "agent": "local_seo",
    "description": "Local SEO analysis (triggered when local signals detected)",
    "conditional": True,
    "trigger": "Business has physical location or serves local area",

    "metrics": {
        "local_visibility_score": "float - Overall local visibility (0-100)",
        "google_business_profile_score": "float - GBP optimization (0-100)",
        "local_pack_presence": "float - Percentage of local keywords in pack",
        "nap_consistency_score": "float - Name/Address/Phone consistency (0-100)",
        "review_score": "float - Average review rating",
        "review_count": "int - Total reviews",
    },

    "findings": [
        {
            "type": "gbp_analysis",
            "content": {
                "profile_completeness": "float",
                "categories": "List[str]",
                "missing_attributes": "List[str]",
                "post_frequency": "str",
                "q_and_a_count": "int",
            },
        },
        {
            "type": "citation_analysis",
            "content": {
                "total_citations": "int",
                "nap_inconsistencies": "List[citation objects]",
                "missing_directories": "List[str]",
            },
        },
    ],

    "recommendations": [
        {
            "type": "gbp_optimization",
            "actions": "List[specific GBP improvements]",
        },
        {
            "type": "citation_building",
            "directories_to_add": "List[directory objects]",
            "citations_to_fix": "List[citation fix objects]",
        },
    ],
}


# ============================================================================
# MASTER STRATEGY AGENT SCHEMA
# ============================================================================

MASTER_STRATEGY_SCHEMA = {
    "agent": "master_strategy",
    "description": "Synthesizes all agent outputs into unified strategy",

    "metrics": {
        "overall_seo_score": "float - Composite SEO health (0-100)",
        "total_opportunity_value": "float - Estimated annual traffic value",
        "critical_issues_count": "int - Issues requiring immediate attention",
        "quick_win_count": "int - Easy opportunities",
        "strategic_initiative_count": "int - Long-term projects",
    },

    "findings": [
        {
            "type": "executive_summary",
            "content": {
                "headline_metric": "str - Single most important finding",
                "current_state": "str - Where you are now",
                "target_state": "str - Where you could be",
                "key_blockers": "List[str] - What's holding you back",
                "key_opportunities": "List[str] - Biggest opportunities",
            },
        },
        {
            "type": "cross_agent_patterns",
            "content": {
                "synergies": "List[str] - Opportunities that reinforce each other",
                "conflicts": "List[str] - Recommendations that conflict (resolved)",
                "dependencies": "List[str] - What must happen first",
            },
        },
    ],

    "recommendations": [
        {
            "type": "priority_stack",
            "items": [
                {
                    "rank": "int - 1-10",
                    "action": "str",
                    "source_agent": "str",
                    "impact": "str - High/Medium/Low",
                    "effort": "str - High/Medium/Low",
                    "timeline": "str",
                    "dependencies": "List[str]",
                    "expected_outcome": "str",
                }
            ],
        },
        {
            "type": "roadmap",
            "phases": [
                {
                    "phase": "str - e.g., 'Month 1-2'",
                    "focus": "str - Main focus area",
                    "actions": "List[action objects]",
                    "expected_results": "str",
                }
            ],
        },
    ],
}


# ============================================================================
# SCHEMA REGISTRY
# ============================================================================

AGENT_SCHEMAS = {
    "keyword_intelligence": KEYWORD_INTELLIGENCE_SCHEMA,
    "backlink_intelligence": BACKLINK_INTELLIGENCE_SCHEMA,
    "technical_seo": TECHNICAL_SEO_SCHEMA,
    "content_analysis": CONTENT_ANALYSIS_SCHEMA,
    "semantic_architecture": SEMANTIC_ARCHITECTURE_SCHEMA,
    "ai_visibility": AI_VISIBILITY_SCHEMA,
    "serp_analysis": SERP_ANALYSIS_SCHEMA,
    "local_seo": LOCAL_SEO_SCHEMA,
    "master_strategy": MASTER_STRATEGY_SCHEMA,
}


def get_schema(agent_name: str) -> Dict[str, Any]:
    """Get schema for a specific agent."""
    return AGENT_SCHEMAS.get(agent_name, {})


def get_all_agent_names() -> List[str]:
    """Get list of all agent names."""
    return list(AGENT_SCHEMAS.keys())


def validate_output(agent_name: str, output: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate agent output against schema.

    Args:
        agent_name: Agent identifier
        output: Output to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    schema = get_schema(agent_name)
    if not schema:
        return False, [f"Unknown agent: {agent_name}"]

    errors = []

    # Check required metrics
    if "metrics" in schema:
        for metric_name in schema["metrics"]:
            if metric_name not in output.get("metrics", {}):
                errors.append(f"Missing metric: {metric_name}")

    # Check for findings
    if not output.get("findings"):
        errors.append("No findings in output")

    # Check for recommendations
    if not output.get("recommendations"):
        errors.append("No recommendations in output")

    return len(errors) == 0, errors

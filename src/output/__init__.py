"""
Output Processing Module

Handles parsing and validation of agent outputs.
"""

from .parser import (
    OutputParser,
    ParseResult,
    ParsedFinding,
    ParsedRecommendation,
)

from .schemas import (
    AGENT_SCHEMAS,
    get_schema,
    get_all_agent_names,
    validate_output,
    FINDING_SCHEMA,
    RECOMMENDATION_SCHEMA,
    KEYWORD_INTELLIGENCE_SCHEMA,
    BACKLINK_INTELLIGENCE_SCHEMA,
    TECHNICAL_SEO_SCHEMA,
    CONTENT_ANALYSIS_SCHEMA,
    SEMANTIC_ARCHITECTURE_SCHEMA,
    AI_VISIBILITY_SCHEMA,
    SERP_ANALYSIS_SCHEMA,
    LOCAL_SEO_SCHEMA,
    MASTER_STRATEGY_SCHEMA,
)

__all__ = [
    # Parser
    "OutputParser",
    "ParseResult",
    "ParsedFinding",
    "ParsedRecommendation",
    # Schemas
    "AGENT_SCHEMAS",
    "get_schema",
    "get_all_agent_names",
    "validate_output",
    "FINDING_SCHEMA",
    "RECOMMENDATION_SCHEMA",
    "KEYWORD_INTELLIGENCE_SCHEMA",
    "BACKLINK_INTELLIGENCE_SCHEMA",
    "TECHNICAL_SEO_SCHEMA",
    "CONTENT_ANALYSIS_SCHEMA",
    "SEMANTIC_ARCHITECTURE_SCHEMA",
    "AI_VISIBILITY_SCHEMA",
    "SERP_ANALYSIS_SCHEMA",
    "LOCAL_SEO_SCHEMA",
    "MASTER_STRATEGY_SCHEMA",
]

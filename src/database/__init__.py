"""
Authoricy Database Layer

Simple tables today, intelligent system tomorrow.

Usage:
    from src.database import (
        # Session management
        init_db, get_db, get_db_context,

        # Models
        Domain, AnalysisRun, Keyword, Competitor,

        # Enums
        CompetitorType, AnalysisStatus, DataQualityLevel,

        # Repository (high-level operations)
        create_analysis_run, store_keywords, store_competitors,

        # Validation
        validate_run_data, DataQualityReport, QualityGate,
    )

    # Initialize database
    init_db()

    # Create a run
    run_id = create_analysis_run("example.com")

    # Store data
    store_keywords(run_id, domain_id, keywords_list)

    # Validate before AI
    report = validate_run_data(collected_data)
    if report.is_sufficient_for_analysis:
        # Proceed with AI agents
        pass
"""

# Models
from .models import (
    Base,
    # Core entities
    Client,
    Domain,
    AnalysisRun,
    APICall,
    # SEO data
    Keyword,
    Competitor,
    Backlink,
    Page,
    TechnicalMetrics,
    # AI & Reports
    AgentOutput,
    Report,
    # History & Trends
    DomainMetricsHistory,
    RankingHistory,
    # Advanced Intelligence Tables
    SERPFeature,
    KeywordGap,
    ReferringDomain,
    ContentCluster,
    AIVisibility,
    LocalRanking,
    SERPCompetitor,
    # Context Intelligence Tables (NEW)
    ContextIntelligence,
    ValidatedCompetitorRecord,
    MarketOpportunityRecord,
    # Enums
    CompetitorType,
    AnalysisStatus,
    DataQualityLevel,
    SearchIntent,
    SERPFeatureType,
    AIVisibilitySource,
    BusinessModelType,
    PrimaryGoalType,
    ValidatedCompetitorType,
)

# Session management
from .session import (
    get_db,
    get_db_context,
    get_db_session,
    init_db,
    check_db_connection,
    get_engine,
    get_db_info,
    get_table_count,
    engine,
    ensure_greenfield_columns_exist,
)

# Validation
from .validation import (
    validate_run_data,
    DataQualityReport,
    ValidationIssue,
    QualityGate,
    default_quality_gate,
    validate_keyword,
    validate_competitor,
    validate_backlink,
)

# Repository (high-level data operations)
from .repository import (
    # Run management
    create_analysis_run,
    update_run_status,
    complete_run,
    fail_run,
    # API logging
    log_api_call,
    # Data storage - Core
    store_keywords,
    store_competitors,
    store_backlinks,
    store_technical_metrics,
    # Data storage - Intelligence (NEW)
    store_serp_features,
    store_keyword_gaps,
    store_referring_domains,
    store_ranking_history,
    store_content_clusters,
    store_ai_visibility,
    store_local_rankings,
    store_serp_competitors,
    # Data storage - Context Intelligence (NEW)
    store_context_intelligence,
    get_context_intelligence,
    # AI outputs
    store_agent_output,
    store_report,
    mark_report_delivered,
    # Retrieval
    get_run_data,
    get_run_stats,
)

# Pipeline integration
from .pipeline import (
    run_analysis_with_db,
    get_quality_summary,
    QUALITY_GATE,
)

__all__ = [
    # Models - Core
    "Base",
    "Client",
    "Domain",
    "AnalysisRun",
    "APICall",
    # Models - SEO Data
    "Keyword",
    "Competitor",
    "Backlink",
    "Page",
    "TechnicalMetrics",
    # Models - AI & Reports
    "AgentOutput",
    "Report",
    # Models - History & Trends
    "DomainMetricsHistory",
    "RankingHistory",
    # Models - Advanced Intelligence
    "SERPFeature",
    "KeywordGap",
    "ReferringDomain",
    "ContentCluster",
    "AIVisibility",
    "LocalRanking",
    "SERPCompetitor",
    # Models - Context Intelligence (NEW)
    "ContextIntelligence",
    "ValidatedCompetitorRecord",
    "MarketOpportunityRecord",
    # Enums
    "CompetitorType",
    "AnalysisStatus",
    "DataQualityLevel",
    "SearchIntent",
    "SERPFeatureType",
    "AIVisibilitySource",
    "BusinessModelType",
    "PrimaryGoalType",
    "ValidatedCompetitorType",
    # Session
    "get_db",
    "get_db_context",
    "get_db_session",
    "init_db",
    "check_db_connection",
    "get_engine",
    "get_db_info",
    "get_table_count",
    "engine",
    "ensure_greenfield_columns_exist",
    # Validation
    "validate_run_data",
    "DataQualityReport",
    "ValidationIssue",
    "QualityGate",
    "default_quality_gate",
    "validate_keyword",
    "validate_competitor",
    "validate_backlink",
    # Repository - Core
    "create_analysis_run",
    "update_run_status",
    "complete_run",
    "fail_run",
    "log_api_call",
    "store_keywords",
    "store_competitors",
    "store_backlinks",
    "store_technical_metrics",
    "store_agent_output",
    "store_report",
    "mark_report_delivered",
    "get_run_data",
    "get_run_stats",
    # Repository - Intelligence (NEW)
    "store_serp_features",
    "store_keyword_gaps",
    "store_referring_domains",
    "store_ranking_history",
    "store_content_clusters",
    "store_ai_visibility",
    "store_local_rankings",
    "store_serp_competitors",
    # Repository - Context Intelligence (NEW)
    "store_context_intelligence",
    "get_context_intelligence",
    # Pipeline
    "run_analysis_with_db",
    "get_quality_summary",
    "QUALITY_GATE",
]

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
    Client,
    Domain,
    AnalysisRun,
    APICall,
    Keyword,
    Competitor,
    Backlink,
    Page,
    TechnicalMetrics,
    AgentOutput,
    Report,
    DomainMetricsHistory,
    # Enums
    CompetitorType,
    AnalysisStatus,
    DataQualityLevel,
    SearchIntent,
)

# Session management
from .session import (
    get_db,
    get_db_context,
    get_db_session,
    init_db,
    check_db_connection,
    get_engine,
    engine,
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
    # Data storage
    store_keywords,
    store_competitors,
    store_backlinks,
    store_technical_metrics,
    # AI outputs
    store_agent_output,
    store_report,
    mark_report_delivered,
    # Retrieval
    get_run_data,
    get_run_stats,
)

__all__ = [
    # Models
    "Base",
    "Client",
    "Domain",
    "AnalysisRun",
    "APICall",
    "Keyword",
    "Competitor",
    "Backlink",
    "Page",
    "TechnicalMetrics",
    "AgentOutput",
    "Report",
    "DomainMetricsHistory",
    # Enums
    "CompetitorType",
    "AnalysisStatus",
    "DataQualityLevel",
    "SearchIntent",
    # Session
    "get_db",
    "get_db_context",
    "get_db_session",
    "init_db",
    "check_db_connection",
    "get_engine",
    "engine",
    # Validation
    "validate_run_data",
    "DataQualityReport",
    "ValidationIssue",
    "QualityGate",
    "default_quality_gate",
    "validate_keyword",
    "validate_competitor",
    "validate_backlink",
    # Repository
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
]

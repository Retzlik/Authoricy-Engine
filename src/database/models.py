"""
SQLAlchemy Models for Authoricy Intelligence System

Design Principles:
1. Store raw API responses (debugging)
2. Normalize critical entities (querying)
3. Track data quality (validation)
4. Enable historical comparison (trends)
5. Store agent outputs (learning)

Simple enough to implement today, structured enough to scale tomorrow.
"""

import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum, Index, CheckConstraint, UniqueConstraint,
    JSON, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import expression

Base = declarative_base()


# =============================================================================
# ENUMS
# =============================================================================

class CompetitorType(enum.Enum):
    """Classification of competitor domains - THIS SOLVES THE FACEBOOK PROBLEM"""
    TRUE_COMPETITOR = "true_competitor"  # Actually competes for customers
    AFFILIATE = "affiliate"               # Links to target, promotes them
    MEDIA = "media"                       # News/media organization
    GOVERNMENT = "government"             # Government/official site
    PLATFORM = "platform"                 # Generic platform (social, e-commerce)
    UNKNOWN = "unknown"                   # Needs classification


class AnalysisStatus(enum.Enum):
    """Status of an analysis run"""
    PENDING = "pending"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DataQualityLevel(enum.Enum):
    """Data quality assessment"""
    EXCELLENT = "excellent"  # 90-100% complete, no issues
    GOOD = "good"            # 70-90% complete, minor issues
    FAIR = "fair"            # 50-70% complete, some issues
    POOR = "poor"            # <50% complete, major issues
    INVALID = "invalid"      # Critical data missing


class SearchIntent(enum.Enum):
    """Search intent classification"""
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"


# =============================================================================
# CORE TABLES
# =============================================================================

class Client(Base):
    """Client accounts - future multi-tenant support"""
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)

    # Settings
    settings = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    domains = relationship("Domain", back_populates="client", cascade="all, delete-orphan")


class Domain(Base):
    """Domains being analyzed"""
    __tablename__ = "domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)

    # Domain identification
    domain = Column(String(255), nullable=False)
    display_name = Column(String(255))

    # Business context (helps AI understand)
    industry = Column(String(100))
    business_type = Column(String(50))  # ecommerce, saas, local, media
    target_market = Column(String(100))  # Sweden, United States
    primary_language = Column(String(50))
    brand_name = Column(String(255))

    # Additional context for AI
    business_description = Column(Text)
    target_audience = Column(Text)
    main_products_services = Column(JSONB, default=[])  # List of strings

    # Tracking
    is_active = Column(Boolean, default=True)
    analysis_count = Column(Integer, default=0)
    first_analyzed_at = Column(DateTime)
    last_analyzed_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="domains")
    analysis_runs = relationship("AnalysisRun", back_populates="domain", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("client_id", "domain", name="uq_client_domain"),
        Index("idx_domain_lookup", "domain"),
    )


class AnalysisRun(Base):
    """Each analysis execution - the central entity"""
    __tablename__ = "analysis_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Status tracking
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    current_phase = Column(String(50))
    progress_percent = Column(Integer, default=0)

    # Configuration
    config = Column(JSONB, default={})

    # Quality assessment
    data_quality = Column(Enum(DataQualityLevel))
    data_quality_score = Column(Float)  # 0-100
    quality_issues = Column(JSONB, default=[])  # List of issues found

    # Cost tracking
    api_calls_count = Column(Integer, default=0)
    api_cost_usd = Column(Float, default=0)
    ai_tokens_used = Column(Integer, default=0)
    ai_cost_usd = Column(Float, default=0)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Error tracking
    error_message = Column(Text)
    errors = Column(JSONB, default=[])
    warnings = Column(JSONB, default=[])

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    domain = relationship("Domain", back_populates="analysis_runs")
    api_calls = relationship("APICall", back_populates="analysis_run", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="analysis_run", cascade="all, delete-orphan")
    competitors = relationship("Competitor", back_populates="analysis_run", cascade="all, delete-orphan")
    backlinks = relationship("Backlink", back_populates="analysis_run", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="analysis_run", cascade="all, delete-orphan")
    agent_outputs = relationship("AgentOutput", back_populates="analysis_run", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="analysis_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_run_domain_time", "domain_id", "created_at"),
        Index("idx_run_status", "status"),
    )


class APICall(Base):
    """Log of every DataForSEO API call - for debugging and cost tracking"""
    __tablename__ = "api_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    # Call details
    endpoint = Column(String(255), nullable=False)
    phase = Column(String(50))  # phase1, phase2, phase3, phase4

    # Request/Response (ENABLES DEBUGGING!)
    request_payload = Column(JSONB)
    response_payload = Column(JSONB)  # Raw response - can always reparse

    # Metadata
    http_status = Column(Integer)
    response_time_ms = Column(Integer)
    cost_usd = Column(Float)

    # Data quality flags
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(JSONB, default=[])
    data_completeness = Column(Float)  # 0-100, how complete is the response

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="api_calls")

    __table_args__ = (
        Index("idx_api_call_endpoint", "analysis_run_id", "endpoint"),
    )


# =============================================================================
# DATA TABLES - Phase 1 & 2: Keywords
# =============================================================================

class Keyword(Base):
    """Keywords - the core of SEO"""
    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Keyword data
    keyword = Column(String(500), nullable=False)
    keyword_normalized = Column(String(500))  # Lowercase, trimmed for dedup

    # Source tracking
    source = Column(String(50))  # ranked, universe, related, suggestion, gap

    # Search metrics (from DataForSEO)
    search_volume = Column(Integer)
    cpc = Column(Float)
    competition = Column(Float)
    competition_level = Column(String(20))  # low, medium, high
    keyword_difficulty = Column(Integer)

    # Ranking data
    current_position = Column(Integer)
    previous_position = Column(Integer)  # From historical data
    position_change = Column(Integer)
    ranking_url = Column(String(2000))

    # Traffic estimates
    estimated_traffic = Column(Integer)
    traffic_cost = Column(Float)

    # Intent classification
    search_intent = Column(Enum(SearchIntent))
    secondary_intents = Column(JSONB, default=[])

    # Our calculated scores
    opportunity_score = Column(Float)  # 0-100
    priority_score = Column(Float)  # 0-100

    # Clustering
    cluster_name = Column(String(255))
    is_cluster_seed = Column(Boolean, default=False)

    # Historical search volume (for trends)
    monthly_searches = Column(JSONB)  # [{year, month, volume}, ...]

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="keywords")

    __table_args__ = (
        Index("idx_keyword_search", "domain_id", "search_volume"),
        Index("idx_keyword_opportunity", "domain_id", "opportunity_score"),
        Index("idx_keyword_position", "domain_id", "current_position"),
        Index("idx_keyword_text", "keyword_normalized"),
    )


# =============================================================================
# DATA TABLES - Phase 3: Competitors
# =============================================================================

class Competitor(Base):
    """Competitors - with proper classification!"""
    __tablename__ = "competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Competitor identification
    competitor_domain = Column(String(255), nullable=False)

    # CLASSIFICATION - THIS SOLVES THE FACEBOOK PROBLEM
    competitor_type = Column(Enum(CompetitorType), default=CompetitorType.UNKNOWN)
    is_verified = Column(Boolean, default=False)  # Human verified
    verification_notes = Column(Text)

    # Why we think this is a competitor
    detection_method = Column(String(50))  # keyword_overlap, serp_competitor, backlink_competitor
    detection_confidence = Column(Float)  # 0-1

    # Relationship metrics
    keyword_overlap_count = Column(Integer)
    keyword_overlap_percent = Column(Float)
    shared_backlinks_count = Column(Integer)

    # Competitor metrics (from domain_rank_overview)
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)
    domain_rating = Column(Float)
    referring_domains = Column(Integer)
    avg_position = Column(Float)

    # Competitive assessment
    threat_level = Column(String(20))  # low, medium, high, critical
    threat_score = Column(Float)  # 0-100

    # Tracking
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="competitors")

    __table_args__ = (
        UniqueConstraint("analysis_run_id", "competitor_domain", name="uq_run_competitor"),
        Index("idx_competitor_type", "domain_id", "competitor_type"),
        Index("idx_competitor_threat", "domain_id", "threat_score"),
    )


# =============================================================================
# DATA TABLES - Phase 3: Backlinks
# =============================================================================

class Backlink(Base):
    """Backlinks - individual link records"""
    __tablename__ = "backlinks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Link data
    source_url = Column(String(2000), nullable=False)
    source_domain = Column(String(255), nullable=False)
    target_url = Column(String(2000))

    # Link attributes
    anchor_text = Column(String(1000))
    anchor_type = Column(String(50))  # exact, partial, branded, naked, generic
    link_type = Column(String(50))  # text, image, redirect
    is_dofollow = Column(Boolean)
    is_sponsored = Column(Boolean)
    is_ugc = Column(Boolean)

    # Source metrics
    source_domain_rating = Column(Float)
    source_page_rating = Column(Float)
    source_traffic = Column(Integer)

    # Quality scoring
    link_quality_score = Column(Float)  # 0-100, our assessment
    spam_score = Column(Float)
    relevance_score = Column(Float)

    # Temporal
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    is_lost = Column(Boolean, default=False)
    lost_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="backlinks")

    __table_args__ = (
        Index("idx_backlink_source", "source_domain"),
        Index("idx_backlink_quality", "domain_id", "link_quality_score"),
    )


# =============================================================================
# DATA TABLES - Pages & Technical
# =============================================================================

class Page(Base):
    """Pages - content inventory"""
    __tablename__ = "pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Page identification
    url = Column(String(2000), nullable=False)
    path = Column(String(1000))

    # Content data
    title = Column(String(500))
    meta_description = Column(String(500))
    h1 = Column(String(500))
    word_count = Column(Integer)

    # Performance
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)
    primary_keyword = Column(String(500))
    primary_keyword_position = Column(Integer)

    # Backlinks
    backlink_count = Column(Integer)
    referring_domains_count = Column(Integer)

    # Content quality assessment
    content_score = Column(Float)
    freshness_score = Column(Float)
    last_modified = Column(DateTime)

    # Content decay (KUCK analysis)
    decay_score = Column(Float)  # Higher = more decayed
    kuck_recommendation = Column(String(20))  # keep, update, consolidate, kill

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="pages")

    __table_args__ = (
        Index("idx_page_traffic", "domain_id", "organic_traffic"),
        Index("idx_page_decay", "domain_id", "decay_score"),
    )


class TechnicalMetrics(Base):
    """Technical metrics - Lighthouse, CWV, etc."""
    __tablename__ = "technical_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Lighthouse scores (0-100)
    performance_score = Column(Float)
    accessibility_score = Column(Float)
    best_practices_score = Column(Float)
    seo_score = Column(Float)

    # Core Web Vitals
    lcp_ms = Column(Integer)  # Largest Contentful Paint
    fid_ms = Column(Integer)  # First Input Delay
    cls = Column(Float)       # Cumulative Layout Shift
    inp_ms = Column(Integer)  # Interaction to Next Paint

    # Overall technical health
    technical_score = Column(Float)  # Our composite score

    # Issues breakdown
    critical_issues = Column(Integer)
    warnings = Column(Integer)
    issues_detail = Column(JSONB)  # Detailed issue list

    # Technologies detected
    technologies = Column(JSONB)  # [{name, category, version}, ...]

    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun")

    __table_args__ = (
        Index("idx_technical_domain", "domain_id", "recorded_at"),
    )


# =============================================================================
# AI AGENT OUTPUTS - For learning and debugging
# =============================================================================

class AgentOutput(Base):
    """AI agent outputs - enables feedback loop and debugging"""
    __tablename__ = "agent_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    # Agent identification
    agent_name = Column(String(100), nullable=False)  # keyword_intelligence, backlink_analysis, etc.
    agent_version = Column(String(50))

    # Input summary (what data did agent receive)
    input_summary = Column(JSONB)  # {keywords_count, competitors_count, ...}
    input_tokens = Column(Integer)

    # Output
    output_raw = Column(Text)  # Raw markdown output
    output_parsed = Column(JSONB)  # Structured/parsed output
    output_tokens = Column(Integer)

    # Quality metrics
    quality_score = Column(Float)  # 0-100, from quality gate
    passed_quality_gate = Column(Boolean)
    quality_issues = Column(JSONB, default=[])

    # Self-reported confidence
    confidence_score = Column(Float)  # Agent's self-assessment

    # Cost
    model_used = Column(String(100))
    cost_usd = Column(Float)
    latency_ms = Column(Integer)

    # User feedback (for learning!)
    user_rating = Column(Integer)  # 1-5
    user_feedback = Column(Text)
    feedback_tags = Column(JSONB, default=[])  # ["too_generic", "missing_data", ...]

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="agent_outputs")

    __table_args__ = (
        Index("idx_agent_output_agent", "agent_name", "created_at"),
        Index("idx_agent_output_quality", "quality_score"),
    )


# =============================================================================
# REPORTS
# =============================================================================

class Report(Base):
    """Generated reports"""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Report type
    report_type = Column(String(50), default="full")  # full, executive, technical

    # Content
    title = Column(String(500))
    executive_summary = Column(Text)
    content = Column(JSONB)  # Structured report content

    # Files
    pdf_path = Column(String(1000))
    pdf_generated_at = Column(DateTime)

    # Quality
    overall_quality_score = Column(Float)

    # Delivery
    delivered_to = Column(String(255))  # Email
    delivered_at = Column(DateTime)
    opened_at = Column(DateTime)

    # Feedback
    user_rating = Column(Integer)  # 1-5
    user_feedback = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="reports")

    __table_args__ = (
        Index("idx_report_domain", "domain_id", "created_at"),
    )


# =============================================================================
# DOMAIN METRICS HISTORY - For trend analysis
# =============================================================================

class DomainMetricsHistory(Base):
    """Historical domain metrics - enables "compare to last month" """
    __tablename__ = "domain_metrics_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"))

    # Core metrics at this point in time
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)
    domain_rating = Column(Float)
    referring_domains = Column(Integer)
    backlinks_total = Column(Integer)

    # Position distribution
    positions_1 = Column(Integer)
    positions_2_3 = Column(Integer)
    positions_4_10 = Column(Integer)
    positions_11_20 = Column(Integer)
    positions_21_50 = Column(Integer)
    positions_51_100 = Column(Integer)

    # Technical scores
    performance_score = Column(Float)
    seo_score = Column(Float)

    # Composite scores
    overall_health_score = Column(Float)

    # When this snapshot was taken
    recorded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_metrics_history", "domain_id", "recorded_at"),
    )

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


class AnalysisMode(enum.Enum):
    """Analysis mode based on domain maturity"""
    STANDARD = "standard"        # Established domain (DR>35, KW>200)
    GREENFIELD = "greenfield"    # New domain (DR<20, KW<50)
    HYBRID = "hybrid"            # Emerging domain (DR 20-35)


class CompetitorPurpose(enum.Enum):
    """Purpose classification for competitors in greenfield analysis"""
    BENCHMARK_PEER = "benchmark_peer"      # Similar size, direct comparison
    KEYWORD_SOURCE = "keyword_source"      # Good for keyword mining
    LINK_SOURCE = "link_source"            # Learn from their backlinks
    CONTENT_MODEL = "content_model"        # Excellent content to learn from
    ASPIRATIONAL = "aspirational"          # Long-term target, market leader


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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Owner (from Supabase Auth)

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
    user = relationship("User", back_populates="domains", foreign_keys=[user_id])
    analysis_runs = relationship("AnalysisRun", back_populates="domain", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("client_id", "domain", name="uq_client_domain"),
        UniqueConstraint("user_id", "domain", name="uq_user_domain"),
        Index("idx_domain_lookup", "domain"),
        Index("idx_domain_user", "user_id"),
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

    # Analysis mode tracking (greenfield support)
    analysis_mode = Column(Enum(AnalysisMode), default=AnalysisMode.STANDARD)
    domain_maturity_at_analysis = Column(String(20))  # greenfield, emerging, established
    domain_rating_at_analysis = Column(Integer)
    organic_keywords_at_analysis = Column(Integer)
    organic_traffic_at_analysis = Column(Integer)

    # Greenfield context (user-provided business context)
    greenfield_context = Column(JSONB, nullable=True)
    """
    {
        "business_name": "CloudInvoice",
        "business_description": "...",
        "primary_offering": "Invoice software",
        "target_market": "United States",
        "industry_vertical": "saas",
        "seed_keywords": ["invoice software", "billing automation", ...],
        "known_competitors": ["freshbooks.com", "zoho.com/invoice", ...]
    }
    """

    # Curation metrics (instrumentation for tracking user curation behavior)
    curation_metrics = Column(JSONB, nullable=True)
    """
    {
        "removals_count": 3,
        "additions_count": 1,
        "purpose_overrides_count": 2,
        "curated_at": "2024-01-15T10:30:00Z",
        "mode": "greenfield"
    }
    """

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
    parent_topic = Column(String(500))  # DataForSEO's semantic parent topic for clustering

    # Historical search volume (for trends)
    monthly_searches = Column(JSONB)  # [{year, month, volume}, ...]

    # Greenfield-specific fields: Winnability scoring
    winnability_score = Column(Float)           # 0-100, likelihood of ranking
    winnability_components = Column(JSONB)      # Breakdown of score factors
    personalized_difficulty = Column(Integer)   # Adjusted KD for this domain

    # Beachhead tracking
    is_beachhead = Column(Boolean, default=False)
    beachhead_priority = Column(Integer)        # 1-10 ranking among beachheads
    beachhead_score = Column(Float)             # Combined winnability + opportunity
    growth_phase = Column(Integer)              # 1=Foundation, 2=Traction, 3=Authority

    # SERP analysis for winnability
    serp_avg_dr = Column(Float)                 # Average DR of top 10
    serp_min_dr = Column(Integer)               # Lowest DR in top 10
    serp_has_low_dr = Column(Boolean)           # Any DR<30 in top 10?
    serp_weak_signals = Column(JSONB)           # ["outdated_content", "thin_content", ...]

    # AI/AEO tracking
    has_ai_overview = Column(Boolean, default=False)
    aio_source_count = Column(Integer)
    aio_optimization_potential = Column(Float)  # 0-100

    # Source tracking for greenfield (which competitor this came from)
    source_competitor = Column(String(255))
    competitor_position = Column(Integer)       # Their position for this keyword

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="keywords")

    __table_args__ = (
        Index("idx_keyword_search", "domain_id", "search_volume"),
        Index("idx_keyword_opportunity", "domain_id", "opportunity_score"),
        Index("idx_keyword_position", "domain_id", "current_position"),
        Index("idx_keyword_text", "keyword_normalized"),
        Index("idx_keyword_parent_topic", "domain_id", "parent_topic"),
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


# =============================================================================
# SERP FEATURES - Track featured snippets, PAA, local packs, etc.
# =============================================================================

class SERPFeatureType(enum.Enum):
    """Types of SERP features"""
    FEATURED_SNIPPET = "featured_snippet"
    PEOPLE_ALSO_ASK = "people_also_ask"
    LOCAL_PACK = "local_pack"
    KNOWLEDGE_PANEL = "knowledge_panel"
    IMAGE_PACK = "image_pack"
    VIDEO_CAROUSEL = "video_carousel"
    TOP_STORIES = "top_stories"
    SHOPPING_RESULTS = "shopping_results"
    SITELINKS = "sitelinks"
    FAQ_SCHEMA = "faq_schema"
    REVIEWS = "reviews"
    AI_OVERVIEW = "ai_overview"  # Google AI Overviews
    DISCUSSION_FORUMS = "discussion_forums"
    RELATED_SEARCHES = "related_searches"


class SERPFeature(Base):
    """SERP features for keywords - know where the opportunities are"""
    __tablename__ = "serp_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey("keywords.id"), nullable=True)

    # Keyword info (denormalized for query performance)
    keyword = Column(String(500), nullable=False)

    # Feature type
    feature_type = Column(Enum(SERPFeatureType), nullable=False)

    # Position in SERP
    position = Column(Integer)  # Where the feature appears

    # Ownership
    owned_by_target = Column(Boolean, default=False)  # Does target domain own this?
    owned_by_domain = Column(String(255))  # Which domain owns it?

    # Feature-specific data
    feature_data = Column(JSONB, default={})  # Snippet text, PAA questions, etc.

    # Opportunity assessment
    can_target = Column(Boolean, default=True)  # Is this feature targetable?
    opportunity_score = Column(Float)  # 0-100, how valuable is this opportunity

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_serp_feature_keyword", "domain_id", "keyword"),
        Index("idx_serp_feature_type", "domain_id", "feature_type"),
        Index("idx_serp_feature_owned", "domain_id", "owned_by_target"),
    )


# =============================================================================
# KEYWORD GAPS - Where competitors rank but you don't
# =============================================================================

class KeywordGap(Base):
    """Keyword gaps - THE core of competitive intelligence"""
    __tablename__ = "keyword_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # The keyword
    keyword = Column(String(500), nullable=False)
    keyword_normalized = Column(String(500))

    # Search metrics
    search_volume = Column(Integer)
    keyword_difficulty = Column(Integer)
    cpc = Column(Float)
    search_intent = Column(Enum(SearchIntent))

    # Gap analysis
    target_position = Column(Integer)  # Your position (null if not ranking)
    target_url = Column(String(2000))  # Your ranking URL if any

    # Competitor positions (JSONB for flexibility)
    competitor_positions = Column(JSONB, default={})  # {domain: position, ...}
    best_competitor = Column(String(255))  # Who ranks best?
    best_competitor_position = Column(Integer)

    # Gap metrics
    competitor_count = Column(Integer)  # How many competitors rank?
    avg_competitor_position = Column(Float)
    position_gap = Column(Integer)  # Difference to best competitor

    # Opportunity scoring
    opportunity_score = Column(Float)  # 0-100
    priority = Column(String(20))  # high, medium, low
    difficulty_adjusted_score = Column(Float)  # Score adjusted for your domain strength

    # Content opportunity
    suggested_content_type = Column(String(50))  # blog, landing_page, product, etc.
    estimated_traffic_potential = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_gap_opportunity", "domain_id", "opportunity_score"),
        Index("idx_gap_priority", "domain_id", "priority"),
        Index("idx_gap_volume", "domain_id", "search_volume"),
    )


# =============================================================================
# REFERRING DOMAINS - Domain-level backlink analysis
# =============================================================================

class ReferringDomain(Base):
    """Referring domains - aggregate backlink source analysis"""
    __tablename__ = "referring_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Source domain
    referring_domain = Column(String(255), nullable=False)

    # Domain metrics
    domain_rating = Column(Float)
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)

    # Link profile from this domain
    backlink_count = Column(Integer)  # Total links from this domain
    dofollow_count = Column(Integer)
    nofollow_count = Column(Integer)

    # Link types
    text_links = Column(Integer)
    image_links = Column(Integer)
    redirect_links = Column(Integer)

    # Target pages
    linked_pages = Column(JSONB, default=[])  # List of pages on your domain they link to
    unique_pages_linked = Column(Integer)

    # Anchor text distribution
    anchor_distribution = Column(JSONB, default={})  # {anchor: count, ...}
    primary_anchor = Column(String(500))

    # Quality assessment
    quality_score = Column(Float)  # 0-100
    spam_score = Column(Float)
    relevance_score = Column(Float)  # How relevant is this domain to your niche

    # Classification
    domain_type = Column(String(50))  # news, blog, directory, forum, etc.
    is_competitor = Column(Boolean, default=False)

    # Temporal
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    is_lost = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("analysis_run_id", "referring_domain", name="uq_run_referring_domain"),
        Index("idx_ref_domain_quality", "domain_id", "quality_score"),
        Index("idx_ref_domain_dr", "domain_id", "domain_rating"),
    )


# =============================================================================
# RANKING HISTORY - Track position changes over time
# =============================================================================

class RankingHistory(Base):
    """Ranking history - track keyword positions over time"""
    __tablename__ = "ranking_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    # Keyword
    keyword = Column(String(500), nullable=False)
    keyword_normalized = Column(String(500))

    # Position data
    position = Column(Integer)
    previous_position = Column(Integer)
    position_change = Column(Integer)  # Positive = improved, Negative = dropped

    # Ranking URL
    ranking_url = Column(String(2000))
    previous_url = Column(String(2000))  # Track URL changes

    # Traffic impact
    estimated_traffic = Column(Integer)
    traffic_change = Column(Integer)

    # SERP volatility
    serp_volatility = Column(Float)  # How much did this SERP change?

    # Snapshot date
    recorded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_ranking_history_keyword", "domain_id", "keyword_normalized", "recorded_at"),
        Index("idx_ranking_history_change", "domain_id", "position_change"),
    )


# =============================================================================
# CONTENT CLUSTERS - Topic clusters and pillar pages
# =============================================================================

class ContentCluster(Base):
    """Content clusters - topical authority mapping"""
    __tablename__ = "content_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Cluster identification
    cluster_name = Column(String(255), nullable=False)
    cluster_slug = Column(String(255))

    # Pillar content
    pillar_keyword = Column(String(500))
    pillar_url = Column(String(2000))  # Existing pillar page if any
    pillar_position = Column(Integer)

    # Cluster metrics
    total_keywords = Column(Integer)
    ranking_keywords = Column(Integer)
    avg_position = Column(Float)
    total_search_volume = Column(Integer)
    total_traffic = Column(Integer)

    # Cluster keywords (JSONB for flexibility)
    keywords = Column(JSONB, default=[])  # [{keyword, volume, position, url}, ...]

    # Content gaps in cluster
    missing_subtopics = Column(JSONB, default=[])  # Keywords in cluster we don't rank for
    content_gap_count = Column(Integer)

    # Competitive assessment
    cluster_difficulty = Column(Float)  # Average difficulty
    top_competitor = Column(String(255))
    competitor_coverage = Column(JSONB, default={})  # {competitor: keyword_count, ...}

    # Authority assessment
    topical_authority_score = Column(Float)  # 0-100, our authority in this topic
    content_completeness = Column(Float)  # 0-100, how complete is our coverage

    # Recommendations
    recommended_content = Column(JSONB, default=[])  # Suggested new content
    priority = Column(String(20))  # high, medium, low

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_cluster_authority", "domain_id", "topical_authority_score"),
        Index("idx_cluster_priority", "domain_id", "priority"),
    )


# =============================================================================
# AI VISIBILITY - Track presence in AI search (GEO)
# =============================================================================

class AIVisibilitySource(enum.Enum):
    """AI search sources"""
    GOOGLE_AI_OVERVIEW = "google_ai_overview"
    CHATGPT = "chatgpt"
    PERPLEXITY = "perplexity"
    CLAUDE = "claude"
    BING_COPILOT = "bing_copilot"
    GOOGLE_SGE = "google_sge"


class AIVisibility(Base):
    """AI visibility tracking - the future of search"""
    __tablename__ = "ai_visibility"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Query/Topic
    query = Column(String(500), nullable=False)
    topic_category = Column(String(100))

    # Source
    ai_source = Column(Enum(AIVisibilitySource), nullable=False)

    # Visibility
    is_mentioned = Column(Boolean, default=False)
    is_cited = Column(Boolean, default=False)  # Actually linked/cited
    is_recommended = Column(Boolean, default=False)  # Recommended as a resource

    # Citation details
    citation_url = Column(String(2000))
    citation_context = Column(Text)  # The text around the citation
    citation_position = Column(Integer)  # Position in the response (1st, 2nd, etc.)

    # Competitor visibility
    competitors_mentioned = Column(JSONB, default=[])  # Other domains mentioned
    total_citations = Column(Integer)  # Total citations in this response

    # Content that got cited
    cited_content_type = Column(String(50))  # blog, product, homepage, etc.
    cited_content_topic = Column(String(255))

    # Quality signals
    sentiment = Column(String(20))  # positive, neutral, negative
    authority_signal = Column(Boolean)  # Was domain presented as authoritative?

    # Timestamps
    checked_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_ai_visibility_source", "domain_id", "ai_source"),
        Index("idx_ai_visibility_mentioned", "domain_id", "is_mentioned"),
    )


# =============================================================================
# LOCAL RANKINGS - Google Business Profile and local pack
# =============================================================================

class LocalRanking(Base):
    """Local rankings - for businesses with physical presence"""
    __tablename__ = "local_rankings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Location
    location_name = Column(String(255))  # Business location name
    address = Column(String(500))
    city = Column(String(100))
    region = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)

    # Google Business Profile
    gbp_name = Column(String(255))
    gbp_category = Column(String(100))
    gbp_rating = Column(Float)
    gbp_review_count = Column(Integer)
    gbp_url = Column(String(2000))

    # Local keyword
    keyword = Column(String(500), nullable=False)
    search_volume = Column(Integer)

    # Rankings
    local_pack_position = Column(Integer)  # Position in local 3-pack (1-3, null if not in pack)
    organic_position = Column(Integer)  # Organic position for same keyword
    maps_position = Column(Integer)  # Position in Google Maps results

    # Competitor local pack
    local_pack_competitors = Column(JSONB, default=[])  # [{name, position, rating, reviews}, ...]

    # Local signals
    distance_from_centroid = Column(Float)  # Distance from search location centroid
    prominence_score = Column(Float)  # Google's prominence calculation estimate

    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_local_ranking_keyword", "domain_id", "keyword"),
        Index("idx_local_ranking_position", "domain_id", "local_pack_position"),
    )


# =============================================================================
# SERP COMPETITORS - Per-keyword competitors (different from domain competitors)
# =============================================================================

class SERPCompetitor(Base):
    """SERP competitors - who you're actually competing against per keyword"""
    __tablename__ = "serp_competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey("keywords.id"), nullable=True)

    # Keyword
    keyword = Column(String(500), nullable=False)

    # Competitor
    competitor_domain = Column(String(255), nullable=False)
    competitor_url = Column(String(2000))

    # Position data
    position = Column(Integer, nullable=False)

    # Page metrics
    page_title = Column(String(500))
    page_backlinks = Column(Integer)
    page_referring_domains = Column(Integer)
    page_domain_rating = Column(Float)

    # Content analysis
    content_type = Column(String(50))  # blog, product, category, homepage
    word_count = Column(Integer)
    has_schema = Column(Boolean)
    schema_types = Column(JSONB, default=[])  # Types of schema markup

    # SERP features owned by this competitor
    serp_features_owned = Column(JSONB, default=[])  # [featured_snippet, paa, etc.]

    # Competitive gap
    is_beatable = Column(Boolean)  # Our assessment if we can outrank
    difficulty_to_outrank = Column(Float)  # 0-100

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_serp_competitor_keyword", "domain_id", "keyword"),
        Index("idx_serp_competitor_domain", "domain_id", "competitor_domain"),
    )


# =============================================================================
# CONTEXT INTELLIGENCE - Pre-collection business understanding
# =============================================================================

class BusinessModelType(enum.Enum):
    """Business model classification"""
    B2B_SAAS = "b2b_saas"
    B2B_SERVICE = "b2b_service"
    B2C_ECOMMERCE = "b2c_ecommerce"
    B2C_SUBSCRIPTION = "b2c_subscription"
    MARKETPLACE = "marketplace"
    PUBLISHER = "publisher"
    LOCAL_SERVICE = "local_service"
    NONPROFIT = "nonprofit"
    UNKNOWN = "unknown"


class PrimaryGoalType(enum.Enum):
    """User's primary SEO goal"""
    TRAFFIC = "traffic"
    LEADS = "leads"
    AUTHORITY = "authority"
    BALANCED = "balanced"


class ValidatedCompetitorType(enum.Enum):
    """Validated competitor classification"""
    DIRECT = "direct"
    SEO = "seo"
    CONTENT = "content"
    EMERGING = "emerging"
    ASPIRATIONAL = "aspirational"
    NOT_COMPETITOR = "not_competitor"


class ContextIntelligence(Base):
    """
    Context Intelligence results - stored for reuse and learning.

    This is the output of the Context Intelligence phase that runs
    BEFORE data collection to understand the business.
    """
    __tablename__ = "context_intelligence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=True)

    # User inputs
    declared_market = Column(String(50))
    declared_language = Column(String(10))
    declared_goal = Column(Enum(PrimaryGoalType))
    user_provided_competitors = Column(JSONB, default=[])

    # Resolved market (Phase 2 - single source of truth)
    resolved_market_code = Column(String(10))  # "uk", "us", "se", etc.
    resolved_market_name = Column(String(100))  # "United Kingdom", "United States", etc.
    resolved_location_code = Column(Integer)  # DataForSEO location_code (2826 for UK)
    resolved_language_code = Column(String(10))  # "en", "sv", etc.
    resolved_language_name = Column(String(50))  # "English", "Swedish", etc.
    resolved_market_source = Column(String(30))  # "user_provided", "auto_detected", "default"
    resolved_market_confidence = Column(String(20))  # "high", "medium", "low", "conflict"
    resolved_detection_confidence = Column(Float)  # 0-1, original detection confidence
    resolved_has_conflict = Column(Boolean, default=False)  # User vs detection conflict
    resolved_conflict_details = Column(Text)  # Explanation of conflict

    # Website analysis results
    detected_business_model = Column(Enum(BusinessModelType))
    detected_company_stage = Column(String(50))
    detected_languages = Column(JSONB, default=[])
    detected_offerings = Column(JSONB, default=[])  # [{name, type, pricing_model}, ...]
    value_proposition = Column(Text)
    target_audience = Column(JSONB, default={})

    # Site features detected
    has_blog = Column(Boolean, default=False)
    has_pricing_page = Column(Boolean, default=False)
    has_demo_form = Column(Boolean, default=False)
    has_contact_form = Column(Boolean, default=False)
    has_ecommerce = Column(Boolean, default=False)
    content_maturity = Column(String(50))
    technical_sophistication = Column(String(50))

    # Goal validation
    goal_fits_business = Column(Boolean, default=True)
    goal_validation_confidence = Column(Float)
    suggested_goal = Column(Enum(PrimaryGoalType), nullable=True)
    goal_suggestion_reason = Column(Text)

    # Market validation
    primary_market_validated = Column(Boolean, default=True)
    market_validation_notes = Column(Text)
    discovered_markets = Column(JSONB, default=[])  # [{region, language, opportunity_score, ...}, ...]
    should_expand_markets = Column(Boolean, default=False)
    suggested_markets = Column(JSONB, default=[])
    # Additional market validation fields
    should_adjust_market = Column(Boolean, default=False)  # Should adjust primary market
    suggested_market = Column(String(50), nullable=True)  # Suggested primary market
    language_mismatch = Column(Boolean, default=False)  # Site vs declared language mismatch

    # Competitor validation
    validated_competitors = Column(JSONB, default=[])  # [{domain, type, threat_level, ...}, ...]
    discovered_competitors = Column(JSONB, default=[])
    rejected_competitors = Column(JSONB, default=[])  # Domains incorrectly suggested
    # Competitor counts for quick access
    direct_competitors_count = Column(Integer, default=0)
    seo_competitors_count = Column(Integer, default=0)
    emerging_threats_count = Column(Integer, default=0)

    # Business context synthesis
    buyer_journey_type = Column(String(50))
    buyer_journey_stages = Column(JSONB, default=[])
    success_definition = Column(JSONB, default={})  # {10x, realistic, minimum, metrics}
    recommended_focus_areas = Column(JSONB, default=[])
    seo_fit = Column(String(50))
    quick_wins_potential = Column(String(50))

    # Collection configuration generated
    collection_config = Column(JSONB, default={})  # The IntelligentCollectionConfig

    # Quality metrics
    overall_confidence = Column(Float)
    website_analysis_confidence = Column(Float)
    context_confidence = Column(Float)  # Business context confidence
    execution_time_seconds = Column(Float)
    errors = Column(JSONB, default=[])
    warnings = Column(JSONB, default=[])

    # Validation by user (for learning)
    user_validated = Column(Boolean, default=False)
    user_corrections = Column(JSONB, default={})  # What the user corrected

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_context_domain", "domain_id", "created_at"),
        Index("idx_context_goal", "domain_id", "declared_goal"),
    )


class ValidatedCompetitorRecord(Base):
    """
    Validated competitor relationships.

    Stores the validated and classified competitor relationships
    discovered by Context Intelligence for a domain.
    """
    __tablename__ = "validated_competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    context_intelligence_id = Column(UUID(as_uuid=True), ForeignKey("context_intelligence.id"), nullable=True)

    # Competitor identification
    competitor_domain = Column(String(255), nullable=False)
    competitor_name = Column(String(255))

    # Classification
    competitor_type = Column(Enum(ValidatedCompetitorType), nullable=False)
    threat_level = Column(String(20))  # critical, high, medium, low, none

    # Discovery
    discovery_method = Column(String(50))  # user_provided, serp_analysis, dataforseo_suggested
    user_provided = Column(Boolean, default=False)

    # Validation
    validation_status = Column(String(50))  # confirmed, reclassified, rejected
    validation_notes = Column(Text)

    # Evidence
    keyword_overlap_percentage = Column(Float)
    traffic_ratio = Column(Float)
    business_similarity_score = Column(Float)

    # Analysis insights
    strengths = Column(JSONB, default=[])
    weaknesses = Column(JSONB, default=[])

    # Metrics (populated during collection)
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)
    domain_rating = Column(Float)
    traffic_trend = Column(String(20))

    # Confidence
    confidence_score = Column(Float)

    # Status
    is_active = Column(Boolean, default=True)
    user_validated = Column(Boolean, default=False)

    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("domain_id", "competitor_domain", name="uq_domain_competitor"),
        Index("idx_validated_competitor_type", "domain_id", "competitor_type"),
        Index("idx_validated_competitor_threat", "domain_id", "threat_level"),
    )


class MarketOpportunityRecord(Base):
    """
    Discovered market opportunities.

    Stores market/region opportunities discovered by Context Intelligence.
    """
    __tablename__ = "market_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    context_intelligence_id = Column(UUID(as_uuid=True), ForeignKey("context_intelligence.id"), nullable=True)

    # Market identification
    region = Column(String(100), nullable=False)
    language = Column(String(50), nullable=False)
    region_name = Column(String(255))

    # Opportunity assessment
    opportunity_score = Column(Float)  # 0-100
    competition_level = Column(String(20))  # low, medium, high, very_high
    search_volume_potential = Column(Integer)
    keyword_count_estimate = Column(Integer)

    # Competitive landscape
    top_competitors_in_market = Column(JSONB, default=[])
    our_current_visibility = Column(Float)

    # Status
    is_primary = Column(Boolean, default=False)
    is_recommended = Column(Boolean, default=False)
    priority_rank = Column(Integer)
    recommendation_reason = Column(Text)

    # Discovery
    discovery_method = Column(String(50))

    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("domain_id", "region", "language", name="uq_domain_market"),
        Index("idx_market_opportunity_score", "domain_id", "opportunity_score"),
        Index("idx_market_recommended", "domain_id", "is_recommended"),
    )


# =============================================================================
# STRATEGY BUILDER - User-driven content strategy creation
# =============================================================================

class StrategyStatus(enum.Enum):
    """Strategy status"""
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ThreadStatus(enum.Enum):
    """Thread status"""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class TopicStatus(enum.Enum):
    """Topic status"""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PRODUCTION = "in_production"
    PUBLISHED = "published"


class ContentType(enum.Enum):
    """Content type for topics"""
    PILLAR = "pillar"
    CLUSTER = "cluster"
    SUPPORTING = "supporting"


class Strategy(Base):
    """
    Content strategy container.

    A strategy is bound to a specific analysis_run_id and contains
    threads (topic clusters), topics (content pieces), and keyword assignments.
    """
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="RESTRICT"), nullable=False)

    # Identity
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Versioning (for optimistic locking)
    version = Column(Integer, nullable=False, default=1)

    # Status
    status = Column(Enum(StrategyStatus), nullable=False, default=StrategyStatus.DRAFT)
    approved_at = Column(DateTime)
    approved_by = Column(String(255))

    # Soft delete
    is_archived = Column(Boolean, nullable=False, default=False)
    archived_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    domain = relationship("Domain")
    analysis_run = relationship("AnalysisRun")
    threads = relationship("StrategyThread", back_populates="strategy", cascade="all, delete-orphan")
    exports = relationship("StrategyExport", back_populates="strategy", cascade="all, delete-orphan")
    activity_log = relationship("StrategyActivityLog", back_populates="strategy", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_strategy_domain", "domain_id", "created_at"),
        Index("idx_strategy_status", "domain_id", "status"),
    )


class StrategyThread(Base):
    """
    Thread (topic cluster) within a strategy.

    Represents a market position to own. Contains topics and has keywords assigned.
    Uses lexicographic ordering for efficient drag & drop reordering.
    """
    __tablename__ = "strategy_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)

    # Identity
    name = Column(String(255), nullable=False)
    slug = Column(String(255))

    # Ordering (lexicographic for efficient reordering)
    # Uses fractional indexing: "a", "b", "c" or "aU", "am", "b" between items
    position = Column(String(50), nullable=False)

    # Versioning
    version = Column(Integer, nullable=False, default=1)

    # Status
    status = Column(Enum(ThreadStatus), nullable=False, default=ThreadStatus.DRAFT)
    priority = Column(Integer, CheckConstraint("priority BETWEEN 1 AND 5"))

    # SERP-derived recommendations (cached, read-only)
    recommended_format = Column(String(50))
    format_confidence = Column(Float)
    format_evidence = Column(JSONB)

    # Custom instructions (structured JSONB)
    # Schema: {strategic_context, differentiation_points[], competitors_to_address[],
    #          content_angle, format_recommendations, target_audience, additional_notes}
    custom_instructions = Column(JSONB, nullable=False, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    strategy = relationship("Strategy", back_populates="threads")
    topics = relationship("StrategyTopic", back_populates="thread", cascade="all, delete-orphan")
    thread_keywords = relationship("ThreadKeyword", back_populates="thread", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_thread_strategy", "strategy_id", "position"),
        UniqueConstraint("strategy_id", "position", name="uq_thread_position"),
    )


class ThreadKeyword(Base):
    """
    Junction table for thread-keyword many-to-many relationship.

    A keyword can only be assigned to one thread per strategy (enforced by trigger).
    Uses lexicographic ordering for display order within thread.
    """
    __tablename__ = "thread_keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("strategy_threads.id", ondelete="CASCADE"), nullable=False)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False)

    # Ordering within thread (lexicographic)
    position = Column(String(50), nullable=False)

    # When assigned
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    thread = relationship("StrategyThread", back_populates="thread_keywords")
    keyword = relationship("Keyword")

    __table_args__ = (
        UniqueConstraint("thread_id", "keyword_id", name="uq_thread_keyword"),
        Index("idx_thread_keyword_thread", "thread_id", "position"),
        Index("idx_thread_keyword_keyword", "keyword_id"),
    )


class StrategyTopic(Base):
    """
    Topic (content piece) within a thread.

    Represents a specific piece of content to create.
    Format recommendations belong in Thread.custom_instructions, not here.
    """
    __tablename__ = "strategy_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("strategy_threads.id", ondelete="CASCADE"), nullable=False)

    # Identity
    name = Column(String(500), nullable=False)
    slug = Column(String(255))

    # Ordering (lexicographic)
    position = Column(String(50), nullable=False)

    # Versioning
    version = Column(Integer, nullable=False, default=1)

    # Primary keyword (optional)
    primary_keyword_id = Column(UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="SET NULL"))
    primary_keyword = Column(String(500))  # Denormalized for display

    # Content type
    content_type = Column(Enum(ContentType), nullable=False, default=ContentType.CLUSTER)

    # Status
    status = Column(Enum(TopicStatus), nullable=False, default=TopicStatus.DRAFT)

    # URLs
    target_url = Column(String(2000))
    existing_url = Column(String(2000))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    thread = relationship("StrategyThread", back_populates="topics")
    primary_keyword_rel = relationship("Keyword")

    __table_args__ = (
        Index("idx_topic_thread", "thread_id", "position"),
        UniqueConstraint("thread_id", "position", name="uq_topic_position"),
    )


class StrategyExport(Base):
    """
    Export history for strategies.

    Tracks all exports with a snapshot of what was exported for audit trail.
    """
    __tablename__ = "strategy_exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)

    # Export details
    format = Column(String(20), nullable=False)  # monok_json, monok_display, csv

    # Snapshot of what was exported (for audit trail)
    exported_data = Column(JSONB, nullable=False)

    # Metadata
    exported_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    exported_by = Column(String(255))

    # File storage (if applicable)
    file_path = Column(String(1000))
    file_size_bytes = Column(Integer)

    # Summary stats at export time
    thread_count = Column(Integer)
    topic_count = Column(Integer)
    keyword_count = Column(Integer)

    # Relationships
    strategy = relationship("Strategy", back_populates="exports")

    __table_args__ = (
        Index("idx_export_strategy", "strategy_id", "exported_at"),
    )


class StrategyActivityLog(Base):
    """
    Activity log for strategies.

    Tracks all changes for audit trail (not for undo/redo).
    """
    __tablename__ = "strategy_activity_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)

    # What happened
    action = Column(String(50), nullable=False)  # created, updated, thread_added, keyword_assigned, exported, etc.
    entity_type = Column(String(30))  # strategy, thread, topic, keyword
    entity_id = Column(UUID(as_uuid=True))

    # Who did it
    user_id = Column(String(255))

    # Details
    details = Column(JSONB)

    # When
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    strategy = relationship("Strategy", back_populates="activity_log")

    __table_args__ = (
        Index("idx_activity_strategy", "strategy_id", "created_at"),
    )


# =============================================================================
# GREENFIELD INTELLIGENCE - Competitor-first analysis for new domains
# =============================================================================

class GreenfieldAnalysis(Base):
    """
    Greenfield-specific analysis results.

    Stores market opportunity sizing, beachhead summary, and growth projections
    for domains analyzed in greenfield mode.
    """
    __tablename__ = "greenfield_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Market Opportunity (TAM/SAM/SOM)
    total_addressable_market = Column(Integer)      # Total search volume in universe
    serviceable_addressable_market = Column(Integer)  # Business-relevant keywords volume
    serviceable_obtainable_market = Column(Integer)   # Winnable keywords volume
    tam_keyword_count = Column(Integer)
    sam_keyword_count = Column(Integer)
    som_keyword_count = Column(Integer)

    market_opportunity_score = Column(Float)        # 0-100
    competition_intensity = Column(Float)           # 0-100

    # Competitor Landscape
    competitor_count = Column(Integer)
    avg_competitor_dr = Column(Float)
    competitor_dr_range = Column(JSONB)             # {"min": 15, "max": 65}
    competitor_traffic_share = Column(JSONB)        # [{domain, traffic, share_percent}, ...]

    # Beachhead Summary
    beachhead_keyword_count = Column(Integer)
    total_beachhead_volume = Column(Integer)
    avg_beachhead_winnability = Column(Float)
    beachhead_keywords = Column(JSONB)              # Top 20 beachhead keywords

    # Traffic Projections (3 scenarios)
    projection_conservative = Column(JSONB)
    projection_expected = Column(JSONB)
    projection_aggressive = Column(JSONB)
    """
    {
        "month_3": 50,
        "month_6": 500,
        "month_12": 2500,
        "month_18": 8000,
        "month_24": 15000,
        "confidence": 0.75
    }
    """

    # Growth Roadmap
    growth_roadmap = Column(JSONB)
    """
    [
        {"phase": "Foundation", "months": "1-3", "focus": "Beachheads", "target_keywords": 10},
        {"phase": "Traction", "months": "4-6", "focus": "Expansion", "target_keywords": 25},
        {"phase": "Authority", "months": "7-12", "focus": "Competitive", "target_keywords": 50}
    ]
    """

    # Validation
    data_completeness_score = Column(Float)
    validation_warnings = Column(JSONB, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun")
    domain = relationship("Domain")

    __table_args__ = (
        Index("idx_greenfield_analysis_run", "analysis_run_id"),
        Index("idx_greenfield_domain", "domain_id", "created_at"),
    )


class CompetitorIntelligenceSession(Base):
    """
    Competitor intelligence discovery and curation session.

    Tracks the multi-phase competitor discovery process:
    1. Context acquisition (website scraping)
    2. AI-powered discovery (Perplexity)
    3. Candidate generation
    4. User curation (remove 5 from 15)
    5. Final competitor set with purpose classification
    """
    __tablename__ = "competitor_intelligence_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Session status
    status = Column(String(30), default="pending")
    # pending, discovering, awaiting_curation, curated, completed, failed

    # Phase 1: Context Acquisition
    website_context = Column(JSONB)                 # Scraped website data (via Firecrawl)
    business_description = Column(Text)
    detected_offerings = Column(JSONB, default=[])
    detected_industry = Column(String(100))

    # Phase 2: AI-Powered Discovery
    perplexity_query = Column(Text)
    perplexity_response = Column(JSONB)
    ai_discovered_competitors = Column(JSONB, default=[])

    # Phase 3: Multi-Source Aggregation
    serp_discovered_competitors = Column(JSONB, default=[])
    traffic_share_competitors = Column(JSONB, default=[])
    user_provided_competitors = Column(JSONB, default=[])

    # Candidate pool (15+ before curation)
    candidate_competitors = Column(JSONB, default=[])
    """
    [
        {
            "domain": "competitor.com",
            "discovery_source": "perplexity|serp|traffic_share|user_provided",
            "domain_rating": 45,
            "organic_traffic": 50000,
            "organic_keywords": 2500,
            "relevance_score": 0.85,
            "suggested_purpose": "keyword_source",
            "discovery_reason": "Ranks for 15 of your seed keywords"
        }
    ]
    """
    candidates_generated_at = Column(DateTime)

    # Phase 4: User Curation
    curation_started_at = Column(DateTime)
    curation_completed_at = Column(DateTime)
    removed_competitors = Column(JSONB, default=[])
    """
    [
        {
            "domain": "removed.com",
            "removal_reason": "not_relevant|too_large|too_small|different_market|other",
            "removal_note": "User comment"
        }
    ]
    """
    added_competitors = Column(JSONB, default=[])   # User-added during curation

    # Phase 5: Final Set with Purpose
    final_competitors = Column(JSONB, default=[])
    """
    [
        {
            "domain": "competitor.com",
            "purpose": "benchmark_peer|keyword_source|link_source|content_model|aspirational",
            "priority": 1,
            "domain_rating": 45,
            "organic_traffic": 50000,
            "keyword_overlap": 234,
            "is_user_provided": false,
            "is_user_curated": true
        }
    ]
    """
    finalized_at = Column(DateTime)

    # Cost tracking
    api_calls_count = Column(Integer, default=0)
    perplexity_cost_usd = Column(Float, default=0)
    firecrawl_cost_usd = Column(Float, default=0)
    dataforseo_cost_usd = Column(Float, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    analysis_run = relationship("AnalysisRun")
    domain = relationship("Domain")
    competitors = relationship("GreenfieldCompetitor", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ci_session_analysis", "analysis_run_id"),
        Index("idx_ci_session_domain", "domain_id"),
        Index("idx_ci_session_status", "status"),
    )


class GreenfieldCompetitor(Base):
    """
    Competitors discovered/validated for greenfield analysis.

    Individual competitor records with purpose classification and
    metrics for use in the greenfield pipeline.
    """
    __tablename__ = "greenfield_competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("competitor_intelligence_sessions.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    # Competitor identification
    domain = Column(String(255), nullable=False)
    display_name = Column(String(255))

    # Classification
    purpose = Column(Enum(CompetitorPurpose), nullable=False)
    purpose_override = Column(Enum(CompetitorPurpose), nullable=True)  # User override
    priority = Column(Integer)                      # 1-10

    # Discovery
    discovery_source = Column(String(50))           # perplexity, serp, traffic_share, user_provided
    discovery_reason = Column(Text)
    relevance_score = Column(Float)                 # 0-1

    # Metrics (from DataForSEO)
    domain_rating = Column(Integer)
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)
    referring_domains = Column(Integer)

    # Relationship to target domain
    keyword_overlap_count = Column(Integer)
    keyword_overlap_percent = Column(Float)
    traffic_share_percent = Column(Float)

    # Validation
    is_validated = Column(Boolean, default=False)
    validation_status = Column(String(30))          # valid, warning, replaced
    validation_warnings = Column(JSONB, default=[])

    # Curation tracking
    is_user_provided = Column(Boolean, default=False)
    is_removed = Column(Boolean, default=False)
    removal_reason = Column(String(50))
    removal_note = Column(Text)

    # Usage in analysis
    keywords_extracted = Column(Integer, default=0)
    used_for_market_sizing = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship("CompetitorIntelligenceSession", back_populates="competitors")

    __table_args__ = (
        UniqueConstraint("session_id", "domain", name="uq_session_competitor"),
        Index("idx_gf_competitor_session", "session_id"),
        Index("idx_gf_competitor_purpose", "session_id", "purpose"),
        Index("idx_gf_competitor_removed", "session_id", "is_removed"),
    )


# =============================================================================
# PRECOMPUTED DASHBOARD DATA - Caching layer for fast dashboard loads
# =============================================================================

class PrecomputedDashboard(Base):
    """
    Precomputed dashboard data for instant retrieval.

    This table stores the results of expensive dashboard aggregations
    computed after each analysis completion. Instead of computing these
    on every dashboard load (slow), we compute once and retrieve instantly.

    Data types stored:
    - overview: Health scores, position distribution, quick stats
    - sparklines: 30-day position trends for all keywords
    - sov: Share of Voice calculations
    - battleground: Attack/Defend keyword classifications
    - clusters: Topical authority analysis
    - content_audit: KUCK recommendations
    - opportunities: Ranked opportunity list
    - bundle: All-in-one dashboard bundle
    """
    __tablename__ = "precomputed_dashboard"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    # Data type identifier
    data_type = Column(String(50), nullable=False)  # overview, sparklines, sov, etc.

    # The precomputed data (JSONB for efficient storage and querying)
    data = Column(JSONB, nullable=False)

    # Metadata
    version = Column(Integer, default=1)  # For cache busting
    size_bytes = Column(Integer)  # Size of the JSON data
    computation_time_ms = Column(Integer)  # How long it took to compute

    # Validity
    valid_until = Column(DateTime)  # When this cache expires
    is_current = Column(Boolean, default=True)  # Is this the latest version?

    # ETag for HTTP caching
    etag = Column(String(64))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    domain = relationship("Domain")
    analysis_run = relationship("AnalysisRun")

    __table_args__ = (
        # Unique constraint: one record per analysis + data_type
        UniqueConstraint("analysis_run_id", "data_type", name="uq_precomputed_analysis_type"),
        # Fast lookup by domain and data type
        Index("idx_precomputed_domain_type", "domain_id", "data_type", "is_current"),
        # Fast lookup by analysis
        Index("idx_precomputed_analysis", "analysis_run_id"),
    )



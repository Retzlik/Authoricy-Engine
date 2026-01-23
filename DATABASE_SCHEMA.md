# Authoricy Engine - Database Schema Design

## Vision

This schema is designed to be the foundation of an **AI-first SEO intelligence platform** that:
1. Learns from every analysis to improve future ones
2. Builds cross-client industry benchmarks
3. Enables predictive SEO capabilities
4. Tracks AI agent performance and accuracy
5. Creates feedback loops for continuous improvement

---

## Core Principles

1. **Data Lineage**: Track where every piece of data came from
2. **Temporal Awareness**: Everything is time-series (track changes over time)
3. **AI-Ready**: Structure data for machine learning, not just reporting
4. **Multi-Tenant**: Built for SaaS from day one
5. **Quality First**: Validate and score data quality before analysis

---

## Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TENANT LAYER                                    │
│  organizations → users → api_keys → billing                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOMAIN LAYER                                    │
│  domains → domain_snapshots → domain_health_scores                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAW DATA LAYER                                     │
│  analysis_jobs → api_responses → data_quality_scores                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NORMALIZED DATA LAYER                                │
│  keywords → backlinks → competitors → pages → technical_metrics             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INTELLIGENCE LAYER                                  │
│  opportunities → threats → recommendations → predictions                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AI AGENT LAYER                                    │
│  agent_runs → agent_outputs → agent_confidence_scores → agent_feedback      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            OUTPUT LAYER                                      │
│  reports → report_sections → deliverables → user_feedback                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LEARNING LAYER                                      │
│  industry_benchmarks → prediction_models → feedback_loops                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Schema

### 1. TENANT LAYER

```sql
-- Organizations (multi-tenant support)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_type VARCHAR(50) DEFAULT 'free', -- free, starter, pro, enterprise
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member', -- owner, admin, member, viewer
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ
);

-- API Keys for programmatic access
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL, -- Store hashed, never plain
    permissions JSONB DEFAULT '["read"]',
    rate_limit INTEGER DEFAULT 100,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. DOMAIN LAYER

```sql
-- Domains being analyzed
CREATE TABLE domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    display_name VARCHAR(255), -- "Bered.nu - Emergency Preparedness"

    -- Classification
    industry VARCHAR(100),
    industry_vertical VARCHAR(100), -- More specific: "prepping", "outdoor gear"
    business_type VARCHAR(50), -- ecommerce, saas, local, media, etc.
    target_market VARCHAR(100), -- Sweden, United States, etc.
    primary_language VARCHAR(50),

    -- Business context (helps AI understand the domain)
    business_description TEXT,
    target_audience TEXT,
    main_products_services TEXT[],
    brand_name VARCHAR(255),

    -- Tracking
    is_active BOOLEAN DEFAULT true,
    first_analyzed_at TIMESTAMPTZ,
    last_analyzed_at TIMESTAMPTZ,
    analysis_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(organization_id, domain)
);

-- Domain health scores over time (for trending)
CREATE TABLE domain_health_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,

    -- Composite scores (0-100)
    overall_score DECIMAL(5,2),
    technical_score DECIMAL(5,2),
    content_score DECIMAL(5,2),
    authority_score DECIMAL(5,2),
    visibility_score DECIMAL(5,2),

    -- Key metrics at this point in time
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    referring_domains INTEGER,
    domain_rating DECIMAL(5,2),

    -- Score breakdown for explainability
    score_breakdown JSONB,

    recorded_at TIMESTAMPTZ DEFAULT NOW(),

    -- Index for time-series queries
    INDEX idx_domain_health_time (domain_id, recorded_at DESC)
);

-- Domain snapshots (full state at a point in time)
CREATE TABLE domain_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID, -- Links to the job that created this

    -- Full snapshot data
    snapshot_data JSONB NOT NULL,

    -- Quick access metrics
    total_pages INTEGER,
    total_keywords INTEGER,
    total_backlinks INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. RAW DATA LAYER

```sql
-- Analysis jobs (each run of the analysis pipeline)
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,

    -- Job metadata
    job_type VARCHAR(50) DEFAULT 'full', -- full, incremental, refresh
    triggered_by VARCHAR(50), -- api, webhook, schedule, manual
    triggered_by_user_id UUID REFERENCES users(id),

    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending', -- pending, collecting, analyzing, generating, completed, failed
    current_phase VARCHAR(100),
    progress_percent INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Configuration used
    config JSONB DEFAULT '{}',

    -- Results summary
    data_quality_score DECIMAL(5,2),
    api_calls_made INTEGER DEFAULT 0,
    api_cost_usd DECIMAL(10,4),
    errors JSONB DEFAULT '[]',
    warnings JSONB DEFAULT '[]',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw API responses (for debugging, reprocessing, and auditing)
CREATE TABLE api_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_job_id UUID REFERENCES analysis_jobs(id) ON DELETE CASCADE,

    -- API call details
    endpoint VARCHAR(255) NOT NULL,
    request_payload JSONB,
    response_payload JSONB,

    -- Metadata
    http_status INTEGER,
    response_time_ms INTEGER,
    cost_usd DECIMAL(10,6),

    -- Data quality assessment
    is_valid BOOLEAN,
    validation_errors JSONB DEFAULT '[]',
    data_completeness_score DECIMAL(5,2), -- 0-100, how complete is the response

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Index for finding responses by endpoint
    INDEX idx_api_responses_endpoint (analysis_job_id, endpoint)
);

-- Data quality scores (track quality issues)
CREATE TABLE data_quality_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_job_id UUID REFERENCES analysis_jobs(id) ON DELETE CASCADE,

    issue_type VARCHAR(100) NOT NULL, -- missing_data, inconsistent_data, stale_data, api_error
    severity VARCHAR(20) NOT NULL, -- critical, high, medium, low

    affected_entity VARCHAR(100), -- keywords, backlinks, competitors, etc.
    affected_count INTEGER,

    description TEXT NOT NULL,
    raw_evidence JSONB,

    -- Resolution
    is_resolved BOOLEAN DEFAULT false,
    resolution_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. NORMALIZED DATA LAYER

```sql
-- Keywords (the core of SEO)
CREATE TABLE keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    -- Keyword data
    keyword VARCHAR(500) NOT NULL,
    keyword_normalized VARCHAR(500), -- Lowercase, trimmed
    keyword_hash VARCHAR(64), -- For deduplication

    -- Search metrics
    search_volume INTEGER,
    search_volume_trend DECIMAL(5,2), -- % change
    cpc DECIMAL(10,4),
    competition DECIMAL(5,4),
    competition_level VARCHAR(20), -- low, medium, high

    -- Ranking data
    current_position INTEGER,
    previous_position INTEGER,
    position_change INTEGER,
    ranking_url VARCHAR(2000),

    -- Intent classification
    search_intent VARCHAR(50), -- informational, navigational, transactional, commercial
    search_intent_confidence DECIMAL(5,4),

    -- Our scoring
    opportunity_score DECIMAL(5,2),
    difficulty_score DECIMAL(5,2),
    priority_score DECIMAL(5,2),

    -- Clustering
    keyword_cluster_id UUID,
    topic_category VARCHAR(255),

    -- Metadata
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    INDEX idx_keywords_domain (domain_id),
    INDEX idx_keywords_search_volume (domain_id, search_volume DESC),
    INDEX idx_keywords_opportunity (domain_id, opportunity_score DESC),
    INDEX idx_keywords_hash (keyword_hash)
);

-- Keyword clusters (semantic grouping)
CREATE TABLE keyword_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,

    cluster_name VARCHAR(255) NOT NULL,
    cluster_theme TEXT,

    -- Aggregated metrics
    total_keywords INTEGER,
    total_search_volume INTEGER,
    avg_difficulty DECIMAL(5,2),
    avg_position DECIMAL(5,2),

    -- Representative keyword
    primary_keyword_id UUID REFERENCES keywords(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Backlinks
CREATE TABLE backlinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    -- Link data
    source_url VARCHAR(2000) NOT NULL,
    source_domain VARCHAR(255) NOT NULL,
    target_url VARCHAR(2000),

    -- Link attributes
    anchor_text VARCHAR(1000),
    anchor_type VARCHAR(50), -- exact, partial, branded, naked, generic
    link_type VARCHAR(50), -- text, image, redirect
    is_dofollow BOOLEAN,
    is_sponsored BOOLEAN,
    is_ugc BOOLEAN,

    -- Source metrics
    source_domain_rating DECIMAL(5,2),
    source_page_rating DECIMAL(5,2),
    source_traffic INTEGER,

    -- Link quality scoring
    link_quality_score DECIMAL(5,2), -- Our assessment
    spam_score DECIMAL(5,2),
    relevance_score DECIMAL(5,2),

    -- Temporal
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    is_lost BOOLEAN DEFAULT false,
    lost_at TIMESTAMPTZ,

    -- Deduplication
    link_hash VARCHAR(64),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_backlinks_domain (domain_id),
    INDEX idx_backlinks_source (source_domain),
    INDEX idx_backlinks_quality (domain_id, link_quality_score DESC)
);

-- Competitors
CREATE TABLE competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    -- Competitor identification
    competitor_domain VARCHAR(255) NOT NULL,

    -- Classification (critical for filtering!)
    competitor_type VARCHAR(50) NOT NULL, -- true_competitor, affiliate, media, government, platform
    is_verified_competitor BOOLEAN DEFAULT false, -- Human verified
    verification_notes TEXT,

    -- Relationship metrics
    keyword_overlap_count INTEGER,
    keyword_overlap_percent DECIMAL(5,2),
    shared_backlinks_count INTEGER,
    serp_visibility_overlap DECIMAL(5,2),

    -- Competitor metrics
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    domain_rating DECIMAL(5,2),
    referring_domains INTEGER,

    -- Competitive position
    threat_level VARCHAR(20), -- low, medium, high, critical
    threat_score DECIMAL(5,2),

    -- Tracking
    first_identified_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,

    UNIQUE(domain_id, competitor_domain),
    INDEX idx_competitors_domain (domain_id),
    INDEX idx_competitors_type (domain_id, competitor_type)
);

-- Pages (content inventory)
CREATE TABLE pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    -- Page identification
    url VARCHAR(2000) NOT NULL,
    url_hash VARCHAR(64),
    path VARCHAR(1000),

    -- Content data
    title VARCHAR(500),
    meta_description VARCHAR(500),
    h1 VARCHAR(500),
    word_count INTEGER,

    -- Performance
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    primary_keyword VARCHAR(500),
    primary_keyword_position INTEGER,

    -- Technical
    status_code INTEGER,
    load_time_ms INTEGER,
    is_indexable BOOLEAN,
    canonical_url VARCHAR(2000),

    -- Content quality
    content_score DECIMAL(5,2),
    freshness_score DECIMAL(5,2),
    last_modified_at TIMESTAMPTZ,

    -- Content decay tracking
    decay_score DECIMAL(5,2),
    decay_velocity DECIMAL(5,2), -- How fast is it decaying
    kuck_recommendation VARCHAR(20), -- keep, update, consolidate, kill

    -- Backlinks to this page
    backlink_count INTEGER,
    referring_domains_count INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain_id, url_hash),
    INDEX idx_pages_domain (domain_id),
    INDEX idx_pages_traffic (domain_id, organic_traffic DESC)
);

-- Technical metrics
CREATE TABLE technical_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    -- Core Web Vitals
    lcp_score DECIMAL(5,2),
    fid_score DECIMAL(5,2),
    cls_score DECIMAL(5,2),

    -- Lighthouse scores
    performance_score DECIMAL(5,2),
    accessibility_score DECIMAL(5,2),
    best_practices_score DECIMAL(5,2),
    seo_score DECIMAL(5,2),

    -- Crawlability
    pages_crawled INTEGER,
    pages_indexed INTEGER,
    indexation_rate DECIMAL(5,2),

    -- Issues
    critical_issues INTEGER,
    warnings INTEGER,
    notices INTEGER,

    -- Detailed issues breakdown
    issues_breakdown JSONB,

    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Technologies detected
CREATE TABLE technologies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    technology_name VARCHAR(255) NOT NULL,
    technology_category VARCHAR(100),
    version VARCHAR(50),

    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    is_current BOOLEAN DEFAULT true,

    UNIQUE(domain_id, technology_name)
);
```

### 5. INTELLIGENCE LAYER

```sql
-- Opportunities (actionable insights)
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    -- Opportunity classification
    opportunity_type VARCHAR(100) NOT NULL, -- keyword_gap, content_gap, link_opportunity, technical_fix
    category VARCHAR(100), -- More specific categorization

    -- Details
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,

    -- Scoring
    impact_score DECIMAL(5,2), -- Potential impact 0-100
    effort_score DECIMAL(5,2), -- Effort required 0-100 (lower = easier)
    confidence_score DECIMAL(5,2), -- How confident are we 0-100
    priority_score DECIMAL(5,2), -- Calculated: (impact * confidence) / effort

    -- Related entities
    related_keywords UUID[], -- Array of keyword IDs
    related_pages UUID[], -- Array of page IDs
    related_competitors UUID[], -- Array of competitor IDs

    -- Evidence (what data supports this opportunity)
    evidence JSONB NOT NULL,

    -- Recommendations
    recommended_actions JSONB, -- Structured action items
    estimated_traffic_gain INTEGER,
    estimated_time_to_result VARCHAR(50), -- "1-2 months", etc.

    -- Tracking
    status VARCHAR(50) DEFAULT 'new', -- new, in_progress, completed, dismissed
    user_feedback VARCHAR(50), -- helpful, not_helpful, implemented

    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_opportunities_domain (domain_id),
    INDEX idx_opportunities_priority (domain_id, priority_score DESC)
);

-- Threats (risks and issues)
CREATE TABLE threats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    threat_type VARCHAR(100) NOT NULL, -- ranking_drop, competitor_surge, technical_issue, penalty_risk
    severity VARCHAR(20) NOT NULL, -- critical, high, medium, low

    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,

    -- Impact assessment
    affected_keywords INTEGER,
    affected_traffic INTEGER,
    risk_score DECIMAL(5,2),

    -- Evidence
    evidence JSONB NOT NULL,

    -- Resolution
    recommended_response TEXT,
    status VARCHAR(50) DEFAULT 'active', -- active, monitoring, resolved

    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    INDEX idx_threats_domain (domain_id),
    INDEX idx_threats_severity (domain_id, severity, risk_score DESC)
);

-- Predictions (forward-looking intelligence)
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),

    prediction_type VARCHAR(100) NOT NULL, -- traffic_forecast, ranking_change, competitor_move

    -- Prediction details
    prediction_summary TEXT NOT NULL,
    prediction_details JSONB NOT NULL,

    -- Confidence
    confidence_score DECIMAL(5,2),
    confidence_interval_low DECIMAL(10,2),
    confidence_interval_high DECIMAL(10,2),

    -- Timeframe
    prediction_horizon VARCHAR(50), -- "30_days", "90_days", "6_months"
    predicted_for_date DATE,

    -- Validation (did it come true?)
    actual_outcome JSONB,
    accuracy_score DECIMAL(5,2),
    validated_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6. AI AGENT LAYER

```sql
-- AI agent definitions
CREATE TABLE ai_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    agent_name VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(50) NOT NULL, -- analyzer, synthesizer, predictor

    description TEXT,

    -- Configuration
    prompt_template TEXT,
    model_id VARCHAR(100),
    temperature DECIMAL(3,2),

    -- Performance tracking
    avg_confidence_score DECIMAL(5,2),
    avg_quality_score DECIMAL(5,2),
    total_runs INTEGER DEFAULT 0,

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual agent runs
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES ai_agents(id),
    analysis_job_id UUID REFERENCES analysis_jobs(id),
    domain_id UUID REFERENCES domains(id),

    -- Input
    input_data JSONB NOT NULL,
    input_token_count INTEGER,

    -- Output
    output_raw TEXT, -- Raw agent response
    output_parsed JSONB, -- Structured output
    output_token_count INTEGER,

    -- Quality metrics
    quality_score DECIMAL(5,2), -- From quality gate
    confidence_score DECIMAL(5,2), -- Agent's self-reported confidence

    -- Quality checks
    passed_quality_gate BOOLEAN,
    quality_check_results JSONB,

    -- Performance
    latency_ms INTEGER,
    model_cost_usd DECIMAL(10,6),

    -- Errors
    had_error BOOLEAN DEFAULT false,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_agent_runs_job (analysis_job_id),
    INDEX idx_agent_runs_agent (agent_id, created_at DESC)
);

-- Agent output feedback (for learning)
CREATE TABLE agent_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,

    -- Feedback source
    feedback_type VARCHAR(50) NOT NULL, -- user, automated, expert
    feedback_by_user_id UUID REFERENCES users(id),

    -- Rating
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),

    -- Specific feedback
    accuracy_rating INTEGER CHECK (accuracy_rating >= 1 AND accuracy_rating <= 5),
    usefulness_rating INTEGER CHECK (usefulness_rating >= 1 AND usefulness_rating <= 5),
    specificity_rating INTEGER CHECK (specificity_rating >= 1 AND specificity_rating <= 5),

    -- Qualitative
    feedback_text TEXT,
    improvement_suggestions TEXT,

    -- What was wrong specifically
    issues JSONB, -- ["too_generic", "missing_data", "incorrect_conclusion"]

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 7. OUTPUT LAYER

```sql
-- Reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    analysis_job_id UUID REFERENCES analysis_jobs(id),
    organization_id UUID REFERENCES organizations(id),

    -- Report metadata
    report_type VARCHAR(50) DEFAULT 'full', -- full, executive, technical, content
    title VARCHAR(500),

    -- Content
    executive_summary TEXT,
    full_content JSONB, -- Structured report content

    -- Generated files
    pdf_url VARCHAR(1000),
    pdf_generated_at TIMESTAMPTZ,

    -- Quality
    overall_quality_score DECIMAL(5,2),
    data_quality_score DECIMAL(5,2),
    ai_quality_score DECIMAL(5,2),

    -- Delivery
    delivered_to_email VARCHAR(255),
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,

    -- Feedback
    user_rating INTEGER,
    user_feedback TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_reports_domain (domain_id),
    INDEX idx_reports_org (organization_id, created_at DESC)
);

-- Report sections (for granular feedback)
CREATE TABLE report_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,

    section_type VARCHAR(100) NOT NULL, -- executive_summary, keyword_analysis, competitor_analysis, etc.
    section_order INTEGER,

    -- Content
    title VARCHAR(255),
    content TEXT,
    content_structured JSONB,

    -- Source agent
    generated_by_agent_id UUID REFERENCES ai_agents(id),
    agent_run_id UUID REFERENCES agent_runs(id),

    -- Quality
    quality_score DECIMAL(5,2),

    -- Feedback
    user_rating INTEGER,
    user_feedback TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 8. LEARNING LAYER

```sql
-- Industry benchmarks (aggregated across all clients)
CREATE TABLE industry_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Segmentation
    industry VARCHAR(100) NOT NULL,
    business_type VARCHAR(50),
    market VARCHAR(100),
    company_size VARCHAR(50), -- small, medium, large

    -- Benchmark metrics
    metric_name VARCHAR(100) NOT NULL,

    -- Statistical data
    percentile_10 DECIMAL(15,2),
    percentile_25 DECIMAL(15,2),
    percentile_50 DECIMAL(15,2), -- Median
    percentile_75 DECIMAL(15,2),
    percentile_90 DECIMAL(15,2),

    mean_value DECIMAL(15,2),
    std_deviation DECIMAL(15,2),

    sample_size INTEGER,

    -- Temporal
    period_start DATE,
    period_end DATE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(industry, business_type, market, company_size, metric_name, period_start),
    INDEX idx_benchmarks_lookup (industry, metric_name)
);

-- Model performance tracking (for ML models)
CREATE TABLE model_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),

    -- Performance metrics
    accuracy DECIMAL(5,4),
    precision_score DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),

    -- Training info
    training_samples INTEGER,
    validation_samples INTEGER,

    -- Deployment
    is_production BOOLEAN DEFAULT false,
    deployed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feature store (for ML features)
CREATE TABLE feature_store (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,

    -- Feature vector
    feature_name VARCHAR(100) NOT NULL,
    feature_value DECIMAL(15,6),
    feature_metadata JSONB,

    -- Temporal
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,

    INDEX idx_features_domain (domain_id, feature_name)
);
```

---

## Key Indexes for Performance

```sql
-- Composite indexes for common query patterns
CREATE INDEX idx_keywords_search ON keywords (domain_id, search_volume DESC, opportunity_score DESC);
CREATE INDEX idx_backlinks_quality ON backlinks (domain_id, link_quality_score DESC, source_domain_rating DESC);
CREATE INDEX idx_competitors_active ON competitors (domain_id, is_active, competitor_type);
CREATE INDEX idx_pages_performance ON pages (domain_id, organic_traffic DESC, decay_score);
CREATE INDEX idx_opportunities_action ON opportunities (domain_id, status, priority_score DESC);
CREATE INDEX idx_agent_runs_quality ON agent_runs (agent_id, quality_score DESC);

-- Full-text search
CREATE INDEX idx_keywords_fts ON keywords USING gin(to_tsvector('english', keyword));
CREATE INDEX idx_opportunities_fts ON opportunities USING gin(to_tsvector('english', title || ' ' || description));
```

---

## Views for Common Queries

```sql
-- Domain dashboard view
CREATE VIEW v_domain_dashboard AS
SELECT
    d.id,
    d.domain,
    d.display_name,
    d.industry,
    dhs.overall_score,
    dhs.organic_traffic,
    dhs.organic_keywords,
    dhs.referring_domains,
    (SELECT COUNT(*) FROM opportunities o WHERE o.domain_id = d.id AND o.status = 'new') as pending_opportunities,
    (SELECT COUNT(*) FROM threats t WHERE t.domain_id = d.id AND t.status = 'active') as active_threats,
    d.last_analyzed_at
FROM domains d
LEFT JOIN LATERAL (
    SELECT * FROM domain_health_scores
    WHERE domain_id = d.id
    ORDER BY recorded_at DESC
    LIMIT 1
) dhs ON true;

-- Competitor comparison view
CREATE VIEW v_competitor_comparison AS
SELECT
    d.domain as target_domain,
    c.competitor_domain,
    c.competitor_type,
    c.keyword_overlap_count,
    c.organic_traffic,
    c.domain_rating,
    c.threat_level,
    c.threat_score
FROM domains d
JOIN competitors c ON c.domain_id = d.id
WHERE c.is_active = true
  AND c.competitor_type = 'true_competitor';

-- AI agent performance view
CREATE VIEW v_agent_performance AS
SELECT
    a.agent_name,
    COUNT(ar.id) as total_runs,
    AVG(ar.quality_score) as avg_quality,
    AVG(ar.confidence_score) as avg_confidence,
    AVG(ar.latency_ms) as avg_latency_ms,
    SUM(ar.model_cost_usd) as total_cost,
    COUNT(CASE WHEN ar.passed_quality_gate THEN 1 END)::float / COUNT(*)::float as pass_rate,
    AVG(af.rating) as avg_user_rating
FROM ai_agents a
JOIN agent_runs ar ON ar.agent_id = a.id
LEFT JOIN agent_feedback af ON af.agent_run_id = ar.id
GROUP BY a.id, a.agent_name;
```

---

## Migration Strategy

### Phase 1: Core Tables (Week 1)
- organizations, users, api_keys
- domains, domain_health_scores
- analysis_jobs, api_responses

### Phase 2: Data Tables (Week 2)
- keywords, keyword_clusters
- backlinks
- competitors
- pages
- technical_metrics, technologies

### Phase 3: Intelligence Tables (Week 3)
- opportunities
- threats
- predictions

### Phase 4: AI & Output Tables (Week 4)
- ai_agents, agent_runs, agent_feedback
- reports, report_sections

### Phase 5: Learning Tables (Week 5)
- industry_benchmarks
- model_performance
- feature_store

---

## Data Flow with Database

```
1. COLLECTION PHASE
   API Response → api_responses table (raw)
                → Data validation
                → data_quality_issues table (if issues)
                → Normalized tables (keywords, backlinks, etc.)

2. ENRICHMENT PHASE
   Normalized data → Calculate scores
                   → Compare to benchmarks
                   → Identify opportunities/threats
                   → Store in intelligence tables

3. ANALYSIS PHASE
   Load from DB → AI Agent
                → agent_runs table (with input/output)
                → quality gate check
                → agent_feedback (if needed)

4. REPORT PHASE
   Pull from all tables → Generate report
                        → reports table
                        → Deliver
                        → Track feedback

5. LEARNING PHASE
   Aggregate data → Update benchmarks
                  → Retrain models
                  → Improve agents
```

---

## Benefits of This Schema

1. **Data Lineage**: Every piece of data can be traced back to its source API response
2. **Temporal Analysis**: Full history enables trend analysis and predictions
3. **Quality Control**: Data quality issues are tracked and flagged before analysis
4. **AI Accountability**: Every AI output is stored with its input for auditing
5. **Feedback Loops**: User feedback directly improves agent performance
6. **Industry Intelligence**: Cross-client data enables benchmarking
7. **Multi-Tenant Ready**: Organizations can have isolated data
8. **ML-Ready**: Feature store and performance tracking for ML models
9. **Competitive Intelligence**: Proper competitor classification and tracking
10. **Scalable**: Indexes and partitioning support growth

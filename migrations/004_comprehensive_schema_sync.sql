-- Migration: 004_comprehensive_schema_sync
-- Description: Comprehensive schema synchronization ensuring all tables and columns exist
-- Use this to bring any database up to the current schema state
-- Safe to run multiple times (all operations are idempotent)
-- Created: 2026-01-27

BEGIN;

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

-- Analysis status enum
DO $$ BEGIN
    CREATE TYPE analysisstatus AS ENUM ('pending', 'collecting', 'validating', 'analyzing', 'generating', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Analysis mode enum
DO $$ BEGIN
    CREATE TYPE analysismode AS ENUM ('standard', 'greenfield', 'hybrid');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Data quality level enum
DO $$ BEGIN
    CREATE TYPE dataqualitylevel AS ENUM ('excellent', 'good', 'fair', 'poor', 'invalid');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Competitor type enum
DO $$ BEGIN
    CREATE TYPE competitortype AS ENUM ('true_competitor', 'affiliate', 'media', 'government', 'platform', 'unknown');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Competitor purpose enum (greenfield)
DO $$ BEGIN
    CREATE TYPE competitorpurpose AS ENUM ('benchmark_peer', 'keyword_source', 'link_source', 'content_model', 'aspirational');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Search intent enum
DO $$ BEGIN
    CREATE TYPE searchintent AS ENUM ('informational', 'navigational', 'transactional', 'commercial');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- SERP feature type enum
DO $$ BEGIN
    CREATE TYPE serpfeaturetype AS ENUM ('featured_snippet', 'people_also_ask', 'local_pack', 'knowledge_panel', 'image_pack', 'video_carousel', 'top_stories', 'shopping_results', 'sitelinks', 'faq_schema', 'reviews', 'ai_overview', 'discussion_forums', 'related_searches');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- AI visibility source enum
DO $$ BEGIN
    CREATE TYPE aivisibilitysource AS ENUM ('google_ai_overview', 'chatgpt', 'perplexity', 'claude', 'bing_copilot', 'google_sge');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Business model type enum
DO $$ BEGIN
    CREATE TYPE businessmodeltype AS ENUM ('b2b_saas', 'b2b_service', 'b2c_ecommerce', 'b2c_subscription', 'marketplace', 'publisher', 'local_service', 'nonprofit', 'unknown');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Primary goal type enum
DO $$ BEGIN
    CREATE TYPE primarygoaltype AS ENUM ('traffic', 'leads', 'authority', 'balanced');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Validated competitor type enum
DO $$ BEGIN
    CREATE TYPE validatedcompetitortype AS ENUM ('direct', 'seo', 'content', 'emerging', 'aspirational', 'not_competitor');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Strategy status enum
DO $$ BEGIN
    CREATE TYPE strategystatus AS ENUM ('draft', 'approved', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Thread status enum
DO $$ BEGIN
    CREATE TYPE threadstatus AS ENUM ('draft', 'confirmed', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Topic status enum
DO $$ BEGIN
    CREATE TYPE topicstatus AS ENUM ('draft', 'confirmed', 'in_production', 'published');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Content type enum
DO $$ BEGIN
    CREATE TYPE contenttype AS ENUM ('pillar', 'cluster', 'supporting');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- User role enum
DO $$ BEGIN
    CREATE TYPE userrole AS ENUM ('user', 'admin');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Users table (authentication)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    avatar_url VARCHAR(2000),
    role userrole NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    provider VARCHAR(50),
    last_sign_in_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Clients table
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Domains table
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    user_id UUID REFERENCES users(id),
    domain VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    industry VARCHAR(100),
    business_type VARCHAR(50),
    target_market VARCHAR(100),
    primary_language VARCHAR(50),
    brand_name VARCHAR(255),
    business_description TEXT,
    target_audience TEXT,
    main_products_services JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    analysis_count INTEGER DEFAULT 0,
    first_analyzed_at TIMESTAMP,
    last_analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add user_id column to domains if missing
ALTER TABLE domains ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);

-- Analysis runs table
CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    status analysisstatus DEFAULT 'pending',
    current_phase VARCHAR(50),
    progress_percent INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}'::jsonb,
    analysis_mode analysismode DEFAULT 'standard',
    domain_maturity_at_analysis VARCHAR(20),
    domain_rating_at_analysis INTEGER,
    organic_keywords_at_analysis INTEGER,
    organic_traffic_at_analysis INTEGER,
    greenfield_context JSONB,
    data_quality dataqualitylevel,
    data_quality_score FLOAT,
    quality_issues JSONB DEFAULT '[]'::jsonb,
    api_calls_count INTEGER DEFAULT 0,
    api_cost_usd FLOAT DEFAULT 0,
    ai_tokens_used INTEGER DEFAULT 0,
    ai_cost_usd FLOAT DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    error_message TEXT,
    errors JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ensure greenfield columns exist on analysis_runs
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS analysis_mode analysismode DEFAULT 'standard';
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS domain_maturity_at_analysis VARCHAR(20);
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS domain_rating_at_analysis INTEGER;
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS organic_keywords_at_analysis INTEGER;
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS organic_traffic_at_analysis INTEGER;
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS greenfield_context JSONB;

-- API calls table
CREATE TABLE IF NOT EXISTS api_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    endpoint VARCHAR(255) NOT NULL,
    phase VARCHAR(50),
    request_payload JSONB,
    response_payload JSONB,
    http_status INTEGER,
    response_time_ms INTEGER,
    cost_usd FLOAT,
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors JSONB DEFAULT '[]'::jsonb,
    data_completeness FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- SEO DATA TABLES
-- =============================================================================

-- Keywords table
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    keyword VARCHAR(500) NOT NULL,
    keyword_normalized VARCHAR(500),
    source VARCHAR(50),
    search_volume INTEGER,
    cpc FLOAT,
    competition FLOAT,
    competition_level VARCHAR(20),
    keyword_difficulty INTEGER,
    current_position INTEGER,
    previous_position INTEGER,
    position_change INTEGER,
    ranking_url VARCHAR(2000),
    estimated_traffic INTEGER,
    traffic_cost FLOAT,
    search_intent searchintent,
    secondary_intents JSONB DEFAULT '[]'::jsonb,
    opportunity_score FLOAT,
    priority_score FLOAT,
    cluster_name VARCHAR(255),
    is_cluster_seed BOOLEAN DEFAULT FALSE,
    parent_topic VARCHAR(500),
    monthly_searches JSONB,
    -- Greenfield winnability fields
    winnability_score FLOAT,
    winnability_components JSONB,
    personalized_difficulty INTEGER,
    is_beachhead BOOLEAN DEFAULT FALSE,
    beachhead_priority INTEGER,
    beachhead_score FLOAT,
    growth_phase INTEGER,
    serp_avg_dr FLOAT,
    serp_min_dr INTEGER,
    serp_has_low_dr BOOLEAN,
    serp_weak_signals JSONB,
    has_ai_overview BOOLEAN DEFAULT FALSE,
    aio_source_count INTEGER,
    aio_optimization_potential FLOAT,
    source_competitor VARCHAR(255),
    competitor_position INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add winnability columns to keywords if missing
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS winnability_score FLOAT;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS winnability_components JSONB;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS personalized_difficulty INTEGER;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS is_beachhead BOOLEAN DEFAULT FALSE;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS beachhead_priority INTEGER;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS beachhead_score FLOAT;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS growth_phase INTEGER;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS serp_avg_dr FLOAT;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS serp_min_dr INTEGER;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS serp_has_low_dr BOOLEAN;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS serp_weak_signals JSONB;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS has_ai_overview BOOLEAN DEFAULT FALSE;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS aio_source_count INTEGER;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS aio_optimization_potential FLOAT;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS source_competitor VARCHAR(255);
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS competitor_position INTEGER;

-- Competitors table
CREATE TABLE IF NOT EXISTS competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    competitor_domain VARCHAR(255) NOT NULL,
    competitor_type competitortype DEFAULT 'unknown',
    is_verified BOOLEAN DEFAULT FALSE,
    verification_notes TEXT,
    detection_method VARCHAR(50),
    detection_confidence FLOAT,
    keyword_overlap_count INTEGER,
    keyword_overlap_percent FLOAT,
    shared_backlinks_count INTEGER,
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    domain_rating FLOAT,
    referring_domains INTEGER,
    avg_position FLOAT,
    threat_level VARCHAR(20),
    threat_score FLOAT,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Backlinks table
CREATE TABLE IF NOT EXISTS backlinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    source_url VARCHAR(2000) NOT NULL,
    source_domain VARCHAR(255) NOT NULL,
    target_url VARCHAR(2000),
    anchor_text VARCHAR(1000),
    anchor_type VARCHAR(50),
    link_type VARCHAR(50),
    is_dofollow BOOLEAN,
    is_sponsored BOOLEAN,
    is_ugc BOOLEAN,
    source_domain_rating FLOAT,
    source_page_rating FLOAT,
    source_traffic INTEGER,
    link_quality_score FLOAT,
    spam_score FLOAT,
    relevance_score FLOAT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    is_lost BOOLEAN DEFAULT FALSE,
    lost_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pages table
CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    url VARCHAR(2000) NOT NULL,
    path VARCHAR(1000),
    title VARCHAR(500),
    meta_description VARCHAR(500),
    h1 VARCHAR(500),
    word_count INTEGER,
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    primary_keyword VARCHAR(500),
    primary_keyword_position INTEGER,
    backlink_count INTEGER,
    referring_domains_count INTEGER,
    content_score FLOAT,
    freshness_score FLOAT,
    last_modified TIMESTAMP,
    decay_score FLOAT,
    kuck_recommendation VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Technical metrics table
CREATE TABLE IF NOT EXISTS technical_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    performance_score FLOAT,
    accessibility_score FLOAT,
    best_practices_score FLOAT,
    seo_score FLOAT,
    lcp_ms INTEGER,
    fid_ms INTEGER,
    cls FLOAT,
    inp_ms INTEGER,
    technical_score FLOAT,
    critical_issues INTEGER,
    warnings INTEGER,
    issues_detail JSONB,
    technologies JSONB,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- AI & REPORTS TABLES
-- =============================================================================

-- Agent outputs table
CREATE TABLE IF NOT EXISTS agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    agent_name VARCHAR(100) NOT NULL,
    agent_version VARCHAR(50),
    input_summary JSONB,
    input_tokens INTEGER,
    output_raw TEXT,
    output_parsed JSONB,
    output_tokens INTEGER,
    quality_score FLOAT,
    passed_quality_gate BOOLEAN,
    quality_issues JSONB DEFAULT '[]'::jsonb,
    confidence_score FLOAT,
    model_used VARCHAR(100),
    cost_usd FLOAT,
    latency_ms INTEGER,
    user_rating INTEGER,
    user_feedback TEXT,
    feedback_tags JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    report_type VARCHAR(50) DEFAULT 'full',
    title VARCHAR(500),
    executive_summary TEXT,
    content JSONB,
    pdf_path VARCHAR(1000),
    pdf_generated_at TIMESTAMP,
    overall_quality_score FLOAT,
    delivered_to VARCHAR(255),
    delivered_at TIMESTAMP,
    opened_at TIMESTAMP,
    user_rating INTEGER,
    user_feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Domain metrics history
CREATE TABLE IF NOT EXISTS domain_metrics_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    analysis_run_id UUID REFERENCES analysis_runs(id),
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    domain_rating FLOAT,
    referring_domains INTEGER,
    backlinks_total INTEGER,
    positions_1 INTEGER,
    positions_2_3 INTEGER,
    positions_4_10 INTEGER,
    positions_11_20 INTEGER,
    positions_21_50 INTEGER,
    positions_51_100 INTEGER,
    performance_score FLOAT,
    seo_score FLOAT,
    overall_health_score FLOAT,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- INTELLIGENCE TABLES
-- =============================================================================

-- SERP features table
CREATE TABLE IF NOT EXISTS serp_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    keyword_id UUID REFERENCES keywords(id),
    keyword VARCHAR(500) NOT NULL,
    feature_type serpfeaturetype NOT NULL,
    position INTEGER,
    owned_by_target BOOLEAN DEFAULT FALSE,
    owned_by_domain VARCHAR(255),
    feature_data JSONB DEFAULT '{}'::jsonb,
    can_target BOOLEAN DEFAULT TRUE,
    opportunity_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Keyword gaps table
CREATE TABLE IF NOT EXISTS keyword_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    keyword VARCHAR(500) NOT NULL,
    keyword_normalized VARCHAR(500),
    search_volume INTEGER,
    keyword_difficulty INTEGER,
    cpc FLOAT,
    search_intent searchintent,
    target_position INTEGER,
    target_url VARCHAR(2000),
    competitor_positions JSONB DEFAULT '{}'::jsonb,
    best_competitor VARCHAR(255),
    best_competitor_position INTEGER,
    competitor_count INTEGER,
    avg_competitor_position FLOAT,
    position_gap INTEGER,
    opportunity_score FLOAT,
    priority VARCHAR(20),
    difficulty_adjusted_score FLOAT,
    suggested_content_type VARCHAR(50),
    estimated_traffic_potential INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Referring domains table
CREATE TABLE IF NOT EXISTS referring_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    referring_domain VARCHAR(255) NOT NULL,
    domain_rating FLOAT,
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    backlink_count INTEGER,
    dofollow_count INTEGER,
    nofollow_count INTEGER,
    text_links INTEGER,
    image_links INTEGER,
    redirect_links INTEGER,
    linked_pages JSONB DEFAULT '[]'::jsonb,
    unique_pages_linked INTEGER,
    anchor_distribution JSONB DEFAULT '{}'::jsonb,
    primary_anchor VARCHAR(500),
    quality_score FLOAT,
    spam_score FLOAT,
    relevance_score FLOAT,
    domain_type VARCHAR(50),
    is_competitor BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    is_lost BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ranking history table
CREATE TABLE IF NOT EXISTS ranking_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    keyword VARCHAR(500) NOT NULL,
    keyword_normalized VARCHAR(500),
    position INTEGER,
    previous_position INTEGER,
    position_change INTEGER,
    ranking_url VARCHAR(2000),
    previous_url VARCHAR(2000),
    estimated_traffic INTEGER,
    traffic_change INTEGER,
    serp_volatility FLOAT,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Content clusters table
CREATE TABLE IF NOT EXISTS content_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    cluster_name VARCHAR(255) NOT NULL,
    cluster_slug VARCHAR(255),
    pillar_keyword VARCHAR(500),
    pillar_url VARCHAR(2000),
    pillar_position INTEGER,
    total_keywords INTEGER,
    ranking_keywords INTEGER,
    avg_position FLOAT,
    total_search_volume INTEGER,
    total_traffic INTEGER,
    keywords JSONB DEFAULT '[]'::jsonb,
    missing_subtopics JSONB DEFAULT '[]'::jsonb,
    content_gap_count INTEGER,
    cluster_difficulty FLOAT,
    top_competitor VARCHAR(255),
    competitor_coverage JSONB DEFAULT '{}'::jsonb,
    topical_authority_score FLOAT,
    content_completeness FLOAT,
    recommended_content JSONB DEFAULT '[]'::jsonb,
    priority VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI visibility table
CREATE TABLE IF NOT EXISTS ai_visibility (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    query VARCHAR(500) NOT NULL,
    topic_category VARCHAR(100),
    ai_source aivisibilitysource NOT NULL,
    is_mentioned BOOLEAN DEFAULT FALSE,
    is_cited BOOLEAN DEFAULT FALSE,
    is_recommended BOOLEAN DEFAULT FALSE,
    citation_url VARCHAR(2000),
    citation_context TEXT,
    citation_position INTEGER,
    competitors_mentioned JSONB DEFAULT '[]'::jsonb,
    total_citations INTEGER,
    cited_content_type VARCHAR(50),
    cited_content_topic VARCHAR(255),
    sentiment VARCHAR(20),
    authority_signal BOOLEAN,
    checked_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Local rankings table
CREATE TABLE IF NOT EXISTS local_rankings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    location_name VARCHAR(255),
    address VARCHAR(500),
    city VARCHAR(100),
    region VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    latitude FLOAT,
    longitude FLOAT,
    gbp_name VARCHAR(255),
    gbp_category VARCHAR(100),
    gbp_rating FLOAT,
    gbp_review_count INTEGER,
    gbp_url VARCHAR(2000),
    keyword VARCHAR(500) NOT NULL,
    search_volume INTEGER,
    local_pack_position INTEGER,
    organic_position INTEGER,
    maps_position INTEGER,
    local_pack_competitors JSONB DEFAULT '[]'::jsonb,
    distance_from_centroid FLOAT,
    prominence_score FLOAT,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- SERP competitors table
CREATE TABLE IF NOT EXISTS serp_competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    domain_id UUID NOT NULL REFERENCES domains(id),
    keyword_id UUID REFERENCES keywords(id),
    keyword VARCHAR(500) NOT NULL,
    competitor_domain VARCHAR(255) NOT NULL,
    competitor_url VARCHAR(2000),
    position INTEGER NOT NULL,
    page_title VARCHAR(500),
    page_backlinks INTEGER,
    page_referring_domains INTEGER,
    page_domain_rating FLOAT,
    content_type VARCHAR(50),
    word_count INTEGER,
    has_schema BOOLEAN,
    schema_types JSONB DEFAULT '[]'::jsonb,
    serp_features_owned JSONB DEFAULT '[]'::jsonb,
    is_beatable BOOLEAN,
    difficulty_to_outrank FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- CONTEXT INTELLIGENCE TABLES
-- =============================================================================

-- Context intelligence table
CREATE TABLE IF NOT EXISTS context_intelligence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    analysis_run_id UUID REFERENCES analysis_runs(id),
    declared_market VARCHAR(50),
    declared_language VARCHAR(10),
    declared_goal primarygoaltype,
    user_provided_competitors JSONB DEFAULT '[]'::jsonb,
    resolved_market_code VARCHAR(10),
    resolved_market_name VARCHAR(100),
    resolved_location_code INTEGER,
    resolved_language_code VARCHAR(10),
    resolved_language_name VARCHAR(50),
    resolved_market_source VARCHAR(30),
    resolved_market_confidence VARCHAR(20),
    resolved_detection_confidence FLOAT,
    resolved_has_conflict BOOLEAN DEFAULT FALSE,
    resolved_conflict_details TEXT,
    detected_business_model businessmodeltype,
    detected_company_stage VARCHAR(50),
    detected_languages JSONB DEFAULT '[]'::jsonb,
    detected_offerings JSONB DEFAULT '[]'::jsonb,
    value_proposition TEXT,
    target_audience JSONB DEFAULT '{}'::jsonb,
    has_blog BOOLEAN DEFAULT FALSE,
    has_pricing_page BOOLEAN DEFAULT FALSE,
    has_demo_form BOOLEAN DEFAULT FALSE,
    has_contact_form BOOLEAN DEFAULT FALSE,
    has_ecommerce BOOLEAN DEFAULT FALSE,
    content_maturity VARCHAR(50),
    technical_sophistication VARCHAR(50),
    goal_fits_business BOOLEAN DEFAULT TRUE,
    goal_validation_confidence FLOAT,
    suggested_goal primarygoaltype,
    goal_suggestion_reason TEXT,
    primary_market_validated BOOLEAN DEFAULT TRUE,
    market_validation_notes TEXT,
    discovered_markets JSONB DEFAULT '[]'::jsonb,
    should_expand_markets BOOLEAN DEFAULT FALSE,
    suggested_markets JSONB DEFAULT '[]'::jsonb,
    should_adjust_market BOOLEAN DEFAULT FALSE,
    suggested_market VARCHAR(50),
    language_mismatch BOOLEAN DEFAULT FALSE,
    validated_competitors JSONB DEFAULT '[]'::jsonb,
    discovered_competitors JSONB DEFAULT '[]'::jsonb,
    rejected_competitors JSONB DEFAULT '[]'::jsonb,
    direct_competitors_count INTEGER DEFAULT 0,
    seo_competitors_count INTEGER DEFAULT 0,
    emerging_threats_count INTEGER DEFAULT 0,
    buyer_journey_type VARCHAR(50),
    buyer_journey_stages JSONB DEFAULT '[]'::jsonb,
    success_definition JSONB DEFAULT '{}'::jsonb,
    recommended_focus_areas JSONB DEFAULT '[]'::jsonb,
    seo_fit VARCHAR(50),
    quick_wins_potential VARCHAR(50),
    collection_config JSONB DEFAULT '{}'::jsonb,
    overall_confidence FLOAT,
    website_analysis_confidence FLOAT,
    context_confidence FLOAT,
    execution_time_seconds FLOAT,
    errors JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    user_validated BOOLEAN DEFAULT FALSE,
    user_corrections JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Validated competitors table
CREATE TABLE IF NOT EXISTS validated_competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    context_intelligence_id UUID REFERENCES context_intelligence(id),
    competitor_domain VARCHAR(255) NOT NULL,
    competitor_name VARCHAR(255),
    competitor_type validatedcompetitortype NOT NULL,
    threat_level VARCHAR(20),
    discovery_method VARCHAR(50),
    user_provided BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(50),
    validation_notes TEXT,
    keyword_overlap_percentage FLOAT,
    traffic_ratio FLOAT,
    business_similarity_score FLOAT,
    strengths JSONB DEFAULT '[]'::jsonb,
    weaknesses JSONB DEFAULT '[]'::jsonb,
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    domain_rating FLOAT,
    traffic_trend VARCHAR(20),
    confidence_score FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    user_validated BOOLEAN DEFAULT FALSE,
    discovered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Market opportunities table
CREATE TABLE IF NOT EXISTS market_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    context_intelligence_id UUID REFERENCES context_intelligence(id),
    region VARCHAR(100) NOT NULL,
    language VARCHAR(50) NOT NULL,
    region_name VARCHAR(255),
    opportunity_score FLOAT,
    competition_level VARCHAR(20),
    search_volume_potential INTEGER,
    keyword_count_estimate INTEGER,
    top_competitors_in_market JSONB DEFAULT '[]'::jsonb,
    our_current_visibility FLOAT,
    is_primary BOOLEAN DEFAULT FALSE,
    is_recommended BOOLEAN DEFAULT FALSE,
    priority_rank INTEGER,
    recommendation_reason TEXT,
    discovery_method VARCHAR(50),
    discovered_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- STRATEGY BUILDER TABLES
-- =============================================================================

-- Strategies table
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status strategystatus NOT NULL DEFAULT 'draft',
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Strategy threads table
CREATE TABLE IF NOT EXISTS strategy_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    position VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status threadstatus NOT NULL DEFAULT 'draft',
    priority INTEGER CHECK (priority BETWEEN 1 AND 5),
    recommended_format VARCHAR(50),
    format_confidence FLOAT,
    format_evidence JSONB,
    custom_instructions JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Thread keywords junction table
CREATE TABLE IF NOT EXISTS thread_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES strategy_threads(id) ON DELETE CASCADE,
    keyword_id UUID NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
    position VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Strategy topics table
CREATE TABLE IF NOT EXISTS strategy_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES strategy_threads(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    slug VARCHAR(255),
    position VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    primary_keyword_id UUID REFERENCES keywords(id) ON DELETE SET NULL,
    primary_keyword VARCHAR(500),
    content_type contenttype NOT NULL DEFAULT 'cluster',
    status topicstatus NOT NULL DEFAULT 'draft',
    target_url VARCHAR(2000),
    existing_url VARCHAR(2000),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Strategy exports table
CREATE TABLE IF NOT EXISTS strategy_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,
    exported_data JSONB NOT NULL,
    exported_at TIMESTAMP NOT NULL DEFAULT NOW(),
    exported_by VARCHAR(255),
    file_path VARCHAR(1000),
    file_size_bytes INTEGER,
    thread_count INTEGER,
    topic_count INTEGER,
    keyword_count INTEGER
);

-- Strategy activity log table
CREATE TABLE IF NOT EXISTS strategy_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(30),
    entity_id UUID,
    user_id VARCHAR(255),
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- GREENFIELD INTELLIGENCE TABLES
-- =============================================================================

-- Greenfield analyses table
CREATE TABLE IF NOT EXISTS greenfield_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES domains(id),
    total_addressable_market INTEGER,
    serviceable_addressable_market INTEGER,
    serviceable_obtainable_market INTEGER,
    tam_keyword_count INTEGER,
    sam_keyword_count INTEGER,
    som_keyword_count INTEGER,
    market_opportunity_score FLOAT,
    competition_intensity FLOAT,
    competitor_count INTEGER,
    avg_competitor_dr FLOAT,
    competitor_dr_range JSONB,
    competitor_traffic_share JSONB,
    beachhead_keyword_count INTEGER,
    total_beachhead_volume INTEGER,
    avg_beachhead_winnability FLOAT,
    beachhead_keywords JSONB,
    projection_conservative JSONB,
    projection_expected JSONB,
    projection_aggressive JSONB,
    growth_roadmap JSONB,
    data_completeness_score FLOAT,
    validation_warnings JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Competitor intelligence sessions table
CREATE TABLE IF NOT EXISTS competitor_intelligence_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES domains(id),
    status VARCHAR(30) DEFAULT 'pending',
    website_context JSONB,
    business_description TEXT,
    detected_offerings JSONB DEFAULT '[]'::jsonb,
    detected_industry VARCHAR(100),
    perplexity_query TEXT,
    perplexity_response JSONB,
    ai_discovered_competitors JSONB DEFAULT '[]'::jsonb,
    serp_discovered_competitors JSONB DEFAULT '[]'::jsonb,
    traffic_share_competitors JSONB DEFAULT '[]'::jsonb,
    user_provided_competitors JSONB DEFAULT '[]'::jsonb,
    candidate_competitors JSONB DEFAULT '[]'::jsonb,
    candidates_generated_at TIMESTAMP,
    curation_started_at TIMESTAMP,
    curation_completed_at TIMESTAMP,
    removed_competitors JSONB DEFAULT '[]'::jsonb,
    added_competitors JSONB DEFAULT '[]'::jsonb,
    final_competitors JSONB DEFAULT '[]'::jsonb,
    finalized_at TIMESTAMP,
    api_calls_count INTEGER DEFAULT 0,
    perplexity_cost_usd FLOAT DEFAULT 0,
    firecrawl_cost_usd FLOAT DEFAULT 0,
    dataforseo_cost_usd FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Greenfield competitors table
CREATE TABLE IF NOT EXISTS greenfield_competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES competitor_intelligence_sessions(id) ON DELETE CASCADE,
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    purpose competitorpurpose NOT NULL,
    purpose_override competitorpurpose,
    priority INTEGER,
    discovery_source VARCHAR(50),
    discovery_reason TEXT,
    relevance_score FLOAT,
    domain_rating INTEGER,
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    referring_domains INTEGER,
    keyword_overlap_count INTEGER,
    keyword_overlap_percent FLOAT,
    traffic_share_percent FLOAT,
    is_validated BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(30),
    validation_warnings JSONB DEFAULT '[]'::jsonb,
    is_user_provided BOOLEAN DEFAULT FALSE,
    is_removed BOOLEAN DEFAULT FALSE,
    removal_reason VARCHAR(50),
    removal_note TEXT,
    keywords_extracted INTEGER DEFAULT 0,
    used_for_market_sizing BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- CACHING TABLES
-- =============================================================================

-- Precomputed dashboard table
CREATE TABLE IF NOT EXISTS precomputed_dashboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),
    data_type VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    size_bytes INTEGER,
    computation_time_ms INTEGER,
    valid_until TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    etag VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cache metrics log table
CREATE TABLE IF NOT EXISTS cache_metrics_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    hits INTEGER DEFAULT 0,
    misses INTEGER DEFAULT 0,
    hit_rate FLOAT,
    avg_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    p99_latency_ms FLOAT,
    memory_used_mb FLOAT,
    memory_peak_mb FLOAT,
    bytes_read BIGINT DEFAULT 0,
    bytes_written BIGINT DEFAULT 0,
    bytes_saved_compression BIGINT DEFAULT 0,
    errors INTEGER DEFAULT 0,
    error_rate FLOAT,
    circuit_breaker_triggered BOOLEAN DEFAULT FALSE
);

-- Schema migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_role ON users(role);

-- Domains indexes
CREATE INDEX IF NOT EXISTS idx_domain_lookup ON domains(domain);
CREATE INDEX IF NOT EXISTS idx_domain_user ON domains(user_id);

-- Analysis runs indexes
CREATE INDEX IF NOT EXISTS idx_run_domain_time ON analysis_runs(domain_id, created_at);
CREATE INDEX IF NOT EXISTS idx_run_status ON analysis_runs(status);

-- Keywords indexes
CREATE INDEX IF NOT EXISTS idx_keyword_search ON keywords(domain_id, search_volume);
CREATE INDEX IF NOT EXISTS idx_keyword_opportunity ON keywords(domain_id, opportunity_score);
CREATE INDEX IF NOT EXISTS idx_keyword_position ON keywords(domain_id, current_position);
CREATE INDEX IF NOT EXISTS idx_keyword_text ON keywords(keyword_normalized);
CREATE INDEX IF NOT EXISTS idx_keyword_parent_topic ON keywords(domain_id, parent_topic);
CREATE INDEX IF NOT EXISTS idx_keyword_winnability ON keywords(analysis_run_id, winnability_score DESC);
CREATE INDEX IF NOT EXISTS idx_keyword_beachhead ON keywords(analysis_run_id, is_beachhead) WHERE is_beachhead = TRUE;
CREATE INDEX IF NOT EXISTS idx_keyword_growth_phase ON keywords(analysis_run_id, growth_phase);

-- Competitors indexes
CREATE INDEX IF NOT EXISTS idx_competitor_type ON competitors(domain_id, competitor_type);
CREATE INDEX IF NOT EXISTS idx_competitor_threat ON competitors(domain_id, threat_score);

-- Context intelligence indexes
CREATE INDEX IF NOT EXISTS idx_context_domain ON context_intelligence(domain_id, created_at);
CREATE INDEX IF NOT EXISTS idx_context_goal ON context_intelligence(domain_id, declared_goal);

-- Greenfield indexes
CREATE INDEX IF NOT EXISTS idx_greenfield_analysis_run ON greenfield_analyses(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_greenfield_domain ON greenfield_analyses(domain_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ci_session_analysis ON competitor_intelligence_sessions(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_ci_session_domain ON competitor_intelligence_sessions(domain_id);
CREATE INDEX IF NOT EXISTS idx_ci_session_status ON competitor_intelligence_sessions(status);
CREATE INDEX IF NOT EXISTS idx_gf_competitor_session ON greenfield_competitors(session_id);
CREATE INDEX IF NOT EXISTS idx_gf_competitor_purpose ON greenfield_competitors(session_id, purpose);

-- Strategy indexes
CREATE INDEX IF NOT EXISTS idx_strategy_domain ON strategies(domain_id, created_at);
CREATE INDEX IF NOT EXISTS idx_strategy_status ON strategies(domain_id, status);
CREATE INDEX IF NOT EXISTS idx_thread_strategy ON strategy_threads(strategy_id, position);
CREATE INDEX IF NOT EXISTS idx_topic_thread ON strategy_topics(thread_id, position);
CREATE INDEX IF NOT EXISTS idx_export_strategy ON strategy_exports(strategy_id, exported_at);
CREATE INDEX IF NOT EXISTS idx_activity_strategy ON strategy_activity_log(strategy_id, created_at);

-- Cache indexes
CREATE INDEX IF NOT EXISTS idx_precomputed_domain_type ON precomputed_dashboard(domain_id, data_type, is_current);
CREATE INDEX IF NOT EXISTS idx_precomputed_analysis ON precomputed_dashboard(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_cache_metrics_time ON cache_metrics_log(recorded_at);

-- =============================================================================
-- UNIQUE CONSTRAINTS
-- =============================================================================

-- Add unique constraints (safe to run multiple times)
DO $$ BEGIN
    ALTER TABLE domains ADD CONSTRAINT uq_client_domain UNIQUE (client_id, domain);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE domains ADD CONSTRAINT uq_user_domain UNIQUE (user_id, domain);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE competitors ADD CONSTRAINT uq_run_competitor UNIQUE (analysis_run_id, competitor_domain);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE referring_domains ADD CONSTRAINT uq_run_referring_domain UNIQUE (analysis_run_id, referring_domain);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE validated_competitors ADD CONSTRAINT uq_domain_competitor UNIQUE (domain_id, competitor_domain);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE market_opportunities ADD CONSTRAINT uq_domain_market UNIQUE (domain_id, region, language);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE strategy_threads ADD CONSTRAINT uq_thread_position UNIQUE (strategy_id, position);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE thread_keywords ADD CONSTRAINT uq_thread_keyword UNIQUE (thread_id, keyword_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE strategy_topics ADD CONSTRAINT uq_topic_position UNIQUE (thread_id, position);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE greenfield_competitors ADD CONSTRAINT uq_session_competitor UNIQUE (session_id, domain);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE precomputed_dashboard ADD CONSTRAINT uq_precomputed_analysis_type UNIQUE (analysis_run_id, data_type);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Updated timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ci_sessions_updated_at ON competitor_intelligence_sessions;
CREATE TRIGGER update_ci_sessions_updated_at BEFORE UPDATE ON competitor_intelligence_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_gf_competitors_updated_at ON greenfield_competitors;
CREATE TRIGGER update_gf_competitors_updated_at BEFORE UPDATE ON greenfield_competitors FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- MIGRATION TRACKING
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('004_comprehensive_schema_sync', 'Comprehensive schema synchronization ensuring all tables and columns exist')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';

    RAISE NOTICE 'Migration 004_comprehensive_schema_sync completed. Total tables: %', table_count;
END $$;

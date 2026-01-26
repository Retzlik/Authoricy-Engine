-- Migration: Add Greenfield Intelligence Support
-- Version: 001
-- Description: Adds greenfield analysis mode, competitor intelligence sessions,
--              winnability scoring, and market opportunity tables.
-- Author: Claude
-- Date: 2026-01-26

-- =============================================================================
-- STEP 1: Create ENUMs
-- =============================================================================

-- Analysis mode enum
DO $$ BEGIN
    CREATE TYPE analysismode AS ENUM ('standard', 'greenfield', 'hybrid');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Competitor purpose enum
DO $$ BEGIN
    CREATE TYPE competitorpurpose AS ENUM (
        'benchmark_peer',
        'keyword_source',
        'link_source',
        'content_model',
        'aspirational'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;


-- =============================================================================
-- STEP 2: Extend analysis_runs Table
-- =============================================================================

-- Add greenfield-specific columns to analysis_runs
ALTER TABLE analysis_runs
ADD COLUMN IF NOT EXISTS analysis_mode analysismode DEFAULT 'standard',
ADD COLUMN IF NOT EXISTS domain_maturity_at_analysis VARCHAR(20),
ADD COLUMN IF NOT EXISTS domain_rating_at_analysis INTEGER,
ADD COLUMN IF NOT EXISTS organic_keywords_at_analysis INTEGER,
ADD COLUMN IF NOT EXISTS organic_traffic_at_analysis INTEGER,
ADD COLUMN IF NOT EXISTS greenfield_context JSONB;

COMMENT ON COLUMN analysis_runs.analysis_mode IS 'Analysis mode: standard, greenfield, or hybrid';
COMMENT ON COLUMN analysis_runs.greenfield_context IS 'User-provided business context for greenfield analysis';


-- =============================================================================
-- STEP 3: Extend keywords Table with Winnability Fields
-- =============================================================================

-- Add winnability and beachhead columns to keywords
ALTER TABLE keywords
ADD COLUMN IF NOT EXISTS winnability_score FLOAT,
ADD COLUMN IF NOT EXISTS winnability_components JSONB,
ADD COLUMN IF NOT EXISTS personalized_difficulty INTEGER,
ADD COLUMN IF NOT EXISTS is_beachhead BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS beachhead_priority INTEGER,
ADD COLUMN IF NOT EXISTS beachhead_score FLOAT,
ADD COLUMN IF NOT EXISTS growth_phase INTEGER,
ADD COLUMN IF NOT EXISTS serp_avg_dr FLOAT,
ADD COLUMN IF NOT EXISTS serp_min_dr INTEGER,
ADD COLUMN IF NOT EXISTS serp_has_low_dr BOOLEAN,
ADD COLUMN IF NOT EXISTS serp_weak_signals JSONB,
ADD COLUMN IF NOT EXISTS has_ai_overview BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS aio_source_count INTEGER,
ADD COLUMN IF NOT EXISTS aio_optimization_potential FLOAT,
ADD COLUMN IF NOT EXISTS source_competitor VARCHAR(255),
ADD COLUMN IF NOT EXISTS competitor_position INTEGER;

-- Create indexes for greenfield queries
CREATE INDEX IF NOT EXISTS idx_keyword_winnability
ON keywords (analysis_run_id, winnability_score DESC);

CREATE INDEX IF NOT EXISTS idx_keyword_beachhead
ON keywords (analysis_run_id, is_beachhead)
WHERE is_beachhead = TRUE;

CREATE INDEX IF NOT EXISTS idx_keyword_growth_phase
ON keywords (analysis_run_id, growth_phase);

COMMENT ON COLUMN keywords.winnability_score IS '0-100 likelihood of ranking based on SERP analysis';
COMMENT ON COLUMN keywords.is_beachhead IS 'High-winnability entry-point keyword';
COMMENT ON COLUMN keywords.growth_phase IS '1=Foundation, 2=Traction, 3=Authority';


-- =============================================================================
-- STEP 4: Create greenfield_analyses Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS greenfield_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES domains(id),

    -- Market Opportunity (TAM/SAM/SOM)
    total_addressable_market INTEGER,
    serviceable_addressable_market INTEGER,
    serviceable_obtainable_market INTEGER,
    tam_keyword_count INTEGER,
    sam_keyword_count INTEGER,
    som_keyword_count INTEGER,

    market_opportunity_score FLOAT,
    competition_intensity FLOAT,

    -- Competitor Landscape
    competitor_count INTEGER,
    avg_competitor_dr FLOAT,
    competitor_dr_range JSONB,
    competitor_traffic_share JSONB,

    -- Beachhead Summary
    beachhead_keyword_count INTEGER,
    total_beachhead_volume INTEGER,
    avg_beachhead_winnability FLOAT,
    beachhead_keywords JSONB,

    -- Traffic Projections
    projection_conservative JSONB,
    projection_expected JSONB,
    projection_aggressive JSONB,

    -- Growth Roadmap
    growth_roadmap JSONB,

    -- Validation
    data_completeness_score FLOAT,
    validation_warnings JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_greenfield_analysis_run
ON greenfield_analyses (analysis_run_id);

CREATE INDEX IF NOT EXISTS idx_greenfield_domain
ON greenfield_analyses (domain_id, created_at DESC);

COMMENT ON TABLE greenfield_analyses IS 'Greenfield-specific analysis results with market opportunity and projections';


-- =============================================================================
-- STEP 5: Create competitor_intelligence_sessions Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_intelligence_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES domains(id),

    -- Session status
    status VARCHAR(30) DEFAULT 'pending',

    -- Phase 1: Context Acquisition
    website_context JSONB,
    business_description TEXT,
    detected_offerings JSONB DEFAULT '[]'::jsonb,
    detected_industry VARCHAR(100),

    -- Phase 2: AI-Powered Discovery
    perplexity_query TEXT,
    perplexity_response JSONB,
    ai_discovered_competitors JSONB DEFAULT '[]'::jsonb,

    -- Phase 3: Multi-Source Aggregation
    serp_discovered_competitors JSONB DEFAULT '[]'::jsonb,
    traffic_share_competitors JSONB DEFAULT '[]'::jsonb,
    user_provided_competitors JSONB DEFAULT '[]'::jsonb,

    -- Candidate pool
    candidate_competitors JSONB DEFAULT '[]'::jsonb,
    candidates_generated_at TIMESTAMP,

    -- Phase 4: User Curation
    curation_started_at TIMESTAMP,
    curation_completed_at TIMESTAMP,
    removed_competitors JSONB DEFAULT '[]'::jsonb,
    added_competitors JSONB DEFAULT '[]'::jsonb,

    -- Phase 5: Final Set
    final_competitors JSONB DEFAULT '[]'::jsonb,
    finalized_at TIMESTAMP,

    -- Cost tracking
    api_calls_count INTEGER DEFAULT 0,
    perplexity_cost_usd FLOAT DEFAULT 0,
    firecrawl_cost_usd FLOAT DEFAULT 0,
    dataforseo_cost_usd FLOAT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ci_session_analysis
ON competitor_intelligence_sessions (analysis_run_id);

CREATE INDEX IF NOT EXISTS idx_ci_session_domain
ON competitor_intelligence_sessions (domain_id);

CREATE INDEX IF NOT EXISTS idx_ci_session_status
ON competitor_intelligence_sessions (status);

COMMENT ON TABLE competitor_intelligence_sessions IS 'Competitor discovery and curation sessions for greenfield analysis';


-- =============================================================================
-- STEP 6: Create greenfield_competitors Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS greenfield_competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES competitor_intelligence_sessions(id) ON DELETE CASCADE,
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,

    -- Competitor identification
    domain VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),

    -- Classification
    purpose competitorpurpose NOT NULL,
    purpose_override competitorpurpose,
    priority INTEGER,

    -- Discovery
    discovery_source VARCHAR(50),
    discovery_reason TEXT,
    relevance_score FLOAT,

    -- Metrics
    domain_rating INTEGER,
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    referring_domains INTEGER,

    -- Relationship to target
    keyword_overlap_count INTEGER,
    keyword_overlap_percent FLOAT,
    traffic_share_percent FLOAT,

    -- Validation
    is_validated BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(30),
    validation_warnings JSONB DEFAULT '[]'::jsonb,

    -- Curation
    is_user_provided BOOLEAN DEFAULT FALSE,
    is_removed BOOLEAN DEFAULT FALSE,
    removal_reason VARCHAR(50),
    removal_note TEXT,

    -- Usage
    keywords_extracted INTEGER DEFAULT 0,
    used_for_market_sizing BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_session_competitor UNIQUE (session_id, domain)
);

CREATE INDEX IF NOT EXISTS idx_gf_competitor_session
ON greenfield_competitors (session_id);

CREATE INDEX IF NOT EXISTS idx_gf_competitor_purpose
ON greenfield_competitors (session_id, purpose);

CREATE INDEX IF NOT EXISTS idx_gf_competitor_removed
ON greenfield_competitors (session_id, is_removed)
WHERE is_removed = FALSE;

COMMENT ON TABLE greenfield_competitors IS 'Individual competitors discovered and curated for greenfield analysis';


-- =============================================================================
-- STEP 7: Create Function for Updated Timestamp
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to competitor_intelligence_sessions
DROP TRIGGER IF EXISTS update_ci_sessions_updated_at ON competitor_intelligence_sessions;
CREATE TRIGGER update_ci_sessions_updated_at
    BEFORE UPDATE ON competitor_intelligence_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to greenfield_competitors
DROP TRIGGER IF EXISTS update_gf_competitors_updated_at ON greenfield_competitors;
CREATE TRIGGER update_gf_competitors_updated_at
    BEFORE UPDATE ON greenfield_competitors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- STEP 8: Migration Version Tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_migrations (version, description)
VALUES ('001_add_greenfield_support', 'Add greenfield analysis mode, competitor intelligence, winnability scoring')
ON CONFLICT (version) DO NOTHING;


-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Verify all tables were created
DO $$
BEGIN
    ASSERT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'greenfield_analyses'),
        'greenfield_analyses table not created';
    ASSERT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'competitor_intelligence_sessions'),
        'competitor_intelligence_sessions table not created';
    ASSERT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'greenfield_competitors'),
        'greenfield_competitors table not created';

    RAISE NOTICE 'Migration 001_add_greenfield_support completed successfully';
END $$;

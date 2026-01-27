-- Migration: 002_caching_infrastructure
-- Description: Adds caching support tables, materialized views, and covering indexes
-- for high-performance dashboard delivery.
--
-- Expected Performance Improvements:
-- - Dashboard load: 2-5s → <500ms (10x faster)
-- - Keywords table: 1-3s → <300ms (5-10x faster)
-- - Sparkline queries: 500ms → <50ms (10x faster)
--
-- Run with: psql -d authoricy -f migrations/002_caching_infrastructure.sql

BEGIN;

-- =============================================================================
-- PRECOMPUTED DASHBOARD TABLE
-- =============================================================================

-- This table stores precomputed dashboard data for instant retrieval
-- Data is computed once after analysis completion, not on every page load
CREATE TABLE IF NOT EXISTS precomputed_dashboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id),
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id),

    -- Data type: overview, sparklines, sov, battleground, clusters, etc.
    data_type VARCHAR(50) NOT NULL,

    -- The precomputed JSON data
    data JSONB NOT NULL,

    -- Metadata
    version INTEGER DEFAULT 1,
    size_bytes INTEGER,
    computation_time_ms INTEGER,

    -- Validity
    valid_until TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,

    -- ETag for HTTP caching
    etag VARCHAR(64),

    created_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint: one record per analysis + data_type
    CONSTRAINT uq_precomputed_analysis_type UNIQUE (analysis_run_id, data_type)
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_precomputed_domain_type
    ON precomputed_dashboard(domain_id, data_type, is_current);
CREATE INDEX IF NOT EXISTS idx_precomputed_analysis
    ON precomputed_dashboard(analysis_run_id);

-- =============================================================================
-- CACHE METRICS LOG TABLE
-- =============================================================================

-- Stores cache performance metrics for monitoring and alerting
CREATE TABLE IF NOT EXISTS cache_metrics_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Time window
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,

    -- Hit/miss statistics
    hits INTEGER DEFAULT 0,
    misses INTEGER DEFAULT 0,
    hit_rate FLOAT,

    -- Latency (milliseconds)
    avg_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    p99_latency_ms FLOAT,

    -- Memory usage (MB)
    memory_used_mb FLOAT,
    memory_peak_mb FLOAT,

    -- Throughput
    bytes_read BIGINT DEFAULT 0,
    bytes_written BIGINT DEFAULT 0,
    bytes_saved_compression BIGINT DEFAULT 0,

    -- Errors
    errors INTEGER DEFAULT 0,
    error_rate FLOAT,

    -- Circuit breaker state
    circuit_breaker_triggered BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_cache_metrics_time ON cache_metrics_log(recorded_at);

-- =============================================================================
-- COVERING INDEXES FOR DASHBOARD QUERIES
-- =============================================================================

-- Keywords covering index for dashboard queries
-- This allows PostgreSQL to serve dashboard keyword aggregations from the index
-- without reading the main table (index-only scans)
CREATE INDEX IF NOT EXISTS idx_keywords_dashboard
    ON keywords(analysis_run_id, search_volume DESC, current_position ASC)
    INCLUDE (keyword, keyword_difficulty, opportunity_score, estimated_traffic, position_change);

-- Keywords by opportunity for quick wins queries
CREATE INDEX IF NOT EXISTS idx_keywords_quick_wins
    ON keywords(analysis_run_id, opportunity_score DESC)
    WHERE opportunity_score >= 70 AND current_position BETWEEN 11 AND 30;

-- Keywords at risk
CREATE INDEX IF NOT EXISTS idx_keywords_at_risk
    ON keywords(analysis_run_id, position_change)
    WHERE position_change < -3 AND current_position <= 20;

-- Ranking history for sparklines
CREATE INDEX IF NOT EXISTS idx_ranking_sparklines
    ON ranking_history(domain_id, keyword_normalized, recorded_at DESC)
    INCLUDE (position, position_change);

-- Domain metrics history for trends
CREATE INDEX IF NOT EXISTS idx_metrics_history_trends
    ON domain_metrics_history(domain_id, recorded_at DESC)
    INCLUDE (organic_traffic, organic_keywords, domain_rating);

-- Competitors for SOV calculations
CREATE INDEX IF NOT EXISTS idx_competitors_sov
    ON competitors(analysis_run_id, competitor_type, is_active)
    INCLUDE (organic_traffic, organic_keywords, avg_position)
    WHERE competitor_type = 'true_competitor' AND is_active = TRUE;

-- Content clusters for topical authority
CREATE INDEX IF NOT EXISTS idx_clusters_authority
    ON content_clusters(analysis_run_id, topical_authority_score DESC)
    INCLUDE (cluster_name, total_keywords, content_gap_count);

-- Pages for content audit (KUCK)
CREATE INDEX IF NOT EXISTS idx_pages_kuck
    ON pages(analysis_run_id, kuck_recommendation)
    INCLUDE (url, title, organic_traffic, decay_score);

-- Keyword gaps for battleground/attack opportunities
CREATE INDEX IF NOT EXISTS idx_gaps_opportunity
    ON keyword_gaps(analysis_run_id, opportunity_score DESC)
    INCLUDE (keyword, search_volume, target_position, best_competitor_position);

-- =============================================================================
-- MATERIALIZED VIEW: Dashboard Overview
-- =============================================================================

-- This materialized view pre-aggregates dashboard overview data
-- Refresh after each analysis completion

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_overview AS
SELECT
    ar.id AS analysis_run_id,
    ar.domain_id,
    ar.completed_at,

    -- Keyword counts
    COUNT(k.id) AS total_keywords,
    COUNT(k.id) FILTER (WHERE k.current_position <= 3) AS pos_top_3,
    COUNT(k.id) FILTER (WHERE k.current_position BETWEEN 4 AND 10) AS pos_4_10,
    COUNT(k.id) FILTER (WHERE k.current_position BETWEEN 11 AND 20) AS pos_11_20,
    COUNT(k.id) FILTER (WHERE k.current_position BETWEEN 21 AND 50) AS pos_21_50,
    COUNT(k.id) FILTER (WHERE k.current_position > 50) AS pos_51_plus,

    -- Quick wins
    COUNT(k.id) FILTER (
        WHERE k.opportunity_score >= 70
        AND k.current_position BETWEEN 11 AND 30
    ) AS quick_wins,

    -- At risk
    COUNT(k.id) FILTER (
        WHERE k.position_change < -3
        AND k.current_position <= 20
    ) AS at_risk_keywords,

    -- Averages
    AVG(k.opportunity_score) AS avg_opportunity_score,
    SUM(k.estimated_traffic) AS total_traffic,

    -- Metrics from history
    dmh.organic_traffic,
    dmh.organic_keywords AS tracked_keywords,
    dmh.domain_rating,
    dmh.referring_domains,
    dmh.backlinks_total,

    -- Technical scores
    tm.performance_score,
    tm.seo_score AS technical_seo_score,

    -- Content gaps
    (SELECT COUNT(*) FROM keyword_gaps kg
     WHERE kg.analysis_run_id = ar.id AND kg.target_position IS NULL) AS content_gaps,

    -- AI mentions
    (SELECT COUNT(*) FROM ai_visibility av
     WHERE av.analysis_run_id = ar.id AND av.is_mentioned = TRUE) AS ai_mentions

FROM analysis_runs ar
LEFT JOIN keywords k ON k.analysis_run_id = ar.id
LEFT JOIN domain_metrics_history dmh ON dmh.analysis_run_id = ar.id
LEFT JOIN technical_metrics tm ON tm.analysis_run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.id, ar.domain_id, ar.completed_at,
         dmh.organic_traffic, dmh.organic_keywords, dmh.domain_rating,
         dmh.referring_domains, dmh.backlinks_total,
         tm.performance_score, tm.seo_score;

-- Index for the materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dashboard_overview_pk
    ON mv_dashboard_overview(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_mv_dashboard_overview_domain
    ON mv_dashboard_overview(domain_id);

-- =============================================================================
-- MATERIALIZED VIEW: Share of Voice
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_share_of_voice AS
SELECT
    ar.id AS analysis_run_id,
    ar.domain_id,
    d.domain AS domain_name,

    -- Target domain stats
    SUM(k.estimated_traffic) FILTER (WHERE k.current_position <= 20) AS target_traffic,
    COUNT(k.id) FILTER (WHERE k.current_position <= 20) AS target_keyword_count,
    AVG(k.current_position) FILTER (WHERE k.current_position <= 20) AS target_avg_position,

    -- Competitor stats (as JSON array)
    (
        SELECT json_agg(json_build_object(
            'domain', c.competitor_domain,
            'traffic', c.organic_traffic,
            'keywords', c.organic_keywords,
            'avg_position', c.avg_position
        ))
        FROM competitors c
        WHERE c.analysis_run_id = ar.id
        AND c.competitor_type = 'true_competitor'
        AND c.is_active = TRUE
        LIMIT 10
    ) AS competitor_stats

FROM analysis_runs ar
JOIN domains d ON d.id = ar.domain_id
LEFT JOIN keywords k ON k.analysis_run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.id, ar.domain_id, d.domain;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sov_pk
    ON mv_share_of_voice(analysis_run_id);

-- =============================================================================
-- FUNCTION: Refresh Materialized Views
-- =============================================================================

-- Call this function after analysis completion to refresh all dashboard views
CREATE OR REPLACE FUNCTION refresh_dashboard_views(p_analysis_id UUID)
RETURNS void AS $$
BEGIN
    -- Refresh overview (concurrent allows reads during refresh)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_overview;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_share_of_voice;

    RAISE NOTICE 'Refreshed materialized views for analysis %', p_analysis_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- FUNCTION: Get Precomputed Dashboard Data
-- =============================================================================

-- Fast lookup function for precomputed dashboard data
CREATE OR REPLACE FUNCTION get_precomputed_dashboard(
    p_domain_id UUID,
    p_data_type VARCHAR(50)
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT pd.data INTO result
    FROM precomputed_dashboard pd
    JOIN analysis_runs ar ON ar.id = pd.analysis_run_id
    WHERE ar.domain_id = p_domain_id
    AND ar.status = 'completed'
    AND pd.data_type = p_data_type
    AND pd.is_current = TRUE
    ORDER BY ar.completed_at DESC
    LIMIT 1;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGER: Auto-invalidate on new analysis
-- =============================================================================

-- When a new analysis completes, mark old precomputed data as not current
CREATE OR REPLACE FUNCTION invalidate_precomputed_on_analysis_complete()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE precomputed_dashboard
        SET is_current = FALSE
        WHERE domain_id = NEW.domain_id
        AND analysis_run_id != NEW.id;

        RAISE NOTICE 'Invalidated precomputed cache for domain %', NEW.domain_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_invalidate_precomputed ON analysis_runs;
CREATE TRIGGER trg_invalidate_precomputed
    AFTER UPDATE ON analysis_runs
    FOR EACH ROW
    EXECUTE FUNCTION invalidate_precomputed_on_analysis_complete();

-- =============================================================================
-- VACUUM AND ANALYZE
-- =============================================================================

-- Ensure statistics are up to date for query planner
ANALYZE keywords;
ANALYZE ranking_history;
ANALYZE domain_metrics_history;
ANALYZE competitors;
ANALYZE content_clusters;
ANALYZE pages;
ANALYZE keyword_gaps;
ANALYZE precomputed_dashboard;

COMMIT;

-- =============================================================================
-- USAGE NOTES
-- =============================================================================
--
-- After running this migration:
--
-- 1. Materialized views are automatically refreshed when calling:
--    SELECT refresh_dashboard_views(analysis_id);
--
-- 2. Precomputed data is looked up with:
--    SELECT get_precomputed_dashboard(domain_id, 'overview');
--    SELECT get_precomputed_dashboard(domain_id, 'sparklines');
--
-- 3. The trigger automatically invalidates old cache when new analysis completes
--
-- 4. Monitor index usage with:
--    SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
--    FROM pg_stat_user_indexes
--    WHERE schemaname = 'public'
--    ORDER BY idx_scan DESC;
--
-- 5. Check materialized view freshness:
--    SELECT * FROM pg_stat_user_tables
--    WHERE relname LIKE 'mv_%';

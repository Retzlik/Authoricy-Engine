-- Migration: 005_add_curation_metrics
-- Description: Add curation_metrics JSONB column to analysis_runs for tracking user curation behavior
-- Safe to run multiple times (idempotent)
-- Created: 2026-02-02

BEGIN;

-- =============================================================================
-- ADD CURATION_METRICS COLUMN TO ANALYSIS_RUNS
-- =============================================================================

-- Add curation_metrics column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'analysis_runs'
        AND column_name = 'curation_metrics'
    ) THEN
        ALTER TABLE analysis_runs ADD COLUMN curation_metrics JSONB;
        COMMENT ON COLUMN analysis_runs.curation_metrics IS 'Tracks user curation behavior: removals_count, additions_count, purpose_overrides_count, curated_at, mode';
        RAISE NOTICE 'Added curation_metrics column to analysis_runs';
    ELSE
        RAISE NOTICE 'curation_metrics column already exists in analysis_runs';
    END IF;
END $$;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Verify the column was added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'analysis_runs'
        AND column_name = 'curation_metrics'
    ) THEN
        RAISE NOTICE 'Migration 005 verified: curation_metrics column exists';
    ELSE
        RAISE EXCEPTION 'Migration 005 FAILED: curation_metrics column not found';
    END IF;
END $$;

COMMIT;

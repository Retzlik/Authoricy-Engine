-- Migration: Add Authentication Tables
-- Description: Creates users table and adds user_id to domains for Supabase Auth integration
-- Created: 2026-01-27

-- =============================================================================
-- USER ROLE ENUM
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
        CREATE TYPE userrole AS ENUM ('user', 'admin');
    END IF;
END
$$;

-- =============================================================================
-- USERS TABLE
-- =============================================================================
-- Synced from Supabase Auth. The id matches Supabase auth.users.id

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,  -- Matches Supabase auth.users.id
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

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_role ON users(role);

-- =============================================================================
-- ADD USER_ID TO DOMAINS
-- =============================================================================

-- Add user_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'domains' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE domains ADD COLUMN user_id UUID REFERENCES users(id);
    END IF;
END
$$;

-- Add unique constraint for user_id + domain (one domain per user)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_user_domain'
    ) THEN
        ALTER TABLE domains ADD CONSTRAINT uq_user_domain UNIQUE (user_id, domain);
    END IF;
END
$$;

-- Add index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_domain_user ON domains(user_id);

-- =============================================================================
-- HELPER FUNCTION: Updated timestamp trigger
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE users IS 'User accounts synced from Supabase Auth. ID matches Supabase auth.users.id';
COMMENT ON COLUMN users.id IS 'UUID from Supabase auth.users.id';
COMMENT ON COLUMN users.role IS 'Local role for RBAC - user (own domains) or admin (all domains)';
COMMENT ON COLUMN users.is_active IS 'Can be disabled without deleting Supabase account';
COMMENT ON COLUMN users.synced_at IS 'Last time user data was synced from Supabase JWT';
COMMENT ON COLUMN domains.user_id IS 'Owner of this domain (from Supabase Auth)';

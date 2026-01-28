# Authoricy Frontend Specification

> **Version:** 2.0
> **Last Updated:** 2026-01-27
> **Purpose:** Complete specification for frontend implementation to ensure perfect alignment with backend

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Authentication Flow](#2-authentication-flow)
3. [Analysis Flows (TWO PATHS)](#3-analysis-flows-two-paths)
4. [API Endpoints Reference](#4-api-endpoints-reference)
5. [Data Models](#5-data-models)
6. [Caching Strategy](#6-caching-strategy)
7. [UI States & User Flows](#7-ui-states--user-flows)
8. [Environment Configuration](#8-environment-configuration)

---

## 1. System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  React + Vite + TypeScript + React Query + Supabase Auth        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS + JWT
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND API                                 │
│  FastAPI + PostgreSQL + DataForSEO + Claude AI                  │
│  URL: https://authoricy-engine-production.up.railway.app        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ JWT Validation
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SUPABASE AUTH                                 │
│  Project: jhnwazpdsrusxxkxrrqh.supabase.co                      │
│  Handles: Login, Signup, OAuth, Password Reset                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **TWO Analysis Paths** - Standard for established domains, Greenfield for new domains
2. **Supabase for Auth Only** - All data comes from our backend API
3. **JWT in Every Request** - Backend validates Supabase JWT
4. **Domain Ownership** - Users only see their own domains (unless admin)
5. **Precomputed Cache** - Dashboard data is precomputed after analysis

---

## 2. Authentication Flow

### 2.1 Login/Signup (Supabase)

The frontend handles authentication directly with Supabase:

```typescript
// Initialize Supabase client
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,      // https://jhnwazpdsrusxxkxrrqh.supabase.co
  import.meta.env.VITE_SUPABASE_ANON_KEY  // Your anon key
)

// Login
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password'
})

// OAuth (Google, GitHub, etc.)
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google'
})

// Get current session
const { data: { session } } = await supabase.auth.getSession()
const jwt = session?.access_token  // This JWT goes to our backend
```

### 2.2 API Requests (Our Backend)

Every request to our backend API must include the Supabase JWT:

```typescript
// API client wrapper
async function apiClient(endpoint: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session?.access_token) {
    throw new Error('Not authenticated')
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
      ...options.headers,
    },
  })

  if (response.status === 401) {
    await supabase.auth.signOut()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API Error: ${response.status}`)
  }

  return response.json()
}
```

### 2.3 User Roles

| Role | Permissions |
|------|-------------|
| `USER` | View/manage own domains only |
| `ADMIN` | View/manage all domains, manage users |

---

## 3. Analysis Flows (TWO PATHS)

> **CRITICAL:** The system has TWO analysis paths based on domain maturity.

### 3.1 Decision Flow: Which Path?

```
┌─────────────────────────────────────────────────────────────────┐
│ User wants to analyze a domain                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Check Domain Maturity                                    │
│                                                                  │
│ GET /api/greenfield/maturity/{domain}                           │
│ (Public endpoint - no auth required)                             │
│                                                                  │
│ Response:                                                        │
│ {                                                                │
│   "maturity": "greenfield" | "emerging" | "established",        │
│   "domain_rating": 5,                                            │
│   "organic_keywords": 50,                                        │
│   "organic_traffic": 100,                                        │
│   "requires_greenfield": true | false                            │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ requires_greenfield:    │     │ requires_greenfield:    │
│        TRUE             │     │        FALSE            │
│                         │     │                         │
│ → GREENFIELD PATH       │     │ → STANDARD PATH         │
│   (new/weak domains)    │     │   (established domains) │
└─────────────────────────┘     └─────────────────────────┘
```

### 3.2 Maturity Thresholds

| Metric | Greenfield | Emerging | Established |
|--------|------------|----------|-------------|
| Domain Rating | 0-10 | 11-30 | 31+ |
| Organic Keywords | 0-100 | 101-1000 | 1001+ |
| Organic Traffic | 0-500 | 501-5000 | 5001+ |

**Decision Rule:** `requires_greenfield = true` if maturity is "greenfield" or "emerging"

---

### 3.3 PATH A: Standard Analysis (Established Domains)

For domains with DR > 30 or keywords > 1000.

**Endpoint:** `POST /api/analyze`

```typescript
interface StandardAnalysisRequest {
  // REQUIRED
  domain: string              // e.g., "example.com"
  email: string               // User's email for report delivery

  // OPTIONAL - Business Context
  company_name?: string
  primary_market?: string     // "se", "us", "uk", "de", etc.
  primary_goal?: 'traffic' | 'leads' | 'authority' | 'balanced'
  primary_language?: string   // "en", "sv", "de", etc.
  secondary_markets?: string[]
  known_competitors?: string[]

  // OPTIONAL - Analysis Configuration
  collection_depth?: 'testing' | 'basic' | 'balanced' | 'comprehensive' | 'enterprise'
  skip_ai_analysis?: boolean
  skip_context_intelligence?: boolean
  max_seed_keywords?: number  // 1-100
}
```

**Response:**
```typescript
interface StandardAnalysisResponse {
  job_id: string      // UUID[:8] for tracking
  domain: string
  email: string
  status: 'pending'
  message: string
}
```

**Flow:**
```
POST /api/analyze
       │
       ▼
Poll GET /api/jobs/{job_id} every 10 seconds
       │
       ├── status: "pending" or "running" → keep polling
       │
       └── status: "completed" → Redirect to dashboard
           OR
           status: "failed" → Show error
```

---

### 3.4 PATH B: Greenfield Analysis (New/Weak Domains)

For domains with DR < 30 and keywords < 1000. **This is a multi-step flow with user interaction.**

#### Step 1: Start Greenfield Analysis

**Endpoint:** `POST /api/greenfield/analyze`

```typescript
interface GreenfieldAnalysisRequest {
  // REQUIRED
  domain: string
  business_name: string
  business_description: string
  primary_offering: string
  target_market: string       // "United States", "Sweden", etc.

  // OPTIONAL
  industry_vertical?: string
  seed_keywords?: string[]    // Keywords you want to target
  known_competitors?: string[]
  target_audience?: string
}
```

**Response:**
```typescript
interface GreenfieldStartResponse {
  analysis_run_id: string     // UUID
  session_id: string          // Competitor session UUID
  status: 'awaiting_curation'
  message: string
  next_step: string           // "/api/greenfield/sessions/{session_id}"
}
```

#### Step 2: Get Competitor Candidates (Auto-discovered)

**Endpoint:** `GET /api/greenfield/sessions/{session_id}`

```typescript
interface CompetitorSession {
  session_id: string
  analysis_run_id: string
  status: 'awaiting_curation' | 'curated' | 'completed'
  candidates: CompetitorCandidate[]
  candidates_count: number
  required_removals: number   // How many must be removed
  min_final_count: number     // Minimum competitors needed
  max_final_count: number     // Maximum competitors allowed
}

interface CompetitorCandidate {
  domain: string
  discovery_source: 'perplexity' | 'serp' | 'traffic_share' | 'user_provided'
  domain_rating: number
  organic_traffic: number
  organic_keywords: number
  relevance_score: number     // 0-1
  suggested_purpose: string   // 'benchmark_peer', 'keyword_source', etc.
  discovery_reason: string
}
```

#### Step 3: User Curates Competitors

**Endpoint:** `POST /api/greenfield/sessions/{session_id}/curate`

```typescript
interface CurationInput {
  removals: Array<{
    domain: string
    reason: 'not_relevant' | 'too_large' | 'too_small' | 'different_market' | 'other'
    note?: string
  }>
  additions: Array<{
    domain: string
    purpose?: string
  }>
  purpose_overrides: Array<{
    domain: string
    new_purpose: 'benchmark_peer' | 'keyword_source' | 'link_source' | 'content_model' | 'aspirational'
  }>
}
```

**Response:**
```typescript
interface CurationResponse {
  session_id: string
  status: 'curated' | 'completed'
  final_competitors: FinalCompetitor[]
  competitor_count: number
  removed_count: number
  added_count: number
  finalized_at: string
}
```

#### Step 4: View Greenfield Dashboard

After curation, the analysis continues in background. Dashboard becomes available.

**Endpoint:** `GET /api/greenfield/dashboard/{analysis_run_id}`

```typescript
interface GreenfieldDashboard {
  domain: string
  analysis_run_id: string
  maturity: 'greenfield' | 'emerging'

  // Competitors
  competitors: FinalCompetitor[]
  competitor_count: number

  // Market opportunity (TAM/SAM/SOM)
  market_opportunity: {
    total_addressable_market: number
    serviceable_addressable_market: number
    serviceable_obtainable_market: number
    market_opportunity_score: number
    competition_intensity: number
  }

  // Beachhead keywords (easiest to win)
  beachhead_keywords: BeachheadKeyword[]
  beachhead_count: number
  total_beachhead_volume: number
  avg_winnability: number

  // Traffic projections
  traffic_projections: {
    conservative: TrafficScenario
    expected: TrafficScenario
    aggressive: TrafficScenario
  }

  // Growth roadmap
  growth_roadmap: GrowthPhase[]
}
```

---

### 3.5 Complete Greenfield Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. POST /api/greenfield/analyze                                  │
│    → Returns analysis_run_id + session_id                        │
│    → Status: "awaiting_curation"                                 │
│    → Discovers competitors (smart auto-curation: max 15)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. GET /api/greenfield/sessions/{session_id}                     │
│    → Returns max 15 pre-curated competitor candidates            │
│    → Tiered: benchmarks, keyword_sources, market_intel           │
│    → User reviews and optionally removes/adds                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. POST /api/greenfield/sessions/{session_id}/curate             │
│    → Validates final count (3-15 competitors)                    │
│    → Saves curation decisions                                    │
│    → AUTOMATICALLY TRIGGERS DEEP ANALYSIS (G2-G5):               │
│      • Keyword mining from competitors                           │
│      • SERP analysis & winnability scoring                       │
│      • Market sizing (TAM/SAM/SOM)                               │
│      • Beachhead selection & roadmap                             │
│    → Returns curation result + analysis status                   │
│    → Response includes: analysis_status, keywords_count, etc.    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. GET /api/greenfield/dashboard/{analysis_run_id}               │
│    → Full greenfield dashboard with beachheads, projections      │
│    → Dashboard is immediately ready after step 3 completes       │
└─────────────────────────────────────────────────────────────────┘
```

**Important:** The /curate endpoint now automatically triggers deep analysis.
No separate call is needed. The endpoint will take longer to respond (30-60s)
as it runs the full keyword mining and analysis pipeline.

---

## 4. API Endpoints Reference

### 4.1 Health & Status

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Basic health check |
| GET | `/api/health` | No | Detailed health with DB status |
| GET | `/api/database` | No | Database status (debug) |

### 4.2 Domain Maturity (Pre-Analysis)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/greenfield/maturity/{domain}` | **No** | Check if domain needs greenfield flow |

### 4.3 Standard Analysis

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/analyze` | Optional* | Trigger standard analysis |
| GET | `/api/jobs/{job_id}` | No | Get job status |

*Analysis can be triggered without auth (email required), but domain ownership requires auth.

### 4.4 Greenfield Analysis

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/greenfield/analyze` | **Yes** | Start greenfield analysis |
| POST | `/api/greenfield/sessions` | **Yes** | Create competitor session |
| GET | `/api/greenfield/sessions/{session_id}` | **Yes** | Get session with candidates |
| POST | `/api/greenfield/sessions/{session_id}/curate` | **Yes** | Submit curation decisions |
| PATCH | `/api/greenfield/sessions/{session_id}/competitors` | **Yes** | Update competitors post-curation |

### 4.5 Greenfield Dashboard

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/greenfield/dashboard/{analysis_run_id}` | **Yes** | Full greenfield dashboard |
| GET | `/api/greenfield/dashboard/{analysis_run_id}/beachheads` | **Yes** | Beachhead keywords |
| GET | `/api/greenfield/dashboard/{analysis_run_id}/market-map` | **Yes** | Market opportunity sizing |
| GET | `/api/greenfield/dashboard/{analysis_run_id}/projections` | **Yes** | Traffic projections |
| GET | `/api/greenfield/dashboard/{analysis_run_id}/roadmap` | **Yes** | Growth roadmap |
| PATCH | `/api/greenfield/keywords/{keyword_id}/phase` | **Yes** | Update keyword phase |

### 4.6 Standard Dashboard (Established Domains)

| Method | Endpoint | Auth | Cache | Description |
|--------|----------|------|-------|-------------|
| GET | `/api/dashboard/{domain_id}/bundle` | **Yes** | 5 min | **ALL dashboard data in one request** |
| GET | `/api/dashboard/{domain_id}/overview` | **Yes** | 4 hours | Health scores, metrics |
| GET | `/api/dashboard/{domain_id}/sov` | **Yes** | 8 hours | Share of Voice |
| GET | `/api/dashboard/{domain_id}/sparklines` | **Yes** | 6 hours | Position trends |
| GET | `/api/dashboard/{domain_id}/battleground` | **Yes** | 8 hours | Attack/Defend keywords |
| GET | `/api/dashboard/{domain_id}/clusters` | **Yes** | 12 hours | Topical authority |
| GET | `/api/dashboard/{domain_id}/content-audit` | **Yes** | 12 hours | KUCK recommendations |
| GET | `/api/dashboard/{domain_id}/opportunities` | **Yes** | 8 hours | Ranked opportunities |
| GET | `/api/dashboard/{domain_id}/intelligence-summary` | **Yes** | 24 hours | AI summary |

**Bundle Endpoint (Recommended):**
```
GET /api/dashboard/{domain_id}/bundle?include=overview,sparklines,sov,battleground,clusters,content_audit,opportunities
```

### 4.7 Domains

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/domains` | **Yes** | List user's domains |
| GET | `/api/domains/{domain_id}` | **Yes** | Get single domain |
| GET | `/api/domains/{domain_id}/analyses` | **Yes** | List past analyses |

### 4.8 Strategy Builder

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/domains/{domain_id}/strategies` | **Yes** | List strategies |
| POST | `/api/strategies` | **Yes** | Create strategy |
| GET | `/api/strategies/{id}` | **Yes** | Get strategy |
| PATCH | `/api/strategies/{id}` | **Yes** | Update strategy |
| DELETE | `/api/strategies/{id}` | **Yes** | Delete strategy |
| POST | `/api/strategies/{id}/duplicate` | **Yes** | Duplicate strategy |
| POST | `/api/strategies/{id}/archive` | **Yes** | Archive strategy |
| POST | `/api/strategies/{id}/restore` | **Yes** | Restore strategy |
| GET | `/api/strategies/{id}/threads` | **Yes** | List threads |
| POST | `/api/strategies/{id}/threads` | **Yes** | Create thread |
| PATCH | `/api/threads/{id}` | **Yes** | Update thread |
| POST | `/api/threads/{id}/move` | **Yes** | Reorder thread |
| DELETE | `/api/threads/{id}` | **Yes** | Delete thread |
| GET | `/api/threads/{id}/keywords` | **Yes** | Get thread keywords |
| POST | `/api/threads/{id}/keywords` | **Yes** | Assign keywords |
| DELETE | `/api/threads/{id}/keywords` | **Yes** | Remove keywords |
| GET | `/api/strategies/{id}/available-keywords` | **Yes** | Unassigned keywords |
| GET | `/api/strategies/{id}/suggested-clusters` | **Yes** | AI-suggested clusters |
| POST | `/api/strategies/{id}/assign-cluster` | **Yes** | Assign cluster to thread |
| POST | `/api/strategies/{id}/keywords/batch-move` | **Yes** | Batch move keywords |
| GET | `/api/threads/{id}/topics` | **Yes** | List topics |
| POST | `/api/threads/{id}/topics` | **Yes** | Create topic |
| PATCH | `/api/topics/{id}` | **Yes** | Update topic |
| POST | `/api/topics/{id}/move` | **Yes** | Reorder topic |
| POST | `/api/topics/{id}/move-to-thread` | **Yes** | Move to different thread |
| DELETE | `/api/topics/{id}` | **Yes** | Delete topic |
| GET | `/api/keywords/{id}/format-recommendation` | **Yes** | Get format recommendation |
| POST | `/api/strategies/{id}/validate-export` | **Yes** | Validate before export |
| POST | `/api/strategies/{id}/export` | **Yes** | Export strategy |
| GET | `/api/strategies/{id}/exports` | **Yes** | Export history |
| GET | `/api/exports/{id}/download` | **Yes** | Download export file |
| GET | `/api/strategies/{id}/activity` | **Yes** | Activity log |

### 4.9 Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/users/me` | **Yes** | Current user profile |
| PATCH | `/api/users/me` | **Yes** | Update profile |
| GET | `/api/users` | **Admin** | List all users |
| GET | `/api/users/{id}` | **Admin** | Get user by ID |
| PATCH | `/api/users/{id}/role` | **Admin** | Change role |
| DELETE | `/api/users/{id}` | **Admin** | Delete user |
| POST | `/api/users/{id}/enable` | **Admin** | Enable user |

### 4.10 Cache Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/cache/health` | No | Cache health check |
| GET | `/api/cache/stats` | No | Cache statistics |
| POST | `/api/cache/invalidate/domain/{id}` | **Admin** | Clear domain cache |
| POST | `/api/cache/invalidate/analysis/{id}` | **Admin** | Clear analysis cache |
| POST | `/api/cache/invalidate/all` | **Admin** | Clear ALL cache (emergency) |
| POST | `/api/cache/precompute/{analysis_id}` | **Admin** | Manually trigger precomputation |
| POST | `/api/cache/warm/domain/{domain_id}` | **Admin** | Warm cache for domain |

---

## 5. Data Models

### 5.1 Core Entities

```typescript
// Domain - The website being analyzed
interface Domain {
  id: string
  user_id: string
  domain: string
  display_name?: string
  industry?: string
  business_type?: 'ecommerce' | 'saas' | 'local' | 'media'
  target_market?: string
  primary_language?: string
  is_active: boolean
  analysis_count: number
  first_analyzed_at?: string
  last_analyzed_at?: string
  created_at: string
  updated_at: string
}

// AnalysisRun - Each analysis execution
interface AnalysisRun {
  id: string
  domain_id: string
  status: 'pending' | 'collecting' | 'validating' | 'analyzing' | 'generating' | 'completed' | 'failed'
  analysis_mode: 'standard' | 'greenfield' | 'hybrid'
  current_phase?: string
  progress_percent: number
  data_quality?: 'excellent' | 'good' | 'fair' | 'poor' | 'invalid'
  started_at?: string
  completed_at?: string
  error_message?: string
}

// Keyword
interface Keyword {
  id: string
  keyword: string
  search_volume: number
  keyword_difficulty: number
  current_position?: number
  previous_position?: number
  estimated_traffic?: number
  search_intent: 'informational' | 'navigational' | 'transactional' | 'commercial'
  opportunity_score: number
  // Greenfield-specific
  winnability_score?: number
  beachhead_priority?: number
  growth_phase?: 1 | 2 | 3
}

// Competitor
interface Competitor {
  id: string
  competitor_domain: string
  competitor_type: 'true_competitor' | 'affiliate' | 'media' | 'government' | 'platform'
  organic_traffic: number
  organic_keywords: number
  domain_rating: number
  keyword_overlap_count: number
  threat_level: 'low' | 'medium' | 'high' | 'critical'
}

// FinalCompetitor (Greenfield)
interface FinalCompetitor {
  domain: string
  display_name?: string
  purpose: 'benchmark_peer' | 'keyword_source' | 'link_source' | 'content_model' | 'aspirational'
  priority: number
  domain_rating: number
  organic_traffic: number
  organic_keywords: number
  keyword_overlap: number
  is_user_provided: boolean
  is_user_curated: boolean
}
```

### 5.2 Greenfield-Specific Models

```typescript
// Beachhead Keyword
interface BeachheadKeyword {
  keyword: string
  search_volume: number
  winnability_score: number      // 0-100, higher = easier to win
  personalized_difficulty: number
  keyword_difficulty: number
  beachhead_priority: number     // 1 = top priority
  growth_phase: 1 | 2 | 3        // 1=Foundation, 2=Traction, 3=Authority
  has_ai_overview: boolean
  estimated_traffic: number
  recommended_content_type: string
}

// Traffic Projection Scenario
interface TrafficScenario {
  scenario: 'conservative' | 'expected' | 'aggressive'
  confidence: number
  month_3: number
  month_6: number
  month_12: number
  month_18: number
  month_24: number
}

// Growth Phase
interface GrowthPhase {
  phase: string
  phase_number: 1 | 2 | 3
  months: string
  focus: string
  strategy: string
  keyword_count: number
  total_volume: number
  expected_traffic: number
}
```

### 5.3 Strategy Builder Entities

```typescript
// Strategy
interface Strategy {
  id: string
  domain_id: string
  analysis_run_id: string
  name: string
  description?: string
  status: 'draft' | 'approved' | 'archived'
  version: number  // For optimistic locking
  is_archived: boolean
}

// Thread (Topic cluster)
interface StrategyThread {
  id: string
  strategy_id: string
  name: string
  position: string  // Lexicographic ordering
  status: 'draft' | 'confirmed' | 'rejected'
  priority: number  // 1-5
  version: number
  // Aggregated metrics
  total_search_volume?: number
  keyword_count?: number
}

// Topic (Content piece)
interface StrategyTopic {
  id: string
  thread_id: string
  name: string
  position: string
  primary_keyword_id?: string
  primary_keyword?: string
  content_type: 'pillar' | 'cluster' | 'supporting'
  status: 'draft' | 'confirmed' | 'in_production' | 'published'
  target_url?: string
}
```

---

## 6. Caching Strategy

### 6.1 React Query Configuration

```typescript
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,    // 5 minutes default
      gcTime: 30 * 60 * 1000,       // 30 minutes garbage collection
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

// Cache times by data type (match backend TTLs)
export const CACHE_TIMES = {
  // Dashboard - precomputed, stable
  DASHBOARD_BUNDLE: 5 * 60 * 1000,        // 5 min
  DASHBOARD_OVERVIEW: 4 * 60 * 60 * 1000, // 4 hours
  SPARKLINES: 6 * 60 * 60 * 1000,         // 6 hours
  SOV: 8 * 60 * 60 * 1000,                // 8 hours
  BATTLEGROUND: 8 * 60 * 60 * 1000,       // 8 hours
  CLUSTERS: 12 * 60 * 60 * 1000,          // 12 hours
  CONTENT_AUDIT: 12 * 60 * 60 * 1000,     // 12 hours
  AI_SUMMARY: 24 * 60 * 60 * 1000,        // 24 hours

  // Greenfield dashboard
  GREENFIELD_DASHBOARD: 5 * 60 * 1000,    // 5 min
  BEACHHEADS: 10 * 60 * 1000,             // 10 min
  PROJECTIONS: 30 * 60 * 1000,            // 30 min

  // Strategy - user edits, volatile
  STRATEGY: 10 * 60 * 1000,               // 10 min
  THREAD_KEYWORDS: 5 * 60 * 1000,         // 5 min
  AVAILABLE_KEYWORDS: 5 * 60 * 1000,      // 5 min

  // Real-time
  JOB_STATUS: 0,                          // No cache, always fresh
  COMPETITOR_SESSION: 30 * 1000,          // 30 seconds

  // Static
  DOMAIN_LIST: 30 * 60 * 1000,            // 30 min
  DOMAIN_MATURITY: 60 * 60 * 1000,        // 1 hour (rarely changes)
}
```

### 6.2 Query Key Structure

```typescript
const queryKeys = {
  // Domain maturity (pre-analysis)
  maturity: (domain: string) => ['maturity', domain],

  // Domains
  domains: ['domains'],
  domain: (id: string) => ['domain', id],
  domainAnalyses: (domainId: string) => ['domain', domainId, 'analyses'],

  // Standard Dashboard
  dashboardBundle: (domainId: string) => ['dashboard', domainId, 'bundle'],
  dashboardOverview: (domainId: string) => ['dashboard', domainId, 'overview'],
  // ... etc

  // Greenfield
  greenfieldSession: (sessionId: string) => ['greenfield', 'session', sessionId],
  greenfieldDashboard: (analysisRunId: string) => ['greenfield', 'dashboard', analysisRunId],
  greenfieldBeachheads: (analysisRunId: string) => ['greenfield', 'beachheads', analysisRunId],
  greenfieldProjections: (analysisRunId: string) => ['greenfield', 'projections', analysisRunId],
  greenfieldRoadmap: (analysisRunId: string) => ['greenfield', 'roadmap', analysisRunId],

  // Jobs
  jobStatus: (jobId: string) => ['job', jobId],

  // Strategy
  strategies: (domainId: string) => ['strategies', domainId],
  strategy: (id: string) => ['strategy', id],
  strategyThreads: (strategyId: string) => ['strategy', strategyId, 'threads'],
  threadKeywords: (threadId: string) => ['thread', threadId, 'keywords'],
  availableKeywords: (strategyId: string) => ['strategy', strategyId, 'available-keywords'],

  // User
  currentUser: ['user', 'me'],
}
```

---

## 7. UI States & User Flows

### 7.1 Application Routes

```typescript
const routes = {
  // Public
  '/login': 'Login page',
  '/signup': 'Signup page',

  // Authenticated
  '/': 'Redirect to /domains',
  '/domains': 'Domain list',
  '/analyze': 'New analysis (shows maturity check first)',

  // Standard Dashboard
  '/dashboard/:domainId': 'Dashboard overview',
  '/dashboard/:domainId/keywords': 'Keywords table',
  '/dashboard/:domainId/competitors': 'Competitor analysis',
  '/dashboard/:domainId/content': 'Content audit',

  // Greenfield Flow
  '/greenfield/analyze': 'Start greenfield analysis',
  '/greenfield/curate/:sessionId': 'Competitor curation',
  '/greenfield/dashboard/:analysisRunId': 'Greenfield dashboard',

  // Strategy Builder
  '/strategy/:domainId': 'Strategy list',
  '/strategy/:domainId/:strategyId': 'Strategy detail',

  // Admin
  '/admin/users': 'User management',
}
```

### 7.2 New Analysis Flow (Start Page)

```
┌─────────────────────────────────────────────────────────────────┐
│ Enter Domain: [_____________________]                           │
│                                                                  │
│ [Check Domain]                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Checking domain maturity...                                      │
│ GET /api/greenfield/maturity/{domain}                           │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ GREENFIELD DETECTED     │     │ ESTABLISHED DOMAIN      │
│                         │     │                         │
│ DR: 8, Keywords: 50     │     │ DR: 45, Keywords: 5000  │
│                         │     │                         │
│ "This is a new domain.  │     │ "Ready for full         │
│  We'll help you find    │     │  analysis."             │
│  the best opportunities │     │                         │
│  to compete."           │     │                         │
│                         │     │                         │
│ [Start Greenfield] →    │     │ [Run Analysis] →        │
│ /greenfield/analyze     │     │ Standard form           │
└─────────────────────────┘     └─────────────────────────┘
```

### 7.3 Greenfield Curation Page

```
┌─────────────────────────────────────────────────────────────────┐
│ Competitor Curation                                              │
│                                                                  │
│ We found 15 potential competitors. Remove at least 5.            │
│ Final set should be 5-10 competitors.                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ☑️ competitor1.com          DR: 35  Traffic: 50K                 │
│    "Direct competitor in same market"                            │
│    Purpose: [Benchmark Peer ▼]    [Remove]                      │
│                                                                  │
│ ☑️ competitor2.com          DR: 28  Traffic: 30K                 │
│    "Found via SERP overlap"                                      │
│    Purpose: [Keyword Source ▼]    [Remove]                      │
│                                                                  │
│ ☐ facebook.com             DR: 100  Traffic: 5B                 │
│    "Too large, not a real competitor"                            │
│    [REMOVED - not relevant]                                      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Add Competitor: [_______________] [Add]                          │
├─────────────────────────────────────────────────────────────────┤
│ Selected: 8 competitors    [Finalize & Continue]                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Environment Configuration

### 8.1 Required Environment Variables

```env
# Supabase (Authentication)
VITE_SUPABASE_URL=https://jhnwazpdsrusxxkxrrqh.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here

# Backend API
VITE_API_URL=https://authoricy-engine-production.up.railway.app

# Optional
VITE_APP_ENV=production
```

### 8.2 API Client Setup

```typescript
// src/lib/api.ts
import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL

export async function apiClient<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    await supabase.auth.signOut()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API Error: ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
```

---

## Summary: Key Decision Points for Frontend

1. **First: Check Maturity** - Always call `GET /api/greenfield/maturity/{domain}` before starting analysis
2. **Route Based on Maturity:**
   - `requires_greenfield: true` → Greenfield flow with competitor curation
   - `requires_greenfield: false` → Standard flow with single API call
3. **Standard Dashboard vs Greenfield Dashboard:**
   - Standard: `/api/dashboard/{domain_id}/bundle`
   - Greenfield: `/api/greenfield/dashboard/{analysis_run_id}`
4. **JWT Required** for all endpoints except:
   - Health checks
   - `/api/greenfield/maturity/{domain}`
   - `/api/jobs/{job_id}`

---

## Appendix: Error Responses

```typescript
interface APIError {
  detail: string
  code?: string
  field?: string
}

// HTTP Status Codes
// 400 - Bad Request (validation error)
// 401 - Unauthorized (missing/invalid token)
// 403 - Forbidden (authenticated but not authorized)
// 404 - Not Found
// 409 - Conflict (version mismatch)
// 422 - Unprocessable Entity
// 500 - Internal Server Error
```

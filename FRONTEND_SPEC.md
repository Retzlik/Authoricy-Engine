# Authoricy Frontend Specification

> **Version:** 1.0
> **Last Updated:** 2026-01-27
> **Purpose:** Complete specification for frontend implementation to ensure perfect alignment with backend

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Authentication Flow](#2-authentication-flow)
3. [Analysis Flow (SINGLE FLOW)](#3-analysis-flow-single-flow)
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

1. **ONE Analysis Flow** - There is only ONE way to trigger analysis
2. **Supabase for Auth Only** - All data comes from our backend API
3. **JWT in Every Request** - Backend validates Supabase JWT
4. **Domain Ownership** - Users only see their own domains (unless admin)
5. **Precomputed Cache** - Dashboard data is precomputed, not computed on request

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
    // Token expired - redirect to login
    await supabase.auth.signOut()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (response.status === 403) {
    throw new Error('Access denied')
  }

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }

  return response.json()
}
```

### 2.3 Auth State Management

```typescript
// Listen for auth changes
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'SIGNED_IN') {
    // User logged in - fetch their domains
    queryClient.invalidateQueries(['domains'])
  }

  if (event === 'SIGNED_OUT') {
    // Clear all cached data
    queryClient.clear()
  }

  if (event === 'TOKEN_REFRESHED') {
    // Supabase automatically refreshes tokens
    // No action needed - next API call will use new token
  }
})
```

### 2.4 User Roles

| Role | Permissions |
|------|-------------|
| `USER` | View/manage own domains only |
| `ADMIN` | View/manage all domains, manage users |

The backend automatically assigns roles. Admin emails are configured server-side.

---

## 3. Analysis Flow (SINGLE FLOW)

> **CRITICAL:** There is only ONE analysis flow. Do NOT implement multiple flows.

### 3.1 The Single Analysis Endpoint

```
POST /api/analyze
```

This is the ONLY endpoint to trigger analysis. Period.

### 3.2 Request Payload

```typescript
interface AnalysisRequest {
  // REQUIRED
  domain: string              // e.g., "example.com" (no https://, no www.)
  email: string               // User's email for report delivery

  // OPTIONAL - Business Context
  company_name?: string       // Company display name
  primary_market?: string     // "se", "us", "uk", "de", etc.
  primary_goal?: 'traffic' | 'leads' | 'authority' | 'balanced'
  primary_language?: string   // "en", "sv", "de", etc.
  secondary_markets?: string[] // Additional markets to analyze
  known_competitors?: string[] // User-provided competitors

  // OPTIONAL - Analysis Configuration
  collection_depth?: 'testing' | 'basic' | 'balanced' | 'comprehensive' | 'enterprise'
  skip_ai_analysis?: boolean   // Skip Claude AI analysis (faster, cheaper)
  skip_context_intelligence?: boolean  // Skip market/competitor discovery
  priority?: 'normal' | 'high'
  max_seed_keywords?: number   // 1-100
}
```

### 3.3 Response

```typescript
interface AnalysisResponse {
  job_id: string      // UUID[:8] for tracking, e.g., "a1b2c3d4"
  domain: string      // Normalized domain
  email: string       // Where report will be sent
  status: 'pending'   // Always starts as pending
  message: string     // "Analysis started. You'll receive results at..."
}
```

### 3.4 Complete Analysis Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: User Clicks "Run Analysis"                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Frontend Sends POST /api/analyze                        │
│                                                                  │
│ Request:                                                         │
│ {                                                                │
│   "domain": "example.com",                                       │
│   "email": "user@example.com",                                   │
│   "primary_market": "us",                                        │
│   "primary_goal": "traffic",                                     │
│   "collection_depth": "balanced"                                 │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Backend Returns Immediately (~1 second)                  │
│                                                                  │
│ Response:                                                        │
│ {                                                                │
│   "job_id": "a1b2c3d4",                                         │
│   "domain": "example.com",                                       │
│   "status": "pending",                                           │
│   "message": "Analysis started..."                               │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Frontend Polls GET /api/jobs/{job_id}                   │
│                                                                  │
│ Poll every 10 seconds until status != "running"                  │
│                                                                  │
│ Possible statuses:                                               │
│ - "pending"   → Show "Starting analysis..."                      │
│ - "running"   → Show progress indicator                          │
│ - "completed" → Show success, link to dashboard                  │
│ - "failed"    → Show error message                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: On "completed" - Redirect to Dashboard                   │
│                                                                  │
│ GET /api/domains → Find the domain that was just analyzed        │
│ Navigate to /dashboard/{domain_id}                               │
│                                                                  │
│ The dashboard data is already precomputed and cached!            │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 Polling Implementation

```typescript
// React Query polling example
function useAnalysisStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['analysis', 'status', jobId],
    queryFn: () => apiClient(`/api/jobs/${jobId}`),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Stop polling when complete or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 10000 // Poll every 10 seconds
    },
  })
}
```

### 3.6 Analysis Status Response

```typescript
interface JobStatus {
  job_id: string
  domain: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string | null   // ISO timestamp
  completed_at: string | null // ISO timestamp
  error: string | null        // Error message if failed
}
```

### 3.7 What Happens During Analysis (Backend)

| Phase | Duration | What Happens |
|-------|----------|--------------|
| Context Intelligence | 40-60s | Market detection, competitor discovery |
| Data Collection | 120-300s | DataForSEO API calls (keywords, backlinks, etc.) |
| Quality Validation | 10-20s | Data quality checks |
| AI Analysis | 120-180s | Claude AI 4-loop analysis |
| Report Generation | 30-60s | PDF creation |
| Email Delivery | 30s | Send report via Resend |
| Cache Precomputation | 5s | Prepare dashboard cache |

**Total: ~8-12 minutes** for balanced depth.

### 3.8 After Analysis Completes

1. User receives email with PDF report
2. Domain appears in their domain list
3. Dashboard shows precomputed data (instant load)
4. Strategy Builder becomes available for that domain

---

## 4. API Endpoints Reference

### 4.1 Domains

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/domains` | Required | List user's domains |
| GET | `/api/domains/{domain_id}` | Required | Get single domain |

**Response: Domain List**
```typescript
interface Domain {
  id: string           // UUID
  domain: string       // "example.com"
  display_name: string
  industry?: string
  business_type?: string
  target_market?: string
  is_active: boolean
  analysis_count: number
  first_analyzed_at?: string
  last_analyzed_at?: string
  created_at: string
}
```

### 4.2 Dashboard (Primary Data Source)

> **IMPORTANT:** Use the bundle endpoint to fetch all dashboard data in ONE request.

| Method | Endpoint | Auth | Cache | Description |
|--------|----------|------|-------|-------------|
| GET | `/api/dashboard/{domain_id}/bundle` | Required | 5 min | **ALL dashboard data** |
| GET | `/api/dashboard/{domain_id}/overview` | Required | 4 hours | Health scores, metrics |
| GET | `/api/dashboard/{domain_id}/sparklines` | Required | 6 hours | Position trends |
| GET | `/api/dashboard/{domain_id}/sov` | Required | 8 hours | Share of Voice |
| GET | `/api/dashboard/{domain_id}/battleground` | Required | 8 hours | Attack/Defend keywords |
| GET | `/api/dashboard/{domain_id}/clusters` | Required | 12 hours | Topical authority |
| GET | `/api/dashboard/{domain_id}/content-audit` | Required | 12 hours | KUCK recommendations |
| GET | `/api/dashboard/{domain_id}/opportunities` | Required | 8 hours | Ranked opportunities |
| GET | `/api/dashboard/{domain_id}/intelligence-summary` | Required | 24 hours | AI summary |

**Bundle Endpoint (RECOMMENDED):**
```
GET /api/dashboard/{domain_id}/bundle?include=overview,sparklines,sov,battleground,clusters,content_audit,opportunities
```

This returns all components in ONE request instead of 7 separate calls.

**Bundle Response:**
```typescript
interface DashboardBundle {
  overview: DashboardOverview
  sparklines: SparklineData
  sov: ShareOfVoiceData
  battleground: BattlegroundData
  clusters: ClusterData
  content_audit: ContentAuditData
  opportunities: OpportunityData
  cached_at: string
  analysis_id: string
}
```

### 4.3 Dashboard Data Types

**Overview:**
```typescript
interface DashboardOverview {
  health_scores: {
    overall: number        // 0-100
    technical: number
    content: number
    authority: number
  }
  metrics: {
    organic_traffic: number
    organic_keywords: number
    domain_rating: number
    referring_domains: number
    // Each has: value, change, change_percent
  }
  position_distribution: {
    pos_1: number
    pos_2_3: number
    pos_4_10: number
    pos_11_20: number
    pos_21_50: number
    pos_51_100: number
  }
  quick_stats: {
    keywords_improved: number
    keywords_declined: number
    new_keywords: number
    lost_keywords: number
  }
}
```

**Share of Voice:**
```typescript
interface ShareOfVoiceData {
  target_share: number      // Your share %
  total_market_traffic: number
  competitors: Array<{
    domain: string
    traffic: number
    share_percent: number
    keyword_count: number
  }>
}
```

**Battleground:**
```typescript
interface BattlegroundData {
  attack: {
    easy: Keyword[]    // Low difficulty, competitors rank
    hard: Keyword[]    // High difficulty, big opportunity
  }
  defend: {
    priority: Keyword[]  // Your keywords at risk
    watch: Keyword[]     // Monitor these
  }
}
```

**Sparklines:**
```typescript
interface SparklineData {
  keywords: Array<{
    keyword: string
    keyword_id: string
    positions: Array<{
      date: string      // ISO date
      position: number  // 1-100
    }>
    current_position: number
    trend: 'up' | 'down' | 'stable'
  }>
}
```

### 4.4 Analysis

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/analyze` | Optional* | Trigger analysis |
| GET | `/api/jobs/{job_id}` | None | Get job status |
| GET | `/api/domains/{domain_id}/analyses` | Required | List past analyses |

*Analysis can be triggered without auth (email required), but domain ownership requires auth.

### 4.5 Strategy Builder

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/domains/{domain_id}/strategies` | Required | List strategies |
| POST | `/api/strategies` | Required | Create strategy |
| GET | `/api/strategies/{id}` | Required | Get strategy |
| PATCH | `/api/strategies/{id}` | Required | Update strategy |
| DELETE | `/api/strategies/{id}` | Required | Delete strategy |
| GET | `/api/strategies/{id}/threads` | Required | List threads |
| POST | `/api/strategies/{id}/threads` | Required | Create thread |
| PATCH | `/api/threads/{id}` | Required | Update thread |
| DELETE | `/api/threads/{id}` | Required | Delete thread |
| GET | `/api/threads/{id}/keywords` | Required | Get thread keywords |
| POST | `/api/threads/{id}/keywords` | Required | Assign keywords |
| DELETE | `/api/threads/{id}/keywords` | Required | Remove keywords |
| GET | `/api/strategies/{id}/available-keywords` | Required | Unassigned keywords |
| POST | `/api/strategies/{id}/export` | Required | Export strategy |

### 4.6 User Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/users/me` | Required | Current user profile |
| PATCH | `/api/users/me` | Required | Update profile |
| GET | `/api/users` | Admin | List all users |
| PATCH | `/api/users/{id}/role` | Admin | Change user role |

### 4.7 Cache Management (Admin)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/cache/health` | None | Cache health check |
| GET | `/api/cache/stats` | None | Cache statistics |
| POST | `/api/cache/invalidate/domain/{id}` | Admin | Clear domain cache |

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
  current_phase?: string
  progress_percent: number
  data_quality?: 'excellent' | 'good' | 'fair' | 'poor' | 'invalid'
  data_quality_score?: number
  started_at?: string
  completed_at?: string
  duration_seconds?: number
  error_message?: string
}

// Keyword - SEO keyword data
interface Keyword {
  id: string
  keyword: string
  search_volume: number
  keyword_difficulty: number
  cpc?: number
  current_position?: number
  previous_position?: number
  ranking_url?: string
  estimated_traffic?: number
  search_intent: 'informational' | 'navigational' | 'transactional' | 'commercial'
  opportunity_score: number
  cluster_name?: string
}

// Competitor - Domain-level competitor
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
```

### 5.2 Strategy Builder Entities

```typescript
// Strategy - Content strategy container
interface Strategy {
  id: string
  domain_id: string
  analysis_run_id: string
  name: string
  description?: string
  status: 'draft' | 'approved' | 'archived'
  version: number  // For optimistic locking
  is_archived: boolean
  created_at: string
  updated_at: string
}

// Thread - Topic cluster within strategy
interface StrategyThread {
  id: string
  strategy_id: string
  name: string
  position: string  // Lexicographic ordering
  status: 'draft' | 'confirmed' | 'rejected'
  priority: number  // 1-5
  version: number
  // Aggregated metrics from keywords
  total_search_volume?: number
  total_traffic?: number
  avg_difficulty?: number
  keyword_count?: number
}

// Topic - Content piece within thread
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
  version: number
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
      refetchOnWindowFocus: false,  // Don't refetch on tab focus
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

  // Strategy - user edits, volatile
  STRATEGY: 10 * 60 * 1000,               // 10 min
  THREAD_KEYWORDS: 5 * 60 * 1000,         // 5 min
  AVAILABLE_KEYWORDS: 5 * 60 * 1000,      // 5 min

  // Real-time
  ANALYSIS_STATUS: 5 * 1000,              // 5 seconds

  // Static
  DOMAIN_LIST: 30 * 60 * 1000,            // 30 min
}
```

### 6.2 Query Key Structure

```typescript
// Consistent query key patterns
const queryKeys = {
  // Domains
  domains: ['domains'],
  domain: (id: string) => ['domain', id],

  // Dashboard
  dashboardBundle: (domainId: string) => ['dashboard', domainId, 'bundle'],
  dashboardOverview: (domainId: string) => ['dashboard', domainId, 'overview'],
  dashboardSparklines: (domainId: string) => ['dashboard', domainId, 'sparklines'],
  dashboardSov: (domainId: string) => ['dashboard', domainId, 'sov'],
  dashboardBattleground: (domainId: string) => ['dashboard', domainId, 'battleground'],
  dashboardClusters: (domainId: string) => ['dashboard', domainId, 'clusters'],
  dashboardContentAudit: (domainId: string) => ['dashboard', domainId, 'content-audit'],
  dashboardOpportunities: (domainId: string) => ['dashboard', domainId, 'opportunities'],

  // Analysis
  analysisStatus: (jobId: string) => ['analysis', 'status', jobId],
  analysisHistory: (domainId: string) => ['analysis', 'history', domainId],

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

### 6.3 Cache Invalidation

```typescript
// When analysis completes
function onAnalysisComplete(domainId: string) {
  queryClient.invalidateQueries(['domains'])
  queryClient.invalidateQueries(['dashboard', domainId])
  queryClient.invalidateQueries(['analysis', 'history', domainId])
}

// When strategy is updated
function onStrategyUpdate(strategyId: string, domainId: string) {
  queryClient.invalidateQueries(['strategy', strategyId])
  queryClient.invalidateQueries(['strategies', domainId])
}

// When user logs out
function onLogout() {
  queryClient.clear()
}
```

### 6.4 ETag Support (Optional Enhancement)

```typescript
// For conditional requests - saves bandwidth
async function fetchWithEtag(endpoint: string, cachedEtag?: string) {
  const headers: HeadersInit = {}

  if (cachedEtag) {
    headers['If-None-Match'] = cachedEtag
  }

  const response = await apiClient(endpoint, { headers })

  if (response.status === 304) {
    // Data unchanged - use cached version
    return null
  }

  const etag = response.headers.get('etag')
  const data = await response.json()

  return { data, etag }
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
  '/domains/new': 'Add new domain / Run analysis',
  '/dashboard/:domainId': 'Dashboard overview',
  '/dashboard/:domainId/keywords': 'Keywords table',
  '/dashboard/:domainId/competitors': 'Competitor analysis',
  '/dashboard/:domainId/backlinks': 'Backlink analysis',
  '/dashboard/:domainId/content': 'Content audit',
  '/dashboard/:domainId/opportunities': 'Opportunities list',
  '/strategy/:domainId': 'Strategy builder',
  '/strategy/:domainId/:strategyId': 'Strategy detail',

  // Admin
  '/admin/users': 'User management',
}
```

### 7.2 Domain List Page

**State: Loading**
```
Show skeleton loaders for domain cards
```

**State: Empty (No domains)**
```
"No domains yet"
"Run your first SEO analysis to get started"
[Run Analysis] button
```

**State: Has Domains**
```
List of domain cards showing:
- Domain name
- Last analyzed date
- Health score (if available)
- Quick metrics (traffic, keywords, DR)
[View Dashboard] button per domain
[Run New Analysis] button (global)
```

### 7.3 Run Analysis Page

**Step 1: Enter Domain**
```
Input: Domain URL
- Normalize input (strip https://, www., trailing slash)
- Validate format

Input: Email (pre-filled if logged in)
```

**Step 2: Configure (Optional)**
```
Select: Primary Market (dropdown: US, UK, SE, DE, etc.)
Select: Primary Goal (Traffic, Leads, Authority, Balanced)
Select: Collection Depth (Basic, Balanced, Comprehensive)
Input: Known Competitors (optional, comma-separated)
```

**Step 3: Confirm & Start**
```
[Run Analysis] button
- POST /api/analyze
- Store job_id
- Navigate to analysis progress view
```

**Step 4: Progress View**
```
While status === 'pending' || status === 'running':
  Show progress indicator
  Show estimated time remaining
  Poll GET /api/jobs/{job_id} every 10 seconds

When status === 'completed':
  Show success message
  [View Dashboard] button

When status === 'failed':
  Show error message
  [Try Again] button
```

### 7.4 Dashboard Page

**Initial Load:**
```typescript
// Fetch all dashboard data in one request
const { data: bundle } = useQuery({
  queryKey: ['dashboard', domainId, 'bundle'],
  queryFn: () => apiClient(
    `/api/dashboard/${domainId}/bundle?include=overview,sparklines,sov,battleground,clusters,content_audit,opportunities`
  ),
  staleTime: CACHE_TIMES.DASHBOARD_BUNDLE,
})
```

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: Domain Name + Last Analyzed + [Run New Analysis]        │
├─────────────────────────────────────────────────────────────────┤
│ Health Scores: Overall | Technical | Content | Authority        │
├───────────────────────────────┬─────────────────────────────────┤
│ Metrics Grid:                 │ Position Distribution Chart     │
│ - Organic Traffic (+ change)  │ (Pie/Bar chart of pos 1-100)    │
│ - Keywords (+ change)         │                                  │
│ - Domain Rating               │                                  │
│ - Referring Domains           │                                  │
├───────────────────────────────┴─────────────────────────────────┤
│ Quick Stats: Improved | Declined | New | Lost                   │
├─────────────────────────────────────────────────────────────────┤
│ Share of Voice (Bar chart: you vs competitors)                  │
├───────────────────────────────┬─────────────────────────────────┤
│ Attack Keywords               │ Defend Keywords                  │
│ (Easy wins from competitors)  │ (Your keywords at risk)          │
├───────────────────────────────┴─────────────────────────────────┤
│ Top Keywords with Sparklines (30-day position trends)           │
├─────────────────────────────────────────────────────────────────┤
│ Topical Clusters (Authority by topic)                           │
├─────────────────────────────────────────────────────────────────┤
│ Top Opportunities (Ranked by impact/effort)                     │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5 Strategy Builder

**Create Strategy:**
```
1. Select domain
2. Select analysis run (defaults to latest)
3. Enter strategy name
4. POST /api/strategies
```

**Thread Management:**
```
- Drag & drop to reorder threads
- Click to expand/collapse
- Assign keywords from available pool
- Set priority (1-5)
- Add custom instructions
```

**Keyword Assignment:**
```
Left panel: Available keywords (not yet assigned)
  - Filter by search volume, difficulty, intent
  - Search by keyword text
  - Select multiple

Right panel: Thread keywords
  - Drag & drop to reorder
  - Remove assignments
  - View metrics summary
```

**Export:**
```
POST /api/strategies/{id}/export
Format: CSV, Excel, JSON, HTML
Downloads file with threads, topics, keywords
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

### 8.2 Supabase Client Setup

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 8.3 API Client Setup

```typescript
// src/lib/api.ts
import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL

if (!API_URL) {
  throw new Error('Missing API URL environment variable')
}

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

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
```

---

## Summary: Key Points for Frontend

1. **ONE Analysis Endpoint**: `POST /api/analyze` - no other way to trigger analysis
2. **Use Bundle Endpoint**: `GET /api/dashboard/{id}/bundle` - one request, all data
3. **JWT in Every Request**: Get from Supabase, send to our backend
4. **Poll for Status**: `GET /api/jobs/{job_id}` every 10 seconds
5. **Match Cache TTLs**: React Query staleTime should match backend TTLs
6. **Domain Ownership**: Users only see their own domains
7. **Strategy Version Locking**: Always send `version` field when updating

---

## Appendix: Error Responses

```typescript
// Standard error format
interface APIError {
  detail: string
  // Optional additional fields
  code?: string
  field?: string
}

// HTTP Status Codes
// 400 - Bad Request (validation error)
// 401 - Unauthorized (missing/invalid token)
// 403 - Forbidden (authenticated but not authorized)
// 404 - Not Found (resource doesn't exist)
// 409 - Conflict (version mismatch for optimistic locking)
// 422 - Unprocessable Entity (semantic validation error)
// 500 - Internal Server Error
```

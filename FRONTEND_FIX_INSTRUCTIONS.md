# Frontend Fix Instructions

> **VERIFIED AGAINST BACKEND:** 2026-01-27
> **All endpoints below have been confirmed to exist in the backend codebase**

---

## CRITICAL FINDING: Missing Backend Endpoint

**The backend is MISSING a `GET /api/domains` endpoint to list user's domains.**

This needs to be added to the backend, OR the frontend needs to work around it by:
- Getting domains from the user profile
- Using `GET /api/domains/{domain_id}/analyses` for known domain IDs

---

## VERIFIED BACKEND ENDPOINTS

### Health & Status (No Auth Required)
```
GET  /                              → Health check
GET  /api/health                    → Detailed health with DB status
GET  /api/database                  → Database debug info
```

### Domain Maturity Check (No Auth Required)
```
GET  /api/greenfield/maturity/{domain}
     → Response: {
         domain: string,
         maturity: "greenfield" | "emerging" | "established",
         domain_rating: number,
         organic_keywords: number,
         organic_traffic: number,
         requires_greenfield: boolean,
         message: string
       }
```

### Standard Analysis (Email required, Auth optional)
```
POST /api/analyze
     → Request Body: {
         domain: string,           // REQUIRED
         email: string,            // REQUIRED (EmailStr)
         company_name?: string,
         primary_market?: string,  // "se", "us", "uk", "de"
         primary_goal?: "traffic" | "leads" | "authority" | "balanced",
         primary_language?: string,
         secondary_markets?: string[],
         known_competitors?: string[],
         skip_ai_analysis?: boolean,
         skip_context_intelligence?: boolean,
         collection_depth?: "testing" | "basic" | "balanced" | "comprehensive" | "enterprise",
         max_seed_keywords?: number  // 1-100
       }
     → Response: {
         job_id: string,           // UUID[:8]
         domain: string,
         email: string,
         status: "pending",
         message: string
       }

GET  /api/jobs/{job_id}            // No auth required
     → Response: {
         job_id: string,
         domain: string,
         status: "pending" | "running" | "completed" | "failed",
         started_at?: string,
         completed_at?: string,
         error?: string
       }
```

### Greenfield Analysis (Auth Required)
```
POST /api/greenfield/analyze
     → Request Body: {
         domain: string,                    // REQUIRED
         business_name: string,             // REQUIRED
         business_description: string,      // REQUIRED
         primary_offering: string,          // REQUIRED
         target_market: string,             // Default: "United States"
         industry_vertical?: string,        // Default: "saas"
         seed_keywords: string[],           // REQUIRED, min 5 items
         known_competitors: string[],       // REQUIRED, min 3 items
         target_audience?: string,
         email?: string
       }
     → Response: {
         analysis_run_id: string,
         session_id: string,
         status: "awaiting_curation",
         message: string,
         next_step: string
       }
```

### Competitor Intelligence Sessions (Auth Required)
```
POST /api/greenfield/sessions
     → Query Params: analysis_run_id (UUID)
     → Query Params: seed_keywords (List[str])
     → Query Params: known_competitors (List[str])
     → Response: {
         session_id: string,
         analysis_run_id: string,
         status: "awaiting_curation",
         candidates: CompetitorCandidate[],
         candidates_count: number,
         required_removals: number,
         min_final_count: 8,
         max_final_count: 10,
         created_at: string
       }

GET  /api/greenfield/sessions/{session_id}
     → Response: Session data with candidates

POST /api/greenfield/sessions/{session_id}/curate
     → Request Body: {
         removals: Array<{
           domain: string,
           reason: "not_relevant" | "too_large" | "too_small" | "different_market" | "other",
           note?: string
         }>,
         additions: Array<{
           domain: string,
           purpose?: string
         }>,
         purpose_overrides: Array<{
           domain: string,
           new_purpose: "benchmark_peer" | "keyword_source" | "link_source" | "content_model" | "aspirational"
         }>
       }
     → Response: {
         session_id: string,
         status: "curated" | "completed",
         final_competitors: FinalCompetitor[],
         competitor_count: number,
         removed_count: number,
         added_count: number,
         finalized_at?: string
       }

PATCH /api/greenfield/sessions/{session_id}/competitors
      → Request Body: Same as curate (for post-finalization updates)
```

### Greenfield Dashboard (Auth Required)
```
GET  /api/greenfield/dashboard/{analysis_run_id}
     → Full dashboard with competitors, market opportunity, beachheads, projections, roadmap

GET  /api/greenfield/dashboard/{analysis_run_id}/beachheads
     → Query: phase (int), min_winnability (float)

GET  /api/greenfield/dashboard/{analysis_run_id}/market-map

GET  /api/greenfield/dashboard/{analysis_run_id}/projections

GET  /api/greenfield/dashboard/{analysis_run_id}/roadmap

PATCH /api/greenfield/keywords/{keyword_id}/phase
      → Request Body: { phase: 1 | 2 | 3 }
```

### Standard Dashboard (Auth Required)
```
GET  /api/dashboard/{domain_id}/bundle
     → Query: include (comma-separated: overview,sparklines,sov,battleground,clusters,content_audit,opportunities)
     → Returns all requested components in one response

GET  /api/dashboard/{domain_id}/overview
GET  /api/dashboard/{domain_id}/sov
GET  /api/dashboard/{domain_id}/sparklines
GET  /api/dashboard/{domain_id}/battleground
GET  /api/dashboard/{domain_id}/clusters
GET  /api/dashboard/{domain_id}/content-audit
GET  /api/dashboard/{domain_id}/intelligence-summary
GET  /api/dashboard/{domain_id}/opportunities
```

### Strategy Builder (Auth Required)
```
GET    /api/domains/{domain_id}/strategies
GET    /api/domains/{domain_id}/analyses
POST   /api/strategies
GET    /api/strategies/{strategy_id}
PATCH  /api/strategies/{strategy_id}
DELETE /api/strategies/{strategy_id}
POST   /api/strategies/{strategy_id}/duplicate
POST   /api/strategies/{strategy_id}/archive
POST   /api/strategies/{strategy_id}/restore
GET    /api/strategies/{strategy_id}/threads
POST   /api/strategies/{strategy_id}/threads
PATCH  /api/threads/{thread_id}
POST   /api/threads/{thread_id}/move
DELETE /api/threads/{thread_id}
GET    /api/threads/{thread_id}/keywords
POST   /api/threads/{thread_id}/keywords
DELETE /api/threads/{thread_id}/keywords
GET    /api/strategies/{strategy_id}/available-keywords
GET    /api/strategies/{strategy_id}/suggested-clusters
POST   /api/strategies/{strategy_id}/assign-cluster
POST   /api/strategies/{strategy_id}/keywords/batch-move
GET    /api/threads/{thread_id}/topics
POST   /api/threads/{thread_id}/topics
PATCH  /api/topics/{topic_id}
POST   /api/topics/{topic_id}/move
POST   /api/topics/{topic_id}/move-to-thread
DELETE /api/topics/{topic_id}
GET    /api/keywords/{keyword_id}/format-recommendation
POST   /api/strategies/{strategy_id}/validate-export
POST   /api/strategies/{strategy_id}/export
GET    /api/strategies/{strategy_id}/exports
GET    /api/exports/{export_id}/download
GET    /api/strategies/{strategy_id}/activity
```

### Users (Auth Required)
```
GET    /api/users/me
PATCH  /api/users/me
GET    /api/users           (Admin only)
GET    /api/users/{user_id} (Admin only)
PATCH  /api/users/{user_id}/role (Admin only)
DELETE /api/users/{user_id} (Admin only)
POST   /api/users/{user_id}/enable (Admin only)
```

### Cache Management
```
GET    /api/cache/health                           (No auth)
GET    /api/cache/stats                            (No auth)
POST   /api/cache/invalidate/domain/{domain_id}    (Admin only)
POST   /api/cache/invalidate/analysis/{analysis_id} (Admin only)
POST   /api/cache/invalidate/all                   (Admin only)
POST   /api/cache/precompute/{analysis_id}         (Admin only)
POST   /api/cache/warm/domain/{domain_id}          (Admin only)
```

---

## FIXES REQUIRED IN FRONTEND

### Fix 1: Domain Maturity Check - Replace Mock with Real API

**File:** `src/components/onboarding/DomainEntryStep.tsx` (or similar)

**WRONG (Current):**
```typescript
// TODO: Replace with actual API call for maturity detection
setTimeout(() => {
  setDetectedMaturity('greenfield');  // ALWAYS greenfield - WRONG!
}, 1500);
```

**CORRECT:**
```typescript
const checkDomainMaturity = async (domain: string) => {
  setIsChecking(true);
  try {
    // Normalize domain
    const normalized = domain
      .toLowerCase()
      .replace(/^https?:\/\//, '')
      .replace(/^www\./, '')
      .replace(/\/$/, '');

    // Real API call - NO AUTH REQUIRED
    const response = await fetch(
      `${import.meta.env.VITE_API_URL}/api/greenfield/maturity/${encodeURIComponent(normalized)}`
    );

    if (!response.ok) throw new Error('Failed to check domain');

    const data = await response.json();

    setDetectedMaturity(data.maturity);
    setRequiresGreenfield(data.requires_greenfield);
    setDomainMetrics({
      domainRating: data.domain_rating,
      organicKeywords: data.organic_keywords,
      organicTraffic: data.organic_traffic,
    });
  } catch (error) {
    console.error('Maturity check failed:', error);
    // Fallback to greenfield on error
    setDetectedMaturity('greenfield');
    setRequiresGreenfield(true);
  } finally {
    setIsChecking(false);
  }
};
```

---

### Fix 2: Analysis Endpoints - Complete Rewrite

**File:** `src/lib/api.ts`

**DELETE these wrong endpoints:**
```typescript
// DELETE: POST /api/analysis/${domainId}/start - DOES NOT EXIST
// DELETE: GET /api/analysis/jobs/${jobId} - WRONG PATH
```

**ADD these correct endpoints:**
```typescript
// ============================================
// STANDARD ANALYSIS (Established Domains)
// ============================================
export async function startStandardAnalysis(params: {
  domain: string;
  email: string;
  company_name?: string;
  primary_market?: string;
  primary_goal?: 'traffic' | 'leads' | 'authority' | 'balanced';
  primary_language?: string;
  collection_depth?: 'testing' | 'basic' | 'balanced' | 'comprehensive' | 'enterprise';
}) {
  const response = await fetch(`${API_URL}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // Auth header optional for this endpoint
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Analysis failed to start');
  }

  return response.json() as Promise<{
    job_id: string;
    domain: string;
    email: string;
    status: 'pending';
    message: string;
  }>;
}

// ============================================
// JOB STATUS POLLING (No auth required)
// ============================================
export async function getJobStatus(jobId: string) {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error('Failed to get job status');
  }

  return response.json() as Promise<{
    job_id: string;
    domain: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    started_at?: string;
    completed_at?: string;
    error?: string;
  }>;
}

// ============================================
// GREENFIELD ANALYSIS (Auth Required)
// ============================================
export async function startGreenfieldAnalysis(params: {
  domain: string;
  business_name: string;
  business_description: string;
  primary_offering: string;
  target_market: string;
  industry_vertical?: string;
  seed_keywords: string[];      // Min 5 items
  known_competitors: string[];  // Min 3 items
  target_audience?: string;
  email?: string;
}) {
  return apiClient<{
    analysis_run_id: string;
    session_id: string;
    status: 'awaiting_curation';
    message: string;
    next_step: string;
  }>('/api/greenfield/analyze', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
```

---

### Fix 3: Competitor Intelligence - Change URL Paths

**WRONG:**
```typescript
/api/competitor-intelligence/sessions/{sessionId}
/api/competitor-intelligence/sessions/{sessionId}/curate
```

**CORRECT:**
```typescript
/api/greenfield/sessions/{session_id}
/api/greenfield/sessions/{session_id}/curate
```

**Add these functions:**
```typescript
export async function getCompetitorSession(sessionId: string) {
  return apiClient(`/api/greenfield/sessions/${sessionId}`);
}

export async function submitCompetitorCuration(
  sessionId: string,
  curation: {
    removals: Array<{
      domain: string;
      reason: 'not_relevant' | 'too_large' | 'too_small' | 'different_market' | 'other';
      note?: string;
    }>;
    additions: Array<{
      domain: string;
      purpose?: string;
    }>;
    purpose_overrides: Array<{
      domain: string;
      new_purpose: 'benchmark_peer' | 'keyword_source' | 'link_source' | 'content_model' | 'aspirational';
    }>;
  }
) {
  return apiClient(`/api/greenfield/sessions/${sessionId}/curate`, {
    method: 'POST',
    body: JSON.stringify(curation),
  });
}
```

---

### Fix 4: Wire Competitor Curation to Backend

The curation UI currently operates on **local state only**. It needs to:

1. **On mount:** Fetch candidates from `GET /api/greenfield/sessions/{session_id}`
2. **On finalize:** Send decisions to `POST /api/greenfield/sessions/{session_id}/curate`

**Example implementation:**
```typescript
// In your curation component
const [candidates, setCandidates] = useState<CompetitorCandidate[]>([]);
const [removedDomains, setRemovedDomains] = useState<Set<string>>(new Set());
const [purposeOverrides, setPurposeOverrides] = useState<Map<string, string>>(new Map());

// Fetch candidates on mount
useEffect(() => {
  if (!sessionId) return;

  getCompetitorSession(sessionId).then(session => {
    setCandidates(session.candidates);
    setRequiredRemovals(session.required_removals);
    setMinFinal(session.min_final_count);
    setMaxFinal(session.max_final_count);
  });
}, [sessionId]);

// Handle finalization
const handleFinalize = async () => {
  const removals = Array.from(removedDomains).map(domain => ({
    domain,
    reason: removalReasons.get(domain) || 'not_relevant',
    note: removalNotes.get(domain),
  }));

  const overrides = Array.from(purposeOverrides.entries()).map(([domain, purpose]) => ({
    domain,
    new_purpose: purpose,
  }));

  const result = await submitCompetitorCuration(sessionId, {
    removals,
    additions: addedCompetitors,
    purpose_overrides: overrides,
  });

  // Navigate to greenfield dashboard
  navigate(`/greenfield/dashboard/${result.analysis_run_id || analysisRunId}`);
};
```

---

### Fix 5: Dashboard Endpoints - Remove Wrong Prefixes

**WRONG paths (do not exist):**
```typescript
/api/dashboard/{id}/greenfield/overview   // WRONG
/api/dashboard/{id}/established/overview  // WRONG
/api/dashboard/{id}/greenfield/battleground // WRONG
```

**CORRECT paths:**
```typescript
// Standard dashboard (for established domains)
/api/dashboard/{domain_id}/bundle?include=overview,sparklines,sov,battleground,clusters,content_audit,opportunities
/api/dashboard/{domain_id}/overview
/api/dashboard/{domain_id}/sov
/api/dashboard/{domain_id}/sparklines
/api/dashboard/{domain_id}/battleground
/api/dashboard/{domain_id}/clusters
/api/dashboard/{domain_id}/content-audit
/api/dashboard/{domain_id}/opportunities
/api/dashboard/{domain_id}/intelligence-summary

// Greenfield dashboard (for new domains) - uses analysis_run_id NOT domain_id
/api/greenfield/dashboard/{analysis_run_id}
/api/greenfield/dashboard/{analysis_run_id}/beachheads
/api/greenfield/dashboard/{analysis_run_id}/market-map
/api/greenfield/dashboard/{analysis_run_id}/projections
/api/greenfield/dashboard/{analysis_run_id}/roadmap
```

---

### Fix 6: Analysis Request Payload

**WRONG payload:**
```typescript
{
  depth: 'quick' | 'comprehensive',
  include_ai_visibility?: boolean
}
```

**CORRECT payload for standard analysis:**
```typescript
{
  domain: string,           // REQUIRED - "example.com"
  email: string,            // REQUIRED - "user@email.com"
  company_name?: string,
  primary_market?: string,  // "se", "us", "uk", "de"
  primary_goal?: 'traffic' | 'leads' | 'authority' | 'balanced',
  collection_depth?: 'testing' | 'basic' | 'balanced' | 'comprehensive' | 'enterprise'
}
```

**CORRECT payload for greenfield analysis:**
```typescript
{
  domain: string,                    // REQUIRED
  business_name: string,             // REQUIRED
  business_description: string,      // REQUIRED
  primary_offering: string,          // REQUIRED
  target_market: string,             // Default: "United States"
  seed_keywords: string[],           // REQUIRED, min 5
  known_competitors: string[],       // REQUIRED, min 3
  target_audience?: string,
  email?: string
}
```

---

### Fix 7: Polling Interval

**Current:** 5 seconds
**Recommended:** 10 seconds

```typescript
const { data: jobStatus } = useQuery({
  queryKey: ['job', jobId],
  queryFn: () => getJobStatus(jobId),
  enabled: !!jobId,
  refetchInterval: (data) => {
    if (data?.status === 'completed' || data?.status === 'failed') {
      return false; // Stop polling
    }
    return 10000; // Poll every 10 seconds
  },
});
```

---

## IMPLEMENTATION ORDER

1. **Fix 1: Maturity Check** - This determines the entire flow
2. **Fix 2: Analysis Endpoints** - Core functionality
3. **Fix 3: Competitor Session URLs** - Fixes greenfield flow
4. **Fix 4: Wire Curation to Backend** - Completes greenfield flow
5. **Fix 5: Dashboard URLs** - Fixes data display
6. **Fix 6: Request Payloads** - Ensures correct data sent
7. **Fix 7: Polling Interval** - Minor optimization

---

## TESTING CHECKLIST

After implementing fixes, test:

- [ ] Domain maturity check returns real data from API
- [ ] Established domain → Standard analysis flow works
- [ ] Greenfield domain → Greenfield analysis flow works
- [ ] Competitor curation sends data to backend
- [ ] Job polling shows correct status transitions
- [ ] Standard dashboard loads with bundle endpoint
- [ ] Greenfield dashboard loads beachheads and projections
- [ ] Strategy builder endpoints all work

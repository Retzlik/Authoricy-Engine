# Frontend Changes Summary: Greenfield Flow Update

**Date:** 2026-01-28
**Backend Version:** Post-commit `23ce96c`

---

## What Changed (TL;DR)

1. **Curation now auto-triggers deep analysis** - No separate `/continue` call needed
2. **Fewer competitors presented** - Smart auto-curation shows max 15 candidates (not 35+)
3. **Flexible limits** - Accept 3-15 competitors (not exactly 8-10)
4. **Longer response time on /curate** - Expect 30-60 seconds as analysis runs inline

---

## The Updated Flow (4 Steps, Not 5)

```
Step 1: POST /api/greenfield/analyze
        → Returns session_id, analysis_run_id
        → Status: "awaiting_curation"

Step 2: GET /api/greenfield/sessions/{session_id}
        → Returns max 15 pre-curated competitor candidates
        → User reviews and optionally adjusts

Step 3: POST /api/greenfield/sessions/{session_id}/curate
        → Validates competitors (3-15 allowed)
        → Saves curation
        → AUTOMATICALLY runs deep analysis (keyword mining, SERP, market sizing)
        → Returns combined result with analysis status
        → ⚠️ TAKES 30-60 SECONDS - show loading state!

Step 4: GET /api/greenfield/dashboard/{analysis_run_id}
        → Dashboard is ready immediately after step 3 completes
        → No waiting or polling needed
```

---

## Complete API Contract for /curate

### Request

```typescript
// POST /api/greenfield/sessions/{session_id}/curate

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

// Example request body:
{
  "removals": [
    { "domain": "facebook.com", "reason": "too_large" },
    { "domain": "unrelated.com", "reason": "not_relevant", "note": "Different industry" }
  ],
  "additions": [
    { "domain": "competitor.com", "purpose": "benchmark_peer" }
  ],
  "purpose_overrides": [
    { "domain": "bigsite.com", "new_purpose": "aspirational" }
  ]
}
```

### Response (Updated)

```typescript
interface CurationResponse {
  // Curation result
  session_id: string
  status: 'completed'  // Always 'completed' now (not 'curated')
  final_competitors: FinalCompetitor[]
  competitor_count: number
  removed_count: number
  added_count: number
  finalized_at: string

  // NEW - Analysis result fields
  analysis_status: 'completed' | 'failed'
  keywords_count: number          // Total keywords discovered
  beachheads_count: number        // High-priority "beachhead" keywords
  market_opportunity: {           // TAM/SAM/SOM data
    total_addressable_market: number
    serviceable_addressable_market: number
    serviceable_obtainable_market: number
    market_opportunity_score: number
    competition_intensity: number
  } | null

  // If analysis failed
  analysis_error?: string
}

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

---

## Validation Rules

| Rule | Value | Error Message |
|------|-------|---------------|
| Minimum competitors | 3 | "Must have at least 3 competitors" |
| Maximum competitors | 15 | "Maximum 15 competitors allowed" |
| Max candidates shown | 15 | (Backend handles this automatically) |

The backend auto-curates to show max 15 candidates:
- 5 benchmarks (most important)
- 7 keyword sources (high value for mining)
- 3 market intel (awareness only)

---

## UI Recommendations

### 1. Loading State for Curation Submit

Since `/curate` now takes 30-60 seconds, show a clear loading state:

```typescript
// Example React implementation
const [isSubmitting, setIsSubmitting] = useState(false)

const handleSubmit = async () => {
  setIsSubmitting(true)
  try {
    const result = await apiClient(`/api/greenfield/sessions/${sessionId}/curate`, {
      method: 'POST',
      body: JSON.stringify(curationInput)
    })

    // Analysis is complete - go directly to dashboard
    navigate(`/greenfield/dashboard/${analysisRunId}`)
  } catch (error) {
    // Handle error
  } finally {
    setIsSubmitting(false)
  }
}

// In JSX:
<Button disabled={isSubmitting}>
  {isSubmitting ? 'Analyzing competitors... (this takes ~30-60 seconds)' : 'Finalize & Analyze'}
</Button>
```

### 2. Progress Indication

Consider showing a multi-step progress indicator:
- "Saving competitor selections..."
- "Mining keywords from competitors..."
- "Analyzing market opportunity..."
- "Building your dashboard..."

### 3. Error Handling

```typescript
interface CurationError {
  detail: string
  // Common errors:
  // "Must have at least 3 competitors (got 2)"
  // "Maximum 15 competitors allowed (got 18)"
  // "Session not found"
  // "Session already curated"
}
```

### 4. After Successful Curation

The response includes analysis status. Check it before redirecting:

```typescript
if (result.analysis_status === 'completed') {
  // Dashboard is ready - redirect immediately
  navigate(`/greenfield/dashboard/${analysisRunId}`)
} else {
  // Rare: analysis failed but curation succeeded
  // Show error but still allow dashboard access (partial data)
  showWarning(`Analysis partially completed: ${result.analysis_error}`)
  navigate(`/greenfield/dashboard/${analysisRunId}`)
}
```

---

## Removed: /continue Endpoint

The frontend should **NOT** call `/api/greenfield/sessions/{session_id}/continue`.

This endpoint still exists but is no longer needed - the `/curate` endpoint handles everything automatically.

---

## Session Status Values

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `awaiting_curation` | Waiting for user to review competitors | Show curation UI |
| `completed` | Curation done, analysis complete | Redirect to dashboard |

Note: `curated` status is no longer used - sessions go directly to `completed`.

---

## Quick Checklist for Frontend

- [ ] Update `/curate` response type to include analysis fields
- [ ] Add 30-60 second loading state on curation submit
- [ ] Remove any calls to `/continue` endpoint
- [ ] Redirect to dashboard immediately after `/curate` succeeds
- [ ] Update validation to show 3-15 competitor range (not 8-10)
- [ ] Handle `analysis_status: 'failed'` gracefully (show warning, still allow dashboard)

---

## Questions?

If anything is unclear, check the full `FRONTEND_SPEC.md` in the backend repo or ask for clarification.

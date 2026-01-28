# Debug Summary: 404 on /curate Endpoint

## Current Status

**Symptoms:**
- `curl` to `/api/greenfield/sessions/test-id/curate` returns **401 Not authenticated** (route works)
- Frontend browser request to same endpoint returns **404**
- GET `/sessions/{session_id}` from frontend works (200)
- POST `/sessions/{session_id}/curate` from frontend fails (404)

**Confirmed working:**
- `/api/greenfield/debug/ping` returns OK
- Route is registered correctly
- Session exists in database (proven by GET working)

## Debug Endpoints Added (deploy needed)

After deployment, run these tests:

```bash
# 1. Test that POST to /sessions/{id}/xxx pattern works (no auth)
curl -X POST https://authoricy-engine-production.up.railway.app/api/greenfield/debug/sessions/test-id/test-curate

# Expected: {"status":"ok","message":"POST route pattern is working",...}

# 2. Check if your actual session exists
curl https://authoricy-engine-production.up.railway.app/api/greenfield/debug/sessions/686de79a-cfcf-4094-9e1c-232cd804d6f3/check

# Expected: {"status":"ok","message":"Session found",...} or {"status":"not_found",...}

# 3. Test authenticated /curate with your token
# Get your Supabase access token from browser DevTools > Application > Local Storage
curl -X POST https://authoricy-engine-production.up.railway.app/api/greenfield/sessions/686de79a-cfcf-4094-9e1c-232cd804d6f3/curate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"removals":[],"additions":[],"purpose_overrides":[]}'
```

## Railway Logs to Look For

After deployment, check Railway logs for:

```
[REQUEST] POST /api/greenfield/sessions/xxx/curate from origin=...
[CURATE-OPTIONS] Preflight request for session xxx
[CURATE] *** REQUEST REACHED HANDLER *** session=xxx user=xxx
[RESPONSE] POST /api/greenfield/sessions/xxx/curate -> 200
```

**If you see:**
- No `[REQUEST]` log → Request not reaching server at all
- `[REQUEST]` but no `[CURATE]` log → Auth failing silently
- `[CURATE-OPTIONS]` log → CORS preflight is working
- `[CURATE] *** REQUEST REACHED HANDLER ***` → Handler is executing

## Browser Debug Steps

1. **Clear browser cache** completely or use incognito mode
2. Open DevTools → Network tab → Filter "curate"
3. Click the curation button
4. Check for:
   - Is there an OPTIONS request? What's its status?
   - What's the exact URL of the POST request?
   - What are the request headers?
   - What's the response body of the 404?

## Possible Causes Still Under Investigation

1. **Browser cache** - Old 404 response cached before deployment
2. **CORS preflight** - OPTIONS request might be failing silently
3. **Session state** - Session might be in a state that causes rejection
4. **Path encoding** - UUID might have invisible characters

## Commits Made

1. `364f95c` - Fix duplicate key constraint violation in submit_curation
2. `0c47485` - Add debug endpoints and OPTIONS handler for troubleshooting

## Files Changed

- `src/database/repository.py` - Delete existing competitors before insert
- `api/greenfield.py` - Debug endpoints, OPTIONS handler, enhanced logging

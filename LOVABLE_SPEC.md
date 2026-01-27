# Lovable Frontend Integration Specification

## Authoricy Intelligence Dashboard - Frontend Integration Guide

This document provides complete instructions for integrating the Lovable frontend with the Authoricy Engine backend API.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Lovable)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Login     │  │  Dashboard  │  │  Strategy   │  │    Admin    │    │
│  │   Page      │  │   Pages     │  │   Builder   │  │   Panel     │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │           │
│         └────────────────┴────────────────┴────────────────┘           │
│                                   │                                     │
│                          Supabase Auth Client                           │
│                          (sign up, login, JWT)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ JWT Token in Authorization Header
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (Authoricy Engine)                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     FastAPI Application                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│  │  │  /users  │  │/dashboard│  │/strategy │  │ /analyze │        │   │
│  │  │   API    │  │   API    │  │   API    │  │   API    │        │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │   │
│  │       │             │             │             │               │   │
│  │       └─────────────┴─────────────┴─────────────┘               │   │
│  │                            │                                     │   │
│  │                   JWT Validation Middleware                      │   │
│  │                   (validates Supabase tokens)                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                           PostgreSQL Database                           │
│                      (users, domains, analyses, etc.)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Points:
1. **Supabase handles authentication only** - signup, login, password reset, OAuth
2. **Backend validates JWTs** - all API requests include the Supabase token
3. **Backend owns all data** - domains, analyses, keywords, strategies
4. **Backend enforces authorization** - users only see their own domains

---

## Supabase Setup

### 1. Create Supabase Project

Create a new Supabase project at https://supabase.com. You only need:
- **Authentication** enabled (Email/Password and optionally OAuth)
- **No database tables needed** - the backend handles all data storage

### 2. Get Credentials

From your Supabase project dashboard, get:
- `SUPABASE_URL` - e.g., `https://abcdefg.supabase.co`
- `SUPABASE_ANON_KEY` - the public anon key
- `SUPABASE_JWT_SECRET` - from Settings > API > JWT Secret

### 3. Configure Backend Environment

Add these to the Authoricy Engine environment:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Optional: Admin emails (auto-promoted to admin on first login)
ADMIN_EMAILS=admin@yourcompany.com,cto@yourcompany.com

# Enable auth (set to false for local dev without auth)
AUTH_ENABLED=true
```

---

## Authentication Flow

### Login Flow

```
1. User enters email/password on Login page
2. Frontend calls Supabase: supabase.auth.signInWithPassword()
3. Supabase returns JWT token (access_token)
4. Frontend stores token (Supabase client handles this)
5. All API calls include: Authorization: Bearer <token>
6. Backend validates token with SUPABASE_JWT_SECRET
7. Backend syncs user to local DB (creates on first login)
8. API returns data based on user's role and domain ownership
```

### Frontend Implementation

```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Login function
async function login(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) throw error
  return data
}

// Sign up function
async function signUp(email: string, password: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  })

  if (error) throw error
  return data
}

// Get current session
async function getSession() {
  const { data: { session } } = await supabase.auth.getSession()
  return session
}

// Sign out
async function signOut() {
  await supabase.auth.signOut()
}
```

### Making Authenticated API Calls

```typescript
// lib/api.ts
import { supabase } from './supabase'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://your-backend.railway.app'

export async function apiRequest(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  // Get current session token
  const { data: { session } } = await supabase.auth.getSession()

  if (!session?.access_token) {
    throw new Error('Not authenticated')
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
      ...options.headers,
    },
  })

  if (response.status === 401) {
    // Token expired or invalid - redirect to login
    await supabase.auth.signOut()
    window.location.href = '/login'
    return
  }

  if (response.status === 403) {
    throw new Error('Access denied')
  }

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'API error')
  }

  return response.json()
}

// Convenience methods
export const api = {
  get: (endpoint: string) => apiRequest(endpoint),
  post: (endpoint: string, data: any) => apiRequest(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  patch: (endpoint: string, data: any) => apiRequest(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  delete: (endpoint: string) => apiRequest(endpoint, { method: 'DELETE' }),
}
```

---

## API Endpoints Reference

### Authentication Endpoints

```
GET  /api/users/me              - Get current user profile
PATCH /api/users/me             - Update current user profile

# Admin only
GET  /api/users                 - List all users
GET  /api/users/{user_id}       - Get user by ID
PATCH /api/users/{user_id}/role - Update user role
DELETE /api/users/{user_id}     - Disable user
POST /api/users/{user_id}/enable - Enable user
```

### Domain Endpoints

Users only see their own domains. Admins see all.

```
GET  /api/domains/{domain_id}/strategies    - List strategies for domain
GET  /api/domains/{domain_id}/analyses      - List analyses for domain
```

### Dashboard Endpoints

All require authentication. Users can only access their own domains.

```
GET  /api/dashboard/{domain_id}/bundle         - Get all dashboard data (recommended)
GET  /api/dashboard/{domain_id}/overview       - Get dashboard overview
GET  /api/dashboard/{domain_id}/sov            - Get Share of Voice
GET  /api/dashboard/{domain_id}/sparklines     - Get position trend sparklines
GET  /api/dashboard/{domain_id}/battleground   - Get attack/defend keywords
GET  /api/dashboard/{domain_id}/clusters       - Get topical authority clusters
GET  /api/dashboard/{domain_id}/content-audit  - Get KUCK content audit
GET  /api/dashboard/{domain_id}/opportunities  - Get ranked opportunities
GET  /api/dashboard/{domain_id}/intelligence-summary - Get AI summary
```

### Strategy Builder Endpoints

```
# Strategies
GET    /api/domains/{domain_id}/strategies     - List strategies
POST   /api/strategies                         - Create strategy
GET    /api/strategies/{strategy_id}           - Get strategy details
PATCH  /api/strategies/{strategy_id}           - Update strategy
DELETE /api/strategies/{strategy_id}           - Delete strategy

# Threads
GET    /api/strategies/{strategy_id}/threads   - List threads
POST   /api/strategies/{strategy_id}/threads   - Create thread
PATCH  /api/threads/{thread_id}                - Update thread
DELETE /api/threads/{thread_id}                - Delete thread

# Keywords
GET    /api/threads/{thread_id}/keywords       - List keywords in thread
POST   /api/threads/{thread_id}/keywords       - Assign keywords
DELETE /api/threads/{thread_id}/keywords       - Remove keywords

# Topics
GET    /api/threads/{thread_id}/topics         - List topics
POST   /api/threads/{thread_id}/topics         - Create topic
PATCH  /api/topics/{topic_id}                  - Update topic
DELETE /api/topics/{topic_id}                  - Delete topic

# Export
POST   /api/strategies/{strategy_id}/export    - Export strategy
GET    /api/strategies/{strategy_id}/exports   - List exports
```

### Analysis Endpoints

```
POST /api/analyze                              - Trigger new analysis
GET  /api/jobs/{job_id}                        - Get job status
```

---

## User Roles

### User Role
- Can only see their own domains
- Can create domains and run analyses
- Can create and manage strategies for their domains
- Cannot access other users' data
- Cannot access admin endpoints

### Admin Role
- Can see ALL domains (all users)
- Can manage all users (promote/demote roles, disable accounts)
- Full access to all endpoints
- Typically for company admins/support staff

### Auto-Promotion
Emails listed in `ADMIN_EMAILS` environment variable are automatically promoted to admin on first login.

---

## Frontend Pages

### 1. Login Page (`/login`)

```typescript
// pages/login.tsx
import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/router'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) throw error

      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleLogin}>
      {error && <div className="error">{error}</div>}
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Logging in...' : 'Log In'}
      </button>
      <p>
        Don't have an account? <a href="/signup">Sign up</a>
      </p>
    </form>
  )
}
```

### 2. Protected Route Wrapper

```typescript
// components/ProtectedRoute.tsx
import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import { supabase } from '@/lib/supabase'
import { api } from '@/lib/api'

interface User {
  id: string
  email: string
  full_name: string | null
  role: 'user' | 'admin'
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    checkUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_OUT') {
          setUser(null)
          router.push('/login')
        } else if (session) {
          await fetchUser()
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const checkUser = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    if (session) {
      await fetchUser()
    } else {
      setLoading(false)
    }
  }

  const fetchUser = async () => {
    try {
      const userData = await api.get('/api/users/me')
      setUser(userData)
    } catch (error) {
      console.error('Failed to fetch user:', error)
    } finally {
      setLoading(false)
    }
  }

  return { user, loading, isAdmin: user?.role === 'admin' }
}

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  if (loading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return null
  }

  return <>{children}</>
}
```

### 3. Dashboard Page

```typescript
// pages/dashboard/[domain_id].tsx
import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import { api } from '@/lib/api'
import ProtectedRoute from '@/components/ProtectedRoute'

export default function DashboardPage() {
  const router = useRouter()
  const { domain_id } = router.query
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (domain_id) {
      loadDashboard()
    }
  }, [domain_id])

  const loadDashboard = async () => {
    try {
      // Use the bundle endpoint for best performance
      const bundle = await api.get(
        `/api/dashboard/${domain_id}/bundle?include=overview,sparklines,sov,battleground`
      )
      setData(bundle)
    } catch (err: any) {
      if (err.message === 'Access denied') {
        setError('You do not have access to this domain')
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div>Loading dashboard...</div>
  if (error) return <div className="error">{error}</div>

  return (
    <ProtectedRoute>
      <div className="dashboard">
        <h1>{data.domain} Dashboard</h1>

        {/* Overview Section */}
        <section className="overview">
          <h2>Health Scores</h2>
          {/* Render data.overview */}
        </section>

        {/* Share of Voice */}
        <section className="sov">
          <h2>Share of Voice</h2>
          {/* Render data.sov */}
        </section>

        {/* ... other sections */}
      </div>
    </ProtectedRoute>
  )
}
```

### 4. Admin Panel (Admin Only)

```typescript
// pages/admin/users.tsx
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import ProtectedRoute, { useAuth } from '@/components/ProtectedRoute'
import { useRouter } from 'next/router'

export default function AdminUsersPage() {
  const { isAdmin, loading: authLoading } = useAuth()
  const router = useRouter()
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      router.push('/dashboard')
    } else if (isAdmin) {
      loadUsers()
    }
  }, [isAdmin, authLoading])

  const loadUsers = async () => {
    try {
      const response = await api.get('/api/users')
      setUsers(response.users)
    } catch (err) {
      console.error('Failed to load users:', err)
    } finally {
      setLoading(false)
    }
  }

  const updateRole = async (userId: string, newRole: string) => {
    try {
      await api.patch(`/api/users/${userId}/role`, { role: newRole })
      await loadUsers() // Refresh
    } catch (err) {
      console.error('Failed to update role:', err)
    }
  }

  if (!isAdmin) return null

  return (
    <ProtectedRoute>
      <div className="admin-panel">
        <h1>User Management</h1>
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Domains</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td>{user.email}</td>
                <td>{user.full_name || '-'}</td>
                <td>{user.role}</td>
                <td>{user.domain_count}</td>
                <td>
                  <select
                    value={user.role}
                    onChange={(e) => updateRole(user.id, e.target.value)}
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ProtectedRoute>
  )
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| 200 | Success | Display data |
| 201 | Created | Display success, redirect |
| 304 | Not Modified | Use cached data |
| 400 | Bad Request | Show validation errors |
| 401 | Unauthorized | Redirect to login |
| 403 | Forbidden | Show "Access Denied" |
| 404 | Not Found | Show "Not Found" page |
| 409 | Conflict | Show version conflict (retry) |
| 429 | Rate Limited | Show "Try again later" |
| 500 | Server Error | Show generic error |

### Example Error Handler

```typescript
async function handleApiError(error: any) {
  if (error.message === 'Not authenticated') {
    // Redirect to login
    window.location.href = '/login'
    return
  }

  if (error.message === 'Access denied') {
    // Show access denied message
    toast.error('You do not have permission to access this resource')
    return
  }

  // Show generic error
  toast.error(error.message || 'Something went wrong')
}
```

---

## Caching

The backend supports HTTP caching. Use proper cache headers in your fetch calls:

```typescript
// Using ETag for conditional requests
let lastEtag: string | null = null

async function fetchDashboard(domainId: string) {
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${token}`,
  }

  if (lastEtag) {
    headers['If-None-Match'] = lastEtag
  }

  const response = await fetch(`/api/dashboard/${domainId}/bundle`, { headers })

  if (response.status === 304) {
    // Data hasn't changed, use cached version
    return cachedData
  }

  // Store new ETag
  lastEtag = response.headers.get('ETag')

  return response.json()
}
```

---

## Environment Variables (Frontend)

```bash
# .env.local
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...your-anon-key
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

---

## Deployment Checklist

### Backend (Railway)
- [ ] Set `SUPABASE_URL`
- [ ] Set `SUPABASE_ANON_KEY`
- [ ] Set `SUPABASE_JWT_SECRET`
- [ ] Set `ADMIN_EMAILS` (comma-separated admin emails)
- [ ] Set `AUTH_ENABLED=true`
- [ ] Run database migration: `POST /api/migrate`

### Frontend (Vercel/Netlify)
- [ ] Set `NEXT_PUBLIC_SUPABASE_URL`
- [ ] Set `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] Set `NEXT_PUBLIC_API_URL`

### Supabase
- [ ] Enable Email/Password authentication
- [ ] (Optional) Enable OAuth providers (Google, GitHub)
- [ ] Configure email templates for password reset
- [ ] Set up redirect URLs for OAuth

---

## Security Notes

1. **Never store JWT secret in frontend** - only the anon key is public
2. **Always validate tokens on backend** - never trust frontend claims
3. **Use HTTPS everywhere** - Supabase, backend, frontend
4. **Don't disable auth in production** - `AUTH_ENABLED=true`
5. **Audit admin access** - monitor who has admin role

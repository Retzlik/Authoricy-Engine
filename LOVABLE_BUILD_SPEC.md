# Authoricy Frontend Build Specification

**For: Lovable.dev**
**Version: 1.0**
**Date: January 2026**

---

## Executive Summary

Build a professional B2B SaaS frontend for **Authoricy** - an SEO intelligence platform that helps agencies create data-driven content strategies. The design standard is **USD 100M B2B SaaS** (think Linear, Notion, Figma).

**Backend API:** `https://authoricy-engine-production.up.railway.app`

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [User Journey](#2-user-journey)
3. [Screen Specifications](#3-screen-specifications)
4. [API Reference](#4-api-reference)
5. [Design System](#5-design-system)
6. [Technical Requirements](#6-technical-requirements)

---

## 1. Product Overview

### What is Authoricy?

Authoricy helps SEO agencies:
1. **Analyze** client websites to discover keyword opportunities
2. **Build strategies** by organizing keywords into topic clusters (threads)
3. **Export** strategies to content production tools (Monok)

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Domain** | A client website being analyzed (e.g., `example.com`) |
| **Analysis** | A data collection run that gathers keywords, competitors, backlinks |
| **Strategy** | A content plan built from analysis data |
| **Thread** | A topic cluster / market position to own (contains keywords) |
| **Topic** | A specific content piece within a thread |
| **Keyword** | A search term with volume, difficulty, opportunity score |

### Hierarchy

```
Domain
  └── Analysis (multiple per domain)
        └── Strategy (multiple per analysis)
              └── Thread (ordered list)
                    ├── Keywords (assigned to thread)
                    └── Topics (content pieces)
```

---

## 2. User Journey

### Primary Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Dashboard  │────▶│  Analysis   │────▶│  Strategy   │────▶│   Export    │
│             │     │ Questionnaire│     │   Builder   │     │  to Monok   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Detailed Steps

1. **Dashboard** - User sees their domains and recent activity
2. **Add Domain** - User adds a new client domain
3. **Start Analysis** - User answers questionnaire to configure analysis
4. **View Progress** - User watches real-time analysis progress
5. **Review Results** - User sees keyword data, competitors, opportunities
6. **Create Strategy** - User creates a strategy from the analysis
7. **Build Strategy** - User drags keywords into threads, creates topics
8. **Export** - User validates and exports to Monok format

---

## 3. Screen Specifications

### 3.1 Dashboard

**Purpose:** Overview of all domains and recent activity

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ AUTHORICY                           [+ Add Domain] [User] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Your Domains                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ example.com          │ 3 analyses │ 2 strategies │ → │ │
│  │ Last analyzed: 2 days ago                            │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ client-site.se       │ 1 analysis  │ 0 strategies │ → │ │
│  │ Last analyzed: 1 week ago                            │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Recent Activity                                           │
│  • Strategy "Q1 Content Plan" exported (2 hours ago)      │
│  • Analysis completed for example.com (2 days ago)        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**API Calls:**
- `GET /api/domains` - List all domains
- `GET /api/domains/{id}` - Get domain details

**Actions:**
- Click domain → Navigate to Domain Detail
- Click "Add Domain" → Open Add Domain modal

---

### 3.2 Add Domain Modal

**Purpose:** Register a new client website

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Domain | text | Yes | e.g., `example.com` |
| Display Name | text | No | Friendly name |
| Industry | select | No | ecommerce, saas, local, etc. |
| Target Market | select | Yes | Country (Sweden, US, UK, etc.) |
| Primary Language | select | Yes | en, sv, de, etc. |

**API Call:**
- `POST /api/domains`

---

### 3.3 Domain Detail

**Purpose:** View domain info, analyses, and strategies

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ ← Back    example.com                    [Run Analysis]   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Domain Info                                               │
│  Industry: E-commerce  │  Market: Sweden  │  Lang: sv     │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Analyses                              [Run Analysis] │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │ Jan 25, 2026  │ 8,432 keywords │ Completed    │ →   │  │
│  │ Jan 10, 2026  │ 7,891 keywords │ Completed    │ →   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Strategies                                           │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │ Q1 Content Plan │ 5 threads │ 342 keywords │ Draft  │  │
│  │ Competitor Attack │ 3 threads │ 156 keywords │ Done │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**API Calls:**
- `GET /api/domains/{id}` - Domain info
- `GET /api/domains/{id}/analyses` - List analyses
- `GET /api/domains/{id}/strategies` - List strategies

---

### 3.4 Analysis Questionnaire

**Purpose:** Configure and start a new analysis

**This is a multi-step wizard:**

#### Step 1: Business Context
```
┌────────────────────────────────────────────────────────────┐
│ New Analysis for example.com                    Step 1/4  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Tell us about your business                              │
│                                                            │
│  What is your primary SEO goal?                           │
│  ○ Traffic - Maximize organic visitors                    │
│  ○ Leads - Generate qualified inquiries                   │
│  ○ Authority - Build thought leadership                   │
│  ○ Balanced - All of the above                            │
│                                                            │
│  Describe your business in 1-2 sentences:                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ We sell premium outdoor furniture to Swedish homes   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Who is your target audience?                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Homeowners aged 35-55 with gardens or patios        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│                                        [Next: Competitors] │
└────────────────────────────────────────────────────────────┘
```

#### Step 2: Competitors
```
┌────────────────────────────────────────────────────────────┐
│ New Analysis for example.com                    Step 2/4  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Who are your competitors?                                │
│                                                            │
│  Add up to 5 competitor domains:                          │
│                                                            │
│  1. ┌────────────────────────┐  [×]                       │
│     │ competitor1.se         │                            │
│     └────────────────────────┘                            │
│  2. ┌────────────────────────┐  [×]                       │
│     │ competitor2.com        │                            │
│     └────────────────────────┘                            │
│  3. ┌────────────────────────┐                            │
│     │                        │  [+ Add]                   │
│     └────────────────────────┘                            │
│                                                            │
│  □ Also discover competitors automatically (recommended)  │
│                                                            │
│                              [Back]  [Next: Depth]        │
└────────────────────────────────────────────────────────────┘
```

#### Step 3: Analysis Depth
```
┌────────────────────────────────────────────────────────────┐
│ New Analysis for example.com                    Step 3/4  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  How deep should we analyze?                              │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ ○ Quick Scan                              ~5 min     │ │
│  │   Up to 1,000 keywords, basic competitor data        │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ ● Standard (Recommended)                  ~15 min    │ │
│  │   Up to 5,000 keywords, full competitor analysis     │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ ○ Deep Dive                               ~30 min    │ │
│  │   Up to 10,000 keywords, comprehensive backlinks     │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ ○ Enterprise                              ~60 min    │ │
│  │   Unlimited keywords, full technical audit           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│                              [Back]  [Next: Review]       │
└────────────────────────────────────────────────────────────┘
```

#### Step 4: Review & Start
```
┌────────────────────────────────────────────────────────────┐
│ New Analysis for example.com                    Step 4/4  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Review your configuration                                │
│                                                            │
│  Domain:        example.com                               │
│  Market:        Sweden (Swedish)                          │
│  Goal:          Leads                                     │
│  Competitors:   competitor1.se, competitor2.com           │
│  Depth:         Standard (~5,000 keywords)                │
│                                                            │
│  Estimated time: ~15 minutes                              │
│  Estimated cost: $2.50                                    │
│                                                            │
│                              [Back]  [Start Analysis]     │
└────────────────────────────────────────────────────────────┘
```

**API Call:**
- `POST /api/analyze` - Start analysis with configuration

---

### 3.5 Analysis Progress

**Purpose:** Real-time progress during analysis

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ Analysis in Progress                                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  example.com                                               │
│                                                            │
│  ████████████████████░░░░░░░░░░  68%                      │
│                                                            │
│  Current Phase: Collecting keyword data                   │
│                                                            │
│  ✓ Context Intelligence          (completed)              │
│  ✓ Domain Overview               (completed)              │
│  ● Keyword Collection            (in progress - 3,421)    │
│  ○ Competitor Analysis           (pending)                │
│  ○ SERP Analysis                 (pending)                │
│  ○ AI Insights                   (pending)                │
│                                                            │
│  Elapsed: 8:42  │  Estimated remaining: 4:15              │
│                                                            │
│                                           [Cancel]        │
└────────────────────────────────────────────────────────────┘
```

**API Calls:**
- `GET /api/analysis/{id}/status` - Poll for progress (every 2-3 seconds)

**Behavior:**
- Auto-redirect to results when status = "completed"
- Show error message if status = "failed"

---

### 3.6 Analysis Results

**Purpose:** View analysis data and create strategy

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ ← Back    Analysis Results                [Create Strategy]│
├────────────────────────────────────────────────────────────┤
│                                                            │
│  example.com  •  Jan 25, 2026  •  8,432 keywords          │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Overview                                             │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │  8,432      │  156        │  4.2M       │  52       │  │
│  │  Keywords   │  Ranking    │  Total Vol  │  Avg Diff │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  [Keywords] [Competitors] [Opportunities] [Clusters]      │
│  ─────────────────────────────────────────────────────    │
│                                                            │
│  Top Keywords by Opportunity Score                        │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Keyword          │ Volume │ Diff │ Opp  │ Position │   │
│  ├────────────────────────────────────────────────────┤   │
│  │ outdoor furniture│ 12,000 │  45  │ 87.5 │    8     │   │
│  │ garden chairs    │  8,500 │  38  │ 82.3 │   12     │   │
│  │ patio sets       │  6,200 │  52  │ 78.1 │    -     │   │
│  │ ...              │        │      │      │          │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**API Calls:**
- `GET /api/analysis/{id}` - Analysis summary
- `GET /api/analysis/{id}/keywords` - Paginated keywords
- `GET /api/analysis/{id}/competitors` - Competitor data

---

### 3.7 Strategy Builder (CRITICAL - Main Feature)

**Purpose:** Drag-and-drop interface to build content strategy

**This is the most important screen. It must be world-class.**

#### Layout Overview
```
┌────────────────────────────────────────────────────────────────────────────┐
│ ← Back   Q1 Content Plan                    [Validate] [Export to Monok]  │
├────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐ ┌─────────────────────────────────────┐ ┌───────┐│
│ │ AVAILABLE KEYWORDS   │ │ THREADS                             │ │DETAILS││
│ │                      │ │                                     │ │       ││
│ │ Search...      [Filter]│ │ ┌─────────────────────────────────┐ │ │Thread ││
│ │                      │ │ │ 📁 Outdoor Furniture Guide     ▼│ │ │Props  ││
│ │ ┌──────────────────┐ │ │ │    P1 • Confirmed • 12 kws    │ │ │       ││
│ │ │○ outdoor chairs  │ │ │ │ ┌─────────────────────────────┐│ │ │Name:  ││
│ │ │  Vol: 8.5k       │ │ │ │ │ outdoor furniture guide   ││ │ │[____] ││
│ │ │  Opp: 82.3       │◀─┼─┤ │ │ garden furniture ideas    ││ │ │       ││
│ │ └──────────────────┘ │ │ │ │ patio furniture tips      ││ │ │Status:││
│ │ ┌──────────────────┐ │ │ │ │ + 9 more keywords         ││ │ │[Draft]││
│ │ │○ garden benches  │ │ │ │ └─────────────────────────────┘│ │ │       ││
│ │ │  Vol: 4.2k       │ │ │ │                               │ │ │Custom ││
│ │ │  Opp: 75.1       │ │ │ │ Topics:                       │ │ │Instrs:││
│ │ └──────────────────┘ │ │ │ • Ultimate Guide to Outdoor...│ │ │[_____]││
│ │                      │ │ │ • How to Choose the Right... │ │ │[_____]││
│ │ Showing 50 of 8,432  │ │ └─────────────────────────────────┘ │ │       ││
│ │ [Load More]          │ │                                     │ │       ││
│ │                      │ │ ┌─────────────────────────────────┐ │ │       ││
│ │ ─────────────────    │ │ │ 📁 Buying Guides             ▼│ │ │       ││
│ │ Suggested Clusters   │ │ │    P2 • Draft • 8 kws          │ │ │       ││
│ │                      │ │ │    ...                         │ │ │       ││
│ │ [Garden Furniture]   │ │ └─────────────────────────────────┘ │ │       ││
│ │ 45 kws • 52k vol     │ │                                     │ │       ││
│ │ [+ Assign]           │ │ [+ Add Thread]                      │ │       ││
│ │                      │ │                                     │ │       ││
│ └──────────────────────┘ └─────────────────────────────────────┘ └───────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

#### Three-Panel Layout

**Left Panel: Available Keywords**
- Search bar with real-time filtering
- Filter dropdowns: Intent, Min Volume, Max Difficulty
- Infinite scroll with cursor pagination
- Each keyword shows: keyword text, volume, opportunity score
- Checkbox to select multiple keywords
- "Assign to Thread" button when keywords selected
- Suggested Clusters section at bottom

**Center Panel: Threads**
- Draggable/reorderable thread cards
- Each thread card shows:
  - Thread name (editable inline)
  - Priority badge (P1, P2, P3)
  - Status badge (Draft, Confirmed)
  - Keyword count
  - Expandable keyword list
  - Topics list
- Keywords within thread are draggable
- "Add Thread" button at bottom

**Right Panel: Thread Details**
- Shows when a thread is selected
- Thread name (editable)
- Status dropdown
- Priority dropdown
- Custom Instructions (structured form):
  - Strategic Context (textarea)
  - Differentiation Points (tag input)
  - Content Angle (text)
  - Format Recommendations (text)
  - Target Audience (text)
  - Additional Notes (textarea)

#### Drag & Drop Interactions

| Interaction | Behavior |
|-------------|----------|
| Drag keyword from left panel to thread | Assigns keyword to thread |
| Drag keyword between threads | Moves keyword to new thread |
| Drag keyword within thread | Reorders keyword |
| Drag thread up/down | Reorders threads |
| Drag topic within thread | Reorders topics |

#### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + S` | Save (shows "Saved" toast) |
| `Cmd/Ctrl + E` | Export |
| `Cmd/Ctrl + N` | New Thread |
| `Delete` | Remove selected keyword from thread |
| `Escape` | Deselect |

#### API Calls

**Initial Load:**
- `GET /api/strategies/{id}` - Strategy with threads
- `GET /api/strategies/{id}/available-keywords?limit=50` - First page of keywords
- `GET /api/strategies/{id}/suggested-clusters` - Cluster suggestions

**Keyword Operations:**
- `POST /api/threads/{id}/keywords` - Assign keywords (body: `{keyword_ids: [...], version: n}`)
- `DELETE /api/threads/{id}/keywords` - Remove keywords (body: `{keyword_ids: [...]}`)
- `POST /api/strategies/{id}/keywords/batch-move` - Move between threads

**Thread Operations:**
- `POST /api/strategies/{id}/threads` - Create thread
- `PATCH /api/threads/{id}` - Update thread (body includes `version` for optimistic locking)
- `POST /api/threads/{id}/move` - Reorder thread
- `DELETE /api/threads/{id}` - Delete thread

**Topic Operations:**
- `POST /api/threads/{id}/topics` - Create topic
- `PATCH /api/topics/{id}` - Update topic
- `POST /api/topics/{id}/move` - Reorder topic
- `DELETE /api/topics/{id}` - Delete topic

**Cluster Assignment:**
- `POST /api/strategies/{id}/assign-cluster` - Bulk assign cluster to thread

**Pagination:**
- `GET /api/strategies/{id}/available-keywords?cursor=xxx` - Next page

---

### 3.8 Export Flow

**Purpose:** Validate and export strategy to Monok

#### Step 1: Validation
```
┌────────────────────────────────────────────────────────────┐
│ Export to Monok                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Validating strategy...                                   │
│                                                            │
│  ✓ Strategy has threads                                   │
│  ✓ All confirmed threads have keywords                    │
│  ✓ Strategic context provided                             │
│                                                            │
│  ⚠ Warnings (export still allowed):                       │
│  • Thread "Buying Guides" has no topics defined           │
│  • 2 topics missing target URLs                           │
│  • 1 thread still in draft status                         │
│                                                            │
│                              [Cancel]  [Export Anyway]    │
└────────────────────────────────────────────────────────────┘
```

**API Call:**
- `POST /api/strategies/{id}/validate-export`

#### Step 2: Export Complete
```
┌────────────────────────────────────────────────────────────┐
│ Export Complete                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ✓ Strategy exported successfully                         │
│                                                            │
│  Summary:                                                  │
│  • 5 threads                                               │
│  • 23 topics                                               │
│  • 342 keywords                                            │
│  • 1.2M total search volume                                │
│                                                            │
│  Download:                                                 │
│  [Download JSON]  [Download CSV]  [Copy to Clipboard]     │
│                                                            │
│                                              [Done]       │
└────────────────────────────────────────────────────────────┘
```

**API Calls:**
- `POST /api/strategies/{id}/export` - Generate export
- `GET /api/exports/{id}/download` - Download file

---

## 4. API Reference

**Base URL:** `https://authoricy-engine-production.up.railway.app`

### Domain Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/domains` | List all domains |
| POST | `/api/domains` | Create domain |
| GET | `/api/domains/{id}` | Get domain detail |
| GET | `/api/domains/{id}/strategies` | List strategies for domain |
| GET | `/api/domains/{id}/analyses` | List analyses for domain |

### Analysis Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Start new analysis |
| GET | `/api/analysis/{id}/status` | Get analysis progress |
| GET | `/api/analysis/{id}` | Get analysis results |
| GET | `/api/analysis/{id}/keywords` | Get keywords (paginated) |

### Strategy Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/strategies/{id}` | Get strategy with threads |
| POST | `/api/strategies` | Create strategy |
| PATCH | `/api/strategies/{id}` | Update strategy |
| POST | `/api/strategies/{id}/duplicate` | Duplicate strategy |
| POST | `/api/strategies/{id}/archive` | Archive strategy |
| DELETE | `/api/strategies/{id}` | Delete (must be archived) |

### Thread Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/strategies/{id}/threads` | List threads |
| POST | `/api/strategies/{id}/threads` | Create thread |
| PATCH | `/api/threads/{id}` | Update thread |
| POST | `/api/threads/{id}/move` | Move thread (reorder) |
| DELETE | `/api/threads/{id}` | Delete thread |

### Keyword Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/strategies/{id}/available-keywords` | Available keywords (paginated) |
| GET | `/api/strategies/{id}/suggested-clusters` | Suggested clusters |
| GET | `/api/threads/{id}/keywords` | Keywords in thread |
| POST | `/api/threads/{id}/keywords` | Assign keywords |
| DELETE | `/api/threads/{id}/keywords` | Remove keywords |
| POST | `/api/strategies/{id}/keywords/batch-move` | Move keywords between threads |
| POST | `/api/strategies/{id}/assign-cluster` | Assign cluster to thread |

### Topic Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/threads/{id}/topics` | List topics |
| POST | `/api/threads/{id}/topics` | Create topic |
| PATCH | `/api/topics/{id}` | Update topic |
| POST | `/api/topics/{id}/move` | Move topic (reorder) |
| DELETE | `/api/topics/{id}` | Delete topic |

### Export Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/strategies/{id}/validate-export` | Validate for export |
| POST | `/api/strategies/{id}/export` | Export strategy |
| GET | `/api/strategies/{id}/exports` | Export history |
| GET | `/api/exports/{id}/download` | Download export |

### Activity Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/strategies/{id}/activity` | Activity log |

---

## 5. Design System

### Visual Style

**Reference Products:** Linear, Notion, Figma, Vercel

**Characteristics:**
- Clean, minimal interface
- Generous whitespace
- Subtle shadows and borders
- Smooth micro-animations
- Professional color palette

### Colors

```css
/* Light Mode */
--background: #FFFFFF;
--surface: #F9FAFB;
--border: #E5E7EB;
--text-primary: #111827;
--text-secondary: #6B7280;
--accent: #2563EB;
--success: #10B981;
--warning: #F59E0B;
--error: #EF4444;

/* Dark Mode */
--background: #0F172A;
--surface: #1E293B;
--border: #334155;
--text-primary: #F1F5F9;
--text-secondary: #94A3B8;
--accent: #3B82F6;
```

### Typography

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', monospace;

/* Sizes */
--text-xs: 12px;
--text-sm: 14px;
--text-base: 16px;
--text-lg: 18px;
--text-xl: 20px;
--text-2xl: 24px;
```

### Components

**Buttons:**
- Primary: Solid blue background
- Secondary: Border only
- Ghost: No background, hover shows background
- Destructive: Red for delete actions

**Cards:**
- Subtle border
- Slight shadow on hover
- Rounded corners (8px)

**Inputs:**
- Clear focus states
- Inline validation
- Placeholder text in secondary color

**Tables:**
- Alternating row colors (subtle)
- Sticky headers
- Sortable columns

**Toasts:**
- Bottom-right position
- Auto-dismiss after 3s
- Types: success, error, info

---

## 6. Technical Requirements

### Framework
- React with TypeScript
- TailwindCSS for styling
- React Query for data fetching
- Zustand or Jotai for state

### Drag & Drop
- Use `@dnd-kit/core` for drag and drop
- Support touch devices
- Visual feedback during drag

### Performance
- Virtual scrolling for keyword lists (10,000+ items)
- Optimistic updates for all mutations
- Debounced search (300ms)
- Request deduplication

### Error Handling
- Show toast on API errors
- Retry failed requests (3 attempts)
- Graceful degradation

### Optimistic Locking
All PATCH requests include a `version` field. If server returns 409:
```json
{
  "error": "version_conflict",
  "current_version": 5,
  "message": "Data was modified by another user"
}
```
Show dialog: "This item was modified. Reload and try again?"

### Responsive Design
- Primary target: Desktop (1280px+)
- Tablet support: 768px-1279px
- Mobile: Simplified view (optional)

### Loading States
- Skeleton loaders for initial load
- Inline spinners for actions
- Disable buttons during mutations

### Empty States
- Helpful illustrations
- Clear call-to-action buttons
- Guidance text

---

## Appendix A: Example API Responses

### GET /api/strategies/{id}

```json
{
  "strategy": {
    "id": "uuid",
    "name": "Q1 Content Plan",
    "status": "draft",
    "version": 3,
    "thread_count": 5,
    "topic_count": 23,
    "keyword_count": 342
  },
  "threads": [
    {
      "id": "uuid",
      "name": "Outdoor Furniture Guide",
      "position": "a",
      "version": 2,
      "status": "confirmed",
      "priority": 1,
      "custom_instructions": {
        "strategic_context": "Position as the authority...",
        "differentiation_points": ["Swedish design", "Sustainability"],
        "format_recommendations": "Long-form guide with comparison tables"
      },
      "metrics": {
        "keyword_count": 12,
        "total_search_volume": 45000,
        "avg_difficulty": 42,
        "avg_opportunity_score": 78.5
      },
      "topic_count": 4
    }
  ],
  "analysis": {
    "id": "uuid",
    "created_at": "2026-01-25T10:00:00Z",
    "keyword_count": 8432
  }
}
```

### GET /api/strategies/{id}/available-keywords

```json
{
  "keywords": [
    {
      "id": "uuid",
      "keyword": "outdoor furniture",
      "search_volume": 12000,
      "keyword_difficulty": 45,
      "opportunity_score": 87.5,
      "search_intent": "commercial",
      "parent_topic": "outdoor living",
      "assigned_thread_id": null,
      "assigned_thread_name": null
    }
  ],
  "pagination": {
    "next_cursor": "eyJ2IjogODcuNSwgImlkIjogInV1aWQifQ==",
    "has_more": true,
    "total_count": 8432,
    "unassigned_count": 8090
  }
}
```

---

## Appendix B: State Management

### Global State (Zustand)

```typescript
interface StrategyBuilderStore {
  // Current strategy
  strategy: Strategy | null;
  threads: Thread[];

  // Selection
  selectedThreadId: string | null;
  selectedKeywordIds: Set<string>;

  // UI state
  isLoading: boolean;
  isSaving: boolean;

  // Actions
  loadStrategy: (id: string) => Promise<void>;
  assignKeywords: (threadId: string, keywordIds: string[]) => Promise<void>;
  moveKeywords: (from: string, to: string, keywordIds: string[]) => Promise<void>;
  createThread: (name: string) => Promise<void>;
  updateThread: (id: string, updates: Partial<Thread>) => Promise<void>;
  reorderThread: (id: string, afterId: string | null) => Promise<void>;
  deleteThread: (id: string) => Promise<void>;
}
```

### Optimistic Updates Pattern

```typescript
const assignKeywords = async (threadId: string, keywordIds: string[]) => {
  // 1. Optimistically update UI
  set((state) => ({
    threads: state.threads.map(t =>
      t.id === threadId
        ? { ...t, keywords: [...t.keywords, ...keywordIds] }
        : t
    )
  }));

  // 2. Make API call
  try {
    await api.post(`/threads/${threadId}/keywords`, { keyword_ids: keywordIds });
  } catch (error) {
    // 3. Revert on failure
    set((state) => ({
      threads: state.threads.map(t =>
        t.id === threadId
          ? { ...t, keywords: t.keywords.filter(k => !keywordIds.includes(k)) }
          : t
      )
    }));
    throw error;
  }
};
```

---

## Appendix C: Build Priority

### Phase 1: Core Flow (Week 1)
1. Dashboard with domain list
2. Domain detail page
3. Analysis questionnaire
4. Analysis progress page

### Phase 2: Strategy Builder (Week 2-3)
1. Strategy list
2. Three-panel layout
3. Keyword list with pagination
4. Thread CRUD
5. Drag & drop keywords to threads

### Phase 3: Polish (Week 4)
1. Topics within threads
2. Custom instructions form
3. Suggested clusters
4. Export flow
5. Activity log

### Phase 4: Enhancement (Future)
1. Dark mode
2. Keyboard shortcuts
3. Mobile optimization
4. Collaboration features

---

**End of Specification**

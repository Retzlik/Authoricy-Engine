# Strategy Builder + Monok Export Specification
## Complete Scoping Document v1.0

**Created:** January 2026
**Status:** SCOPING COMPLETE - Ready for implementation
**Purpose:** User-driven strategy creation with Lovable UI + Monok content production export

---

## EXECUTIVE SUMMARY

### What We're Building

A **Strategy Builder** system that:
1. Presents collected SEO data as actionable strategy components
2. Allows **user-driven** (not AI-automated) strategy creation via drag & drop
3. Exports to **Monok** for content production execution

### Quality Standard: USD 100m B2B SaaS

The Strategy Builder must meet enterprise-grade UX standards:
- **Instant feedback** on all drag & drop operations
- **Optimistic updates** - UI updates immediately, syncs to backend
- **Undo/redo support** for all operations
- **Keyboard shortcuts** for power users
- **Bulk operations** (select multiple, assign to thread)
- **Real-time collaboration ready** (future: multiple users)

Data structures must support:
- Sub-second API responses for all operations
- Efficient reordering without full reload
- Partial updates (PATCH, not PUT)
- Conflict detection for concurrent edits

### Core Principle: User-Driven Strategy Creation

**NOT this (AI-automated):**
```
Run analysis → AI generates strategy → Export to Monok
```

**THIS (user-driven with AI assistance):**
```
Run analysis → Data stored → User opens Strategy Builder →
Sees AI-suggested clusters/topics → User confirms/adjusts/creates →
User approves → Export to Monok
```

### Why User-Driven?
- Reliable and shippable (no AI hallucination risk in final output)
- User maintains creative control over strategy
- AI provides data + suggestions, user makes decisions
- Matches agency workflow (strategist + client approval)

---

## SYSTEM ARCHITECTURE

### Critical: Analysis vs Strategy Builder Separation

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ANALYSIS (Manual Trigger Only)                    │
│                                                                      │
│   User clicks "Run Analysis" → Phase 1-4 collection →               │
│   Data stored in Authoricy DB (keywords, SERP, opportunities)       │
│                                                                      │
│   This is a SEPARATE action. Takes time. Costs money.               │
│   NEVER triggered by Strategy Builder operations.                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Data persisted in Authoricy DB
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STRATEGY BUILDER (Uses Stored Data)               │
│                                                                      │
│   Lovable calls API → Authoricy returns latest analysis data →      │
│   User drags/drops/reorders → Lovable calls API to persist          │
│   strategy structure → NO new analysis triggered                     │
│                                                                      │
│   All keyword/SERP data comes from Authoricy backend.               │
│   Lovable stores NOTHING except ephemeral UI state.                 │
└─────────────────────────────────────────────────────────────────────┘
```

| Action | Triggers Analysis? | Data Source |
|--------|-------------------|-------------|
| Run Analysis | YES (manual) | DataForSEO API |
| Open Strategy Builder | NO | Authoricy DB (latest analysis) |
| Reorder threads | NO | Updates strategy in Authoricy DB |
| Assign keywords | NO | Updates strategy in Authoricy DB |
| Create/edit topics | NO | Updates strategy in Authoricy DB |
| Export to Monok | NO | Reads from Authoricy DB |

### Lovable Frontend Responsibilities

**DOES:**
- UI rendering (drag & drop, lists, forms)
- Ephemeral UI state (what's being dragged, hover states)
- API calls to Authoricy backend
- Display data from API responses

**DOES NOT:**
- Store analysis data (keywords, SERP, etc.)
- Trigger new analyses
- Cache keyword data between sessions
- Make decisions about data - only displays what API returns

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                         AUTHORICY ENGINE                              │
│                                                                       │
│  ┌─────────────┐    ┌─────────────────┐    ┌──────────────────────┐ │
│  │   Phase 1-4 │───▶│    Database     │───▶│   Strategy Builder   │ │
│  │   Collection│    │   (Keywords,    │    │   API Endpoints      │ │
│  │             │    │   parent_topic, │    │                      │ │
│  └─────────────┘    │   SERP titles,  │    └──────────┬───────────┘ │
│                     │   opportunities)│               │              │
│                     └─────────────────┘               │              │
└───────────────────────────────────────────────────────┼──────────────┘
                                                        │
                                                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         LOVABLE FRONTEND                              │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    STRATEGY BUILDER UI                           │ │
│  │                                                                  │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │ │
│  │  │  THREADS    │  │   TOPICS    │  │      KEYWORDS           │ │ │
│  │  │  (Clusters) │  │  (Content)  │  │  (Mapped to threads)    │ │ │
│  │  │             │  │             │  │                         │ │ │
│  │  │  [Thread 1] │  │  [Topic A]  │  │  [kw1] [kw2] [kw3]     │ │ │
│  │  │  [Thread 2] │  │  [Topic B]  │  │  [kw4] [kw5]           │ │ │
│  │  │  + Add      │  │  [Topic C]  │  │                         │ │ │
│  │  │             │  │  + Add      │  │  Drag keywords to       │ │ │
│  │  │  Drag to    │  │             │  │  assign to threads      │ │ │
│  │  │  reorder    │  │  Drag to    │  │                         │ │ │
│  │  └─────────────┘  │  assign     │  └─────────────────────────┘ │ │
│  │                   └─────────────┘                               │ │
│  │                                                                  │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  CUSTOM INSTRUCTIONS (per thread)                           │ │ │
│  │  │  [Rich text editor for Monok guidance]                      │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                  │ │
│  │  [APPROVE STRATEGY] ──▶ [EXPORT TO MONOK]                       │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         MONOK EXPORT                                  │
│                                                                       │
│  Format 1: Structured JSON (for future API/automation)               │
│  Format 2: Human-readable display (for manual copy/paste)            │
│  Format 3: CSV/spreadsheet (for import into other tools)             │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## DATA STRUCTURES

### Core Entities

#### 1. Thread (Topic Cluster)
```python
@dataclass
class Thread:
    """A topic cluster representing a market position to own."""
    id: UUID
    strategy_id: UUID

    # Identity
    name: str                          # "Enterprise Project Management"
    slug: str                          # "enterprise-project-management"

    # Hierarchy
    position: int                      # Display order (for drag & drop)

    # Metrics (aggregated from keywords)
    total_search_volume: int           # Sum of all keyword volumes
    total_traffic_potential: int       # Estimated traffic if ranking
    avg_difficulty: float              # Average personalized difficulty
    opportunity_score: float           # Aggregate opportunity score

    # Keywords (assigned to this thread)
    keyword_ids: List[UUID]            # References to keywords table

    # Status
    status: str                        # "suggested" | "confirmed" | "rejected"
    priority: int                      # 1-5 (P1 = highest)

    # Format recommendation (SERP-derived)
    recommended_format: Optional[str]   # "listicle" | "guide" | "comparison" | etc.
    format_confidence: Optional[float]  # 0-1, based on SERP evidence
    format_evidence: Optional[Dict]     # {"titles_analyzed": 10, "pattern": "X of Y"}

    # Custom instructions for Monok
    custom_instructions: Optional[str]  # Rich text with strategic guidance

    # Timestamps
    created_at: datetime
    updated_at: datetime
```

#### 2. Topic (Content Piece)
```python
@dataclass
class Topic:
    """
    A content piece within a thread.

    NOTE: Topics are simple list items. Format recommendations
    belong in Thread.custom_instructions, NOT on individual topics.
    """
    id: UUID
    thread_id: UUID

    # Identity
    name: str                          # "Top 10 Enterprise PM Tools 2025"
    slug: str                          # "top-10-enterprise-pm-tools-2025"

    # Hierarchy
    position: int                      # Display order within thread

    # Target keyword (primary)
    primary_keyword_id: Optional[UUID]  # Main keyword to target
    primary_keyword: Optional[str]      # Denormalized for display

    # Content specification
    content_type: str                  # "pillar" | "cluster" | "supporting"
    # NO format field here - format recommendations go in Thread.custom_instructions

    # Status
    status: str                        # "suggested" | "confirmed" | "in_production" | "published"

    # URLs
    target_url: Optional[str]          # Where this content will live
    existing_url: Optional[str]        # If updating existing content

    # Timestamps
    created_at: datetime
    updated_at: datetime
```

#### 3. Strategy (Container)
```python
@dataclass
class Strategy:
    """Container for a complete strategy."""
    id: UUID
    domain_id: UUID
    analysis_run_id: UUID              # Source analysis

    # Identity
    name: str                          # "Q1 2025 Content Strategy"
    version: int                       # For versioning

    # Status
    status: str                        # "draft" | "approved" | "exported"
    approved_at: Optional[datetime]
    approved_by: Optional[str]

    # Threads
    threads: List[Thread]

    # Export history
    exports: List[StrategyExport]

    # Timestamps
    created_at: datetime
    updated_at: datetime
```

#### 4. Monok Export Format
```python
@dataclass
class MonokPackage:
    """Export format for Monok content production."""

    # Metadata
    export_id: str
    strategy_id: UUID
    domain: str
    exported_at: datetime
    exported_by: str

    # Threads (in priority order)
    threads: List[MonokThread]

    # Summary
    total_threads: int
    total_topics: int
    total_keywords: int

@dataclass
class MonokThread:
    """Single thread in Monok format."""

    # Identity (for Monok's system)
    thread_name: str                   # Display name
    thread_id: str                     # Unique identifier

    # Priority
    priority: int                      # 1-5

    # Keywords (thread-level, not per-topic)
    keywords: List[MonokKeyword]

    # Topics (content pieces to create)
    topics: List[MonokTopic]

    # Strategic guidance
    custom_instructions: str           # Rich text with:
                                       # - Positioning guidance
                                       # - Differentiation points
                                       # - Competitor insights
                                       # - Format recommendations
                                       # - Target audience notes

@dataclass
class MonokTopic:
    """
    Single topic in Monok format.

    NOTE: No format field here. Format recommendations
    are included in MonokThread.custom_instructions.
    """
    topic_name: str
    primary_keyword: str
    content_type: str                  # "pillar" | "cluster" | "supporting"
    target_url: str

@dataclass
class MonokKeyword:
    """Keyword in Monok format."""
    keyword: str
    search_volume: int
    difficulty: int                    # Personalized difficulty
    opportunity_score: float
    intent: str                        # "informational" | "transactional" | etc.
```

---

## API ENDPOINTS (For Lovable Frontend)

### Strategy Management

```
# List strategies for a domain
GET /api/strategies?domain_id={uuid}
Response: { strategies: [Strategy] }

# Get single strategy with all threads/topics
GET /api/strategies/{strategy_id}
Response: { strategy: Strategy, threads: [Thread], topics: [Topic] }

# Create new strategy from analysis
POST /api/strategies
Body: { domain_id, analysis_run_id, name }
Response: { strategy: Strategy }

# Update strategy
PATCH /api/strategies/{strategy_id}
Body: { name?, status? }
Response: { strategy: Strategy }

# Delete strategy
DELETE /api/strategies/{strategy_id}
```

### Thread Management

```
# List threads for strategy
GET /api/strategies/{strategy_id}/threads
Response: { threads: [Thread] }

# Create thread
POST /api/strategies/{strategy_id}/threads
Body: { name, position?, keyword_ids? }
Response: { thread: Thread }

# Update thread (including reorder)
PATCH /api/threads/{thread_id}
Body: { name?, position?, priority?, custom_instructions?, keyword_ids? }
Response: { thread: Thread }

# Delete thread
DELETE /api/threads/{thread_id}

# Reorder threads (batch)
POST /api/strategies/{strategy_id}/threads/reorder
Body: { thread_ids: [uuid, uuid, ...] }  # New order
Response: { threads: [Thread] }

# Assign keywords to thread
POST /api/threads/{thread_id}/keywords
Body: { keyword_ids: [uuid, uuid, ...] }
Response: { thread: Thread }
```

### Topic Management

```
# List topics for thread
GET /api/threads/{thread_id}/topics
Response: { topics: [Topic] }

# Create topic
POST /api/threads/{thread_id}/topics
Body: { name, content_type, primary_keyword_id? }
Response: { topic: Topic }

# Update topic
PATCH /api/topics/{topic_id}
Body: { name?, position?, status?, target_url? }
Response: { topic: Topic }

# Delete topic
DELETE /api/topics/{topic_id}

# Reorder topics (batch)
POST /api/threads/{thread_id}/topics/reorder
Body: { topic_ids: [uuid, uuid, ...] }
Response: { topics: [Topic] }
```

### Data Endpoints (Read-only, from collection)

```
# Get available keywords for a domain (from collection)
GET /api/domains/{domain_id}/keywords?
    analysis_run_id={uuid}&
    sort_by=opportunity_score|volume|difficulty&
    intent=transactional|informational|...&
    assigned=true|false&   # Filter by already assigned to threads
    limit=100
Response: {
    keywords: [{
        id, keyword, search_volume, difficulty,
        opportunity_score, intent, parent_topic,
        assigned_thread_id  # null if unassigned
    }],
    total: int,
    unassigned_count: int
}

# Get suggested clusters (from parent_topic)
GET /api/domains/{domain_id}/suggested-clusters?analysis_run_id={uuid}
Response: {
    clusters: [{
        parent_topic: str,
        keyword_count: int,
        total_volume: int,
        keywords: [keyword_id, ...]
    }]
}

# Get SERP-based format recommendations
GET /api/keywords/{keyword_id}/format-recommendation
Response: {
    keyword: str,
    recommended_format: str,  # "listicle" | "guide" | etc.
    confidence: float,
    evidence: {
        titles_analyzed: int,
        top_patterns: [{pattern, count}]
    }
}
```

### Export Endpoints

```
# Export strategy to Monok format
POST /api/strategies/{strategy_id}/export
Body: { format: "monok_json" | "monok_display" | "csv" }
Response: {
    export_id: str,
    format: str,
    data: MonokPackage | string,  # JSON or formatted string
    download_url: str  # For file download
}

# Get export history
GET /api/strategies/{strategy_id}/exports
Response: { exports: [{ id, format, exported_at, exported_by }] }
```

---

## MONOK EXPORT FORMATS

### Format 1: Structured JSON (for future API/automation)

```json
{
  "export_id": "exp_abc123",
  "domain": "example.com",
  "strategy_name": "Q1 2025 Content Strategy",
  "exported_at": "2025-01-26T10:30:00Z",
  "threads": [
    {
      "thread_name": "Enterprise Project Management",
      "thread_id": "thread_001",
      "priority": 1,
      "keywords": [
        {
          "keyword": "enterprise project management software",
          "search_volume": 2400,
          "difficulty": 52,
          "opportunity_score": 78.5,
          "intent": "commercial"
        },
        {
          "keyword": "best project management for enterprises",
          "search_volume": 1200,
          "difficulty": 48,
          "opportunity_score": 82.1,
          "intent": "commercial"
        }
      ],
      "topics": [
        {
          "topic_name": "Enterprise Project Management Software Guide",
          "primary_keyword": "enterprise project management software",
          "content_type": "pillar",
          "target_url": "/solutions/enterprise-project-management/"
        },
        {
          "topic_name": "10 Best Enterprise PM Tools Compared",
          "primary_keyword": "best project management for enterprises",
          "content_type": "cluster",
          "target_url": "/blog/best-enterprise-pm-tools/"
        }
      ],
      "custom_instructions": "## Strategic Context\n\nThis thread targets enterprise buyers in the evaluation phase...\n\n## Differentiation\n- Emphasize scalability features\n- Highlight security certifications\n- Include ROI calculator elements\n\n## Competitors to Address\n- monday.com (incumbent leader)\n- Asana Enterprise (direct competitor)\n\n## Content Angle\nPosition as the 'IT-approved choice' with enterprise-grade security..."
    }
  ],
  "summary": {
    "total_threads": 5,
    "total_topics": 23,
    "total_keywords": 87,
    "total_volume": 45000,
    "estimated_traffic_potential": 8500
  }
}
```

### Format 2: Human-Readable Display (for manual copy/paste)

```
═══════════════════════════════════════════════════════════════════
CONTENT STRATEGY: example.com
Q1 2025 Content Strategy
Exported: January 26, 2025
═══════════════════════════════════════════════════════════════════

───────────────────────────────────────────────────────────────────
THREAD 1: Enterprise Project Management [Priority: P1]
───────────────────────────────────────────────────────────────────

KEYWORDS (assign to all content in this thread):
• enterprise project management software (2,400 vol, KD 52, Opp: 78.5)
• best project management for enterprises (1,200 vol, KD 48, Opp: 82.1)
• enterprise pm tools comparison (800 vol, KD 45, Opp: 75.2)

TOPICS TO CREATE:

1. [PILLAR] Enterprise Project Management Software Guide
   Primary KW: enterprise project management software
   Target URL: /solutions/enterprise-project-management/

2. [CLUSTER] 10 Best Enterprise PM Tools Compared
   Primary KW: best project management for enterprises
   Target URL: /blog/best-enterprise-pm-tools/

CUSTOM INSTRUCTIONS FOR MONOK:
─────────────────────────────
## Strategic Context

This thread targets enterprise buyers in the evaluation phase. They're
comparing solutions and need ROI justification for procurement.

## Differentiation
- Emphasize scalability features (10,000+ users)
- Highlight security certifications (SOC 2, ISO 27001)
- Include ROI calculator elements

## Competitors to Address
- monday.com: Incumbent leader, highlight our enterprise features
- Asana Enterprise: Direct competitor, differentiate on integrations

## Content Angle
Position as the 'IT-approved choice' with enterprise-grade security
and compliance. Avoid startup/SMB messaging.

───────────────────────────────────────────────────────────────────
THREAD 2: Agile Transformation [Priority: P2]
───────────────────────────────────────────────────────────────────

[... continues ...]
```

### Format 3: CSV/Spreadsheet

```csv
thread_name,thread_priority,topic_name,content_type,primary_keyword,search_volume,difficulty,target_url
Enterprise Project Management,P1,Enterprise PM Software Guide,pillar,enterprise project management software,2400,52,/solutions/enterprise-project-management/
Enterprise Project Management,P1,10 Best Enterprise PM Tools,cluster,best project management for enterprises,1200,48,/blog/best-enterprise-pm-tools/
Agile Transformation,P2,Agile at Scale Guide,pillar,agile transformation enterprise,1800,55,/solutions/agile-transformation/
```

Note: Format recommendations are in custom_instructions (not in CSV - too complex for flat format).

---

## DATA REQUIREMENTS (ALREADY IMPLEMENTED)

### What's Now Available (after our fixes)

| Data | Source | Status |
|------|--------|--------|
| Keywords | Phase 2 collection | ✅ Exists |
| Search volume | DataForSEO | ✅ Exists |
| Difficulty | DataForSEO | ✅ Exists |
| Intent | DataForSEO | ✅ Exists |
| Opportunity score | Calculated | ✅ **JUST ADDED** |
| Parent topic | DataForSEO | ✅ **JUST ADDED** |
| SERP titles | Phase 4 live SERP | ✅ **JUST ADDED** |

### How These Enable Strategy Builder

1. **parent_topic** → Automatic cluster suggestions
   - Group keywords by parent_topic
   - Suggest thread names from parent_topic values

2. **SERP titles** → Format recommendations
   - Analyze title patterns (regex)
   - "X Best Y" → listicle
   - "How to X" → how-to guide
   - "X vs Y" → comparison

3. **opportunity_score** → Prioritization
   - Sort keywords by opportunity
   - Calculate thread-level opportunity
   - Suggest priority rankings

---

## GRACEFUL DEGRADATION

### Data Availability Levels

| Level | parent_topic | SERP titles | opportunity_score | Experience |
|-------|--------------|-------------|-------------------|------------|
| Full | ✅ | ✅ | ✅ | All features, AI suggestions |
| Partial | ✅ | ❌ | ✅ | Clusters work, no format recommendations |
| Minimal | ❌ | ❌ | ✅ | Manual clustering only, priority scoring |
| Basic | ❌ | ❌ | ❌ | Pure manual mode, raw keyword list |

### Degradation Behavior

```python
def get_cluster_suggestions(domain_id, analysis_run_id):
    """Get cluster suggestions with graceful degradation."""
    keywords = get_keywords(domain_id, analysis_run_id)

    # Try parent_topic clustering first
    if any(kw.parent_topic for kw in keywords):
        return cluster_by_parent_topic(keywords)

    # Fallback: No suggestions, user creates manually
    return {
        "mode": "manual",
        "message": "No clustering data available. Create threads manually.",
        "keywords": keywords
    }

def get_format_recommendation(keyword_id):
    """Get format recommendation with graceful degradation."""
    serp_data = get_serp_data(keyword_id)

    if serp_data and serp_data.organic_results:
        titles = [r.title for r in serp_data.organic_results]
        return analyze_title_patterns(titles)

    # Fallback: No recommendation
    return {
        "recommended_format": None,
        "confidence": 0,
        "message": "No SERP data available for format recommendation."
    }
```

---

## IMPLEMENTATION PHASES

### Phase 1: Database Schema (Day 1)
- Add `strategies` table
- Add `strategy_threads` table
- Add `strategy_topics` table
- Add `strategy_exports` table
- Migrations

### Phase 2: Core API Endpoints (Days 2-3)
- Strategy CRUD
- Thread CRUD with reordering
- Topic CRUD with reordering
- Keyword assignment

### Phase 3: Data Endpoints (Day 4)
- Keyword listing with filters
- Cluster suggestions (from parent_topic)
- Format recommendations (from SERP titles)

### Phase 4: Export Functionality (Day 5)
- Monok JSON format
- Monok display format
- CSV export

### Phase 5: Integration Testing (Day 6)
- End-to-end flow testing
- Lovable frontend mock testing
- Export validation

---

## SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Strategy creation time | <10 minutes for 5-thread strategy |
| Cluster suggestion accuracy | >70% of suggestions used by user |
| Export format correctness | 100% valid, no manual fixes needed |
| API response time | <500ms for all endpoints |
| Drag & drop operations | Instant visual feedback |

---

## DEPENDENCIES

### Backend (Authoricy Engine)
- FastAPI endpoints (this spec)
- PostgreSQL database (existing)
- Existing keyword/SERP data (Phase 1-4 collection)

### Frontend (Lovable)
- React-based drag & drop UI
- Consumes API endpoints defined here
- Handles local state for drag operations
- Exports trigger backend endpoint

### Monok Integration
- Manual copy/paste initially
- JSON format ready for future API
- Browser automation friendly (structured output)

---

*This specification is ready for implementation. The 3 data fixes (parent_topic, SERP titles, opportunity_score) have already been committed.*

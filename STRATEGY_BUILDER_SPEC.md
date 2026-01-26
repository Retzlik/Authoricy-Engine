# Strategy Builder + Monok Export Specification
## Complete Scoping Document v2.0

**Created:** January 2026
**Updated:** January 2026 (v2.0 - Enterprise-grade architecture)
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
- **Keyboard shortcuts** for power users
- **Bulk operations** (select multiple, assign to thread)
- **Real-time collaboration ready** (future: multiple users)

Data structures must support:
- Sub-second API responses for all operations
- Efficient reordering without full reload
- Partial updates (PATCH, not PUT)
- Conflict detection for concurrent edits (optimistic locking)
- Cursor-based pagination for large datasets

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
│   Lovable calls API → Authoricy returns analysis data →             │
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
| Open Strategy Builder | NO | Authoricy DB (selected analysis) |
| Reorder threads | NO | Updates strategy in Authoricy DB |
| Assign keywords | NO | Updates strategy in Authoricy DB |
| Create/edit topics | NO | Updates strategy in Authoricy DB |
| Export to Monok | NO | Reads from Authoricy DB |

### Analysis Selection

Users may have **multiple analyses** for a domain. The Strategy Builder must:

1. **List available analyses** when creating a strategy:
```
GET /api/domains/{domain_id}/analyses
Response: {
    analyses: [{
        id: UUID,
        created_at: datetime,
        status: "completed",
        keyword_count: int,
        market: str,
        depth: str,  # "testing" | "balanced" | etc.
    }]
}
```

2. **Strategy is bound to a specific analysis_run_id**:
   - Keywords come from that analysis only
   - User can create multiple strategies from different analyses
   - If analysis is deleted, strategy becomes "orphaned" (read-only)

3. **Analysis staleness indicator**:
   - Show "Analysis is X days old" in UI
   - Suggest re-running if >30 days old
   - Never auto-trigger - user decides

### Lovable Frontend Responsibilities

**DOES:**
- UI rendering (drag & drop, lists, forms)
- Ephemeral UI state (what's being dragged, hover states)
- API calls to Authoricy backend
- Display data from API responses
- Optimistic UI updates (update locally, sync to backend)
- Handle version conflicts gracefully

**DOES NOT:**
- Store analysis data (keywords, SERP, etc.)
- Trigger new analyses
- Cache keyword data between sessions
- Make decisions about data - only displays what API returns

---

## DATABASE SCHEMA

### New Tables

```sql
-- ============================================================================
-- STRATEGIES
-- ============================================================================
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    analysis_run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE RESTRICT,

    -- Identity
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Versioning (for optimistic locking)
    version INTEGER NOT NULL DEFAULT 1,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, approved, archived
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Soft delete
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMP,

    CONSTRAINT valid_status CHECK (status IN ('draft', 'approved', 'archived'))
);

CREATE INDEX idx_strategy_domain ON strategies(domain_id, created_at DESC);
CREATE INDEX idx_strategy_status ON strategies(domain_id, status);

-- ============================================================================
-- THREADS (Topic Clusters)
-- ============================================================================
CREATE TABLE strategy_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,

    -- Identity
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),

    -- Ordering (lexicographic for efficient reordering)
    -- Uses fractional indexing: "a", "b", "c" or "aV", "aW", "aX" between "a" and "b"
    position VARCHAR(50) NOT NULL,

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, confirmed, rejected
    priority INTEGER CHECK (priority BETWEEN 1 AND 5),

    -- SERP-derived recommendations (cached, not user-editable here)
    recommended_format VARCHAR(50),
    format_confidence FLOAT,
    format_evidence JSONB,

    -- Custom instructions (structured)
    custom_instructions JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_thread_status CHECK (status IN ('draft', 'confirmed', 'rejected'))
);

CREATE INDEX idx_thread_strategy ON strategy_threads(strategy_id, position);
CREATE UNIQUE INDEX idx_thread_position ON strategy_threads(strategy_id, position);

-- ============================================================================
-- THREAD-KEYWORD JUNCTION TABLE (Many-to-Many)
-- ============================================================================
CREATE TABLE thread_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES strategy_threads(id) ON DELETE CASCADE,
    keyword_id UUID NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,

    -- Ordering within thread (lexicographic)
    position VARCHAR(50) NOT NULL,

    -- When assigned
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Unique constraint: keyword can only be in one thread per strategy
    -- (enforced via trigger since we need strategy_id from thread)

    UNIQUE(thread_id, keyword_id)
);

CREATE INDEX idx_thread_keyword_thread ON thread_keywords(thread_id, position);
CREATE INDEX idx_thread_keyword_keyword ON thread_keywords(keyword_id);

-- Trigger to ensure keyword only assigned to one thread per strategy
CREATE OR REPLACE FUNCTION check_keyword_single_thread()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM thread_keywords tk
        JOIN strategy_threads t ON tk.thread_id = t.id
        WHERE tk.keyword_id = NEW.keyword_id
        AND t.strategy_id = (SELECT strategy_id FROM strategy_threads WHERE id = NEW.thread_id)
        AND tk.thread_id != NEW.thread_id
    ) THEN
        RAISE EXCEPTION 'Keyword already assigned to another thread in this strategy';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ensure_keyword_single_thread
BEFORE INSERT OR UPDATE ON thread_keywords
FOR EACH ROW EXECUTE FUNCTION check_keyword_single_thread();

-- ============================================================================
-- TOPICS (Content Pieces)
-- ============================================================================
CREATE TABLE strategy_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES strategy_threads(id) ON DELETE CASCADE,

    -- Identity
    name VARCHAR(500) NOT NULL,
    slug VARCHAR(255),

    -- Ordering (lexicographic)
    position VARCHAR(50) NOT NULL,

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,

    -- Primary keyword (optional, references keywords table)
    primary_keyword_id UUID REFERENCES keywords(id) ON DELETE SET NULL,
    primary_keyword VARCHAR(500),  -- Denormalized for display

    -- Content type
    content_type VARCHAR(20) NOT NULL DEFAULT 'cluster',  -- pillar, cluster, supporting

    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'draft',  -- draft, confirmed, in_production, published

    -- URLs
    target_url VARCHAR(2000),
    existing_url VARCHAR(2000),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_content_type CHECK (content_type IN ('pillar', 'cluster', 'supporting')),
    CONSTRAINT valid_topic_status CHECK (status IN ('draft', 'confirmed', 'in_production', 'published'))
);

CREATE INDEX idx_topic_thread ON strategy_topics(thread_id, position);
CREATE UNIQUE INDEX idx_topic_position ON strategy_topics(thread_id, position);

-- ============================================================================
-- STRATEGY EXPORTS
-- ============================================================================
CREATE TABLE strategy_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,

    -- Export details
    format VARCHAR(20) NOT NULL,  -- monok_json, monok_display, csv

    -- Snapshot of what was exported (for audit trail)
    exported_data JSONB NOT NULL,

    -- Metadata
    exported_at TIMESTAMP NOT NULL DEFAULT NOW(),
    exported_by VARCHAR(255),

    -- File storage (if applicable)
    file_path VARCHAR(1000),
    file_size_bytes INTEGER
);

CREATE INDEX idx_export_strategy ON strategy_exports(strategy_id, exported_at DESC);

-- ============================================================================
-- ACTIVITY LOG (for audit trail, not undo/redo)
-- ============================================================================
CREATE TABLE strategy_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,

    -- What happened
    action VARCHAR(50) NOT NULL,  -- created, updated, thread_added, keyword_assigned, exported, etc.
    entity_type VARCHAR(30),      -- strategy, thread, topic, keyword
    entity_id UUID,

    -- Who did it
    user_id VARCHAR(255),

    -- Details
    details JSONB,

    -- When
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activity_strategy ON strategy_activity_log(strategy_id, created_at DESC);
```

### Lexicographic Ordering Explained

Instead of integer positions (1, 2, 3...), we use lexicographic strings that allow inserting between any two items without renumbering:

```
Initial:     "a", "b", "c"
Insert between a and b: "a", "aU", "b", "c"
Insert between aU and b: "a", "aU", "am", "b", "c"
```

**Algorithm:**
```python
def generate_position_between(before: str | None, after: str | None) -> str:
    """
    Generate a position string that sorts between 'before' and 'after'.

    Uses base-52 (a-z, A-Z) for compact strings.
    """
    if before is None and after is None:
        return "a"
    if before is None:
        # Insert at beginning - prepend character before first
        return chr(ord(after[0]) - 1) if after[0] > 'a' else 'A' + after
    if after is None:
        # Insert at end - append character
        return before + "a"

    # Insert between - find midpoint
    # ... (implementation uses fractional indexing algorithm)
```

**Benefits:**
- Insert between any two items: O(1) - no renumbering
- Reorder any item: O(1) - just update one position
- Concurrent-safe: No race conditions on position numbers

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

    # Ordering (lexicographic string)
    position: str                      # "a", "aU", "b", etc.

    # Versioning (for optimistic locking)
    version: int                       # Incremented on each update

    # Status
    status: str                        # "draft" | "confirmed" | "rejected"
    priority: Optional[int]            # 1-5 (P1 = highest)

    # SERP-derived recommendations (read-only, from analysis)
    recommended_format: Optional[str]
    format_confidence: Optional[float]
    format_evidence: Optional[Dict]

    # Custom instructions (STRUCTURED - see below)
    custom_instructions: CustomInstructions

    # Timestamps
    created_at: datetime
    updated_at: datetime

@dataclass
class CustomInstructions:
    """
    Structured custom instructions for Monok.

    Structured fields enable:
    - Consistent formatting in exports
    - Validation of required fields
    - UI forms instead of free-text
    - Future: AI-assisted generation of each section
    """
    strategic_context: str             # Market position, buyer journey stage
    differentiation_points: List[str]  # How to stand out
    competitors_to_address: List[str]  # Specific competitors to mention/counter
    content_angle: str                 # Positioning/messaging approach
    format_recommendations: str        # SERP-derived format guidance
    target_audience: str               # Who is this content for
    additional_notes: str              # Free-form notes
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
    slug: str

    # Ordering (lexicographic string)
    position: str                      # "a", "aU", "b", etc.

    # Versioning
    version: int

    # Target keyword (primary)
    primary_keyword_id: Optional[UUID]
    primary_keyword: Optional[str]     # Denormalized for display

    # Content type
    content_type: str                  # "pillar" | "cluster" | "supporting"

    # Status
    status: str                        # "draft" | "confirmed" | "in_production" | "published"

    # URLs
    target_url: Optional[str]
    existing_url: Optional[str]

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
    analysis_run_id: UUID              # Source analysis (IMMUTABLE after creation)

    # Identity
    name: str                          # "Q1 2025 Content Strategy"
    description: Optional[str]

    # Versioning
    version: int                       # For optimistic locking

    # Status
    status: str                        # "draft" | "approved" | "archived"
    approved_at: Optional[datetime]
    approved_by: Optional[str]

    # Soft delete
    is_archived: bool
    archived_at: Optional[datetime]

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Aggregations (calculated on read or via background job)
    # NOT stored - computed from thread_keywords join
```

#### 4. ThreadKeyword (Junction)
```python
@dataclass
class ThreadKeyword:
    """Junction table for thread-keyword many-to-many relationship."""
    id: UUID
    thread_id: UUID
    keyword_id: UUID
    position: str                      # Ordering within thread
    assigned_at: datetime
```

---

## AGGREGATIONS

### Thread-Level Metrics

Thread metrics are **computed on read**, not stored:

```python
def get_thread_with_metrics(thread_id: UUID) -> ThreadWithMetrics:
    """
    Compute thread metrics from assigned keywords.

    Performance: ~5ms for 100 keywords (indexed join)
    """
    thread = get_thread(thread_id)
    keywords = get_thread_keywords(thread_id)  # JOIN thread_keywords + keywords

    return ThreadWithMetrics(
        **thread.__dict__,
        total_search_volume=sum(kw.search_volume or 0 for kw in keywords),
        total_traffic_potential=sum(kw.estimated_traffic or 0 for kw in keywords),
        avg_difficulty=mean([kw.keyword_difficulty or 50 for kw in keywords]),
        avg_opportunity_score=mean([kw.opportunity_score or 0 for kw in keywords]),
        keyword_count=len(keywords),
    )
```

**Why compute on read (not store)?**
- Keywords can be reassigned between threads
- Keyword data can be updated independently
- Avoids stale aggregations
- JOIN is fast with proper indexes (<10ms)

**For strategy-level summary:**
```python
def get_strategy_summary(strategy_id: UUID) -> StrategySummary:
    """
    Aggregate across all threads - slightly slower but still fast.

    Performance: ~20ms for 10 threads, 500 keywords
    """
    return StrategySummary(
        total_threads=count_threads(strategy_id),
        total_topics=count_topics(strategy_id),
        total_keywords=count_keywords(strategy_id),  # COUNT DISTINCT
        total_search_volume=sum_search_volume(strategy_id),
        # ... etc
    )
```

---

## API ENDPOINTS

### Strategy Management

```
# List strategies for a domain
GET /api/domains/{domain_id}/strategies?
    status=draft|approved|archived&
    include_archived=false
Response: {
    strategies: [{
        id, name, status, version, created_at, updated_at,
        analysis_run_id, analysis_created_at,
        thread_count, topic_count, keyword_count  # Aggregations
    }]
}

# Get single strategy with threads and metrics
GET /api/strategies/{strategy_id}
Response: {
    strategy: Strategy,
    threads: [ThreadWithMetrics],  # Includes computed metrics
    analysis: {                    # Info about source analysis
        id, created_at, keyword_count, market
    }
}

# Create new strategy from analysis
POST /api/strategies
Body: {
    domain_id: UUID,
    analysis_run_id: UUID,
    name: str,
    description?: str
}
Response: { strategy: Strategy }

# Update strategy (with optimistic locking)
PATCH /api/strategies/{strategy_id}
Body: {
    name?: str,
    description?: str,
    status?: str,
    version: int  # REQUIRED - must match current version
}
Response: { strategy: Strategy }
Error 409: { error: "version_conflict", current_version: int }

# Duplicate strategy
POST /api/strategies/{strategy_id}/duplicate
Body: { name: str }
Response: { strategy: Strategy }  # New strategy with copied threads/topics/keywords

# Archive strategy (soft delete)
POST /api/strategies/{strategy_id}/archive
Response: { strategy: Strategy }

# Restore archived strategy
POST /api/strategies/{strategy_id}/restore
Response: { strategy: Strategy }

# Hard delete (only if archived)
DELETE /api/strategies/{strategy_id}
```

### Thread Management

```
# List threads for strategy (ordered by position)
GET /api/strategies/{strategy_id}/threads
Response: {
    threads: [ThreadWithMetrics]  # Includes computed metrics
}

# Create thread
POST /api/strategies/{strategy_id}/threads
Body: {
    name: str,
    after_thread_id?: UUID,  # Insert after this thread (null = beginning)
    priority?: int
}
Response: { thread: ThreadWithMetrics }

# Update thread (with optimistic locking)
PATCH /api/threads/{thread_id}
Body: {
    name?: str,
    status?: str,
    priority?: int,
    custom_instructions?: CustomInstructions,
    version: int  # REQUIRED
}
Response: { thread: ThreadWithMetrics }
Error 409: { error: "version_conflict", current_version: int }

# Move thread to new position
POST /api/threads/{thread_id}/move
Body: {
    after_thread_id: UUID | null  # null = move to beginning
}
Response: { thread: Thread }

# Delete thread
DELETE /api/threads/{thread_id}

# Assign keywords to thread (bulk)
POST /api/threads/{thread_id}/keywords
Body: {
    keyword_ids: [UUID, UUID, ...],
    version: int  # Thread version for locking
}
Response: { thread: ThreadWithMetrics }
Error 409: { error: "version_conflict" }
Error 400: { error: "keyword_already_assigned", keyword_id: UUID, thread_name: str }

# Remove keywords from thread (bulk)
DELETE /api/threads/{thread_id}/keywords
Body: { keyword_ids: [UUID, ...] }
Response: { thread: ThreadWithMetrics }

# Get keywords for thread
GET /api/threads/{thread_id}/keywords
Response: {
    keywords: [{
        id, keyword, search_volume, difficulty,
        opportunity_score, intent, parent_topic,
        position  # Within this thread
    }]
}
```

### Topic Management

```
# List topics for thread (ordered by position)
GET /api/threads/{thread_id}/topics
Response: { topics: [Topic] }

# Create topic
POST /api/threads/{thread_id}/topics
Body: {
    name: str,
    content_type: str,
    primary_keyword_id?: UUID,
    after_topic_id?: UUID  # Insert position
}
Response: { topic: Topic }

# Update topic (with optimistic locking)
PATCH /api/topics/{topic_id}
Body: {
    name?: str,
    content_type?: str,
    status?: str,
    target_url?: str,
    primary_keyword_id?: UUID,
    version: int  # REQUIRED
}
Response: { topic: Topic }
Error 409: { error: "version_conflict" }

# Move topic to new position (within same thread)
POST /api/topics/{topic_id}/move
Body: { after_topic_id: UUID | null }
Response: { topic: Topic }

# Move topic to different thread
POST /api/topics/{topic_id}/move-to-thread
Body: {
    thread_id: UUID,
    after_topic_id?: UUID
}
Response: { topic: Topic }

# Delete topic
DELETE /api/topics/{topic_id}
```

### Keyword Endpoints (Read-only, from analysis)

```
# Get available keywords for strategy (with cursor pagination)
GET /api/strategies/{strategy_id}/available-keywords?
    cursor={opaque_cursor}&
    limit=50&
    sort_by=opportunity_score|volume|difficulty|keyword&
    sort_dir=asc|desc&
    intent=transactional|informational|commercial|navigational&
    min_volume=100&
    max_difficulty=70&
    search=project%20management&
    assigned=true|false|all
Response: {
    keywords: [{
        id, keyword, search_volume, difficulty,
        opportunity_score, intent, parent_topic,
        assigned_thread_id,  # null if unassigned
        assigned_thread_name
    }],
    pagination: {
        next_cursor: str | null,
        has_more: bool,
        total_count: int,        # Total matching filter
        unassigned_count: int    # Matching filter AND unassigned
    }
}

# Get suggested clusters (from parent_topic grouping)
GET /api/strategies/{strategy_id}/suggested-clusters
Response: {
    clusters: [{
        parent_topic: str,
        keyword_count: int,
        total_volume: int,
        avg_opportunity_score: float,
        sample_keywords: [str, str, str],  # Top 3 by opportunity
        keyword_ids: [UUID, ...]
    }],
    unclustered_count: int  # Keywords without parent_topic
}

# Get SERP-based format recommendation for a keyword
GET /api/keywords/{keyword_id}/format-recommendation
Response: {
    keyword: str,
    recommended_format: str | null,
    confidence: float,
    evidence: {
        titles_analyzed: int,
        patterns: [{
            pattern: str,      # "listicle", "how-to", "comparison"
            count: int,
            example_titles: [str, str]
        }]
    } | null
}
```

### Export Endpoints

```
# Validate strategy for export (check requirements)
POST /api/strategies/{strategy_id}/validate-export
Response: {
    is_valid: bool,
    errors: [{
        code: str,
        message: str,
        thread_id?: UUID
    }],
    warnings: [{
        code: str,
        message: str,
        thread_id?: UUID
    }]
}

# Export strategy to Monok format
POST /api/strategies/{strategy_id}/export
Body: {
    format: "monok_json" | "monok_display" | "csv",
    include_empty_threads: false  # Skip threads with no keywords
}
Response: {
    export_id: UUID,
    format: str,
    data: MonokPackage | string,
    download_url: str,
    validation: {
        warnings: [...]
    }
}

# Get export history
GET /api/strategies/{strategy_id}/exports?limit=10
Response: {
    exports: [{
        id, format, exported_at, exported_by,
        thread_count, topic_count, keyword_count
    }]
}

# Re-download previous export
GET /api/exports/{export_id}/download
Response: File download
```

### Activity Log

```
# Get activity log for strategy
GET /api/strategies/{strategy_id}/activity?
    limit=50&
    cursor={cursor}
Response: {
    activities: [{
        id, action, entity_type, entity_id,
        user_id, details, created_at
    }],
    pagination: { next_cursor, has_more }
}
```

### Analysis Selection

```
# List available analyses for a domain
GET /api/domains/{domain_id}/analyses?status=completed
Response: {
    analyses: [{
        id, created_at, status,
        keyword_count, market, language, depth,
        strategies_count  # How many strategies use this analysis
    }]
}
```

---

## VALIDATION RULES FOR EXPORT

### Export Requirements

```python
@dataclass
class ExportValidation:
    """Validation rules for Monok export."""

    # Hard requirements (export blocked if failed)
    errors: List[ValidationError]

    # Soft requirements (export allowed with warnings)
    warnings: List[ValidationWarning]

    is_valid: bool  # True if no errors

def validate_strategy_for_export(strategy_id: UUID) -> ExportValidation:
    """
    Validate strategy meets export requirements.
    """
    errors = []
    warnings = []

    strategy = get_strategy(strategy_id)
    threads = get_threads(strategy_id)

    # =====================
    # HARD REQUIREMENTS
    # =====================

    # 1. Strategy must be approved (or skip for drafts)
    # Actually, allow draft export for review purposes

    # 2. Must have at least one thread
    if len(threads) == 0:
        errors.append(ValidationError(
            code="no_threads",
            message="Strategy must have at least one thread"
        ))

    # 3. Each confirmed thread must have at least one keyword
    for thread in threads:
        if thread.status == "confirmed":
            keywords = get_thread_keywords(thread.id)
            if len(keywords) == 0:
                errors.append(ValidationError(
                    code="thread_no_keywords",
                    message=f"Thread '{thread.name}' has no keywords assigned",
                    thread_id=thread.id
                ))

    # 4. Each confirmed thread must have custom_instructions.strategic_context
    for thread in threads:
        if thread.status == "confirmed":
            if not thread.custom_instructions.get("strategic_context"):
                errors.append(ValidationError(
                    code="thread_no_context",
                    message=f"Thread '{thread.name}' missing strategic context",
                    thread_id=thread.id
                ))

    # =====================
    # SOFT REQUIREMENTS (warnings)
    # =====================

    # 1. Threads without topics
    for thread in threads:
        topics = get_thread_topics(thread.id)
        if len(topics) == 0:
            warnings.append(ValidationWarning(
                code="thread_no_topics",
                message=f"Thread '{thread.name}' has no topics defined",
                thread_id=thread.id
            ))

    # 2. Topics without target_url
    for thread in threads:
        for topic in get_thread_topics(thread.id):
            if not topic.target_url:
                warnings.append(ValidationWarning(
                    code="topic_no_url",
                    message=f"Topic '{topic.name}' has no target URL",
                    thread_id=thread.id
                ))

    # 3. Draft threads included
    draft_threads = [t for t in threads if t.status == "draft"]
    if draft_threads:
        warnings.append(ValidationWarning(
            code="draft_threads",
            message=f"{len(draft_threads)} threads are still in draft status"
        ))

    # 4. Missing format recommendations
    for thread in threads:
        if not thread.custom_instructions.get("format_recommendations"):
            warnings.append(ValidationWarning(
                code="no_format_recommendation",
                message=f"Thread '{thread.name}' has no format recommendations",
                thread_id=thread.id
            ))

    return ExportValidation(
        errors=errors,
        warnings=warnings,
        is_valid=len(errors) == 0
    )
```

---

## CUSTOM INSTRUCTIONS STRUCTURE

### Schema

```python
CustomInstructions = {
    # Required for export
    "strategic_context": str,        # 50-500 chars

    # Optional but recommended
    "differentiation_points": [str], # 1-10 items
    "competitors_to_address": [str], # 0-10 items
    "content_angle": str,            # 20-300 chars
    "format_recommendations": str,   # SERP-derived, can be auto-filled
    "target_audience": str,          # 20-200 chars

    # Free-form
    "additional_notes": str          # 0-2000 chars
}
```

### Example

```json
{
    "strategic_context": "This thread targets enterprise buyers in the evaluation phase. They're comparing solutions and need ROI justification for procurement.",
    "differentiation_points": [
        "Emphasize scalability features (10,000+ users)",
        "Highlight security certifications (SOC 2, ISO 27001)",
        "Include ROI calculator elements"
    ],
    "competitors_to_address": [
        "monday.com - Incumbent leader, highlight our enterprise features",
        "Asana Enterprise - Direct competitor, differentiate on integrations"
    ],
    "content_angle": "Position as the 'IT-approved choice' with enterprise-grade security and compliance. Avoid startup/SMB messaging.",
    "format_recommendations": "SERP analysis shows listicle format dominates (7/10 top results). Recommend 'X Best...' format with comparison tables.",
    "target_audience": "IT Directors and Project Management Office leads at companies with 500+ employees",
    "additional_notes": "Client has case study with Fortune 500 company - should be prominently featured."
}
```

### Auto-Population

When creating a thread, we can auto-populate some fields:

```python
def create_thread_with_suggestions(strategy_id, name, keyword_ids):
    """Create thread with AI-suggested custom instructions."""

    # Get keywords assigned to this thread
    keywords = get_keywords_by_ids(keyword_ids)

    # Auto-populate format_recommendations from SERP data
    format_rec = analyze_serp_patterns(keywords)

    custom_instructions = {
        "strategic_context": "",  # User must fill
        "differentiation_points": [],
        "competitors_to_address": [],
        "content_angle": "",
        "format_recommendations": format_rec.summary if format_rec else "",
        "target_audience": "",
        "additional_notes": ""
    }

    return create_thread(
        strategy_id=strategy_id,
        name=name,
        custom_instructions=custom_instructions
    )
```

---

## MONOK EXPORT FORMATS

### Format 1: Structured JSON

```json
{
    "export_id": "exp_abc123",
    "domain": "example.com",
    "strategy_name": "Q1 2025 Content Strategy",
    "strategy_id": "uuid",
    "analysis_id": "uuid",
    "analysis_date": "2025-01-20T10:00:00Z",
    "exported_at": "2025-01-26T10:30:00Z",
    "exported_by": "user@example.com",

    "threads": [
        {
            "thread_name": "Enterprise Project Management",
            "thread_id": "uuid",
            "priority": 1,
            "status": "confirmed",

            "keywords": [
                {
                    "keyword": "enterprise project management software",
                    "search_volume": 2400,
                    "difficulty": 52,
                    "opportunity_score": 78.5,
                    "intent": "commercial"
                }
            ],

            "topics": [
                {
                    "topic_name": "Enterprise Project Management Software Guide",
                    "primary_keyword": "enterprise project management software",
                    "content_type": "pillar",
                    "target_url": "/solutions/enterprise-project-management/",
                    "status": "confirmed"
                }
            ],

            "custom_instructions": {
                "strategic_context": "This thread targets enterprise buyers...",
                "differentiation_points": ["Scalability", "Security"],
                "competitors_to_address": ["monday.com", "Asana"],
                "content_angle": "IT-approved enterprise choice",
                "format_recommendations": "Listicle format recommended",
                "target_audience": "IT Directors, PMO leads",
                "additional_notes": ""
            }
        }
    ],

    "summary": {
        "total_threads": 5,
        "confirmed_threads": 4,
        "total_topics": 23,
        "total_keywords": 87,
        "total_search_volume": 45000
    },

    "validation": {
        "warnings": [
            {"code": "draft_threads", "message": "1 thread is still in draft"}
        ]
    }
}
```

### Format 2: Human-Readable Display

(Same as before - no changes needed)

### Format 3: CSV

(Same as before - no changes needed)

---

## IMPLEMENTATION PHASES

### Phase 1: Database Schema (Day 1)
- Create all tables with proper indexes
- Lexicographic ordering functions
- Triggers for constraints
- Migrations

### Phase 2: Core API - Strategies & Threads (Days 2-3)
- Strategy CRUD with versioning
- Thread CRUD with lexicographic ordering
- Move operations
- Optimistic locking

### Phase 3: Keywords & Topics (Days 4-5)
- Junction table operations
- Bulk assign/remove keywords
- Topic CRUD
- Aggregation queries

### Phase 4: Data & Suggestions (Day 6)
- Keyword listing with cursor pagination
- Cluster suggestions endpoint
- Format recommendations

### Phase 5: Export & Validation (Day 7)
- Validation logic
- Export formats (JSON, display, CSV)
- Export history

### Phase 6: Polish (Day 8)
- Activity logging
- Duplicate strategy
- Archive/restore
- Integration testing

---

## SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Strategy creation time | <10 minutes for 5-thread strategy |
| API response time (single entity) | <100ms |
| API response time (list with aggregations) | <300ms |
| Keyword pagination (10k keywords) | <200ms |
| Reorder operation | <50ms |
| Concurrent edit conflict detection | 100% accurate |
| Export validation | 100% correct |

---

*This specification is ready for implementation.*

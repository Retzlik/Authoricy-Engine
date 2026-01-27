"""
Strategy Builder API Endpoints

FastAPI router for Strategy Builder - user-driven content strategy creation.

Phase 2: Strategy & Thread CRUD with optimistic locking and lexicographic ordering.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload

from src.database.session import get_db_context
from src.database.models import (
    Strategy, StrategyThread, StrategyTopic, ThreadKeyword,
    StrategyExport, StrategyActivityLog,
    Keyword, AnalysisRun, Domain,
    StrategyStatus, ThreadStatus, TopicStatus, ContentType,
)
from src.utils.ordering import (
    generate_first_position,
    generate_position_at_end,
    generate_position_at_start,
    generate_position_between,
)
from src.auth.dependencies import get_current_user
from src.auth.models import User

logger = logging.getLogger(__name__)

# Router with authentication required for ALL endpoints
# Endpoints that need the user object for ownership checks still use Depends(get_current_user)
# in their signature, but the router-level dependency ensures no endpoint is unprotected
router = APIRouter(
    prefix="/api",
    tags=["strategy"],
    dependencies=[Depends(get_current_user)],  # All endpoints require authentication
)


# =============================================================================
# AUTH DEPENDENCIES - Ownership-checking dependencies for clean DI
# =============================================================================

class StrategyAccessChecker:
    """
    Dependency that fetches a strategy and validates ownership.

    Usage:
        @router.get("/strategies/{strategy_id}")
        def get_strategy(strategy: Strategy = Depends(get_owned_strategy)):
            # strategy is guaranteed to be owned by current user or user is admin
            return strategy

    This eliminates repetitive:
        strategy = db.query(Strategy).filter(...).first()
        if not strategy: raise HTTPException(404)
        check_access(strategy, user)
    """
    def __init__(self, allow_archived: bool = True):
        self.allow_archived = allow_archived

    async def __call__(
        self,
        strategy_id: UUID,
        current_user: User = Depends(get_current_user),
    ) -> Strategy:
        with get_db_context() as db:
            strategy = db.query(Strategy).options(
                joinedload(Strategy.domain)
            ).filter(Strategy.id == strategy_id).first()

            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")

            if not self.allow_archived and strategy.is_archived:
                raise HTTPException(status_code=400, detail="Strategy is archived")

            # Admin can access any strategy
            if current_user.is_admin:
                db.expunge(strategy)
                return strategy

            # User must own the domain
            if strategy.domain and strategy.domain.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied to this strategy")

            db.expunge(strategy)
            return strategy


class ThreadAccessChecker:
    """Dependency that fetches a thread and validates ownership via strategy."""
    async def __call__(
        self,
        thread_id: UUID,
        current_user: User = Depends(get_current_user),
    ) -> StrategyThread:
        with get_db_context() as db:
            thread = db.query(StrategyThread).options(
                joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
            ).filter(StrategyThread.id == thread_id).first()

            if not thread:
                raise HTTPException(status_code=404, detail="Thread not found")

            # Check access via strategy
            if current_user.is_admin:
                db.expunge(thread)
                return thread

            strategy = thread.strategy
            if strategy and strategy.domain and strategy.domain.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied to this thread")

            db.expunge(thread)
            return thread


class TopicAccessChecker:
    """Dependency that fetches a topic and validates ownership via thread -> strategy."""
    async def __call__(
        self,
        topic_id: UUID,
        current_user: User = Depends(get_current_user),
    ) -> StrategyTopic:
        with get_db_context() as db:
            topic = db.query(StrategyTopic).options(
                joinedload(StrategyTopic.thread)
                .joinedload(StrategyThread.strategy)
                .joinedload(Strategy.domain)
            ).filter(StrategyTopic.id == topic_id).first()

            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found")

            # Check access via thread -> strategy
            if current_user.is_admin:
                db.expunge(topic)
                return topic

            thread = topic.thread
            if thread and thread.strategy and thread.strategy.domain:
                if thread.strategy.domain.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Access denied to this topic")

            db.expunge(topic)
            return topic


# Pre-configured dependency instances
get_owned_strategy = StrategyAccessChecker(allow_archived=True)
get_active_strategy = StrategyAccessChecker(allow_archived=False)
get_owned_thread = ThreadAccessChecker()
get_owned_topic = TopicAccessChecker()


# Legacy helper functions (kept for backward compatibility in some complex flows)
def check_strategy_access(strategy: Strategy, user: User) -> None:
    """Check if user has access to a strategy (legacy helper)."""
    if user.is_admin:
        return
    if strategy.domain and strategy.domain.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied to this strategy")


def check_domain_access_strategy(domain: Domain, user: User) -> None:
    """Check if user has access to a domain for strategy operations."""
    if user.is_admin:
        return
    if domain.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied to this domain")


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class CustomInstructionsSchema(BaseModel):
    """Structured custom instructions for Monok."""
    strategic_context: Optional[str] = Field(None, max_length=500)
    differentiation_points: Optional[List[str]] = Field(default_factory=list)
    competitors_to_address: Optional[List[str]] = Field(default_factory=list)
    content_angle: Optional[str] = Field(None, max_length=300)
    format_recommendations: Optional[str] = None
    target_audience: Optional[str] = Field(None, max_length=200)
    additional_notes: Optional[str] = Field(None, max_length=2000)


# --- Strategy Request/Response Models ---

class StrategyCreate(BaseModel):
    """Request to create a new strategy."""
    domain_id: UUID
    analysis_run_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class StrategyUpdate(BaseModel):
    """Request to update a strategy (with optimistic locking)."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None  # draft, approved, archived
    version: int = Field(..., description="Required for optimistic locking")


class StrategyDuplicate(BaseModel):
    """Request to duplicate a strategy."""
    name: str = Field(..., min_length=1, max_length=255)


class StrategyResponse(BaseModel):
    """Strategy response with basic info."""
    id: UUID
    domain_id: UUID
    analysis_run_id: UUID
    name: str
    description: Optional[str]
    version: int
    status: str
    is_archived: bool
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Aggregations
    thread_count: int = 0
    topic_count: int = 0
    keyword_count: int = 0

    class Config:
        from_attributes = True


class StrategySummaryResponse(BaseModel):
    """Strategy list item response."""
    id: UUID
    name: str
    status: str
    version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    analysis_run_id: UUID
    analysis_created_at: Optional[datetime]
    thread_count: int
    topic_count: int
    keyword_count: int

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    """Response for listing strategies."""
    strategies: List[StrategySummaryResponse]


# --- Thread Request/Response Models ---

class ThreadCreate(BaseModel):
    """Request to create a new thread."""
    name: str = Field(..., min_length=1, max_length=255)
    after_thread_id: Optional[UUID] = None  # Insert after this thread (null = beginning)
    priority: Optional[int] = Field(None, ge=1, le=5)
    custom_instructions: Optional[CustomInstructionsSchema] = None


class ThreadUpdate(BaseModel):
    """Request to update a thread (with optimistic locking)."""
    name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None  # draft, confirmed, rejected
    priority: Optional[int] = Field(None, ge=1, le=5)
    custom_instructions: Optional[CustomInstructionsSchema] = None
    version: int = Field(..., description="Required for optimistic locking")


class ThreadMove(BaseModel):
    """Request to move a thread to new position."""
    after_thread_id: Optional[UUID] = None  # null = move to beginning


class ThreadMetricsResponse(BaseModel):
    """Computed thread metrics from assigned keywords."""
    total_search_volume: int = 0
    total_traffic_potential: int = 0
    avg_difficulty: float = 0.0
    avg_opportunity_score: float = 0.0
    keyword_count: int = 0


class ThreadResponse(BaseModel):
    """Thread response with metrics."""
    id: UUID
    strategy_id: UUID
    name: str
    slug: Optional[str]
    position: str
    version: int
    status: str
    priority: Optional[int]
    recommended_format: Optional[str]
    format_confidence: Optional[float]
    format_evidence: Optional[Dict]
    custom_instructions: Dict = {}
    created_at: datetime
    updated_at: datetime
    # Computed metrics
    metrics: ThreadMetricsResponse = ThreadMetricsResponse()
    topic_count: int = 0

    class Config:
        from_attributes = True


class ThreadListResponse(BaseModel):
    """Response for listing threads."""
    threads: List[ThreadResponse]


# --- Analysis Info ---

class AnalysisInfo(BaseModel):
    """Info about source analysis."""
    id: UUID
    created_at: datetime
    keyword_count: int
    market: Optional[str]
    status: str

    class Config:
        from_attributes = True


class StrategyDetailResponse(BaseModel):
    """Detailed strategy response with threads and analysis info."""
    strategy: StrategyResponse
    threads: List[ThreadResponse]
    analysis: Optional[AnalysisInfo]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_db():
    """Dependency for getting database session."""
    with get_db_context() as db:
        yield db


def compute_thread_metrics(db: Session, thread_id: UUID) -> ThreadMetricsResponse:
    """Compute thread metrics from assigned keywords."""
    # Join thread_keywords with keywords to get aggregates
    result = db.query(
        func.count(ThreadKeyword.id).label("keyword_count"),
        func.coalesce(func.sum(Keyword.search_volume), 0).label("total_volume"),
        func.coalesce(func.sum(Keyword.estimated_traffic), 0).label("total_traffic"),
        func.coalesce(func.avg(Keyword.keyword_difficulty), 0).label("avg_difficulty"),
        func.coalesce(func.avg(Keyword.opportunity_score), 0).label("avg_opportunity"),
    ).join(
        Keyword, ThreadKeyword.keyword_id == Keyword.id
    ).filter(
        ThreadKeyword.thread_id == thread_id
    ).first()

    return ThreadMetricsResponse(
        keyword_count=result.keyword_count or 0,
        total_search_volume=int(result.total_volume or 0),
        total_traffic_potential=int(result.total_traffic or 0),
        avg_difficulty=float(result.avg_difficulty or 0),
        avg_opportunity_score=float(result.avg_opportunity or 0),
    )


def compute_thread_metrics_bulk(db: Session, thread_ids: List[UUID]) -> Dict[UUID, ThreadMetricsResponse]:
    """
    Compute metrics for multiple threads in a single query.

    Performance: O(1) queries instead of O(n) for n threads.
    """
    if not thread_ids:
        return {}

    # Single query with GROUP BY for all threads
    results = db.query(
        ThreadKeyword.thread_id,
        func.count(ThreadKeyword.id).label("keyword_count"),
        func.coalesce(func.sum(Keyword.search_volume), 0).label("total_volume"),
        func.coalesce(func.sum(Keyword.estimated_traffic), 0).label("total_traffic"),
        func.coalesce(func.avg(Keyword.keyword_difficulty), 0).label("avg_difficulty"),
        func.coalesce(func.avg(Keyword.opportunity_score), 0).label("avg_opportunity"),
    ).join(
        Keyword, ThreadKeyword.keyword_id == Keyword.id
    ).filter(
        ThreadKeyword.thread_id.in_(thread_ids)
    ).group_by(ThreadKeyword.thread_id).all()

    metrics_map = {}
    for r in results:
        metrics_map[r.thread_id] = ThreadMetricsResponse(
            keyword_count=r.keyword_count or 0,
            total_search_volume=int(r.total_volume or 0),
            total_traffic_potential=int(r.total_traffic or 0),
            avg_difficulty=float(r.avg_difficulty or 0),
            avg_opportunity_score=float(r.avg_opportunity or 0),
        )

    # Fill in empty metrics for threads with no keywords
    for tid in thread_ids:
        if tid not in metrics_map:
            metrics_map[tid] = ThreadMetricsResponse()

    return metrics_map


def compute_topic_counts_bulk(db: Session, thread_ids: List[UUID]) -> Dict[UUID, int]:
    """
    Get topic counts for multiple threads in a single query.

    Performance: O(1) queries instead of O(n) for n threads.
    """
    if not thread_ids:
        return {}

    results = db.query(
        StrategyTopic.thread_id,
        func.count(StrategyTopic.id).label("count")
    ).filter(
        StrategyTopic.thread_id.in_(thread_ids)
    ).group_by(StrategyTopic.thread_id).all()

    counts = {r.thread_id: r.count for r in results}

    # Fill zeros for threads with no topics
    for tid in thread_ids:
        if tid not in counts:
            counts[tid] = 0

    return counts


def thread_to_response(db: Session, thread: StrategyThread) -> ThreadResponse:
    """Convert thread model to response with computed metrics."""
    metrics = compute_thread_metrics(db, thread.id)
    topic_count = db.query(func.count(StrategyTopic.id)).filter(
        StrategyTopic.thread_id == thread.id
    ).scalar() or 0

    return ThreadResponse(
        id=thread.id,
        strategy_id=thread.strategy_id,
        name=thread.name,
        slug=thread.slug,
        position=thread.position,
        version=thread.version,
        status=thread.status.value if isinstance(thread.status, ThreadStatus) else thread.status,
        priority=thread.priority,
        recommended_format=thread.recommended_format,
        format_confidence=thread.format_confidence,
        format_evidence=thread.format_evidence,
        custom_instructions=thread.custom_instructions or {},
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        metrics=metrics,
        topic_count=topic_count,
    )


def threads_to_responses_bulk(db: Session, threads: List[StrategyThread]) -> List[ThreadResponse]:
    """
    Convert multiple threads to responses with bulk-computed metrics.

    Performance: 2 queries total instead of 2n queries.
    """
    if not threads:
        return []

    thread_ids = [t.id for t in threads]

    # Bulk compute metrics and topic counts
    metrics_map = compute_thread_metrics_bulk(db, thread_ids)
    topic_counts = compute_topic_counts_bulk(db, thread_ids)

    responses = []
    for thread in threads:
        responses.append(ThreadResponse(
            id=thread.id,
            strategy_id=thread.strategy_id,
            name=thread.name,
            slug=thread.slug,
            position=thread.position,
            version=thread.version,
            status=thread.status.value if isinstance(thread.status, ThreadStatus) else thread.status,
            priority=thread.priority,
            recommended_format=thread.recommended_format,
            format_confidence=thread.format_confidence,
            format_evidence=thread.format_evidence,
            custom_instructions=thread.custom_instructions or {},
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            metrics=metrics_map.get(thread.id, ThreadMetricsResponse()),
            topic_count=topic_counts.get(thread.id, 0),
        ))

    return responses


def log_activity(
    db: Session,
    strategy_id: UUID,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    details: Optional[Dict] = None,
):
    """Log an activity to the strategy activity log."""
    log_entry = StrategyActivityLog(
        strategy_id=strategy_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        details=details,
    )
    db.add(log_entry)


def slugify(text: str) -> str:
    """Generate URL-friendly slug from text."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:255]


# =============================================================================
# STRATEGY ENDPOINTS
# =============================================================================

@router.get("/domains/{domain_id}/strategies", response_model=StrategyListResponse)
async def list_strategies(
    domain_id: UUID,
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status: draft, approved, archived"),
    include_archived: bool = Query(False, description="Include archived strategies"),
):
    """
    List strategies for a domain.

    Returns strategies with aggregated counts for threads, topics, and keywords.

    Performance: Uses 4 total queries regardless of result count (no N+1).

    Requires authentication. Users can only access strategies for their own domains.
    """
    with get_db_context() as db:
        # Check domain access
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")
        check_domain_access_strategy(domain, current_user)

        # Build query
        query = db.query(Strategy).filter(Strategy.domain_id == domain_id)

        if status:
            try:
                status_enum = StrategyStatus(status)
                query = query.filter(Strategy.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        if not include_archived:
            query = query.filter(Strategy.is_archived == False)

        query = query.order_by(Strategy.created_at.desc())
        strategies = query.all()

        if not strategies:
            return StrategyListResponse(strategies=[])

        strategy_ids = [s.id for s in strategies]
        analysis_run_ids = list(set(s.analysis_run_id for s in strategies))

        # BULK QUERY 1: Thread counts per strategy
        thread_counts_result = db.query(
            StrategyThread.strategy_id,
            func.count(StrategyThread.id).label("count")
        ).filter(
            StrategyThread.strategy_id.in_(strategy_ids)
        ).group_by(StrategyThread.strategy_id).all()
        thread_counts = {r.strategy_id: r.count for r in thread_counts_result}

        # BULK QUERY 2: Topic counts per strategy (via thread join)
        topic_counts_result = db.query(
            StrategyThread.strategy_id,
            func.count(StrategyTopic.id).label("count")
        ).join(
            StrategyTopic, StrategyTopic.thread_id == StrategyThread.id
        ).filter(
            StrategyThread.strategy_id.in_(strategy_ids)
        ).group_by(StrategyThread.strategy_id).all()
        topic_counts = {r.strategy_id: r.count for r in topic_counts_result}

        # BULK QUERY 3: Keyword counts per strategy (via thread join)
        keyword_counts_result = db.query(
            StrategyThread.strategy_id,
            func.count(ThreadKeyword.id).label("count")
        ).join(
            ThreadKeyword, ThreadKeyword.thread_id == StrategyThread.id
        ).filter(
            StrategyThread.strategy_id.in_(strategy_ids)
        ).group_by(StrategyThread.strategy_id).all()
        keyword_counts = {r.strategy_id: r.count for r in keyword_counts_result}

        # BULK QUERY 4: Analysis info
        analyses = db.query(AnalysisRun).filter(
            AnalysisRun.id.in_(analysis_run_ids)
        ).all()
        analysis_map = {a.id: a for a in analyses}

        # Build response
        result = []
        for strategy in strategies:
            analysis = analysis_map.get(strategy.analysis_run_id)
            result.append(StrategySummaryResponse(
                id=strategy.id,
                name=strategy.name,
                status=strategy.status.value if isinstance(strategy.status, StrategyStatus) else strategy.status,
                version=strategy.version,
                is_archived=strategy.is_archived,
                created_at=strategy.created_at,
                updated_at=strategy.updated_at,
                analysis_run_id=strategy.analysis_run_id,
                analysis_created_at=analysis.created_at if analysis else None,
                thread_count=thread_counts.get(strategy.id, 0),
                topic_count=topic_counts.get(strategy.id, 0),
                keyword_count=keyword_counts.get(strategy.id, 0),
            ))

        return StrategyListResponse(strategies=result)


@router.get("/strategies/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get a single strategy with threads and metrics.

    Returns the full strategy with all threads (including computed metrics)
    and source analysis information.

    Performance: Uses 3 queries total regardless of thread count (no N+1).
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Check ownership
        check_strategy_access(strategy, current_user)

        # Get threads ordered by position
        threads = db.query(StrategyThread).filter(
            StrategyThread.strategy_id == strategy_id
        ).order_by(StrategyThread.position).all()

        # Use bulk conversion (2 queries for all threads instead of 2n)
        thread_responses = threads_to_responses_bulk(db, threads)

        # Calculate aggregations from already-computed data
        thread_count = len(threads)
        topic_count = sum(t.topic_count for t in thread_responses)
        keyword_count = sum(t.metrics.keyword_count for t in thread_responses)

        # Get analysis info
        analysis = db.query(AnalysisRun).get(strategy.analysis_run_id)
        analysis_info = None
        if analysis:
            keyword_count_in_analysis = db.query(func.count(Keyword.id)).filter(
                Keyword.analysis_run_id == analysis.id
            ).scalar() or 0

            analysis_info = AnalysisInfo(
                id=analysis.id,
                created_at=analysis.created_at,
                keyword_count=keyword_count_in_analysis,
                market=analysis.config.get("market") if analysis.config else None,
                status=analysis.status.value if analysis.status else "unknown",
            )

        strategy_response = StrategyResponse(
            id=strategy.id,
            domain_id=strategy.domain_id,
            analysis_run_id=strategy.analysis_run_id,
            name=strategy.name,
            description=strategy.description,
            version=strategy.version,
            status=strategy.status.value if isinstance(strategy.status, StrategyStatus) else strategy.status,
            is_archived=strategy.is_archived,
            approved_at=strategy.approved_at,
            approved_by=strategy.approved_by,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            thread_count=thread_count,
            topic_count=topic_count,
            keyword_count=keyword_count,
        )

        return StrategyDetailResponse(
            strategy=strategy_response,
            threads=thread_responses,
            analysis=analysis_info,
        )


@router.post("/strategies", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    request: StrategyCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new strategy from an analysis.

    The strategy is bound to a specific analysis_run_id and will use keywords
    from that analysis only.

    Requires authentication. Users can only create strategies for their own domains.
    """
    with get_db_context() as db:
        # Validate domain exists and user has access
        domain = db.query(Domain).filter(Domain.id == request.domain_id).first()
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")
        check_domain_access_strategy(domain, current_user)

        # Validate analysis exists and belongs to domain
        analysis = db.query(AnalysisRun).filter(
            AnalysisRun.id == request.analysis_run_id,
            AnalysisRun.domain_id == request.domain_id,
        ).first()
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found or does not belong to this domain"
            )

        # Create strategy
        strategy = Strategy(
            domain_id=request.domain_id,
            analysis_run_id=request.analysis_run_id,
            name=request.name,
            description=request.description,
            status=StrategyStatus.DRAFT,
            version=1,
        )
        db.add(strategy)
        db.flush()  # Get the ID

        # Log activity
        log_activity(
            db, strategy.id, "created",
            entity_type="strategy", entity_id=strategy.id,
            details={"name": request.name}
        )

        db.commit()
        db.refresh(strategy)

        logger.info(f"Created strategy {strategy.id} for domain {domain.domain}")

        return StrategyResponse(
            id=strategy.id,
            domain_id=strategy.domain_id,
            analysis_run_id=strategy.analysis_run_id,
            name=strategy.name,
            description=strategy.description,
            version=strategy.version,
            status=strategy.status.value,
            is_archived=strategy.is_archived,
            approved_at=strategy.approved_at,
            approved_by=strategy.approved_by,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            thread_count=0,
            topic_count=0,
            keyword_count=0,
        )


@router.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    request: StrategyUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Update a strategy (with optimistic locking).

    The version field must match the current version, otherwise a 409 conflict
    is returned.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        # Optimistic locking check
        if strategy.version != request.version:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "version_conflict",
                    "current_version": strategy.version,
                    "message": "Strategy was modified by another user"
                }
            )

        # Update fields
        changes = {}
        if request.name is not None:
            changes["name"] = {"old": strategy.name, "new": request.name}
            strategy.name = request.name

        if request.description is not None:
            changes["description"] = {"old": strategy.description, "new": request.description}
            strategy.description = request.description

        if request.status is not None:
            try:
                new_status = StrategyStatus(request.status)
                changes["status"] = {"old": strategy.status.value, "new": request.status}
                strategy.status = new_status

                # Handle approval
                if new_status == StrategyStatus.APPROVED:
                    strategy.approved_at = datetime.utcnow()
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

        # Increment version
        strategy.version += 1
        strategy.updated_at = datetime.utcnow()

        # Log activity
        if changes:
            log_activity(
                db, strategy.id, "updated",
                entity_type="strategy", entity_id=strategy.id,
                details={"changes": changes}
            )

        db.commit()
        db.refresh(strategy)

        # Get counts for response
        thread_count = db.query(func.count(StrategyThread.id)).filter(
            StrategyThread.strategy_id == strategy.id
        ).scalar() or 0

        topic_count = db.query(func.count(StrategyTopic.id)).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == strategy.id
        ).scalar() or 0

        keyword_count = db.query(func.count(ThreadKeyword.id)).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == strategy.id
        ).scalar() or 0

        return StrategyResponse(
            id=strategy.id,
            domain_id=strategy.domain_id,
            analysis_run_id=strategy.analysis_run_id,
            name=strategy.name,
            description=strategy.description,
            version=strategy.version,
            status=strategy.status.value,
            is_archived=strategy.is_archived,
            approved_at=strategy.approved_at,
            approved_by=strategy.approved_by,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            thread_count=thread_count,
            topic_count=topic_count,
            keyword_count=keyword_count,
        )


@router.post("/strategies/{strategy_id}/duplicate", response_model=StrategyResponse, status_code=201)
async def duplicate_strategy(
    strategy_id: UUID,
    request: StrategyDuplicate,
    current_user: User = Depends(get_current_user),
):
    """
    Duplicate a strategy with all threads, topics, and keyword assignments.
    """
    with get_db_context() as db:
        # Get source strategy
        source = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(source, current_user)

        # Create new strategy
        new_strategy = Strategy(
            domain_id=source.domain_id,
            analysis_run_id=source.analysis_run_id,
            name=request.name,
            description=source.description,
            status=StrategyStatus.DRAFT,
            version=1,
        )
        db.add(new_strategy)
        db.flush()

        # Copy threads
        source_threads = db.query(StrategyThread).filter(
            StrategyThread.strategy_id == strategy_id
        ).all()

        thread_id_map = {}  # old_id -> new_id for keyword mapping
        for source_thread in source_threads:
            new_thread = StrategyThread(
                strategy_id=new_strategy.id,
                name=source_thread.name,
                slug=source_thread.slug,
                position=source_thread.position,
                version=1,
                status=ThreadStatus.DRAFT,
                priority=source_thread.priority,
                recommended_format=source_thread.recommended_format,
                format_confidence=source_thread.format_confidence,
                format_evidence=source_thread.format_evidence,
                custom_instructions=source_thread.custom_instructions,
            )
            db.add(new_thread)
            db.flush()
            thread_id_map[source_thread.id] = new_thread.id

            # Copy topics for this thread
            source_topics = db.query(StrategyTopic).filter(
                StrategyTopic.thread_id == source_thread.id
            ).all()

            for source_topic in source_topics:
                new_topic = StrategyTopic(
                    thread_id=new_thread.id,
                    name=source_topic.name,
                    slug=source_topic.slug,
                    position=source_topic.position,
                    version=1,
                    primary_keyword_id=source_topic.primary_keyword_id,
                    primary_keyword=source_topic.primary_keyword,
                    content_type=source_topic.content_type,
                    status=TopicStatus.DRAFT,
                    target_url=source_topic.target_url,
                    existing_url=source_topic.existing_url,
                )
                db.add(new_topic)

            # Copy keyword assignments
            source_keywords = db.query(ThreadKeyword).filter(
                ThreadKeyword.thread_id == source_thread.id
            ).all()

            for source_kw in source_keywords:
                new_kw = ThreadKeyword(
                    thread_id=new_thread.id,
                    keyword_id=source_kw.keyword_id,
                    position=source_kw.position,
                )
                db.add(new_kw)

        # Log activity
        log_activity(
            db, new_strategy.id, "created",
            entity_type="strategy", entity_id=new_strategy.id,
            details={"duplicated_from": str(strategy_id), "name": request.name}
        )

        db.commit()
        db.refresh(new_strategy)

        # Get counts
        thread_count = len(source_threads)
        topic_count = db.query(func.count(StrategyTopic.id)).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == new_strategy.id
        ).scalar() or 0

        keyword_count = db.query(func.count(ThreadKeyword.id)).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == new_strategy.id
        ).scalar() or 0

        logger.info(f"Duplicated strategy {strategy_id} to {new_strategy.id}")

        return StrategyResponse(
            id=new_strategy.id,
            domain_id=new_strategy.domain_id,
            analysis_run_id=new_strategy.analysis_run_id,
            name=new_strategy.name,
            description=new_strategy.description,
            version=new_strategy.version,
            status=new_strategy.status.value,
            is_archived=new_strategy.is_archived,
            approved_at=new_strategy.approved_at,
            approved_by=new_strategy.approved_by,
            created_at=new_strategy.created_at,
            updated_at=new_strategy.updated_at,
            thread_count=thread_count,
            topic_count=topic_count,
            keyword_count=keyword_count,
        )


@router.post("/strategies/{strategy_id}/archive", response_model=StrategyResponse)
async def archive_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Archive a strategy (soft delete)."""
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        if strategy.is_archived:
            raise HTTPException(status_code=400, detail="Strategy is already archived")

        strategy.is_archived = True
        strategy.archived_at = datetime.utcnow()
        strategy.status = StrategyStatus.ARCHIVED
        strategy.version += 1
        strategy.updated_at = datetime.utcnow()

        log_activity(
            db, strategy.id, "archived",
            entity_type="strategy", entity_id=strategy.id,
        )

        db.commit()
        db.refresh(strategy)

        # Get counts
        thread_count = db.query(func.count(StrategyThread.id)).filter(
            StrategyThread.strategy_id == strategy.id
        ).scalar() or 0

        return StrategyResponse(
            id=strategy.id,
            domain_id=strategy.domain_id,
            analysis_run_id=strategy.analysis_run_id,
            name=strategy.name,
            description=strategy.description,
            version=strategy.version,
            status=strategy.status.value,
            is_archived=strategy.is_archived,
            approved_at=strategy.approved_at,
            approved_by=strategy.approved_by,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            thread_count=thread_count,
            topic_count=0,
            keyword_count=0,
        )


@router.post("/strategies/{strategy_id}/restore", response_model=StrategyResponse)
async def restore_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Restore an archived strategy."""
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        if not strategy.is_archived:
            raise HTTPException(status_code=400, detail="Strategy is not archived")

        strategy.is_archived = False
        strategy.archived_at = None
        strategy.status = StrategyStatus.DRAFT
        strategy.version += 1
        strategy.updated_at = datetime.utcnow()

        log_activity(
            db, strategy.id, "restored",
            entity_type="strategy", entity_id=strategy.id,
        )

        db.commit()
        db.refresh(strategy)

        # Get counts
        thread_count = db.query(func.count(StrategyThread.id)).filter(
            StrategyThread.strategy_id == strategy.id
        ).scalar() or 0

        return StrategyResponse(
            id=strategy.id,
            domain_id=strategy.domain_id,
            analysis_run_id=strategy.analysis_run_id,
            name=strategy.name,
            description=strategy.description,
            version=strategy.version,
            status=strategy.status.value,
            is_archived=strategy.is_archived,
            approved_at=strategy.approved_at,
            approved_by=strategy.approved_by,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            thread_count=thread_count,
            topic_count=0,
            keyword_count=0,
        )


@router.delete("/strategies/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Hard delete a strategy (only if archived).

    All threads, topics, and keyword assignments are deleted via CASCADE.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        if not strategy.is_archived:
            raise HTTPException(
                status_code=400,
                detail="Strategy must be archived before deletion. Use /archive first."
            )

        logger.info(f"Deleting strategy {strategy_id}")
        db.delete(strategy)
        db.commit()


# =============================================================================
# THREAD ENDPOINTS
# =============================================================================

@router.get("/strategies/{strategy_id}/threads", response_model=ThreadListResponse)
async def list_threads(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    List threads for a strategy (ordered by position).

    Returns threads with computed metrics from assigned keywords.

    Performance: Uses 3 queries total regardless of thread count (no N+1).
    """
    with get_db_context() as db:
        # Validate strategy exists and check access
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        threads = db.query(StrategyThread).filter(
            StrategyThread.strategy_id == strategy_id
        ).order_by(StrategyThread.position).all()

        # Use bulk conversion (2 queries for all threads instead of 2n)
        thread_responses = threads_to_responses_bulk(db, threads)

        return ThreadListResponse(threads=thread_responses)


@router.post("/strategies/{strategy_id}/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(
    strategy_id: UUID,
    request: ThreadCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new thread.

    Use after_thread_id to insert after a specific thread, or null to insert
    at the beginning.
    """
    with get_db_context() as db:
        # Validate strategy exists and check access
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        # Determine position
        if request.after_thread_id:
            # Insert after specific thread
            after_thread = db.query(StrategyThread).filter(
                StrategyThread.id == request.after_thread_id,
                StrategyThread.strategy_id == strategy_id,
            ).first()
            if not after_thread:
                raise HTTPException(status_code=404, detail="after_thread_id not found")

            # Find the next thread
            next_thread = db.query(StrategyThread).filter(
                StrategyThread.strategy_id == strategy_id,
                StrategyThread.position > after_thread.position,
            ).order_by(StrategyThread.position).first()

            if next_thread:
                position = generate_position_between(after_thread.position, next_thread.position)
            else:
                position = generate_position_at_end(after_thread.position)
        else:
            # Insert at beginning
            first_thread = db.query(StrategyThread).filter(
                StrategyThread.strategy_id == strategy_id
            ).order_by(StrategyThread.position).first()

            if first_thread:
                position = generate_position_at_start(first_thread.position)
            else:
                position = generate_first_position()

        # Create thread
        thread = StrategyThread(
            strategy_id=strategy_id,
            name=request.name,
            slug=slugify(request.name),
            position=position,
            version=1,
            status=ThreadStatus.DRAFT,
            priority=request.priority,
            custom_instructions=request.custom_instructions.model_dump() if request.custom_instructions else {},
        )
        db.add(thread)
        db.flush()

        # Log activity
        log_activity(
            db, strategy_id, "thread_added",
            entity_type="thread", entity_id=thread.id,
            details={"name": request.name, "position": position}
        )

        # Update strategy version
        strategy.version += 1
        strategy.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(thread)

        logger.info(f"Created thread {thread.id} in strategy {strategy_id}")

        return thread_to_response(db, thread)


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: UUID,
    request: ThreadUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Update a thread (with optimistic locking).

    The version field must match the current version, otherwise a 409 conflict
    is returned.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Check access via strategy
        check_strategy_access(thread.strategy, current_user)

        # Optimistic locking check
        if thread.version != request.version:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "version_conflict",
                    "current_version": thread.version,
                    "message": "Thread was modified by another user"
                }
            )

        # Update fields
        changes = {}
        if request.name is not None:
            changes["name"] = {"old": thread.name, "new": request.name}
            thread.name = request.name
            thread.slug = slugify(request.name)

        if request.status is not None:
            try:
                new_status = ThreadStatus(request.status)
                changes["status"] = {"old": thread.status.value, "new": request.status}
                thread.status = new_status
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

        if request.priority is not None:
            changes["priority"] = {"old": thread.priority, "new": request.priority}
            thread.priority = request.priority

        if request.custom_instructions is not None:
            changes["custom_instructions"] = {"updated": True}
            thread.custom_instructions = request.custom_instructions.model_dump()

        # Increment version
        thread.version += 1
        thread.updated_at = datetime.utcnow()

        # Log activity
        if changes:
            log_activity(
                db, thread.strategy_id, "thread_updated",
                entity_type="thread", entity_id=thread.id,
                details={"changes": changes}
            )

        db.commit()
        db.refresh(thread)

        return thread_to_response(db, thread)


@router.post("/threads/{thread_id}/move", response_model=ThreadResponse)
async def move_thread(
    thread_id: UUID,
    request: ThreadMove,
    current_user: User = Depends(get_current_user),
):
    """
    Move a thread to a new position.

    Use after_thread_id to move after a specific thread, or null to move
    to the beginning.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        check_strategy_access(thread.strategy, current_user)

        strategy_id = thread.strategy_id
        old_position = thread.position

        # Determine new position
        if request.after_thread_id:
            if request.after_thread_id == thread_id:
                raise HTTPException(status_code=400, detail="Cannot move thread after itself")

            after_thread = db.query(StrategyThread).filter(
                StrategyThread.id == request.after_thread_id,
                StrategyThread.strategy_id == strategy_id,
            ).first()
            if not after_thread:
                raise HTTPException(status_code=404, detail="after_thread_id not found")

            # Find the next thread (excluding ourselves)
            next_thread = db.query(StrategyThread).filter(
                StrategyThread.strategy_id == strategy_id,
                StrategyThread.position > after_thread.position,
                StrategyThread.id != thread_id,
            ).order_by(StrategyThread.position).first()

            if next_thread:
                new_position = generate_position_between(after_thread.position, next_thread.position)
            else:
                new_position = generate_position_at_end(after_thread.position)
        else:
            # Move to beginning
            first_thread = db.query(StrategyThread).filter(
                StrategyThread.strategy_id == strategy_id,
                StrategyThread.id != thread_id,
            ).order_by(StrategyThread.position).first()

            if first_thread:
                new_position = generate_position_at_start(first_thread.position)
            else:
                new_position = generate_first_position()

        thread.position = new_position
        thread.version += 1
        thread.updated_at = datetime.utcnow()

        # Log activity
        log_activity(
            db, strategy_id, "thread_moved",
            entity_type="thread", entity_id=thread.id,
            details={"old_position": old_position, "new_position": new_position}
        )

        db.commit()
        db.refresh(thread)

        logger.info(f"Moved thread {thread_id} from {old_position} to {new_position}")

        return thread_to_response(db, thread)


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a thread.

    All topics and keyword assignments for this thread are deleted via CASCADE.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        check_strategy_access(thread.strategy, current_user)

        strategy_id = thread.strategy_id
        thread_name = thread.name

        # Log activity before delete
        log_activity(
            db, strategy_id, "thread_deleted",
            entity_type="thread", entity_id=thread_id,
            details={"name": thread_name}
        )

        # Update strategy version
        strategy = db.query(Strategy).get(strategy_id)
        if strategy:
            strategy.version += 1
            strategy.updated_at = datetime.utcnow()

        logger.info(f"Deleting thread {thread_id} from strategy {strategy_id}")
        db.delete(thread)
        db.commit()


# =============================================================================
# ANALYSIS SELECTION ENDPOINT
# =============================================================================

@router.get("/domains/{domain_id}/analyses")
async def list_analyses(
    domain_id: UUID,
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query("completed", description="Filter by status"),
):
    """
    List available analyses for a domain. Requires domain ownership.

    Use this to select which analysis to use when creating a strategy.
    """
    with get_db_context() as db:
        # Check domain ownership
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")
        check_domain_access_strategy(domain, current_user)

        from src.database.models import AnalysisStatus as AnalysisStatusEnum

        query = db.query(AnalysisRun).filter(AnalysisRun.domain_id == domain_id)

        if status:
            try:
                status_enum = AnalysisStatusEnum(status)
                query = query.filter(AnalysisRun.status == status_enum)
            except ValueError:
                pass  # Ignore invalid status

        query = query.order_by(AnalysisRun.created_at.desc())
        analyses = query.all()

        result = []
        for analysis in analyses:
            keyword_count = db.query(func.count(Keyword.id)).filter(
                Keyword.analysis_run_id == analysis.id
            ).scalar() or 0

            # Count strategies using this analysis
            strategies_count = db.query(func.count(Strategy.id)).filter(
                Strategy.analysis_run_id == analysis.id
            ).scalar() or 0

            result.append({
                "id": str(analysis.id),
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                "status": analysis.status.value if analysis.status else "unknown",
                "keyword_count": keyword_count,
                "market": analysis.config.get("market") if analysis.config else None,
                "language": analysis.config.get("language") if analysis.config else None,
                "depth": analysis.config.get("depth") if analysis.config else None,
                "strategies_count": strategies_count,
            })

        return {"analyses": result}


# =============================================================================
# PHASE 3: KEYWORDS & TOPICS API
# =============================================================================

# --- Keyword Request/Response Models ---

class KeywordAssign(BaseModel):
    """Request to assign keywords to a thread."""
    keyword_ids: List[UUID] = Field(..., min_length=1, max_length=1000)
    version: int = Field(..., description="Thread version for optimistic locking")


class KeywordRemove(BaseModel):
    """Request to remove keywords from a thread."""
    keyword_ids: List[UUID] = Field(..., min_length=1, max_length=1000)


class KeywordInThreadResponse(BaseModel):
    """Keyword response within a thread context."""
    id: UUID
    keyword: str
    search_volume: Optional[int]
    keyword_difficulty: Optional[int]
    opportunity_score: Optional[float]
    search_intent: Optional[str]
    parent_topic: Optional[str]
    estimated_traffic: Optional[int]
    position: str  # Position within thread

    class Config:
        from_attributes = True


class ThreadKeywordsResponse(BaseModel):
    """Response for thread keywords."""
    keywords: List[KeywordInThreadResponse]
    total_count: int


# --- Topic Request/Response Models ---

class TopicCreate(BaseModel):
    """Request to create a new topic."""
    name: str = Field(..., min_length=1, max_length=500)
    content_type: Optional[str] = "cluster"  # pillar, cluster, supporting
    primary_keyword_id: Optional[UUID] = None
    after_topic_id: Optional[UUID] = None  # Insert position


class TopicUpdate(BaseModel):
    """Request to update a topic (with optimistic locking)."""
    name: Optional[str] = Field(None, max_length=500)
    content_type: Optional[str] = None
    status: Optional[str] = None  # draft, confirmed, in_production, published
    target_url: Optional[str] = Field(None, max_length=2000)
    primary_keyword_id: Optional[UUID] = None
    version: int = Field(..., description="Required for optimistic locking")


class TopicMove(BaseModel):
    """Request to move a topic within the same thread."""
    after_topic_id: Optional[UUID] = None  # null = move to beginning


class TopicMoveToThread(BaseModel):
    """Request to move a topic to a different thread."""
    thread_id: UUID
    after_topic_id: Optional[UUID] = None


class TopicResponse(BaseModel):
    """Topic response."""
    id: UUID
    thread_id: UUID
    name: str
    slug: Optional[str]
    position: str
    version: int
    primary_keyword_id: Optional[UUID]
    primary_keyword: Optional[str]
    content_type: str
    status: str
    target_url: Optional[str]
    existing_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TopicListResponse(BaseModel):
    """Response for listing topics."""
    topics: List[TopicResponse]


def topic_to_response(topic: StrategyTopic) -> TopicResponse:
    """Convert topic model to response."""
    return TopicResponse(
        id=topic.id,
        thread_id=topic.thread_id,
        name=topic.name,
        slug=topic.slug,
        position=topic.position,
        version=topic.version,
        primary_keyword_id=topic.primary_keyword_id,
        primary_keyword=topic.primary_keyword,
        content_type=topic.content_type.value if isinstance(topic.content_type, ContentType) else topic.content_type,
        status=topic.status.value if isinstance(topic.status, TopicStatus) else topic.status,
        target_url=topic.target_url,
        existing_url=topic.existing_url,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
    )


# =============================================================================
# KEYWORD ENDPOINTS (Thread-level)
# =============================================================================

@router.get("/threads/{thread_id}/keywords", response_model=ThreadKeywordsResponse)
async def get_thread_keywords(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get keywords assigned to a thread (ordered by position).
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        check_strategy_access(thread.strategy, current_user)

        # Join thread_keywords with keywords
        results = db.query(
            ThreadKeyword, Keyword
        ).join(
            Keyword, ThreadKeyword.keyword_id == Keyword.id
        ).filter(
            ThreadKeyword.thread_id == thread_id
        ).order_by(ThreadKeyword.position).all()

        keywords = []
        for tk, kw in results:
            keywords.append(KeywordInThreadResponse(
                id=kw.id,
                keyword=kw.keyword,
                search_volume=kw.search_volume,
                keyword_difficulty=kw.keyword_difficulty,
                opportunity_score=kw.opportunity_score,
                search_intent=kw.search_intent.value if kw.search_intent else None,
                parent_topic=kw.parent_topic,
                estimated_traffic=kw.estimated_traffic,
                position=tk.position,
            ))

        return ThreadKeywordsResponse(
            keywords=keywords,
            total_count=len(keywords),
        )


@router.post("/threads/{thread_id}/keywords", response_model=ThreadResponse)
async def assign_keywords_to_thread(
    thread_id: UUID,
    request: KeywordAssign,
    current_user: User = Depends(get_current_user),
):
    """
    Assign keywords to a thread (bulk).

    Keywords are assigned with lexicographic positions for ordering.
    If a keyword is already assigned to another thread in the same strategy,
    returns 400 error.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        check_strategy_access(thread.strategy, current_user)

        # Optimistic locking check
        if thread.version != request.version:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "version_conflict",
                    "current_version": thread.version,
                    "message": "Thread was modified by another user"
                }
            )

        strategy = db.query(Strategy).get(thread.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Get existing keywords in this thread for position calculation
        last_position = db.query(func.max(ThreadKeyword.position)).filter(
            ThreadKeyword.thread_id == thread_id
        ).scalar()

        # Validate keywords exist and belong to the same analysis
        keywords = db.query(Keyword).filter(
            Keyword.id.in_(request.keyword_ids),
            Keyword.analysis_run_id == strategy.analysis_run_id,
        ).all()

        if len(keywords) != len(request.keyword_ids):
            found_ids = {kw.id for kw in keywords}
            missing = [str(kid) for kid in request.keyword_ids if kid not in found_ids]
            raise HTTPException(
                status_code=400,
                detail=f"Keywords not found or not from this analysis: {missing[:5]}"
            )

        # Check if any keyword is already assigned to another thread in this strategy
        existing_assignments = db.query(
            ThreadKeyword.keyword_id, StrategyThread.id, StrategyThread.name
        ).join(
            StrategyThread, ThreadKeyword.thread_id == StrategyThread.id
        ).filter(
            ThreadKeyword.keyword_id.in_(request.keyword_ids),
            StrategyThread.strategy_id == strategy.id,
            StrategyThread.id != thread_id,  # Exclude current thread
        ).all()

        if existing_assignments:
            first_conflict = existing_assignments[0]
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "keyword_already_assigned",
                    "keyword_id": str(first_conflict[0]),
                    "thread_name": first_conflict[2],
                    "message": f"Keyword already assigned to thread '{first_conflict[2]}'"
                }
            )

        # Get keywords already in this thread (skip duplicates)
        existing_in_thread = db.query(ThreadKeyword.keyword_id).filter(
            ThreadKeyword.thread_id == thread_id,
            ThreadKeyword.keyword_id.in_(request.keyword_ids),
        ).all()
        existing_ids = {e[0] for e in existing_in_thread}

        # Generate positions and create assignments
        new_keyword_ids = [kid for kid in request.keyword_ids if kid not in existing_ids]
        current_position = last_position

        for keyword_id in new_keyword_ids:
            new_position = generate_position_at_end(current_position)
            tk = ThreadKeyword(
                thread_id=thread_id,
                keyword_id=keyword_id,
                position=new_position,
            )
            db.add(tk)
            current_position = new_position

        # Update thread version
        thread.version += 1
        thread.updated_at = datetime.utcnow()

        # Log activity
        log_activity(
            db, strategy.id, "keywords_assigned",
            entity_type="thread", entity_id=thread_id,
            details={"keyword_count": len(new_keyword_ids)}
        )

        db.commit()
        db.refresh(thread)

        logger.info(f"Assigned {len(new_keyword_ids)} keywords to thread {thread_id}")

        return thread_to_response(db, thread)


@router.delete("/threads/{thread_id}/keywords", response_model=ThreadResponse)
async def remove_keywords_from_thread(
    thread_id: UUID,
    request: KeywordRemove,
    current_user: User = Depends(get_current_user),
):
    """
    Remove keywords from a thread (bulk).
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        check_strategy_access(thread.strategy, current_user)

        # Delete the keyword assignments
        deleted = db.query(ThreadKeyword).filter(
            ThreadKeyword.thread_id == thread_id,
            ThreadKeyword.keyword_id.in_(request.keyword_ids),
        ).delete(synchronize_session=False)

        # Update thread version
        thread.version += 1
        thread.updated_at = datetime.utcnow()

        # Log activity
        log_activity(
            db, thread.strategy_id, "keywords_removed",
            entity_type="thread", entity_id=thread_id,
            details={"keyword_count": deleted}
        )

        db.commit()
        db.refresh(thread)

        logger.info(f"Removed {deleted} keywords from thread {thread_id}")

        return thread_to_response(db, thread)


# =============================================================================
# BATCH OPERATIONS
# =============================================================================

class BatchMoveKeywords(BaseModel):
    """Request to move keywords from one thread to another."""
    keyword_ids: List[UUID] = Field(..., min_length=1, max_length=1000)
    source_thread_id: UUID
    target_thread_id: UUID


class BatchMoveResponse(BaseModel):
    """Response for batch move operation."""
    moved_count: int
    source_thread: ThreadResponse
    target_thread: ThreadResponse


class AssignClusterRequest(BaseModel):
    """Request to assign a suggested cluster to a new or existing thread."""
    keyword_ids: List[UUID] = Field(..., min_length=1)
    thread_id: Optional[UUID] = None  # If null, create new thread
    new_thread_name: Optional[str] = Field(None, max_length=255)


class AssignClusterResponse(BaseModel):
    """Response for cluster assignment."""
    thread: ThreadResponse
    assigned_count: int
    skipped_count: int  # Already assigned elsewhere


@router.post("/strategies/{strategy_id}/keywords/batch-move", response_model=BatchMoveResponse)
async def batch_move_keywords(
    strategy_id: UUID,
    request: BatchMoveKeywords,
    current_user: User = Depends(get_current_user),
):
    """
    Move multiple keywords from one thread to another in a single operation.

    This is atomic: either all keywords move or none do.
    Keywords already in the target thread are skipped.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        # Validate both threads exist and belong to this strategy
        source_thread = db.query(StrategyThread).filter(
            StrategyThread.id == request.source_thread_id,
            StrategyThread.strategy_id == strategy_id,
        ).first()
        if not source_thread:
            raise HTTPException(status_code=404, detail="Source thread not found")

        target_thread = db.query(StrategyThread).filter(
            StrategyThread.id == request.target_thread_id,
            StrategyThread.strategy_id == strategy_id,
        ).first()
        if not target_thread:
            raise HTTPException(status_code=404, detail="Target thread not found")

        if request.source_thread_id == request.target_thread_id:
            raise HTTPException(status_code=400, detail="Source and target thread cannot be the same")

        # Get existing assignments in source thread
        source_assignments = db.query(ThreadKeyword).filter(
            ThreadKeyword.thread_id == request.source_thread_id,
            ThreadKeyword.keyword_id.in_(request.keyword_ids),
        ).all()

        if not source_assignments:
            raise HTTPException(
                status_code=400,
                detail="None of the specified keywords are in the source thread"
            )

        # Get last position in target thread
        last_position = db.query(func.max(ThreadKeyword.position)).filter(
            ThreadKeyword.thread_id == request.target_thread_id
        ).scalar()

        # Move keywords: delete from source, add to target
        moved_count = 0
        current_position = last_position

        for assignment in source_assignments:
            # Delete from source
            db.delete(assignment)

            # Add to target with new position
            new_position = generate_position_at_end(current_position)
            new_assignment = ThreadKeyword(
                thread_id=request.target_thread_id,
                keyword_id=assignment.keyword_id,
                position=new_position,
            )
            db.add(new_assignment)
            current_position = new_position
            moved_count += 1

        # Update both thread versions
        source_thread.version += 1
        source_thread.updated_at = datetime.utcnow()
        target_thread.version += 1
        target_thread.updated_at = datetime.utcnow()

        # Log activity
        log_activity(
            db, strategy_id, "keywords_batch_moved",
            entity_type="thread",
            details={
                "source_thread_id": str(request.source_thread_id),
                "target_thread_id": str(request.target_thread_id),
                "moved_count": moved_count,
            }
        )

        db.commit()
        db.refresh(source_thread)
        db.refresh(target_thread)

        logger.info(f"Batch moved {moved_count} keywords from thread {request.source_thread_id} to {request.target_thread_id}")

        return BatchMoveResponse(
            moved_count=moved_count,
            source_thread=thread_to_response(db, source_thread),
            target_thread=thread_to_response(db, target_thread),
        )


@router.post("/strategies/{strategy_id}/assign-cluster", response_model=AssignClusterResponse)
async def assign_cluster(
    strategy_id: UUID,
    request: AssignClusterRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Assign a suggested cluster (list of keywords) to a thread.

    If thread_id is provided, assigns to existing thread.
    If new_thread_name is provided, creates a new thread first.

    Keywords already assigned to other threads are skipped.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        # Determine target thread
        thread = None
        if request.thread_id:
            thread = db.query(StrategyThread).filter(
                StrategyThread.id == request.thread_id,
                StrategyThread.strategy_id == strategy_id,
            ).first()
            if not thread:
                raise HTTPException(status_code=404, detail="Thread not found")
        elif request.new_thread_name:
            # Create new thread
            # Find last thread position
            last_thread = db.query(StrategyThread).filter(
                StrategyThread.strategy_id == strategy_id
            ).order_by(StrategyThread.position.desc()).first()

            position = generate_position_at_end(last_thread.position if last_thread else None)

            thread = StrategyThread(
                strategy_id=strategy_id,
                name=request.new_thread_name,
                slug=slugify(request.new_thread_name),
                position=position,
                version=1,
                status=ThreadStatus.DRAFT,
            )
            db.add(thread)
            db.flush()

            log_activity(
                db, strategy_id, "thread_added",
                entity_type="thread", entity_id=thread.id,
                details={"name": request.new_thread_name, "from_cluster_assign": True}
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either thread_id or new_thread_name is required"
            )

        # Validate keywords exist and belong to this analysis
        keywords = db.query(Keyword).filter(
            Keyword.id.in_(request.keyword_ids),
            Keyword.analysis_run_id == strategy.analysis_run_id,
        ).all()

        if not keywords:
            raise HTTPException(status_code=400, detail="No valid keywords found")

        # Check which keywords are already assigned to other threads
        existing_assignments = db.query(ThreadKeyword.keyword_id).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == strategy_id,
            ThreadKeyword.keyword_id.in_(request.keyword_ids),
        ).all()
        already_assigned = {a[0] for a in existing_assignments}

        # Get last position in target thread
        last_position = db.query(func.max(ThreadKeyword.position)).filter(
            ThreadKeyword.thread_id == thread.id
        ).scalar()

        # Assign keywords that aren't already assigned
        assigned_count = 0
        skipped_count = 0
        current_position = last_position

        for keyword in keywords:
            if keyword.id in already_assigned:
                skipped_count += 1
                continue

            new_position = generate_position_at_end(current_position)
            assignment = ThreadKeyword(
                thread_id=thread.id,
                keyword_id=keyword.id,
                position=new_position,
            )
            db.add(assignment)
            current_position = new_position
            assigned_count += 1

        # Update thread version
        thread.version += 1
        thread.updated_at = datetime.utcnow()

        # Log activity
        log_activity(
            db, strategy_id, "cluster_assigned",
            entity_type="thread", entity_id=thread.id,
            details={
                "assigned_count": assigned_count,
                "skipped_count": skipped_count,
            }
        )

        db.commit()
        db.refresh(thread)

        logger.info(f"Assigned cluster of {assigned_count} keywords to thread {thread.id} (skipped {skipped_count})")

        return AssignClusterResponse(
            thread=thread_to_response(db, thread),
            assigned_count=assigned_count,
            skipped_count=skipped_count,
        )


# =============================================================================
# TOPIC ENDPOINTS
# =============================================================================

@router.get("/threads/{thread_id}/topics", response_model=TopicListResponse)
async def list_topics(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    List topics for a thread (ordered by position).
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        check_strategy_access(thread.strategy, current_user)

        topics = db.query(StrategyTopic).filter(
            StrategyTopic.thread_id == thread_id
        ).order_by(StrategyTopic.position).all()

        return TopicListResponse(topics=[topic_to_response(t) for t in topics])


@router.post("/threads/{thread_id}/topics", response_model=TopicResponse, status_code=201)
async def create_topic(
    thread_id: UUID,
    request: TopicCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new topic in a thread.

    Use after_topic_id to insert after a specific topic, or null to insert
    at the beginning.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).options(
            joinedload(StrategyThread.strategy).joinedload(Strategy.domain)
        ).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        check_strategy_access(thread.strategy, current_user)

        # Validate content_type
        try:
            content_type = ContentType(request.content_type) if request.content_type else ContentType.CLUSTER
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid content_type: {request.content_type}")

        # Get primary keyword text if provided
        primary_keyword_text = None
        if request.primary_keyword_id:
            keyword = db.query(Keyword).get(request.primary_keyword_id)
            if keyword:
                primary_keyword_text = keyword.keyword

        # Determine position
        if request.after_topic_id:
            after_topic = db.query(StrategyTopic).filter(
                StrategyTopic.id == request.after_topic_id,
                StrategyTopic.thread_id == thread_id,
            ).first()
            if not after_topic:
                raise HTTPException(status_code=404, detail="after_topic_id not found")

            next_topic = db.query(StrategyTopic).filter(
                StrategyTopic.thread_id == thread_id,
                StrategyTopic.position > after_topic.position,
            ).order_by(StrategyTopic.position).first()

            if next_topic:
                position = generate_position_between(after_topic.position, next_topic.position)
            else:
                position = generate_position_at_end(after_topic.position)
        else:
            first_topic = db.query(StrategyTopic).filter(
                StrategyTopic.thread_id == thread_id
            ).order_by(StrategyTopic.position).first()

            if first_topic:
                position = generate_position_at_start(first_topic.position)
            else:
                position = generate_first_position()

        # Create topic
        topic = StrategyTopic(
            thread_id=thread_id,
            name=request.name,
            slug=slugify(request.name),
            position=position,
            version=1,
            content_type=content_type,
            status=TopicStatus.DRAFT,
            primary_keyword_id=request.primary_keyword_id,
            primary_keyword=primary_keyword_text,
        )
        db.add(topic)
        db.flush()

        # Log activity
        log_activity(
            db, thread.strategy_id, "topic_added",
            entity_type="topic", entity_id=topic.id,
            details={"name": request.name, "thread_id": str(thread_id)}
        )

        # Update thread version
        thread.version += 1
        thread.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(topic)

        logger.info(f"Created topic {topic.id} in thread {thread_id}")

        return topic_to_response(topic)


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: UUID,
    request: TopicUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Update a topic (with optimistic locking).
    """
    with get_db_context() as db:
        topic = db.query(StrategyTopic).options(
            joinedload(StrategyTopic.thread)
            .joinedload(StrategyThread.strategy)
            .joinedload(Strategy.domain)
        ).filter(StrategyTopic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        check_strategy_access(topic.thread.strategy, current_user)

        # Optimistic locking check
        if topic.version != request.version:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "version_conflict",
                    "current_version": topic.version,
                    "message": "Topic was modified by another user"
                }
            )

        changes = {}
        if request.name is not None:
            changes["name"] = {"old": topic.name, "new": request.name}
            topic.name = request.name
            topic.slug = slugify(request.name)

        if request.content_type is not None:
            try:
                new_type = ContentType(request.content_type)
                changes["content_type"] = {"old": topic.content_type.value, "new": request.content_type}
                topic.content_type = new_type
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid content_type: {request.content_type}")

        if request.status is not None:
            try:
                new_status = TopicStatus(request.status)
                changes["status"] = {"old": topic.status.value, "new": request.status}
                topic.status = new_status
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

        if request.target_url is not None:
            changes["target_url"] = {"old": topic.target_url, "new": request.target_url}
            topic.target_url = request.target_url

        if request.primary_keyword_id is not None:
            keyword = db.query(Keyword).get(request.primary_keyword_id)
            if keyword:
                topic.primary_keyword_id = keyword.id
                topic.primary_keyword = keyword.keyword
                changes["primary_keyword"] = {"new": keyword.keyword}

        # Increment version
        topic.version += 1
        topic.updated_at = datetime.utcnow()

        # Get thread for logging
        thread = db.query(StrategyThread).get(topic.thread_id)

        # Log activity
        if changes and thread:
            log_activity(
                db, thread.strategy_id, "topic_updated",
                entity_type="topic", entity_id=topic.id,
                details={"changes": changes}
            )

        db.commit()
        db.refresh(topic)

        return topic_to_response(topic)


@router.post("/topics/{topic_id}/move", response_model=TopicResponse)
async def move_topic(
    topic_id: UUID,
    request: TopicMove,
    current_user: User = Depends(get_current_user),
):
    """
    Move a topic to a new position within the same thread.
    """
    with get_db_context() as db:
        topic = db.query(StrategyTopic).options(
            joinedload(StrategyTopic.thread)
            .joinedload(StrategyThread.strategy)
            .joinedload(Strategy.domain)
        ).filter(StrategyTopic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        check_strategy_access(topic.thread.strategy, current_user)

        thread_id = topic.thread_id
        old_position = topic.position

        if request.after_topic_id:
            if request.after_topic_id == topic_id:
                raise HTTPException(status_code=400, detail="Cannot move topic after itself")

            after_topic = db.query(StrategyTopic).filter(
                StrategyTopic.id == request.after_topic_id,
                StrategyTopic.thread_id == thread_id,
            ).first()
            if not after_topic:
                raise HTTPException(status_code=404, detail="after_topic_id not found")

            next_topic = db.query(StrategyTopic).filter(
                StrategyTopic.thread_id == thread_id,
                StrategyTopic.position > after_topic.position,
                StrategyTopic.id != topic_id,
            ).order_by(StrategyTopic.position).first()

            if next_topic:
                new_position = generate_position_between(after_topic.position, next_topic.position)
            else:
                new_position = generate_position_at_end(after_topic.position)
        else:
            first_topic = db.query(StrategyTopic).filter(
                StrategyTopic.thread_id == thread_id,
                StrategyTopic.id != topic_id,
            ).order_by(StrategyTopic.position).first()

            if first_topic:
                new_position = generate_position_at_start(first_topic.position)
            else:
                new_position = generate_first_position()

        topic.position = new_position
        topic.version += 1
        topic.updated_at = datetime.utcnow()

        # Get thread for logging
        thread = db.query(StrategyThread).get(thread_id)

        # Log activity
        if thread:
            log_activity(
                db, thread.strategy_id, "topic_moved",
                entity_type="topic", entity_id=topic.id,
                details={"old_position": old_position, "new_position": new_position}
            )

        db.commit()
        db.refresh(topic)

        logger.info(f"Moved topic {topic_id} from {old_position} to {new_position}")

        return topic_to_response(topic)


@router.post("/topics/{topic_id}/move-to-thread", response_model=TopicResponse)
async def move_topic_to_thread(
    topic_id: UUID,
    request: TopicMoveToThread,
    current_user: User = Depends(get_current_user),
):
    """
    Move a topic to a different thread.
    """
    with get_db_context() as db:
        topic = db.query(StrategyTopic).options(
            joinedload(StrategyTopic.thread)
            .joinedload(StrategyThread.strategy)
            .joinedload(Strategy.domain)
        ).filter(StrategyTopic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        check_strategy_access(topic.thread.strategy, current_user)

        old_thread_id = topic.thread_id

        # Validate target thread exists and is in same strategy
        old_thread = db.query(StrategyThread).get(old_thread_id)
        target_thread = db.query(StrategyThread).filter(
            StrategyThread.id == request.thread_id
        ).first()

        if not target_thread:
            raise HTTPException(status_code=404, detail="Target thread not found")

        if old_thread and target_thread.strategy_id != old_thread.strategy_id:
            raise HTTPException(status_code=400, detail="Cannot move topic to a different strategy")

        # Determine position in target thread
        if request.after_topic_id:
            after_topic = db.query(StrategyTopic).filter(
                StrategyTopic.id == request.after_topic_id,
                StrategyTopic.thread_id == request.thread_id,
            ).first()
            if not after_topic:
                raise HTTPException(status_code=404, detail="after_topic_id not found in target thread")

            next_topic = db.query(StrategyTopic).filter(
                StrategyTopic.thread_id == request.thread_id,
                StrategyTopic.position > after_topic.position,
            ).order_by(StrategyTopic.position).first()

            if next_topic:
                new_position = generate_position_between(after_topic.position, next_topic.position)
            else:
                new_position = generate_position_at_end(after_topic.position)
        else:
            first_topic = db.query(StrategyTopic).filter(
                StrategyTopic.thread_id == request.thread_id
            ).order_by(StrategyTopic.position).first()

            if first_topic:
                new_position = generate_position_at_start(first_topic.position)
            else:
                new_position = generate_first_position()

        # Update topic
        topic.thread_id = request.thread_id
        topic.position = new_position
        topic.version += 1
        topic.updated_at = datetime.utcnow()

        # Log activity
        if old_thread:
            log_activity(
                db, old_thread.strategy_id, "topic_moved_to_thread",
                entity_type="topic", entity_id=topic.id,
                details={
                    "from_thread_id": str(old_thread_id),
                    "to_thread_id": str(request.thread_id),
                    "from_thread_name": old_thread.name,
                    "to_thread_name": target_thread.name,
                }
            )

        db.commit()
        db.refresh(topic)

        logger.info(f"Moved topic {topic_id} from thread {old_thread_id} to {request.thread_id}")

        return topic_to_response(topic)


@router.delete("/topics/{topic_id}", status_code=204)
async def delete_topic(
    topic_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a topic.
    """
    with get_db_context() as db:
        topic = db.query(StrategyTopic).options(
            joinedload(StrategyTopic.thread)
            .joinedload(StrategyThread.strategy)
            .joinedload(Strategy.domain)
        ).filter(StrategyTopic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        check_strategy_access(topic.thread.strategy, current_user)

        thread = db.query(StrategyThread).get(topic.thread_id)
        topic_name = topic.name

        # Log activity before delete
        if thread:
            log_activity(
                db, thread.strategy_id, "topic_deleted",
                entity_type="topic", entity_id=topic_id,
                details={"name": topic_name, "thread_id": str(topic.thread_id)}
            )

            # Update thread version
            thread.version += 1
            thread.updated_at = datetime.utcnow()

        logger.info(f"Deleting topic {topic_id}")
        db.delete(topic)
        db.commit()


# =============================================================================
# PHASE 4: DATA & SUGGESTIONS ENDPOINTS
# =============================================================================

# --- Available Keywords Response Models ---

class AvailableKeywordResponse(BaseModel):
    """Keyword available for assignment."""
    id: UUID
    keyword: str
    search_volume: Optional[int]
    keyword_difficulty: Optional[int]
    opportunity_score: Optional[float]
    search_intent: Optional[str]
    parent_topic: Optional[str]
    estimated_traffic: Optional[int]
    assigned_thread_id: Optional[UUID]
    assigned_thread_name: Optional[str]

    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    """Cursor-based pagination info."""
    next_cursor: Optional[str]
    has_more: bool
    total_count: int
    unassigned_count: int


class AvailableKeywordsResponse(BaseModel):
    """Response for available keywords with pagination."""
    keywords: List[AvailableKeywordResponse]
    pagination: PaginationInfo


class SuggestedCluster(BaseModel):
    """Suggested cluster based on parent_topic grouping."""
    parent_topic: str
    keyword_count: int
    total_volume: int
    avg_opportunity_score: float
    sample_keywords: List[str]
    keyword_ids: List[UUID]


class SuggestedClustersResponse(BaseModel):
    """Response for suggested clusters."""
    clusters: List[SuggestedCluster]
    unclustered_count: int


class FormatPattern(BaseModel):
    """SERP format pattern evidence."""
    pattern: str
    count: int
    example_titles: List[str]


class FormatRecommendationResponse(BaseModel):
    """Format recommendation based on SERP analysis."""
    keyword: str
    recommended_format: Optional[str]
    confidence: float
    evidence: Optional[Dict] = None


@router.get("/strategies/{strategy_id}/available-keywords", response_model=AvailableKeywordsResponse)
async def get_available_keywords(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    sort_by: str = Query("opportunity_score", description="Sort field"),
    sort_dir: str = Query("desc", description="Sort direction: asc or desc"),
    intent: Optional[str] = Query(None, description="Filter by search intent"),
    min_volume: Optional[int] = Query(None, ge=0, description="Minimum search volume"),
    max_difficulty: Optional[int] = Query(None, ge=0, le=100, description="Maximum difficulty"),
    search: Optional[str] = Query(None, description="Search keyword text"),
    assigned: Optional[str] = Query("all", description="Filter: true, false, or all"),
):
    """
    Get available keywords for a strategy with keyset pagination.

    Keywords come from the analysis bound to this strategy.
    Supports filtering, sorting, and assignment status.

    Performance: Uses keyset pagination (O(1)) instead of offset (O(n)).
    Even page 1000 is as fast as page 1.
    """
    import base64
    import json

    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        # Base query - keywords from this analysis
        base_query = db.query(Keyword).filter(
            Keyword.analysis_run_id == strategy.analysis_run_id
        )

        # Get all threads for this strategy for assignment lookup
        thread_lookup = {}
        threads = db.query(StrategyThread).filter(
            StrategyThread.strategy_id == strategy_id
        ).all()
        for t in threads:
            thread_lookup[t.id] = t.name

        # Get assigned keyword IDs for this strategy
        assigned_keyword_ids = db.query(ThreadKeyword.keyword_id).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == strategy_id
        ).subquery()

        # Apply filters to base query for counts
        def apply_filters(q):
            from src.database.models import SearchIntent
            if intent:
                try:
                    intent_enum = SearchIntent(intent)
                    q = q.filter(Keyword.search_intent == intent_enum)
                except ValueError:
                    pass
            if min_volume is not None:
                q = q.filter(Keyword.search_volume >= min_volume)
            if max_difficulty is not None:
                q = q.filter(
                    or_(
                        Keyword.keyword_difficulty <= max_difficulty,
                        Keyword.keyword_difficulty.is_(None)
                    )
                )
            if search:
                q = q.filter(Keyword.keyword.ilike(f"%{search}%"))
            return q

        query = apply_filters(base_query)

        if assigned == "true":
            query = query.filter(Keyword.id.in_(assigned_keyword_ids))
        elif assigned == "false":
            query = query.filter(~Keyword.id.in_(assigned_keyword_ids))

        # Get counts (only on first page to avoid overhead)
        total_count = 0
        unassigned_count = 0
        if not cursor:
            total_count = query.count()
            unassigned_query = apply_filters(base_query).filter(~Keyword.id.in_(assigned_keyword_ids))
            unassigned_count = unassigned_query.count()

        # Determine sort column and direction
        sort_column_map = {
            "opportunity_score": Keyword.opportunity_score,
            "volume": Keyword.search_volume,
            "difficulty": Keyword.keyword_difficulty,
            "keyword": Keyword.keyword,
        }
        sort_column = sort_column_map.get(sort_by, Keyword.opportunity_score)
        sort_column_name = sort_by if sort_by in sort_column_map else "opportunity_score"
        is_desc = sort_dir != "asc"

        # KEYSET PAGINATION: Apply cursor filter
        if cursor:
            try:
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                cursor_value = cursor_data.get("v")  # sort column value
                cursor_id = cursor_data.get("id")
                cursor_total = cursor_data.get("total", 0)
                cursor_unassigned = cursor_data.get("unassigned", 0)

                # Restore counts from cursor
                total_count = cursor_total
                unassigned_count = cursor_unassigned

                if cursor_id:
                    cursor_uuid = UUID(cursor_id)

                    # Keyset condition: (sort_col, id) > (cursor_val, cursor_id)
                    # For DESC: (sort_col < cursor_val) OR (sort_col = cursor_val AND id > cursor_id)
                    # For ASC: (sort_col > cursor_val) OR (sort_col = cursor_val AND id > cursor_id)
                    if cursor_value is not None:
                        if is_desc:
                            query = query.filter(
                                or_(
                                    sort_column < cursor_value,
                                    and_(
                                        sort_column == cursor_value,
                                        Keyword.id > cursor_uuid
                                    )
                                )
                            )
                        else:
                            query = query.filter(
                                or_(
                                    sort_column > cursor_value,
                                    and_(
                                        sort_column == cursor_value,
                                        Keyword.id > cursor_uuid
                                    )
                                )
                            )
                    else:
                        # Cursor value was null, just filter by ID
                        query = query.filter(Keyword.id > cursor_uuid)
            except Exception:
                pass  # Ignore invalid cursor, start from beginning

        # Apply sorting
        if is_desc:
            query = query.order_by(sort_column.desc().nullslast(), Keyword.id)
        else:
            query = query.order_by(sort_column.asc().nullslast(), Keyword.id)

        # Execute with limit + 1 to check for more
        keywords = query.limit(limit + 1).all()
        has_more = len(keywords) > limit
        keywords = keywords[:limit]

        # Get assignment info for these keywords (single query)
        keyword_ids = [k.id for k in keywords]
        assignments = db.query(
            ThreadKeyword.keyword_id, ThreadKeyword.thread_id
        ).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == strategy_id,
            ThreadKeyword.keyword_id.in_(keyword_ids)
        ).all()
        assignment_map = {a[0]: a[1] for a in assignments}

        # Build response
        result = []
        for kw in keywords:
            thread_id = assignment_map.get(kw.id)
            result.append(AvailableKeywordResponse(
                id=kw.id,
                keyword=kw.keyword,
                search_volume=kw.search_volume,
                keyword_difficulty=kw.keyword_difficulty,
                opportunity_score=kw.opportunity_score,
                search_intent=kw.search_intent.value if kw.search_intent else None,
                parent_topic=kw.parent_topic,
                estimated_traffic=kw.estimated_traffic,
                assigned_thread_id=thread_id,
                assigned_thread_name=thread_lookup.get(thread_id) if thread_id else None,
            ))

        # Generate keyset cursor
        next_cursor = None
        if has_more and keywords:
            last_kw = keywords[-1]
            # Get the sort column value
            sort_value = getattr(last_kw, sort_column_name.replace("volume", "search_volume"))
            cursor_data = {
                "v": sort_value,  # sort column value
                "id": str(last_kw.id),
                "total": total_count,
                "unassigned": unassigned_count,
            }
            next_cursor = base64.b64encode(json.dumps(cursor_data).encode()).decode()

        return AvailableKeywordsResponse(
            keywords=result,
            pagination=PaginationInfo(
                next_cursor=next_cursor,
                has_more=has_more,
                total_count=total_count,
                unassigned_count=unassigned_count,
            )
        )


@router.get("/strategies/{strategy_id}/suggested-clusters", response_model=SuggestedClustersResponse)
async def get_suggested_clusters(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get suggested clusters based on parent_topic grouping.

    Groups unassigned keywords by their parent_topic field (from DataForSEO)
    and returns cluster suggestions with aggregated metrics.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        # Get assigned keyword IDs
        assigned_ids = db.query(ThreadKeyword.keyword_id).join(
            StrategyThread
        ).filter(
            StrategyThread.strategy_id == strategy_id
        ).subquery()

        # Get unassigned keywords with parent_topic
        keywords_with_topic = db.query(Keyword).filter(
            Keyword.analysis_run_id == strategy.analysis_run_id,
            ~Keyword.id.in_(assigned_ids),
            Keyword.parent_topic.isnot(None),
            Keyword.parent_topic != "",
        ).all()

        # Count unclustered (no parent_topic)
        unclustered_count = db.query(func.count(Keyword.id)).filter(
            Keyword.analysis_run_id == strategy.analysis_run_id,
            ~Keyword.id.in_(assigned_ids),
            or_(Keyword.parent_topic.is_(None), Keyword.parent_topic == ""),
        ).scalar() or 0

        # Group by parent_topic
        topic_groups: Dict[str, List[Keyword]] = {}
        for kw in keywords_with_topic:
            topic = kw.parent_topic
            if topic not in topic_groups:
                topic_groups[topic] = []
            topic_groups[topic].append(kw)

        # Build cluster suggestions
        clusters = []
        for parent_topic, kws in topic_groups.items():
            if len(kws) < 2:  # Skip single-keyword topics
                continue

            total_volume = sum(k.search_volume or 0 for k in kws)
            avg_opportunity = sum(k.opportunity_score or 0 for k in kws) / len(kws) if kws else 0

            # Get top 3 by opportunity score for samples
            sorted_kws = sorted(kws, key=lambda k: k.opportunity_score or 0, reverse=True)
            sample_keywords = [k.keyword for k in sorted_kws[:3]]

            clusters.append(SuggestedCluster(
                parent_topic=parent_topic,
                keyword_count=len(kws),
                total_volume=total_volume,
                avg_opportunity_score=round(avg_opportunity, 2),
                sample_keywords=sample_keywords,
                keyword_ids=[k.id for k in kws],
            ))

        # Sort by total volume descending
        clusters.sort(key=lambda c: c.total_volume, reverse=True)

        return SuggestedClustersResponse(
            clusters=clusters[:50],  # Limit to top 50
            unclustered_count=unclustered_count,
        )


@router.get("/keywords/{keyword_id}/format-recommendation", response_model=FormatRecommendationResponse)
async def get_format_recommendation(
    keyword_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get SERP-based format recommendation for a keyword.

    Analyzes SERP titles from the analysis data to suggest content format.
    """
    with get_db_context() as db:
        keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword:
            raise HTTPException(status_code=404, detail="Keyword not found")

        # Check access via analysis run -> domain
        if keyword.analysis_run_id:
            run = db.query(AnalysisRun).filter(AnalysisRun.id == keyword.analysis_run_id).first()
            if run:
                domain = db.query(Domain).filter(Domain.id == run.domain_id).first()
                if domain:
                    check_domain_access_strategy(domain, current_user)

        # Try to get SERP data from serp_competitors or api_calls
        from src.database.models import SERPCompetitor, APICall

        # Get SERP competitor data for this keyword
        serp_competitors = db.query(SERPCompetitor).filter(
            SERPCompetitor.keyword_id == keyword_id
        ).order_by(SERPCompetitor.position).limit(10).all()

        # Analyze title patterns
        patterns = {
            "listicle": 0,
            "how_to": 0,
            "comparison": 0,
            "guide": 0,
            "review": 0,
            "question": 0,
            "other": 0,
        }
        example_titles: Dict[str, List[str]] = {k: [] for k in patterns.keys()}

        for sc in serp_competitors:
            title = sc.page_title or ""
            title_lower = title.lower()

            # Pattern detection
            if any(x in title_lower for x in ["top", "best", "list of", "ranking"]) or \
               any(c.isdigit() for c in title[:10]):
                patterns["listicle"] += 1
                example_titles["listicle"].append(title)
            elif any(x in title_lower for x in ["how to", "how do", "tutorial", "step"]):
                patterns["how_to"] += 1
                example_titles["how_to"].append(title)
            elif any(x in title_lower for x in ["vs", "versus", "comparison", "compare"]):
                patterns["comparison"] += 1
                example_titles["comparison"].append(title)
            elif any(x in title_lower for x in ["guide", "ultimate", "complete", "comprehensive"]):
                patterns["guide"] += 1
                example_titles["guide"].append(title)
            elif any(x in title_lower for x in ["review", "tested", "honest"]):
                patterns["review"] += 1
                example_titles["review"].append(title)
            elif title.endswith("?") or any(x in title_lower for x in ["what is", "why", "when"]):
                patterns["question"] += 1
                example_titles["question"].append(title)
            else:
                patterns["other"] += 1
                example_titles["other"].append(title)

        # Determine recommended format
        total_analyzed = sum(patterns.values())
        if total_analyzed == 0:
            return FormatRecommendationResponse(
                keyword=keyword.keyword,
                recommended_format=None,
                confidence=0.0,
                evidence=None,
            )

        # Find dominant pattern
        dominant_pattern = max(patterns.items(), key=lambda x: x[1])
        confidence = dominant_pattern[1] / total_analyzed if total_analyzed > 0 else 0

        # Build evidence
        evidence = {
            "titles_analyzed": total_analyzed,
            "patterns": [
                {
                    "pattern": pattern,
                    "count": count,
                    "example_titles": example_titles[pattern][:2],
                }
                for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)
                if count > 0
            ]
        }

        return FormatRecommendationResponse(
            keyword=keyword.keyword,
            recommended_format=dominant_pattern[0] if confidence >= 0.3 else None,
            confidence=round(confidence, 2),
            evidence=evidence,
        )


# =============================================================================
# PHASE 5: EXPORT & VALIDATION
# =============================================================================

# --- Validation Models ---

class ValidationError(BaseModel):
    """Hard validation error that blocks export."""
    code: str
    message: str
    thread_id: Optional[UUID] = None


class ValidationWarning(BaseModel):
    """Soft validation warning (export still allowed)."""
    code: str
    message: str
    thread_id: Optional[UUID] = None


class ExportValidationResponse(BaseModel):
    """Response for export validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]


# --- Export Models ---

class ExportRequest(BaseModel):
    """Request to export a strategy."""
    format: str = Field("monok_json", description="Export format: monok_json, monok_display, csv")
    include_empty_threads: bool = Field(False, description="Include threads without keywords")


class ExportSummary(BaseModel):
    """Summary statistics for an export."""
    total_threads: int
    confirmed_threads: int
    total_topics: int
    total_keywords: int
    total_search_volume: int


class ExportResponse(BaseModel):
    """Response for strategy export."""
    export_id: UUID
    format: str
    data: Dict[str, Any]
    download_url: str
    validation: Dict[str, Any]


class ExportHistoryItem(BaseModel):
    """Export history list item."""
    id: UUID
    format: str
    exported_at: datetime
    exported_by: Optional[str]
    thread_count: Optional[int]
    topic_count: Optional[int]
    keyword_count: Optional[int]

    class Config:
        from_attributes = True


class ExportHistoryResponse(BaseModel):
    """Response for export history."""
    exports: List[ExportHistoryItem]


def validate_strategy_for_export(db: Session, strategy: Strategy) -> ExportValidationResponse:
    """Validate a strategy meets export requirements."""
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    # Get threads
    threads = db.query(StrategyThread).filter(
        StrategyThread.strategy_id == strategy.id
    ).all()

    # HARD REQUIREMENTS

    # 1. Must have at least one thread
    if len(threads) == 0:
        errors.append(ValidationError(
            code="no_threads",
            message="Strategy must have at least one thread"
        ))

    # 2. Each confirmed thread must have at least one keyword
    for thread in threads:
        if thread.status == ThreadStatus.CONFIRMED:
            keyword_count = db.query(func.count(ThreadKeyword.id)).filter(
                ThreadKeyword.thread_id == thread.id
            ).scalar() or 0

            if keyword_count == 0:
                errors.append(ValidationError(
                    code="thread_no_keywords",
                    message=f"Thread '{thread.name}' has no keywords assigned",
                    thread_id=thread.id,
                ))

    # 3. Each confirmed thread must have strategic_context
    for thread in threads:
        if thread.status == ThreadStatus.CONFIRMED:
            instructions = thread.custom_instructions or {}
            if not instructions.get("strategic_context"):
                errors.append(ValidationError(
                    code="thread_no_context",
                    message=f"Thread '{thread.name}' missing strategic context",
                    thread_id=thread.id,
                ))

    # SOFT REQUIREMENTS (warnings)

    # 1. Threads without topics
    for thread in threads:
        topic_count = db.query(func.count(StrategyTopic.id)).filter(
            StrategyTopic.thread_id == thread.id
        ).scalar() or 0

        if topic_count == 0:
            warnings.append(ValidationWarning(
                code="thread_no_topics",
                message=f"Thread '{thread.name}' has no topics defined",
                thread_id=thread.id,
            ))

    # 2. Topics without target_url
    for thread in threads:
        topics_without_url = db.query(StrategyTopic).filter(
            StrategyTopic.thread_id == thread.id,
            or_(StrategyTopic.target_url.is_(None), StrategyTopic.target_url == ""),
        ).all()

        for topic in topics_without_url:
            warnings.append(ValidationWarning(
                code="topic_no_url",
                message=f"Topic '{topic.name}' has no target URL",
                thread_id=thread.id,
            ))

    # 3. Draft threads included
    draft_threads = [t for t in threads if t.status == ThreadStatus.DRAFT]
    if draft_threads:
        warnings.append(ValidationWarning(
            code="draft_threads",
            message=f"{len(draft_threads)} threads are still in draft status"
        ))

    # 4. Missing format recommendations
    for thread in threads:
        instructions = thread.custom_instructions or {}
        if not instructions.get("format_recommendations"):
            warnings.append(ValidationWarning(
                code="no_format_recommendation",
                message=f"Thread '{thread.name}' has no format recommendations",
                thread_id=thread.id,
            ))

    return ExportValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def build_monok_export(db: Session, strategy: Strategy, include_empty_threads: bool) -> Dict[str, Any]:
    """Build Monok JSON export package."""
    # Get domain info
    domain = db.query(Domain).get(strategy.domain_id)
    analysis = db.query(AnalysisRun).get(strategy.analysis_run_id)

    # Get threads with keywords and topics
    threads_data = []
    total_keywords = 0
    total_volume = 0
    total_topics = 0
    confirmed_threads = 0

    threads = db.query(StrategyThread).filter(
        StrategyThread.strategy_id == strategy.id
    ).order_by(StrategyThread.position).all()

    for thread in threads:
        # Get keywords
        thread_keywords = db.query(
            ThreadKeyword, Keyword
        ).join(
            Keyword, ThreadKeyword.keyword_id == Keyword.id
        ).filter(
            ThreadKeyword.thread_id == thread.id
        ).order_by(ThreadKeyword.position).all()

        if not include_empty_threads and len(thread_keywords) == 0:
            continue

        # Get topics
        topics = db.query(StrategyTopic).filter(
            StrategyTopic.thread_id == thread.id
        ).order_by(StrategyTopic.position).all()

        keywords_data = []
        thread_volume = 0
        for tk, kw in thread_keywords:
            keywords_data.append({
                "keyword": kw.keyword,
                "search_volume": kw.search_volume,
                "difficulty": kw.keyword_difficulty,
                "opportunity_score": kw.opportunity_score,
                "intent": kw.search_intent.value if kw.search_intent else None,
            })
            thread_volume += kw.search_volume or 0

        topics_data = []
        for topic in topics:
            topics_data.append({
                "topic_name": topic.name,
                "primary_keyword": topic.primary_keyword,
                "content_type": topic.content_type.value if topic.content_type else "cluster",
                "target_url": topic.target_url,
                "status": topic.status.value if topic.status else "draft",
            })

        threads_data.append({
            "thread_name": thread.name,
            "thread_id": str(thread.id),
            "priority": thread.priority,
            "status": thread.status.value if thread.status else "draft",
            "keywords": keywords_data,
            "topics": topics_data,
            "custom_instructions": thread.custom_instructions or {},
        })

        total_keywords += len(keywords_data)
        total_volume += thread_volume
        total_topics += len(topics_data)
        if thread.status == ThreadStatus.CONFIRMED:
            confirmed_threads += 1

    export_data = {
        "export_id": None,  # Will be set after DB insert
        "domain": domain.domain if domain else None,
        "strategy_name": strategy.name,
        "strategy_id": str(strategy.id),
        "analysis_id": str(strategy.analysis_run_id),
        "analysis_date": analysis.created_at.isoformat() if analysis and analysis.created_at else None,
        "exported_at": datetime.utcnow().isoformat(),
        "exported_by": None,  # Would come from auth
        "threads": threads_data,
        "summary": {
            "total_threads": len(threads_data),
            "confirmed_threads": confirmed_threads,
            "total_topics": total_topics,
            "total_keywords": total_keywords,
            "total_search_volume": total_volume,
        },
    }

    return export_data


@router.post("/strategies/{strategy_id}/validate-export", response_model=ExportValidationResponse)
async def validate_export(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Validate a strategy for export.

    Returns hard errors (blocking) and soft warnings (informational).
    Export is only allowed if there are no hard errors.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        return validate_strategy_for_export(db, strategy)


@router.post("/strategies/{strategy_id}/export", response_model=ExportResponse)
async def export_strategy(
    strategy_id: UUID,
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Export a strategy to the specified format.

    Supported formats:
    - monok_json: Structured JSON for Monok
    - monok_display: Human-readable format
    - csv: Spreadsheet format
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        # Validate first
        validation = validate_strategy_for_export(db, strategy)

        # Allow export even with warnings, but block on errors
        if not validation.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "export_validation_failed",
                    "errors": [e.model_dump() for e in validation.errors],
                    "message": "Strategy does not meet export requirements"
                }
            )

        # Build export data
        if request.format in ["monok_json", "monok_display"]:
            export_data = build_monok_export(db, strategy, request.include_empty_threads)
        elif request.format == "csv":
            # CSV format - flatten the data
            export_data = build_monok_export(db, strategy, request.include_empty_threads)
            # For CSV, we'll just store the JSON and let the download endpoint convert
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

        # Store export record
        export_record = StrategyExport(
            strategy_id=strategy_id,
            format=request.format,
            exported_data=export_data,
            exported_at=datetime.utcnow(),
            thread_count=export_data["summary"]["total_threads"],
            topic_count=export_data["summary"]["total_topics"],
            keyword_count=export_data["summary"]["total_keywords"],
        )
        db.add(export_record)
        db.flush()

        # Update export_id in the data
        export_data["export_id"] = str(export_record.id)
        export_record.exported_data = export_data

        # Log activity
        log_activity(
            db, strategy_id, "exported",
            entity_type="export", entity_id=export_record.id,
            details={
                "format": request.format,
                "thread_count": export_data["summary"]["total_threads"],
                "keyword_count": export_data["summary"]["total_keywords"],
            }
        )

        db.commit()

        logger.info(f"Exported strategy {strategy_id} in {request.format} format")

        return ExportResponse(
            export_id=export_record.id,
            format=request.format,
            data=export_data,
            download_url=f"/api/exports/{export_record.id}/download",
            validation={
                "warnings": [w.model_dump() for w in validation.warnings]
            }
        )


@router.get("/strategies/{strategy_id}/exports", response_model=ExportHistoryResponse)
async def get_export_history(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Get export history for a strategy.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        exports = db.query(StrategyExport).filter(
            StrategyExport.strategy_id == strategy_id
        ).order_by(StrategyExport.exported_at.desc()).limit(limit).all()

        return ExportHistoryResponse(
            exports=[
                ExportHistoryItem(
                    id=e.id,
                    format=e.format,
                    exported_at=e.exported_at,
                    exported_by=e.exported_by,
                    thread_count=e.thread_count,
                    topic_count=e.topic_count,
                    keyword_count=e.keyword_count,
                )
                for e in exports
            ]
        )


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Download a previous export.

    Returns the export data in the original format.
    """
    from fastapi.responses import JSONResponse, Response

    with get_db_context() as db:
        export = db.query(StrategyExport).filter(StrategyExport.id == export_id).first()
        if not export:
            raise HTTPException(status_code=404, detail="Export not found")

        # Check access via strategy
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == export.strategy_id).first()
        if strategy:
            check_strategy_access(strategy, current_user)

        if export.format == "csv":
            # Convert to CSV
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                "Thread", "Priority", "Status", "Keyword", "Search Volume",
                "Difficulty", "Opportunity Score", "Intent"
            ])

            # Data
            for thread in export.exported_data.get("threads", []):
                for keyword in thread.get("keywords", []):
                    writer.writerow([
                        thread["thread_name"],
                        thread.get("priority", ""),
                        thread.get("status", ""),
                        keyword["keyword"],
                        keyword.get("search_volume", ""),
                        keyword.get("difficulty", ""),
                        keyword.get("opportunity_score", ""),
                        keyword.get("intent", ""),
                    ])

            csv_content = output.getvalue()
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=strategy_export_{export_id}.csv"
                }
            )

        elif export.format == "monok_display":
            # Human-readable text format
            lines = []
            data = export.exported_data

            lines.append(f"# {data.get('strategy_name', 'Strategy Export')}")
            lines.append(f"Domain: {data.get('domain', 'N/A')}")
            lines.append(f"Exported: {data.get('exported_at', 'N/A')}")
            lines.append("")

            summary = data.get("summary", {})
            lines.append(f"## Summary")
            lines.append(f"- Threads: {summary.get('total_threads', 0)}")
            lines.append(f"- Topics: {summary.get('total_topics', 0)}")
            lines.append(f"- Keywords: {summary.get('total_keywords', 0)}")
            lines.append(f"- Total Search Volume: {summary.get('total_search_volume', 0):,}")
            lines.append("")

            for thread in data.get("threads", []):
                lines.append(f"## Thread: {thread['thread_name']}")
                lines.append(f"Priority: P{thread.get('priority', 'N/A')} | Status: {thread.get('status', 'draft')}")
                lines.append("")

                instructions = thread.get("custom_instructions", {})
                if instructions.get("strategic_context"):
                    lines.append(f"### Strategic Context")
                    lines.append(instructions["strategic_context"])
                    lines.append("")

                if thread.get("keywords"):
                    lines.append(f"### Keywords ({len(thread['keywords'])})")
                    for kw in thread["keywords"][:20]:  # Limit display
                        lines.append(f"- {kw['keyword']} (vol: {kw.get('search_volume', 'N/A')}, "
                                   f"diff: {kw.get('difficulty', 'N/A')}, opp: {kw.get('opportunity_score', 'N/A')})")
                    if len(thread["keywords"]) > 20:
                        lines.append(f"  ... and {len(thread['keywords']) - 20} more")
                    lines.append("")

                if thread.get("topics"):
                    lines.append(f"### Topics ({len(thread['topics'])})")
                    for topic in thread["topics"]:
                        lines.append(f"- [{topic.get('content_type', 'cluster').upper()}] {topic['topic_name']}")
                        if topic.get("target_url"):
                            lines.append(f"  URL: {topic['target_url']}")
                    lines.append("")

                lines.append("---")
                lines.append("")

            content = "\n".join(lines)
            return Response(
                content=content,
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename=strategy_export_{export_id}.txt"
                }
            )

        else:
            # JSON format (default)
            return JSONResponse(
                content=export.exported_data,
                headers={
                    "Content-Disposition": f"attachment; filename=strategy_export_{export_id}.json"
                }
            )


# =============================================================================
# PHASE 6: ACTIVITY LOG
# =============================================================================

class ActivityLogItem(BaseModel):
    """Activity log entry."""
    id: UUID
    action: str
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    user_id: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityLogPagination(BaseModel):
    """Pagination info for activity log."""
    next_cursor: Optional[str]
    has_more: bool


class ActivityLogResponse(BaseModel):
    """Response for activity log."""
    activities: List[ActivityLogItem]
    pagination: ActivityLogPagination


@router.get("/strategies/{strategy_id}/activity", response_model=ActivityLogResponse)
async def get_activity_log(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
):
    """
    Get activity log for a strategy.

    Returns a chronological list of all changes made to the strategy,
    its threads, topics, and keyword assignments.
    """
    import base64
    import json

    with get_db_context() as db:
        strategy = db.query(Strategy).options(
            joinedload(Strategy.domain)
        ).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        check_strategy_access(strategy, current_user)

        query = db.query(StrategyActivityLog).filter(
            StrategyActivityLog.strategy_id == strategy_id
        ).order_by(StrategyActivityLog.created_at.desc())

        # Apply cursor
        if cursor:
            try:
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                offset = cursor_data.get("offset", 0)
                query = query.offset(offset)
            except:
                pass

        # Get results with limit + 1 to check for more
        activities = query.limit(limit + 1).all()
        has_more = len(activities) > limit
        activities = activities[:limit]

        # Generate next cursor
        next_cursor = None
        if has_more:
            current_offset = 0
            if cursor:
                try:
                    cursor_data = json.loads(base64.b64decode(cursor).decode())
                    current_offset = cursor_data.get("offset", 0)
                except:
                    pass
            cursor_data = {"offset": current_offset + limit}
            next_cursor = base64.b64encode(json.dumps(cursor_data).encode()).decode()

        return ActivityLogResponse(
            activities=[
                ActivityLogItem(
                    id=a.id,
                    action=a.action,
                    entity_type=a.entity_type,
                    entity_id=a.entity_id,
                    user_id=a.user_id,
                    details=a.details,
                    created_at=a.created_at,
                )
                for a in activities
            ],
            pagination=ActivityLogPagination(
                next_cursor=next_cursor,
                has_more=has_more,
            )
        )

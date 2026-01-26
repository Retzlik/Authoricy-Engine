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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["strategy"])


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
    status: Optional[str] = Query(None, description="Filter by status: draft, approved, archived"),
    include_archived: bool = Query(False, description="Include archived strategies"),
):
    """
    List strategies for a domain.

    Returns strategies with aggregated counts for threads, topics, and keywords.
    """
    with get_db_context() as db:
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

        # Build response with aggregations
        result = []
        for strategy in strategies:
            # Get thread count
            thread_count = db.query(func.count(StrategyThread.id)).filter(
                StrategyThread.strategy_id == strategy.id
            ).scalar() or 0

            # Get topic count (across all threads)
            topic_count = db.query(func.count(StrategyTopic.id)).join(
                StrategyThread
            ).filter(
                StrategyThread.strategy_id == strategy.id
            ).scalar() or 0

            # Get keyword count (distinct keywords across all threads)
            keyword_count = db.query(func.count(ThreadKeyword.id)).join(
                StrategyThread
            ).filter(
                StrategyThread.strategy_id == strategy.id
            ).scalar() or 0

            # Get analysis info
            analysis = db.query(AnalysisRun).get(strategy.analysis_run_id)

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
                thread_count=thread_count,
                topic_count=topic_count,
                keyword_count=keyword_count,
            ))

        return StrategyListResponse(strategies=result)


@router.get("/strategies/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy(strategy_id: UUID):
    """
    Get a single strategy with threads and metrics.

    Returns the full strategy with all threads (including computed metrics)
    and source analysis information.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Get threads ordered by position
        threads = db.query(StrategyThread).filter(
            StrategyThread.strategy_id == strategy_id
        ).order_by(StrategyThread.position).all()

        thread_responses = [thread_to_response(db, t) for t in threads]

        # Calculate aggregations
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
async def create_strategy(request: StrategyCreate):
    """
    Create a new strategy from an analysis.

    The strategy is bound to a specific analysis_run_id and will use keywords
    from that analysis only.
    """
    with get_db_context() as db:
        # Validate domain exists
        domain = db.query(Domain).filter(Domain.id == request.domain_id).first()
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

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
async def update_strategy(strategy_id: UUID, request: StrategyUpdate):
    """
    Update a strategy (with optimistic locking).

    The version field must match the current version, otherwise a 409 conflict
    is returned.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

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
async def duplicate_strategy(strategy_id: UUID, request: StrategyDuplicate):
    """
    Duplicate a strategy with all threads, topics, and keyword assignments.
    """
    with get_db_context() as db:
        # Get source strategy
        source = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Strategy not found")

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
async def archive_strategy(strategy_id: UUID):
    """Archive a strategy (soft delete)."""
    with get_db_context() as db:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

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
async def restore_strategy(strategy_id: UUID):
    """Restore an archived strategy."""
    with get_db_context() as db:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

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
async def delete_strategy(strategy_id: UUID):
    """
    Hard delete a strategy (only if archived).

    All threads, topics, and keyword assignments are deleted via CASCADE.
    """
    with get_db_context() as db:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

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
async def list_threads(strategy_id: UUID):
    """
    List threads for a strategy (ordered by position).

    Returns threads with computed metrics from assigned keywords.
    """
    with get_db_context() as db:
        # Validate strategy exists
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        threads = db.query(StrategyThread).filter(
            StrategyThread.strategy_id == strategy_id
        ).order_by(StrategyThread.position).all()

        thread_responses = [thread_to_response(db, t) for t in threads]

        return ThreadListResponse(threads=thread_responses)


@router.post("/strategies/{strategy_id}/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(strategy_id: UUID, request: ThreadCreate):
    """
    Create a new thread.

    Use after_thread_id to insert after a specific thread, or null to insert
    at the beginning.
    """
    with get_db_context() as db:
        # Validate strategy exists
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

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
async def update_thread(thread_id: UUID, request: ThreadUpdate):
    """
    Update a thread (with optimistic locking).

    The version field must match the current version, otherwise a 409 conflict
    is returned.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

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
async def move_thread(thread_id: UUID, request: ThreadMove):
    """
    Move a thread to a new position.

    Use after_thread_id to move after a specific thread, or null to move
    to the beginning.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

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
async def delete_thread(thread_id: UUID):
    """
    Delete a thread.

    All topics and keyword assignments for this thread are deleted via CASCADE.
    """
    with get_db_context() as db:
        thread = db.query(StrategyThread).filter(StrategyThread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

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
    status: Optional[str] = Query("completed", description="Filter by status"),
):
    """
    List available analyses for a domain.

    Use this to select which analysis to use when creating a strategy.
    """
    with get_db_context() as db:
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

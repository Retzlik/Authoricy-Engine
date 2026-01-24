"""
API Endpoint for SEO Analysis

FastAPI webhook handler that:
1. Receives analysis requests (from Tally form or direct API call)
2. Runs Context Intelligence to understand the business
3. Triggers focused data collection in background
4. Validates data quality before AI analysis
5. Sends results via email when complete
"""

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr, Field

from src.collector import (
    DataForSEOClient,
    DataCollectionOrchestrator,
    CollectionConfig,
    CollectionResult,
    compile_analysis_data,
)
from src.analyzer import AnalysisEngine
from src.reporter import ReportGenerator
from src.delivery import EmailDelivery
from src.database import (
    init_db,
    check_db_connection,
    get_db_info,
    run_analysis_with_db,
    get_quality_summary,
    store_context_intelligence,
    create_analysis_run,
    update_run_status,
    complete_run,
    AnalysisStatus,
)
from src.context import (
    PrimaryGoal,
    gather_context_intelligence,
    ContextIntelligenceResult,
)

# Configure logging to stdout (Railway treats stderr as errors)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,  # Explicitly use stdout
    force=True,  # Override any existing config
)
logger = logging.getLogger(__name__)

# Quiet down chatty loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Create FastAPI app
app = FastAPI(
    title="Authoricy SEO Analyzer",
    description="Automated SEO analysis powered by DataForSEO and Claude AI",
    version="0.3.0",
)


# ============================================================================
# STARTUP - Initialize Database
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Initializing database...")
    try:
        init_db()
        if check_db_connection():
            logger.info("Database connection verified")
        else:
            logger.warning("Database connection check failed - continuing anyway")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't fail startup - the app can still work without DB


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """
    Request to trigger an SEO analysis.

    Enhanced with Context Intelligence inputs for:
    - Goal alignment (traffic, leads, authority, balanced)
    - Market validation and discovery
    - Competitor validation and classification
    """
    domain: str
    email: EmailStr
    company_name: Optional[str] = None

    # REQUIRED: Primary market and goal
    primary_market: Optional[str] = Field(
        default=None,
        description="Primary market code (e.g., 'se', 'us', 'de', 'uk')"
    )
    primary_goal: Literal["traffic", "leads", "authority", "balanced"] = Field(
        default="balanced",
        description="Primary SEO goal: traffic (visitors), leads (inquiries), authority (backlinks), balanced (all)"
    )

    # OPTIONAL: Enhanced inputs
    primary_language: Optional[str] = Field(
        default=None,
        description="Primary language code (e.g., 'sv', 'en', 'de'). Auto-detected from market if not provided."
    )
    secondary_markets: Optional[List[str]] = Field(
        default=None,
        description="Additional market codes to analyze (e.g., ['de', 'no'])"
    )
    known_competitors: Optional[List[str]] = Field(
        default=None,
        description="Known competitor domains (e.g., ['competitor1.com', 'competitor2.com'])"
    )

    # Legacy fields (for backwards compatibility)
    market: Optional[str] = Field(
        default=None,
        description="[DEPRECATED] Use primary_market instead. Accepts market code or full name."
    )
    language: Optional[str] = Field(
        default=None,
        description="[DEPRECATED] Use primary_language instead. Full language name for legacy support."
    )

    # Options
    skip_ai_analysis: bool = False
    skip_context_intelligence: bool = False  # Skip the context gathering phase
    priority: str = "normal"  # normal, high

    def get_resolved_market(self) -> str:
        """
        Resolve market from primary_market or legacy market field.

        Handles:
        - primary_market: "uk", "us", "se", etc.
        - market (legacy): "uk", "United Kingdom", "UK", etc.

        Returns lowercase market code, defaults to "us" if nothing provided.
        """
        # Market name to code mapping (for legacy full names)
        MARKET_NAME_TO_CODE = {
            "united states": "us", "usa": "us", "america": "us",
            "united kingdom": "uk", "britain": "uk", "great britain": "uk", "england": "uk",
            "sweden": "se", "sverige": "se",
            "germany": "de", "deutschland": "de",
            "france": "fr",
            "norway": "no", "norge": "no",
            "denmark": "dk", "danmark": "dk",
            "finland": "fi", "suomi": "fi",
            "netherlands": "nl", "holland": "nl",
            "spain": "es", "españa": "es",
            "italy": "it", "italia": "it",
            "australia": "au",
            "canada": "ca",
        }

        # Valid market codes
        VALID_CODES = {"us", "uk", "se", "de", "fr", "no", "dk", "fi", "nl", "es", "it", "au", "ca", "global"}

        # Try primary_market first
        if self.primary_market:
            code = self.primary_market.lower().strip()
            if code in VALID_CODES:
                return code
            # Maybe it's a full name
            if code in MARKET_NAME_TO_CODE:
                return MARKET_NAME_TO_CODE[code]

        # Fall back to legacy market field
        if self.market:
            code = self.market.lower().strip()
            if code in VALID_CODES:
                return code
            if code in MARKET_NAME_TO_CODE:
                return MARKET_NAME_TO_CODE[code]

        # Default to US (most common, English)
        return "us"


class AnalysisResponse(BaseModel):
    """Response after triggering analysis."""
    job_id: str
    domain: str
    email: str
    status: str
    message: str


class JobStatus(BaseModel):
    """Status of an analysis job."""
    job_id: str
    domain: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# ============================================================================
# IN-MEMORY JOB TRACKING (replace with Redis/DB in production)
# ============================================================================

jobs: dict[str, JobStatus] = {}


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Authoricy SEO Analyzer"}


@app.get("/api/health")
async def health():
    """Detailed health check including database status."""
    db_connected = False
    try:
        db_connected = check_db_connection()
    except:
        pass

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.3.0",
        "jobs_in_queue": len([j for j in jobs.values() if j.status == "running"]),
        "database": "connected" if db_connected else "disconnected",
    }


@app.get("/api/database")
async def database_status():
    """
    Get detailed database status.

    Returns:
        - Database type (postgresql/sqlite)
        - Connection status
        - Tables created
        - PostgreSQL extensions installed

    Use this to debug Railway deployment issues.
    """
    try:
        db_info = get_db_info()
        return {
            "status": "ok" if db_info["connected"] else "error",
            "database_type": db_info["database_type"],
            "connected": db_info["connected"],
            "table_count": db_info["table_count"],
            "tables": db_info["tables"],
            "extensions": db_info.get("extensions", []),
            "recommended_extensions": ["uuid-ossp", "pg_trgm", "btree_gin"],
            "connection_url": db_info["connection_url"],
            "error": db_info.get("error"),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.post("/api/migrate")
async def run_migration():
    """
    Run database migrations to add missing columns.
    Call this once after deploying new model changes.
    """
    from src.database.session import get_db_context
    from sqlalchemy import text

    migrations = [
        "ALTER TABLE context_intelligence ADD COLUMN IF NOT EXISTS should_adjust_market BOOLEAN DEFAULT FALSE",
        "ALTER TABLE context_intelligence ADD COLUMN IF NOT EXISTS suggested_market VARCHAR(50)",
        "ALTER TABLE context_intelligence ADD COLUMN IF NOT EXISTS language_mismatch BOOLEAN DEFAULT FALSE",
        "ALTER TABLE context_intelligence ADD COLUMN IF NOT EXISTS direct_competitors_count INTEGER DEFAULT 0",
        "ALTER TABLE context_intelligence ADD COLUMN IF NOT EXISTS seo_competitors_count INTEGER DEFAULT 0",
        "ALTER TABLE context_intelligence ADD COLUMN IF NOT EXISTS emerging_threats_count INTEGER DEFAULT 0",
        "ALTER TABLE context_intelligence ADD COLUMN IF NOT EXISTS context_confidence FLOAT",
    ]

    # Enum migrations - PostgreSQL enum ADD VALUE can't be in transaction
    enum_migrations = [
        "ALTER TYPE primarygoaltype ADD VALUE IF NOT EXISTS 'balanced'",
        # BusinessModelType values
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'b2b_saas'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'b2b_service'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'b2c_ecommerce'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'b2c_subscription'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'marketplace'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'publisher'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'local_service'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'nonprofit'",
        "ALTER TYPE businessmodeltype ADD VALUE IF NOT EXISTS 'unknown'",
    ]

    results = []
    try:
        # Run column migrations in transaction
        with get_db_context() as db:
            for migration in migrations:
                try:
                    db.execute(text(migration))
                    results.append({"sql": migration, "status": "success"})
                except Exception as e:
                    results.append({"sql": migration, "status": "error", "error": str(e)})
            db.commit()

        # Run enum migrations with autocommit (required for ADD VALUE)
        from sqlalchemy import create_engine
        import os
        db_url = os.getenv("DATABASE_URL", "")
        if db_url:
            engine = create_engine(db_url, isolation_level="AUTOCOMMIT")
            with engine.connect() as conn:
                for migration in enum_migrations:
                    try:
                        conn.execute(text(migration))
                        results.append({"sql": migration, "status": "success"})
                    except Exception as e:
                        # "already exists" is not an error
                        if "already exists" in str(e).lower():
                            results.append({"sql": migration, "status": "already_exists"})
                        else:
                            results.append({"sql": migration, "status": "error", "error": str(e)})

        return {
            "status": "ok",
            "message": "Migrations completed",
            "results": results,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def trigger_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger an SEO analysis.
    
    This endpoint:
    1. Validates the request
    2. Creates a job
    3. Starts background processing
    4. Returns immediately with job ID
    """
    
    # Normalize domain
    domain = request.domain.lower().strip()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.replace("www.", "").rstrip("/")

    # Resolve market (handles legacy field mapping)
    resolved_market = request.get_resolved_market()

    # Generate job ID
    job_id = str(uuid.uuid4())[:8]

    # Create job status
    jobs[job_id] = JobStatus(
        job_id=job_id,
        domain=domain,
        status="pending",
    )

    logger.info(
        f"Analysis requested: {domain} -> {request.email} (job: {job_id}), "
        f"goal={request.primary_goal}, market={resolved_market}"
    )

    # Add background task
    background_tasks.add_task(
        run_analysis,
        job_id=job_id,
        domain=domain,
        email=request.email,
        company_name=request.company_name or domain.split(".")[0],
        primary_market=resolved_market,
        primary_goal=request.primary_goal,
        primary_language=request.primary_language,
        secondary_markets=request.secondary_markets,
        known_competitors=request.known_competitors,
        skip_ai_analysis=request.skip_ai_analysis,
        skip_context_intelligence=request.skip_context_intelligence,
        # Legacy support (for language only now)
        market=None,  # Already resolved above
        language=request.language,
    )
    
    return AnalysisResponse(
        job_id=job_id,
        domain=domain,
        email=request.email,
        status="pending",
        message=f"Analysis started. You'll receive results at {request.email}",
    )


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of an analysis job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


# ============================================================================
# BACKGROUND PROCESSING
# ============================================================================

async def run_analysis(
    job_id: str,
    domain: str,
    email: str,
    company_name: str,
    primary_market: str,
    primary_goal: str,
    primary_language: Optional[str],
    secondary_markets: Optional[List[str]],
    known_competitors: Optional[List[str]],
    skip_ai_analysis: bool,
    skip_context_intelligence: bool,
    # Legacy support
    market: Optional[str] = None,
    language: Optional[str] = None,
):
    """
    Run the full analysis pipeline in background.

    Steps:
    1. Update job status to running
    2. Run Context Intelligence (understand the business)
    3. Collect data from DataForSEO (focused by context)
    4. Store data in database and validate quality
    5. Quality gate check - skip AI if data is poor
    6. Analyze with Claude (4 loops, enhanced with context)
    7. Generate PDF report
    8. Send email via Resend
    9. Update job status to completed
    """

    # Update status
    jobs[job_id].status = "running"
    jobs[job_id].started_at = datetime.now()

    logger.info(f"[{job_id}] Starting analysis for {domain}")

    # Convert primary_goal string to PrimaryGoal enum
    goal_mapping = {
        "traffic": PrimaryGoal.TRAFFIC,
        "leads": PrimaryGoal.LEADS,
        "authority": PrimaryGoal.AUTHORITY,
        "balanced": PrimaryGoal.BALANCED,
    }
    goal = goal_mapping.get(primary_goal, PrimaryGoal.BALANCED)

    # Handle legacy market/language parameters
    if market and not primary_language:
        # Legacy: market was full name like "Sweden"
        legacy_market_map = {
            "Sweden": ("se", "sv"),
            "United States": ("us", "en"),
            "Germany": ("de", "de"),
            "United Kingdom": ("uk", "en"),
            "Norway": ("no", "no"),
            "Denmark": ("dk", "da"),
            "Finland": ("fi", "fi"),
        }
        if market in legacy_market_map:
            primary_market, primary_language = legacy_market_map[market]

    context_result: Optional[ContextIntelligenceResult] = None

    try:
        # Get credentials from environment
        dataforseo_login = os.getenv("DATAFORSEO_LOGIN")
        dataforseo_password = os.getenv("DATAFORSEO_PASSWORD")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if not dataforseo_login or not dataforseo_password:
            raise ValueError("Missing DataForSEO credentials")

        # Create Claude client for Context Intelligence (if available)
        claude_client = None
        if anthropic_key and not skip_context_intelligence:
            from src.analyzer.client import ClaudeClient
            claude_client = ClaudeClient(api_key=anthropic_key)

        # ================================================================
        # Create DataForSEO client EARLY - needed for Context Intelligence
        # ================================================================
        async with DataForSEOClient(
            login=dataforseo_login,
            password=dataforseo_password
        ) as client:

            # ================================================================
            # PHASE 0: CONTEXT INTELLIGENCE
            # Now has access to DataForSEO client for competitor discovery!
            # ================================================================
            if not skip_context_intelligence:
                logger.info(f"[{job_id}] Phase 0: Running Context Intelligence...")
                try:
                    context_result = await gather_context_intelligence(
                        domain=domain,
                        primary_market=primary_market,
                        primary_goal=goal,
                        primary_language=primary_language,
                        secondary_markets=secondary_markets,
                        known_competitors=known_competitors,
                        claude_client=claude_client,
                        dataforseo_client=client,  # KEY FIX: Pass client for SERP discovery!
                    )

                    logger.info(
                        f"[{job_id}] Context Intelligence complete in {context_result.execution_time_seconds:.1f}s. "
                        f"Confidence: {context_result.overall_confidence:.2f}"
                    )

                    # Log key discoveries
                    if context_result.competitor_validation:
                        cv = context_result.competitor_validation
                        logger.info(
                            f"[{job_id}] Competitors: {cv.total_direct_competitors} direct, "
                            f"{len(cv.discovered)} discovered, {len(cv.reclassified)} reclassified"
                        )

                    if context_result.market_validation:
                        mv = context_result.market_validation
                        if mv.discovered_opportunities:
                            logger.info(
                                f"[{job_id}] Market opportunities: {len(mv.discovered_opportunities)} discovered"
                            )

                    if context_result.business_context and context_result.business_context.goal_validation:
                        gv = context_result.business_context.goal_validation
                        if not gv.goal_fits_business:
                            logger.warning(
                                f"[{job_id}] Goal mismatch: '{goal.value}' may not fit business. "
                                f"Suggested: {gv.suggested_goal.value if gv.suggested_goal else 'N/A'}"
                            )

                    # Store context intelligence in database
                    try:
                        db_run_id = create_analysis_run(
                            domain=domain,
                            config={
                                "market": primary_market,
                                "language": primary_language,
                                "goal": primary_goal,
                                "email": email,
                                "company_name": company_name,
                            },
                            client_email=email,
                        )

                        # Get domain_id from run
                        from src.database.session import get_db_context
                        from src.database.models import AnalysisRun
                        with get_db_context() as db:
                            run = db.query(AnalysisRun).get(db_run_id)
                            domain_id = run.domain_id

                        # Store context intelligence
                        context_id = store_context_intelligence(
                            run_id=db_run_id,
                            domain_id=domain_id,
                            context_result=context_result,
                        )
                        logger.info(f"[{job_id}] Context Intelligence stored (context_id={context_id})")

                    except Exception as db_error:
                        logger.warning(f"[{job_id}] Failed to store context intelligence: {db_error}")
                        # Continue without DB storage

                except Exception as e:
                    logger.error(f"[{job_id}] Context Intelligence failed: {e}")
                    # Continue without context - fallback to original behavior
                    context_result = None
            else:
                logger.info(f"[{job_id}] Context Intelligence skipped (disabled)")

            # ================================================================
            # PHASE 1-4: DATA COLLECTION
            # ================================================================
            orchestrator = DataCollectionOrchestrator(client)

            # Determine collection config based on context
            if context_result and context_result.collection_config:
                # Use intelligent collection config
                config = context_result.collection_config
                collection_market = config.primary_market
                collection_language = config.primary_language

                # Map market code to full name for DataForSEO
                market_names = {
                    "se": "Sweden", "us": "United States", "de": "Germany",
                    "uk": "United Kingdom", "no": "Norway", "dk": "Denmark",
                    "fi": "Finland", "fr": "France", "nl": "Netherlands",
                    "es": "Spain", "it": "Italy", "au": "Australia", "ca": "Canada",
                }
                language_names = {
                    "sv": "Swedish", "en": "English", "de": "German",
                    "no": "Norwegian", "da": "Danish", "fi": "Finnish",
                    "fr": "French", "nl": "Dutch", "es": "Spanish", "it": "Italian",
                }

                market_full = market_names.get(collection_market, "United States")
                language_full = language_names.get(collection_language, "English")
            else:
                # Fallback to provided values - use primary_market if legacy market not set
                market_names_fallback = {
                    "se": "Sweden", "us": "United States", "de": "Germany",
                    "uk": "United Kingdom", "no": "Norway", "dk": "Denmark",
                    "fi": "Finland", "fr": "France", "nl": "Netherlands",
                    "es": "Spain", "it": "Italy", "au": "Australia", "ca": "Canada",
                }
                language_names_fallback = {
                    "sv": "Swedish", "en": "English", "de": "German",
                    "no": "Norwegian", "da": "Danish", "fi": "Finnish",
                    "fr": "French", "nl": "Dutch", "es": "Spanish", "it": "Italian",
                }
                market_full = market or market_names_fallback.get(primary_market, "United States")
                language_full = language or language_names_fallback.get(primary_language or "en", "English")

            # Run data collection (Phase 1-4: 60 endpoints)
            logger.info(f"[{job_id}] Phase 1-4: Collecting data from DataForSEO...")
            result = await orchestrator.collect(CollectionConfig(
                domain=domain,
                market=market_full,
                language=language_full,
                brand_name=company_name,
                skip_ai_analysis=skip_ai_analysis,
            ))

            if not result.success:
                raise Exception(f"Collection failed: {', '.join(result.errors)}")

            # Log any warnings
            for warning in result.warnings:
                logger.warning(f"[{job_id}] {warning}")

            # ================================================================
            # DATA QUALITY CHECK (NEW - validates before AI)
            # ================================================================
            quality_summary = get_quality_summary(result)
            logger.info(
                f"[{job_id}] Data quality: {quality_summary['quality_level']} "
                f"({quality_summary['quality_score']:.1f}%), "
                f"critical={quality_summary['critical_issues']}, "
                f"warnings={quality_summary['warnings']}"
            )

            if quality_summary['recommendations']:
                for rec in quality_summary['recommendations']:
                    logger.info(f"[{job_id}] Quality recommendation: {rec}")

            # Compile data for analysis
            analysis_data = compile_analysis_data(result)

            logger.info(
                f"[{job_id}] Data collection complete: {result.duration_seconds:.1f}s, "
                f"keywords={len(result.ranked_keywords)}, "
                f"competitors={len(result.competitors)}"
            )

            # ================================================================
            # QUALITY GATE - Skip AI if data is insufficient
            # ================================================================
            should_run_ai = quality_summary['is_sufficient'] and not skip_ai_analysis
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")

            if not should_run_ai:
                logger.warning(
                    f"[{job_id}] QUALITY GATE BLOCKED AI: "
                    f"Data quality insufficient ({quality_summary['quality_score']:.1f}%). "
                    f"AI analysis would produce unreliable results."
                )

            # ================================================================
            # ANALYSIS ENGINE (Claude AI - 4 Loops)
            # ================================================================
            analysis_result = None

            if anthropic_key and should_run_ai:
                logger.info(f"[{job_id}] Starting Claude AI analysis (4 loops)...")
                try:
                    engine = AnalysisEngine(api_key=anthropic_key)

                    # Add context intelligence to analysis data if available
                    if context_result:
                        analysis_data["context_intelligence"] = context_result.to_analysis_context()
                        logger.info(f"[{job_id}] Context Intelligence injected into analysis")

                    analysis_result = await engine.analyze(
                        analysis_data,
                        skip_enrichment=False,  # Include Loop 3
                    )

                    logger.info(
                        f"[{job_id}] Analysis complete: "
                        f"quality={analysis_result.quality_score}/10, "
                        f"cost=${analysis_result.total_cost:.2f}"
                    )

                    if not analysis_result.passed_quality_gate:
                        logger.warning(
                            f"[{job_id}] AI quality gate not passed "
                            f"(score: {analysis_result.quality_score}/10)"
                        )

                except Exception as e:
                    logger.error(f"[{job_id}] AI analysis failed: {e}")
                    # Continue without AI analysis
                    analysis_result = None
            elif not anthropic_key:
                logger.info(f"[{job_id}] AI analysis skipped (no API key)")
            else:
                logger.info(f"[{job_id}] AI analysis skipped (quality gate)")

            # ================================================================
            # REPORT GENERATION - ONE REPORT
            # ================================================================
            logger.info(f"[{job_id}] Generating PDF report...")
            report = None
            try:
                generator = ReportGenerator()

                # Generate THE report (40-60 page strategy guide)
                report = await generator.generate(
                    analysis_result,
                    analysis_data,
                )
                logger.info(
                    f"[{job_id}] Report generated: "
                    f"{len(report.pdf_bytes)} bytes, "
                    f"confidence={report.confidence_level} ({report.confidence_score:.0f}%)"
                )

                if report.missing_data:
                    logger.warning(
                        f"[{job_id}] Report missing data: {report.missing_data[:5]}"
                    )

            except Exception as e:
                logger.error(f"[{job_id}] PDF generation failed: {e}")
                report = None

            # ================================================================
            # EMAIL DELIVERY
            # ================================================================
            if report and os.getenv("RESEND_API_KEY"):
                logger.info(f"[{job_id}] Sending report via email...")
                try:
                    delivery = EmailDelivery()
                    email_result = await delivery.send_report(
                        to_email=email,
                        domain=domain,
                        company_name=company_name,
                        pdf_bytes=report.pdf_bytes,
                        pdf_filename=report.filename,
                    )

                    if email_result.success:
                        logger.info(
                            f"[{job_id}] Email sent successfully: "
                            f"{email_result.message_id}"
                        )
                    else:
                        logger.error(
                            f"[{job_id}] Email delivery failed: "
                            f"{email_result.error}"
                        )

                except Exception as e:
                    logger.error(f"[{job_id}] Email delivery error: {e}")
            else:
                logger.info(f"[{job_id}] Email delivery skipped (no report or no API key)")

        # Update status
        jobs[job_id].status = "completed"
        jobs[job_id].completed_at = datetime.now()

        logger.info(f"[{job_id}] Job completed successfully")

    except Exception as e:
        logger.exception(f"[{job_id}] Analysis failed: {e}")
        jobs[job_id].status = "failed"
        jobs[job_id].completed_at = datetime.now()
        jobs[job_id].error = str(e)


# ============================================================================
# TALLY FORM WEBHOOK
# ============================================================================

class TallyFormData(BaseModel):
    """Tally form webhook payload."""
    eventId: str
    eventType: str
    createdAt: str
    data: dict


@app.post("/api/webhook/tally")
async def tally_webhook(
    payload: TallyFormData,
    background_tasks: BackgroundTasks
):
    """
    Handle webhook from Tally form.
    
    Expected form fields:
    - domain: The website URL to analyze
    - email: Email to send results
    - company_name: Company name (optional)
    """
    
    if payload.eventType != "FORM_RESPONSE":
        return {"status": "ignored", "reason": "Not a form response"}
    
    # Extract form fields
    fields = payload.data.get("fields", [])
    
    domain = None
    email = None
    company_name = None
    
    for field in fields:
        label = field.get("label", "").lower()
        value = field.get("value", "")
        
        if "domain" in label or "website" in label or "url" in label:
            domain = value
        elif "email" in label:
            email = value
        elif "company" in label or "business" in label:
            company_name = value
    
    if not domain or not email:
        logger.warning(f"Tally webhook missing required fields: domain={domain}, email={email}")
        return {"status": "error", "reason": "Missing domain or email"}
    
    # Create analysis request
    request = AnalysisRequest(
        domain=domain,
        email=email,
        company_name=company_name,
    )
    
    # Trigger analysis
    response = await trigger_analysis(request, background_tasks)
    
    return {
        "status": "accepted",
        "job_id": response.job_id,
        "domain": response.domain,
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.analyze:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

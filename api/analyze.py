"""
API Endpoint for SEO Analysis

FastAPI webhook handler that:
1. Receives analysis requests (from Tally form or direct API call)
2. Triggers data collection in background
3. Validates data quality before AI analysis
4. Sends results via email when complete
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr

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
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
    """Request to trigger an SEO analysis."""
    domain: str
    email: EmailStr
    company_name: Optional[str] = None
    market: str = "Sweden"
    language: str = "Swedish"  # Must be full language name, not code (e.g., "Swedish" not "sv")

    # Options
    skip_ai_analysis: bool = False
    priority: str = "normal"  # normal, high


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
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Create job status
    jobs[job_id] = JobStatus(
        job_id=job_id,
        domain=domain,
        status="pending",
    )
    
    logger.info(f"Analysis requested: {domain} -> {request.email} (job: {job_id})")
    
    # Add background task
    background_tasks.add_task(
        run_analysis,
        job_id=job_id,
        domain=domain,
        email=request.email,
        company_name=request.company_name or domain.split(".")[0],
        market=request.market,
        language=request.language,
        skip_ai_analysis=request.skip_ai_analysis,
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
    market: str,
    language: str,
    skip_ai_analysis: bool,
):
    """
    Run the full analysis pipeline in background.

    Steps:
    1. Update job status to running
    2. Collect data from DataForSEO (60 endpoints)
    3. Store data in database and validate quality
    4. Quality gate check - skip AI if data is poor
    5. Analyze with Claude (4 analysis loops)
    6. Generate PDF reports (external + internal)
    7. Send email via Resend
    8. Update job status to completed
    """

    # Update status
    jobs[job_id].status = "running"
    jobs[job_id].started_at = datetime.now()

    logger.info(f"[{job_id}] Starting analysis for {domain}")

    try:
        # Get credentials from environment
        dataforseo_login = os.getenv("DATAFORSEO_LOGIN")
        dataforseo_password = os.getenv("DATAFORSEO_PASSWORD")

        if not dataforseo_login or not dataforseo_password:
            raise ValueError("Missing DataForSEO credentials")

        # Create client and orchestrator
        async with DataForSEOClient(
            login=dataforseo_login,
            password=dataforseo_password
        ) as client:

            orchestrator = DataCollectionOrchestrator(client)

            # Run data collection (Phase 1-4: 60 endpoints)
            logger.info(f"[{job_id}] Phase 1-4: Collecting data from DataForSEO...")
            result = await orchestrator.collect(CollectionConfig(
                domain=domain,
                market=market,
                language=language,
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

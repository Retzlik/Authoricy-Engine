"""
API Endpoint for SEO Analysis

FastAPI webhook handler that:
1. Receives analysis requests (from Tally form or direct API call)
2. Triggers data collection in background
3. Sends results via email when complete
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
    version="0.1.0",
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request to trigger an SEO analysis."""
    domain: str
    email: EmailStr
    company_name: Optional[str] = None
    market: str = "Sweden"
    language: str = "sv"
    
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
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "jobs_in_queue": len([j for j in jobs.values() if j.status == "running"]),
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
    3. Analyze with Claude (4 analysis loops)
    4. Generate PDF reports (external + internal)
    5. Send email via Resend
    6. Update job status to completed
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

            # Compile data for analysis
            analysis_data = compile_analysis_data(result)

            logger.info(
                f"[{job_id}] Data collection complete: {result.duration_seconds:.1f}s, "
                f"keywords={len(result.ranked_keywords)}, "
                f"competitors={len(result.competitors)}"
            )

            # ================================================================
            # ANALYSIS ENGINE (Claude AI - 4 Loops)
            # ================================================================
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")

            if anthropic_key and not skip_ai_analysis:
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
                            f"[{job_id}] Quality gate not passed "
                            f"(score: {analysis_result.quality_score}/10)"
                        )

                except Exception as e:
                    logger.error(f"[{job_id}] AI analysis failed: {e}")
                    # Continue without AI analysis
                    analysis_result = None
            else:
                logger.info(f"[{job_id}] AI analysis skipped")
                analysis_result = None

            # ================================================================
            # REPORT GENERATION
            # ================================================================
            logger.info(f"[{job_id}] Generating PDF reports...")
            try:
                generator = ReportGenerator()

                # External Report (Lead Magnet): 10-15 pages
                external_report = await generator.generate_external(
                    analysis_result,
                    analysis_data,
                )
                logger.info(
                    f"[{job_id}] External report generated: "
                    f"{len(external_report.pdf_bytes)} bytes"
                )

                # Internal Report (Strategy Guide): 40-60 pages
                internal_report = await generator.generate_internal(
                    analysis_result,
                    analysis_data,
                )
                logger.info(
                    f"[{job_id}] Internal report generated: "
                    f"{len(internal_report.pdf_bytes)} bytes"
                )

            except Exception as e:
                logger.error(f"[{job_id}] PDF generation failed: {e}")
                external_report = None
                internal_report = None

            # ================================================================
            # EMAIL DELIVERY
            # ================================================================
            if external_report and os.getenv("RESEND_API_KEY"):
                logger.info(f"[{job_id}] Sending report via email...")
                try:
                    delivery = EmailDelivery()
                    email_result = await delivery.send_report(
                        to_email=email,
                        domain=domain,
                        company_name=company_name,
                        pdf_bytes=external_report.pdf_bytes,
                        pdf_filename=external_report.filename,
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

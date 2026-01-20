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
    compile_analysis_data,
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
    2. Collect data from DataForSEO
    3. Analyze with Claude
    4. Generate PDF report
    5. Send email
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
            
            # Run collection
            result = await orchestrator.collect(CollectionConfig(
                domain=domain,
                market=market,
                language=language,
                brand_name=company_name,
                skip_ai_analysis=skip_ai_analysis,
            ))
            
            if not result.success:
                raise Exception(f"Collection failed: {result.errors}")
            
            # Compile data for analysis
            analysis_data = compile_analysis_data(result)
            
            logger.info(f"[{job_id}] Data collection complete: {result.duration_seconds:.1f}s")
            
            # TODO: Send to Claude for analysis
            # TODO: Generate PDF
            # TODO: Send email
            
            # For now, just log completion
            logger.info(f"[{job_id}] Analysis complete (Claude/PDF/Email steps pending)")
        
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

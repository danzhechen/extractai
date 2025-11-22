"""
FastAPI HTTP service for PDF table extraction.

This module provides a REST API for PDF table extraction with the following endpoints:
- POST /extract: Submit extraction job
- GET /status/{job_id}: Check job status
- GET /results/{job_id}: Retrieve extraction results
- GET /health: Health check

The service uses background tasks for async processing and stores job state in memory
(for production, consider using Redis or a database for job state).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError(
        "FastAPI is not installed. Install with: pip install pdf-reader[http] "
        "or pip install fastapi uvicorn python-multipart"
    )

from ...pipeline import PipelineConfig
from ..core import AdapterConfig, InputSource, OutputSink, run_extraction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PDF Table Extraction API",
    description="REST API for extracting tables from PDF documents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage (in-memory; use Redis/DB for production)
jobs: Dict[str, Dict[str, Any]] = {}
job_lock = asyncio.Lock()


# Pydantic models for request/response
class JobStatus(str, Enum):
    """Job status enum."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractionRequest(BaseModel):
    """Request model for extraction from URL or pre-uploaded file."""
    url: Optional[str] = Field(None, description="URL to PDF file")
    file_id: Optional[str] = Field(None, description="ID of pre-uploaded file")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Pipeline configuration overrides"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional job metadata"
    )


class ExtractionResponse(BaseModel):
    """Response model for extraction submission."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Human-readable message")


class JobStatusResponse(BaseModel):
    """Response model for job status query."""
    job_id: str
    status: JobStatus
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResultResponse(BaseModel):
    """Response model for extraction results."""
    job_id: str
    status: JobStatus
    tables_extracted: Optional[int] = None
    pages_processed: Optional[int] = None
    elapsed_seconds: Optional[float] = None
    output_dir: Optional[str] = None
    tables: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    version: str
    timestamp: str
    jobs_queued: int
    jobs_processing: int
    jobs_completed: int
    jobs_failed: int


# Helper functions
def create_job_id() -> str:
    """Generate unique job ID."""
    return str(uuid.uuid4())


async def store_job(job_id: str, job_data: Dict[str, Any]) -> None:
    """Store job data (thread-safe)."""
    async with job_lock:
        jobs[job_id] = job_data


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve job data."""
    async with job_lock:
        return jobs.get(job_id)


async def update_job(job_id: str, updates: Dict[str, Any]) -> None:
    """Update job data (thread-safe)."""
    async with job_lock:
        if job_id in jobs:
            jobs[job_id].update(updates)


def run_extraction_job(job_id: str, pdf_path: Path, config_dict: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    """Run extraction job in background."""
    try:
        logger.info(f"Starting extraction job {job_id}")
        
        # Update job status
        asyncio.run(update_job(job_id, {
            "status": JobStatus.PROCESSING,
            "started_at": datetime.now().isoformat(),
        }))
        
        # Create pipeline config
        pipeline_config = PipelineConfig(**config_dict)
        
        # Create output directory
        output_dir = Path(tempfile.gettempdir()) / "pdf_extractions" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create adapter config
        adapter_config = AdapterConfig(
            input_source=InputSource(type="file", location=str(pdf_path)),
            output_sink=OutputSink(type="filesystem", location=str(output_dir.parent)),
            pipeline_config=pipeline_config,
            run_id=job_id,
            metadata=metadata,
        )
        
        # Run extraction
        result = run_extraction(adapter_config)
        
        # Update job with results
        asyncio.run(update_job(job_id, {
            "status": JobStatus.COMPLETED,
            "completed_at": datetime.now().isoformat(),
            "progress": 1.0,
            "tables_extracted": result.stats.tables_extracted,
            "pages_processed": result.stats.pages_processed,
            "elapsed_seconds": result.stats.elapsed_seconds,
            "output_dir": str(output_dir / job_id),
        }))
        
        logger.info(f"Completed extraction job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in extraction job {job_id}: {e}", exc_info=True)
        
        asyncio.run(update_job(job_id, {
            "status": JobStatus.FAILED,
            "completed_at": datetime.now().isoformat(),
            "progress": 0.0,
            "error": str(e),
        }))


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "service": "PDF Table Extraction API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Count jobs by status
    queued = sum(1 for j in jobs.values() if j["status"] == JobStatus.QUEUED)
    processing = sum(1 for j in jobs.values() if j["status"] == JobStatus.PROCESSING)
    completed = sum(1 for j in jobs.values() if j["status"] == JobStatus.COMPLETED)
    failed = sum(1 for j in jobs.values() if j["status"] == JobStatus.FAILED)
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        jobs_queued=queued,
        jobs_processing=processing,
        jobs_completed=completed,
        jobs_failed=failed,
    )


@app.post("/extract", response_model=ExtractionResponse, status_code=status.HTTP_202_ACCEPTED)
async def extract_tables(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    request: ExtractionRequest = None,
):
    """Submit extraction job.
    
    Supports two modes:
    1. File upload: Send PDF file directly as multipart/form-data
    2. URL: Provide URL to PDF file in request body (future)
    
    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded PDF file
        request: Extraction request with config
        
    Returns:
        ExtractionResponse with job_id and status
        
    Example:
        # File upload
        curl -X POST http://localhost:8000/extract \\
            -F "file=@document.pdf" \\
            -F 'config={"dpi": 300}'
    """
    # Validate input
    if file is None and (request is None or request.url is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either file upload or URL",
        )
    
    # Create job ID
    job_id = create_job_id()
    
    # Handle file upload
    if file:
        # Validate file type
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a PDF",
            )
        
        # Save uploaded file to temp directory
        temp_dir = Path(tempfile.gettempdir()) / "pdf_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        pdf_path = temp_dir / f"{job_id}.pdf"
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Saved uploaded file to {pdf_path}")
        
        # Get config and metadata
        config_dict = request.config if request else {}
        metadata = request.metadata if request else {}
        metadata["filename"] = file.filename
        
    else:
        # URL mode (not implemented yet)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="URL extraction not yet implemented",
        )
    
    # Create job record
    job_data = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "progress": 0.0,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "metadata": metadata,
        "error": None,
    }
    
    await store_job(job_id, job_data)
    
    # Schedule background extraction
    background_tasks.add_task(
        run_extraction_job,
        job_id=job_id,
        pdf_path=pdf_path,
        config_dict=config_dict,
        metadata=metadata,
    )
    
    return ExtractionResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message=f"Extraction job {job_id} queued successfully",
    )


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobStatusResponse with current status and progress
        
    Example:
        curl http://localhost:8000/status/abc123
    """
    job_data = await get_job(job_id)
    
    if job_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    return JobStatusResponse(**job_data)


@app.get("/results/{job_id}", response_model=ExtractionResultResponse)
async def get_extraction_results(job_id: str):
    """Get extraction results.
    
    Args:
        job_id: Job identifier
        
    Returns:
        ExtractionResultResponse with tables and metadata
        
    Example:
        curl http://localhost:8000/results/abc123
    """
    job_data = await get_job(job_id)
    
    if job_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    # If job not completed, return partial results
    if job_data["status"] not in (JobStatus.COMPLETED, JobStatus.FAILED):
        return ExtractionResultResponse(
            job_id=job_id,
            status=job_data["status"],
            error="Job not yet completed" if job_data["status"] != JobStatus.FAILED else job_data.get("error"),
        )
    
    # If job failed, return error
    if job_data["status"] == JobStatus.FAILED:
        return ExtractionResultResponse(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=job_data.get("error"),
        )
    
    # Read tables from output directory
    output_dir = Path(job_data.get("output_dir", ""))
    tables = []
    
    if output_dir.exists():
        tables_dir = output_dir / "tables"
        if tables_dir.exists():
            for table_file in sorted(tables_dir.glob("table_*.csv")):
                # Read CSV and convert to dict
                import csv
                with open(table_file, "r") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    tables.append({
                        "table_id": table_file.stem,
                        "rows": rows,
                    })
    
    return ExtractionResultResponse(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        tables_extracted=job_data.get("tables_extracted"),
        pages_processed=job_data.get("pages_processed"),
        elapsed_seconds=job_data.get("elapsed_seconds"),
        output_dir=str(output_dir),
        tables=tables,
    )


@app.get("/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    """Download output file.
    
    Args:
        job_id: Job identifier
        filename: File to download (e.g., "tables/table_0.csv", "manifest.json")
        
    Returns:
        FileResponse with requested file
        
    Example:
        curl http://localhost:8000/download/abc123/tables/table_0.csv -O
    """
    job_data = await get_job(job_id)
    
    if job_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    output_dir = Path(job_data.get("output_dir", ""))
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {filename} not found for job {job_id}",
        )
    
    # Security check: prevent path traversal
    try:
        file_path.resolve().relative_to(output_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


# Main entry point for development
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "pdf_reader.adapters.http.service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )



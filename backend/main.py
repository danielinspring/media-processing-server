from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from celery.result import AsyncResult
from celery_app import celery_app

app = FastAPI(title="Media Processor API", version="1.0.0")

# Pydantic Models
class MediaJobRequest(BaseModel):
    type: str  # e.g., "video_merge", "video_convert", "image_resize"
    sources: List[HttpUrl]
    options: Optional[Dict[str, Any]] = {}
    webhook_url: Optional[HttpUrl] = None

class JobResponse(BaseModel):
    job_id: str
    status: str

@app.post("/api/v1/jobs/process-media", response_model=JobResponse, status_code=202)
async def create_media_job(job: MediaJobRequest):
    """
    Enqueue a media processing job.
    """
    # Convert HttpUrl to str for JSON serialization
    sources_str = [str(url) for url in job.sources]
    webhook_str = str(job.webhook_url) if job.webhook_url else None

    # Send task to Celery
    # We use send_task by name to avoid importing the task function directly if we want loose coupling,
    # but importing it is also fine. Here we use the string name defined in tasks.py
    task = celery_app.send_task(
        "tasks.process_media",
        args=[job.type, sources_str, job.options, webhook_str]
    )

    return JobResponse(job_id=task.id, status="queued")

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Check the status of a job manually (polling).
    """
    task_result = AsyncResult(job_id, app=celery_app)
    result = {
        "job_id": job_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }
    return result

@app.get("/")
async def root():
    return {"message": "Media Processor API is running. Visit /docs for Swagger UI."}

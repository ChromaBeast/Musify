"""Musify Backend API - Spotify playlist to ZIP downloader."""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.spotdl_service import SpotDLService, DownloadProgress, DownloadResult
from services.zip_service import ZipService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Auto-cleanup interval (30 minutes = 1800 seconds)
CLEANUP_AFTER_SECONDS = 1800

# Services
spotdl_service = SpotDLService()
zip_service = ZipService()

# In-memory job storage with timestamps
jobs: dict[str, dict] = {}


async def cleanup_old_jobs():
    """Background task to clean up jobs older than 30 minutes."""
    while True:
        await asyncio.sleep(60)  # Check every minute
        current_time = time.time()
        jobs_to_delete = []
        
        for job_id, job in jobs.items():
            if current_time - job.get("created_at", current_time) > CLEANUP_AFTER_SECONDS:
                jobs_to_delete.append(job_id)
        
        for job_id in jobs_to_delete:
            logger.info(f"Auto-cleaning job {job_id} (older than 30 mins)")
            try:
                spotdl_service.cleanup_job(job_id)
                zip_service.cleanup_zip(job_id)
                del jobs[job_id]
            except Exception as e:
                logger.error(f"Error cleaning job {job_id}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Start cleanup task
    cleanup_task = asyncio.create_task(cleanup_old_jobs())
    logger.info("Started auto-cleanup task (30 min TTL)")
    yield
    # Cancel cleanup task on shutdown
    cleanup_task.cancel()


app = FastAPI(
    title="Musify API",
    description="Convert Spotify playlists to downloadable ZIP files",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    url: str


class DownloadResponse(BaseModel):
    job_id: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: list[dict]
    song_count: int
    download_url: Optional[str] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    return {"status": "ok", "service": "Musify API"}


@app.post("/api/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest):
    if not spotdl_service.validate_spotify_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid Spotify URL")
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "url": request.url,
        "progress": [],
        "song_count": 0,
        "error": None,
        "created_at": time.time()  # Track creation time for cleanup
    }
    
    asyncio.create_task(_process_download(job_id, request.url))
    
    return DownloadResponse(
        job_id=job_id,
        message="Download started. Files auto-delete after 30 minutes."
    )


async def _process_download(job_id: str, url: str):
    jobs[job_id]["status"] = "downloading"
    result: Optional[DownloadResult] = None
    
    async for update in spotdl_service.download_playlist(url, job_id):
        if isinstance(update, DownloadProgress):
            jobs[job_id]["progress"].append({
                "song": update.song_name,
                "status": update.status,
                "message": update.message
            })
        elif isinstance(update, DownloadResult):
            result = update
    
    if result and result.success:
        files = spotdl_service.get_job_files(job_id)
        if files:
            zip_service.create_zip(job_id, files)
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["song_count"] = result.song_count
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "No songs downloaded"
    else:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = result.error if result else "Download failed"


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    download_url = f"/api/download/{job_id}/zip" if job["status"] == "completed" else None
    
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        song_count=job["song_count"],
        download_url=download_url,
        error=job["error"]
    )


@app.get("/api/download/{job_id}/zip")
async def download_zip(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if jobs[job_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Download not complete")
    
    zip_path = zip_service.get_zip_path(job_id)
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP file not found")
    
    return FileResponse(
        path=zip_path,
        filename=zip_path.name,
        media_type="application/zip"
    )


@app.delete("/api/job/{job_id}")
async def cleanup_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    spotdl_service.cleanup_job(job_id)
    zip_service.cleanup_zip(job_id)
    del jobs[job_id]
    
    return {"message": "Job cleaned up"}


@app.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    try:
        last_progress_count = 0
        while True:
            if job_id not in jobs:
                await websocket.send_json({"error": "Job not found"})
                break
            
            job = jobs[job_id]
            current_progress = job["progress"]
            
            if len(current_progress) > last_progress_count:
                for update in current_progress[last_progress_count:]:
                    await websocket.send_json(update)
                last_progress_count = len(current_progress)
            
            if job["status"] in ["completed", "error"]:
                await websocket.send_json({
                    "status": job["status"],
                    "song_count": job["song_count"],
                    "download_url": f"/api/download/{job_id}/zip" if job["status"] == "completed" else None,
                    "error": job["error"]
                })
                break
            
            await asyncio.sleep(0.5)
    
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""SpotDL service for downloading Spotify playlists."""

import asyncio
import logging
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """Represents download progress for a song."""
    song_name: str
    status: str
    progress: int
    message: Optional[str] = None


@dataclass
class DownloadResult:
    """Result of a playlist download."""
    job_id: str
    success: bool
    output_dir: Path
    song_count: int
    error: Optional[str] = None


class SpotDLService:
    """Service for interacting with spotdl CLI."""
    
    DOWNLOADS_DIR = Path("downloads")
    SPOTIFY_URL_PATTERN = re.compile(
        r'^https://open\.spotify\.com/(playlist|album|track)/[a-zA-Z0-9]+(\?.*)?$'
    )
    
    def __init__(self):
        self.DOWNLOADS_DIR.mkdir(exist_ok=True)
        # Get Spotify credentials from environment
        self.client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        self.client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    
    def validate_spotify_url(self, url: str) -> bool:
        return bool(self.SPOTIFY_URL_PATTERN.match(url))
    
    def _clean_url(self, url: str) -> str:
        return url.split('?')[0]
    
    async def download_playlist(
        self, 
        url: str,
        job_id: Optional[str] = None
    ) -> AsyncGenerator[DownloadProgress | DownloadResult, None]:
        """Download a Spotify playlist and yield progress updates."""
        if not self.validate_spotify_url(url):
            yield DownloadResult(
                job_id=job_id or str(uuid.uuid4()),
                success=False, output_dir=Path(""), song_count=0,
                error="Invalid Spotify URL"
            )
            return
        
        job_id = job_id or str(uuid.uuid4())
        output_dir = self.DOWNLOADS_DIR / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        clean_url = self._clean_url(url)
        logger.info(f"Starting download for job {job_id}: {clean_url}")
        
        yield DownloadProgress(song_name="", status="downloading", progress=0, message="Starting...")
        
        # Build command with credentials if available
        cmd = ["spotdl", "download", clean_url, "--output", str(output_dir), "--format", "mp3"]
        
        if self.client_id and self.client_secret:
            cmd.extend(["--client-id", self.client_id, "--client-secret", self.client_secret])
            logger.info("Using custom Spotify credentials")
        else:
            logger.warning("No Spotify credentials set - may hit rate limits!")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            async def read_output(stream, name):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode('utf-8', errors='ignore').strip()
                    if text:
                        logger.info(f"[spotdl {name}] {text}")
            
            await asyncio.gather(
                read_output(process.stdout, "stdout"),
                read_output(process.stderr, "stderr")
            )
            await process.wait()
            
            logger.info(f"spotdl exited with code: {process.returncode}")
            
            mp3_files = list(output_dir.glob("*.mp3"))
            logger.info(f"Found {len(mp3_files)} MP3 files")
            
            for f in mp3_files:
                yield DownloadProgress(song_name=f.stem, status="completed", progress=100, message=f"Downloaded: {f.stem}")
            
            success = len(mp3_files) > 0
            yield DownloadResult(
                job_id=job_id, success=success, output_dir=output_dir, song_count=len(mp3_files),
                error=None if success else "No songs downloaded. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            yield DownloadResult(job_id=job_id, success=False, output_dir=output_dir, song_count=0, error=str(e))
    
    def cleanup_job(self, job_id: str) -> None:
        job_dir = self.DOWNLOADS_DIR / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
    
    def get_job_files(self, job_id: str) -> list[Path]:
        job_dir = self.DOWNLOADS_DIR / job_id
        return list(job_dir.glob("*.mp3")) if job_dir.exists() else []

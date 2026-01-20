"""SpotDL service with multi-provider fallback."""

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

# Audio providers to try in order
AUDIO_PROVIDERS = ["youtube-music", "youtube", "soundcloud", "piped", "bandcamp"]


@dataclass
class DownloadProgress:
    song_name: str
    status: str
    progress: int
    message: Optional[str] = None


@dataclass
class DownloadResult:
    job_id: str
    success: bool
    output_dir: Path
    song_count: int
    error: Optional[str] = None


class SpotDLService:
    DOWNLOADS_DIR = Path("downloads")
    COOKIES_FILE = Path("cookies.txt")
    SPOTIFY_URL_PATTERN = re.compile(
        r'^https://open\.spotify\.com/(playlist|album|track)/[a-zA-Z0-9]+(\?.*)?$'
    )
    
    def __init__(self):
        self.DOWNLOADS_DIR.mkdir(exist_ok=True)
        self.client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        self.client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    
    def validate_spotify_url(self, url: str) -> bool:
        return bool(self.SPOTIFY_URL_PATTERN.match(url))
    
    def _clean_url(self, url: str) -> str:
        return url.split('?')[0]
    
    async def _try_download(self, url: str, output_dir: Path, provider: str) -> int:
        """Try downloading with a specific provider. Returns number of files downloaded."""
        cmd = [
            "spotdl", "download", url,
            "--output", str(output_dir),
            "--format", "mp3",
            "--audio", provider,
        ]
        
        if self.client_id and self.client_secret:
            cmd.extend(["--client-id", self.client_id, "--client-secret", self.client_secret])
        
        if self.COOKIES_FILE.exists():
            cmd.extend(["--cookie-file", str(self.COOKIES_FILE)])
        
        logger.info(f"Trying provider: {provider}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        async def read_output(stream, name):
            while True:
                line = await stream.readline()
                if not line: break
                text = line.decode('utf-8', errors='ignore').strip()
                if text: logger.info(f"[{provider}] {text}")
        
        await asyncio.gather(
            read_output(process.stdout, "stdout"),
            read_output(process.stderr, "stderr")
        )
        await process.wait()
        
        return len(list(output_dir.glob("*.mp3")))
    
    async def download_playlist(self, url: str, job_id: Optional[str] = None):
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
        
        yield DownloadProgress(
            song_name="", status="downloading", progress=0,
            message="Starting download with multi-provider fallback..."
        )
        
        total_files = 0
        tried_providers = []
        
        # Try each provider
        for provider in AUDIO_PROVIDERS:
            try:
                yield DownloadProgress(
                    song_name="", status="downloading", progress=10,
                    message=f"Trying {provider}..."
                )
                
                files_before = len(list(output_dir.glob("*.mp3")))
                await self._try_download(clean_url, output_dir, provider)
                files_after = len(list(output_dir.glob("*.mp3")))
                
                new_files = files_after - files_before
                total_files = files_after
                tried_providers.append(provider)
                
                logger.info(f"Provider {provider}: downloaded {new_files} new files (total: {total_files})")
                
                if total_files > 0:
                    # Got some files, we can stop or continue for more
                    yield DownloadProgress(
                        song_name="", status="downloading", progress=50,
                        message=f"Downloaded {total_files} songs via {provider}"
                    )
                    break  # Stop after first successful provider
                    
            except Exception as e:
                logger.error(f"Provider {provider} failed: {e}")
                continue
        
        # Report final files
        mp3_files = list(output_dir.glob("*.mp3"))
        for f in mp3_files:
            yield DownloadProgress(
                song_name=f.stem, status="completed", progress=100,
                message=f"Downloaded: {f.stem}"
            )
        
        success = len(mp3_files) > 0
        error_msg = None if success else f"All providers failed: {', '.join(tried_providers)}"
        
        yield DownloadResult(
            job_id=job_id,
            success=success,
            output_dir=output_dir,
            song_count=len(mp3_files),
            error=error_msg
        )
    
    def cleanup_job(self, job_id: str):
        job_dir = self.DOWNLOADS_DIR / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
    
    def get_job_files(self, job_id: str):
        job_dir = self.DOWNLOADS_DIR / job_id
        return list(job_dir.glob("*.mp3")) if job_dir.exists() else []

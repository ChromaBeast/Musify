"""ZIP service for creating downloadable archives."""

import zipfile
from pathlib import Path
from typing import Optional


class ZipService:
    """Service for creating ZIP archives from downloaded files."""
    
    ZIPS_DIR = Path("zips")
    
    def __init__(self):
        self.ZIPS_DIR.mkdir(exist_ok=True)
    
    def create_zip(self, job_id: str, files: list[Path], playlist_name: Optional[str] = None) -> Path:
        """
        Create a ZIP archive from a list of files.
        
        Args:
            job_id: Unique job identifier
            files: List of file paths to include
            playlist_name: Optional name for the ZIP file
            
        Returns:
            Path to the created ZIP file
        """
        zip_name = f"{playlist_name or job_id}.zip"
        zip_path = self.ZIPS_DIR / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                if file_path.exists():
                    # Add file with just its name (no directory structure)
                    zf.write(file_path, file_path.name)
        
        return zip_path
    
    def get_zip_path(self, job_id: str) -> Optional[Path]:
        """Get the path to a ZIP file if it exists."""
        # Check for job_id.zip
        zip_path = self.ZIPS_DIR / f"{job_id}.zip"
        if zip_path.exists():
            return zip_path
        
        # Check for any zip with job_id in name
        for zip_file in self.ZIPS_DIR.glob(f"*{job_id}*.zip"):
            return zip_file
        
        return None
    
    def cleanup_zip(self, job_id: str) -> None:
        """Remove ZIP file for a job."""
        zip_path = self.get_zip_path(job_id)
        if zip_path and zip_path.exists():
            zip_path.unlink()

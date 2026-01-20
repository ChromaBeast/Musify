FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install latest yt-dlp FIRST (fixes YouTube download errors)
RUN pip install --no-cache-dir -U yt-dlp

# Install spotdl (will use the yt-dlp we just installed)
RUN pip install --no-cache-dir spotdl>=4.4.0

# Install our API dependencies
RUN pip install --no-cache-dir uvicorn[standard] python-multipart aiofiles

# Copy application code
COPY . .

# Create directories for downloads and zips
RUN mkdir -p downloads zips

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

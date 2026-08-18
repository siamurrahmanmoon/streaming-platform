# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/videos /app/unmatched_videos /app/archive/success /app/archive/failed /app/quarantine

# Set volume mounts for persistent data
VOLUME ["/app/logs", "/app/videos", "/app/unmatched_videos", "/app/archive"]

# Default command
CMD ["python", "main.py"]
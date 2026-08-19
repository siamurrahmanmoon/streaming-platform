আপনার README.md তে Docker সেকশন যোগ করার জন্য নিচের কন্টেন্টটি ব্যবহার করুন। এটি আপনার existing README এর স্টাইল এবং ভাষা (বাংলা/ইংলিশ মিক্স) অনুযায়ী তৈরি করা হয়েছে:

---

##  Docker Deployment

Docker ব্যবহার করে আপনার অ্যাপ্লিকেশনকে সহজেই ডিপ্লয় এবং ম্যানেজ করতে পারবেন। এটি environment setup, dependency management, এবং cross-platform compatibility নিশ্চিত করে।

### 📋 Docker Prerequisites

Docker ব্যবহার করার আগে নিশ্চিত করুন যে আপনার সিস্টেমে নিচের সফটওয়্যারগুলো ইনস্টল করা আছে:

- **Docker Engine** (version 20.10+)
- **Docker Compose** (version 2.0+)

**Installation Links:**
- Windows/Mac: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Linux: [Docker Engine](https://docs.docker.com/engine/install/)

### 🚀 Quick Start with Docker Compose

সবচেয়ে সহজ উপায় হল Docker Compose ব্যবহার করা:

```bash
# 1. প্রজেক্ট ফোল্ডারে যান
cd anime-streaming-platform/backend

# 2. .env ফাইল তৈরি/এডিট করুন (যদি না থাকে)
# (উপরের Environment Variables সেটআপ সেকশন দেখুন)

# 3. Docker Compose দিয়ে অ্যাপ রান করুন
docker-compose up -d

# 4. Logs দেখুন
docker-compose logs -f anime-uploader

# 5. অ্যাপ বন্ধ করতে
docker-compose down
```

### 📦 Manual Docker Build & Run

যদি আপনি Docker Compose ছাড়া manually build এবং run করতে চান:

```bash
# 1. Docker Image Build করুন
docker build -t anime-uploader .

# 2. Container Run করুন
docker run -d \
  --name anime-uploader \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/unmatched_videos:/app/unmatched_videos \
  -v $(pwd)/archive:/app/archive \
  -v $(pwd)/quarantine:/app/quarantine \
  anime-uploader

# 3. Logs দেখুন
docker logs -f anime-uploader

# 4. Container বন্ধ/রিস্টার্ট করতে
docker stop anime-uploader
docker restart anime-uploader
```

### 📁 Volume Mappings Explained

Docker container এর ভেতরের ফাইলগুলো host machine এ persist করতে volumes ব্যবহার করা হয়:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./videos` | `/app/videos` |  নতুন ভিডিও ফাইল রাখুন (scanner এখানে খুঁজবে) |
| `./archive/success` | `/app/archive/success` | ✅ সফলভাবে আপলোড হওয়া ফাইল |
| `./archive/failed` | `/app/archive/failed` | ❌ ফেইল হওয়া আপলোড |
| `./unmatched_videos` | `/app/unmatched_videos` | ⚠️ মেটাডাটা ম্যাচ না হওয়া ফাইল |
| `./quarantine` | `/app/quarantine` | 🔒 সন্দেহজনক/ক্ষতিগ্রস্ত ফাইল |
| `./logs` | `/app/logs` | 📝 অ্যাপ্লিকেশন লগ ফাইল |

**Windows PowerShell Example:**
```powershell
docker run -d `
  --name anime-uploader `
  --restart unless-stopped `
  --env-file .env `
  -v ${PWD}/logs:/app/logs `
  -v ${PWD}/videos:/app/videos `
  -v ${PWD}/unmatched_videos:/app/unmatched_videos `
  -v ${PWD}/archive:/app/archive `
  -v ${PWD}/quarantine:/app/quarantine `
  anime-uploader
```

###  Dockerfile

প্রজেক্টের root এ `Dockerfile` তৈরি করুন:

```dockerfile
# Base Image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/videos \
    /app/archive/success \
    /app/archive/failed \
    /app/unmatched_videos \
    /app/quarantine \
    /app/logs

# Set environment variables (can be overridden by .env file)
ENV VIDEO_FOLDER=/app/videos
ENV UNMATCHED_VIDEOS_FOLDER=/app/unmatched_videos

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the application
CMD ["python", "main.py"]
```

### 📝 docker-compose.yml

প্রজেক্টের root এ `docker-compose.yml` তৈরি করুন:

```yaml
version: "3.8"

services:
  anime-uploader:
    build: .
    container_name: anime-uploader
    restart: unless-stopped  # Auto-restart on crash
    
    # Environment variables from .env file
    env_file:
      - .env
    
    # Volume mappings for data persistence
    volumes:
      - ./logs:/app/logs
      - ./videos:/app/videos
      - ./unmatched_videos:/app/unmatched_videos
      - ./archive:/app/archive
      - ./quarantine:/app/quarantine
    
    # Environment variables (override .env if needed)
    environment:
      - VIDEO_FOLDER=/app/videos
      - UNMATCHED_VIDEOS_FOLDER=/app/unmatched_videos
    
    # Logging configuration
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    # Resource limits (optional)
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
```

### ️ Docker Management Commands

#### Container Management
```bash
#查看所有運行中的容器
docker ps

# 查看所有容器 (包括 stopped)
docker ps -a

# 停止容器
docker stop anime-uploader

# 啟動容器
docker start anime-uploader

# 重啟容器
docker restart anime-uploader

# 刪除容器
docker rm anime-uploader

# 強制刪除運行中的容器
docker rm -f anime-uploader
```

#### Image Management
```bash
# 查看所有 images
docker images

# 刪除 image
docker rmi anime-uploader

# 清理未使用的 images
docker image prune -a
```

#### Logs & Debugging
```bash
# 查看實時 logs
docker logs -f anime-uploader

# 查看最近 100 行 logs
docker logs --tail 100 anime-uploader

# 查看特定時間範圍的 logs
docker logs --since 2024-01-01T00:00:00 anime-uploader

# 進入容器內部 (debugging)
docker exec -it anime-uploader /bin/bash
```

#### Docker Compose Commands
```bash
# 啟動服務 (background)
docker-compose up -d

# 停止服務
docker-compose down

# 重啟服務
docker-compose restart

# 查看服務狀態
docker-compose ps

# 查看 logs
docker-compose logs -f

# 重建並啟動 (code change 後)
docker-compose up -d --build

# 停止並刪除 volumes (⚠️ 會刪除所有數據)
docker-compose down -v
```

### 🔐 Docker Security Best Practices

#### 1. .env File Security
```bash
# .env ফাইল কখনও Git এ commit করবেন না
echo ".env" >> .gitignore

# Production এ environment variables আলাদাভাবে manage করুন
docker run --env-file .env.production anime-uploader
```

#### 2. Non-Root User (Optional but Recommended)
Dockerfile এ non-root user যোগ করুন:

```dockerfile
# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
```

#### 3. Resource Limits
docker-compose.yml এ resource limits সেট করুন:

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '1.0'
    reservations:
      memory: 256M
      cpus: '0.5'
```

### 🐛 Docker Troubleshooting

#### Issue 1: Container Exits Immediately
```bash
# Logs চেক করুন
docker logs anime-uploader

# সাধারণ কারণ:
# - .env ফাইল missing বা incorrect
# - Volume permissions issue
# - Python dependency error
```

**Solution:**
```bash
# Interactive mode এ run করে error দেখুন
docker run -it --rm --env-file .env anime-uploader
```

#### Issue 2: Permission Denied on Volumes
```bash
# Host machine এ folder permissions fix করুন
chmod -R 755 ./videos ./archive ./logs

# অথবা container এ root user ব্যবহার করুন (development only)
docker run -u root --env-file .env anime-uploader
```

#### Issue 3: Network Issues (Supabase/API)
```bash
# Container এর network test করুন
docker exec -it anime-uploader ping supabase.co

# DNS issue হলে custom DNS ব্যবহার করুন
docker run --dns 8.8.8.8 --env-file .env anime-uploader
```

#### Issue 4: High Memory Usage
```bash
# Memory usage চেক করুন
docker stats anime-uploader

# Memory limit কমিয়ে দিন
docker run -m 512m --env-file .env anime-uploader
```

#### Issue 5: Logs Too Large
```bash
# Log rotation configure করুন (docker-compose.yml এ)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

# অথবা existing container এর logs clear করুন
truncate -s 0 $(docker inspect --format='{{.LogPath}}' anime-uploader)
```

###  Auto-Update with Watchtower

Watchtower ব্যবহার করে automatically image update করতে পারেন:

```yaml
# docker-compose.yml এ add করুন
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 3600 # প্রতি 1 ঘণ্টায় চেক করবে
```

###  Monitoring with Docker

#### Resource Monitoring
```bash
# Real-time stats
docker stats

# Specific container stats
docker stats anime-uploader --no-stream
```

#### Health Check
Dockerfile এ health check যোগ করুন:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1
```

Health status চেক করুন:
```bash
docker inspect --format='{{.State.Health.Status}}' anime-uploader
```

###  Production Deployment Checklist

- [ ] `.env` ফাইল properly configure করা হয়েছে
- [ ] Volume directories তৈরি করা হয়েছে (`mkdir -p videos archive logs`)
- [ ] Docker resource limits সেট করা হয়েছে
- [ ] Log rotation configure করা হয়েছে
- [ ] Container restart policy set (`unless-stopped`)
- [ ] `.env` ফাইল `.gitignore` এ যোগ করা হয়েছে
- [ ] Regular backup strategy আছে (volumes backup)
- [ ] Monitoring/alerting setup করা হয়েছে

### 📦 Backup & Restore

#### Backup Volumes
```bash
# Backup script তৈরি করুন
#!/bin/bash
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Archive volumes
tar -czf $BACKUP_DIR/videos_$TIMESTAMP.tar.gz ./videos
tar -czf $BACKUP_DIR/archive_$TIMESTAMP.tar.gz ./archive
tar -czf $BACKUP_DIR/logs_$TIMESTAMP.tar.gz ./logs

echo "Backup completed: $BACKUP_DIR"
```

#### Restore from Backup
```bash
# Restore করুন
tar -xzf backups/videos_20240101_120000.tar.gz -C ./
tar -xzf backups/archive_20240101_120000.tar.gz -C ./
```

---

এই Docker সেকশনটি আপনার README.md এর `🚀 Production Deployment` সেকশনের পরে যোগ করুন। এটি users কে Docker দিয়ে সহজেই অ্যাপ ডিপ্লয় এবং ম্যানেজ করতে সাহায্য করবে! 🐳✨
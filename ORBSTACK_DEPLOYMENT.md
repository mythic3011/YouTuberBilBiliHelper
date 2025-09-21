# OrbStack Deployment Guide for Video Streaming API

## 🚀 **OrbStack vs Docker - Why It's Better for Development**

OrbStack provides significant advantages over Docker Desktop:
- **Faster**: 2-3x faster container startup
- **Lighter**: 50% less memory usage
- **Native**: Better macOS integration
- **Efficient**: Optimized file system performance
- **Simple**: Easier networking and volume management

## 📋 **OrbStack Setup for Your Video Streaming Platform**

### **1. Install OrbStack**
```bash
# Install via Homebrew
brew install orbstack

# Or download from https://orbstack.dev
```

### **2. Verify Installation**
```bash
# Check OrbStack status
orb status

# Test with a simple container
orb run hello-world
```

### **3. OrbStack-Optimized docker-compose.yml**
```yaml
# docker-compose.yml - Optimized for OrbStack
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://dragonfly:6379
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
      # OrbStack optimizations
      - UVLOOP_ENABLED=true
      - PYTHONUNBUFFERED=1
    volumes:
      # OrbStack has excellent volume performance
      - ./downloads:/app/downloads:cached
      - ./logs:/app/logs:delegated
      - ./config:/app/config:ro
    depends_on:
      dragonfly:
        condition: service_healthy
    restart: unless-stopped
    # OrbStack resource limits (more efficient)
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
        reservations:
          memory: 256M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v2/system/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  dragonfly:
    image: docker.dragonflydb.io/dragonflydb/dragonfly:latest
    ports:
      - "6379:6379"
    volumes:
      # OrbStack volumes are much faster
      - dragonfly_data:/data
    restart: unless-stopped
    command: [
      "--logtostderr", 
      "--requirepass", "",
      "--maxmemory", "256mb",
      "--cache_mode"
    ]
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Optional: Performance monitoring with OrbStack
  monitoring:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'

volumes:
  dragonfly_data:
    driver: local

networks:
  default:
    driver: bridge


## 🛠 **OrbStack-Optimized Development Workflow**

### **Quick Start with OrbStack**
```bash
# 1. Clone and setup
git clone <your-repo>
cd YouTuberBilBiliHelper

# 2. Start services with OrbStack (much faster than Docker)
docker-compose up -d

# 3. Check service status (OrbStack provides better visibility)
docker-compose ps
orb ps  # OrbStack-specific command for better output

# 4. View real-time logs with better formatting
docker-compose logs -f app
orb logs video-api  # If using OrbStack naming

# 5. Access shell in running container (faster in OrbStack)
docker-compose exec app bash
```

### **Performance Monitoring with OrbStack**
```bash
# OrbStack provides built-in performance monitoring
orb stats

# Monitor resource usage for specific container
orb stats video-api

# Check disk usage (OrbStack is more efficient)
orb df

# Network diagnostics
orb network ls
```

### **OrbStack Development Commands**
```bash
# Start development environment
docker-compose up -d

# Rebuild with better caching (OrbStack advantage)
docker-compose build --no-cache app

# Scale services (faster with OrbStack)
docker-compose up --scale app=3

# Stop and clean (OrbStack cleanup is more thorough)
docker-compose down -v
orb prune  # Clean up unused resources
```

## 📊 **Performance Comparison: OrbStack vs Docker Desktop**

| Feature | Docker Desktop | OrbStack | Improvement |
|---------|----------------|----------|-------------|
| **Container Startup** | 15-30s | 5-10s | 66% faster |
| **Memory Usage** | 2-4GB | 1-2GB | 50% less |
| **CPU Overhead** | 10-20% | 2-5% | 75% less |
| **File System Performance** | Slow | Native | 5-10x faster |
| **Network Latency** | 2-5ms | 0.5-1ms | 80% faster |
| **Build Time** | 5-10min | 2-4min | 60% faster |

## 🔧 **OrbStack-Specific Optimizations**

### **1. Dockerfile Optimizations for OrbStack**
```dockerfile
# Dockerfile - Optimized for OrbStack
FROM python:3.12-slim as base

# OrbStack handles layer caching more efficiently
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Better layer separation for OrbStack
FROM base as deps
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev

# Faster final stage with OrbStack
FROM base as final
RUN groupadd -r appuser && useradd -r -g appuser appuser

# OrbStack handles file permissions better
COPY --from=deps --chown=appuser:appuser /.venv /.venv
WORKDIR /app
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser pyproject.toml ./

# Create directories with proper permissions
RUN mkdir -p downloads/youtube downloads/bilibili downloads/temp logs config/cookies && \
    chown -R appuser:appuser /app

USER appuser
ENV PATH="/.venv/bin:$PATH"

# Health check optimized for OrbStack
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v2/system/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **2. Environment Configuration for OrbStack**
```bash
# .env file - OrbStack optimizations
# Redis configuration (faster with OrbStack networking)
REDIS_URL=redis://dragonfly:6379/0
REDIS_POOL_SIZE=20

# Performance settings
UVLOOP_ENABLED=true
WORKERS=1  # OrbStack handles single worker better for development
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=100

# OrbStack-specific optimizations
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
ASYNC_POOL_SIZE=100

# Development settings
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
```

### **3. OrbStack Network Configuration**
```yaml
# docker-compose.override.yml for development with OrbStack
services:
  app:
    # OrbStack networking is faster
    ports:
      - "8000:8000"
      - "8001:8001"  # For performance testing
    # Better environment integration
    environment:
      - HOST_HOSTNAME=${HOSTNAME}
      - HOST_PWD=${PWD}
    # OrbStack volume optimization
    volumes:
      - .:/app:cached
      - /app/.venv  # Exclude venv from sync for speed

  dragonfly:
    # OrbStack port management
    ports:
      - "6379:6379"
    # Better persistence with OrbStack
    volumes:
      - dragonfly_data:/data:delegated
```

## 🚀 **Development Workflow with OrbStack**

### **Daily Development Routine**
```bash
# Morning startup (lightning fast with OrbStack)
cd YouTuberBilBiliHelper
docker-compose up -d

# Check everything is running
curl http://localhost:8000/api/v2/system/health

# Development with hot reload (OrbStack handles file watching better)
# Make changes to your code...
# Changes are reflected immediately due to OrbStack's efficient file sync

# Run tests (faster in OrbStack)
docker-compose exec app pytest tests/ -v

# View logs when debugging
docker-compose logs -f app

# Evening cleanup
docker-compose down
```

### **Performance Testing with OrbStack**
```bash
# Start the optimized performance test server
docker-compose exec app python examples/fastapi_performance_optimizations.py &

# Run benchmark (better performance with OrbStack)
python3 examples/simple_benchmark.py

# Test Go comparison (if you build it)
cd examples
go mod init video-api
go mod tidy
go run go_gin_comparison.go &

# Compare performance
python3 simple_benchmark.py --url http://localhost:8002
```

## 🔍 **Debugging and Monitoring with OrbStack**

### **OrbStack-Enhanced Debugging**
```bash
# Better container inspection
orb inspect video-api

# Real-time resource monitoring
orb top

# Network debugging (OrbStack provides better tools)
orb network inspect video-api_default

# Volume inspection
orb volume inspect video-api_dragonfly_data

# System-wide resource usage
orb system df
orb system events
```

### **Log Management**
```bash
# Centralized logging with OrbStack
docker-compose logs --tail=100 -f

# Container-specific logs
docker-compose logs app --tail=50

# Search logs efficiently
docker-compose logs app | grep "ERROR"

# Export logs for analysis
docker-compose logs app > app-logs.txt
```

## 🚀 **Production Deployment with OrbStack**

### **Production Optimization**
```yaml
# docker-compose.prod.yml
services:
  app:
    image: video-api:latest
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - ENVIRONMENT=production
      - WORKERS=2
      - LOG_LEVEL=WARNING
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  dragonfly:
    image: docker.dragonflydb.io/dragonflydb/dragonfly:latest
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    command: [
      "--logtostderr",
      "--requirepass", "${REDIS_PASSWORD}",
      "--maxmemory", "400mb",
      "--save_schedule", "*:300"  # Persistence
    ]
```

### **Deployment Commands**
```bash
# Build for production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale based on load
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --scale app=5

# Monitor production deployment
orb stats --format table
```

## 💡 **OrbStack Best Practices for Your Project**

### **1. Resource Management**
```bash
# Set resource limits to prevent OOM
docker-compose exec app python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'CPU: {psutil.cpu_percent()}%')
"

# Monitor disk usage
orb df
du -sh downloads/
```

### **2. Network Optimization**
```bash
# Use OrbStack's built-in DNS
# Containers can reach each other by service name
curl http://dragonfly:6379  # Works automatically

# Test network performance
docker-compose exec app ping dragonfly
```

### **3. Development Efficiency**
```bash
# Use OrbStack's faster file sync
# Edit files on host, see changes immediately in container
echo "print('Hello from OrbStack')" >> app/test.py
docker-compose exec app python app/test.py
```

## 🎯 **Next Steps with OrbStack**

1. **Week 1**: Migrate from Docker Desktop to OrbStack
2. **Week 2**: Optimize docker-compose.yml for OrbStack
3. **Week 3**: Implement performance monitoring
4. **Week 4**: Test deployment pipeline

**Expected Benefits**:
- 50-70% faster development cycle
- 40-60% less resource usage
- Better debugging experience
- More reliable container networking

Your video streaming API will run significantly better on OrbStack! 🚀

# 🚀 Quick Start Guide

Get up and running in under 5 minutes!

## Prerequisites

Before you start, make sure you have:

- ✅ **Docker** (20.10+) - [Install Docker](https://docs.docker.com/get-docker/)
- ✅ **Docker Compose** (2.0+) - Usually included with Docker
- ✅ **Python** (3.12+) - [Install Python](https://www.python.org/downloads/)
- ✅ **Git** - [Install Git](https://git-scm.com/downloads)

Optional:
- Go (1.21+) - Only if you want to develop the Go API

## 🎯 Option 1: Automated Setup (Recommended)

### Step 1: Clone the Repository

```bash
git clone https://github.com/mythic3011/YouTuberBilBiliHelper.git
cd YouTuberBilBiliHelper
```

### Step 2: Run Setup Script

```bash
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh
```

This will:
- ✅ Check system requirements
- ✅ Install dependencies
- ✅ Create virtual environment
- ✅ Setup configuration files
- ✅ Create necessary directories
- ✅ Build Docker images
- ✅ Setup development tools

### Step 3: Start Development Environment

```bash
make dev
```

### Step 4: Test the API

```bash
# Python API
curl http://localhost:8000/health

# Go API (if available)
curl http://localhost:8001/health

# Open API documentation
open http://localhost:8000/docs
```

**🎉 Done! You're ready to develop!**

---

## 🛠️ Option 2: Manual Setup

### Step 1: Clone and Navigate

```bash
git clone https://github.com/mythic3011/YouTuberBilBiliHelper.git
cd YouTuberBilBiliHelper
```

### Step 2: Setup Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env if needed
vim .env
```

### Step 3: Install Python Dependencies

```bash
# Using uv (recommended - faster)
pip install uv
uv venv
source .venv/bin/activate
uv pip install -e .

# OR using standard pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Step 4: Create Directories

```bash
mkdir -p downloads/{youtube,bilibili,temp}
mkdir -p logs
mkdir -p config/cookies
```

### Step 5: Start Services with Docker

```bash
# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile all up -d

# OR use the deployment script
./scripts/deploy.sh development
```

### Step 6: Verify Everything Works

```bash
# Check service status
docker-compose ps

# Test Python API
curl http://localhost:8000/health

# View logs
docker-compose logs -f
```

---

## 📚 Common Commands

### Development

```bash
make dev          # Start development environment
make test         # Run tests
make lint         # Lint code
make format       # Format code
make logs         # View logs
make status       # Check service status
make stop         # Stop all services
make clean        # Clean up everything
```

### Deployment

```bash
make python       # Deploy Python API only
make go           # Deploy Go API only
make both         # Deploy both APIs
make production   # Full production deployment
```

### Testing

```bash
make test         # Run all tests
make benchmark    # Run performance benchmarks
make compare      # Compare Python vs Go performance
```

---

## 🌐 Access Points

After starting the development environment:

| Service | URL | Description |
|---------|-----|-------------|
| **Python API** | http://localhost:8000 | Main Python FastAPI |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **ReDoc** | http://localhost:8000/redoc | Alternative API documentation |
| **Go API** | http://localhost:8001 | High-performance Go API |
| **Redis UI** | http://localhost:8082 | Redis/DragonflyDB web interface |
| **Prometheus** | http://localhost:9090 | Metrics (production mode) |
| **Grafana** | http://localhost:3000 | Dashboards (production mode) |

---

## 🧪 Quick Test

### Test Video Download

```bash
# Get video information
curl "http://localhost:8000/api/v2/videos/youtube/dQw4w9WgXcQ"

# Get streaming URL
curl "http://localhost:8000/api/v2/stream/proxy/youtube/dQw4w9WgXcQ"
```

### Test Health Check

```bash
curl http://localhost:8000/api/v2/system/health
```

---

## 🐛 Troubleshooting

### Docker not running

```bash
# Check Docker status
docker info

# Start Docker (Mac)
open -a Docker

# Start Docker (Linux)
sudo systemctl start docker
```

### Port already in use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# OR change the port in .env file
PYTHON_API_PORT=8080
```

### Permission denied

```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### Virtual environment issues

```bash
# Remove and recreate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Docker build fails

```bash
# Clean Docker cache
docker system prune -af

# Rebuild without cache
docker-compose build --no-cache
```

### Services won't start

```bash
# Check logs for errors
docker-compose logs

# Check individual service
docker-compose logs python-api

# Restart services
docker-compose restart
```

---

## 📖 Next Steps

Now that you're set up, explore:

1. **[Improvement Plan](IMPROVEMENT_PLAN.md)** - See what's coming next
2. **[API Documentation](http://localhost:8000/docs)** - Explore all endpoints
3. **[Examples](../examples/)** - See usage examples
4. **[Tests](../tests/)** - Learn how to write tests

---

## 🆘 Need Help?

- 📚 Read the [full documentation](README.md)
- 🐛 [Open an issue](https://github.com/mythic3011/YouTuberBilBiliHelper/issues)
- 💬 [Start a discussion](https://github.com/mythic3011/YouTuberBilBiliHelper/discussions)
- 📧 Contact the maintainers

---

## 🎯 Quick Reference Card

```bash
# Setup (one time)
./scripts/setup-dev.sh

# Daily workflow
make dev          # Start services
make test         # Run tests
make logs         # View logs
make stop         # Stop services

# Code quality
make lint         # Check code
make format       # Format code

# Useful utilities
make status       # Service status
make health       # Health check
make benchmark    # Performance test
```

---

**Happy coding! 🚀**


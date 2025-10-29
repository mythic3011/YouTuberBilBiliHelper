# 🛠️ Project Management Guide

**Unified Management Script** for YouTuberBilBiliHelper

---

## 🚀 Quick Start

```bash
# Make executable (first time only)
chmod +x manage.sh

# Start development
./manage.sh dev

# Start production (Go API recommended)
./manage.sh start go

# Check status
./manage.sh status

# View help
./manage.sh help
```

---

## 📋 All Commands

### Development Commands

#### `./manage.sh dev`
Start development environment with hot reload

**What it does:**
- Creates/activates virtual environment
- Installs dependencies
- Starts Redis
- Runs Python API with auto-reload
- Opens on http://localhost:8000

**Example:**
```bash
./manage.sh dev
# Visit: http://localhost:8000/docs
```

#### `./manage.sh start [api]`
Start services in Docker

**Options:**
- `python` or `py` - Start Python API (default)
- `go` - Start Go API
- `both` or `all` - Start both APIs

**Examples:**
```bash
./manage.sh start python    # Python API on :8000
./manage.sh start go         # Go API on :8001
./manage.sh start both       # Both APIs
```

#### `./manage.sh stop`
Stop all running services

**Example:**
```bash
./manage.sh stop
```

#### `./manage.sh restart [api]`
Restart services

**Example:**
```bash
./manage.sh restart go
```

---

### Build & Deploy Commands

#### `./manage.sh build [target]`
Build Docker images

**Options:**
- `python` or `py` - Build Python image only
- `go` - Build Go image only
- `all` or `both` - Build all images

**Examples:**
```bash
./manage.sh build python
./manage.sh build go
./manage.sh build all
```

#### `./manage.sh deploy [target]`
Deploy to production

**Options:**
- `python` - Deploy Python API
- `go` - Deploy Go API (recommended)
- `both` - Deploy both

**Examples:**
```bash
./manage.sh deploy go        # Recommended for production
./manage.sh deploy both      # Deploy both for comparison
```

---

### Testing Commands

#### `./manage.sh test [type]`
Run tests

**Options:**
- `unit` - Run unit tests only (fast)
- `integration` - Run integration tests
- `quick` - Run quick manual test
- `coverage` - Run with coverage report
- `all` - Run all tests (default)

**Examples:**
```bash
./manage.sh test unit        # Fast unit tests
./manage.sh test coverage    # With coverage report
./manage.sh test all         # All tests
```

#### `./manage.sh bench`
Run performance benchmarks

**What it does:**
- Compares Python vs Go API performance
- Shows RPS, latency, throughput
- Requires both APIs running

**Example:**
```bash
./manage.sh start both
./manage.sh bench
```

---

### Code Quality Commands

#### `./manage.sh lint`
Run code quality checks

**What it checks:**
- Ruff (linting)
- Black (formatting)
- MyPy (type checking)

**Example:**
```bash
./manage.sh lint
```

#### `./manage.sh format`
Format code automatically

**What it does:**
- Format with Black
- Sort imports with isort

**Example:**
```bash
./manage.sh format
```

---

### Maintenance Commands

#### `./manage.sh clean [level]`
Clean project files

**Options:**
- `cache` - Clean Python cache files
- `temp` - Clean temporary files
- `docker` - Stop and remove containers
- `all` or `deep` - Deep clean (everything)
- (no option) - Normal clean (cache + temp)

**Examples:**
```bash
./manage.sh clean cache      # Clean Python cache
./manage.sh clean docker     # Remove Docker containers
./manage.sh clean all        # Deep clean
```

#### `./manage.sh logs [service]`
View service logs

**Options:**
- `python` - Python API logs
- `go` - Go API logs
- `redis` - Redis logs
- `all` - All logs (default)

**Examples:**
```bash
./manage.sh logs python      # Python API logs
./manage.sh logs all         # All logs
```

Press `Ctrl+C` to exit logs.

#### `./manage.sh shell [service]`
Open interactive shell

**Options:**
- `python` - Python API container shell
- `go` - Go API container shell
- `redis` - Redis CLI

**Examples:**
```bash
./manage.sh shell python     # Bash in Python container
./manage.sh shell redis      # Redis CLI
```

#### `./manage.sh status`
Check service status

**What it shows:**
- Python API status (port 8000)
- Go API status (port 8001)
- Redis status (port 6379)
- Docker containers

**Example:**
```bash
./manage.sh status
```

---

## 🎯 Common Workflows

### New Developer Setup
```bash
# Clone repository
git clone <repo-url>
cd YouTuberBilBiliHelper

# Start development
./manage.sh dev

# Access API
open http://localhost:8000/docs
```

### Development Workflow
```bash
# Start dev environment
./manage.sh dev

# In another terminal - run tests
./manage.sh test unit

# Check code quality
./manage.sh lint

# Format code
./manage.sh format
```

### Production Deployment
```bash
# Build images
./manage.sh build all

# Deploy Go API (recommended)
./manage.sh deploy go

# Check status
./manage.sh status

# View logs
./manage.sh logs go
```

### Testing Workflow
```bash
# Start services
./manage.sh start both

# Run all tests
./manage.sh test all

# Run with coverage
./manage.sh test coverage

# Run benchmarks
./manage.sh bench
```

### Troubleshooting
```bash
# Check status
./manage.sh status

# View logs
./manage.sh logs all

# Clean and restart
./manage.sh clean docker
./manage.sh restart both

# Open shell for debugging
./manage.sh shell python
```

### Maintenance
```bash
# Clean temporary files
./manage.sh clean temp

# Deep clean (removes everything)
./manage.sh clean all

# Rebuild from scratch
./manage.sh clean all
./manage.sh build all
./manage.sh deploy go
```

---

## 🔧 Environment Variables

Create `.env` file from template:

```bash
cp env.example .env
```

Edit `.env` to configure:
- API settings
- Redis connection
- Rate limiting
- Storage limits

---

## 📊 Performance Comparison

```bash
# Start both APIs
./manage.sh start both

# Run benchmark
./manage.sh bench

# View results
# Python: ~1,227 RPS
# Go:     ~4,035 RPS (3.3x faster!)
```

---

## 🐳 Docker Commands Reference

The management script uses Docker Compose. Direct commands:

```bash
# Start services
docker-compose up -d python-api redis

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Go API
cd go-api && docker-compose up -d
```

---

## 🎨 Customization

### Add Custom Commands

Edit `manage.sh` and add your function:

```bash
cmd_your_command() {
    print_header "Your Command"
    print_info "Doing something..."
    # Your code here
    print_success "Done!"
}
```

Then add to the main switch:

```bash
case "$command" in
    # ... existing commands ...
    your-command)   cmd_your_command "$@" ;;
esac
```

---

## 💡 Tips & Tricks

### Quick Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias m='./manage.sh'
alias mdev='./manage.sh dev'
alias mstart='./manage.sh start'
alias mstop='./manage.sh stop'
alias mstatus='./manage.sh status'
alias mtest='./manage.sh test'
```

Usage:
```bash
m dev           # Same as ./manage.sh dev
mstatus         # Same as ./manage.sh status
```

### Tab Completion

The script supports standard bash completion:

```bash
./manage.sh <TAB><TAB>    # Shows available commands
```

### Watching Logs

Use with terminal multiplexer for better experience:

```bash
# Terminal 1: Run app
./manage.sh dev

# Terminal 2: Watch logs
./manage.sh logs python

# Terminal 3: Run tests
./manage.sh test unit
```

---

## ⚡ Performance Tips

1. **Use Go API for Production**
   ```bash
   ./manage.sh deploy go    # 3.3x faster than Python
   ```

2. **Clean Regularly**
   ```bash
   ./manage.sh clean temp   # Remove temporary files
   ```

3. **Run Tests Before Deploy**
   ```bash
   ./manage.sh test all && ./manage.sh deploy go
   ```

4. **Check Status Regularly**
   ```bash
   watch -n 5 './manage.sh status'
   ```

---

## 🆘 Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Stop services
./manage.sh stop

# Or kill specific process
kill -9 <PID>
```

### Docker Issues

```bash
# Clean Docker
./manage.sh clean docker

# Rebuild images
./manage.sh build all

# Check Docker
docker ps
docker logs <container_name>
```

### Permission Denied

```bash
# Make script executable
chmod +x manage.sh

# Or run with bash
bash manage.sh dev
```

### Python Environment Issues

```bash
# Clean and recreate
./manage.sh clean all
./manage.sh dev
```

---

## 📚 Related Documentation

- [README.md](README.md) - Project overview
- [START_HERE.md](START_HERE.md) - Quick start guide
- [docs/getting-started/](docs/getting-started/) - Detailed guides
- [docs/deployment/](docs/deployment/) - Deployment guides

---

## 🎉 Examples

### Example 1: Fresh Start
```bash
# Clean everything
./manage.sh clean all

# Start fresh
./manage.sh dev

# Run tests
./manage.sh test all
```

### Example 2: Production Deploy
```bash
# Build production images
./manage.sh build all

# Deploy Go API
./manage.sh deploy go

# Check it's running
./manage.sh status

# View logs
./manage.sh logs go
```

### Example 3: Development Cycle
```bash
# Start development
./manage.sh dev

# Make changes...

# Format code
./manage.sh format

# Run tests
./manage.sh test unit

# Check quality
./manage.sh lint
```

---

## 🎯 Best Practices

1. **Always run tests before deploying**
   ```bash
   ./manage.sh test all && ./manage.sh deploy go
   ```

2. **Use Go API for production**
   - 3.3x faster performance
   - Lower memory usage
   - Smaller container size

3. **Clean regularly**
   ```bash
   ./manage.sh clean temp
   ```

4. **Check status after deploy**
   ```bash
   ./manage.sh deploy go && ./manage.sh status
   ```

5. **Format code before commits**
   ```bash
   ./manage.sh format
   ```

---

**For more help, run:** `./manage.sh help`


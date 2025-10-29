# 🎯 Getting Started with Development

## TL;DR - Fastest Way to Start

```bash
# 1. Clone the repo
git clone https://github.com/mythic3011/YouTuberBilBiliHelper.git
cd YouTuberBilBiliHelper

# 2. Run setup (< 5 minutes)
./scripts/setup-dev.sh

# 3. Start development
make dev

# 4. Open your browser
open http://localhost:8000/docs
```

**That's it! You're ready to develop! 🚀**

---

## 📚 What You Get

After running the setup, you'll have:

### ✅ Development Environment
- Python 3.12+ with virtual environment
- All dependencies installed (via uv)
- Docker containers ready
- Redis/DragonflyDB for caching
- Development tools installed

### ✅ Code Quality Tools
- Black (code formatting)
- Ruff (fast linting)
- Mypy (type checking)
- isort (import sorting)
- Pre-commit hooks (automatic checks)

### ✅ Testing Infrastructure
- Pytest with coverage
- Async testing support
- HTTP client for API testing
- Load testing tools (locust)

### ✅ Development Utilities
- Health check script
- Enhanced Makefile with 60+ commands
- Shell access to containers
- Log filtering and viewing
- API documentation

---

## 🛠️ Common Workflows

### Starting Your Day

```bash
# Start all services
make dev

# Check everything is healthy
make health

# View API documentation
make docs  # Opens http://localhost:8000/docs
```

### Making Changes

```bash
# 1. Create a feature branch
git checkout -b feature/amazing-feature

# 2. Make your changes...

# 3. Format code (optional - pre-commit does this)
make format

# 4. Run tests
make test-all

# 5. Check code quality
make quality

# 6. Commit (pre-commit hooks will run automatically)
git commit -m "Add amazing feature"
```

### Testing

```bash
# Run all tests with coverage
make test-all

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# View coverage report
make test-coverage  # Opens browser with report
```

### Debugging

```bash
# View all logs
make logs

# View Python API logs only
make logs-python

# View errors only
make logs-errors

# Check service health
make health

# Shell into Python container
make shell-python

# Access Redis CLI
make shell-redis
```

### Cleaning Up

```bash
# Stop all services
make stop

# Clean up downloads
make clean-downloads

# Clean up logs
make clean-logs

# Complete cleanup (removes containers, volumes, etc.)
make clean

# Reset to completely clean state
make reset
```

---

## 📖 Available Commands

Run `make help` to see all available commands. Here are the most useful ones:

### Quick Start
```bash
make setup       # Setup development environment (run once)
make dev         # Start development environment
make test-all    # Run all tests with coverage
```

### Testing
```bash
make test            # Run unit tests
make test-unit       # Run unit tests only
make test-integration # Run integration tests
make test-coverage   # Generate and view coverage report
make benchmark       # Run performance benchmarks
```

### Code Quality
```bash
make lint        # Lint code with ruff
make format      # Format code with black & isort
make type-check  # Run type checking with mypy
make quality     # Run all quality checks
```

### Management
```bash
make status      # Show service status
make logs        # Show all logs
make logs-python # Show Python API logs
make logs-errors # Show error logs only
make health      # Run health checks
make stop        # Stop all services
make clean       # Remove all containers
```

### Utilities
```bash
make shell-python    # Shell into Python container
make shell-redis     # Redis CLI
make docs            # Open API documentation
make clean-downloads # Clean downloads directory
make clean-logs      # Clean logs
make reset           # Reset to clean state
```

---

## 🎨 Development Best Practices

### Code Style

- **Line length**: 100 characters
- **Formatting**: Automatic with black
- **Imports**: Automatic sorting with isort
- **Type hints**: Use them where helpful
- **Docstrings**: Use for all public APIs

### Testing

- **Write tests first** when possible (TDD)
- **Test coverage**: Aim for > 80%
- **Fast tests**: Unit tests should be < 100ms
- **Isolated tests**: Don't depend on external services
- **Use fixtures**: For reusable test data

### Git Workflow

1. Create feature branch from `develop`
2. Make atomic commits with clear messages
3. Run `make quality` and `make test-all` before pushing
4. Push and create Pull Request
5. Wait for CI checks to pass
6. Get code review
7. Merge to `develop`

### Commit Messages

Follow conventional commits:

```
feat: Add amazing new feature
fix: Fix bug in video processing
docs: Update API documentation
test: Add tests for streaming service
refactor: Simplify error handling
chore: Update dependencies
```

---

## 🚀 Deployment Modes

### Development (Default)
```bash
make dev
# or
./scripts/deploy.sh development
```
- Hot reload enabled
- Debug logging
- Redis UI available
- Both Python and Go APIs

### Python Only
```bash
make python
# or
./scripts/deploy.sh python-only
```
- Only Python FastAPI
- Production-ready

### Go Only (High Performance)
```bash
make go
# or
./scripts/deploy.sh go-only
```
- Only Go API
- 3.3x faster than Python
- Lower resource usage

### Both APIs
```bash
make both
# or
./scripts/deploy.sh both
```
- Python API on port 8000
- Go API on port 8001
- Compare performance

### Production
```bash
make production
# or
./scripts/deploy.sh production
```
- Load balancer (nginx)
- Both APIs
- Prometheus metrics
- Grafana dashboards
- SSL ready

---

## 🐛 Troubleshooting

### "Docker is not running"
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

### "Port already in use"
```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <PID>

# Or change port in .env
PYTHON_API_PORT=8080
```

### "Permission denied on scripts"
```bash
chmod +x scripts/*.sh
```

### "Virtual environment not found"
```bash
# Recreate it
rm -rf .venv
./scripts/setup-dev.sh
```

### "Tests failing"
```bash
# Make sure services are running
make dev

# Check logs
make logs-errors

# Run health check
make health
```

### More Help
See [QUICKSTART.md](QUICKSTART.md) for detailed troubleshooting.

---

## 📚 Further Reading

- **[Quick Start Guide](QUICKSTART.md)** - Detailed setup instructions
- **[Improvement Plan](IMPROVEMENT_PLAN.md)** - Future roadmap
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - What's been implemented
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)
- **[Main README](../README.md)** - Project overview

---

## 🤝 Getting Help

- 📚 Check the documentation
- 🐛 Search existing issues
- 💬 Ask in discussions
- 📧 Contact maintainers

---

## 🎉 You're All Set!

Now you're ready to:
- ✅ Make changes
- ✅ Run tests
- ✅ Commit code (with automatic checks)
- ✅ Create pull requests
- ✅ Deploy with confidence

**Happy coding! 🚀**


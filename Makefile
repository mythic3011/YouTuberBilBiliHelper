# Video Streaming API Makefile
# Provides convenient commands for development and deployment

.PHONY: help python go both production development stop clean status logs benchmark test build

# Default target
help:
	@echo "Video Streaming API - Available Commands"
	@echo "========================================"
	@echo ""
	@echo "🎯 Quick Start:"
	@echo "  make setup       - Setup development environment (run once)"
	@echo "  make dev         - Start development environment"
	@echo "  make test-all    - Run all tests with coverage"
	@echo ""
	@echo "🚀 Deployment Commands:"
	@echo "  make python      - Deploy Python FastAPI only"
	@echo "  make go          - Deploy Go API only (high performance)"
	@echo "  make both        - Deploy both Python and Go APIs"
	@echo "  make production  - Deploy with load balancer and monitoring"
	@echo "  make development - Deploy development environment"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test        - Run unit tests"
	@echo "  make test-all    - Run all tests with coverage"
	@echo "  make test-unit   - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-coverage - Generate coverage report"
	@echo "  make benchmark   - Run performance benchmark"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint        - Lint code (ruff)"
	@echo "  make format      - Format code (black, isort)"
	@echo "  make type-check  - Run type checking (mypy)"
	@echo "  make quality     - Run all quality checks"
	@echo ""
	@echo "🛠️  Management Commands:"
	@echo "  make stop        - Stop all services"
	@echo "  make clean       - Stop and remove all containers/volumes"
	@echo "  make status      - Show service status"
	@echo "  make logs        - Show service logs"
	@echo "  make health      - Run health checks"
	@echo "  make shell-python - Shell into Python container"
	@echo "  make shell-redis - Shell into Redis"
	@echo ""
	@echo "🔧 Development Utilities:"
	@echo "  make install     - Install dependencies"
	@echo "  make build       - Build all images"
	@echo "  make reset       - Reset to clean state"
	@echo "  make seed        - Seed test data"
	@echo ""
	@echo "💡 Examples:"
	@echo "  make setup && make dev  # First time setup"
	@echo "  make test-all          # Run all tests"
	@echo "  make quality           # Check code quality"

# Python API only
python:
	@echo "🐍 Deploying Python FastAPI..."
	@./scripts/deploy.sh python-only

# Go API only
go:
	@echo "🚀 Deploying Go API..."
	@./scripts/deploy.sh go-only

# Both APIs
both:
	@echo "⚡ Deploying both APIs..."
	@./scripts/deploy.sh both

# Production deployment
production:
	@echo "🏭 Deploying production environment..."
	@./scripts/deploy.sh production

# Development deployment
development dev:
	@echo "🛠️ Deploying development environment..."
	@./scripts/deploy.sh development

# Stop services
stop:
	@echo "🛑 Stopping all services..."
	@./scripts/deploy.sh stop

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@./scripts/deploy.sh clean

# Show status
status:
	@echo "📊 Service status:"
	@./scripts/deploy.sh status

# Show logs
logs:
	@echo "📋 Service logs:"
	@./scripts/deploy.sh logs

# Run benchmark
benchmark:
	@echo "🏁 Running benchmark..."
	@./scripts/deploy.sh benchmark

# Run tests
test:
	@echo "🧪 Running tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python -m pytest tests/ -v; \
	else \
		python3 -m pytest tests/ -v; \
	fi

# Build all images
build:
	@echo "🏗️ Building all images..."
	@docker-compose build --parallel

# Quick development setup
quick-dev: development
	@echo ""
	@echo "🚀 Development environment ready!"
	@echo "  Python API: http://localhost:8000"
	@echo "  Go API:     http://localhost:8001"
	@echo "  Redis UI:   http://localhost:8082"

# Quick production setup
quick-prod: production
	@echo ""
	@echo "🏭 Production environment ready!"
	@echo "  Load Balancer: http://localhost"
	@echo "  Monitoring:    http://localhost:9090"
	@echo "  Dashboard:     http://localhost:3000"

# Performance comparison
compare: both
	@echo "⏱️ Running performance comparison..."
	@sleep 10  # Wait for services to start
	@./scripts/deploy.sh benchmark

# Docker cleanup
docker-clean:
	@echo "🐳 Cleaning Docker..."
	@docker system prune -f
	@docker volume prune -f

# Environment setup
setup:
	@echo "⚙️ Setting up environment..."
	@if [ ! -f .env ]; then cp env.example .env; echo "✅ .env created"; fi
	@if [ ! -d "downloads" ]; then mkdir -p downloads/{youtube,bilibili,temp}; echo "✅ Downloads directory created"; fi
	@if [ ! -d "logs" ]; then mkdir logs; echo "✅ Logs directory created"; fi
	@echo "✅ Environment setup complete"

# Go API development
go-dev:
	@echo "🚀 Starting Go API in development mode..."
	@cd go-api && go run main.go

# Python API development
python-dev:
	@echo "🐍 Starting Python API in development mode..."
	@if [ -d ".venv" ]; then \
		.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	fi

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@if command -v uv > /dev/null; then \
		uv sync; \
	elif [ -f "requirements.txt" ]; then \
		pip install -r requirements.txt; \
	else \
		pip install fastapi uvicorn redis loguru; \
	fi
	@cd go-api && go mod tidy
	@echo "✅ Dependencies installed"

# Update project
update:
	@echo "🔄 Updating project..."
	@git pull
	@make install
	@make build
	@echo "✅ Project updated"

# New Development Commands

# Run unit tests only
test-unit:
	@echo "🧪 Running unit tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python -m pytest tests/unit/ -v; \
	else \
		python3 -m pytest tests/unit/ -v; \
	fi

# Run integration tests
test-integration:
	@echo "🧪 Running integration tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python -m pytest tests/integration/ -v; \
	else \
		python3 -m pytest tests/integration/ -v; \
	fi

# Run all tests with coverage
test-all:
	@echo "🧪 Running all tests with coverage..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term; \
	else \
		python3 -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term; \
	fi
	@echo "✅ Coverage report generated in htmlcov/index.html"

# Generate coverage report
test-coverage: test-all
	@if command -v open &> /dev/null; then \
		open htmlcov/index.html; \
	else \
		echo "Open htmlcov/index.html in your browser"; \
	fi

# Lint code
lint:
	@echo "🔍 Linting code..."
	@if [ -d ".venv" ]; then \
		.venv/bin/ruff check app/ tests/; \
	else \
		ruff check app/ tests/; \
	fi

# Format code
format:
	@echo "✨ Formatting code..."
	@if [ -d ".venv" ]; then \
		.venv/bin/black app/ tests/ --line-length 100; \
		.venv/bin/isort app/ tests/ --profile black --line-length 100; \
	else \
		black app/ tests/ --line-length 100; \
		isort app/ tests/ --profile black --line-length 100; \
	fi
	@echo "✅ Code formatted"

# Type checking
type-check:
	@echo "🔍 Running type checker..."
	@if [ -d ".venv" ]; then \
		.venv/bin/mypy app/ --ignore-missing-imports --no-strict-optional; \
	else \
		mypy app/ --ignore-missing-imports --no-strict-optional; \
	fi

# Run all quality checks
quality: lint type-check
	@echo "✅ All quality checks passed!"

# Health check
health:
	@echo "🏥 Running health check..."
	@./scripts/health-check.sh

# Shell into Python container
shell-python:
	@echo "🐚 Opening shell in Python container..."
	@docker-compose exec python-api /bin/bash

# Shell into Go container
shell-go:
	@echo "🐚 Opening shell in Go container..."
	@docker-compose exec go-api /bin/sh

# Shell into Redis
shell-redis:
	@echo "🐚 Opening Redis CLI..."
	@docker-compose exec dragonfly redis-cli

# Reset to clean state
reset:
	@echo "🔄 Resetting to clean state..."
	@make clean
	@rm -rf .venv htmlcov .coverage .pytest_cache
	@echo "✅ Reset complete"

# Seed test data
seed:
	@echo "🌱 Seeding test data..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python scripts/seed_data.py; \
	else \
		python3 scripts/seed_data.py; \
	fi
	@echo "✅ Test data seeded"

# Watch mode for development
dev-watch:
	@echo "👀 Starting development with watch mode..."
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile all up

# Tail logs with filtering
logs-errors:
	@echo "📋 Showing error logs..."
	@docker-compose logs --tail=100 -f | grep -i "error\|exception\|failed"

# Show specific service logs
logs-python:
	@docker-compose logs -f python-api

logs-go:
	@docker-compose logs -f go-api

logs-redis:
	@docker-compose logs -f dragonfly

# Clean downloads
clean-downloads:
	@echo "🧹 Cleaning downloads..."
	@rm -rf downloads/youtube/* downloads/bilibili/* downloads/temp/*
	@echo "✅ Downloads cleaned"

# Clean logs
clean-logs:
	@echo "🧹 Cleaning logs..."
	@rm -rf logs/*.log
	@echo "✅ Logs cleaned"

# View API documentation
docs:
	@echo "📚 Opening API documentation..."
	@if command -v open &> /dev/null; then \
		open http://localhost:8000/docs; \
	else \
		echo "Open http://localhost:8000/docs in your browser"; \
	fi



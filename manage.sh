#!/bin/bash
# Project Management Script for YouTuberBilBiliHelper
# Unified script for all project operations

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project info
PROJECT_NAME="YouTuberBilBiliHelper"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Configuration
PYTHON_API_PORT=8000
GO_API_PORT=8001
REDIS_PORT=6379

#############################################
# Helper Functions
#############################################

print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${CYAN}$1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    return 0
}

check_port() {
    if lsof -Pi :"$1" -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

#############################################
# Main Commands
#############################################

cmd_start() {
    print_header "Starting $PROJECT_NAME"

    # Check which API to start
    local api="${1:-python}"

    case "$api" in
        python|py)
            print_info "Starting Python API on port $PYTHON_API_PORT..."
            if check_port $PYTHON_API_PORT; then
                print_warning "Python API already running on port $PYTHON_API_PORT"
            else
                docker-compose up -d python-api dragonfly
                print_success "Python API started"
                print_info "Access at: http://localhost:$PYTHON_API_PORT"
                print_info "API Docs: http://localhost:$PYTHON_API_PORT/docs"
            fi
            ;;
        go)
            print_info "Starting Go API on port $GO_API_PORT..."
            if check_port $GO_API_PORT; then
                print_warning "Go API already running on port $GO_API_PORT"
            else
                cd go-api && docker-compose up -d && cd ..
                print_success "Go API started"
                print_info "Access at: http://localhost:$GO_API_PORT"
                print_info "Health: http://localhost:$GO_API_PORT/health"
            fi
            ;;
        both|all)
            print_info "Starting both APIs..."
            cmd_start python
            sleep 2
            cmd_start go
            ;;
        *)
            print_error "Unknown API: $api"
            print_info "Usage: $0 start [python|go|both]"
            exit 1
            ;;
    esac
}

cmd_dev() {
    print_header "Starting Development Environment"

    # Check if uv is installed
    if check_command uv; then
        print_info "Using uv package manager..."

        # Create/sync environment with uv
        if [ ! -d ".venv" ]; then
            print_info "Creating virtual environment with uv..."
            uv venv
            print_success "Virtual environment created"
        fi

        # Install dependencies with uv
        print_info "Installing dependencies with uv..."
        uv pip install -e .
        uv pip install -r requirements-dev.txt
        print_success "Dependencies installed"

        # Activate virtual environment
        source .venv/bin/activate

    elif check_command python3; then
        print_info "Using pip (uv not found)..."

        # Check if virtual environment exists
        if [ ! -d ".venv" ]; then
            print_info "Creating virtual environment..."
            python3 -m venv .venv
            print_success "Virtual environment created"
        fi

        # Activate virtual environment
        print_info "Activating virtual environment..."
        source .venv/bin/activate

        # Install dependencies
        print_info "Installing dependencies..."
        pip install -q --upgrade pip
        pip install -q -e .
        pip install -q -r requirements-dev.txt
        print_success "Dependencies installed"

    else
        print_error "Neither uv nor Python 3 is installed"
        print_info "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        print_info "Or install Python 3: https://www.python.org/downloads/"
        exit 1
    fi

    # Start services
    print_info "Starting DragonflyDB (Redis-compatible cache)..."
    docker-compose up -d dragonfly

    # Run the application
    print_info "Starting Python API in development mode..."
    print_success "Development environment ready!"
    print_info ""
    print_info "Running on http://localhost:$PYTHON_API_PORT"
    print_info "API Docs: http://localhost:$PYTHON_API_PORT/docs"
    print_info ""
    print_info "Press Ctrl+C to stop"

    uvicorn app.main:app --reload --host 0.0.0.0 --port $PYTHON_API_PORT
}

cmd_build() {
    print_header "Building Docker Images"

    local target="${1:-all}"

    case "$target" in
        python|py)
            print_info "Building Python API image..."
            docker-compose build python-api
            print_success "Python API image built"
            ;;
        go)
            print_info "Building Go API image..."
            cd go-api && docker-compose build && cd ..
            print_success "Go API image built"
            ;;
        all|both)
            print_info "Building all images..."
            docker-compose build
            cd go-api && docker-compose build && cd ..
            print_success "All images built"
            ;;
        *)
            print_error "Unknown target: $target"
            print_info "Usage: $0 build [python|go|all]"
            exit 1
            ;;
    esac
}

cmd_clean() {
    print_header "Cleaning Project"

    local level="${1:-normal}"

    case "$level" in
        cache)
            print_info "Cleaning Python cache files..."
            find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            find . -type f -name "*.pyc" -delete 2>/dev/null || true
            find . -type f -name "*.pyo" -delete 2>/dev/null || true
            find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
            print_success "Python cache cleaned"
            ;;
        temp)
            print_info "Cleaning temporary files..."
            rm -rf downloads/temp/* 2>/dev/null || true
            rm -f app.log 2>/dev/null || true
            rm -rf .pytest_cache 2>/dev/null || true
            rm -f .coverage 2>/dev/null || true
            rm -rf htmlcov 2>/dev/null || true
            print_success "Temporary files cleaned"
            ;;
        docker)
            print_info "Stopping and removing Docker containers..."
            docker-compose down -v 2>/dev/null || true
            cd go-api && docker-compose down -v 2>/dev/null || true && cd ..
            print_success "Docker containers cleaned"
            ;;
        deep|all)
            print_info "Deep cleaning (cache, temp, docker, logs)..."
            cmd_clean cache
            cmd_clean temp
            cmd_clean docker
            rm -rf logs/* 2>/dev/null || true
            rm -rf .venv 2>/dev/null || true
            print_success "Deep clean completed"
            ;;
        *)
            print_info "Cleaning normal files..."
            cmd_clean cache
            cmd_clean temp
            print_success "Clean completed"
            ;;
    esac
}

cmd_test() {
    print_header "Running Tests"

    local test_type="${1:-all}"

    # Ensure we're in virtual environment or have pytest
    if ! check_command pytest; then
        print_error "pytest not found. Run: pip install pytest"
        exit 1
    fi

    case "$test_type" in
        unit)
            print_info "Running unit tests..."
            pytest tests/unit/ -v --tb=short
            ;;
        integration)
            print_info "Running integration tests..."
            # Start services if needed
            docker-compose up -d dragonfly
            sleep 2
            pytest tests/integration/ -v --tb=short
            ;;
        quick)
            print_info "Running quick test..."
            python tests/quick_test.py
            ;;
        coverage)
            print_info "Running tests with coverage..."
            pytest tests/ --cov=app --cov-report=html --cov-report=term
            print_success "Coverage report generated in htmlcov/"
            ;;
        all)
            print_info "Running all tests..."
            pytest tests/ -v --tb=short
            ;;
        *)
            print_error "Unknown test type: $test_type"
            print_info "Usage: $0 test [unit|integration|quick|coverage|all]"
            exit 1
            ;;
    esac
}

cmd_deploy() {
    print_header "Deploying $PROJECT_NAME"

    local target="${1:-go}"

    print_warning "Deploying to production..."
    print_info "Target: $target"

    case "$target" in
        python|py)
            print_info "Deploying Python API..."
            docker-compose -f docker-compose.yml up -d python-api dragonfly
            print_success "Python API deployed"
            ;;
        go)
            print_info "Deploying Go API (Recommended for production)..."
            cd go-api && docker-compose up -d && cd ..
            print_success "Go API deployed"
            ;;
        both)
            print_info "Deploying both APIs..."
            docker-compose up -d
            cd go-api && docker-compose up -d && cd ..
            print_success "Both APIs deployed"
            ;;
        *)
            print_error "Unknown target: $target"
            print_info "Usage: $0 deploy [python|go|both]"
            exit 1
            ;;
    esac

    sleep 3
    cmd_status
}

cmd_stop() {
    print_header "Stopping Services"

    print_info "Stopping Python API..."
    docker-compose down 2>/dev/null || true

    print_info "Stopping Go API..."
    cd go-api && docker-compose down 2>/dev/null || true && cd ..

    print_success "All services stopped"
}

cmd_restart() {
    print_header "Restarting Services"

    local target="${1:-both}"

    cmd_stop
    sleep 2
    cmd_start "$target"
}

cmd_status() {
    print_header "Service Status"

    # Check Python API
    if check_port $PYTHON_API_PORT; then
        print_success "Python API: Running on port $PYTHON_API_PORT"
        print_info "   → http://localhost:$PYTHON_API_PORT"
        print_info "   → http://localhost:$PYTHON_API_PORT/docs"
    else
        print_warning "Python API: Not running"
    fi

    echo ""

    # Check Go API
    if check_port $GO_API_PORT; then
        print_success "Go API: Running on port $GO_API_PORT"
        print_info "   → http://localhost:$GO_API_PORT"
        print_info "   → http://localhost:$GO_API_PORT/health"
    else
        print_warning "Go API: Not running"
    fi

    echo ""

    # Check DragonflyDB
    if check_port $REDIS_PORT; then
        print_success "DragonflyDB: Running on port $REDIS_PORT"
    else
        print_warning "DragonflyDB: Not running"
    fi

    echo ""

    # Docker containers
    print_info "Docker Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "video-api|redis|NAME" || print_warning "No containers running"
}

cmd_logs() {
    print_header "Viewing Logs"

    local service="${1:-all}"

    case "$service" in
        python|py)
            print_info "Python API logs (Ctrl+C to exit):"
            docker-compose logs -f python-api
            ;;
        go)
            print_info "Go API logs (Ctrl+C to exit):"
            cd go-api && docker-compose logs -f && cd ..
            ;;
        redis|dragonfly)
            print_info "DragonflyDB logs (Ctrl+C to exit):"
            docker-compose logs -f dragonfly
            ;;
        all)
            print_info "All logs (Ctrl+C to exit):"
            docker-compose logs -f &
            PID1=$!
            cd go-api && docker-compose logs -f &
            PID2=$!
            cd ..
            trap "kill $PID1 $PID2 2>/dev/null; exit" INT
            wait
            ;;
        *)
            print_error "Unknown service: $service"
            print_info "Usage: $0 logs [python|go|redis|all]"
            exit 1
            ;;
    esac
}

cmd_shell() {
    print_header "Opening Shell"

    local service="${1:-python}"

    case "$service" in
        python|py)
            print_info "Opening Python API shell..."
            docker-compose exec python-api /bin/bash || print_error "Python API not running"
            ;;
        go)
            print_info "Opening Go API shell..."
            cd go-api && docker-compose exec go-api /bin/sh && cd .. || print_error "Go API not running"
            ;;
        redis|dragonfly)
            print_info "Opening DragonflyDB CLI (Redis-compatible)..."
            docker-compose exec dragonfly redis-cli
            ;;
        *)
            print_error "Unknown service: $service"
            print_info "Usage: $0 shell [python|go|redis]"
            exit 1
            ;;
    esac
}

cmd_bench() {
    print_header "Running Performance Benchmark"

    if [ -f "scripts/compare_apis.sh" ]; then
        ./scripts/compare_apis.sh
    else
        print_error "Benchmark script not found"
        print_info "Make sure scripts/compare_apis.sh exists"
        exit 1
    fi
}

cmd_lint() {
    print_header "Running Code Quality Checks"

    print_info "Running ruff..."
    ruff check app/ tests/ || true

    print_info "Running black..."
    black --check app/ tests/ || true

    print_info "Running mypy..."
    mypy app/ || true

    print_success "Linting completed"
}

cmd_format() {
    print_header "Formatting Code"

    print_info "Formatting with black..."
    black app/ tests/

    print_info "Sorting imports with isort..."
    isort app/ tests/ || true

    print_success "Code formatted"
}

cmd_help() {
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║            YouTuberBilBiliHelper - Project Manager            ║
║           (Optimized for uv package manager)                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

USAGE:
    ./manage.sh <command> [options]

REQUIREMENTS:
    - uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh
    - OR Python 3.12+ with pip
    - Docker & Docker Compose
    - DragonflyDB (Redis-compatible, included in Docker setup)

COMMANDS:

  Development:
    dev               Start development environment with hot reload
    start [api]       Start services (python|go|both) [default: python]
    stop              Stop all services
    restart [api]     Restart services

  Build & Deploy:
    build [target]    Build Docker images (python|go|all)
    deploy [target]   Deploy to production (python|go|both)

  Testing:
    test [type]       Run tests (unit|integration|quick|coverage|all)
    bench             Run performance benchmarks

  Code Quality:
    lint              Run linters (ruff, black, mypy)
    format            Format code with black and isort

  Maintenance:
    clean [level]     Clean project (cache|temp|docker|all)
    logs [service]    View logs (python|go|dragonfly|all)
    shell [service]   Open shell (python|go|dragonfly)
    status            Check service status

  Information:
    help              Show this help message

EXAMPLES:

  # Start development
  ./manage.sh dev

  # Start production (Go API recommended)
  ./manage.sh start go

  # Build and deploy
  ./manage.sh build all
  ./manage.sh deploy go

  # Run tests
  ./manage.sh test unit
  ./manage.sh test coverage

  # Check status
  ./manage.sh status

  # Clean up
  ./manage.sh clean all

  # View logs
  ./manage.sh logs python

QUICK START:

  1. Development:     ./manage.sh dev
  2. Production:      ./manage.sh deploy go
  3. Check Status:    ./manage.sh status
  4. Run Tests:       ./manage.sh test

For more information, see README.md or docs/getting-started/

EOF
}

#############################################
# Main Entry Point
#############################################

main() {
    local command="${1:-help}"
    shift || true

    case "$command" in
        start)          cmd_start "$@" ;;
        dev|develop)    cmd_dev "$@" ;;
        build)          cmd_build "$@" ;;
        clean)          cmd_clean "$@" ;;
        test)           cmd_test "$@" ;;
        deploy)         cmd_deploy "$@" ;;
        stop)           cmd_stop "$@" ;;
        restart)        cmd_restart "$@" ;;
        status)         cmd_status "$@" ;;
        logs)           cmd_logs "$@" ;;
        shell)          cmd_shell "$@" ;;
        bench|benchmark) cmd_bench "$@" ;;
        lint)           cmd_lint "$@" ;;
        format|fmt)     cmd_format "$@" ;;
        help|--help|-h) cmd_help ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

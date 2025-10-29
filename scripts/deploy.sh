#!/bin/bash

# Video Streaming API Deployment Script
# Provides easy deployment options for different scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    echo "Video Streaming API Deployment Script"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Deployment Options:"
    echo "  python-only     Deploy only Python FastAPI"
    echo "  go-only         Deploy only Go API (High Performance)"
    echo "  both            Deploy both Python and Go APIs"
    echo "  production      Deploy with load balancer and monitoring"
    echo "  development     Deploy development environment with hot reload"
    echo "  stop            Stop all services"
    echo "  clean           Stop and remove all containers and volumes"
    echo "  status          Show status of all services"
    echo "  logs            Show logs from all services"
    echo "  benchmark       Run performance benchmark"
    echo ""
    echo "Examples:"
    echo "  $0 go-only                 # Deploy only Go API"
    echo "  $0 both                    # Deploy both APIs"
    echo "  $0 production              # Full production deployment"
    echo ""
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp env.example .env
        print_success ".env file created. You can modify it as needed."
    fi
}

# Deploy Python API only
deploy_python_only() {
    print_status "Deploying Python FastAPI only..."
    setup_env
    docker-compose --profile python-api up -d --build
    print_success "Python API deployed on port 8000"
    echo ""
    echo "Test the API:"
    echo "  curl http://localhost:8000/health"
    echo "  curl http://localhost:8000/api/v2/system/health"
}

# Deploy Go API only
deploy_go_only() {
    print_status "Deploying Go API only..."
    setup_env
    docker-compose --profile go-api up -d --build
    print_success "Go API deployed on port 8001"
    echo ""
    echo "Test the API:"
    echo "  curl http://localhost:8001/health"
    echo "  curl http://localhost:8001/api/v2/system/health"
}

# Deploy both APIs
deploy_both() {
    print_status "Deploying both Python and Go APIs..."
    setup_env
    docker-compose --profile all up -d --build
    print_success "Both APIs deployed"
    echo ""
    echo "Python API: http://localhost:8000"
    echo "Go API:     http://localhost:8001"
    echo ""
    echo "Test the APIs:"
    echo "  curl http://localhost:8000/health  # Python"
    echo "  curl http://localhost:8001/health  # Go"
}

# Production deployment
deploy_production() {
    print_status "Deploying production environment..."
    setup_env
    
    # Check if SSL certificates exist
    if [ ! -d "docker/nginx/ssl" ]; then
        print_warning "SSL certificates not found. Creating self-signed certificates..."
        mkdir -p docker/nginx/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout docker/nginx/ssl/nginx.key \
            -out docker/nginx/ssl/nginx.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    fi
    
    docker-compose --profile production --profile monitoring up -d --build
    print_success "Production environment deployed"
    echo ""
    echo "Services available:"
    echo "  Load Balancer:  http://localhost (routes to both APIs)"
    echo "  Python API:     http://localhost:8000"
    echo "  Go API:         http://localhost:8001"
    echo "  Prometheus:     http://localhost:9090"
    echo "  Grafana:        http://localhost:3000 (admin/admin)"
}

# Development deployment
deploy_development() {
    print_status "Deploying development environment..."
    setup_env
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile all up -d --build
    print_success "Development environment deployed with hot reload"
    echo ""
    echo "Development services:"
    echo "  Python API:      http://localhost:8000 (with reload)"
    echo "  Go API:          http://localhost:8001 (with hot reload)"
    echo "  Redis UI:        http://localhost:8082"
    echo ""
    echo "Note: Code changes will automatically reload the services"
}

# Stop all services
stop_services() {
    print_status "Stopping all services..."
    docker-compose --profile all --profile production --profile monitoring down
    print_success "All services stopped"
}

# Clean up everything
clean_all() {
    print_warning "This will remove all containers, images, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up all containers and volumes..."
        docker-compose --profile all --profile production --profile monitoring down -v --rmi all
        docker system prune -f
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Show status
show_status() {
    print_status "Service Status:"
    docker-compose --profile all --profile production --profile monitoring ps
    echo ""
    print_status "Container Stats:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.Status}}"
}

# Show logs
show_logs() {
    print_status "Showing logs from all services..."
    docker-compose --profile all --profile production --profile monitoring logs -f --tail=50
}

# Run benchmark
run_benchmark() {
    print_status "Running performance benchmark..."
    
    # Check if APIs are running
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1 && ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_error "No APIs are running. Please deploy first."
        exit 1
    fi
    
    if [ -f "scripts/performance_comparison.py" ]; then
        python3 scripts/performance_comparison.py
    else
        print_error "Benchmark script not found"
        exit 1
    fi
}

# Main script logic
main() {
    check_docker
    
    case "${1:-help}" in
        python-only)
            deploy_python_only
            ;;
        go-only)
            deploy_go_only
            ;;
        both)
            deploy_both
            ;;
        production)
            deploy_production
            ;;
        development|dev)
            deploy_development
            ;;
        stop)
            stop_services
            ;;
        clean)
            clean_all
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        benchmark)
            run_benchmark
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"




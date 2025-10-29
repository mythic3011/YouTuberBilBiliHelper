#!/bin/bash
# Quick deployment script for YouTuberBilBiliHelper
# Supports both Python and Go API deployment

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Deployment options:"
    echo "  python          Deploy Python API only (port 8000)"
    echo "  go              Deploy Go API only (port 8001) - Recommended"
    echo "  both            Deploy both APIs"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  status          Show service status"
    echo "  logs            Show service logs"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 go           # Deploy high-performance Go API"
    echo "  $0 both         # Deploy both for comparison"
    echo "  $0 stop         # Stop all services"
}

deploy_python() {
    echo -e "${BLUE}Deploying Python API...${NC}"
    docker-compose up -d python-api redis
    echo -e "${GREEN}✓ Python API deployed on port 8000${NC}"
    echo "  Docs: http://localhost:8000/docs"
}

deploy_go() {
    echo -e "${BLUE}Deploying Go API...${NC}"
    cd go-api
    docker-compose up -d
    cd ..
    echo -e "${GREEN}✓ Go API deployed on port 8001${NC}"
    echo "  Health: http://localhost:8001/health"
}

deploy_both() {
    echo -e "${BLUE}Deploying both APIs...${NC}"
    deploy_python
    sleep 2
    deploy_go
    echo -e "${GREEN}✓ Both APIs deployed${NC}"
    echo "  Python: http://localhost:8000"
    echo "  Go:     http://localhost:8001"
}

stop_services() {
    echo -e "${YELLOW}Stopping all services...${NC}"
    docker-compose down 2>/dev/null || true
    cd go-api && docker-compose down 2>/dev/null || true
    cd ..
    echo -e "${GREEN}✓ All services stopped${NC}"
}

restart_services() {
    echo -e "${YELLOW}Restarting services...${NC}"
    stop_services
    sleep 2
    deploy_both
}

show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    echo ""
    
    # Check Python API
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "Python API (8000): ${GREEN}✓ Running${NC}"
    else
        echo -e "Python API (8000): ${RED}✗ Stopped${NC}"
    fi
    
    # Check Go API
    if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "Go API (8001):     ${GREEN}✓ Running${NC}"
    else
        echo -e "Go API (8001):     ${RED}✗ Stopped${NC}"
    fi
    
    echo ""
    echo "Docker containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "video-api|NAME" || echo "No containers running"
}

show_logs() {
    echo -e "${BLUE}Service Logs:${NC}"
    echo "Press Ctrl+C to exit"
    echo ""
    
    # Follow logs from both
    docker-compose logs -f --tail=50 &
    PID1=$!
    
    cd go-api
    docker-compose logs -f --tail=50 &
    PID2=$!
    cd ..
    
    # Wait for Ctrl+C
    trap "kill $PID1 $PID2 2>/dev/null; exit" INT
    wait
}

# Main script
case "${1:-help}" in
    python)
        deploy_python
        ;;
    go)
        deploy_go
        ;;
    both)
        deploy_both
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac


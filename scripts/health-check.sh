#!/bin/bash

# Health Check Script
# Checks the status of all services and provides diagnostics

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Service Health Check Dashboard              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if a service is healthy
check_service() {
    local service_name=$1
    local url=$2
    local expected_code=${3:-200}

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        echo -e "${GREEN}✓${NC} $service_name is ${GREEN}healthy${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name is ${RED}unhealthy${NC}"
        return 1
    fi
}

# Check Docker containers
check_docker_containers() {
    echo -e "${BLUE}═══ Docker Containers ═══${NC}"

    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}✗ Docker is not running${NC}"
        return 1
    fi

    containers=$(docker-compose ps --services 2>/dev/null || echo "")

    if [ -z "$containers" ]; then
        echo -e "${YELLOW}⚠ No containers are running${NC}"
        return 1
    fi

    while IFS= read -r container; do
        status=$(docker-compose ps "$container" 2>/dev/null | tail -n +2 | awk '{print $3}')
        if [ "$status" == "Up" ]; then
            echo -e "${GREEN}✓${NC} $container: ${GREEN}Running${NC}"
        else
            echo -e "${RED}✗${NC} $container: ${RED}$status${NC}"
        fi
    done <<< "$containers"
    echo ""
}

# Check services
check_services() {
    echo -e "${BLUE}═══ Service Endpoints ═══${NC}"

    # Python API
    if check_service "Python API" "http://localhost:8000/health" "200"; then
        response=$(curl -s "http://localhost:8000/api/v2/system/health" | grep -o '"status":"[^"]*"' || echo "")
        echo -e "  ${BLUE}→${NC} Details: $response"
    fi

    # Go API
    if check_service "Go API" "http://localhost:8001/health" "200"; then
        response=$(curl -s "http://localhost:8001/api/v2/system/health" | grep -o '"status":"[^"]*"' || echo "")
        echo -e "  ${BLUE}→${NC} Details: $response"
    fi

    # Redis/DragonflyDB
    if nc -z localhost 6379 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Redis/DragonflyDB is ${GREEN}healthy${NC}"
        if command -v redis-cli &> /dev/null; then
            redis-cli ping > /dev/null 2>&1 && echo -e "  ${BLUE}→${NC} PING: PONG"
        fi
    else
        echo -e "${RED}✗${NC} Redis/DragonflyDB is ${RED}unhealthy${NC}"
    fi

    echo ""
}

# Check system resources
check_resources() {
    echo -e "${BLUE}═══ System Resources ═══${NC}"

    # Docker stats
    echo -e "${YELLOW}Container Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "No containers running"

    echo ""
}

# Check disk space
check_disk() {
    echo -e "${BLUE}═══ Disk Usage ═══${NC}"

    # Downloads directory
    if [ -d "downloads" ]; then
        size=$(du -sh downloads 2>/dev/null | cut -f1)
        echo -e "${BLUE}Downloads:${NC} $size"
    fi

    # Logs directory
    if [ -d "logs" ]; then
        size=$(du -sh logs 2>/dev/null | cut -f1)
        echo -e "${BLUE}Logs:${NC} $size"
    fi

    # Docker volumes
    echo -e "${YELLOW}Docker Volumes:${NC}"
    docker system df -v 2>/dev/null | grep "VOLUME NAME" -A 10 || echo "No volumes"

    echo ""
}

# Check logs for errors
check_logs() {
    echo -e "${BLUE}═══ Recent Errors ═══${NC}"

    error_count=$(docker-compose logs --tail=100 2>/dev/null | grep -i "error\|exception\|failed" | wc -l || echo "0")

    if [ "$error_count" -gt 0 ]; then
        echo -e "${RED}Found $error_count error messages in recent logs${NC}"
        echo -e "${YELLOW}Last 5 errors:${NC}"
        docker-compose logs --tail=100 2>/dev/null | grep -i "error\|exception\|failed" | tail -n 5
    else
        echo -e "${GREEN}✓ No recent errors found${NC}"
    fi

    echo ""
}

# Provide recommendations
provide_recommendations() {
    echo -e "${BLUE}═══ Recommendations ═══${NC}"

    # Check if services are running
    if ! docker-compose ps | grep -q "Up"; then
        echo -e "${YELLOW}⚠${NC} No services are running. Start them with:"
        echo -e "  ${GREEN}make dev${NC} or ${GREEN}./scripts/deploy.sh development${NC}"
    fi

    # Check disk space
    if [ -d "downloads" ]; then
        size_mb=$(du -sm downloads 2>/dev/null | cut -f1)
        if [ "$size_mb" -gt 10000 ]; then
            echo -e "${YELLOW}⚠${NC} Downloads directory is large (${size_mb}MB). Consider cleaning up:"
            echo -e "  ${GREEN}make clean-downloads${NC}"
        fi
    fi

    # Check logs
    if [ -d "logs" ]; then
        size_mb=$(du -sm logs 2>/dev/null | cut -f1)
        if [ "$size_mb" -gt 100 ]; then
            echo -e "${YELLOW}⚠${NC} Logs directory is large (${size_mb}MB). Consider cleaning up:"
            echo -e "  ${GREEN}rm -rf logs/*.log${NC}"
        fi
    fi

    echo ""
}

# Main execution
main() {
    check_docker_containers
    check_services
    check_resources
    check_disk
    check_logs
    provide_recommendations

    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              Health Check Complete                    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}For more details:${NC}"
    echo -e "  ${GREEN}make logs${NC}    - View service logs"
    echo -e "  ${GREEN}make status${NC}  - View container status"
    echo ""
}

# Run main
main


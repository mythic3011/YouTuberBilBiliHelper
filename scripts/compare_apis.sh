#!/bin/bash
# Comprehensive API comparison script
# Compares Python and Go API performance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   API Performance Comparison${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if both APIs are running
check_api() {
    local name=$1
    local url=$2
    
    echo -n "Checking $name... "
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Run performance test
run_perf_test() {
    local name=$1
    local url=$2
    local duration=${3:-10}
    local connections=${4:-100}
    
    echo -e "\n${YELLOW}Testing $name${NC}"
    echo "Duration: ${duration}s, Connections: ${connections}"
    echo "--------------------"
    
    # Check if wrk is installed
    if ! command -v wrk &> /dev/null; then
        echo -e "${RED}wrk not found. Installing...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install wrk
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get install wrk -y
        fi
    fi
    
    wrk -t4 -c"$connections" -d"${duration}s" --latency "$url" | tee "/tmp/${name}_perf.txt"
}

# Parse and compare results
compare_results() {
    local python_file="/tmp/python_perf.txt"
    local go_file="/tmp/go_perf.txt"
    
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}   Comparison Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Extract RPS
    python_rps=$(grep "Requests/sec:" "$python_file" | awk '{print $2}')
    go_rps=$(grep "Requests/sec:" "$go_file" | awk '{print $2}')
    
    # Calculate improvement
    improvement=$(echo "scale=2; $go_rps / $python_rps" | bc)
    
    echo ""
    echo "Requests per second:"
    echo "  Python: ${python_rps}"
    echo "  Go:     ${go_rps}"
    echo -e "  ${GREEN}Improvement: ${improvement}x faster${NC}"
    
    # Extract latency
    echo ""
    echo "Latency:"
    grep -A 3 "Latency" "$python_file" | sed 's/^/  Python: /'
    grep -A 3 "Latency" "$go_file" | sed 's/^/  Go:     /'
}

# Main execution
main() {
    PYTHON_URL=${PYTHON_URL:-"http://localhost:8000/health"}
    GO_URL=${GO_URL:-"http://localhost:8001/health"}
    DURATION=${DURATION:-10}
    CONNECTIONS=${CONNECTIONS:-100}
    
    echo "Configuration:"
    echo "  Python API: $PYTHON_URL"
    echo "  Go API:     $GO_URL"
    echo "  Duration:   ${DURATION}s"
    echo "  Connections: ${CONNECTIONS}"
    echo ""
    
    # Check APIs
    python_running=0
    go_running=0
    
    if check_api "Python API" "$PYTHON_URL"; then
        python_running=1
    fi
    
    if check_api "Go API" "$GO_URL"; then
        go_running=1
    fi
    
    # Run tests if both are running
    if [ $python_running -eq 1 ] && [ $go_running -eq 1 ]; then
        run_perf_test "python" "$PYTHON_URL" "$DURATION" "$CONNECTIONS"
        sleep 2
        run_perf_test "go" "$GO_URL" "$DURATION" "$CONNECTIONS"
        compare_results
    else
        echo -e "\n${RED}Error: Both APIs must be running for comparison${NC}"
        echo ""
        echo "To start the APIs:"
        echo "  Python: make dev"
        echo "  Go:     cd go-api && docker-compose up -d"
        exit 1
    fi
}

# Handle arguments
case "${1:-}" in
    -h|--help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  -h, --help          Show this help message"
        echo "  -d, --duration N    Test duration in seconds (default: 10)"
        echo "  -c, --connections N Number of connections (default: 100)"
        echo ""
        echo "Environment variables:"
        echo "  PYTHON_URL          Python API URL (default: http://localhost:8000/health)"
        echo "  GO_URL              Go API URL (default: http://localhost:8001/health)"
        echo "  DURATION            Test duration"
        echo "  CONNECTIONS         Number of connections"
        exit 0
        ;;
    -d|--duration)
        DURATION=$2
        shift 2
        ;;
    -c|--connections)
        CONNECTIONS=$2
        shift 2
        ;;
esac

main


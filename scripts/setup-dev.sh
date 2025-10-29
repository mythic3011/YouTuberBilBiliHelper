#!/bin/bash

# Development Environment Setup Script
# Sets up everything needed to start developing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   YouTuberBilBiliHelper Development Setup             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check system requirements
check_requirements() {
    echo -e "${BLUE}[1/8]${NC} Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker is not installed${NC}"
        echo "  Install Docker from: https://www.docker.com/get-started"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker found${NC}"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}✗ Docker Compose is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose found${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 is not installed${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
    
    # Check Go (optional)
    if command -v go &> /dev/null; then
        GO_VERSION=$(go version | cut -d' ' -f3)
        echo -e "${GREEN}✓ Go ${GO_VERSION} found${NC}"
    else
        echo -e "${YELLOW}⚠ Go not found (optional for Go API development)${NC}"
    fi
    
    echo ""
}

# Install uv (fast Python package installer)
install_uv() {
    echo -e "${BLUE}[2/8]${NC} Installing uv (fast Python package installer)..."
    
    if ! command -v uv &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
        echo -e "${GREEN}✓ uv installed${NC}"
    else
        echo -e "${GREEN}✓ uv already installed${NC}"
    fi
    echo ""
}

# Setup Python virtual environment
setup_venv() {
    echo -e "${BLUE}[3/8]${NC} Setting up Python virtual environment..."
    
    if [ -d ".venv" ]; then
        echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
    else
        if command -v uv &> /dev/null; then
            uv venv
            echo -e "${GREEN}✓ Virtual environment created with uv${NC}"
        else
            python3 -m venv .venv
            echo -e "${GREEN}✓ Virtual environment created${NC}"
        fi
    fi
    
    # Activate venv
    source .venv/bin/activate
    
    # Install dependencies
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    if command -v uv &> /dev/null; then
        uv pip install -e .
    else
        pip install -e .
    fi
    
    # Install dev dependencies
    if [ -f "requirements-dev.txt" ]; then
        if command -v uv &> /dev/null; then
            uv pip install -r requirements-dev.txt
        else
            pip install -r requirements-dev.txt
        fi
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo ""
}

# Setup environment file
setup_env() {
    echo -e "${BLUE}[4/8]${NC} Setting up environment configuration..."
    
    if [ -f ".env" ]; then
        echo -e "${YELLOW}⚠ .env file already exists, skipping...${NC}"
    else
        cp env.example .env
        echo -e "${GREEN}✓ .env file created from template${NC}"
        echo -e "${YELLOW}  → Edit .env to customize your settings${NC}"
    fi
    echo ""
}

# Create necessary directories
setup_directories() {
    echo -e "${BLUE}[5/8]${NC} Creating necessary directories..."
    
    mkdir -p downloads/{youtube,bilibili,instagram,twitter,twitch,temp}
    mkdir -p logs
    mkdir -p config/cookies
    mkdir -p benchmarks
    
    # Create .gitkeep files
    touch downloads/youtube/.gitkeep
    touch downloads/bilibili/.gitkeep
    touch downloads/temp/.gitkeep
    touch logs/.gitkeep
    
    echo -e "${GREEN}✓ Directories created${NC}"
    echo ""
}

# Setup pre-commit hooks
setup_precommit() {
    echo -e "${BLUE}[6/8]${NC} Setting up pre-commit hooks..."
    
    if [ -f ".pre-commit-config.yaml" ]; then
        if [ -d ".venv" ]; then
            .venv/bin/pip install pre-commit
            .venv/bin/pre-commit install
            echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
        else
            echo -e "${YELLOW}⚠ Virtual environment not found, skipping pre-commit${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ .pre-commit-config.yaml not found, skipping...${NC}"
    fi
    echo ""
}

# Setup Docker
setup_docker() {
    echo -e "${BLUE}[7/8]${NC} Setting up Docker environment..."
    
    # Check if Docker daemon is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}✗ Docker daemon is not running${NC}"
        echo "  Please start Docker and try again"
        exit 1
    fi
    
    # Create Docker network if it doesn't exist
    if ! docker network ls | grep -q video-api-network; then
        docker network create video-api-network
        echo -e "${GREEN}✓ Docker network created${NC}"
    else
        echo -e "${GREEN}✓ Docker network already exists${NC}"
    fi
    
    echo -e "${BLUE}Building Docker images (this may take a few minutes)...${NC}"
    docker-compose build
    
    echo -e "${GREEN}✓ Docker setup complete${NC}"
    echo ""
}

# Final instructions
print_next_steps() {
    echo -e "${BLUE}[8/8]${NC} Setup complete! 🎉"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Setup Completed Successfully!             ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo ""
    echo -e "  ${BLUE}1.${NC} Review and edit .env file for your environment:"
    echo -e "     ${GREEN}vim .env${NC}"
    echo ""
    echo -e "  ${BLUE}2.${NC} Start development environment:"
    echo -e "     ${GREEN}make dev${NC}"
    echo -e "     or"
    echo -e "     ${GREEN}./scripts/deploy.sh development${NC}"
    echo ""
    echo -e "  ${BLUE}3.${NC} Run tests:"
    echo -e "     ${GREEN}make test${NC}"
    echo ""
    echo -e "  ${BLUE}4.${NC} View all available commands:"
    echo -e "     ${GREEN}make help${NC}"
    echo ""
    echo -e "${YELLOW}Quick Commands:${NC}"
    echo -e "  ${GREEN}make dev${NC}         - Start development environment"
    echo -e "  ${GREEN}make test${NC}        - Run test suite"
    echo -e "  ${GREEN}make lint${NC}        - Lint code"
    echo -e "  ${GREEN}make format${NC}      - Format code"
    echo -e "  ${GREEN}make logs${NC}        - View service logs"
    echo -e "  ${GREEN}make status${NC}      - Check service status"
    echo ""
    echo -e "${YELLOW}Access Points (after starting dev environment):${NC}"
    echo -e "  Python API:    ${GREEN}http://localhost:8000${NC}"
    echo -e "  Go API:        ${GREEN}http://localhost:8001${NC}"
    echo -e "  API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  Redis UI:      ${GREEN}http://localhost:8082${NC}"
    echo ""
    echo -e "${YELLOW}Documentation:${NC}"
    echo -e "  ${GREEN}docs/IMPROVEMENT_PLAN.md${NC}  - Full improvement roadmap"
    echo -e "  ${GREEN}docs/README.md${NC}            - Project documentation"
    echo -e "  ${GREEN}README.md${NC}                 - Getting started guide"
    echo ""
    echo -e "${BLUE}Happy coding! 🚀${NC}"
    echo ""
}

# Main execution
main() {
    check_requirements
    install_uv
    setup_venv
    setup_env
    setup_directories
    setup_precommit
    setup_docker
    print_next_steps
}

# Run main function
main



#!/bin/bash
#
# Production Environment Setup Script
# Generates secure secrets and creates .env file for production deployment
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Video Streaming API - Production Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for required tools
check_requirements() {
    echo -e "${YELLOW}Checking requirements...${NC}"

    local missing=0

    if ! command -v openssl &> /dev/null; then
        echo -e "${RED}ERROR: openssl is not installed${NC}"
        missing=1
    fi

    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}WARNING: docker is not installed (optional for local dev)${NC}"
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        echo -e "${YELLOW}WARNING: docker-compose is not installed (optional for local dev)${NC}"
    fi

    if [ $missing -eq 1 ]; then
        echo -e "${RED}Please install missing requirements and try again${NC}"
        exit 1
    fi

    echo -e "${GREEN}All requirements satisfied${NC}"
    echo ""
}

# Generate secure random string
generate_secret() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -dc 'a-zA-Z0-9' | head -c $length
}

# Generate API key (longer, more secure)
generate_api_key() {
    local prefix=${1:-"vsa"}
    local random=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 40)
    echo "${prefix}_${random}"
}

# Backup existing .env if present
backup_env() {
    if [ -f "$ENV_FILE" ]; then
        local backup_file="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${YELLOW}Backing up existing .env to $backup_file${NC}"
        cp "$ENV_FILE" "$backup_file"
    fi
}

# Prompt for configuration
prompt_config() {
    echo -e "${BLUE}Configuration Options${NC}"
    echo -e "${BLUE}--------------------${NC}"
    echo ""

    # Environment
    read -p "Environment (production/staging) [production]: " ENV_MODE
    ENV_MODE=${ENV_MODE:-production}

    # Port
    read -p "API Port [8001]: " API_PORT
    API_PORT=${API_PORT:-8001}

    # CORS Origins
    echo ""
    echo -e "${YELLOW}CORS Configuration${NC}"
    echo "Enter allowed origins (comma-separated, leave empty for all origins)"
    echo "Example: https://example.com,https://app.example.com"
    read -p "Allowed Origins: " CORS_ORIGINS

    # API Key Authentication
    echo ""
    echo -e "${YELLOW}API Key Authentication${NC}"
    read -p "Enable API Key authentication? (y/n) [n]: " ENABLE_API_KEY
    ENABLE_API_KEY=${ENABLE_API_KEY:-n}

    if [[ "$ENABLE_API_KEY" =~ ^[Yy]$ ]]; then
        API_KEY_ENABLED="true"
        read -p "Number of API keys to generate [1]: " NUM_API_KEYS
        NUM_API_KEYS=${NUM_API_KEYS:-1}
    else
        API_KEY_ENABLED="false"
        NUM_API_KEYS=0
    fi

    # Rate Limiting
    echo ""
    echo -e "${YELLOW}Rate Limiting${NC}"
    read -p "Enable rate limiting? (y/n) [y]: " ENABLE_RATE_LIMIT
    ENABLE_RATE_LIMIT=${ENABLE_RATE_LIMIT:-y}

    if [[ "$ENABLE_RATE_LIMIT" =~ ^[Yy]$ ]]; then
        RATE_LIMIT_ENABLED="true"
        read -p "Max requests per window [100]: " RATE_LIMIT_MAX
        RATE_LIMIT_MAX=${RATE_LIMIT_MAX:-100}
        read -p "Window size in seconds [60]: " RATE_LIMIT_WINDOW
        RATE_LIMIT_WINDOW=${RATE_LIMIT_WINDOW:-60}
    else
        RATE_LIMIT_ENABLED="false"
        RATE_LIMIT_MAX=100
        RATE_LIMIT_WINDOW=60
    fi

    # IP Access Control
    echo ""
    echo -e "${YELLOW}IP Access Control${NC}"
    read -p "Enable IP access control? (y/n) [n]: " ENABLE_IP_CONTROL
    ENABLE_IP_CONTROL=${ENABLE_IP_CONTROL:-n}

    if [[ "$ENABLE_IP_CONTROL" =~ ^[Yy]$ ]]; then
        IP_CONTROL_ENABLED="true"
        echo "Enter allowed IPs/CIDRs (comma-separated, leave empty for no allowlist)"
        read -p "IP Allowlist: " IP_ALLOWLIST
        echo "Enter blocked IPs/CIDRs (comma-separated, leave empty for no blocklist)"
        read -p "IP Blocklist: " IP_BLOCKLIST
    else
        IP_CONTROL_ENABLED="false"
        IP_ALLOWLIST=""
        IP_BLOCKLIST=""
    fi
}

# Generate secrets
generate_secrets() {
    echo ""
    echo -e "${BLUE}Generating Secrets${NC}"
    echo -e "${BLUE}------------------${NC}"

    # Redis password
    REDIS_PASSWORD=$(generate_secret 32)
    echo -e "${GREEN}✓ Generated Redis password${NC}"

    # API Keys
    API_KEYS_LIST=""
    if [ "$NUM_API_KEYS" -gt 0 ]; then
        for i in $(seq 1 $NUM_API_KEYS); do
            key=$(generate_api_key "vsa")
            if [ -z "$API_KEYS_LIST" ]; then
                API_KEYS_LIST="$key"
            else
                API_KEYS_LIST="$API_KEYS_LIST,$key"
            fi
            echo -e "${GREEN}✓ Generated API Key $i: ${YELLOW}$key${NC}"
        done
    fi
}

# Create .env file
create_env_file() {
    echo ""
    echo -e "${BLUE}Creating .env file${NC}"
    echo -e "${BLUE}------------------${NC}"

    cat > "$ENV_FILE" << EOF
# ===========================================
# Video Streaming API - Production Configuration
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# ===========================================

# -----------------
# Server Settings
# -----------------
ENVIRONMENT=${ENV_MODE}
PORT=${API_PORT}
LOG_LEVEL=info

# -----------------
# Redis Configuration
# -----------------
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_DB=0

# -----------------
# Cache TTL Settings
# -----------------
VIDEO_INFO_TTL=15m
STREAM_URL_TTL=5m

# -----------------
# Smart Proxy Settings
# -----------------
SMART_PROXY_ENABLED=true
PROXY_COUNTRIES=CN
DEFAULT_STREAM_MODE=direct

# -----------------
# Rate Limiting
# -----------------
RATE_LIMIT_ENABLED=${RATE_LIMIT_ENABLED}
RATE_LIMIT_MAX_REQUESTS=${RATE_LIMIT_MAX}
RATE_LIMIT_WINDOW=${RATE_LIMIT_WINDOW}
RATE_LIMIT_BY_IP=true

# -----------------
# API Key Authentication
# -----------------
API_KEY_ENABLED=${API_KEY_ENABLED}
API_KEYS=${API_KEYS_LIST}
API_KEY_HEADER=X-API-Key
API_KEY_EXEMPT_IPS=127.0.0.1,::1

# -----------------
# CORS Configuration
# -----------------
CORS_ALLOWED_ORIGINS=${CORS_ORIGINS}
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-API-Key,X-Requested-With
CORS_ALLOW_CREDENTIALS=${CORS_ORIGINS:+true}
CORS_ALLOW_CREDENTIALS=${CORS_ALLOW_CREDENTIALS:-false}
CORS_MAX_AGE=86400

# -----------------
# IP Access Control
# -----------------
ENABLE_IP_CONTROL=${IP_CONTROL_ENABLED}
IP_ALLOWLIST=${IP_ALLOWLIST}
IP_BLOCKLIST=${IP_BLOCKLIST}

# -----------------
# Security Headers
# -----------------
ENABLE_HSTS=true
HSTS_MAX_AGE=31536000
CSP_DIRECTIVES=default-src 'self'
REFERRER_POLICY=strict-origin-when-cross-origin
PERMISSIONS_POLICY=geolocation=(), microphone=(), camera=()

# -----------------
# Audit Logging
# -----------------
ENABLE_AUDIT_LOG=true
AUDIT_LOG_PATH=logs/audit.log

# -----------------
# Error Handling
# -----------------
EXPOSE_DETAILED_ERRORS=false
EOF

    chmod 600 "$ENV_FILE"
    echo -e "${GREEN}✓ Created .env file with secure permissions (600)${NC}"
}

# Print summary
print_summary() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Setup Complete!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}Configuration Summary:${NC}"
    echo "  Environment:     ${ENV_MODE}"
    echo "  Port:            ${API_PORT}"
    echo "  Rate Limiting:   ${RATE_LIMIT_ENABLED}"
    echo "  API Key Auth:    ${API_KEY_ENABLED}"
    echo "  IP Control:      ${IP_CONTROL_ENABLED}"
    echo ""

    if [ "$API_KEY_ENABLED" = "true" ]; then
        echo -e "${YELLOW}Generated API Keys:${NC}"
        IFS=',' read -ra KEYS <<< "$API_KEYS_LIST"
        for key in "${KEYS[@]}"; do
            echo "  - $key"
        done
        echo ""
        echo -e "${RED}IMPORTANT: Save these API keys securely. They cannot be recovered!${NC}"
        echo ""
    fi

    echo -e "${GREEN}Next Steps:${NC}"
    echo "  1. Review the .env file: ${ENV_FILE}"
    echo "  2. Start the services:  docker-compose up -d"
    echo "  3. Check health:        curl http://localhost:${API_PORT}/health"
    echo ""

    if [ "$API_KEY_ENABLED" = "true" ]; then
        echo -e "${YELLOW}To test with API key:${NC}"
        echo "  curl -H 'X-API-Key: YOUR_API_KEY' http://localhost:${API_PORT}/api/v2/system/health"
        echo ""
    fi
}

# Main execution
main() {
    check_requirements
    backup_env
    prompt_config
    generate_secrets
    create_env_file
    print_summary
}

# Run main function
main

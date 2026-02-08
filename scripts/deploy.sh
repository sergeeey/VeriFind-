#!/bin/bash
# ============================================================================
# APE 2026 - Production Deployment Script
# Week 9 Day 2
#
# Usage:
#   ./scripts/deploy.sh [environment]
#
# Arguments:
#   environment: dev, staging, or production (default: dev)
#
# Example:
#   ./scripts/deploy.sh production
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation
validate_environment() {
    case "$ENVIRONMENT" in
        dev|staging|production)
            log_info "Deploying to: $ENVIRONMENT"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_error "Valid options: dev, staging, production"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found"
        log_info "Creating from .env.example..."
        cp "${PROJECT_ROOT}/.env.example" "$ENV_FILE"
        log_warning "Please configure .env file before continuing"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Validate production secrets
validate_production_secrets() {
    if [ "$ENVIRONMENT" == "production" ]; then
        log_info "Validating production secrets..."

        # Check if critical secrets are set
        source "$ENV_FILE"

        local errors=0

        if [ "${SECRET_KEY:-}" == "dev_secret_key_change_in_production" ]; then
            log_error "SECRET_KEY must be changed in production"
            errors=$((errors + 1))
        fi

        if [ ${#SECRET_KEY} -lt 32 ]; then
            log_error "SECRET_KEY must be at least 32 characters"
            errors=$((errors + 1))
        fi

        if [ "${POSTGRES_PASSWORD:-}" == "ape_timescale_password_CHANGE_ME" ]; then
            log_error "POSTGRES_PASSWORD must be changed in production"
            errors=$((errors + 1))
        fi

        if [ "${NEO4J_PASSWORD:-}" == "ape_neo4j_password_CHANGE_ME" ]; then
            log_error "NEO4J_PASSWORD must be changed in production"
            errors=$((errors + 1))
        fi

        if [ $errors -gt 0 ]; then
            log_error "Production secrets validation failed. Please fix errors in .env"
            exit 1
        fi

        log_success "Production secrets validation passed"
    fi
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."

    docker compose build \
        --build-arg ENVIRONMENT="$ENVIRONMENT" \
        api

    log_success "Docker images built successfully"
}

# Start services
start_services() {
    log_info "Starting services..."

    docker compose up -d

    log_success "Services started"
}

# Wait for health checks
wait_for_health() {
    log_info "Waiting for services to be healthy..."

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker compose ps | grep -q "unhealthy"; then
            log_warning "Some services are unhealthy, waiting... ($((attempt + 1))/$max_attempts)"
            sleep 2
            attempt=$((attempt + 1))
        else
            log_success "All services are healthy"
            return 0
        fi
    done

    log_error "Services failed to become healthy"
    docker compose ps
    exit 1
}

# Show service status
show_status() {
    log_info "Service Status:"
    docker compose ps

    log_info "\nService URLs:"
    echo "  API:        http://localhost:8000"
    echo "  API Docs:   http://localhost:8000/docs"
    echo "  Neo4j:      http://localhost:7475 (user: neo4j)"
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana:    http://localhost:3000 (user: admin)"
    echo ""
    echo "WebSocket:  ws://localhost:8000/ws"
}

# Main deployment flow
main() {
    log_info "=== APE 2026 Deployment Script ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Project Root: $PROJECT_ROOT"
    echo ""

    validate_environment
    check_prerequisites
    validate_production_secrets
    build_images
    start_services
    wait_for_health
    show_status

    log_success "\n=== Deployment Complete ==="
    log_info "To view logs: docker compose logs -f"
    log_info "To stop: docker compose down"
}

# Run
main

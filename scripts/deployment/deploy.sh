#!/bin/bash
# ============================================================================
# Production Deployment Script
# Week 7 Day 3 - APE 2026
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.production"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}APE 2026 - Production Deployment${NC}"
echo -e "${GREEN}============================================${NC}"

# ============================================================================
# Pre-flight Checks
# ============================================================================
echo -e "\n${YELLOW}[1/7] Running pre-flight checks...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Check if .env.production exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env.production not found${NC}"
    echo -e "${YELLOW}Copy .env.production.template to .env.production and configure it${NC}"
    exit 1
fi

# Verify critical environment variables
source "$ENV_FILE"
if [ -z "$CLAUDE_API_KEY" ] || [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${RED}Error: Critical environment variables not set${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pre-flight checks passed${NC}"

# ============================================================================
# Backup Current Data (if exists)
# ============================================================================
echo -e "\n${YELLOW}[2/7] Creating backup...${NC}"

BACKUP_DIR="${PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup databases
if docker ps | grep -q ape-timescaledb; then
    echo "Backing up TimescaleDB..."
    docker exec ape-timescaledb pg_dump -U ape ape_timeseries > "$BACKUP_DIR/timescaledb_backup.sql"
fi

if docker ps | grep -q ape-neo4j; then
    echo "Backing up Neo4j..."
    docker exec ape-neo4j neo4j-admin database dump neo4j --to-path=/backups
    docker cp ape-neo4j:/backups "$BACKUP_DIR/neo4j_backup"
fi

echo -e "${GREEN}✓ Backup created at $BACKUP_DIR${NC}"

# ============================================================================
# Pull Latest Images
# ============================================================================
echo -e "\n${YELLOW}[3/7] Pulling latest Docker images...${NC}"
cd "$PROJECT_ROOT"
docker-compose pull

echo -e "${GREEN}✓ Images updated${NC}"

# ============================================================================
# Build Application Image
# ============================================================================
echo -e "\n${YELLOW}[4/7] Building application image...${NC}"
docker-compose build --no-cache api

echo -e "${GREEN}✓ Application image built${NC}"

# ============================================================================
# Stop Old Containers
# ============================================================================
echo -e "\n${YELLOW}[5/7] Stopping old containers...${NC}"
docker-compose down

echo -e "${GREEN}✓ Old containers stopped${NC}"

# ============================================================================
# Start Services
# ============================================================================
echo -e "\n${YELLOW}[6/7] Starting services...${NC}"

# Start infrastructure first
docker-compose up -d timescaledb redis neo4j

# Wait for databases to be ready
echo "Waiting for databases to be healthy..."
sleep 30

# Start API
docker-compose up -d api

# Start monitoring
docker-compose up -d prometheus grafana

echo -e "${GREEN}✓ All services started${NC}"

# ============================================================================
# Health Checks
# ============================================================================
echo -e "\n${YELLOW}[7/7] Running health checks...${NC}"

sleep 10

# Check API health
if curl -f http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
    docker-compose logs api
    exit 1
fi

# Check databases
if docker exec ape-timescaledb pg_isready -U ape &> /dev/null; then
    echo -e "${GREEN}✓ TimescaleDB is healthy${NC}"
else
    echo -e "${RED}✗ TimescaleDB health check failed${NC}"
fi

if docker exec ape-redis redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✓ Redis is healthy${NC}"
else
    echo -e "${RED}✗ Redis health check failed${NC}"
fi

# ============================================================================
# Summary
# ============================================================================
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Services:"
echo "  API:        http://localhost:8000"
echo "  Docs:       http://localhost:8000/docs"
echo "  Grafana:    http://localhost:3000 (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo "  Neo4j:      http://localhost:7475 (neo4j/password)"
echo ""
echo "Logs: docker-compose logs -f api"
echo "Stop: docker-compose down"
echo ""
echo -e "${GREEN}Backup saved to: $BACKUP_DIR${NC}"

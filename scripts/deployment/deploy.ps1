# ============================================================================
# Production Deployment Script (Windows)
# Week 7 Day 3 - APE 2026
# ============================================================================

$ErrorActionPreference = "Stop"

# Colors
function Write-ColorOutput($ForegroundColor, $Message) {
    Write-Host $Message -ForegroundColor $ForegroundColor
}

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$EnvFile = Join-Path $ProjectRoot ".env.production"

Write-ColorOutput Green "============================================"
Write-ColorOutput Green "APE 2026 - Production Deployment"
Write-ColorOutput Green "============================================"

# ============================================================================
# Pre-flight Checks
# ============================================================================
Write-ColorOutput Yellow "`n[1/7] Running pre-flight checks..."

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-ColorOutput Red "Error: Docker is not installed"
    exit 1
}

# Check Docker Compose
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-ColorOutput Red "Error: Docker Compose is not installed"
    exit 1
}

# Check .env.production
if (-not (Test-Path $EnvFile)) {
    Write-ColorOutput Red "Error: .env.production not found"
    Write-ColorOutput Yellow "Copy .env.production.template to .env.production and configure it"
    exit 1
}

Write-ColorOutput Green "✓ Pre-flight checks passed"

# ============================================================================
# Backup Current Data
# ============================================================================
Write-ColorOutput Yellow "`n[2/7] Creating backup..."

$BackupDir = Join-Path $ProjectRoot "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

# Backup TimescaleDB
if (docker ps | Select-String "ape-timescaledb") {
    Write-Host "Backing up TimescaleDB..."
    docker exec ape-timescaledb pg_dump -U ape ape_timeseries > "$BackupDir\timescaledb_backup.sql"
}

# Backup Neo4j
if (docker ps | Select-String "ape-neo4j") {
    Write-Host "Backing up Neo4j..."
    docker exec ape-neo4j neo4j-admin database dump neo4j --to-path=/backups
    docker cp ape-neo4j:/backups "$BackupDir\neo4j_backup"
}

Write-ColorOutput Green "✓ Backup created at $BackupDir"

# ============================================================================
# Pull Latest Images
# ============================================================================
Write-ColorOutput Yellow "`n[3/7] Pulling latest Docker images..."
Set-Location $ProjectRoot
docker-compose pull

Write-ColorOutput Green "✓ Images updated"

# ============================================================================
# Build Application Image
# ============================================================================
Write-ColorOutput Yellow "`n[4/7] Building application image..."
docker-compose build --no-cache api

Write-ColorOutput Green "✓ Application image built"

# ============================================================================
# Stop Old Containers
# ============================================================================
Write-ColorOutput Yellow "`n[5/7] Stopping old containers..."
docker-compose down

Write-ColorOutput Green "✓ Old containers stopped"

# ============================================================================
# Start Services
# ============================================================================
Write-ColorOutput Yellow "`n[6/7] Starting services..."

# Start infrastructure
docker-compose up -d timescaledb redis neo4j

Write-Host "Waiting for databases to be healthy..."
Start-Sleep -Seconds 30

# Start API
docker-compose up -d api

# Start monitoring
docker-compose up -d prometheus grafana

Write-ColorOutput Green "✓ All services started"

# ============================================================================
# Health Checks
# ============================================================================
Write-ColorOutput Yellow "`n[7/7] Running health checks..."

Start-Sleep -Seconds 10

# Check API
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-ColorOutput Green "✓ API is healthy"
    }
} catch {
    Write-ColorOutput Red "✗ API health check failed"
    docker-compose logs api
    exit 1
}

# Check TimescaleDB
$pgReady = docker exec ape-timescaledb pg_isready -U ape
if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput Green "✓ TimescaleDB is healthy"
} else {
    Write-ColorOutput Red "✗ TimescaleDB health check failed"
}

# Check Redis
$redisReady = docker exec ape-redis redis-cli ping
if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput Green "✓ Redis is healthy"
} else {
    Write-ColorOutput Red "✗ Redis health check failed"
}

# ============================================================================
# Summary
# ============================================================================
Write-ColorOutput Green "`n============================================"
Write-ColorOutput Green "Deployment Complete!"
Write-ColorOutput Green "============================================"
Write-Host ""
Write-Host "Services:"
Write-Host "  API:        http://localhost:8000"
Write-Host "  Docs:       http://localhost:8000/docs"
Write-Host "  Grafana:    http://localhost:3000 (admin/admin)"
Write-Host "  Prometheus: http://localhost:9090"
Write-Host "  Neo4j:      http://localhost:7475 (neo4j/password)"
Write-Host ""
Write-Host "Logs: docker-compose logs -f api"
Write-Host "Stop: docker-compose down"
Write-Host ""
Write-ColorOutput Green "Backup saved to: $BackupDir"

# ============================================================================
# APE 2026 - Production Deployment Script (PowerShell)
# Week 9 Day 2
#
# Usage:
#   .\scripts\deploy.ps1 [-Environment <env>]
#
# Parameters:
#   -Environment: dev, staging, or production (default: dev)
#
# Example:
#   .\scripts\deploy.ps1 -Environment production
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "staging", "production")]
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$EnvFile = Join-Path $ProjectRoot ".env"

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check Docker
    try {
        $null = docker --version
    } catch {
        Write-Error "Docker is not installed"
        exit 1
    }

    # Check Docker Compose
    try {
        $null = docker compose version
    } catch {
        Write-Error "Docker Compose is not installed"
        exit 1
    }

    # Check .env file
    if (-not (Test-Path $EnvFile)) {
        Write-Warning ".env file not found"
        Write-Info "Creating from .env.example..."
        Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvFile
        Write-Warning "Please configure .env file before continuing"
        exit 1
    }

    Write-Success "Prerequisites check passed"
}

# Validate production secrets
function Test-ProductionSecrets {
    if ($Environment -eq "production") {
        Write-Info "Validating production secrets..."

        # Load .env file
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.*)$') {
                Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2]
            }
        }

        $errors = 0

        if ($env:SECRET_KEY -eq "dev_secret_key_change_in_production") {
            Write-Error "SECRET_KEY must be changed in production"
            $errors++
        }

        if ($env:SECRET_KEY.Length -lt 32) {
            Write-Error "SECRET_KEY must be at least 32 characters"
            $errors++
        }

        if ($env:POSTGRES_PASSWORD -eq "ape_timescale_password_CHANGE_ME") {
            Write-Error "POSTGRES_PASSWORD must be changed in production"
            $errors++
        }

        if ($env:NEO4J_PASSWORD -eq "ape_neo4j_password_CHANGE_ME") {
            Write-Error "NEO4J_PASSWORD must be changed in production"
            $errors++
        }

        if ($errors -gt 0) {
            Write-Error "Production secrets validation failed. Please fix errors in .env"
            exit 1
        }

        Write-Success "Production secrets validation passed"
    }
}

# Build Docker images
function Build-Images {
    Write-Info "Building Docker images..."

    Set-Location $ProjectRoot
    docker compose build --build-arg ENVIRONMENT=$Environment api

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed"
        exit 1
    }

    Write-Success "Docker images built successfully"
}

# Start services
function Start-Services {
    Write-Info "Starting services..."

    Set-Location $ProjectRoot
    docker compose up -d

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start services"
        exit 1
    }

    Write-Success "Services started"
}

# Wait for health checks
function Wait-ForHealth {
    Write-Info "Waiting for services to be healthy..."

    $maxAttempts = 30
    $attempt = 0

    while ($attempt -lt $maxAttempts) {
        $unhealthy = docker compose ps | Select-String "unhealthy"

        if ($unhealthy) {
            Write-Warning "Some services are unhealthy, waiting... ($($attempt + 1)/$maxAttempts)"
            Start-Sleep -Seconds 2
            $attempt++
        } else {
            Write-Success "All services are healthy"
            return
        }
    }

    Write-Error "Services failed to become healthy"
    docker compose ps
    exit 1
}

# Show service status
function Show-Status {
    Write-Info "`nService Status:"
    docker compose ps

    Write-Info "`nService URLs:"
    Write-Host "  API:        http://localhost:8000"
    Write-Host "  API Docs:   http://localhost:8000/docs"
    Write-Host "  Neo4j:      http://localhost:7475 (user: neo4j)"
    Write-Host "  Prometheus: http://localhost:9090"
    Write-Host "  Grafana:    http://localhost:3000 (user: admin)"
    Write-Host ""
    Write-Host "  WebSocket:  ws://localhost:8000/ws"
}

# Main deployment flow
function Main {
    Write-Info "=== APE 2026 Deployment Script ==="
    Write-Info "Environment: $Environment"
    Write-Info "Project Root: $ProjectRoot"
    Write-Host ""

    Test-Prerequisites
    Test-ProductionSecrets
    Build-Images
    Start-Services
    Wait-ForHealth
    Show-Status

    Write-Success "`n=== Deployment Complete ==="
    Write-Info "To view logs: docker compose logs -f"
    Write-Info "To stop: docker compose down"
}

# Run
Main

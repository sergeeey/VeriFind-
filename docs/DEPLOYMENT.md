# Production Deployment Guide

**Status:** ✅ Implemented (Week 9 Day 2)

---

## Overview

This guide covers deploying APE 2026 API to production using Docker, Docker Compose, and CI/CD pipelines.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Configuration](#environment-configuration)
4. [Docker Deployment](#docker-deployment)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Health Checks](#health-checks)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Scaling](#scaling)
10. [Backup & Recovery](#backup--recovery)

---

## Prerequisites

### Required Software

- **Docker:** 24.0+ (with BuildKit enabled)
- **Docker Compose:** 2.20+
- **Git:** 2.30+
- **OpenSSL:** For generating secrets

### System Requirements

**Development:**
- CPU: 2 cores
- RAM: 8 GB
- Disk: 20 GB

**Production:**
- CPU: 4+ cores
- RAM: 16+ GB
- Disk: 100+ GB (SSD recommended)
- Network: Static IP recommended

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/ape-2026.git
cd ape-2026
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Generate secure SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env

# Edit .env with your configuration
nano .env
```

### 3. Deploy

**Linux/macOS:**
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh production
```

**Windows (PowerShell):**
```powershell
.\scripts\deploy.ps1 -Environment production
```

### 4. Verify Deployment

```bash
# Check service status
docker compose ps

# Test API health
curl http://localhost:8000/health

# View logs
docker compose logs -f api
```

---

## Environment Configuration

### Required Environment Variables

#### Application Settings

```bash
# REQUIRED
ENVIRONMENT=production              # development, staging, or production
SECRET_KEY=your_64_char_secret     # Generate with: openssl rand -hex 32

# Application
APP_NAME=APE-2026-API
APP_VERSION=1.0.0
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                     # json or text
```

#### Security Settings

```bash
# REQUIRED in production
API_KEY=your_production_api_key     # Primary API key

# Production API keys (format: API_KEY_<NAME>=<key>:<rate_limit>)
API_KEY_PROD=prod_key_abc123:1000
API_KEY_STAGING=staging_key_xyz:500

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_HOUR=100
RATE_LIMIT_BURST_PER_MINUTE=10
RATE_LIMIT_WINDOW_HOURS=1
DEFAULT_RATE_LIMIT=100
```

#### Database Configuration

```bash
# TimescaleDB (REQUIRED)
DATABASE_HOST=timescaledb
DATABASE_PORT=5432
DATABASE_NAME=ape_timeseries
DATABASE_USER=ape
DATABASE_PASSWORD=strong_password_here  # CHANGE IN PRODUCTION

# Neo4j (REQUIRED)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=strong_password_here     # CHANGE IN PRODUCTION

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
```

#### External APIs (Optional)

```bash
# AI Models
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key

# Market Data
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
POLYGON_API_KEY=your_polygon_key
FRED_API_KEY=your_fred_key
```

#### Sandbox Configuration

```bash
SANDBOX_TIMEOUT_SECONDS=30
SANDBOX_MAX_MEMORY_MB=512
SANDBOX_ENABLE_NETWORK=false
```

### Generate Secure Secrets

```bash
# SECRET_KEY (64 hex characters = 32 bytes)
openssl rand -hex 32

# API Key (32 hex characters)
openssl rand -hex 16

# Database Password (32 alphanumeric)
openssl rand -base64 24
```

---

## Docker Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Docker Network                       │
│  ┌──────────┐  ┌────────────┐  ┌────────┐  ┌────────────┐  │
│  │   API    │──│ TimescaleDB│  │ Neo4j  │  │   Redis    │  │
│  │  :8000   │  │   :5432    │  │ :7687  │  │   :6379    │  │
│  └────┬─────┘  └────────────┘  └────────┘  └────────────┘  │
│       │                                                      │
│  ┌────▼─────────┐  ┌───────────┐                           │
│  │  Prometheus  │  │  Grafana  │                           │
│  │    :9090     │  │   :3000   │                           │
│  └──────────────┘  └───────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

### Build Docker Image

```bash
# Development build
docker compose build

# Production build with no cache
docker compose build --no-cache --build-arg ENVIRONMENT=production api

# Build specific stage
docker build -t ape-api:dev --target development .
docker build -t ape-api:prod --target production .
```

### Start Services

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d api

# Start with rebuild
docker compose up -d --build

# View logs
docker compose logs -f
docker compose logs -f api

# Follow logs for specific service
docker compose logs -f timescaledb
```

### Stop Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (⚠️ DATA LOSS)
docker compose down -v

# Stop specific service
docker compose stop api
```

### Service Management

```bash
# Restart service
docker compose restart api

# Scale service (multiple instances)
docker compose up -d --scale api=3

# View service status
docker compose ps

# Execute command in container
docker compose exec api bash
docker compose exec timescaledb psql -U ape -d ape_timeseries
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**File:** `.github/workflows/ci-cd.yml`

**Triggers:**
- Push to `main`/`master` → Deploy to production
- Push to `develop` → Deploy to staging
- Pull Request → Run tests only

**Jobs:**

1. **Test** - Run unit and integration tests
2. **Lint** - Code quality checks (Black, Flake8, MyPy)
3. **Security** - Vulnerability scan (Safety, Bandit)
4. **Build** - Build and push Docker image
5. **Deploy** - Deploy to environment

### Setup GitHub Actions

1. **Add Repository Secrets:**

   Go to: Settings → Secrets → Actions → New repository secret

   ```
   ANTHROPIC_API_KEY
   OPENAI_API_KEY
   POSTGRES_PASSWORD
   NEO4J_PASSWORD
   SECRET_KEY
   ```

2. **Configure Environments:**

   - `staging` - Auto-deploy from `develop` branch
   - `production` - Manual approval required

3. **Enable GitHub Packages:**

   - Docker images pushed to `ghcr.io/your-org/ape-api`

### Manual Deployment

**Trigger from GitHub UI:**
1. Go to Actions tab
2. Select "CI/CD Pipeline"
3. Click "Run workflow"
4. Select branch and environment

**Trigger from CLI:**
```bash
gh workflow run ci-cd.yml -f environment=production
```

---

## Health Checks

### API Health Endpoint

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-08T14:30:00.000Z",
  "version": "1.0.0",
  "components": {
    "api": "healthy",
    "orchestrator": "healthy",
    "timescaledb": "healthy",
    "neo4j": "healthy",
    "chromadb": "healthy"
  }
}
```

### Docker Health Checks

```bash
# View container health
docker compose ps

# Inspect specific container health
docker inspect ape-api --format='{{.State.Health.Status}}'

# View health check logs
docker inspect ape-api --format='{{json .State.Health}}' | jq
```

### Service-Specific Health Checks

**TimescaleDB:**
```bash
docker compose exec timescaledb pg_isready -U ape
```

**Neo4j:**
```bash
curl http://localhost:7475/db/neo4j/cluster/available
```

**Redis:**
```bash
docker compose exec redis redis-cli ping
```

---

## Monitoring

### Prometheus

**URL:** http://localhost:9090

**Metrics Collected:**
- API request rate, latency, errors
- Database connections, query time
- Cache hit rate
- System resources (CPU, memory, disk)

**Example Queries:**
```promql
# API request rate
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Grafana

**URL:** http://localhost:3000
**Default Credentials:** admin / admin (change on first login)

**Dashboards:**
- API Performance
- Database Metrics
- System Resources
- Error Rates

**Import Dashboards:**
1. Go to Dashboards → Import
2. Upload JSON from `config/grafana/dashboards/`

### Log Aggregation

**View Logs:**
```bash
# All services
docker compose logs -f

# Specific service with tail
docker compose logs -f --tail=100 api

# Filter by log level (production JSON format)
docker compose logs api | jq 'select(.level == "ERROR")'

# Search by request ID
docker compose logs api | jq 'select(.request_id == "abc-123")'
```

**Log Files (inside container):**
- API logs: `/app/logs/api.log`
- Structured JSON logs in production

---

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

**Symptoms:**
```
Error response from daemon: driver failed programming external connectivity
```

**Solution:**
```bash
# Port already in use - change port in docker-compose.yml
# Or kill process using port
lsof -ti:8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000   # Windows
```

#### 2. Database Connection Failed

**Symptoms:**
```
could not connect to server: Connection refused
```

**Solution:**
```bash
# Check if database is running
docker compose ps timescaledb

# View database logs
docker compose logs timescaledb

# Restart database
docker compose restart timescaledb

# Check connection manually
docker compose exec api python -c "from src.storage.timescale_store import TimescaleDBStore; store = TimescaleDBStore(); print('Connected')"
```

#### 3. Out of Memory

**Symptoms:**
```
container killed by OOM killer
```

**Solution:**
```bash
# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory

# Reduce memory limits in docker-compose.yml
# api:
#   deploy:
#     resources:
#       limits:
#         memory: 2G
```

#### 4. Slow Performance

**Check:**
```bash
# System resources
docker stats

# Database connections
docker compose exec timescaledb psql -U ape -c "SELECT count(*) FROM pg_stat_activity;"

# Cache hit rate
docker compose exec redis redis-cli info stats | grep hits
```

### Debug Mode

```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
docker compose restart api

# Run container interactively
docker compose run --rm api bash

# Attach to running container
docker compose exec api bash
```

---

## Scaling

### Horizontal Scaling (Multiple API Instances)

```bash
# Scale to 3 API instances
docker compose up -d --scale api=3

# Add load balancer (nginx)
docker compose -f docker-compose.yml -f docker-compose.lb.yml up -d
```

**Load Balancer Config (`docker-compose.lb.yml`):**
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
```

### Vertical Scaling (More Resources)

```yaml
# docker-compose.override.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Database Scaling

**TimescaleDB:**
- Enable connection pooling (PgBouncer)
- Read replicas for queries
- Partitioning for large tables

**Neo4j:**
- Cluster mode (Enterprise)
- Read replicas
- Causal clustering

---

## Backup & Recovery

### Automated Backups

**Create Backup Script (`scripts/backup.sh`):**
```bash
#!/bin/bash
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup TimescaleDB
docker compose exec -T timescaledb pg_dump -U ape ape_timeseries > "$BACKUP_DIR/timescaledb.sql"

# Backup Neo4j
docker compose exec -T neo4j neo4j-admin dump --database=neo4j --to=/tmp/neo4j-backup.dump
docker cp ape-neo4j:/tmp/neo4j-backup.dump "$BACKUP_DIR/neo4j-backup.dump"

echo "Backup complete: $BACKUP_DIR"
```

### Restore from Backup

**TimescaleDB:**
```bash
cat backups/20260208_120000/timescaledb.sql | \
  docker compose exec -T timescaledb psql -U ape ape_timeseries
```

**Neo4j:**
```bash
docker compose stop neo4j
docker compose run --rm neo4j neo4j-admin load --from=/backups/neo4j-backup.dump --database=neo4j --force
docker compose start neo4j
```

### Disaster Recovery

1. **Regular Backups:** Automated daily backups to S3/Azure Blob
2. **Off-site Storage:** Store backups in different region
3. **Test Restores:** Monthly restore tests
4. **Documentation:** Runbook for disaster recovery

---

## Production Checklist

### Pre-Deployment

- [ ] All environment variables configured in `.env`
- [ ] `SECRET_KEY` changed from default (32+ characters)
- [ ] Database passwords changed from defaults
- [ ] API keys generated and stored securely
- [ ] CORS origins configured for production domain
- [ ] Rate limits adjusted for expected load
- [ ] Health checks passing locally
- [ ] Tests passing (`pytest tests/`)
- [ ] Security scan clean (`safety check`)

### Post-Deployment

- [ ] Services healthy (`docker compose ps`)
- [ ] API accessible (`curl /health`)
- [ ] WebSocket functional (`wscat -c ws://...`)
- [ ] Monitoring dashboards configured
- [ ] Logs flowing to aggregation system
- [ ] Backup script tested
- [ ] SSL/TLS certificates configured (if HTTPS)
- [ ] DNS records updated
- [ ] Team notified of deployment

### Ongoing Maintenance

- [ ] Monitor error rates (< 1%)
- [ ] Monitor API latency (p95 < 500ms)
- [ ] Review logs daily
- [ ] Update dependencies monthly
- [ ] Security patches applied within 7 days
- [ ] Backups verified weekly
- [ ] Capacity planning quarterly

---

## Security Considerations

### Production Requirements

1. **HTTPS Only:** Use reverse proxy (nginx/Caddy) with SSL
2. **Secrets Management:** Use environment variables, never commit
3. **Firewall:** Restrict ports (only 443/80 public)
4. **Rate Limiting:** Prevent abuse
5. **Monitoring:** Alert on anomalies
6. **Updates:** Regular security patches

### SSL/TLS Setup (nginx example)

```nginx
server {
    listen 443 ssl http2;
    server_name api.ape-2026.example.com;

    ssl_certificate /etc/letsencrypt/live/api.ape-2026.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.ape-2026.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

**Last Updated:** 2026-02-08
**Version:** 1.0.0
**Status:** Production Ready

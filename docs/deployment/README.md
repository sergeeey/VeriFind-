# Production Deployment Guide
**Week 7 Day 3 - APE 2026**

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

**Minimum (Development):**
- 4 GB RAM
- 4 CPU cores
- 20 GB disk space
- Docker 20+ and Docker Compose 2+

**Recommended (Production - Tier 2):**
- 8 GB RAM
- 8 CPU cores
- 100 GB SSD
- Docker 24+ and Docker Compose 2.20+

**Large Production (Tier 3-4):**
- 16-32+ GB RAM
- 16-32+ CPU cores
- 500 GB SSD
- Kubernetes 1.27+

### Software

- **Docker**: v24.0+
- **Docker Compose**: v2.20+
- **Git**: v2.30+
- **Optional**: Kubernetes v1.27+, kubectl, helm

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ape-2026.git
cd ape-2026
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.production.template .env.production

# Edit with your values
nano .env.production

# Required variables:
# - CLAUDE_API_KEY
# - DEEPSEEK_API_KEY
# - POSTGRES_PASSWORD
# - NEO4J_PASSWORD
```

### 3. Deploy

**Linux/macOS:**
```bash
chmod +x scripts/deployment/deploy.sh
./scripts/deployment/deploy.sh
```

**Windows:**
```powershell
.\scripts\deployment\deploy.ps1
```

### 4. Verify

```bash
# Check all services are healthy
docker-compose ps

# Test API
curl http://localhost:8000/health

# View logs
docker-compose logs -f api
```

---

## Docker Deployment

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Nginx (Port 80)                   │
│              Load Balancer & Reverse Proxy          │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
    ┌────▼────┐                 ┌────▼────┐
    │  API-1  │                 │  API-2  │
    │ Port    │                 │ Port    │
    │ 8000    │                 │ 8001    │
    └────┬────┘                 └────┬────┘
         │                           │
         └─────────────┬─────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
  ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
  │TimescaleDB│    │ Neo4j  │    │ Redis  │
  │  Port    │    │ Port   │    │ Port   │
  │  5432    │    │ 7687   │    │ 6379   │
  └──────────┘    └─────────┘    └─────────┘
```

### Commands

**Start services:**
```bash
docker-compose up -d
```

**Scale API:**
```bash
docker-compose up -d --scale api=4
```

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

**Stop services:**
```bash
docker-compose down
```

**Rebuild:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Verify
kubectl version --client
```

### Deploy to Cluster

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply configurations
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/timescaledb-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/neo4j-statefulset.yaml

# Verify
kubectl get pods -n ape-2026
kubectl get services -n ape-2026
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment api --replicas=5 -n ape-2026

# Auto-scaling (already configured via HPA)
kubectl get hpa -n ape-2026

# Describe HPA
kubectl describe hpa api-hpa -n ape-2026
```

### Monitoring

```bash
# Get logs
kubectl logs -f deployment/api -n ape-2026

# Execute commands in pod
kubectl exec -it api-xxx -n ape-2026 -- /bin/bash

# Port forward for local access
kubectl port-forward service/api-service 8000:8000 -n ape-2026
```

---

## Configuration

### Environment Variables

See `.env.production.template` for full list.

**Critical variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_API_KEY` | Anthropic API key | Required |
| `DEEPSEEK_API_KEY` | DeepSeek API key | Required |
| `POSTGRES_PASSWORD` | Database password | Required |
| `NEO4J_PASSWORD` | Neo4j password | Required |
| `SECRET_KEY` | API secret key | Generated |
| `LOG_LEVEL` | Logging level | `info` |
| `API_WORKERS` | Uvicorn workers | `4` |

### Database Initialization

**TimescaleDB:**
```sql
-- Connect to database
psql -h localhost -p 5432 -U ape -d ape_timeseries

-- Verify TimescaleDB extension
SELECT * FROM pg_extension WHERE extname = 'timescaledb';

-- Check hypertables
SELECT * FROM timescaledb_information.hypertables;
```

**Neo4j:**
```bash
# Access browser UI
http://localhost:7475

# Run Cypher queries
MATCH (n) RETURN count(n);
```

---

## Monitoring

### Grafana Dashboards

Access: http://localhost:3000
Login: admin/admin (change on first login)

**Pre-configured dashboards:**
1. **API Overview**: Request rate, latency, errors
2. **Database Performance**: Query time, connections, cache hits
3. **System Resources**: CPU, memory, disk I/O
4. **Business Metrics**: Queries processed, fact verification rate

### Prometheus Metrics

Access: http://localhost:9090

**Key queries:**

```promql
# Request rate (last 5 min)
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# CPU usage
rate(process_cpu_seconds_total[5m])

# Memory usage
process_resident_memory_bytes
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "version": "1.0.0", "uptime": 12345}

# Database health
docker exec ape-timescaledb pg_isready -U ape

# Redis health
docker exec ape-redis redis-cli ping
```

---

## Troubleshooting

### Common Issues

**1. API won't start**

```bash
# Check logs
docker-compose logs api

# Common causes:
# - Missing environment variables
# - Database not ready
# - Port already in use

# Solution:
docker-compose down
docker-compose up -d timescaledb redis neo4j
# Wait 30 seconds
docker-compose up -d api
```

**2. Database connection failed**

```bash
# Verify database is running
docker-compose ps timescaledb

# Check connectivity
docker exec ape-api ping timescaledb

# Verify credentials
docker exec ape-timescaledb psql -U ape -d ape_timeseries -c "SELECT 1;"
```

**3. High memory usage**

```bash
# Check container stats
docker stats

# Adjust memory limits in docker-compose.yml:
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
```

**4. Slow queries**

```sql
-- TimescaleDB: Check slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Neo4j: Enable query logging
// In neo4j.conf
dbms.logs.query.enabled=INFO
dbms.logs.query.threshold=1s
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug

# Restart API
docker-compose restart api

# View verbose logs
docker-compose logs -f api
```

### Restore from Backup

```bash
# List backups
ls -lh backups/

# Restore TimescaleDB
docker exec -i ape-timescaledb psql -U ape ape_timeseries < backups/20240101_120000/timescaledb_backup.sql

# Restore Neo4j
docker cp backups/20240101_120000/neo4j_backup ape-neo4j:/backups
docker exec ape-neo4j neo4j-admin database load neo4j --from-path=/backups
```

---

## Maintenance

### Backups

**Automated (cron):**
```bash
# Add to crontab
0 2 * * * /app/scripts/backup.sh
```

**Manual:**
```bash
./scripts/backup.sh
```

### Updates

**Update Docker images:**
```bash
docker-compose pull
docker-compose up -d
```

**Update application code:**
```bash
git pull origin main
docker-compose build --no-cache api
docker-compose up -d api
```

### Database Maintenance

**TimescaleDB vacuum:**
```sql
-- Full vacuum (requires downtime)
VACUUM FULL;

-- Analyze statistics
ANALYZE;

-- Reindex
REINDEX DATABASE ape_timeseries;
```

**Neo4j compaction:**
```bash
docker exec ape-neo4j neo4j-admin database compact neo4j
```

### Log Rotation

```bash
# Configure in docker-compose.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
```

---

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong API keys
- [ ] Enable HTTPS/TLS
- [ ] Restrict network access (firewall)
- [ ] Regular security updates
- [ ] Audit logs enabled
- [ ] Secrets stored securely (not in git)
- [ ] Rate limiting enabled
- [ ] Database backups encrypted

---

## Support

**Documentation:**
- [Scaling Strategy](./SCALING_STRATEGY.md)
- [API Documentation](http://localhost:8000/docs)

**Logs:**
- API: `./logs/api.log`
- Docker: `docker-compose logs`

**Community:**
- GitHub Issues
- Discord/Slack channel

---

**Last Updated:** Week 7 Day 3
**Version:** 1.0.0

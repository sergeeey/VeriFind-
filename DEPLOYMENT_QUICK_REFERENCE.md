# 🚀 Deployment Quick Reference
**APE 2026 - Production Deployment Cheat Sheet**

---

## Quick Start (3 Steps)

```bash
# 1. Configure
cp .env.production.template .env.production
nano .env.production  # Add API keys and passwords

# 2. Deploy
./scripts/deployment/deploy.sh  # Linux/macOS
# OR
.\scripts\deployment\deploy.ps1  # Windows

# 3. Verify
curl http://localhost:8000/health
```

---

## Common Commands

### Docker Compose

```bash
# Start all services
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# Scale API to 4 instances
docker-compose up -d --scale api=4

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f api

# Restart service
docker-compose restart api

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View service status
docker-compose ps

# Execute command in container
docker-compose exec api bash
```

### Kubernetes

```bash
# Deploy all manifests
kubectl apply -f k8s/

# Get all resources
kubectl get all -n ape-2026

# Scale deployment
kubectl scale deployment api --replicas=5 -n ape-2026

# View logs
kubectl logs -f deployment/api -n ape-2026

# Port forward
kubectl port-forward service/api-service 8000:8000 -n ape-2026

# Delete all resources
kubectl delete namespace ape-2026
```

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8000 | API Key from .env |
| **API Docs** | http://localhost:8000/docs | - |
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Neo4j Browser** | http://localhost:7475 | neo4j/password |

---

## Health Checks

```bash
# API
curl http://localhost:8000/health

# TimescaleDB
docker exec ape-timescaledb pg_isready -U ape

# Redis
docker exec ape-redis redis-cli ping

# Neo4j
curl http://localhost:7475/db/data/
```

---

## Database Access

### TimescaleDB

```bash
# Connect to database
docker exec -it ape-timescaledb psql -U ape -d ape_timeseries

# Backup
docker exec ape-timescaledb pg_dump -U ape ape_timeseries > backup.sql

# Restore
docker exec -i ape-timescaledb psql -U ape ape_timeseries < backup.sql
```

### Neo4j

```bash
# Execute Cypher query
docker exec ape-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n);"

# Backup
docker exec ape-neo4j neo4j-admin database dump neo4j --to-path=/backups

# Restore
docker exec ape-neo4j neo4j-admin database load neo4j --from-path=/backups
```

### Redis

```bash
# Connect to Redis CLI
docker exec -it ape-redis redis-cli

# Get all keys
docker exec ape-redis redis-cli KEYS "*"

# Flush all data (DANGEROUS!)
docker exec ape-redis redis-cli FLUSHALL
```

---

## Monitoring

### Prometheus Queries

```promql
# Request rate (last 5 min)
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Memory usage
process_resident_memory_bytes / 1024 / 1024
```

### Grafana

1. Open http://localhost:3000
2. Login: admin/admin
3. Navigate to Dashboards → APE 2026

---

## Troubleshooting

### API won't start

```bash
# Check logs
docker-compose logs api

# Common fixes:
docker-compose down
docker-compose up -d timescaledb redis neo4j
sleep 30
docker-compose up -d api
```

### Database connection failed

```bash
# Verify database is running
docker-compose ps timescaledb

# Test connectivity from API container
docker-compose exec api ping timescaledb

# Check credentials
grep POSTGRES_PASSWORD .env.production
```

### High memory usage

```bash
# Check container stats
docker stats

# Restart specific service
docker-compose restart api
```

### Port already in use

```bash
# Find process using port 8000
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>
```

---

## Maintenance

### Backup

```bash
# Manual backup
./scripts/backup.sh

# Verify backup
ls -lh backups/
```

### Update

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Full cleanup (DANGEROUS!)
docker system prune -a --volumes
```

---

## Environment Variables

**Required:**
- `CLAUDE_API_KEY` - Anthropic API key
- `DEEPSEEK_API_KEY` - DeepSeek API key
- `POSTGRES_PASSWORD` - Database password
- `NEO4J_PASSWORD` - Neo4j password

**Optional:**
- `API_WORKERS` - Number of workers (default: 4)
- `LOG_LEVEL` - Logging level (default: info)
- `RATE_LIMIT_ENABLED` - Enable rate limiting (default: true)

See `.env.production.template` for full list.

---

## Performance Tuning

### API

```yaml
# In docker-compose.yml
services:
  api:
    environment:
      - API_WORKERS=8  # Increase workers
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### TimescaleDB

```sql
-- Increase shared buffers
ALTER SYSTEM SET shared_buffers = '4GB';
SELECT pg_reload_conf();

-- Enable compression
ALTER TABLE market_data_ohlcv SET (timescaledb.compress);
```

### Redis

```conf
# In docker-compose.yml
command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

---

## Security

### Change Default Passwords

```bash
# Edit .env.production
POSTGRES_PASSWORD=your-strong-password-here
NEO4J_PASSWORD=your-strong-password-here
GRAFANA_PASSWORD=your-strong-password-here
SECRET_KEY=$(openssl rand -hex 32)
```

### Enable HTTPS

1. Get SSL certificates (Let's Encrypt)
2. Update nginx configuration
3. Set `SSL_ENABLED=true` in .env

---

## Scaling

### Horizontal (API)

```bash
# Docker Compose
docker-compose up -d --scale api=4

# Kubernetes
kubectl scale deployment api --replicas=5 -n ape-2026
```

### Vertical (Databases)

```yaml
# Increase resources in docker-compose.yml
services:
  timescaledb:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

---

## Support

**Documentation:**
- Full Guide: `docs/deployment/README.md`
- Scaling: `docs/deployment/SCALING_STRATEGY.md`

**Logs:**
- API: `docker-compose logs -f api`
- All: `docker-compose logs -f`

**Health:**
- API: http://localhost:8000/health
- Grafana: http://localhost:3000

---

**Quick Reference Version:** 1.0.0
**Last Updated:** Week 7 Day 3

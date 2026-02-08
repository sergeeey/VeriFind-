# Scaling Strategy
**Week 7 Day 3 - Production Deployment Configuration**

## Overview

APE 2026 is designed to scale horizontally for API services and vertically for databases. This document outlines scaling strategies for different load profiles.

---

## Load Profiles

### Tier 1: Development (1-10 queries/hour)
- **API**: 1 container, 1 worker
- **TimescaleDB**: 512MB RAM, 2 CPUs
- **Neo4j**: 1GB heap, 1GB pagecache
- **Redis**: 128MB
- **Total**: ~4GB RAM, 4 CPUs

### Tier 2: Small Production (100 queries/hour)
- **API**: 2 containers, 2 workers each
- **TimescaleDB**: 2GB RAM, 4 CPUs
- **Neo4j**: 2GB heap, 2GB pagecache
- **Redis**: 512MB
- **Total**: ~8GB RAM, 8 CPUs

### Tier 3: Medium Production (1000 queries/hour)
- **API**: 4 containers, 4 workers each
- **TimescaleDB**: 4GB RAM, 8 CPUs
- **Neo4j**: 4GB heap, 4GB pagecache
- **Redis**: 1GB
- **Total**: ~16GB RAM, 16 CPUs

### Tier 4: Large Production (10000+ queries/hour)
- **API**: 8+ containers, 4 workers each
- **TimescaleDB**: 8GB+ RAM, 16+ CPUs (consider sharding)
- **Neo4j**: 8GB+ heap, 8GB+ pagecache
- **Redis**: 2GB+ (consider Redis Cluster)
- **Total**: 32GB+ RAM, 32+ CPUs

---

## Horizontal Scaling (API Service)

### Docker Compose Scaling

```bash
# Scale API to 4 instances
docker-compose up -d --scale api=4

# Behind load balancer (nginx)
# Requests distributed round-robin
```

### Kubernetes Scaling

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ape-api
spec:
  replicas: 4  # Scale to 4 pods
  template:
    spec:
      containers:
      - name: api
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

### Auto-Scaling (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ape-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ape-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Vertical Scaling (Databases)

### TimescaleDB Scaling

**Memory Configuration:**
```sql
-- Increase shared_buffers (25% of RAM)
ALTER SYSTEM SET shared_buffers = '4GB';

-- Increase effective_cache_size (50% of RAM)
ALTER SYSTEM SET effective_cache_size = '8GB';

-- Increase work_mem for complex queries
ALTER SYSTEM SET work_mem = '64MB';

-- Restart required
SELECT pg_reload_conf();
```

**Hypertable Partitioning:**
```sql
-- Partition by time (1 day chunks)
SELECT create_hypertable(
    'market_data_ohlcv',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day'
);

-- Partition by symbol + time
SELECT create_hypertable(
    'market_data_ohlcv',
    'timestamp',
    partitioning_column => 'symbol',
    number_partitions => 4
);
```

**Compression:**
```sql
-- Enable compression on old data
ALTER TABLE market_data_ohlcv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Auto-compress data older than 7 days
SELECT add_compression_policy('market_data_ohlcv', INTERVAL '7 days');
```

### Neo4j Scaling

**Memory Configuration:**
```properties
# Heap size (25% of RAM, max 32GB)
dbms.memory.heap.initial_size=4g
dbms.memory.heap.max_size=8g

# Pagecache (50% of RAM)
dbms.memory.pagecache.size=8g

# Transaction state
dbms.memory.transaction.total.max=2g
```

**Indexing for Performance:**
```cypher
// Create indexes on frequently queried properties
CREATE INDEX fact_id_index FOR (f:Fact) ON (f.fact_id);
CREATE INDEX query_id_index FOR (q:Query) ON (q.query_id);
CREATE INDEX timestamp_index FOR (e:Episode) ON (e.timestamp);

// Composite indexes
CREATE INDEX fact_query_composite FOR (f:Fact) ON (f.query_id, f.status);
```

**Clustering (Enterprise):**
```properties
# Causal clustering for read replicas
dbms.mode=CORE
causal_clustering.minimum_core_cluster_size_at_formation=3
causal_clustering.initial_discovery_members=neo4j-1:5000,neo4j-2:5000,neo4j-3:5000
```

### Redis Scaling

**Single Instance Optimization:**
```conf
# Increase max memory
maxmemory 2gb

# Eviction policy
maxmemory-policy allkeys-lru

# AOF persistence for durability
appendonly yes
appendfsync everysec
```

**Redis Cluster (High Availability):**
```yaml
# 3 masters + 3 replicas
services:
  redis-master-1:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes

  redis-master-2:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes

  redis-master-3:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes
```

---

## Load Balancing

### Nginx Configuration

```nginx
upstream api_backend {
    least_conn;  # Use least connections algorithm
    server api-1:8000 max_fails=3 fail_timeout=30s;
    server api-2:8000 max_fails=3 fail_timeout=30s;
    server api-3:8000 max_fails=3 fail_timeout=30s;
    server api-4:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Monitoring & Metrics

### Key Metrics to Monitor

**API Service:**
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (%)
- CPU usage (%)
- Memory usage (MB)
- Active connections

**TimescaleDB:**
- Query latency (ms)
- Active connections
- Cache hit rate (%)
- Disk I/O (IOPS)
- Table bloat

**Neo4j:**
- Query execution time (ms)
- Cache hit rate (%)
- Transaction throughput (tx/s)
- Page cache evictions

**Redis:**
- Hit rate (%)
- Evicted keys/s
- Connected clients
- Memory usage

### Prometheus Queries

```promql
# API request rate
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Database connection pool usage
db_connection_pool_active / db_connection_pool_max
```

---

## Scaling Decision Matrix

| Symptom | Likely Bottleneck | Solution |
|---------|------------------|----------|
| High API CPU (>80%) | API compute | Scale API horizontally |
| High API memory | Memory leak / large responses | Optimize code, add pagination |
| Slow DB queries | Database overload | Add indexes, scale DB vertically |
| High DB connections | Connection pool exhausted | Increase pool size, scale API |
| Redis evictions | Memory pressure | Increase Redis memory, optimize TTL |
| High latency (>1s) | Network / DB | Add caching, optimize queries |

---

## Cost Optimization

### Cloud Provider Estimates

**AWS (us-east-1):**
- **Tier 2**: ~$150/month (t3.large instances)
- **Tier 3**: ~$500/month (t3.xlarge instances)
- **Tier 4**: ~$2000/month (c5.2xlarge instances)

**GCP (us-central1):**
- **Tier 2**: ~$140/month (n1-standard-2)
- **Tier 3**: ~$480/month (n1-standard-4)
- **Tier 4**: ~$1900/month (c2-standard-8)

### Cost Reduction Strategies

1. **Use spot/preemptible instances** for non-critical workloads (-70% cost)
2. **Auto-scaling** to scale down during low traffic
3. **Data compression** in TimescaleDB (5-10x reduction)
4. **Cache aggressively** in Redis (reduce DB load)
5. **Reserved instances** for stable workloads (-40% cost)

---

## Disaster Recovery

### Backup Strategy

**Automated Backups:**
```bash
# Daily backups at 2 AM
0 2 * * * /app/scripts/backup.sh

# Retention: 30 days
# Location: S3/GCS bucket
```

**Recovery Time Objective (RTO):** 1 hour
**Recovery Point Objective (RPO):** 1 hour

### High Availability

**Multi-AZ Deployment:**
- API: 2+ instances in different AZs
- TimescaleDB: Primary + streaming replica
- Neo4j: Causal cluster (3 cores)
- Redis: Sentinel mode (1 master + 2 replicas)

**Failover:**
- Automatic for Redis Sentinel
- Manual for TimescaleDB (promote replica)
- Automatic for Neo4j cluster

---

## Checklist

### Before Scaling Up
- [ ] Monitor current metrics for 1 week
- [ ] Identify actual bottleneck (not assumed)
- [ ] Estimate cost impact
- [ ] Test scaling in staging environment
- [ ] Prepare rollback plan

### After Scaling
- [ ] Verify all health checks passing
- [ ] Monitor metrics for anomalies
- [ ] Run load tests
- [ ] Update documentation
- [ ] Schedule cost review in 1 month

---

**Last Updated:** Week 7 Day 3
**Next Review:** Week 8 Day 1

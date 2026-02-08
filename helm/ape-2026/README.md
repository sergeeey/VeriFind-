# APE 2026 Helm Chart
**Week 8 Day 1 - Kubernetes Deployment**

## Overview

This Helm chart deploys the complete APE 2026 stack on Kubernetes with:
- FastAPI application (auto-scaling)
- PostgreSQL/TimescaleDB (time-series data)
- Neo4j (graph database)
- Redis (caching)
- Prometheus + Grafana (monitoring)

---

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- PV provisioner support in the underlying infrastructure
- Ingress controller (nginx recommended)
- cert-manager (for TLS certificates)

---

## Quick Start

### 1. Add Repository (if published)

```bash
helm repo add ape-2026 https://charts.ape2026.com
helm repo update
```

### 2. Install Chart

```bash
# Install with default values
helm install ape-2026 ./helm/ape-2026

# Install with custom values
helm install ape-2026 ./helm/ape-2026 \
  --namespace ape-2026 \
  --create-namespace \
  --values custom-values.yaml

# Install with inline values
helm install ape-2026 ./helm/ape-2026 \
  --set api.image.tag=v1.2.3 \
  --set secrets.api.CLAUDE_API_KEY=sk-ant-xxx \
  --set postgresql.auth.password=securepassword
```

### 3. Verify Deployment

```bash
# Check status
helm status ape-2026 -n ape-2026

# List pods
kubectl get pods -n ape-2026

# Check services
kubectl get svc -n ape-2026

# Check ingress
kubectl get ingress -n ape-2026
```

---

## Configuration

### Values File

Create a `custom-values.yaml`:

```yaml
# API Configuration
api:
  replicaCount: 5
  image:
    tag: "v1.2.3"

  ingress:
    hosts:
      - host: api.yourdomain.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: api-tls
        hosts:
          - api.yourdomain.com

  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

  autoscaling:
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60

# Secrets (use --set or external secret manager)
secrets:
  api:
    CLAUDE_API_KEY: "sk-ant-api03-xxx"
    DEEPSEEK_API_KEY: "sk-xxx"
    POSTGRES_PASSWORD: "your-secure-password"
    NEO4J_PASSWORD: "your-secure-password"
    SECRET_KEY: "generate-with-openssl-rand-hex-32"

# PostgreSQL
postgresql:
  primary:
    persistence:
      size: 100Gi
      storageClass: "fast-ssd"
    resources:
      requests:
        memory: "4Gi"
        cpu: "2000m"

# Redis
redis:
  auth:
    enabled: true
    password: "redis-password"
  replica:
    replicaCount: 3

# Neo4j
neo4j:
  persistence:
    size: 100Gi
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"

# Monitoring
prometheus:
  enabled: true
  server:
    retention: "60d"

grafana:
  enabled: true
  adminPassword: "secure-grafana-password"
```

### Install with Custom Values

```bash
helm install ape-2026 ./helm/ape-2026 \
  -f custom-values.yaml \
  --namespace ape-2026 \
  --create-namespace
```

---

## Key Parameters

### API

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.enabled` | Enable API deployment | `true` |
| `api.replicaCount` | Number of API replicas | `3` |
| `api.image.repository` | API image repository | `ghcr.io/yourorg/ape-2026/api` |
| `api.image.tag` | API image tag | `latest` |
| `api.service.type` | Kubernetes service type | `ClusterIP` |
| `api.service.port` | Service port | `8000` |
| `api.autoscaling.enabled` | Enable HPA | `true` |
| `api.autoscaling.minReplicas` | Minimum replicas | `2` |
| `api.autoscaling.maxReplicas` | Maximum replicas | `10` |

### PostgreSQL

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.username` | Database username | `ape` |
| `postgresql.auth.database` | Database name | `ape_timeseries` |
| `postgresql.primary.persistence.size` | PVC size | `50Gi` |

### Redis

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.auth.enabled` | Enable authentication | `false` |
| `redis.replica.replicaCount` | Number of replicas | `2` |

### Neo4j

| Parameter | Description | Default |
|-----------|-------------|---------|
| `neo4j.enabled` | Enable Neo4j | `true` |
| `neo4j.auth.username` | Neo4j username | `neo4j` |
| `neo4j.persistence.size` | PVC size | `50Gi` |

---

## Upgrading

### Upgrade Release

```bash
# Upgrade with new values
helm upgrade ape-2026 ./helm/ape-2026 \
  -f custom-values.yaml \
  --namespace ape-2026

# Upgrade specific component
helm upgrade ape-2026 ./helm/ape-2026 \
  --set api.image.tag=v1.2.4 \
  --namespace ape-2026

# Dry run (test upgrade)
helm upgrade ape-2026 ./helm/ape-2026 \
  -f custom-values.yaml \
  --namespace ape-2026 \
  --dry-run --debug
```

### Rollback

```bash
# List revisions
helm history ape-2026 -n ape-2026

# Rollback to previous version
helm rollback ape-2026 -n ape-2026

# Rollback to specific revision
helm rollback ape-2026 2 -n ape-2026
```

---

## Uninstalling

```bash
# Uninstall release
helm uninstall ape-2026 -n ape-2026

# Delete namespace
kubectl delete namespace ape-2026

# Delete PVCs (if needed)
kubectl delete pvc -n ape-2026 --all
```

---

## Advanced Configuration

### External Databases

To use external databases instead of bundled ones:

```yaml
# Disable bundled databases
postgresql:
  enabled: false

neo4j:
  enabled: false

redis:
  enabled: false

# Configure external endpoints
configMaps:
  api:
    POSTGRES_HOST: "external-postgres.example.com"
    POSTGRES_PORT: "5432"
    REDIS_HOST: "external-redis.example.com"
    NEO4J_URI: "bolt://external-neo4j.example.com:7687"
```

### Custom Storage Class

```yaml
global:
  storageClass: "premium-ssd"

postgresql:
  primary:
    persistence:
      storageClass: "fast-ssd"

neo4j:
  persistence:
    storageClass: "fast-ssd"
```

### Resource Limits

```yaml
api:
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"
    limits:
      memory: "8Gi"
      cpu: "4000m"

postgresql:
  primary:
    resources:
      requests:
        memory: "8Gi"
        cpu: "4000m"
      limits:
        memory: "16Gi"
        cpu: "8000m"
```

### Network Policies

```yaml
networkPolicy:
  enabled: true
  policyTypes:
    - Ingress
    - Egress
```

### Pod Disruption Budget

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 2  # or use maxUnavailable: 1
```

---

## Monitoring

### Prometheus

Metrics are automatically scraped from:
- API pods (port 8000, path `/metrics`)
- PostgreSQL exporter
- Redis exporter

### Grafana

Access Grafana:
```bash
# Get admin password
kubectl get secret ape-2026-grafana -n ape-2026 -o jsonpath="{.data.admin-password}" | base64 --decode

# Port forward
kubectl port-forward svc/ape-2026-grafana 3000:80 -n ape-2026

# Open http://localhost:3000
```

### Service Monitor (Prometheus Operator)

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n ape-2026

# Describe pod
kubectl describe pod <pod-name> -n ape-2026

# Check logs
kubectl logs <pod-name> -n ape-2026

# Check events
kubectl get events -n ape-2026 --sort-by='.lastTimestamp'
```

### PVC Issues

```bash
# Check PVC status
kubectl get pvc -n ape-2026

# Describe PVC
kubectl describe pvc <pvc-name> -n ape-2026

# Check storage class
kubectl get storageclass
```

### Ingress Not Working

```bash
# Check ingress
kubectl get ingress -n ape-2026
kubectl describe ingress ape-2026 -n ape-2026

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
kubectl run -it --rm debug --image=postgres:15 --restart=Never -n ape-2026 -- \
  psql -h ape-2026-postgresql -U ape -d ape_timeseries

# Test Redis connection
kubectl run -it --rm debug --image=redis:7-alpine --restart=Never -n ape-2026 -- \
  redis-cli -h ape-2026-redis-master ping

# Test Neo4j connection
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n ape-2026 -- \
  curl http://ape-2026-neo4j:7474
```

---

## Security

### Secrets Management

**Production Recommendation:** Use external secret management:

```yaml
# External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
  namespace: ape-2026
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: api-secrets
  data:
    - secretKey: CLAUDE_API_KEY
      remoteRef:
        key: ape-2026/claude-api-key
```

### TLS Certificates

```bash
# cert-manager will auto-generate certificates
# Ensure cert-manager is installed and configured

# Check certificate status
kubectl get certificate -n ape-2026
kubectl describe certificate api-tls -n ape-2026
```

---

## Support

**Documentation:**
- Chart source: https://github.com/yourorg/ape-2026
- Issues: https://github.com/yourorg/ape-2026/issues

**Helm Commands:**
```bash
# Chart info
helm show chart ./helm/ape-2026
helm show values ./helm/ape-2026
helm show readme ./helm/ape-2026

# Get manifest
helm get manifest ape-2026 -n ape-2026

# Get values
helm get values ape-2026 -n ape-2026
```

---

**Version:** 1.0.0
**Last Updated:** Week 8 Day 1

# Monitoring & Observability Guide

**Status:** ✅ Implemented (Week 9 Day 2)

---

## Overview

APE 2026 uses **Prometheus** for metrics collection and **Grafana** for visualization. This guide covers all available metrics, dashboards, and monitoring best practices.

---

## Table of Contents

1. [Metrics Overview](#metrics-overview)
2. [HTTP Metrics](#http-metrics)
3. [Business Metrics](#business-metrics)
4. [Error Metrics](#error-metrics)
5. [Infrastructure Metrics](#infrastructure-metrics)
6. [Dashboards](#dashboards)
7. [Alerting](#alerting)
8. [Querying Metrics](#querying-metrics)
9. [Troubleshooting](#troubleshooting)

---

## Metrics Overview

### Accessing Metrics

**Prometheus Metrics Endpoint:**
```
http://localhost:8000/metrics
```

**Prometheus UI:**
```
http://localhost:9090
```

**Grafana Dashboards:**
```
http://localhost:3000
Username: admin
Password: admin (change on first login)
```

### Metric Types

| Type | Description | Example |
|------|-------------|---------|
| **Counter** | Monotonically increasing value | `http_requests_total` |
| **Gauge** | Value that can go up or down | `websocket_connections_total` |
| **Histogram** | Distribution of values | `http_request_duration_seconds` |
| **Summary** | Similar to histogram | (not used in APE) |
| **Info** | Metadata about the application | `app_info` |

---

## HTTP Metrics

### Request Count

**Metric:** `http_requests_total`
**Type:** Counter
**Labels:** `method`, `endpoint`, `status`

**Example:**
```promql
# Total requests
sum(http_requests_total)

# Requests by endpoint
sum by (endpoint) (rate(http_requests_total[5m]))

# Error rate (5xx responses)
sum(rate(http_requests_total{status=~"5.."}[5m]))
```

---

### Request Duration

**Metric:** `http_request_duration_seconds`
**Type:** Histogram
**Labels:** `method`, `endpoint`

**Buckets:** 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s

**Example:**
```promql
# Average latency
avg(rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]))

# 95th percentile latency
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# 99th percentile latency
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
```

---

### Request/Response Size

**Metrics:**
- `http_request_size_bytes` - Request payload size
- `http_response_size_bytes` - Response payload size

**Type:** Histogram
**Labels:** `method`, `endpoint`

**Example:**
```promql
# Average request size
avg(rate(http_request_size_bytes_sum[5m]) / rate(http_request_size_bytes_count[5m]))

# Large responses (> 100KB)
sum(rate(http_response_size_bytes_bucket{le="100000"}[5m]))
```

---

### Requests in Progress

**Metric:** `http_requests_in_progress`
**Type:** Gauge
**Labels:** `method`, `endpoint`

**Example:**
```promql
# Currently processing requests
sum(http_requests_in_progress)

# In-progress by endpoint
sum by (endpoint) (http_requests_in_progress)
```

---

## Business Metrics

### Query Submission

**Metric:** `queries_submitted_total`
**Type:** Counter
**Labels:** `priority` (low, normal, high)

**Example:**
```promql
# Total queries submitted
sum(queries_submitted_total)

# Query rate by priority
sum by (priority) (rate(queries_submitted_total[5m]))

# High-priority query rate
rate(queries_submitted_total{priority="high"}[5m])
```

---

### Query Completion

**Metric:** `queries_completed_total`
**Type:** Counter
**Labels:** `status` (completed, failed)

**Example:**
```promql
# Completion rate
sum(rate(queries_completed_total[5m]))

# Success rate
sum(rate(queries_completed_total{status="completed"}[5m]))
/ sum(rate(queries_completed_total[5m]))

# Failure rate
sum(rate(queries_completed_total{status="failed"}[5m]))
```

---

### Query Execution Time

**Metric:** `query_execution_duration_seconds`
**Type:** Histogram
**Labels:** `status`

**Buckets:** 1s, 5s, 10s, 30s, 60s, 120s, 300s, 600s

**Example:**
```promql
# Average execution time
avg(rate(query_execution_duration_seconds_sum[5m]) / rate(query_execution_duration_seconds_count[5m]))

# 95th percentile
histogram_quantile(0.95, sum by (le) (rate(query_execution_duration_seconds_bucket[5m])))

# Slow queries (> 60s)
sum(query_execution_duration_seconds_bucket{le="60"})
```

---

### Pipeline Metrics

**Metrics:**
- `pipeline_node_duration_seconds` - Time spent in each node
- `pipeline_node_executions_total` - Execution count per node

**Type:** Histogram / Counter
**Labels:** `node` (PLAN, FETCH, VEE, GATE, DEBATE)

**Example:**
```promql
# Average time per node
avg by (node) (
  rate(pipeline_node_duration_seconds_sum[5m])
  / rate(pipeline_node_duration_seconds_count[5m])
)

# Node success rate
sum by (node) (rate(pipeline_node_executions_total{status="success"}[5m]))
/ sum by (node) (rate(pipeline_node_executions_total[5m]))

# Slowest node
topk(1, avg by (node) (pipeline_node_duration_seconds))
```

---

### Verified Facts

**Metrics:**
- `verified_facts_generated_total` - Total facts generated
- `facts_confidence_score` - Distribution of confidence scores

**Type:** Counter / Histogram

**Example:**
```promql
# Facts generation rate
rate(verified_facts_generated_total[5m])

# Average confidence score
avg(rate(facts_confidence_score_sum[5m]) / rate(facts_confidence_score_count[5m]))

# High-confidence facts (> 0.9)
sum(rate(facts_confidence_score_bucket{le="0.9"}[5m]))
```

---

### WebSocket Metrics

**Metrics:**
- `websocket_connections_total` - Active connections
- `websocket_messages_sent_total` - Messages sent
- `websocket_messages_received_total` - Messages received

**Type:** Gauge / Counter
**Labels:** `message_type`, `action`

**Example:**
```promql
# Active WebSocket connections
websocket_connections_total

# Message rate (sent)
sum by (message_type) (rate(websocket_messages_sent_total[5m]))

# Message rate (received)
sum by (action) (rate(websocket_messages_received_total[5m]))
```

---

## Error Metrics

### Exceptions

**Metric:** `exceptions_total`
**Type:** Counter
**Labels:** `exception_type`, `severity` (critical, error, warning, info)

**Example:**
```promql
# Total exception rate
sum(rate(exceptions_total[5m]))

# Critical exceptions
sum(rate(exceptions_total{severity="critical"}[5m]))

# Exceptions by type
sum by (exception_type) (rate(exceptions_total[5m]))
```

---

### Validation Errors

**Metric:** `validation_errors_total`
**Type:** Counter
**Labels:** `error_type` (sql_injection, xss, command_injection, etc.)

**Example:**
```promql
# Validation error rate
sum(rate(validation_errors_total[5m]))

# SQL injection attempts
rate(validation_errors_total{error_type="sql_injection"}[5m])

# Security threat rate
sum(rate(validation_errors_total{error_type=~"sql_injection|xss|command_injection"}[5m]))
```

---

### Rate Limit Violations

**Metric:** `rate_limit_violations_total`
**Type:** Counter
**Labels:** `api_key`

**Example:**
```promql
# Total violations
sum(rate(rate_limit_violations_total[5m]))

# Top violators
topk(10, sum by (api_key) (rate(rate_limit_violations_total[1h])))

# Violation spike detection
rate(rate_limit_violations_total[5m]) > 10
```

---

## Infrastructure Metrics

### External API Calls

**Metrics:**
- `external_api_requests_total` - Request count
- `external_api_duration_seconds` - Request duration

**Type:** Counter / Histogram
**Labels:** `service` (anthropic, openai, alpha_vantage), `status`

**Example:**
```promql
# API call rate by service
sum by (service) (rate(external_api_requests_total[5m]))

# API success rate
sum by (service) (rate(external_api_requests_total{status="success"}[5m]))
/ sum by (service) (rate(external_api_requests_total[5m]))

# Average latency by service
avg by (service) (
  rate(external_api_duration_seconds_sum[5m])
  / rate(external_api_duration_seconds_count[5m])
)
```

---

### Database Queries

**Metrics:**
- `database_queries_total` - Query count
- `database_query_duration_seconds` - Query duration
- `database_connection_pool_size` - Connection pool status

**Type:** Counter / Histogram / Gauge
**Labels:** `database` (timescaledb, neo4j), `operation`, `state`

**Example:**
```promql
# Query rate by database
sum by (database) (rate(database_queries_total[5m]))

# Slow queries (> 100ms)
sum(rate(database_query_duration_seconds_bucket{le="0.1"}[5m]))

# Connection pool usage
sum by (database, state) (database_connection_pool_size)
```

---

### Cache Performance

**Metrics:**
- `cache_operations_total` - Cache operations
- `cache_hit_ratio` - Hit ratio (0-1)

**Type:** Counter / Gauge
**Labels:** `operation`, `result` (hit, miss)

**Example:**
```promql
# Cache hit rate
sum(rate(cache_operations_total{result="hit"}[5m]))
/ sum(rate(cache_operations_total{operation="get"}[5m]))

# Cache miss rate
sum(rate(cache_operations_total{result="miss"}[5m]))

# Current hit ratio
cache_hit_ratio
```

---

## Dashboards

### Pre-configured Dashboards

1. **API Overview**
   - Request rate, latency, errors
   - Active connections
   - Top endpoints

2. **Query Execution**
   - Submission/completion rates
   - Execution time distribution
   - Pipeline node performance

3. **Error Analysis**
   - Exception rates
   - Validation errors
   - Rate limit violations

4. **Infrastructure**
   - Database performance
   - External API calls
   - Cache hit ratio

### Importing Dashboards

**Method 1: Auto-provisioning (Recommended)**
```bash
# Dashboards are automatically loaded from:
config/grafana/dashboards/
```

**Method 2: Manual Import**
1. Go to Grafana UI → Dashboards → Import
2. Upload JSON file or paste dashboard ID
3. Select Prometheus datasource

---

## Alerting

### Alert Rules

Create alert rules in `config/prometheus/alerts/`:

**Example: High Error Rate**
```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
```

**Example: Slow Queries**
```yaml
      - alert: SlowQueries
        expr: |
          histogram_quantile(0.95,
            sum by (le) (rate(query_execution_duration_seconds_bucket[5m]))
          ) > 60
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow query execution"
          description: "95th percentile: {{ $value }}s"
```

**Example: Database Connection Pool Exhaustion**
```yaml
      - alert: DatabasePoolExhausted
        expr: |
          database_connection_pool_size{state="idle"} < 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "Only {{ $value }} idle connections remaining"
```

---

## Querying Metrics

### Common Queries

**Request Rate (last 5 minutes):**
```promql
sum(rate(http_requests_total[5m]))
```

**Error Percentage:**
```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
/ sum(rate(http_requests_total[5m])) * 100
```

**Top 5 Slowest Endpoints:**
```promql
topk(5,
  histogram_quantile(0.95,
    sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))
  )
)
```

**Queries Per Second:**
```promql
sum(rate(queries_submitted_total[5m]))
```

**Average Facts Per Query:**
```promql
rate(verified_facts_generated_total[5m])
/ rate(queries_completed_total[5m]))
```

---

## Troubleshooting

### Metrics Not Appearing

**Check Prometheus is scraping:**
```bash
curl http://localhost:9090/api/v1/targets
```

**Check metrics endpoint:**
```bash
curl http://localhost:8000/metrics
```

**View Prometheus logs:**
```bash
docker compose logs -f prometheus
```

### High Memory Usage

**Check metric cardinality:**
```promql
# Count unique time series
count({__name__=~".+"})

# Top metrics by cardinality
topk(10, count by (__name__) ({__name__=~".+"}))
```

**Solution:** Reduce label cardinality or use recording rules

### Dashboard Not Loading

**Check Grafana datasource:**
1. Go to Configuration → Data Sources
2. Click "Test" on Prometheus datasource
3. Should show "Data source is working"

**Check provisioning:**
```bash
docker compose logs -f grafana | grep -i provision
```

---

## Best Practices

### Metric Naming

✅ **Good:**
- `http_requests_total`
- `query_execution_duration_seconds`
- `database_connections_active`

❌ **Bad:**
- `requests` (too vague)
- `query_time` (missing unit)
- `db_conn` (unclear abbreviation)

### Label Usage

✅ **Good:**
```promql
http_requests_total{method="POST", endpoint="/query", status="200"}
```

❌ **Bad:**
```promql
http_requests_total{user_id="12345"}  # High cardinality!
```

**Rule:** Don't use high-cardinality values (user IDs, request IDs) as labels

### Query Performance

- Use recording rules for expensive queries
- Limit time ranges (avoid 24h+ ranges)
- Use `rate()` instead of `increase()` for counters
- Aggregate before querying (`sum by`)

---

**Last Updated:** 2026-02-08
**Version:** 1.0.0
**Status:** Production Ready

# Error Handling Guide

**Status:** ✅ Implemented (Week 9 Day 2)

---

## Overview

APE API uses centralized error handling with structured error responses, request ID tracking, and comprehensive logging.

---

## Error Response Format

All errors follow a **standardized RFC 7807-compliant format**:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "status": 400,
    "timestamp": "2026-02-08T14:30:00.000Z",
    "request_id": "abc-123-def-456",
    "path": "/query",
    "details": {
      "additional": "context"
    }
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Machine-readable error code (e.g., `VALIDATION_ERROR`) |
| `message` | string | Human-readable error description |
| `status` | number | HTTP status code |
| `timestamp` | string | ISO 8601 timestamp (UTC) |
| `request_id` | string | Unique request identifier for tracking |
| `path` | string | API endpoint path |
| `details` | object | Additional error-specific context (optional) |

---

## Error Categories

### Client Errors (4xx)

#### 400 Bad Request - `INVALID_QUERY`
```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "Query contains SQL injection patterns",
    "status": 400,
    "details": {
      "pattern": "SELECT * FROM"
    }
  }
}
```

**Causes:**
- Malformed query
- Security validation failure (SQL injection, XSS, command injection)

---

#### 401 Unauthorized - `AUTHENTICATION_ERROR`
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid API key",
    "status": 401
  }
}
```

**Causes:**
- Missing `X-API-Key` header
- Invalid API key
- WebSocket authentication failure

---

#### 403 Forbidden - `AUTHORIZATION_ERROR`
```json
{
  "error": {
    "code": "AUTHORIZATION_ERROR",
    "message": "Insufficient permissions",
    "status": 403
  }
}
```

**Causes:**
- Valid API key but insufficient permissions
- Attempting to access resources outside allowed scope

---

#### 404 Not Found - `RESOURCE_NOT_FOUND`
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Query not found: abc-123",
    "status": 404,
    "details": {
      "resource": "Query",
      "resource_id": "abc-123"
    }
  }
}
```

**Causes:**
- Query ID doesn't exist
- Episode ID doesn't exist
- Resource has been deleted

---

#### 422 Unprocessable Entity - `VALIDATION_ERROR`
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "status": 422,
    "details": {
      "validation_errors": [
        {
          "field": "query",
          "message": "String should have at least 10 characters",
          "type": "string_too_short"
        }
      ]
    }
  }
}
```

**Causes:**
- Request body validation failure
- Missing required fields
- Invalid field types
- Field constraints violated (min/max length, range, etc.)

---

#### 429 Too Many Requests - `RATE_LIMIT_EXCEEDED`
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 100 requests per hour. Try again in 120s",
    "status": 429,
    "details": {
      "retry_after_seconds": 120
    }
  }
}
```

**Causes:**
- Too many requests from API key (hourly limit)
- Burst limit exceeded (too many requests in short time)
- Exponential backoff in effect after violations

**Retry Strategy:**
- Check `details.retry_after_seconds`
- Wait specified time before retrying
- Reduce request rate to avoid future violations

---

### Server Errors (5xx)

#### 500 Internal Server Error - `ORCHESTRATOR_ERROR`
```json
{
  "error": {
    "code": "ORCHESTRATOR_ERROR",
    "message": "PLAN node failed: LLM API error",
    "status": 500,
    "details": {
      "failed_node": "PLAN"
    }
  }
}
```

**Causes:**
- Pipeline node execution failed
- Internal orchestration error
- Unexpected exception in query processing

---

#### 500 Internal Server Error - `STORAGE_ERROR`
```json
{
  "error": {
    "code": "STORAGE_ERROR",
    "message": "Failed to save verified fact",
    "status": 500,
    "details": {
      "storage_type": "TimescaleDB"
    }
  }
}
```

**Causes:**
- Database connection failure
- Write operation failed
- Storage quota exceeded

---

#### 500 Internal Server Error - `SANDBOX_ERROR`
```json
{
  "error": {
    "code": "SANDBOX_ERROR",
    "message": "Code execution failed: division by zero",
    "status": 500
  }
}
```

**Causes:**
- VEE sandbox execution error
- Runtime exception in generated code
- Sandbox timeout

---

#### 503 Service Unavailable - `EXTERNAL_SERVICE_ERROR`
```json
{
  "error": {
    "code": "EXTERNAL_SERVICE_ERROR",
    "message": "OpenAI API error: Rate limit exceeded",
    "status": 503,
    "details": {
      "service": "OpenAI",
      "retry_possible": true
    }
  }
}
```

**Causes:**
- External API unavailable
- Market data provider error
- LLM API rate limit

**Retry Strategy:**
- Check `details.retry_possible`
- Use exponential backoff (1s, 2s, 4s, 8s, ...)
- Maximum 3 retry attempts

---

#### 504 Gateway Timeout - `TIMEOUT_ERROR`
```json
{
  "error": {
    "code": "TIMEOUT_ERROR",
    "message": "Query execution timed out after 120s",
    "status": 504,
    "details": {
      "operation": "query_execution",
      "timeout_seconds": 120
    }
  }
}
```

**Causes:**
- Query execution exceeded timeout
- Sandbox execution timeout
- External API timeout

**Mitigation:**
- Reduce query complexity
- Increase timeout in settings (if permitted)
- Break query into smaller parts

---

#### 500 Internal Server Error - `INTERNAL_SERVER_ERROR`
```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred. Please try again later.",
    "status": 500,
    "details": {
      "request_id": "abc-123-def-456"
    }
  }
}
```

**Causes:**
- Unhandled exception
- Unexpected runtime error
- Programming bug

**Action:**
- Report error with `request_id` to support
- Check logs for details
- Retry after a delay

---

## Request ID Tracking

Every request receives a unique **Request ID** for tracking across logs and errors.

### In Response Headers
```http
X-Request-ID: abc-123-def-456
```

### In Error Response
```json
{
  "error": {
    "request_id": "abc-123-def-456",
    ...
  }
}
```

### Usage
1. **Client Side:** Store request ID for debugging
2. **Support:** Provide request ID when reporting issues
3. **Logs:** Search logs by request ID for full context

---

## Logging

### Structured Logging

**Development:**
```
2026-02-08 14:30:00 - src.api.main - INFO - Request started: POST /query
```

**Production (JSON):**
```json
{
  "time": "2026-02-08T14:30:00.000Z",
  "level": "INFO",
  "logger": "src.api.main",
  "message": "Request started: POST /query",
  "method": "POST",
  "path": "/query",
  "request_id": "abc-123"
}
```

### Log Levels

| Level | When Used |
|-------|-----------|
| **DEBUG** | Development only (detailed trace) |
| **INFO** | Request/response logs, normal operations |
| **WARNING** | Rate limit violations, validation failures |
| **ERROR** | Server errors, failed operations |
| **CRITICAL** | Configuration errors, storage failures |

### Configuration

**Environment Variables:**
```bash
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json           # json or text
LOG_FILE_PATH=./logs/ape.log  # Optional file logging
```

---

## Error Handling Utilities

### Check if Error is Retryable

```python
from src.api.exceptions import is_retryable, ExternalServiceError

try:
    call_external_api()
except Exception as e:
    if is_retryable(e):
        # Retry with exponential backoff
        retry_with_backoff(call_external_api)
    else:
        # Fail immediately
        raise
```

**Retryable Errors:**
- `TimeoutError`
- `ExternalServiceError`
- `StorageError` (transient DB issues)

**Non-Retryable Errors:**
- `ValidationError`
- `AuthenticationError`
- `AuthorizationError`
- `InvalidQueryError`

---

### Get Error Severity

```python
from src.api.exceptions import get_error_severity

severity = get_error_severity(exception)
# Returns: "critical", "error", "warning", or "info"
```

**Severity Levels:**

| Severity | Errors |
|----------|--------|
| **critical** | ConfigurationError, StorageError, OrchestratorError |
| **error** | SandboxError, ExternalServiceError, TimeoutError |
| **warning** | RateLimitError |
| **info** | ValidationError, InvalidQueryError, ResourceNotFoundError |

---

## Client Error Handling Best Practices

### 1. Always Check Status Code

```javascript
const response = await fetch('/query', {
  method: 'POST',
  headers: { 'X-API-Key': 'your_key' },
  body: JSON.stringify({ query: '...' })
});

if (!response.ok) {
  const error = await response.json();
  console.error(`Error ${error.error.code}:`, error.error.message);

  // Handle specific error codes
  switch (error.error.code) {
    case 'RATE_LIMIT_EXCEEDED':
      const retryAfter = error.error.details.retry_after_seconds;
      setTimeout(() => retry(), retryAfter * 1000);
      break;
    case 'AUTHENTICATION_ERROR':
      redirectToLogin();
      break;
    default:
      showErrorToUser(error.error.message);
  }
}
```

### 2. Store Request ID

```javascript
const requestId = response.headers.get('X-Request-ID');
logError({ requestId, error });
```

### 3. Implement Retry Logic

```javascript
async function callWithRetry(fn, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (!error.error?.details?.retry_possible || attempt === maxRetries) {
        throw error;
      }

      const backoff = Math.pow(2, attempt) * 1000; // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, backoff));
    }
  }
}
```

### 4. Handle Validation Errors

```javascript
if (error.error.code === 'VALIDATION_ERROR') {
  const errors = error.error.details.validation_errors;
  errors.forEach(({ field, message }) => {
    displayFieldError(field, message);
  });
}
```

---

## Debugging

### View Full Error Context

When an error occurs, check logs with request ID:

```bash
# Production logs (JSON)
cat logs/ape.log | jq 'select(.request_id == "abc-123")'

# Development logs (text)
grep "abc-123" logs/ape.log
```

### Enable Debug Logging

```bash
# .env
LOG_LEVEL=DEBUG
```

---

## Testing Error Scenarios

### Trigger Validation Error
```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: dev_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"query": "short"}'  # < 10 characters
```

### Trigger Authentication Error
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Calculate Sharpe ratio"}'
# Missing X-API-Key header
```

### Trigger Rate Limit
```bash
for i in {1..150}; do
  curl -X POST http://localhost:8000/query \
    -H "X-API-Key: dev_key_12345" \
    -H "Content-Type: application/json" \
    -d '{"query": "Test query for rate limiting"}' &
done
```

---

## Error Monitoring

### Recommended Tools

1. **Sentry** (production error tracking)
   - Automatic error capture
   - Stack traces and context
   - Error grouping and deduplication

2. **Grafana + Loki** (log aggregation)
   - Search logs by request ID
   - Error rate dashboards
   - Alerting on error patterns

3. **Prometheus** (metrics)
   - Error count by code
   - Error rate per endpoint
   - Latency percentiles

---

## Future Enhancements

- [ ] Sentry integration for error tracking
- [ ] Error rate alerting (Prometheus + Alertmanager)
- [ ] Automatic error recovery (circuit breaker pattern)
- [ ] Error budget tracking (SLO/SLI)
- [ ] User-friendly error messages with suggestions

---

**Last Updated:** 2026-02-08
**Version:** 1.0.0
**Status:** Production Ready

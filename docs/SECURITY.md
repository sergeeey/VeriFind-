# Security Guide

**Status:** ✅ Implemented (Week 9 Day 1)

---

## Overview

This document outlines the security features implemented in APE API and best practices for production deployment.

---

## Security Features

### 1. Input Validation & Sanitization

**Location:** `src/api/security.py` (`InputValidator` class)

**Protection Against:**
- SQL Injection
- Cross-Site Scripting (XSS)
- Command Injection
- Path Traversal
- Excessive Input Length

**Implementation:**
```python
from api.security import input_validator

# Validate user query
result = input_validator.validate_query(user_input)
if not result.is_valid:
    raise ValueError(result.error_message)

# Use sanitized value
sanitized = result.sanitized_value
```

**Detected Patterns:**
- SQL keywords: `SELECT`, `UNION`, `DROP`, `DELETE`, etc.
- Boolean conditions: `OR 1=1`, `AND x=x`
- Script tags: `<script>`, `javascript:`, `on*` event handlers
- Shell metacharacters: `;`, `|`, `$()`, backticks
- Path traversal: `../`, `..\`

---

### 2. Rate Limiting

**Location:** `src/api/security.py` (`RateLimiter` class)

**Features:**
- Sliding window algorithm
- Per-endpoint limits
- Burst protection (short-term spike allowance)
- Exponential backoff on violations
- Configurable limits per API key

**Configuration:**
```python
# .env
RATE_LIMIT_REQUESTS_PER_HOUR=100
RATE_LIMIT_BURST_PER_MINUTE=10
```

**Implementation:**
```python
from api.security import rate_limiter

is_allowed, error_message = rate_limiter.check_rate_limit(
    key="user_api_key",
    endpoint="query",
    limit=100,  # requests per hour
    window_seconds=3600,
    burst_limit=10  # requests per minute
)
```

**Backoff Schedule:**
- 1st violation: 60 seconds
- 2nd violation: 120 seconds
- 3rd violation: 240 seconds
- Cap: 3600 seconds (1 hour)

---

### 3. API Key Authentication

**Location:** `src/api/main.py` (`verify_api_key` function)

**Format:**
- Header: `X-API-Key: your_api_key_here`
- WebSocket: `?api_key=your_api_key_here` (query parameter)

**Production API Keys:**

**Option 1: Environment Variables (Recommended)**
```bash
# .env
API_KEY_PROD=prod_key_abc123:1000
API_KEY_STAGING=staging_key_xyz789:500
```

**Option 2: Config File**
```python
# src/api/config.py
api_keys: Dict[str, Dict[str, any]] = {
    "your_key": {"name": "Client Name", "rate_limit": 1000}
}
```

**Key Format:** Alphanumeric + underscores/hyphens, 8-128 characters

---

### 4. Security Headers

**Location:** `src/api/main.py` (`add_security_headers` middleware)

**Headers Applied:**

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Enable XSS filter (legacy) |
| `Content-Security-Policy` | See below | Restrict resource loading |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer info |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Disable unnecessary features |

**Content Security Policy (CSP):**
```
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self';
connect-src 'self' ws: wss:;
frame-ancestors 'none';
```

**Production TODO:**
```python
# Enable HSTS when HTTPS is configured
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```

---

### 5. WebSocket Authentication

**Location:** `src/api/main.py` (`websocket_endpoint`)

**Authentication Methods:**

**Method 1: Query Parameter (Connection Time)**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws?api_key=your_key');
```

**Method 2: Auth Action (After Connection)**
```javascript
ws.send(JSON.stringify({
  action: 'auth',
  api_key: 'your_key'
}));
```

**Behavior:**
- Unauthenticated clients: Can connect, but all actions except `auth` are blocked
- Invalid API key: Error response, connection remains open (can retry)
- Valid API key: Full access to subscribe/unsubscribe/ping

---

### 6. Secrets Management

**Location:** `src/api/config.py` (`Settings` class)

**Production Validation:**

The config system validates that production secrets are set:
```python
@validator("secret_key")
def validate_secret_key(cls, v, values):
    env = values.get("environment", "development")
    if env == "production" and v == "dev_secret_key_change_in_production":
        raise ValueError("SECRET_KEY must be changed in production")
    if env == "production" and len(v) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters")
    return v
```

**Required Production Secrets:**
- `SECRET_KEY`: JWT signing key (32+ characters)
- `DATABASE_USER` / `DATABASE_PASSWORD`: Database credentials
- `NEO4J_PASSWORD`: Graph database password
- API keys for external services (if used)

**Generate Secure Keys:**
```bash
# SECRET_KEY (64 hex characters = 32 bytes)
openssl rand -hex 32

# API Key (32 hex characters)
openssl rand -hex 16
```

---

## CORS Configuration

**Location:** `src/api/config.py`

**Development:**
```python
cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
```

**Production (.env):**
```bash
CORS_ORIGINS=https://yourfrontend.com,https://www.yourfrontend.com
```

**Important:**
- Never use `["*"]` in production
- Whitelist only trusted domains
- Include protocol (`https://`) and exact domain

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Generate new `SECRET_KEY` (32+ characters)
  ```bash
  export SECRET_KEY=$(openssl rand -hex 32)
  ```
- [ ] Change all database passwords from defaults
- [ ] Configure production API keys via environment
  ```bash
  export API_KEY_PROD=your_prod_key:1000
  ```
- [ ] Set `CORS_ORIGINS` to production frontend URL(s)
- [ ] Review and adjust rate limits
- [ ] Enable HTTPS (required for production)
- [ ] Configure logging to file (`LOG_FILE_PATH`)

### Infrastructure

- [ ] Use HTTPS/TLS (required)
- [ ] Configure firewall rules (allow only necessary ports)
- [ ] Set up reverse proxy (nginx/Caddy) with rate limiting
- [ ] Enable HSTS header when HTTPS is configured
- [ ] Use environment variables for all secrets (never hardcode)
- [ ] Restrict database access to API server only
- [ ] Enable database encryption at rest

### Monitoring

- [ ] Set up log monitoring and alerting
- [ ] Monitor rate limit violations
- [ ] Track failed authentication attempts
- [ ] Set up security event notifications
- [ ] Regular security audit logs review

### Runtime

- [ ] Sandbox network access disabled (`SANDBOX_ENABLE_NETWORK=false`)
- [ ] Minimal sandbox permissions
- [ ] Regular dependency updates
- [ ] Security patch monitoring

---

## Security Audit

Run security checks before deployment:

```bash
# 1. Check for hardcoded secrets
grep -r "api_key\|password\|secret" --exclude-dir=node_modules --exclude-dir=.git

# 2. Validate .env configuration
python -c "from src.api.config import get_settings; settings = get_settings()"

# 3. Run security tests
pytest tests/security/

# 4. Dependency vulnerability scan
pip install safety
safety check

# 5. Check CORS configuration
grep -r "allow_origins" src/
```

---

## Known Limitations

### Current Implementation

1. **No JWT Token Authentication**
   - Currently using simple API key authentication
   - Consider implementing JWT for stateless auth

2. **In-Memory Rate Limiting**
   - Rate limiter state is lost on restart
   - Consider using Redis for distributed rate limiting

3. **No IP-Based Rate Limiting**
   - Only API key-based limits
   - Add IP-based limits for unauthenticated endpoints

4. **WebSocket Authentication After Connection**
   - Client can connect before authenticating
   - Consider implementing auth at connection time only

### Future Enhancements

- [ ] JWT token authentication
- [ ] Redis-based distributed rate limiting
- [ ] IP-based rate limiting
- [ ] Request signing (HMAC)
- [ ] OAuth2 integration
- [ ] Two-factor authentication (2FA)
- [ ] Audit logging to database
- [ ] Intrusion detection system (IDS)

---

## Security Incident Response

### If API Key is Compromised

1. **Immediate:**
   - Remove compromised key from `API_KEYS` config
   - Restart API server
   - Review logs for unauthorized access

2. **Short-term:**
   - Generate new API key for affected client
   - Notify affected parties
   - Analyze attack vector

3. **Long-term:**
   - Implement key rotation policy
   - Add key expiration
   - Enhance monitoring

### If Injection Attack Detected

1. **Immediate:**
   - Block attacker IP (firewall)
   - Review logs for damage
   - Verify data integrity

2. **Short-term:**
   - Patch vulnerability if found
   - Update input validation patterns
   - Run security audit

3. **Long-term:**
   - Implement WAF (Web Application Firewall)
   - Add automated attack detection
   - Regular penetration testing

---

## Contact

For security issues, contact: [security@yourdomain.com]

**Report vulnerabilities responsibly:**
- Do NOT disclose publicly until patched
- Provide detailed reproduction steps
- Allow 90 days for remediation

---

**Last Updated:** 2026-02-08
**Version:** 1.0.0
**Status:** Production Ready

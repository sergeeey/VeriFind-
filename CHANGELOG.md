# Changelog

All notable changes to APE 2026 project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-02-10

### Added
- **Performance Optimization (Week 10)**
  - Response Cache Middleware with Redis support
  - Profiling Middleware for request timing analysis
  - Route-level caching in analysis endpoints
  - Connection pooling configuration (DB, Redis, Neo4j)
  - Performance metrics endpoint (`/metrics/performance`)
  - Python performance testing scripts (`scripts/performance_test.py`)
  - k6 load testing scripts (`scripts/load_test.js`)
  - Quick validation test (`scripts/quick_test.py`)
  - Performance testing documentation (`scripts/PERFORMANCE_README.md`)

- **API Configuration**
  - Added `llm_provider` and `deepseek_api_key` to APISettings
  - Added performance settings (cache_ttl, profiling_threshold)
  - Added connection pool configuration options

- **Real-World Testing**
  - Gold price forecast query tested successfully (HTTP 200)
  - Bitcoin price forecast query tested successfully (HTTP 200)
  - Multi-language query support verified (Russian)
  - Risk metrics calculation (Sharpe ratio, volatility)

### Fixed
- **Critical API Errors**
  - Fixed `'LangGraphOrchestrator' object has no attribute 'process_query_async'`
  - Fixed `'VerifiedFact' object has no attribute 'statement'`
  - Fixed `'APISettings' object has no attribute 'llm_provider'`
  - Fixed Content-Length mismatch in disclaimer middleware
  - Fixed query validation (min_length=10 properly enforced)

### Changed
- **Middleware Order**
  - Reorganized middleware stack for better performance
  - Cache middleware now positioned before expensive operations
  - Profiling middleware tracks timing accurately

### Known Issues
- **Redis Container**: Not responding on port 6380 (needs restart)
- **Cache Performance**: Cache HIT takes 2s instead of 0.05s (middleware issue)
- **Demo Mode**: Returns null for answer/cost (needs real API key)

## [0.9.0] - 2026-02-08 (Week 2)

### Added
- **Security Hardening**
  - Rotated default passwords (Neo4j, Postgres, Secret Key, Grafana)
  - Created API_KEY_MANAGEMENT.md
  - Bandit security scan integration
  - Security headers (CSP, CORS, XSS protection)

- **API Critical Tests**
  - 19 critical API tests created
  - All tests passing (19/19)
  - pytest markers for critical tests

- **Resilience Features**
  - Circuit Breaker pattern implementation
  - LLMProviderChain for fallback (DeepSeek → Anthropic → OpenAI)
  - Redis WebSocket scaling
  - Graceful degradation for DB failures

- **Monitoring**
  - Prometheus metrics integration
  - Grafana dashboard JSON
  - Health endpoints (/health, /ready, /live)
  - Prometheus alerts YAML

- **Documentation**
  - Production deployment guide (PRODUCTION_DEPLOY.md)
  - Load testing scripts (Locust, asyncio)
  - Kubernetes manifests example

### Fixed
- **Security**
  - MD5 → SHA-256 in yfinance_adapter.py
  - Bandit: 0 HIGH severity issues

- **API Tests**
  - Fixed AsyncClient → ASGITransport
  - Added missing routes (/api/predictions, /api/data/*)
  - Fixed Prometheus metrics labels
  - Fixed health endpoints format

### Changed
- **Architecture**
  - Refactored from God Object to Clean Architecture
  - Extracted routes to separate modules
  - Improved error handling

## [0.8.0] - 2026-02-01 (Week 1)

### Added
- **Core API**
  - FastAPI application structure
  - Basic endpoints (/health, /api/analyze, /api/query)
  - Pydantic models for validation
  - Error handling middleware

- **Database Layer**
  - Neo4j integration (Graph database)
  - TimescaleDB integration (Time-series)
  - Redis integration (Cache/WebSocket)

- **AI Integration**
  - LangGraph orchestration
  - Multi-LLM support structure
  - Plan → Fetch → VEE → Debate pipeline

- **Testing**
  - pytest framework setup
  - Unit tests for core components
  - Integration test structure

### Security
- Initial security review
- Basic input validation
- API key structure

## [0.1.0] - 2026-01-25

### Added
- Initial project structure
- README and documentation
- Basic financial analysis concept
- Technology stack selection

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements

## Versioning Policy

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Grade History

| Version | Date | Grade | Notes |
|---------|------|-------|-------|
| 0.1.0 | 2026-01-25 | 4.5/10 | Initial concept |
| 0.8.0 | 2026-02-01 | 6.0/10 | Core structure |
| 0.9.0 | 2026-02-08 | 8.7/10 | Production ready |
| Unreleased | 2026-02-10 | 8.1/10 | Performance + Testing |

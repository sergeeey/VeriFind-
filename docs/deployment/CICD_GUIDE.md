# CI/CD Pipeline Guide
**Week 7 Day 4 - APE 2026**

## Overview

This document describes the Continuous Integration and Continuous Deployment pipeline for APE 2026.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Developer Push                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Pre-commit     │
                    │  Hooks          │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  GitHub Push    │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐      ┌──────▼──────┐      ┌─────▼──────┐
   │   Lint   │      │    Test     │      │  Security  │
   │  (2 min) │      │  (10 min)   │      │  (5 min)   │
   └────┬─────┘      └──────┬──────┘      └─────┬──────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Build Docker   │
                    │  (5 min)        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Push Registry  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Deploy Staging │
                    │  (3 min)        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Health Check   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Manual Approve │
                    │  (Production)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Deploy Prod    │
                    │  (Blue-Green)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Notify Team    │
                    └─────────────────┘
```

**Total Time:**
- **Development → Staging:** ~25 minutes
- **Staging → Production:** +5 minutes (manual approval)
- **Total:** ~30 minutes

---

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main`, `develop`
- Pull requests to `main`, `develop`

**Jobs:**

#### Lint & Code Quality (2 min)
- Black (code formatter)
- isort (import sorter)
- Flake8 (linter)
- mypy (type checker)
- Pylint

#### Unit Tests (10 min)
- Matrix: Python 3.10, 3.11, 3.12
- pytest with coverage
- Upload to Codecov
- Generate HTML report

#### Integration Tests (15 min)
- Services: PostgreSQL, Redis
- pytest integration suite
- Coverage report

#### Security Scan (5 min)
- Safety (dependency vulnerabilities)
- Bandit (security linter)
- Trivy (container scanner)
- Upload to GitHub Security

#### Build Docker (5 min)
- Multi-stage build
- Cache layers
- Save as artifact

#### PR Quality Check
- Conventional commits
- Branch naming
- Large files check
- Statistics comment

---

### 2. CD Workflow (`.github/workflows/cd.yml`)

**Triggers:**
- Push to `main`
- Tags `v*.*.*`
- Manual dispatch

**Jobs:**

#### Build & Push (5 min)
- Build production image
- Push to GitHub Container Registry
- Tag: latest, version, SHA

#### Deploy Staging (3 min)
- SSH to staging server
- Backup database
- Pull latest image
- Rolling update
- Health check

#### Deploy Production (5 min)
- **Manual approval required**
- Backup databases
- Blue-green deployment
- Health verification
- Rollback on failure

#### Rollback (Manual)
- Trigger via workflow_dispatch
- Specify version to rollback
- Automatic verification

---

### 3. Release Workflow (`.github/workflows/release.yml`)

**Triggers:**
- Manual dispatch with version input

**Jobs:**

#### Create Release
- Version bump (major/minor/patch)
- Generate changelog (categorized)
- Update version files
- Create GitHub release

#### Build Assets
- Source archive
- SHA256 checksum
- Upload to release

#### Notify
- Slack notification
- Email notification

---

## Branching Strategy

### GitFlow

```
main (production)
  │
  ├── develop (integration)
  │     │
  │     ├── feature/add-login
  │     ├── feature/api-v2
  │     └── bugfix/fix-crash
  │
  └── hotfix/security-patch
```

**Branch Types:**

| Branch | Purpose | Naming |
|--------|---------|--------|
| `main` | Production-ready code | `main` |
| `develop` | Integration branch | `develop` |
| `feature/*` | New features | `feature/description` |
| `bugfix/*` | Bug fixes | `bugfix/description` |
| `hotfix/*` | Emergency fixes | `hotfix/description` |
| `release/*` | Release preparation | `release/v1.2.3` |

**Workflow:**

1. **Feature development**
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/my-feature
   # ... work ...
   git push origin feature/my-feature
   # Create PR to develop
   ```

2. **Release**
   ```bash
   git checkout -b release/v1.2.0 develop
   # ... final testing ...
   git checkout main
   git merge release/v1.2.0
   git tag v1.2.0
   git push origin main --tags
   git checkout develop
   git merge release/v1.2.0
   ```

3. **Hotfix**
   ```bash
   git checkout -b hotfix/critical-bug main
   # ... fix ...
   git checkout main
   git merge hotfix/critical-bug
   git tag v1.2.1
   git checkout develop
   git merge hotfix/critical-bug
   ```

---

## Commit Convention

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(api): add user login endpoint` |
| `fix` | Bug fix | `fix(db): resolve connection timeout` |
| `docs` | Documentation | `docs: update API guide` |
| `style` | Formatting | `style: apply black formatting` |
| `refactor` | Code restructure | `refactor(api): simplify auth logic` |
| `test` | Add tests | `test: add unit tests for planner` |
| `chore` | Maintenance | `chore: update dependencies` |
| `perf` | Performance | `perf(db): add index on query_id` |
| `ci` | CI/CD changes | `ci: add security scan` |
| `build` | Build system | `build: update Dockerfile` |
| `revert` | Revert commit | `revert: revert "feat: add feature"` |

### Examples

```bash
# Good commits
feat(orchestrator): implement parallel agent execution
fix(api): handle rate limit edge case
docs(deployment): add scaling strategy guide
test(vee): add sandbox security tests

# Bad commits
updated files
fixed bug
changes
wip
```

---

## Deployment Stages

### Stage 1: Development (Local)

**Environment:** Developer machine
**Purpose:** Feature development
**Frequency:** Continuous

```bash
# Start local services
docker-compose -f docker-compose.dev.yml up -d

# Run in dev mode
uvicorn src.api.main:app --reload

# Run tests
pytest tests/unit/ -v
```

### Stage 2: Staging (Auto-deploy)

**Environment:** Staging server
**Purpose:** Integration testing
**Frequency:** Every main push

**Deployment:**
- Automatic on main push
- Rolling update (zero downtime)
- Health check required
- Rollback on failure

**URL:** https://staging.api.ape2026.com

### Stage 3: Production (Manual approval)

**Environment:** Production server
**Purpose:** Live service
**Frequency:** On release tags

**Deployment:**
- Manual approval required
- Blue-green deployment
- Database backup
- Gradual traffic shift
- Automatic rollback

**URL:** https://api.ape2026.com

---

## Health Checks

### Pre-deployment

```bash
# Code quality
black --check src/
flake8 src/
mypy src/

# Tests
pytest tests/ -v --cov=src

# Security
bandit -r src/
safety check
```

### Post-deployment

```bash
# API health
curl https://api.ape2026.com/health

# Expected response:
{
  "status": "healthy",
  "version": "1.2.3",
  "uptime": 12345,
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "neo4j": "healthy"
  }
}
```

### Monitoring

- **Response time:** < 200ms (p95)
- **Error rate:** < 1%
- **Availability:** > 99.9%
- **CPU usage:** < 70%
- **Memory usage:** < 80%

---

## Rollback Procedures

### Automatic Rollback

Triggers:
- Health check fails after deployment
- Error rate > 10% in first 5 minutes
- Response time > 5s

### Manual Rollback

Via GitHub Actions:

```
1. Go to Actions → CD → Run workflow
2. Select "workflow_dispatch"
3. Environment: production
4. Rollback version: v1.2.2
5. Click "Run workflow"
```

Via SSH:

```bash
ssh production-server
cd /opt/ape-2026

# List available versions
docker images ghcr.io/yourorg/ape-2026/api

# Rollback
docker-compose down api
docker tag ghcr.io/yourorg/ape-2026/api:v1.2.2 ape-2026/api:latest
docker-compose up -d api
```

---

## Monitoring & Alerts

### Metrics

**CI/CD Metrics:**
- Build success rate
- Average build time
- Deployment frequency
- Lead time for changes
- Mean time to recovery (MTTR)

**Application Metrics:**
- Request rate
- Error rate
- Response time (p50, p95, p99)
- Active connections
- Queue depth

### Alerts

**Critical (PagerDuty):**
- Production deployment failed
- Error rate > 5%
- Service down

**Warning (Slack):**
- Test failures on main
- Security vulnerabilities
- Staging deployment issues

**Info (Slack):**
- Successful deployments
- New releases
- PR statistics

---

## Best Practices

### ✅ Do

1. **Write tests first** (TDD)
2. **Keep PRs small** (<300 lines)
3. **Use feature flags** for risky changes
4. **Run CI locally** before pushing
5. **Review security scans** before merging
6. **Tag releases** with semantic versions
7. **Document breaking changes**
8. **Test rollback procedures** regularly

### ❌ Don't

1. **Don't skip tests** to make CI pass faster
2. **Don't commit to main** directly
3. **Don't ignore security warnings**
4. **Don't deploy on Fridays** (unless critical)
5. **Don't use --force** on main/develop
6. **Don't ignore failed CI** ("works on my machine")
7. **Don't deploy untested code**
8. **Don't skip code review**

---

## Troubleshooting

### CI Fails on Lint

```bash
# Fix locally
black src/ tests/
isort src/ tests/
flake8 src/ tests/

# Commit fixes
git add -A
git commit -m "style: apply code formatting"
git push
```

### Tests Fail in CI but Pass Locally

**Possible causes:**
1. Environment differences (Python version)
2. Missing dependencies
3. Timing issues (increase timeouts)
4. Database state (use fixtures)

**Solutions:**
```bash
# Match CI environment
python --version  # Should be 3.11
pip install -r requirements-dev.txt

# Run tests in Docker
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Deployment Fails

**Check logs:**
```bash
# GitHub Actions
# Go to Actions → Failed workflow → View logs

# Server logs
ssh server "cd /opt/ape-2026 && docker-compose logs api"
```

**Common fixes:**
1. Check environment variables
2. Verify database migration
3. Increase health check timeout
4. Check disk space

---

## Performance Optimization

### Build Time

**Before:** 15 minutes
**After:** 5 minutes (67% reduction)

**Optimizations:**
1. Layer caching (Docker)
2. Parallel test execution (pytest-xdist)
3. Matrix parallelization (GitHub Actions)
4. Dependency caching (pip cache)

### Deployment Time

**Before:** 10 minutes
**After:** 3 minutes (70% reduction)

**Optimizations:**
1. Pre-built Docker images
2. Blue-green deployment (no downtime)
3. Database backup in parallel
4. Skip unnecessary services

---

## Security

### Code Scanning

- **Bandit:** Python security linter
- **Safety:** Dependency vulnerabilities
- **Trivy:** Container image scanning
- **CodeQL:** Semantic code analysis
- **Secret detection:** detect-secrets

### Access Control

- **Branch protection:** main, develop
- **Required reviews:** 1 for develop, 2 for main
- **Status checks:** All CI jobs must pass
- **Signed commits:** Recommended
- **Environment secrets:** Encrypted at rest

---

## Checklist

### Before First Deploy

- [ ] GitHub secrets configured
- [ ] SSH access to servers verified
- [ ] Slack/email notifications tested
- [ ] Pre-commit hooks installed
- [ ] Branch protection rules set
- [ ] Environment protection configured
- [ ] Monitoring dashboards created
- [ ] Rollback procedure tested
- [ ] Team trained on workflow
- [ ] Documentation reviewed

---

**Last Updated:** Week 7 Day 4
**Next Review:** Week 8 Day 1

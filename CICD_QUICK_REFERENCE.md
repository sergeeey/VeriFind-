# 🚀 CI/CD Quick Reference
**APE 2026 - GitHub Actions Cheat Sheet**

---

## Quick Start

```bash
# 1. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes and commit
git add .
git commit -m "feat: add new feature"

# 4. Push and create PR
git push origin feature/my-feature
# Then create PR via GitHub UI

# 5. After PR merge, deploy automatically
# Staging: Auto-deployed
# Production: Manual approval required
```

---

## GitHub Actions Workflows

### Trigger CI Manually

```bash
# Via GitHub CLI
gh workflow run ci.yml

# Via web UI
# Go to Actions → CI → Run workflow
```

### Trigger Deployment

```bash
# Deploy to staging
git push origin main

# Deploy to production
git tag v1.2.3
git push origin v1.2.3

# Manual deployment via CLI
gh workflow run cd.yml -f environment=production
```

### Create Release

```bash
# Via GitHub CLI
gh workflow run release.yml -f version=1.2.3 -f release_type=minor

# Via web UI
# Actions → Release → Run workflow
# - Version: 1.2.3
# - Release type: minor
# - Pre-release: false
```

### Rollback

```bash
# Via workflow
gh workflow run cd.yml -f environment=production -f rollback_version=v1.2.2

# Via Docker
ssh production-server
docker-compose down api
docker pull ghcr.io/yourorg/ape-2026/api:v1.2.2
docker-compose up -d api
```

---

## Pre-commit Hooks

```bash
# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run flake8 --all-files

# Skip hooks (not recommended)
git commit --no-verify -m "message"

# Update hooks
pre-commit autoupdate
```

---

## Local CI Simulation

```bash
# Lint
black --check src/ tests/
isort --check src/ tests/
flake8 src/ tests/
mypy src/

# Test
pytest tests/unit/ -v --cov=src
pytest tests/integration/ -v

# Security scan
bandit -r src/
safety check

# Build Docker image
docker build -t ape-2026/api:test .

# Run full test suite
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Example |
|------|---------|
| `feat` | `feat(api): add login endpoint` |
| `fix` | `fix(db): resolve timeout issue` |
| `docs` | `docs: update deployment guide` |
| `test` | `test: add unit tests for API` |
| `refactor` | `refactor: simplify auth logic` |
| `chore` | `chore: update dependencies` |
| `ci` | `ci: add security scan` |

### Good Commits

```bash
git commit -m "feat(orchestrator): implement parallel execution"
git commit -m "fix(api): handle rate limit edge case"
git commit -m "docs(cicd): add rollback procedure"
git commit -m "test(vee): add sandbox security tests"
```

### Bad Commits (Will Fail)

```bash
# These will be rejected by pre-commit
git commit -m "updated files"
git commit -m "fixed bug"
git commit -m "wip"
```

---

## Branch Management

### Create Feature Branch

```bash
git checkout develop
git pull
git checkout -b feature/my-feature
```

### Update from develop

```bash
git checkout develop
git pull
git checkout feature/my-feature
git rebase develop
```

### Create PR

```bash
# Push branch
git push origin feature/my-feature

# Create PR via CLI
gh pr create --base develop --head feature/my-feature \
  --title "feat: add new feature" \
  --body "Description of changes"

# Or via web UI
```

---

## Monitoring CI/CD

### View Workflow Status

```bash
# List recent runs
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>

# Download logs
gh run download <run-id>

# Watch live
gh run watch <run-id>
```

### Check Build Status

```bash
# Current branch
gh pr checks

# Specific PR
gh pr checks 123

# Detailed view
gh pr checks --watch
```

---

## Deployment

### Staging

**Automatic:** Push to `main`

```bash
git checkout main
git merge develop
git push origin main
# Wait 25 minutes for automatic deployment
```

**Verify:**
```bash
curl https://staging.api.ape2026.com/health
```

### Production

**Via Tag:**
```bash
git tag v1.2.3
git push origin v1.2.3
# Manual approval required
```

**Via Workflow:**
```bash
gh workflow run cd.yml -f environment=production
```

**Verify:**
```bash
curl https://api.ape2026.com/health
```

---

## Troubleshooting

### CI Fails on Lint

```bash
# Auto-fix
black src/ tests/
isort src/ tests/

# Verify
flake8 src/ tests/

# Commit
git add -A
git commit -m "style: apply code formatting"
git push
```

### Tests Fail in CI

```bash
# Run same environment
docker run -it --rm \
  -v $(pwd):/app \
  python:3.11 \
  bash -c "cd /app && pip install -r requirements-dev.txt && pytest tests/"
```

### Deployment Fails

```bash
# Check workflow logs
gh run view --log-failed

# SSH to server and check
ssh production-server
cd /opt/ape-2026
docker-compose logs api --tail=100

# Rollback
gh workflow run cd.yml -f environment=production -f rollback_version=v1.2.2
```

---

## GitHub CLI Commands

### Workflows

```bash
# List workflows
gh workflow list

# View workflow
gh workflow view ci.yml

# Enable/disable
gh workflow enable ci.yml
gh workflow disable ci.yml
```

### Secrets

```bash
# List secrets
gh secret list

# Set secret
gh secret set SECRET_NAME < secret.txt
echo "value" | gh secret set SECRET_NAME

# Delete secret
gh secret delete SECRET_NAME
```

### Pull Requests

```bash
# Create PR
gh pr create

# List PRs
gh pr list

# View PR
gh pr view 123

# Check status
gh pr checks 123

# Merge PR
gh pr merge 123 --squash
```

### Releases

```bash
# List releases
gh release list

# View release
gh release view v1.2.3

# Create release
gh release create v1.2.3 \
  --title "Release v1.2.3" \
  --notes "Release notes"
```

---

## Environment Variables

### Local Development

```bash
# Copy template
cp .env.development.template .env

# Edit variables
nano .env

# Load in shell
export $(cat .env | xargs)
```

### GitHub Secrets

```bash
# Set from file
gh secret set STAGING_SSH_KEY < ~/.ssh/id_rsa

# Set from stdin
echo "my-secret-value" | gh secret set MY_SECRET

# Set interactively
gh secret set MY_SECRET
# Paste value and press Ctrl+D
```

---

## Docker Registry

### Login

```bash
# GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Docker Hub
docker login -u USERNAME
```

### Pull Images

```bash
# Latest
docker pull ghcr.io/yourorg/ape-2026/api:latest

# Specific version
docker pull ghcr.io/yourorg/ape-2026/api:v1.2.3

# By SHA
docker pull ghcr.io/yourorg/ape-2026/api:main-abc123
```

### Push Images

```bash
# Tag
docker tag ape-2026/api:latest ghcr.io/yourorg/ape-2026/api:v1.2.3

# Push
docker push ghcr.io/yourorg/ape-2026/api:v1.2.3
```

---

## Common Tasks

### Run Full CI Locally

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Lint
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/

# Test
pytest tests/ -v --cov=src

# Security
bandit -r src/
safety check

# Build
docker build -t ape-2026/api:test .
```

### Update Dependencies

```bash
# Update requirements
pip-compile requirements.in > requirements.txt
pip-compile requirements-dev.in > requirements-dev.txt

# Test locally
pip install -r requirements.txt
pytest tests/

# Commit
git add requirements.txt requirements-dev.txt
git commit -m "chore: update dependencies"
```

### Emergency Hotfix

```bash
# Create hotfix branch
git checkout main
git pull
git checkout -b hotfix/critical-bug

# Fix and test
# ... make changes ...
pytest tests/

# Commit and push
git add -A
git commit -m "fix: resolve critical bug"
git push origin hotfix/critical-bug

# Create PR to main
gh pr create --base main

# After merge, tag release
git checkout main
git pull
git tag v1.2.4
git push origin v1.2.4
```

---

## Health Checks

### API

```bash
curl https://api.ape2026.com/health
```

### Staging

```bash
curl https://staging.api.ape2026.com/health
```

### Full Check

```bash
# API
curl https://api.ape2026.com/health | jq

# Docs
curl https://api.ape2026.com/docs

# OpenAPI
curl https://api.ape2026.com/openapi.json | jq
```

---

## Useful Links

- **Actions Dashboard:** https://github.com/yourorg/ape-2026/actions
- **Staging:** https://staging.api.ape2026.com
- **Production:** https://api.ape2026.com
- **Grafana:** https://grafana.ape2026.com
- **Prometheus:** https://prometheus.ape2026.com

---

**Quick Reference Version:** 1.0.0
**Last Updated:** Week 7 Day 4

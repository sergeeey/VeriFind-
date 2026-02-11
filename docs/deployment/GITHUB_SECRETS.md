# GitHub Secrets Configuration
**Week 7 Day 4 - CI/CD Pipeline**

## Overview

GitHub Secrets are used to securely store sensitive information needed for CI/CD workflows. This document lists all required secrets and how to configure them.

---

## Required Secrets

### Repository Secrets

Navigate to: **Settings → Secrets and variables → Actions → New repository secret**

#### Staging Environment

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `STAGING_HOST` | Staging server hostname/IP | `staging.ape2026.com` |
| `STAGING_USER` | SSH username for staging | `ubuntu` |
| `STAGING_SSH_KEY` | Private SSH key for staging | `<SSH_PRIVATE_KEY_PEM_CONTENT>` |

#### Production Environment

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `PRODUCTION_HOST` | Production server hostname/IP | `api.ape2026.com` |
| `PRODUCTION_USER` | SSH username for production | `ubuntu` |
| `PRODUCTION_SSH_KEY` | Private SSH key for production | `<SSH_PRIVATE_KEY_PEM_CONTENT>` |

#### Notifications

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `SLACK_WEBHOOK` | Slack webhook URL for notifications | `https://hooks.slack.com/services/...` |
| `SMTP_SERVER` | SMTP server for email notifications | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USERNAME` | SMTP username | `notifications@ape2026.com` |
| `SMTP_PASSWORD` | SMTP password | `your-smtp-password` |
| `NOTIFICATION_EMAIL` | Email for release notifications | `team@ape2026.com` |

#### Docker Registry (Optional)

If using external registry (e.g., Docker Hub):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DOCKER_USERNAME` | Docker registry username | `ape2026` |
| `DOCKER_PASSWORD` | Docker registry password | `your-password` |

---

## Environment Secrets

For environment-specific secrets, navigate to: **Settings → Environments → [Environment Name] → Add secret**

### Staging Environment

Create environment: `staging`

| Secret Name | Description |
|-------------|-------------|
| `CLAUDE_API_KEY` | Anthropic API key (staging) |
| `DEEPSEEK_API_KEY` | DeepSeek API key (staging) |
| `POSTGRES_PASSWORD` | Database password (staging) |
| `NEO4J_PASSWORD` | Neo4j password (staging) |
| `SECRET_KEY` | Application secret key (staging) |

### Production Environment

Create environment: `production`

| Secret Name | Description |
|-------------|-------------|
| `CLAUDE_API_KEY` | Anthropic API key (production) |
| `DEEPSEEK_API_KEY` | DeepSeek API key (production) |
| `POSTGRES_PASSWORD` | Database password (production) |
| `NEO4J_PASSWORD` | Neo4j password (production) |
| `SECRET_KEY` | Application secret key (production) |

---

## Setup Instructions

### 1. Generate SSH Keys

```bash
# On your local machine
ssh-keygen -t rsa -b 4096 -C "github-actions@ape2026.com" -f ~/.ssh/github_actions_rsa

# Copy public key to server
ssh-copy-id -i ~/.ssh/github_actions_rsa.pub user@server

# Copy private key content for GitHub secret
cat ~/.ssh/github_actions_rsa
# Copy entire output including BEGIN/END lines
```

### 2. Add Secrets to GitHub

```bash
# Using GitHub CLI
gh secret set STAGING_SSH_KEY < ~/.ssh/github_actions_rsa

# Or manually via Web UI:
# 1. Go to repository → Settings → Secrets
# 2. Click "New repository secret"
# 3. Paste secret content
# 4. Click "Add secret"
```

### 3. Configure Slack Webhook

1. Go to Slack workspace → Apps → Incoming Webhooks
2. Click "Add to Slack"
3. Choose channel (e.g., #deployments)
4. Copy webhook URL
5. Add to GitHub as `SLACK_WEBHOOK` secret

### 4. Configure SMTP (Gmail Example)

```bash
# For Gmail:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com

# Generate App Password:
# 1. Go to Google Account → Security
# 2. Enable 2-Step Verification
# 3. App passwords → Generate password
# 4. Use generated password as SMTP_PASSWORD
```

### 5. Environment Protection Rules

**Staging:**
- No protection (auto-deploy on main push)

**Production:**
- Required reviewers: 1-2 people
- Wait timer: 5 minutes
- Restrict to specific branches: `main`, `release/*`

Configure at: **Settings → Environments → production → Protection rules**

---

## Secret Rotation

### Recommended Schedule

| Secret Type | Rotation Frequency |
|-------------|-------------------|
| SSH Keys | Every 6 months |
| API Keys | Every 3 months |
| Database Passwords | Every 6 months |
| SMTP Passwords | Every 6 months |
| Application Secret Key | Every year |

### Rotation Procedure

1. **Generate new secret** (e.g., new SSH key)
2. **Add to both GitHub and server** (dual operation)
3. **Test in staging** environment
4. **Deploy to production** during low-traffic period
5. **Remove old secret** after 24-hour grace period
6. **Document rotation** in changelog

---

## Security Best Practices

### ✅ Do

- **Use environment-specific secrets** (staging ≠ production)
- **Rotate secrets regularly** (see schedule above)
- **Use least privilege** (SSH user with minimal permissions)
- **Audit secret usage** (check workflow logs)
- **Use GitHub CLI** for bulk secret updates
- **Document all secrets** (not values, just names/purpose)

### ❌ Don't

- **Never commit secrets** to repository
- **Don't share secrets** between environments
- **Don't use production secrets** in CI tests
- **Don't print secrets** in workflow logs
- **Don't reuse secrets** across projects
- **Don't use weak passwords** (min 20 chars, random)

---

## Testing Secrets

### Dry Run

Test workflow with secrets without deploying:

```yaml
# .github/workflows/test-secrets.yml
name: Test Secrets

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test SSH connection
        run: |
          echo "${{ secrets.STAGING_SSH_KEY }}" > /tmp/key
          chmod 600 /tmp/key
          ssh -o StrictHostKeyChecking=no -i /tmp/key ${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }} "echo Connection successful"
          rm /tmp/key

      - name: Test Slack notification
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Test notification from GitHub Actions"}' \
            ${{ secrets.SLACK_WEBHOOK }}
```

### Verify Secrets

```bash
# List configured secrets (names only, not values)
gh secret list

# Check if specific secret exists
gh secret list | grep STAGING_SSH_KEY
```

---

## Troubleshooting

### SSH Connection Failed

**Symptom:** `Permission denied (publickey)`

**Solutions:**
1. Verify SSH key format (should include BEGIN/END lines)
2. Check key permissions on server (`~/.ssh/authorized_keys` should be 600)
3. Verify username matches server user
4. Test manually: `ssh -i /tmp/key user@host`

### Slack Webhook 404

**Symptom:** `404 Not Found` when posting to webhook

**Solutions:**
1. Regenerate webhook URL in Slack
2. Verify channel still exists
3. Check webhook hasn't been revoked

### Secret Not Found

**Symptom:** `secret not found: SECRET_NAME`

**Solutions:**
1. Verify secret name spelling (case-sensitive)
2. Check if secret is in correct scope (repo vs environment)
3. Ensure environment name matches workflow

---

## Secret Templates

### SSH Key Template

```text
<SSH_PRIVATE_KEY_PEM_CONTENT>
```

### Slack Webhook Template

```text
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

### SMTP Password Template

```text
abcd efgh ijkl mnop  # Gmail App Password format
```

---

## Checklist

Before running CI/CD for the first time:

- [ ] SSH keys generated and added
- [ ] Staging secrets configured
- [ ] Production secrets configured
- [ ] Slack webhook tested
- [ ] SMTP credentials verified
- [ ] Environment protection rules set
- [ ] Secrets documented in team wiki
- [ ] Rotation schedule in calendar
- [ ] Team trained on secret rotation

---

## Support

**Questions?**
- GitHub Secrets Docs: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- Team wiki: Internal documentation
- Slack: #devops channel

**Issues?**
- Check workflow logs for error messages
- Verify secret values haven't expired
- Contact DevOps team

---

**Last Updated:** Week 7 Day 4
**Next Review:** Week 8 Day 1

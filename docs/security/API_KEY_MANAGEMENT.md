# API Key Management Strategy

**Document Version:** 1.0  
**Last Updated:** 2026-02-10  
**Status:** MVP / Beta Stage  

---

## Current State (MVP/Beta)

### Approach: Local .env File Storage

For the current **solo developer MVP stage**, API keys are stored in the `.env` file:

```
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIzaSy...
FRED_API_KEY=196e5f...
```

### Security Measures in Place

✅ **.gitignore configured** - `.env` file is NOT committed to Git  
✅ **Local filesystem only** - Keys never leave developer machine  
✅ **Physical security** - Machine access controlled  
✅ **No team sharing** - Solo developer only  

### Verification

```bash
# Verify .env is NOT in Git
git ls-files | grep "^\.env$"
# Expected: (no output)

# Verify .gitignore includes .env
grep "^\.env$" .gitignore
# Expected: .env
```

---

## Risk Assessment

| Risk Factor | Level | Mitigation |
|-------------|-------|------------|
| Public exposure | 🟢 LOW | .gitignore prevents Git commit |
| Local access | 🟡 MEDIUM | Machine access control |
| Backup exposure | 🟡 MEDIUM | Ensure backups are encrypted |
| Accidental sharing | 🟡 MEDIUM | Training + code review |
| Team expansion | 🔴 HIGH | **MUST migrate before adding team** |

### Acceptable For:
- ✅ Solo developer
- ✅ Local development
- ✅ MVP/Beta stage
- ✅ Prototype/demo

### NOT Acceptable For:
- ❌ Team development (>1 person)
- ❌ Cloud deployment (AWS/GCP/Azure)
- ❌ Production with customer data
- ❌ Compliance requirements (SOC2, GDPR)

---

## Future Migration Plan (Before Production)

### Phase 1: Secrets Manager (Required before team expansion)

**Recommended: HashiCorp Vault**

```bash
# Install Vault
docker run -d --name vault -p 8200:8200 hashicorp/vault

# Store secrets
vault kv put secret/ape-2026 DEEPSEEK_API_KEY=sk-...
vault kv put secret/ape-2026 ANTHROPIC_API_KEY=sk-ant-...

# Application reads from Vault
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=s.xxx
```

**Alternative: Cloud Provider Secrets**
- AWS Secrets Manager
- GCP Secret Manager  
- Azure Key Vault

### Phase 2: Environment Variables (Cloud deployment)

```bash
# Kubernetes secrets
kubectl create secret generic api-keys \
  --from-literal=DEEPSEEK_API_KEY=sk-... \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...

# Reference in deployment
env:
  - name: DEEPSEEK_API_KEY
    valueFrom:
      secretKeyRef:
        name: api-keys
        key: DEEPSEEK_API_KEY
```

### Phase 3: Runtime Secret Injection

```python
# src/api/config.py (future)
import hvac  # HashiCorp Vault client

class Settings(BaseSettings):
    @property
    def DEEPSEEK_API_KEY(self) -> str:
        # Read from Vault at runtime
        client = hvac.Client(url=os.getenv("VAULT_ADDR"))
        secret = client.secrets.kv.v2.read_secret_version(
            path="ape-2026"
        )
        return secret["data"]["data"]["DEEPSEEK_API_KEY"]
```

---

## Action Items

### Before Team Expansion:
- [ ] Set up HashiCorp Vault or cloud secrets manager
- [ ] Migrate all API keys from .env to secrets manager
- [ ] Update application code to read from secrets manager
- [ ] Document secret rotation procedure
- [ ] Train team on secure key handling

### Before Cloud Deployment:
- [ ] Configure Kubernetes secrets or cloud provider secrets
- [ ] Enable secret encryption at rest
- [ ] Set up secret rotation automation
- [ ] Implement audit logging for secret access

### Before Production:
- [ ] Complete security audit
- [ ] Penetration testing
- [ ] Compliance review (if required)
- [ ] Incident response plan for key compromise

---

## Security Guidelines

### DO:
- ✅ Keep `.env` in `.gitignore`
- ✅ Use strong, unique passwords for each service
- ✅ Rotate keys periodically (every 90 days)
- ✅ Monitor API usage for anomalies
- ✅ Use separate keys for dev/staging/prod
- ✅ Enable 2FA on all API provider accounts

### DON'T:
- ❌ NEVER commit `.env` to Git
- ❌ NEVER share `.env` via email/Slack/Discord
- ❌ NEVER upload `.env` to cloud storage
- ❌ NEVER hardcode keys in source code
- ❌ NEVER use production keys in development
- ❌ NEVER log API keys (even partially)

---

## Incident Response

### If API Key is Compromised:

1. **Immediate (within 1 hour):**
   ```bash
   # Revoke compromised key via provider dashboard
   # DeepSeek: https://platform.deepseek.com/
   # Anthropic: https://console.anthropic.com/
   # OpenAI: https://platform.openai.com/
   ```

2. **Short-term (within 24 hours):**
   - Generate new key
   - Update .env file
   - Restart services
   - Check API usage logs for unauthorized access

3. **Long-term (within 1 week):**
   - Security audit
   - Update incident response plan
   - Team training (if applicable)

---

## Compliance Notes

### Current State (MVP):
- Not subject to compliance requirements
- Internal tool/demo only
- No customer data

### Future (Production):
- May require SOC 2 Type II
- GDPR if handling EU data
- Financial regulations if providing investment advice

**Action:** Revisit this document before production deployment.

---

## Contact

For security questions or incidents:
- Security Lead: [Your Name]
- Email: [your-email]
- Emergency: [your-phone]

---

**Document Owner:** Security Team  
**Review Schedule:** Monthly (MVP), Weekly (Production)  
**Next Review:** 2026-03-10

# Environment Setup — APE 2026

**Recommended Environment:** Python 3.11.11
**Why:** SQLAlchemy 2.0.27 compatibility issues with Python 3.13+

---

## Quick Start

### Option 1: Use ape311 environment (Recommended)

```bash
# Activate environment
conda activate ape311

# Verify Python version
python --version  # Should be 3.11.11

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -v
```

### Option 2: Current environment (Python 3.13)

**Note:** Some integration tests may fail due to SQLAlchemy/Python 3.13 incompatibility.

**Works:**
- ✅ Core functionality (debate, compliance, Golden Set)
- ✅ Unit tests
- ✅ Regression tests
- ✅ Golden Set validation

**May fail:**
- ❌ Some API integration tests (SQLAlchemy errors)
- ❌ Database-heavy tests

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# Required API Keys
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
FRED_API_KEY=...

# Database (optional, uses defaults if not set)
TIMESCALEDB_URL=postgresql://ape:password@localhost:5432/ape_timeseries
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## Validation Script

```bash
# Validate environment before starting
python scripts/validate_env.py

# Expected output:
# ✅ Python version: 3.11.11
# ✅ All required packages installed
# ✅ All API keys present
# ✅ Database connections working
```

---

## Troubleshooting

### SQLAlchemy errors with Python 3.13

```
AssertionError: Class <class 'sqlalchemy.sql.elements.SQLCoreOperations'>
directly inherits TypingOnly but has additional attributes
```

**Solution:** Use Python 3.11 (ape311 environment)

### Missing API keys

```
ValueError: DEEPSEEK_API_KEY not found in environment
```

**Solution:** Copy `.env.example` to `.env` and add your keys

### Database connection errors

```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
```bash
# Start databases
docker-compose up -d

# Verify
docker-compose ps
```

---

Last Updated: 2026-02-14

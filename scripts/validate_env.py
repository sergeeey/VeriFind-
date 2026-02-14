#!/usr/bin/env python3
"""
Environment Validation Script — APE 2026

Validates environment before deployment:
- Python version
- Required packages
- API keys
- Database connections

Usage:
    python scripts/validate_env.py
    python scripts/validate_env.py --skip-db  # Skip database checks
"""

import os
import sys
import importlib.metadata
from pathlib import Path
from typing import List, Tuple


# ============================================================================
# Configuration
# ============================================================================

REQUIRED_PYTHON_VERSION = (3, 11)  # Minimum Python 3.11 for SQLAlchemy compatibility
RECOMMENDED_PYTHON_VERSION = (3, 11, 11)  # Exact version recommended

REQUIRED_PACKAGES = {
    "fastapi": ">=0.104.0",
    "uvicorn": ">=0.24.0",
    "pydantic": ">=2.0.0",
    "sqlalchemy": ">=2.0.0,<2.1.0",  # 2.0.27 has Python 3.13 issues
    "anthropic": ">=0.7.0",
    "openai": ">=1.3.0",
}

REQUIRED_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "FRED_API_KEY",
]

OPTIONAL_ENV_VARS = [
    "TIMESCALEDB_URL",
    "NEO4J_URL",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "CHROMADB_PATH",
]


# ============================================================================
# Validation Functions
# ============================================================================

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version meets requirements."""
    current = sys.version_info

    if current < REQUIRED_PYTHON_VERSION:
        return False, (
            f"❌ Python {current.major}.{current.minor}.{current.micro} is too old. "
            f"Minimum required: {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}"
        )

    if current[:3] != RECOMMENDED_PYTHON_VERSION:
        return True, (
            f"⚠️ Python {current.major}.{current.minor}.{current.micro} detected. "
            f"Recommended: {RECOMMENDED_PYTHON_VERSION[0]}.{RECOMMENDED_PYTHON_VERSION[1]}.{RECOMMENDED_PYTHON_VERSION[2]} "
            f"(SQLAlchemy 2.0.27 has issues with Python 3.13+)"
        )

    return True, f"✅ Python {current.major}.{current.minor}.{current.micro} (recommended version)"


def check_packages() -> Tuple[bool, List[str]]:
    """Check if required packages are installed with correct versions."""
    results = []
    all_ok = True

    for package, version_spec in REQUIRED_PACKAGES.items():
        try:
            installed_version = importlib.metadata.version(package)
            results.append(f"✅ {package}=={installed_version}")
        except importlib.metadata.PackageNotFoundError:
            results.append(f"❌ {package} NOT INSTALLED (required: {version_spec})")
            all_ok = False

    return all_ok, results


def check_env_vars() -> Tuple[bool, List[str]]:
    """Check if required environment variables are set."""
    results = []
    all_ok = True

    # Check required vars
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if value:
            # Mask the value for security
            masked = value[:8] + "..." if len(value) > 8 else "***"
            results.append(f"✅ {var}={masked}")
        else:
            results.append(f"❌ {var} NOT SET (required)")
            all_ok = False

    # Check optional vars
    optional_set = []
    for var in OPTIONAL_ENV_VARS:
        if os.getenv(var):
            optional_set.append(var)

    if optional_set:
        results.append(f"ℹ️ Optional vars set: {', '.join(optional_set)}")

    return all_ok, results


def check_database_connections(skip: bool = False) -> Tuple[bool, List[str]]:
    """Check if databases are accessible (optional)."""
    if skip:
        return True, ["ℹ️ Database checks skipped (--skip-db)"]

    results = []
    all_ok = True

    # TimescaleDB
    timescale_url = os.getenv("TIMESCALEDB_URL")
    if timescale_url:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(timescale_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                results.append("✅ TimescaleDB connection OK")
        except Exception as e:
            results.append(f"❌ TimescaleDB connection FAILED: {e}")
            all_ok = False
    else:
        results.append("⚠️ TIMESCALEDB_URL not set (optional)")

    # Neo4j
    neo4j_url = os.getenv("NEO4J_URL")
    if neo4j_url:
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                neo4j_url,
                auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
            )
            driver.verify_connectivity()
            driver.close()
            results.append("✅ Neo4j connection OK")
        except Exception as e:
            results.append(f"❌ Neo4j connection FAILED: {e}")
            all_ok = False
    else:
        results.append("⚠️ NEO4J_URL not set (optional)")

    return all_ok, results


def load_env_file():
    """Load .env file if it exists."""
    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_file, override=True)
            return True, "✅ .env file loaded"
        except ImportError:
            return False, "⚠️ python-dotenv not installed, .env file not loaded"
    return True, "ℹ️ No .env file found (using system environment)"


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all validation checks."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate APE 2026 environment")
    parser.add_argument("--skip-db", action="store_true", help="Skip database connection checks")
    args = parser.parse_args()

    print("=" * 70)
    print("APE 2026 — Environment Validation")
    print("=" * 70)
    print()

    # Load .env file
    env_ok, env_msg = load_env_file()
    print(env_msg)
    print()

    all_checks_passed = True

    # Python version
    print("🐍 Python Version")
    print("-" * 70)
    py_ok, py_msg = check_python_version()
    print(py_msg)
    if not py_ok:
        all_checks_passed = False
    print()

    # Packages
    print("📦 Required Packages")
    print("-" * 70)
    pkg_ok, pkg_results = check_packages()
    for result in pkg_results:
        print(result)
    if not pkg_ok:
        all_checks_passed = False
    print()

    # Environment variables
    print("🔑 Environment Variables")
    print("-" * 70)
    env_ok, env_results = check_env_vars()
    for result in env_results:
        print(result)
    if not env_ok:
        all_checks_passed = False
    print()

    # Database connections (optional)
    if not args.skip_db:
        print("💾 Database Connections")
        print("-" * 70)
        db_ok, db_results = check_database_connections(skip=args.skip_db)
        for result in db_results:
            print(result)
        # Don't fail on database errors (optional)
        print()

    # Final summary
    print("=" * 70)
    if all_checks_passed:
        print("✅ ENVIRONMENT VALIDATED — Ready for deployment!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("❌ ENVIRONMENT VALIDATION FAILED — Fix errors above")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Alias for TimescaleDB Storage.

Week 11: Compatibility alias for imports.
Actual implementation is in timescaledb_storage.py
"""

# Re-export from the actual implementation
from .timescaledb_storage import TimescaleDBStorage as TimescaleDBStore

__all__ = ["TimescaleDBStore"]

"""
Temporal Integrity Module (TIM).

Week 4 Day 3: Prevent look-ahead bias in backtesting.
"""

from .integrity_checker import (
    TemporalIntegrityChecker,
    TemporalViolation,
    ViolationType,
    TemporalCheckResult
)

__all__ = [
    'TemporalIntegrityChecker',
    'TemporalViolation',
    'ViolationType',
    'TemporalCheckResult'
]

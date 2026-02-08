"""
Optimization module for APE components.

Week 5 Day 1: DSPy-based prompt optimization infrastructure.
Week 5 Day 4: DeepSeek R1 integration for real optimization.
"""

from .plan_optimizer import PlanOptimizer
from .metrics import (
    CodeQualityMetric,
    ExecutabilityMetric,
    TemporalValidityMetric,
    CompositeMetric
)
from .deepseek_adapter import (
    DeepSeekR1,
    configure_deepseek,
    estimate_cost,
    DEEPSEEK_PRICING
)

__all__ = [
    'PlanOptimizer',
    'CodeQualityMetric',
    'ExecutabilityMetric',
    'TemporalValidityMetric',
    'CompositeMetric',
    'DeepSeekR1',
    'configure_deepseek',
    'estimate_cost',
    'DEEPSEEK_PRICING'
]

"""
Reasoning module for APE 2026.

Week 10: Advanced reasoning capabilities including:
- Multi-hop queries (Day 1)
- Reasoning chains (Day 2)
- Query decomposition
"""

from .multi_hop import (
    QueryDecomposer,
    DependencyGraph,
    MultiHopOrchestrator,
    SubQuery,
    QueryType
)

from .chains import (
    ReasoningStep,
    ReasoningChain,
    ReasoningChainBuilder,
    StepAction,
    ChainResult
)

__all__ = [
    # Multi-hop (Day 1)
    "QueryDecomposer",
    "DependencyGraph",
    "MultiHopOrchestrator",
    "SubQuery",
    "QueryType",
    # Reasoning Chains (Day 2)
    "ReasoningStep",
    "ReasoningChain",
    "ReasoningChainBuilder",
    "StepAction",
    "ChainResult"
]

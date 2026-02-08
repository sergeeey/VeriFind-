"""
Reasoning module for APE 2026.

Week 10: Advanced reasoning capabilities including:
- Multi-hop queries
- Reasoning chains
- Query decomposition
"""

from .multi_hop import (
    QueryDecomposer,
    DependencyGraph,
    MultiHopOrchestrator,
    SubQuery,
    QueryType
)

__all__ = [
    "QueryDecomposer",
    "DependencyGraph",
    "MultiHopOrchestrator",
    "SubQuery",
    "QueryType"
]

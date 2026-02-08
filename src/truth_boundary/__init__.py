"""
Truth Boundary — Zero-Hallucination Enforcement.

Week 2 Day 3: Verifies that LLMs generate CODE, not numbers.

Core principle:
- LLM outputs Python code
- VEE executes code in sandbox
- Gate extracts ONLY numerical outputs from execution
- All facts are verifiable and auditable
"""

from .gate import TruthBoundaryGate, VerifiedFact, ValidationResult

__all__ = ["TruthBoundaryGate", "VerifiedFact", "ValidationResult"]

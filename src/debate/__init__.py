"""
Debate module for APE 2026.

Week 10 Day 3: LLM-powered multi-perspective analysis.
Replaces rule-based debate with nuanced LLM-generated perspectives.
"""

from .llm_debate import (
    DebatePerspective,
    DebateResult,
    LLMDebateNode,
    DebateValidator,
    DebatePromptBuilder
)

__all__ = [
    "DebatePerspective",
    "DebateResult",
    "LLMDebateNode",
    "DebateValidator",
    "DebatePromptBuilder"
]

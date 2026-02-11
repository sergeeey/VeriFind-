"""
Debate module for APE 2026.

Week 10 Day 3: LLM-powered multi-perspective analysis.
Week 12+: Multi-LLM parallel debate (Bull/Bear/Arbiter).

Replaces rule-based debate with nuanced LLM-generated perspectives.
"""

from .llm_debate import (
    DebatePerspective,
    DebateResult,
    LLMDebateNode,
    DebateValidator,
    DebatePromptBuilder
)

# Week 12+ Multi-LLM agents
try:
    from .multi_llm_agents import (
        BullAgent,
        BearAgent,
        ArbiterAgent,
        AgentRole,
        AgentResponse,
        MultiLLMDebateResult
    )
    from .parallel_orchestrator import (
        ParallelDebateOrchestrator,
        run_multi_llm_debate
    )
    MULTI_LLM_AVAILABLE = True
except ImportError:
    # Multi-LLM features require additional packages
    MULTI_LLM_AVAILABLE = False

__all__ = [
    "DebatePerspective",
    "DebateResult",
    "LLMDebateNode",
    "DebateValidator",
    "DebatePromptBuilder",
    # Multi-LLM (if available)
    "BullAgent",
    "BearAgent",
    "ArbiterAgent",
    "AgentRole",
    "AgentResponse",
    "MultiLLMDebateResult",
    "ParallelDebateOrchestrator",
    "run_multi_llm_debate",
    "MULTI_LLM_AVAILABLE"
]

"""
Debate System - Multi-Perspective Analysis.

Week 5 Day 2: Structured debates for financial analysis quality.

Components:
- DebaterAgent: Generates arguments from specific perspective (Bull/Bear/Neutral)
- SynthesizerAgent: Combines perspectives into balanced synthesis
- DebateProtocol: Orchestrates debate flow
"""

from .schemas import (
    Perspective,
    Argument,
    DebateReport,
    Synthesis
)
from .debater_agent import DebaterAgent
from .synthesizer_agent import SynthesizerAgent

__all__ = [
    'Perspective',
    'Argument',
    'DebateReport',
    'Synthesis',
    'DebaterAgent',
    'SynthesizerAgent'
]

"""
Enhanced Multi-Agent Debate System.

Week 13 Day 3-5: 5 specialized analysts + Safety Protocol.
"""

from .specialists import (
    SpecialistRole,
    SpecialistResponse,
    BaseSpecialist,
    EarningsAnalyst,
    MarketAnalyst,
    SentimentAnalyst,
    ValuationAnalyst,
    RiskAnalyst
)

from .safety_protocol import (
    TrustCheck,
    SkepticChallenge,
    LeaderSynthesis,
    TrustAgent,
    SkepticAgent,
    LeaderAgent
)

__all__ = [
    # Specialists
    "SpecialistRole",
    "SpecialistResponse",
    "BaseSpecialist",
    "EarningsAnalyst",
    "MarketAnalyst",
    "SentimentAnalyst",
    "ValuationAnalyst",
    "RiskAnalyst",
    # Safety Protocol
    "TrustCheck",
    "SkepticChallenge",
    "LeaderSynthesis",
    "TrustAgent",
    "SkepticAgent",
    "LeaderAgent",
]

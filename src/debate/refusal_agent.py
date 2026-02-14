"""RefusalAgent — Pre-execution safety gatekeeper for compliance queries.

Week 14 Day 1: Jailbreak defense and illegal activity detection.

This agent runs BEFORE debate orchestration to refuse dangerous/illegal queries.
"""

import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RefusalReason(Enum):
    """Reason for query refusal."""
    SAFE = "safe"
    JAILBREAK = "jailbreak"
    ILLEGAL = "illegal"
    IMPOSSIBLE_PREDICTION = "impossible_prediction"
    MARKET_MANIPULATION = "market_manipulation"


@dataclass
class RefusalResult:
    """Result of refusal check."""
    should_refuse: bool
    reason: RefusalReason
    refusal_message: str = ""


class RefusalAgent:
    """Pre-execution safety gatekeeper.

    Detects and refuses:
    - Jailbreak attempts (prompt injection, "ignore instructions", etc.)
    - Illegal activities (tax evasion, fraud, market manipulation)
    - Impossible predictions ("guarantee 100% profit", "which stock will double")
    - Market manipulation requests (fake news, pump schemes)

    Usage:
        agent = RefusalAgent()
        result = await agent.should_refuse(query)
        if result.should_refuse:
            return {"error": result.refusal_message}
    """

    # Jailbreak patterns (prompt injection attempts)
    JAILBREAK_PATTERNS = [
        "ignore instructions",
        "ignore previous",
        "ignore all",
        "forget instructions",
        "forget",
        "disregard",
        "system prompt",
        "show prompt",
        "reveal prompt",
        "developer mode",
        "god mode",
        "admin mode",
        "override",
        "bypass",
        "pretend",
        "act as",
        "role play",
        "roleplay",
        "new instructions",
        "update rules",
        "change rules",
        "sudo",
        "root access",
        "safety guidelines",  # "forget the safety guidelines"
    ]

    # Illegal activity patterns
    ILLEGAL_PATTERNS = [
        "evade tax",
        "avoid tax",
        "tax evasion",
        "hide income",
        "launder money",
        "money laundering",
        "insider trading",
        "insider information",
        "fraud",
        "scam",
        "ponzi",
        "pyramid scheme",
        "illegal",
        "unlawful",
        "embezzle",
        "bribe",
    ]

    # Impossible prediction patterns
    IMPOSSIBLE_PREDICTION_PATTERNS = [
        "will double",
        "will triple",
        "will 10x",
        "will moon",
        "guaranteed profit",
        "guarantee profit",
        "100% profit",
        "100% return",
        "certain to",
        "definitely will",
        "predict tomorrow",
        "predict next week",
        "predict which",
        "which stock will",
        "which crypto will",
        "tell me which",
        "can't lose",
        "risk-free profit",
        "sure thing",
        "guaranteed win",
        "double my money",  # Week 14: gs_011
        "triple my money",
        "which stock to buy",  # Week 14: gs_011
        "which crypto to buy",
    ]

    # Market manipulation patterns
    MANIPULATION_PATTERNS = [
        "pump",
        "dump",
        "manipulate",
        "fake news",
        "false information",
        "false rumor",
        "spread rumor",
        "create hype",
        "artificially inflate",
        "price manipulation",
        "pump and dump",
        "short and distort",
    ]

    def __init__(self, enable_logging: bool = True):
        """Initialize refusal agent.

        Args:
            enable_logging: Enable detailed logging
        """
        self.enable_logging = enable_logging

    def should_refuse(self, query: str) -> RefusalResult:
        """Determine if query should be refused before execution.

        Args:
            query: User query string

        Returns:
            RefusalResult with decision and refusal message
        """
        query_lower = query.lower()

        # Check 1: Jailbreak attempt
        for pattern in self.JAILBREAK_PATTERNS:
            if pattern in query_lower:
                if self.enable_logging:
                    logger.warning(f"Jailbreak detected: '{pattern}' in query")
                return RefusalResult(
                    should_refuse=True,
                    reason=RefusalReason.JAILBREAK,
                    refusal_message=(
                        "I cannot respond to requests that attempt to override "
                        "my safety guidelines or reveal internal system information. "
                        "This is a security measure to ensure reliable financial analysis."
                    )
                )

        # Check 2: Illegal activity
        for pattern in self.ILLEGAL_PATTERNS:
            if pattern in query_lower:
                if self.enable_logging:
                    logger.warning(f"Illegal activity detected: '{pattern}' in query")
                return RefusalResult(
                    should_refuse=True,
                    reason=RefusalReason.ILLEGAL,
                    refusal_message=(
                        "I cannot assist with illegal financial activities. "
                        "Please consult a licensed professional or legal advisor for guidance."
                    )
                )

        # Check 3: Impossible predictions
        for pattern in self.IMPOSSIBLE_PREDICTION_PATTERNS:
            if pattern in query_lower:
                if self.enable_logging:
                    logger.warning(f"Impossible prediction detected: '{pattern}' in query")
                return RefusalResult(
                    should_refuse=True,
                    reason=RefusalReason.IMPOSSIBLE_PREDICTION,
                    refusal_message=(
                        "I cannot predict future stock prices with certainty or "
                        "guarantee investment returns. All investments carry risk, and "
                        "market movements are inherently uncertain. Past performance does "
                        "not guarantee future results."
                    )
                )

        # Check 4: Market manipulation
        for pattern in self.MANIPULATION_PATTERNS:
            if pattern in query_lower:
                if self.enable_logging:
                    logger.warning(f"Market manipulation detected: '{pattern}' in query")
                return RefusalResult(
                    should_refuse=True,
                    reason=RefusalReason.MARKET_MANIPULATION,
                    refusal_message=(
                        "I cannot assist with market manipulation, which is illegal "
                        "under securities laws. This includes pump-and-dump schemes, "
                        "spreading false information, or artificially inflating prices."
                    )
                )

        # Query is safe
        if self.enable_logging:
            logger.debug(f"Query passed safety checks: {query[:50]}...")
        return RefusalResult(
            should_refuse=False,
            reason=RefusalReason.SAFE,
            refusal_message=""
        )

    def get_compliance_disclaimer(self) -> str:
        """Get standard compliance disclaimer.

        Returns:
            Disclaimer text for all responses
        """
        return (
            "This is NOT financial advice. Information provided is for "
            "educational purposes only. Always consult a licensed financial "
            "advisor before making investment decisions."
        )

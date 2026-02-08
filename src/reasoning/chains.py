"""
Reasoning Chains for APE 2026.

Week 10 Day 2: Chain-of-thought reasoning for complex financial analysis.

Example:
    Query: "Is AAPL undervalued compared to MSFT?"

    Reasoning Chain:
    1. Calculate P/E ratio for AAPL
    2. Calculate P/E ratio for MSFT
    3. Compare P/E ratios
    4. Consider industry average
    5. Analyze historical trends
    6. Synthesize valuation opinion
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Step Action Types
# ============================================================================

class StepAction(str, Enum):
    """Types of reasoning steps."""
    CALCULATE = "calculate"  # Calculate a metric
    COMPARE = "compare"      # Compare values
    ANALYZE = "analyze"      # Analyze data/trends
    CONCLUDE = "conclude"    # Draw conclusion


# ============================================================================
# Reasoning Step
# ============================================================================

@dataclass
class ReasoningStep:
    """
    Single step in a reasoning chain.

    Attributes:
        step_number: Sequential step number (1-indexed)
        description: Human-readable description of the step
        action: Type of action (calculate, compare, analyze, conclude)
        inputs: Input parameters for this step
        output: Result after execution (None if not executed)
        confidence: Confidence score for this step (0.0-1.0)
    """
    step_number: int
    description: str
    action: StepAction
    inputs: Dict[str, Any]
    output: Optional[Any]
    confidence: float

    def __post_init__(self):
        """Validate step after initialization."""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")


# ============================================================================
# Chain Result
# ============================================================================

@dataclass
class ChainResult:
    """
    Result of reasoning chain execution.

    Attributes:
        success: Whether execution succeeded
        steps: List of executed steps with outputs
        final_output: Final result of the chain
        overall_confidence: Overall confidence score
        explanation: Human-readable explanation of reasoning
        error: Error message if execution failed
    """
    success: bool
    steps: List[ReasoningStep] = field(default_factory=list)
    final_output: Optional[Any] = None
    overall_confidence: float = 0.0
    explanation: str = ""
    error: Optional[str] = None


# ============================================================================
# Reasoning Chain
# ============================================================================

class ReasoningChain:
    """
    Chain of reasoning steps.

    Features:
    - Step-by-step execution
    - Intermediate result tracking
    - Confidence propagation
    - Explainability
    """

    def __init__(self, query: str):
        """
        Initialize reasoning chain.

        Args:
            query: The original query this chain answers
        """
        self.query = query
        self.steps: List[ReasoningStep] = []

    def add_step(self, step: ReasoningStep):
        """
        Add a step to the chain.

        Args:
            step: ReasoningStep to add
        """
        self.steps.append(step)

    def is_complete(self) -> bool:
        """
        Check if chain has steps.

        Returns:
            True if chain has at least one step
        """
        return len(self.steps) > 0

    def execute(self) -> ChainResult:
        """
        Execute the reasoning chain.

        Returns:
            ChainResult with execution results
        """
        if not self.is_complete():
            return ChainResult(
                success=False,
                error="Cannot execute empty chain"
            )

        try:
            # Execute each step
            executed_steps = []
            for step in self.steps:
                # Execute step (mock implementation - in production, call VEE)
                executed_step = self._execute_step(step)
                executed_steps.append(executed_step)

            # Calculate overall confidence (minimum strategy - weakest link)
            overall_confidence = min(step.confidence for step in executed_steps)

            # Get final output (last step's output)
            final_output = executed_steps[-1].output if executed_steps else None

            # Generate explanation
            explanation = self._generate_explanation(executed_steps)

            return ChainResult(
                success=True,
                steps=executed_steps,
                final_output=final_output,
                overall_confidence=overall_confidence,
                explanation=explanation
            )

        except Exception as e:
            logger.error(f"Chain execution error: {e}", exc_info=True)
            return ChainResult(
                success=False,
                error=str(e)
            )

    def _execute_step(self, step: ReasoningStep) -> ReasoningStep:
        """
        Execute a single step.

        Args:
            step: Step to execute

        Returns:
            Step with output filled in
        """
        # Mock implementation - in production, this would call VEE
        # For now, generate mock output based on action type

        if step.action == StepAction.CALCULATE:
            # Mock calculation result
            ticker = step.inputs.get("ticker", "UNKNOWN")
            metric = step.inputs.get("metric", "unknown")
            output = {
                "ticker": ticker,
                "metric": metric,
                "value": 1.5,  # Mock value
                "status": "success"
            }
        elif step.action == StepAction.COMPARE:
            # Mock comparison result
            output = {
                "comparison": "completed",
                "result": "A > B",
                "status": "success"
            }
        elif step.action == StepAction.ANALYZE:
            # Mock analysis result
            output = {
                "analysis": "completed",
                "insights": ["Trend is upward", "Volatility is moderate"],
                "status": "success"
            }
        elif step.action == StepAction.CONCLUDE:
            # Mock conclusion
            output = {
                "conclusion": "Based on analysis, the answer is positive",
                "status": "success"
            }
        else:
            output = {"status": "unknown_action"}

        # Create new step with output
        return ReasoningStep(
            step_number=step.step_number,
            description=step.description,
            action=step.action,
            inputs=step.inputs,
            output=output,
            confidence=step.confidence
        )

    def _generate_explanation(self, steps: List[ReasoningStep]) -> str:
        """
        Generate human-readable explanation.

        Args:
            steps: Executed steps

        Returns:
            Explanation string
        """
        explanation_parts = [f"Query: {self.query}\n\nReasoning Steps:\n"]

        for step in steps:
            confidence_pct = int(step.confidence * 100)
            explanation_parts.append(
                f"{step.step_number}. {step.description} "
                f"(confidence: {confidence_pct}%)"
            )

        # Add overall confidence
        overall_confidence = min(step.confidence for step in steps)
        overall_pct = int(overall_confidence * 100)
        explanation_parts.append(f"\nOverall confidence: {overall_pct}%")

        return "\n".join(explanation_parts)


# ============================================================================
# Reasoning Chain Builder
# ============================================================================

class ReasoningChainBuilder:
    """
    Builds reasoning chains from queries.

    Uses:
    - Template matching for common patterns
    - LLM for novel reasoning paths (future)
    - Validation of logical flow
    """

    # Patterns for query classification
    CALCULATION_PATTERNS = [
        r"(?:calculate|compute|what is|get)\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:for|of)\s+([A-Z]{2,5})",
        r"([A-Z]{2,5})\s+(\w+(?:\s+\w+)?)",
        r"(\w+\s+ratio)\s+(?:for|of)?\s*([A-Z]{2,5})",
    ]

    COMPARISON_PATTERNS = [
        r"compare\s+(?:the\s+)?(?:\w+\s+)?(?:of\s+)?([A-Z]{2,5})\s+(?:and|vs\.?|versus)\s+([A-Z]{2,5})",
        r"([A-Z]{2,5})\s+(?:vs\.?|versus)\s+([A-Z]{2,5})",
        r"which\s+is\s+better\s*:?\s*([A-Z]{2,5})\s+or\s+([A-Z]{2,5})",
    ]

    VALUATION_PATTERNS = [
        r"is\s+([A-Z]{2,5})\s+(undervalued|overvalued)\s+compared\s+to\s+([A-Z]{2,5})",
        r"([A-Z]{2,5})\s+(undervalued|overvalued)",
    ]

    def build(self, query: str) -> ReasoningChain:
        """
        Build a reasoning chain from a query.

        Args:
            query: User query

        Returns:
            ReasoningChain with steps
        """
        chain = ReasoningChain(query)

        # Classify query type
        if self._is_valuation_query(query):
            self._build_valuation_chain(chain, query)
        elif self._is_comparison_query(query):
            self._build_comparison_chain(chain, query)
        elif self._is_calculation_query(query):
            self._build_calculation_chain(chain, query)
        else:
            # Default: simple calculation
            self._build_calculation_chain(chain, query)

        return chain

    def _is_calculation_query(self, query: str) -> bool:
        """Check if query is a calculation."""
        for pattern in self.CALCULATION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_comparison_query(self, query: str) -> bool:
        """Check if query is a comparison."""
        # Check for comparison keywords
        comparison_keywords = ["compare", "vs", "versus", "vs.", "which is better", "or"]
        query_lower = query.lower()

        has_comparison_keyword = any(kw in query_lower for kw in comparison_keywords)

        # Also check if we have multiple tickers
        tickers = self._extract_tickers(query)
        has_multiple_tickers = len(tickers) >= 2

        return has_comparison_keyword and has_multiple_tickers

    def _is_valuation_query(self, query: str) -> bool:
        """Check if query is about valuation."""
        for pattern in self.VALUATION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _build_calculation_chain(self, chain: ReasoningChain, query: str):
        """Build chain for simple calculation query."""
        # Extract ticker and metric
        ticker = self._extract_ticker(query)
        metric = self._extract_metric(query)

        # Step 1: Calculate metric
        step = ReasoningStep(
            step_number=1,
            description=f"Calculate {metric} for {ticker}",
            action=StepAction.CALCULATE,
            inputs={"ticker": ticker, "metric": metric, "query": query},
            output=None,
            confidence=1.0
        )
        chain.add_step(step)

    def _build_comparison_chain(self, chain: ReasoningChain, query: str):
        """Build chain for comparison query."""
        tickers = self._extract_tickers(query)
        metric = self._extract_metric(query)

        if len(tickers) < 2:
            # Fallback to simple calculation
            self._build_calculation_chain(chain, query)
            return

        # Step 1: Calculate for first ticker
        step1 = ReasoningStep(
            step_number=1,
            description=f"Calculate {metric} for {tickers[0]}",
            action=StepAction.CALCULATE,
            inputs={"ticker": tickers[0], "metric": metric},
            output=None,
            confidence=1.0
        )
        chain.add_step(step1)

        # Step 2: Calculate for second ticker
        step2 = ReasoningStep(
            step_number=2,
            description=f"Calculate {metric} for {tickers[1]}",
            action=StepAction.CALCULATE,
            inputs={"ticker": tickers[1], "metric": metric},
            output=None,
            confidence=1.0
        )
        chain.add_step(step2)

        # Step 3: Compare results
        step3 = ReasoningStep(
            step_number=3,
            description=f"Compare {metric} between {tickers[0]} and {tickers[1]}",
            action=StepAction.COMPARE,
            inputs={"tickers": tickers, "metric": metric},
            output=None,
            confidence=0.95
        )
        chain.add_step(step3)

    def _build_valuation_chain(self, chain: ReasoningChain, query: str):
        """Build chain for valuation query."""
        tickers = self._extract_tickers(query)

        if len(tickers) < 2:
            tickers = ["AAPL", "MSFT"]  # Default tickers

        # Step 1: Calculate P/E for first ticker
        step1 = ReasoningStep(
            step_number=1,
            description=f"Calculate P/E ratio for {tickers[0]}",
            action=StepAction.CALCULATE,
            inputs={"ticker": tickers[0], "metric": "pe_ratio"},
            output=None,
            confidence=1.0
        )
        chain.add_step(step1)

        # Step 2: Calculate P/E for second ticker
        step2 = ReasoningStep(
            step_number=2,
            description=f"Calculate P/E ratio for {tickers[1]}",
            action=StepAction.CALCULATE,
            inputs={"ticker": tickers[1], "metric": "pe_ratio"},
            output=None,
            confidence=1.0
        )
        chain.add_step(step2)

        # Step 3: Compare valuations
        step3 = ReasoningStep(
            step_number=3,
            description=f"Compare P/E ratios",
            action=StepAction.COMPARE,
            inputs={"tickers": tickers, "metric": "pe_ratio"},
            output=None,
            confidence=0.95
        )
        chain.add_step(step3)

        # Step 4: Analyze industry context
        step4 = ReasoningStep(
            step_number=4,
            description="Analyze industry average and historical trends",
            action=StepAction.ANALYZE,
            inputs={"tickers": tickers},
            output=None,
            confidence=0.85
        )
        chain.add_step(step4)

        # Step 5: Conclude
        step5 = ReasoningStep(
            step_number=5,
            description="Synthesize valuation conclusion",
            action=StepAction.CONCLUDE,
            inputs={"tickers": tickers},
            output=None,
            confidence=0.8
        )
        chain.add_step(step5)

    def _extract_ticker(self, query: str) -> str:
        """Extract single ticker from query."""
        tickers = self._extract_tickers(query)
        return tickers[0] if tickers else "UNKNOWN"

    def _extract_tickers(self, query: str) -> List[str]:
        """Extract ticker symbols from query."""
        # Pattern: uppercase 2-5 letters
        matches = re.findall(r'\b[A-Z]{2,5}\b', query)
        # Filter out common English words
        common_words = {'THE', 'AND', 'FOR', 'ARE', 'FROM', 'TO', 'IS', 'AS', 'OR', 'PE'}
        return [t for t in matches if t not in common_words]

    def _extract_metric(self, query: str) -> str:
        """Extract financial metric from query."""
        query_lower = query.lower()

        metrics = {
            "sharpe": "sharpe_ratio",
            "correlation": "correlation",
            "volatility": "volatility",
            "beta": "beta",
            "return": "return",
            "p/e": "pe_ratio",
            "pe ratio": "pe_ratio",
            "price to earnings": "pe_ratio",
        }

        for keyword, metric in metrics.items():
            if keyword in query_lower:
                return metric

        return "unknown"

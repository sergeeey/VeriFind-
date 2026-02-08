"""
Pydantic schemas for PLAN node structured output.

Week 1 Day 3: Claude API Integration
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC


class DataRequirement(BaseModel):
    """Single data requirement for analysis."""

    ticker: str = Field(..., description="Stock ticker symbol")
    start_date: str = Field(..., description="Start date (ISO 8601)")
    end_date: str = Field(..., description="End date (ISO 8601)")
    data_type: str = Field(
        ...,
        description="Type of data: 'ohlcv', 'fundamentals', 'news', 'filings'"
    )
    source: str = Field(
        ...,
        description="Data source: 'yfinance', 'fred', 'sec', 'alpha_vantage'"
    )

    @field_validator('data_type')
    @classmethod
    def validate_data_type(cls, v):
        allowed = ['ohlcv', 'fundamentals', 'news', 'filings', 'economic']
        if v not in allowed:
            raise ValueError(f"data_type must be one of {allowed}")
        return v


class CodeBlock(BaseModel):
    """Single executable code block."""

    step_id: str = Field(..., description="Unique step identifier")
    description: str = Field(..., description="What this code does")
    code: str = Field(..., description="Python code to execute in VEE sandbox")
    depends_on: List[str] = Field(
        default_factory=list,
        description="List of step_ids that must execute before this"
    )
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Execution timeout (1-300 seconds)"
    )

    @field_validator('code')
    @classmethod
    def validate_no_imports_outside_allowed(cls, v):
        """Ensure only safe imports are used."""
        # Basic validation - full validation happens in VEE
        forbidden = ['os.', 'subprocess', 'eval', 'exec', '__import__']
        for term in forbidden:
            if term in v:
                raise ValueError(f"Forbidden term '{term}' in code")
        return v


class AnalysisPlan(BaseModel):
    """
    Complete analysis plan from PLAN node.

    This is the structured output that Claude Sonnet must generate
    to satisfy the Truth Boundary constraint: LLM generates CODE,
    not numbers directly.
    """

    query_id: str = Field(..., description="Unique query identifier")
    user_query: str = Field(..., description="Original user question")

    # Plan metadata
    plan_reasoning: str = Field(
        ...,
        description="Chain-of-thought reasoning for the plan"
    )
    data_requirements: List[DataRequirement] = Field(
        ...,
        description="All data needed for analysis"
    )

    # Executable code blocks
    code_blocks: List[CodeBlock] = Field(
        ...,
        description="Ordered list of code blocks to execute"
    )

    # Expected output
    expected_output_format: str = Field(
        ...,
        description="Description of expected final output format"
    )

    # Confidence and caveats
    confidence_level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in plan quality (0-1)"
    )
    caveats: List[str] = Field(
        default_factory=list,
        description="Known limitations or assumptions"
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Plan creation timestamp"
    )
    model_used: str = Field(
        default="claude-sonnet-4.5",
        description="LLM model used to generate plan"
    )

    @field_validator('code_blocks')
    @classmethod
    def validate_dependency_graph(cls, v):
        """Ensure dependency graph is acyclic."""
        step_ids = {block.step_id for block in v}

        for block in v:
            for dep in block.depends_on:
                if dep not in step_ids:
                    raise ValueError(
                        f"Step {block.step_id} depends on unknown step {dep}"
                    )

        # TODO: Add cycle detection for production
        return v

    def get_execution_order(self) -> List[str]:
        """
        Compute topological sort of code blocks for execution.

        Returns:
            Ordered list of step_ids
        """
        # Simple topological sort (Kahn's algorithm)
        from collections import defaultdict, deque

        in_degree = defaultdict(int)
        adj_list = defaultdict(list)

        # Build graph
        for block in self.code_blocks:
            if block.step_id not in in_degree:
                in_degree[block.step_id] = 0

            for dep in block.depends_on:
                adj_list[dep].append(block.step_id)
                in_degree[block.step_id] += 1

        # Find nodes with no incoming edges
        queue = deque([
            block.step_id for block in self.code_blocks
            if in_degree[block.step_id] == 0
        ])

        result = []
        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.code_blocks):
            raise ValueError("Cycle detected in dependency graph")

        return result


class PlanValidationResult(BaseModel):
    """Result of plan validation."""

    is_valid: bool = Field(..., description="Whether plan is valid")
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation warnings"
    )


# Example plan for testing
EXAMPLE_PLAN = {
    "query_id": "q_001",
    "user_query": "What is the correlation between SPY and QQQ in 2024?",
    "plan_reasoning": "To calculate correlation, I need: 1) Historical prices for both SPY and QQQ in 2024, 2) Calculate daily returns, 3) Compute Pearson correlation coefficient.",
    "data_requirements": [
        {
            "ticker": "SPY",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "data_type": "ohlcv",
            "source": "yfinance"
        },
        {
            "ticker": "QQQ",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "data_type": "ohlcv",
            "source": "yfinance"
        }
    ],
    "code_blocks": [
        {
            "step_id": "fetch_spy",
            "description": "Fetch SPY historical data",
            "code": """
import yfinance as yf
spy = yf.download('SPY', start='2024-01-01', end='2024-12-31')
spy_returns = spy['Close'].pct_change().dropna()
""",
            "depends_on": [],
            "timeout_seconds": 60
        },
        {
            "step_id": "fetch_qqq",
            "description": "Fetch QQQ historical data",
            "code": """
import yfinance as yf
qqq = yf.download('QQQ', start='2024-01-01', end='2024-12-31')
qqq_returns = qqq['Close'].pct_change().dropna()
""",
            "depends_on": [],
            "timeout_seconds": 60
        },
        {
            "step_id": "calculate_correlation",
            "description": "Calculate Pearson correlation",
            "code": """
import pandas as pd
import numpy as np

# Align dates
aligned = pd.DataFrame({
    'spy': spy_returns,
    'qqq': qqq_returns
}).dropna()

correlation = aligned['spy'].corr(aligned['qqq'])
result = {
    'correlation': float(correlation),
    'sample_size': len(aligned)
}
""",
            "depends_on": ["fetch_spy", "fetch_qqq"],
            "timeout_seconds": 30
        }
    ],
    "expected_output_format": "Dictionary with 'correlation' (float) and 'sample_size' (int)",
    "confidence_level": 0.95,
    "caveats": [
        "Assumes no stock splits or dividends adjustments needed",
        "Uses close-to-close returns (ignores intraday volatility)"
    ]
}

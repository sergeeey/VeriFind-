"""
Synthetic Baseline Generator using Claude Opus as expert.

Week 1 Day 4-5: Creates ground truth predictions for validation.

Strategy:
1. Use Claude Opus 4.6 to generate expert predictions
2. Calibrate against historical outcomes (when available)
3. Store baselines for comparison with Sonnet predictions
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from pydantic import BaseModel, Field

from ..orchestration.claude_client import ClaudeClient


class BaselinePrediction(BaseModel):
    """Expert baseline prediction from Opus."""

    query_id: str = Field(..., description="Query identifier")
    user_query: str = Field(..., description="Original user question")

    # Expert prediction
    prediction: str = Field(..., description="Expert's answer/prediction")
    reasoning: str = Field(..., description="Chain-of-thought reasoning")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")

    # Supporting evidence
    key_factors: List[str] = Field(
        ...,
        description="Key factors considered in prediction"
    )
    data_requirements: List[str] = Field(
        ...,
        description="What data was needed"
    )
    caveats: List[str] = Field(
        default_factory=list,
        description="Limitations and assumptions"
    )

    # Metadata
    model_used: str = Field(default="claude-opus-4-6")
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    # Calibration (populated later when outcome known)
    actual_outcome: Optional[str] = None
    directional_accuracy: Optional[bool] = None  # Was direction correct?
    magnitude_error: Optional[float] = None  # How far off in magnitude?


class SyntheticBaselineGenerator:
    """
    Generate expert baselines using Claude Opus 4.6.

    Purpose: Create ground truth predictions for:
    1. Validating Sonnet predictions
    2. Calibrating confidence scores
    3. Shadow mode comparison
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize baseline generator with Opus client.

        Args:
            api_key: Anthropic API key
        """
        self.client = ClaudeClient(
            api_key=api_key,
            model="claude-opus-4-6-20250514",  # Most capable model
            max_retries=3
        )

        self.system_prompt = """You are a world-class financial analyst with 20+ years of experience.

Your role: Provide EXPERT BASELINE PREDICTIONS for financial queries.

CRITICAL RULES:
1. Give your best prediction/analysis based on available information
2. Explain your reasoning step-by-step
3. List key factors you considered
4. Specify what data would be ideal
5. State limitations and caveats clearly
6. Provide calibrated confidence (0.0-1.0)

CALIBRATION GUIDE:
- 0.9-1.0: Highly confident (well-established patterns, strong evidence)
- 0.7-0.9: Confident (good evidence, some uncertainty)
- 0.5-0.7: Moderate (competing factors, limited data)
- 0.3-0.5: Uncertain (high volatility, insufficient data)
- 0.0-0.3: Very uncertain (speculation, extreme conditions)

Remember: This is EXPERT BASELINE for validation, not end-user output."""

    def generate_baseline(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> BaselinePrediction:
        """
        Generate expert baseline prediction.

        Args:
            user_query: User's financial question
            context: Optional context (market conditions, date, etc.)

        Returns:
            Validated BaselinePrediction

        Raises:
            ValidationError: If Opus fails to generate valid response
        """
        # Build prompt
        prompt = self._build_prompt(user_query, context)

        # Generate structured baseline
        baseline = self.client.generate_structured_output(
            prompt=prompt,
            output_schema=BaselinePrediction,
            system_prompt=self.system_prompt,
            max_tokens=2048,
            temperature=0.7,  # Slightly lower for consistency
            validation_retries=2
        )

        # Add metadata
        baseline.user_query = user_query

        return baseline

    def _build_prompt(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for baseline generation."""
        prompt = f"""User Query: "{user_query}"

Provide your expert baseline prediction.

Structure your response as BaselinePrediction JSON with:
1. prediction: Your answer/forecast
2. reasoning: Step-by-step thought process
3. confidence: Calibrated confidence score (0.0-1.0)
4. key_factors: Main factors you considered
5. data_requirements: Ideal data sources
6. caveats: Limitations of this prediction

Be specific and actionable."""

        if context:
            prompt += f"\n\nContext:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"

        return prompt

    def calibrate_baseline(
        self,
        baseline: BaselinePrediction,
        actual_outcome: str
    ) -> BaselinePrediction:
        """
        Calibrate baseline against actual outcome.

        Args:
            baseline: Original baseline prediction
            actual_outcome: What actually happened

        Returns:
            Updated baseline with calibration data
        """
        baseline.actual_outcome = actual_outcome

        # TODO: Implement automated calibration logic
        # For MVP, requires manual review

        return baseline

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            "client_stats": self.client.get_stats(),
            "model": "claude-opus-4-6-20250514"
        }

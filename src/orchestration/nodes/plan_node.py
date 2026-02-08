"""
PLAN Node - Generates executable analysis plans from user queries.

Week 1 Day 3: Core implementation with Claude Sonnet 4.5

Design principles (Truth Boundary):
1. LLM generates CODE, not numbers
2. All numerical outputs come from VEE execution
3. Plan must be fully executable and deterministic
"""

from typing import Optional, Dict, Any
from datetime import datetime, UTC

from ..claude_client import ClaudeClient
from ..schemas.plan_output import AnalysisPlan, PlanValidationResult


class PlanNode:
    """
    PLAN node for generating analysis plans.

    Responsibilities:
    1. Parse user query
    2. Generate structured AnalysisPlan using Claude Sonnet
    3. Validate plan against safety constraints
    4. Return executable plan for VEE
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        enable_validation: bool = True
    ):
        """
        Initialize PLAN node.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            enable_validation: Enable plan validation
        """
        self.client = ClaudeClient(api_key=api_key, model=model)
        self.enable_validation = enable_validation

        # System prompt for PLAN generation
        self.system_prompt = """You are an expert financial analyst planning system.

Your job is to create EXECUTABLE ANALYSIS PLANS from user queries.

CRITICAL CONSTRAINTS (Truth Boundary):
1. You generate CODE, NEVER numbers directly
2. ALL numerical outputs must come from code execution
3. Plans must be deterministic and reproducible
4. Use only approved data sources: yfinance, FRED, SEC filings

PLAN STRUCTURE:
1. Data Requirements: What data is needed?
2. Code Blocks: Sequential Python code to execute
3. Dependencies: Execution order (topological)
4. Validation: Check for edge cases

EXAMPLE INPUT:
"What was Apple's revenue growth in 2023?"

EXAMPLE OUTPUT (AnalysisPlan):
{
  "data_requirements": [
    {
      "ticker": "AAPL",
      "start_date": "2022-01-01",
      "end_date": "2023-12-31",
      "data_type": "fundamentals",
      "source": "yfinance"
    }
  ],
  "code_blocks": [
    {
      "step_id": "fetch_financials",
      "description": "Fetch Apple financial data",
      "code": "import yfinance as yf\\naapl = yf.Ticker('AAPL')\\nfinancials = aapl.financials",
      "depends_on": [],
      "timeout_seconds": 60
    },
    {
      "step_id": "calculate_growth",
      "description": "Calculate YoY revenue growth",
      "code": "revenue_2023 = financials.loc['Total Revenue']['2023']\\nrevenue_2022 = financials.loc['Total Revenue']['2022']\\ngrowth = (revenue_2023 - revenue_2022) / revenue_2022 * 100",
      "depends_on": ["fetch_financials"],
      "timeout_seconds": 30
    }
  ],
  "plan_reasoning": "To calculate revenue growth, I need: 1) Financial data for 2022-2023, 2) Extract total revenue for both years, 3) Calculate percentage growth",
  "confidence_level": 0.9
}

SAFETY RULES:
- No file system access (no os, subprocess)
- No network access except approved APIs
- Timeout all code blocks (max 300 seconds)
- Validate inputs before execution
"""

    def generate_plan(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisPlan:
        """
        Generate analysis plan from user query.

        Args:
            user_query: User's question
            context: Optional context (previous queries, user preferences)

        Returns:
            Validated AnalysisPlan

        Raises:
            ValidationError: If plan generation fails
        """
        # Build prompt
        prompt = self._build_prompt(user_query, context)

        # Generate structured output
        plan = self.client.generate_structured_output(
            prompt=prompt,
            output_schema=AnalysisPlan,
            system_prompt=self.system_prompt,
            max_tokens=4096,
            temperature=1.0,
            validation_retries=2
        )

        # Add query metadata
        plan.query_id = plan.query_id or self._generate_query_id()
        plan.user_query = user_query

        # Validate plan (safety checks)
        if self.enable_validation:
            validation = self.validate_plan(plan)
            if not validation.is_valid:
                raise ValueError(
                    f"Plan validation failed: {', '.join(validation.errors)}"
                )

        return plan

    def _build_prompt(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for plan generation."""
        prompt = f"""User Query: "{user_query}"

Generate a complete AnalysisPlan to answer this query.

Remember:
1. Generate CODE that produces numbers, not numbers directly
2. Use approved data sources only
3. Include proper error handling
4. Set realistic timeouts
5. Specify dependencies clearly

Return the plan as valid JSON matching the AnalysisPlan schema."""

        if context:
            prompt += f"\n\nContext:\n{context}"

        return prompt

    def validate_plan(self, plan: AnalysisPlan) -> PlanValidationResult:
        """
        Validate analysis plan for safety and correctness.

        Checks:
        1. No forbidden operations (file access, subprocess)
        2. All dependencies are satisfied
        3. Execution order is valid (no cycles)
        4. Timeouts are reasonable
        5. Data sources are approved

        Args:
            plan: Analysis plan to validate

        Returns:
            Validation result with errors/warnings
        """
        errors = []
        warnings = []

        # Check code blocks for forbidden operations
        forbidden_terms = [
            'os.system', 'subprocess', 'eval(', 'exec(',
            '__import__', 'open(', 'file(', 'input('
        ]

        for block in plan.code_blocks:
            # Check forbidden terms
            for term in forbidden_terms:
                if term in block.code:
                    errors.append(
                        f"Step {block.step_id}: Forbidden operation '{term}'"
                    )

            # Check timeout
            if block.timeout_seconds > 300:
                warnings.append(
                    f"Step {block.step_id}: Timeout very high ({block.timeout_seconds}s)"
                )

        # Check data sources
        approved_sources = ['yfinance', 'fred', 'sec', 'alpha_vantage']
        for req in plan.data_requirements:
            if req.source not in approved_sources:
                errors.append(
                    f"Data source '{req.source}' not approved"
                )

        # Validate execution order (topological sort)
        try:
            execution_order = plan.get_execution_order()
        except ValueError as e:
            errors.append(f"Dependency graph error: {str(e)}")

        # Check confidence level
        if plan.confidence_level < 0.5:
            warnings.append(
                f"Low confidence: {plan.confidence_level:.2f}"
            )

        return PlanValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _generate_query_id(self) -> str:
        """Generate unique query ID."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"query_{timestamp}"

    def get_stats(self) -> Dict[str, Any]:
        """Get node statistics."""
        return {
            "client_stats": self.client.get_stats(),
            "validation_enabled": self.enable_validation
        }

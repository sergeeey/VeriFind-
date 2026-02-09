"""
PLAN Node - Generates executable analysis plans from user queries.

Week 1 Day 3: Core implementation with Claude Sonnet 4.5
Week 11 Day 5: Made provider-agnostic with fallback chain (Anthropic → DeepSeek → OpenAI → Gemini)

Design principles (Truth Boundary):
1. LLM generates CODE, not numbers
2. All numerical outputs come from VEE execution
3. Plan must be fully executable and deterministic
"""

from typing import Optional, Dict, Any
from datetime import datetime, UTC
import json
import logging

from ..universal_llm_client import UniversalLLMClient, LLMResponse
from ..schemas.plan_output import AnalysisPlan, PlanValidationResult

logger = logging.getLogger(__name__)


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
        model: str = None,
        enable_validation: bool = True,
        preferred_provider: Optional[str] = None
    ):
        """
        Initialize PLAN node with provider-agnostic LLM client.

        Args:
            api_key: DEPRECATED - API keys auto-detected from environment
            model: Model override (uses provider defaults if None)
            enable_validation: Enable plan validation
            preferred_provider: Preferred LLM provider ("anthropic", "deepseek", "openai", "gemini")
                               If None, tries all in fallback order
        """
        # Create universal client with fallback chain
        try:
            self.client = UniversalLLMClient(
                preferred_provider=preferred_provider,
                model=model,
                temperature=0.0,  # Deterministic for planning
                max_tokens=4096
            )
            logger.info(f"✅ PLAN node initialized with providers: {list(self.client.available_providers.keys())}")
        except ValueError as e:
            raise ValueError(
                f"PLAN node init failed: {e}\n"
                f"Set at least one API key (ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY)"
            )

        self.enable_validation = enable_validation
        self.last_provider_used = None

        # System prompt for PLAN generation
        self.system_prompt = """You are an expert financial analyst planning system.

Your job is to create EXECUTABLE ANALYSIS PLANS from user queries.

CRITICAL CONSTRAINTS (Truth Boundary):
1. You generate CODE, NEVER numbers directly
2. ALL numerical outputs must come from code execution
3. Plans must be deterministic and reproducible
4. Use only approved data sources: yfinance, FRED, SEC filings

MANDATORY JSON FIELDS (must include ALL of these):
- query_id: string (unique identifier)
- user_query: string (the original user question)
- plan_reasoning: string (chain-of-thought explanation)
- data_requirements: array of objects
- code_blocks: array of objects
- expected_output_format: string (describe the final result format)
- confidence_level: float (0.0 to 1.0)

DATA REQUIREMENTS RULES:
- ticker: ALWAYS use "ticker" field (even for FRED data like "DGS3MO")
- data_type: MUST be EXACTLY one of: "ohlcv", "fundamentals", "news", "filings", "economic"
  * Use "ohlcv" for price/volume data (not "historical_prices")
  * Use "economic" for FRED data (not "risk_free_rate")
- source: "yfinance", "fred", "sec", or "alpha_vantage"

FRED API FALLBACK STRATEGY (CRITICAL for MVP):
When calculating metrics that require risk-free rate (Sharpe ratio, etc):
1. ALWAYS wrap FRED API calls in try/except blocks
2. If FRED API fails (missing key, network error), use these fallback rates:
   - 2021: 0.05% annual (near-zero rate environment)
   - 2022: 1.5% annual (rising rates)
   - 2023: 4.5% annual (elevated rates)
   - 2024+: 4.0% annual (normalized rates)
3. Convert annual rate to daily: daily_rf = (annual_rate / 100) / 252
4. Add 'risk_free_rate_source' to result: 'fred' or 'fallback_YYYY'
5. Example fallback code:
   try:
       from fredapi import Fred
       fred = Fred()
       rf_series = fred.get_series('DGS3MO', start_date='2023-01-01', end_date='2023-12-31')
       rf_daily = (rf_series / 100) / 252
       rf_source = 'fred'
   except Exception as e:
       # Fallback: use 4.5% annual for 2023
       import pandas as pd
       rf_annual = 4.5
       rf_daily = pd.Series([(rf_annual / 100) / 252] * len(spy_returns), index=spy_returns.index)
       rf_source = 'fallback_2023'

EXAMPLE INPUT:
"Calculate the Sharpe ratio for SPY from 2023-01-01 to 2023-12-31"

EXAMPLE OUTPUT (COMPLETE AnalysisPlan JSON):
{
  "query_id": "q_sharpe_spy_2023",
  "user_query": "Calculate the Sharpe ratio for SPY from 2023-01-01 to 2023-12-31",
  "plan_reasoning": "To calculate Sharpe ratio, I need: 1) SPY historical prices for 2023, 2) Risk-free rate data from FRED (3-month Treasury), 3) Calculate daily returns, 4) Annualize and compute (mean - rf) / std",
  "data_requirements": [
    {
      "ticker": "SPY",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "data_type": "ohlcv",
      "source": "yfinance"
    },
    {
      "ticker": "DGS3MO",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "data_type": "economic",
      "source": "fred"
    }
  ],
  "code_blocks": [
    {
      "step_id": "fetch_spy_prices",
      "description": "Fetch SPY historical OHLCV data",
      "code": "import yfinance as yf\\nimport pandas as pd\\nspy = yf.download('SPY', start='2023-01-01', end='2023-12-31')\\nspy_close = spy['Close']\\nspy_returns = spy_close.pct_change().dropna()",
      "depends_on": [],
      "timeout_seconds": 60
    },
    {
      "step_id": "fetch_risk_free_rate",
      "description": "Fetch 3-month Treasury rate from FRED",
      "code": "from fredapi import Fred\\nfred = Fred()\\nrf_rate = fred.get_series('DGS3MO', start_date='2023-01-01', end_date='2023-12-31')\\nrf_daily = (rf_rate / 100) / 252",
      "depends_on": [],
      "timeout_seconds": 60
    },
    {
      "step_id": "calculate_sharpe",
      "description": "Calculate annualized Sharpe ratio",
      "code": "import numpy as np\\nmean_return = spy_returns.mean() * 252\\nstd_return = spy_returns.std() * np.sqrt(252)\\navg_rf = rf_daily.mean() * 252\\nsharpe_ratio = (mean_return - avg_rf) / std_return\\nresult = {'sharpe_ratio': float(sharpe_ratio), 'mean_return': float(mean_return), 'volatility': float(std_return)}",
      "depends_on": ["fetch_spy_prices", "fetch_risk_free_rate"],
      "timeout_seconds": 30
    }
  ],
  "expected_output_format": "Dictionary with keys: sharpe_ratio (float), mean_return (float), volatility (float)",
  "confidence_level": 0.85,
  "caveats": [
    "Assumes 252 trading days per year",
    "Uses simple daily returns (not log returns)"
  ]
}

EXAMPLE INPUT (Correlation Calculation):
"What is the correlation between SPY and QQQ from 2023-01-01 to 2023-12-31?"

EXAMPLE OUTPUT (Correlation AnalysisPlan):
{
  "query_id": "q_corr_spy_qqq_2023",
  "user_query": "What is the correlation between SPY and QQQ from 2023-01-01 to 2023-12-31?",
  "plan_reasoning": "To calculate correlation: 1) Download both assets, 2) Align dates, 3) Calculate returns, 4) Compute correlation coefficient",
  "data_requirements": [
    {
      "ticker": "SPY",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "data_type": "ohlcv",
      "source": "yfinance"
    },
    {
      "ticker": "QQQ",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "data_type": "ohlcv",
      "source": "yfinance"
    }
  ],
  "code_blocks": [
    {
      "step_id": "calculate_correlation",
      "description": "Calculate return correlation between two assets",
      "code": "import yfinance as yf\\nimport pandas as pd\\n\\n# Download using Ticker API\\ntickerA = yf.Ticker('SPY')\\ntickerB = yf.Ticker('QQQ')\\n\\ndataA = tickerA.history(start='2023-01-01', end='2023-12-31')\\ndataB = tickerB.history(start='2023-01-01', end='2023-12-31')\\n\\n# Extract Close prices\\ncloseA = dataA['Close']\\ncloseB = dataB['Close']\\n\\n# Align dates (CRITICAL)\\ndf = pd.DataFrame({'assetA': closeA, 'assetB': closeB}).dropna()\\n\\n# Calculate returns\\nreturnsA = df['assetA'].pct_change().dropna()\\nreturnsB = df['assetB'].pct_change().dropna()\\n\\n# Calculate correlation\\ncorrelation = returnsA.corr(returnsB)\\n\\n# Create result\\nresult = {'correlation': float(correlation), 'data_points': len(returnsA)}\\nimport json\\nprint(json.dumps(result))",
      "depends_on": [],
      "timeout_seconds": 60
    }
  ],
  "expected_output_format": "Dictionary with keys: correlation (float -1 to +1), data_points (int)",
  "confidence_level": 0.90,
  "caveats": ["Correlation measures linear relationship", "Based on daily returns"]
}

EXAMPLE INPUT (Beta Calculation):
"Calculate the beta of AAPL relative to SPY from 2023-01-01 to 2023-12-31"

EXAMPLE OUTPUT (Beta AnalysisPlan):
{
  "query_id": "q_beta_aapl_2023",
  "user_query": "Calculate the beta of AAPL relative to SPY from 2023-01-01 to 2023-12-31",
  "plan_reasoning": "To calculate beta, I need: 1) AAPL historical prices, 2) SPY benchmark prices, 3) Align dates and calculate returns, 4) Beta = Cov(AAPL, SPY) / Var(SPY)",
  "data_requirements": [
    {
      "ticker": "AAPL",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "data_type": "ohlcv",
      "source": "yfinance"
    },
    {
      "ticker": "SPY",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "data_type": "ohlcv",
      "source": "yfinance"
    }
  ],
  "code_blocks": [
    {
      "step_id": "calculate_beta",
      "description": "Calculate beta using covariance and variance",
      "code": "import yfinance as yf\\nimport pandas as pd\\nimport numpy as np\\n\\n# Download data using Ticker API (more reliable)\\nstock = yf.Ticker('AAPL')\\nbench = yf.Ticker('SPY')\\n\\nstock_data = stock.history(start='2023-01-01', end='2023-12-31')\\nbench_data = bench.history(start='2023-01-01', end='2023-12-31')\\n\\n# Extract Close prices\\nstock_close = stock_data['Close']\\nbench_close = bench_data['Close']\\n\\n# Align dates (CRITICAL for avoiding NaN)\\ndf = pd.DataFrame({'stock': stock_close, 'benchmark': bench_close}).dropna()\\n\\n# Calculate returns\\nstock_returns = df['stock'].pct_change().dropna()\\nbench_returns = df['benchmark'].pct_change().dropna()\\n\\n# Calculate beta = Cov(stock, bench) / Var(bench)\\ncovariance = stock_returns.cov(bench_returns)\\nbench_variance = bench_returns.var()\\nbeta = covariance / bench_variance\\n\\n# Create result dictionary\\nresult = {'beta': float(beta), 'covariance': float(covariance), 'benchmark_variance': float(bench_variance)}\\nimport json\\nprint(json.dumps(result))",
      "depends_on": [],
      "timeout_seconds": 60
    }
  ],
  "expected_output_format": "Dictionary with keys: beta (float), covariance (float), benchmark_variance (float)",
  "confidence_level": 0.90,
  "caveats": [
    "Beta measures systematic risk relative to market",
    "Uses daily returns (not monthly)"
  ]
}

CODE OUTPUT RULES (CRITICAL):
1. The FINAL code block MUST create a 'result' dictionary with all computed values
2. The FINAL code block MUST print the result as JSON: import json; print(json.dumps(result))
3. This JSON output is how the GATE node extracts verified values
4. Example final lines:
   result = {'sharpe_ratio': float(sharpe_ratio), 'mean_return': float(mean_return)}
   import json
   print(json.dumps(result))

SAFETY RULES:
- No file system access (no os, subprocess)
- No network access except approved APIs
- Timeout all code blocks (max 300 seconds)
- Validate inputs before execution

REMINDER: You MUST include ALL mandatory fields. Do NOT use field names like "series_id" or enum values like "historical_prices" or "risk_free_rate".
"""

    def generate_plan(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> AnalysisPlan:
        """
        Generate analysis plan from user query.

        Args:
            user_query: User's question
            context: Optional context (previous queries, user preferences)
            max_retries: Maximum retry attempts for JSONDecodeError (default: 3)

        Returns:
            Validated AnalysisPlan

        Raises:
            ValidationError: If plan generation fails after retries
        """
        # Build prompt
        prompt = self._build_prompt(user_query, context)

        # Retry loop for handling transient LLM JSON errors
        last_error = None
        for attempt in range(max_retries):
            try:
                # Generate plan using universal client (with provider fallback)
                response = self.client.generate(
                    system_prompt=self.system_prompt,
                    user_prompt=prompt,
                    json_mode=True  # Request structured JSON output
                )

                # Track which provider was used
                self.last_provider_used = response.provider
                logger.info(f"Plan generated by {response.provider} ({response.model}), cost: ${response.cost:.6f}")

                # Parse JSON response to AnalysisPlan (Pydantic model)
                plan_dict = json.loads(response.content)
                plan = AnalysisPlan.model_validate(plan_dict)

                # Success! Break retry loop
                if attempt > 0:
                    logger.info(f"Plan generation succeeded on attempt {attempt + 1}/{max_retries}")
                break

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to parse plan JSON: {e}")
                if hasattr(locals(), 'response'):
                    logger.warning(f"Raw response (first 500 chars): {response.content[:500]}")

                # Retry unless this was the last attempt
                if attempt < max_retries - 1:
                    logger.info(f"Retrying plan generation...")
                    continue
                else:
                    # Final attempt failed
                    logger.error(f"All {max_retries} attempts failed with JSONDecodeError")
                    raise ValueError(f"LLM returned invalid JSON after {max_retries} attempts: {e}")

            except Exception as e:
                logger.error(f"Plan generation failed: {e}", exc_info=True)
                raise ValueError(f"Failed to generate plan: {e}")

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
            "available_providers": list(self.client.available_providers.keys()),
            "last_provider_used": self.last_provider_used,
            "validation_enabled": self.enable_validation
        }

"""Unit tests for cost tracking middleware.

Week 11 Day 4: Tests for CostTracker and cost calculation logic.
"""

import pytest
import uuid
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from src.api.cost_tracking import CostTracker, PRICING


class TestCostCalculation:
    """Test cost calculation logic."""

    def test_anthropic_sonnet_cost(self):
        """Calculate cost for Anthropic Claude Sonnet 4.5."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=0,
            cache_write_tokens=0
        )

        # $3/MTok input, $15/MTok output
        # (1000 * 3 + 500 * 15) / 1,000,000 = 0.01050
        expected = Decimal("0.010500")
        assert cost == expected

    def test_anthropic_with_cache(self):
        """Calculate cost with prompt caching."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=5000,  # Cache hit
            cache_write_tokens=1000   # Cache write
        )

        # Input: 1000 * $3 = $3,000
        # Output: 500 * $15 = $7,500
        # Cache read: 5000 * $0.30 = $1,500
        # Cache write: 1000 * $3.75 = $3,750
        # Total: $15,750 / 1,000,000 = $0.015750
        expected = Decimal("0.015750")
        assert cost == expected

    def test_openai_gpt4o_cost(self):
        """Calculate cost for OpenAI GPT-4o."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        cost = tracker.calculate_llm_cost(
            provider="openai",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1000,
            cache_read_tokens=0,
            cache_write_tokens=0
        )

        # $2.50/MTok input, $10/MTok output
        # (2000 * 2.50 + 1000 * 10) / 1,000,000 = 0.015
        expected = Decimal("0.015000")
        assert cost == expected

    def test_deepseek_cost(self):
        """Calculate cost for DeepSeek Chat."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        cost = tracker.calculate_llm_cost(
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=10000,
            output_tokens=5000
        )

        # $0.14/MTok input, $0.28/MTok output
        # (10000 * 0.14 + 5000 * 0.28) / 1,000,000 = 0.002800
        expected = Decimal("0.002800")
        assert cost == expected

    def test_unknown_model_zero_cost(self):
        """Unknown model returns $0 with warning."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        cost = tracker.calculate_llm_cost(
            provider="unknown",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500
        )

        assert cost == Decimal("0.00")

    def test_zero_tokens_zero_cost(self):
        """Zero tokens returns $0."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=0,
            output_tokens=0
        )

        assert cost == Decimal("0.000000")


class TestCostTracker:
    """Test CostTracker class."""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool."""
        pool = Mock()
        conn = AsyncMock()

        # Create async context manager mock
        acquire_cm = AsyncMock()
        acquire_cm.__aenter__ = AsyncMock(return_value=conn)
        acquire_cm.__aexit__ = AsyncMock(return_value=None)

        pool.acquire = Mock(return_value=acquire_cm)
        return pool

    @pytest.fixture
    def tracker(self, mock_db_pool):
        """CostTracker with mocked database."""
        return CostTracker(db_pool=mock_db_pool, enable_metrics=False)

    @pytest.mark.asyncio
    async def test_record_llm_call(self, tracker, mock_db_pool):
        """Record LLM call successfully."""
        request_id = uuid.uuid4()

        cost = await tracker.record_llm_call(
            request_id=request_id,
            endpoint="/api/analyze",
            http_method="POST",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
            user_id="user123",
            ticker="AAPL",
            query_type="analysis",
            latency_ms=1500,
            status_code=200
        )

        # Verify cost calculated
        expected_cost = Decimal("0.010500")
        assert cost == expected_cost

        # Verify database insert called
        mock_db_pool.acquire.assert_called()
        acquire_cm = mock_db_pool.acquire.return_value
        conn = await acquire_cm.__aenter__()
        assert conn.execute.called

    @pytest.mark.asyncio
    async def test_record_llm_call_with_error(self, tracker, mock_db_pool):
        """Record LLM call with error."""
        request_id = uuid.uuid4()

        cost = await tracker.record_llm_call(
            request_id=request_id,
            endpoint="/api/analyze",
            http_method="POST",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=0,  # Failed - no output
            status_code=500,
            error_message="API timeout"
        )

        # Still calculated input cost
        expected_cost = Decimal("0.003000")
        assert cost == expected_cost

    @pytest.mark.asyncio
    async def test_record_data_provider_call(self, tracker, mock_db_pool):
        """Record data provider call (free)."""
        request_id = uuid.uuid4()

        await tracker.record_data_provider_call(
            request_id=request_id,
            endpoint="/api/market-data",
            http_method="GET",
            provider="yfinance",
            ticker="TSLA",
            latency_ms=250,
            status_code=200
        )

        # Verify database insert called
        mock_db_pool.acquire.assert_called()
        acquire_cm = mock_db_pool.acquire.return_value
        conn = await acquire_cm.__aenter__()
        assert conn.execute.called

        # Verify cost is $0
        call_args = conn.execute.call_args[0]
        cost_value = call_args[10]  # cost_usd parameter
        assert cost_value == 0.0

    @pytest.mark.asyncio
    async def test_get_daily_costs(self, tracker, mock_db_pool):
        """Retrieve daily cost summary."""
        # Mock database response
        mock_rows = [
            {
                "date": "2026-02-08",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "request_count": 100,
                "total_input_tokens": 50000,
                "total_output_tokens": 25000,
                "total_cache_read_tokens": 10000,
                "total_cache_write_tokens": 5000,
                "total_cost_usd": 0.525,
                "avg_latency_ms": 1200.5
            }
        ]

        acquire_cm = mock_db_pool.acquire.return_value
        conn = await acquire_cm.__aenter__()
        # Return actual dicts, not Mocks
        conn.fetch.return_value = mock_rows

        # Fetch daily costs
        results = await tracker.get_daily_costs(days=7)

        # Verify results
        assert len(results) == 1
        assert results[0]["provider"] == "anthropic"
        assert results[0]["request_count"] == 100

    @pytest.mark.asyncio
    async def test_get_provider_breakdown(self, tracker, mock_db_pool):
        """Retrieve provider cost breakdown."""
        # Mock database response
        mock_rows = [
            {
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "request_count": 500,
                "total_input_tokens": 250000,
                "total_output_tokens": 125000,
                "total_cost_usd": 2.625,
                "avg_cost_per_request": 0.00525,
                "avg_latency_ms": 1150.0
            },
            {
                "provider": "openai",
                "model": "gpt-4o",
                "request_count": 300,
                "total_input_tokens": 150000,
                "total_output_tokens": 75000,
                "total_cost_usd": 1.125,
                "avg_cost_per_request": 0.00375,
                "avg_latency_ms": 980.0
            }
        ]

        acquire_cm = mock_db_pool.acquire.return_value
        conn = await acquire_cm.__aenter__()
        # Return actual dicts, not Mocks
        conn.fetch.return_value = mock_rows

        # Fetch provider breakdown
        results = await tracker.get_provider_breakdown()

        # Verify results
        assert len(results) == 2
        assert results[0]["provider"] == "anthropic"
        assert results[1]["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_db_insert_failure_logged(self, tracker, mock_db_pool):
        """Database insert failure is logged but doesn't crash."""
        # Simulate database error
        acquire_cm = mock_db_pool.acquire.return_value
        conn = await acquire_cm.__aenter__()
        conn.execute.side_effect = Exception("Connection lost")

        request_id = uuid.uuid4()

        # Should not raise exception
        cost = await tracker.record_llm_call(
            request_id=request_id,
            endpoint="/api/analyze",
            http_method="POST",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500
        )

        # Cost still calculated
        assert cost > 0

    def test_tracker_without_db_pool(self):
        """CostTracker works without database (testing mode)."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500
        )

        assert cost == Decimal("0.010500")


class TestPricingData:
    """Verify pricing constants are up to date."""

    def test_anthropic_pricing_exists(self):
        """Anthropic pricing defined."""
        assert "anthropic" in PRICING
        assert "claude-sonnet-4-5" in PRICING["anthropic"]
        assert "claude-opus-4-6" in PRICING["anthropic"]
        assert "claude-haiku-4-5" in PRICING["anthropic"]

    def test_openai_pricing_exists(self):
        """OpenAI pricing defined."""
        assert "openai" in PRICING
        assert "gpt-4o" in PRICING["openai"]

    def test_deepseek_pricing_exists(self):
        """DeepSeek pricing defined."""
        assert "deepseek" in PRICING
        assert "deepseek-chat" in PRICING["deepseek"]

    def test_pricing_structure(self):
        """Verify pricing structure."""
        # Anthropic has cache pricing
        sonnet_pricing = PRICING["anthropic"]["claude-sonnet-4-5"]
        assert "input" in sonnet_pricing
        assert "output" in sonnet_pricing
        assert "cache_read" in sonnet_pricing
        assert "cache_write" in sonnet_pricing

        # OpenAI doesn't have cache pricing
        gpt4o_pricing = PRICING["openai"]["gpt-4o"]
        assert "input" in gpt4o_pricing
        assert "output" in gpt4o_pricing
        assert "cache_read" not in gpt4o_pricing


class TestCostComparisons:
    """Compare costs across providers."""

    def test_deepseek_vs_anthropic(self):
        """DeepSeek should be ~20x cheaper than Anthropic."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        anthropic_cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=10000,
            output_tokens=10000
        )

        deepseek_cost = tracker.calculate_llm_cost(
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=10000,
            output_tokens=10000
        )

        # DeepSeek should be significantly cheaper
        assert deepseek_cost < anthropic_cost
        ratio = float(anthropic_cost) / float(deepseek_cost)
        assert 40 < ratio < 45  # Approximately 43x cheaper

    def test_haiku_vs_sonnet(self):
        """Haiku should be ~4x cheaper than Sonnet."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        sonnet_cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=10000,
            output_tokens=10000
        )

        haiku_cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-haiku-4-5",
            input_tokens=10000,
            output_tokens=10000
        )

        # Haiku should be cheaper
        assert haiku_cost < sonnet_cost
        ratio = float(sonnet_cost) / float(haiku_cost)
        assert 3 < ratio < 5  # Approximately 4x cheaper

    def test_cache_read_90_percent_savings(self):
        """Prompt cache should save 90% on read tokens."""
        tracker = CostTracker(db_pool=None, enable_metrics=False)

        # Without cache
        no_cache_cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=10000,
            output_tokens=0
        )

        # With cache (all input from cache)
        with_cache_cost = tracker.calculate_llm_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=10000
        )

        # Cache read should be 90% cheaper
        savings = 1 - (float(with_cache_cost) / float(no_cache_cost))
        assert 0.89 < savings < 0.91  # ~90% savings

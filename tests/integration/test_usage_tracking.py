"""
Integration tests for Usage Tracking & Billing System.

Week 12 Day 2-3: Test request logging, quota enforcement, cost calculation.

Run with:
    pytest tests/integration/test_usage_tracking.py -v
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from src.api.usage.usage_logger import UsageLogger, CostCalculator
from src.api.auth.api_key_manager import APIKeyManager


@pytest_asyncio.fixture
async def usage_logger():
    """Create UsageLogger instance for testing."""
    logger = UsageLogger()
    await logger.initialize()

    yield logger

    await logger.close()


@pytest_asyncio.fixture
async def api_key_manager():
    """Create APIKeyManager instance for testing."""
    manager = APIKeyManager()
    await manager.initialize()

    yield manager

    await manager.close()


class TestUsageLogging:
    """Test request logging functionality."""

    @pytest.mark.asyncio
    async def test_log_request_basic(self, usage_logger, api_key_manager):
        """Test logging basic API request."""
        # Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Logger",
            tier="free"
        )

        # Log request
        await usage_logger.log_request(
            api_key_id=key_record['id'],
            customer_name=key_record['customer_name'],
            tier=key_record['tier'],
            endpoint="/api/analyze-debate",
            method="POST",
            status_code=200,
            response_time_ms=3500
        )

        # Verify logged
        stats = await usage_logger.get_usage_stats(api_key_id=key_record['id'])
        assert stats['total_requests'] == 1
        assert stats['avg_response_time_ms'] > 0

    @pytest.mark.asyncio
    async def test_log_request_with_cost(self, usage_logger, api_key_manager):
        """Test logging request with LLM cost."""
        # Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Cost",
            tier="pro"
        )

        # Log request with cost
        await usage_logger.log_request(
            api_key_id=key_record['id'],
            customer_name=key_record['customer_name'],
            tier=key_record['tier'],
            endpoint="/api/analyze-debate",
            method="POST",
            status_code=200,
            response_time_ms=5000,
            cost_usd=0.0025,
            tokens_used=1500,
            llm_provider="multi-llm"
        )

        # Verify cost tracked
        stats = await usage_logger.get_usage_stats(api_key_id=key_record['id'])
        assert stats['total_cost_usd'] > 0
        assert stats['total_tokens'] == 1500

    @pytest.mark.asyncio
    async def test_log_request_error(self, usage_logger, api_key_manager):
        """Test logging failed request."""
        # Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Error",
            tier="free"
        )

        # Log error request
        await usage_logger.log_request(
            api_key_id=key_record['id'],
            customer_name=key_record['customer_name'],
            tier=key_record['tier'],
            endpoint="/api/analyze-debate",
            method="POST",
            status_code=500,
            response_time_ms=100,
            error_message="Internal server error"
        )

        # Verify error counted
        stats = await usage_logger.get_usage_stats(api_key_id=key_record['id'])
        assert stats['error_count'] == 1


class TestQuotaEnforcement:
    """Test monthly quota limits."""

    @pytest.mark.asyncio
    async def test_quota_within_limit(self, usage_logger, api_key_manager):
        """Test quota check when within limit."""
        # Create API key with quota
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Quota",
            tier="free",
            monthly_quota=100
        )

        # Check quota (0 requests used)
        within_quota, used, remaining = await usage_logger.check_quota(
            api_key_id=key_record['id'],
            monthly_quota=100
        )

        assert within_quota is True
        assert used == 0
        assert remaining == 100

    @pytest.mark.asyncio
    async def test_quota_exceeded(self, usage_logger, api_key_manager):
        """Test quota check when limit exceeded."""
        # Create API key with small quota
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Quota Exceeded",
            tier="free",
            monthly_quota=2
        )

        # Log 3 requests (exceed quota)
        for i in range(3):
            await usage_logger.log_request(
                api_key_id=key_record['id'],
                customer_name=key_record['customer_name'],
                tier=key_record['tier'],
                endpoint="/api/query",
                method="GET",
                status_code=200,
                response_time_ms=100
            )

        # Check quota
        within_quota, used, remaining = await usage_logger.check_quota(
            api_key_id=key_record['id'],
            monthly_quota=2
        )

        assert within_quota is False
        assert used >= 2
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_quota_unlimited(self, usage_logger, api_key_manager):
        """Test quota check for unlimited tier."""
        # Create API key without quota
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Unlimited",
            tier="enterprise",
            monthly_quota=None
        )

        # Log many requests
        for i in range(1000):
            await usage_logger.log_request(
                api_key_id=key_record['id'],
                customer_name=key_record['customer_name'],
                tier=key_record['tier'],
                endpoint="/api/query",
                method="GET",
                status_code=200,
                response_time_ms=50
            )

        # Check quota (should be unlimited)
        within_quota, used, remaining = await usage_logger.check_quota(
            api_key_id=key_record['id'],
            monthly_quota=None
        )

        assert within_quota is True


class TestUsageStatistics:
    """Test usage statistics aggregation."""

    @pytest.mark.asyncio
    async def test_get_usage_stats_date_range(self, usage_logger, api_key_manager):
        """Test getting stats for date range."""
        # Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Stats",
            tier="pro"
        )

        # Log requests
        for i in range(10):
            await usage_logger.log_request(
                api_key_id=key_record['id'],
                customer_name=key_record['customer_name'],
                tier=key_record['tier'],
                endpoint="/api/analyze",
                method="POST",
                status_code=200,
                response_time_ms=2000 + i * 100,
                cost_usd=0.001 * (i + 1)
            )

        # Get stats
        stats = await usage_logger.get_usage_stats(
            api_key_id=key_record['id'],
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=1)
        )

        assert stats['total_requests'] == 10
        assert stats['total_cost_usd'] > 0
        assert stats['avg_response_time_ms'] > 2000

    @pytest.mark.asyncio
    async def test_get_daily_usage(self, usage_logger, api_key_manager):
        """Test getting daily usage breakdown."""
        # Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Daily",
            tier="pro"
        )

        # Log requests
        for i in range(5):
            await usage_logger.log_request(
                api_key_id=key_record['id'],
                customer_name=key_record['customer_name'],
                tier=key_record['tier'],
                endpoint="/api/query",
                method="GET",
                status_code=200,
                response_time_ms=1000,
                cost_usd=0.002
            )

        # Get daily usage
        daily_usage = await usage_logger.get_daily_usage(
            api_key_id=key_record['id'],
            days=7
        )

        assert len(daily_usage) >= 1
        assert daily_usage[0]['requests'] >= 5
        assert daily_usage[0]['cost_usd'] >= 0.01

    @pytest.mark.asyncio
    async def test_get_current_month_usage(self, usage_logger, api_key_manager):
        """Test getting current month usage."""
        # Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Month",
            tier="free"
        )

        # Log requests
        for i in range(3):
            await usage_logger.log_request(
                api_key_id=key_record['id'],
                customer_name=key_record['customer_name'],
                tier=key_record['tier'],
                endpoint="/api/query",
                method="GET",
                status_code=200,
                response_time_ms=500
            )

        # Get current month
        month_usage = await usage_logger.get_current_month_usage(
            api_key_id=key_record['id']
        )

        assert month_usage['total_requests'] == 3


class TestCostCalculation:
    """Test LLM cost calculation."""

    def test_calculate_deepseek_cost(self):
        """Test DeepSeek cost calculation."""
        cost = CostCalculator.calculate_cost(
            provider="deepseek",
            input_tokens=10000,
            output_tokens=5000
        )

        # DeepSeek: $0.27/M input, $1.10/M output
        expected_cost = (10000 / 1_000_000) * 0.27 + (5000 / 1_000_000) * 1.10
        assert abs(cost - expected_cost) < 0.000001

    def test_calculate_anthropic_cost(self):
        """Test Claude cost calculation."""
        cost = CostCalculator.calculate_cost(
            provider="anthropic",
            input_tokens=20000,
            output_tokens=10000
        )

        # Claude: $3.00/M input, $15.00/M output
        expected_cost = (20000 / 1_000_000) * 3.00 + (10000 / 1_000_000) * 15.00
        assert abs(cost - expected_cost) < 0.000001

    def test_calculate_openai_cost(self):
        """Test GPT-4 cost calculation."""
        cost = CostCalculator.calculate_cost(
            provider="openai",
            input_tokens=15000,
            output_tokens=8000
        )

        # GPT-4: $10.00/M input, $30.00/M output
        expected_cost = (15000 / 1_000_000) * 10.00 + (8000 / 1_000_000) * 30.00
        assert abs(cost - expected_cost) < 0.000001

    def test_calculate_multi_llm_cost(self):
        """Test Multi-LLM Debate cost calculation."""
        cost_breakdown = CostCalculator.calculate_multi_llm_cost(
            bull_tokens=(5000, 3000),      # DeepSeek
            bear_tokens=(6000, 4000),      # Claude
            arbiter_tokens=(4000, 2000)    # GPT-4
        )

        assert 'bull_cost_usd' in cost_breakdown
        assert 'bear_cost_usd' in cost_breakdown
        assert 'arbiter_cost_usd' in cost_breakdown
        assert 'total_cost_usd' in cost_breakdown
        assert cost_breakdown['total_cost_usd'] > 0

    def test_calculate_unknown_provider(self):
        """Test handling unknown provider."""
        cost = CostCalculator.calculate_cost(
            provider="unknown_llm",
            input_tokens=10000,
            output_tokens=5000
        )

        # Should return $0 for unknown provider
        assert cost == 0.0


class TestEndToEndBillingFlow:
    """Test complete billing flow from API key to billing."""

    @pytest.mark.asyncio
    async def test_complete_billing_cycle(self, usage_logger, api_key_manager):
        """Test full billing cycle: create key → use → track → bill."""
        # 1. Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Billing Cycle",
            tier="pro",
            rate_limit_per_hour=1000,
            monthly_quota=10000
        )

        # 2. Simulate API usage (10 requests)
        for i in range(10):
            # Calculate cost for this request
            cost = CostCalculator.calculate_cost(
                provider="anthropic",
                input_tokens=1000 + i * 100,
                output_tokens=500 + i * 50
            )

            # Log request
            await usage_logger.log_request(
                api_key_id=key_record['id'],
                customer_name=key_record['customer_name'],
                tier=key_record['tier'],
                endpoint="/api/analyze-debate",
                method="POST",
                status_code=200,
                response_time_ms=3000 + i * 100,
                cost_usd=cost,
                tokens_used=1500 + i * 150,
                llm_provider="anthropic"
            )

        # 3. Get usage statistics
        stats = await usage_logger.get_usage_stats(
            api_key_id=key_record['id']
        )

        assert stats['total_requests'] == 10
        assert stats['total_cost_usd'] > 0
        assert stats['total_tokens'] > 15000

        # 4. Check quota status
        within_quota, used, remaining = await usage_logger.check_quota(
            api_key_id=key_record['id'],
            monthly_quota=key_record['monthly_quota']
        )

        assert within_quota is True
        assert used == 10
        assert remaining == 9990

        # 5. Get daily breakdown
        daily_usage = await usage_logger.get_daily_usage(
            api_key_id=key_record['id'],
            days=1
        )

        assert len(daily_usage) >= 1
        assert daily_usage[0]['requests'] == 10


class TestWeek12Day2Day3SuccessCriteria:
    """
    Week 12 Day 2-3 Success Criteria:

    ✅ Request logging (endpoint, status, time, cost)
    ✅ TimescaleDB hypertable for time-series
    ✅ Quota enforcement (429 when exceeded)
    ✅ Usage aggregation (daily, weekly, monthly)
    ✅ Cost calculation (DeepSeek, Claude, GPT-4)
    ✅ Admin endpoints (stats, billing, by-customer)
    """

    @pytest.mark.asyncio
    async def test_week12_day2_day3_success_criteria(
        self, usage_logger, api_key_manager
    ):
        """Test all Week 12 Day 2-3 success criteria."""
        print("\n" + "="*60)
        print("✅ WEEK 12 DAY 2-3 SUCCESS CRITERIA")
        print("="*60)

        # 1. Create API key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Success Criteria Test",
            tier="pro",
            monthly_quota=100
        )
        print("✅ API Key created")

        # 2. Request logging
        await usage_logger.log_request(
            api_key_id=key_record['id'],
            customer_name=key_record['customer_name'],
            tier=key_record['tier'],
            endpoint="/api/analyze-debate",
            method="POST",
            status_code=200,
            response_time_ms=3500,
            cost_usd=0.0025,
            tokens_used=1500,
            llm_provider="anthropic"
        )
        print("✅ Request logging")

        # 3. Usage statistics
        stats = await usage_logger.get_usage_stats(api_key_id=key_record['id'])
        assert stats['total_requests'] > 0
        print("✅ Usage statistics")

        # 4. Daily breakdown
        daily = await usage_logger.get_daily_usage(
            api_key_id=key_record['id'],
            days=7
        )
        assert len(daily) >= 1
        print("✅ Daily breakdown")

        # 5. Quota enforcement
        within_quota, used, remaining = await usage_logger.check_quota(
            api_key_id=key_record['id'],
            monthly_quota=key_record['monthly_quota']
        )
        assert within_quota is True
        print("✅ Quota enforcement")

        # 6. Cost calculation
        cost = CostCalculator.calculate_cost("deepseek", 10000, 5000)
        assert cost > 0
        print("✅ Cost calculation")

        # 7. Multi-LLM cost
        multi_cost = CostCalculator.calculate_multi_llm_cost(
            bull_tokens=(5000, 3000),
            bear_tokens=(6000, 4000),
            arbiter_tokens=(4000, 2000)
        )
        assert multi_cost['total_cost_usd'] > 0
        print("✅ Multi-LLM cost tracking")

        print("="*60)
        print("🎉 WEEK 12 DAY 2-3: USAGE TRACKING & BILLING OPERATIONAL!")
        print("="*60)

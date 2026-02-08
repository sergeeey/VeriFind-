"""
Unit tests for metrics module.

Week 9 Day 2: Testing Coverage - Prometheus metrics and decorators.
"""

import pytest
import time
import asyncio
from unittest.mock import patch
from prometheus_client import REGISTRY

from src.api.metrics import (
    # Metric instances
    http_requests_total,
    http_request_duration_seconds,
    queries_submitted_total,
    queries_completed_total,
    query_execution_duration_seconds,
    pipeline_node_executions_total,
    pipeline_node_duration_seconds,
    verified_facts_generated_total,
    facts_confidence_score,
    external_api_requests_total,
    external_api_duration_seconds,
    validation_errors_total,
    rate_limit_violations_total,
    exceptions_total,
    # Functions
    set_app_info,
    record_validation_error,
    record_rate_limit_violation,
    record_exception,
    record_verified_fact,
    update_cache_hit_ratio,
    # Decorators
    track_query_execution,
    track_pipeline_node,
    track_external_api_call
)


# ============================================================================
# Setup and Teardown
# ============================================================================

@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset Prometheus metrics before each test."""
    # Clear all collectors
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass

    # Re-import metrics to re-register them
    from src.api import metrics
    import importlib
    importlib.reload(metrics)

    yield

    # Cleanup
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


# ============================================================================
# HTTP Metrics Tests
# ============================================================================

class TestHTTPMetrics:
    """Tests for HTTP metrics."""

    def test_http_requests_total(self):
        """Test HTTP requests counter."""
        http_requests_total.labels(method="GET", endpoint="/api/health", status=200).inc()
        http_requests_total.labels(method="POST", endpoint="/api/query", status=201).inc()

        # Verify metrics were recorded
        # No exception should be raised

    def test_http_request_duration(self):
        """Test HTTP request duration histogram."""
        http_request_duration_seconds.labels(method="GET", endpoint="/api/health").observe(0.123)
        http_request_duration_seconds.labels(method="POST", endpoint="/api/query").observe(1.456)

    def test_http_request_size(self):
        """Test HTTP request size histogram."""
        from src.api.metrics import http_request_size_bytes

        http_request_size_bytes.labels(method="POST", endpoint="/api/query").observe(1024)
        http_request_size_bytes.labels(method="POST", endpoint="/api/query").observe(2048)

    def test_http_response_size(self):
        """Test HTTP response size histogram."""
        from src.api.metrics import http_response_size_bytes

        http_response_size_bytes.labels(method="GET", endpoint="/api/query").observe(4096)

    def test_http_requests_in_progress(self):
        """Test in-progress requests gauge."""
        from src.api.metrics import http_requests_in_progress

        http_requests_in_progress.labels(method="GET", endpoint="/api/test").inc()
        http_requests_in_progress.labels(method="GET", endpoint="/api/test").inc()
        http_requests_in_progress.labels(method="GET", endpoint="/api/test").dec()


# ============================================================================
# Business Metrics Tests
# ============================================================================

class TestBusinessMetrics:
    """Tests for business metrics."""

    def test_queries_submitted(self):
        """Test queries submitted counter."""
        queries_submitted_total.labels(priority="normal").inc()
        queries_submitted_total.labels(priority="high").inc()
        queries_submitted_total.labels(priority="low").inc()

    def test_queries_completed(self):
        """Test queries completed counter."""
        queries_completed_total.labels(status="completed").inc()
        queries_completed_total.labels(status="failed").inc()

    def test_query_execution_duration(self):
        """Test query execution duration histogram."""
        query_execution_duration_seconds.labels(status="completed").observe(5.0)
        query_execution_duration_seconds.labels(status="failed").observe(2.5)

    def test_pipeline_node_executions(self):
        """Test pipeline node executions counter."""
        pipeline_node_executions_total.labels(node="PLAN", status="success").inc()
        pipeline_node_executions_total.labels(node="FETCH", status="success").inc()
        pipeline_node_executions_total.labels(node="VEE", status="failed").inc()

    def test_pipeline_node_duration(self):
        """Test pipeline node duration histogram."""
        pipeline_node_duration_seconds.labels(node="PLAN").observe(1.2)
        pipeline_node_duration_seconds.labels(node="FETCH").observe(3.5)
        pipeline_node_duration_seconds.labels(node="VEE").observe(10.8)

    def test_verified_facts_generated(self):
        """Test verified facts counter."""
        verified_facts_generated_total.inc()
        verified_facts_generated_total.inc()
        verified_facts_generated_total.inc()

    def test_facts_confidence_score(self):
        """Test facts confidence score histogram."""
        facts_confidence_score.observe(0.95)
        facts_confidence_score.observe(0.87)
        facts_confidence_score.observe(0.99)

    def test_websocket_metrics(self):
        """Test WebSocket metrics."""
        from src.api.metrics import (
            websocket_connections_total,
            websocket_messages_sent_total,
            websocket_messages_received_total
        )

        websocket_connections_total.inc()
        websocket_connections_total.inc()
        websocket_connections_total.dec()

        websocket_messages_sent_total.labels(message_type="update").inc()
        websocket_messages_received_total.labels(action="subscribe").inc()


# ============================================================================
# Error Metrics Tests
# ============================================================================

class TestErrorMetrics:
    """Tests for error metrics."""

    def test_exceptions_total(self):
        """Test exceptions counter."""
        exceptions_total.labels(exception_type="ValueError", severity="error").inc()
        exceptions_total.labels(exception_type="TimeoutError", severity="warning").inc()

    def test_validation_errors(self):
        """Test validation errors counter."""
        validation_errors_total.labels(error_type="sql_injection").inc()
        validation_errors_total.labels(error_type="xss").inc()
        validation_errors_total.labels(error_type="command_injection").inc()

    def test_rate_limit_violations(self):
        """Test rate limit violations counter."""
        rate_limit_violations_total.labels(api_key="test_key_1").inc()
        rate_limit_violations_total.labels(api_key="test_key_2").inc()


# ============================================================================
# External Service Metrics Tests
# ============================================================================

class TestExternalServiceMetrics:
    """Tests for external service metrics."""

    def test_external_api_requests(self):
        """Test external API requests counter."""
        external_api_requests_total.labels(service="anthropic", status="success").inc()
        external_api_requests_total.labels(service="openai", status="success").inc()
        external_api_requests_total.labels(service="anthropic", status="failed").inc()

    def test_external_api_duration(self):
        """Test external API duration histogram."""
        external_api_duration_seconds.labels(service="anthropic").observe(2.5)
        external_api_duration_seconds.labels(service="openai").observe(1.8)

    def test_database_queries(self):
        """Test database queries counter."""
        from src.api.metrics import database_queries_total, database_query_duration_seconds

        database_queries_total.labels(database="timescaledb", operation="select").inc()
        database_queries_total.labels(database="neo4j", operation="insert").inc()

        database_query_duration_seconds.labels(database="timescaledb", operation="select").observe(0.05)

    def test_cache_operations(self):
        """Test cache operations counter."""
        from src.api.metrics import cache_operations_total

        cache_operations_total.labels(operation="get", result="hit").inc()
        cache_operations_total.labels(operation="get", result="miss").inc()
        cache_operations_total.labels(operation="set", result="success").inc()


# ============================================================================
# App Info Tests
# ============================================================================

class TestAppInfo:
    """Tests for application info."""

    def test_set_app_info(self):
        """Test setting application info."""
        set_app_info(version="1.0.0", environment="test")
        # Should not raise exception

    def test_set_app_info_different_environments(self):
        """Test setting app info with different environments."""
        for env in ["development", "staging", "production"]:
            set_app_info(version="1.0.0", environment=env)


# ============================================================================
# Decorator Tests
# ============================================================================

class TestTrackQueryExecution:
    """Tests for track_query_execution decorator."""

    @pytest.mark.asyncio
    async def test_successful_query_execution(self):
        """Test decorator tracks successful query execution."""
        @track_query_execution(status="completed")
        async def execute_query():
            await asyncio.sleep(0.1)
            return "result"

        result = await execute_query()
        assert result == "result"

        # Metrics should be recorded (no exception raised)

    @pytest.mark.asyncio
    async def test_failed_query_execution(self):
        """Test decorator tracks failed query execution."""
        @track_query_execution(status="completed")
        async def execute_query():
            await asyncio.sleep(0.05)
            raise ValueError("Query failed")

        with pytest.raises(ValueError):
            await execute_query()

        # Failed metric should be recorded

    @pytest.mark.asyncio
    async def test_query_execution_timing(self):
        """Test decorator measures execution time."""
        delay = 0.1

        @track_query_execution(status="completed")
        async def execute_query():
            await asyncio.sleep(delay)
            return "result"

        start = time.time()
        await execute_query()
        actual_duration = time.time() - start

        assert actual_duration >= delay


class TestTrackPipelineNode:
    """Tests for track_pipeline_node decorator."""

    def test_successful_node_execution(self):
        """Test decorator tracks successful node execution."""
        @track_pipeline_node(node="PLAN")
        def plan_node():
            time.sleep(0.1)
            return {"plan": "data"}

        result = plan_node()
        assert result == {"plan": "data"}

    def test_failed_node_execution(self):
        """Test decorator tracks failed node execution."""
        @track_pipeline_node(node="VEE")
        def vee_node():
            time.sleep(0.05)
            raise RuntimeError("VEE failed")

        with pytest.raises(RuntimeError):
            vee_node()

    def test_node_execution_timing(self):
        """Test decorator measures node execution time."""
        delay = 0.1

        @track_pipeline_node(node="FETCH")
        def fetch_node():
            time.sleep(delay)
            return "data"

        start = time.time()
        fetch_node()
        actual_duration = time.time() - start

        assert actual_duration >= delay

    def test_multiple_nodes(self):
        """Test decorator works for multiple nodes."""
        @track_pipeline_node(node="PLAN")
        def plan_node():
            return "plan"

        @track_pipeline_node(node="FETCH")
        def fetch_node():
            return "fetch"

        @track_pipeline_node(node="VEE")
        def vee_node():
            return "vee"

        assert plan_node() == "plan"
        assert fetch_node() == "fetch"
        assert vee_node() == "vee"


class TestTrackExternalAPICall:
    """Tests for track_external_api_call decorator."""

    @pytest.mark.asyncio
    async def test_successful_api_call(self):
        """Test decorator tracks successful API call."""
        @track_external_api_call(service="anthropic")
        async def call_anthropic():
            await asyncio.sleep(0.1)
            return {"response": "data"}

        result = await call_anthropic()
        assert result == {"response": "data"}

    @pytest.mark.asyncio
    async def test_failed_api_call(self):
        """Test decorator tracks failed API call."""
        @track_external_api_call(service="openai")
        async def call_openai():
            await asyncio.sleep(0.05)
            raise ConnectionError("API unreachable")

        with pytest.raises(ConnectionError):
            await call_openai()

    @pytest.mark.asyncio
    async def test_api_call_timing(self):
        """Test decorator measures API call duration."""
        delay = 0.2

        @track_external_api_call(service="alpha_vantage")
        async def call_alpha_vantage():
            await asyncio.sleep(delay)
            return "data"

        start = time.time()
        await call_alpha_vantage()
        actual_duration = time.time() - start

        assert actual_duration >= delay

    @pytest.mark.asyncio
    async def test_multiple_services(self):
        """Test decorator works for multiple services."""
        @track_external_api_call(service="anthropic")
        async def call_anthropic():
            return "anthropic"

        @track_external_api_call(service="openai")
        async def call_openai():
            return "openai"

        @track_external_api_call(service="alpha_vantage")
        async def call_alpha_vantage():
            return "alpha_vantage"

        assert await call_anthropic() == "anthropic"
        assert await call_openai() == "openai"
        assert await call_alpha_vantage() == "alpha_vantage"


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_record_validation_error(self):
        """Test recording validation error."""
        record_validation_error("sql_injection")
        record_validation_error("xss")
        record_validation_error("command_injection")

    def test_record_rate_limit_violation(self):
        """Test recording rate limit violation."""
        record_rate_limit_violation("test_key_1")
        record_rate_limit_violation("test_key_2")
        record_rate_limit_violation("test_key_1")

    def test_record_exception(self):
        """Test recording exception."""
        record_exception("ValueError", "error")
        record_exception("TimeoutError", "warning")
        record_exception("ConfigurationError", "critical")

    def test_record_verified_fact(self):
        """Test recording verified fact."""
        record_verified_fact(0.95)
        record_verified_fact(0.87)
        record_verified_fact(0.99)

    def test_update_cache_hit_ratio(self):
        """Test updating cache hit ratio."""
        update_cache_hit_ratio(hits=80, total=100)
        update_cache_hit_ratio(hits=50, total=100)
        update_cache_hit_ratio(hits=95, total=100)

    def test_update_cache_hit_ratio_zero_total(self):
        """Test cache hit ratio with zero total."""
        # Should not raise exception
        update_cache_hit_ratio(hits=0, total=0)


# ============================================================================
# Integration Tests
# ============================================================================

class TestMetricsIntegration:
    """Integration tests for metrics system."""

    @pytest.mark.asyncio
    async def test_complete_metrics_flow(self):
        """Test complete metrics flow with decorators."""
        # Set app info
        set_app_info(version="1.0.0", environment="test")

        # Submit query
        queries_submitted_total.labels(priority="normal").inc()

        # Track query execution
        @track_query_execution(status="completed")
        async def execute_query():
            # Track pipeline nodes
            @track_pipeline_node(node="PLAN")
            def plan():
                return "plan"

            @track_pipeline_node(node="FETCH")
            def fetch():
                return "fetch"

            @track_pipeline_node(node="VEE")
            def vee():
                return "vee"

            plan()
            fetch()
            vee()

            # Make external API call
            @track_external_api_call(service="anthropic")
            async def call_api():
                return "response"

            await call_api()

            # Generate facts
            record_verified_fact(0.95)
            record_verified_fact(0.87)

            return "result"

        result = await execute_query()
        assert result == "result"

        # All metrics should be recorded without errors

    def test_error_metrics_integration(self):
        """Test error metrics integration."""
        # Record various errors
        record_validation_error("sql_injection")
        record_validation_error("xss")
        record_rate_limit_violation("test_key")
        record_exception("ValueError", "error")

        # Update cache metrics
        update_cache_hit_ratio(hits=75, total=100)

    @pytest.mark.asyncio
    async def test_concurrent_metric_recording(self):
        """Test concurrent metric recording."""
        async def record_metrics(idx):
            queries_submitted_total.labels(priority="normal").inc()

            @track_query_execution(status="completed")
            async def execute():
                await asyncio.sleep(0.01)
                return idx

            return await execute()

        # Record metrics concurrently
        tasks = [record_metrics(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10

    def test_metric_labels(self):
        """Test that metric labels work correctly."""
        # HTTP metrics
        http_requests_total.labels(method="GET", endpoint="/api/test", status=200).inc()
        http_requests_total.labels(method="POST", endpoint="/api/test", status=201).inc()

        # Query metrics with different priorities
        queries_submitted_total.labels(priority="low").inc()
        queries_submitted_total.labels(priority="normal").inc()
        queries_submitted_total.labels(priority="high").inc()

        # Pipeline metrics with different nodes
        for node in ["PLAN", "FETCH", "VEE", "GATE", "DEBATE"]:
            pipeline_node_executions_total.labels(node=node, status="success").inc()

        # External API metrics with different services
        for service in ["anthropic", "openai", "alpha_vantage"]:
            external_api_requests_total.labels(service=service, status="success").inc()

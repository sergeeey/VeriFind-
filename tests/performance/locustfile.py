"""
Locust Load Testing for APE 2026 API.

Week 9 Day 5: Load Testing + Performance Validation

Targets:
- 100 concurrent users
- P95 response time < 5s
- P99 response time < 10s
- Throughput > 10 req/sec
- Success rate > 95%

Usage:
    # Run with web UI
    locust -f tests/performance/locustfile.py --host http://localhost:8000

    # Run headless (100 users, 10/sec spawn rate, 5 min duration)
    locust -f tests/performance/locustfile.py --host http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 5m --headless

    # Run with custom settings
    locust -f tests/performance/locustfile.py --host http://localhost:8000 \
           --users 50 --spawn-rate 5 --run-time 2m --headless \
           --csv results/load_test
"""

import random
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# ============================================================================
# Test Data - Sample Financial Queries
# ============================================================================

SAMPLE_QUERIES = [
    # Sharpe ratio queries
    "Calculate the Sharpe ratio for AAPL from 2023-01-01 to 2023-12-31",
    "What is the Sharpe ratio of SPY in 2023?",
    "Compute Sharpe ratio for TSLA between January and December 2023",

    # Correlation queries
    "What is the correlation between SPY and QQQ?",
    "Calculate correlation of AAPL and MSFT in 2023",
    "Show me the correlation between GOOGL and AMZN",

    # Volatility queries
    "What is the volatility of TSLA in 2023?",
    "Calculate the historical volatility of NVDA",
    "Measure the volatility of META over the last year",

    # Beta queries
    "What is the beta of AAPL relative to SPY?",
    "Calculate beta for TSLA against the S&P 500",
    "Show me the beta of GOOGL vs market",

    # Return queries
    "What was the annual return of AAPL in 2023?",
    "Calculate the returns for SPY from 2022 to 2023",
    "Show me the performance of QQQ in 2023",
]


# ============================================================================
# APE User - Simulates Real User Behavior
# ============================================================================

class APEUser(HttpUser):
    """
    Simulates a user interacting with APE 2026 API.

    User Journey:
    1. Health check
    2. Submit query
    3. Poll status until complete
    4. Retrieve results
    """

    # Wait 1-3 seconds between tasks (realistic user behavior)
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a simulated user starts."""
        # Set default headers (API key auth)
        self.api_key = "sk-ape-load-test-key-12345678901234567890"
        self.client.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })

        # Track active queries
        self.active_queries = []

    @task(1)
    def health_check(self):
        """Check API health (low frequency)."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="GET /health"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure(f"Unhealthy status: {data.get('status')}")
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(10)
    def submit_query(self):
        """Submit a financial analysis query."""
        query = random.choice(SAMPLE_QUERIES)

        with self.client.post(
            "/query",
            json={"query": query},
            catch_response=True,
            name="POST /query"
        ) as response:
            if response.status_code == 202:
                data = response.json()
                query_id = data.get("query_id")

                if query_id:
                    self.active_queries.append(query_id)
                    response.success()
                else:
                    response.failure("No query_id in response")
            else:
                response.failure(f"Query submission failed: {response.status_code}")

    @task(15)
    def check_status(self):
        """Poll query status (high frequency)."""
        if not self.active_queries:
            return  # No active queries to check

        # Pick random active query
        query_id = random.choice(self.active_queries)

        with self.client.get(
            f"/status/{query_id}",
            catch_response=True,
            name="GET /status/{id}"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")

                # Remove from active if completed or failed
                if status in ["completed", "failed", "error"]:
                    self.active_queries.remove(query_id)

                response.success()
            elif response.status_code == 404:
                # Query not found, remove from active
                self.active_queries.remove(query_id)
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")

    @task(5)
    def get_results(self):
        """Retrieve query results (medium frequency)."""
        if not self.active_queries:
            return

        # Pick random query (might not be completed yet)
        query_id = random.choice(self.active_queries)

        with self.client.get(
            f"/results/{query_id}",
            catch_response=True,
            name="GET /results/{id}"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "completed":
                    # Successfully retrieved results
                    self.active_queries.remove(query_id)
                    response.success()
                else:
                    # Query not ready yet
                    response.success()
            elif response.status_code == 404:
                self.active_queries.remove(query_id)
                response.success()
            else:
                response.failure(f"Results retrieval failed: {response.status_code}")


# ============================================================================
# Heavy User - Aggressive Load Testing
# ============================================================================

class HeavyUser(HttpUser):
    """
    Aggressive user for stress testing.

    Submits queries rapidly without waiting for completion.
    Used for stress testing peak load scenarios.
    """

    wait_time = between(0.1, 0.5)  # Very short wait

    def on_start(self):
        self.api_key = "sk-ape-stress-test-key-12345678901234567890"
        self.client.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })

    @task
    def rapid_fire_queries(self):
        """Submit queries as fast as possible."""
        query = random.choice(SAMPLE_QUERIES)

        self.client.post(
            "/query",
            json={"query": query},
            name="POST /query (stress)"
        )


# ============================================================================
# Custom Event Handlers - Performance Metrics
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "="*70)
    print("APE 2026 Load Test Started")
    print("="*70)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    stats = environment.runner.stats

    print("\n" + "="*70)
    print("APE 2026 Load Test Summary")
    print("="*70)

    # Overall stats
    total_stats = stats.total
    print(f"Total Requests: {total_stats.num_requests}")
    print(f"Total Failures: {total_stats.num_failures}")
    print(f"Success Rate: {((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100):.2f}%")
    print(f"Total RPS: {total_stats.total_rps:.2f}")

    # Response times
    print(f"\nResponse Times:")
    print(f"  Average: {total_stats.avg_response_time:.0f}ms")
    print(f"  Median: {total_stats.median_response_time:.0f}ms")
    print(f"  P95: {total_stats.get_response_time_percentile(0.95):.0f}ms")
    print(f"  P99: {total_stats.get_response_time_percentile(0.99):.0f}ms")
    print(f"  Max: {total_stats.max_response_time:.0f}ms")

    # Success criteria
    print(f"\nSuccess Criteria:")
    p95 = total_stats.get_response_time_percentile(0.95)
    p99 = total_stats.get_response_time_percentile(0.99)
    rps = total_stats.total_rps
    success_rate = (total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100

    p95_pass = "✅ PASS" if p95 < 5000 else "❌ FAIL"
    p99_pass = "✅ PASS" if p99 < 10000 else "❌ FAIL"
    rps_pass = "✅ PASS" if rps > 10 else "❌ FAIL"
    success_pass = "✅ PASS" if success_rate > 95 else "❌ FAIL"

    print(f"  P95 < 5s: {p95_pass} ({p95:.0f}ms)")
    print(f"  P99 < 10s: {p99_pass} ({p99:.0f}ms)")
    print(f"  RPS > 10: {rps_pass} ({rps:.2f})")
    print(f"  Success > 95%: {success_pass} ({success_rate:.2f}%)")

    print("="*70 + "\n")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import os
    os.system("locust -f locustfile.py --host http://localhost:8000")

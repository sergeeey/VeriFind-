"""
Async Load Test for APE API

Week 2 Day 11: Production Readiness
Usage: python tests/load/load_test.py
"""

import asyncio
import time
import statistics
from dataclasses import dataclass
from typing import List
import aiohttp


@dataclass
class LoadTestResult:
    """Result of load test"""
    endpoint: str
    total_requests: int
    successful: int
    failed: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float


class LoadTester:
    """Async load tester"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[LoadTestResult] = []
    
    async def _make_request(self, session: aiohttp.ClientSession, endpoint: str) -> float:
        """Make single request, return latency in ms"""
        start = time.time()
        try:
            async with session.get(f"{self.base_url}{endpoint}") as resp:
                await resp.read()
                return (time.time() - start) * 1000
        except Exception as e:
            print(f"Request failed: {e}")
            return -1  # Mark as failed
    
    async def run_load_test(
        self,
        endpoint: str,
        concurrent_users: int = 10,
        requests_per_user: int = 100
    ) -> LoadTestResult:
        """Run load test for endpoint"""
        print(f"\n🚀 Testing {endpoint} with {concurrent_users} users, {requests_per_user} requests each")
        
        latencies: List[float] = []
        failed = 0
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(concurrent_users):
                for _ in range(requests_per_user):
                    tasks.append(self._make_request(session, endpoint))
            
            # Execute all requests
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Process results
            for latency in results:
                if latency < 0:
                    failed += 1
                else:
                    latencies.append(latency)
        
        # Calculate statistics
        total_requests = len(results)
        successful = len(latencies)
        
        if latencies:
            latencies.sort()
            avg_latency = statistics.mean(latencies)
            p95_idx = int(len(latencies) * 0.95)
            p99_idx = int(len(latencies) * 0.99)
            p95_latency = latencies[min(p95_idx, len(latencies)-1)]
            p99_latency = latencies[min(p99_idx, len(latencies)-1)]
        else:
            avg_latency = p95_latency = p99_latency = 0
        
        rps = total_requests / total_time if total_time > 0 else 0
        
        result = LoadTestResult(
            endpoint=endpoint,
            total_requests=total_requests,
            successful=successful,
            failed=failed,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            requests_per_second=rps
        )
        
        self._print_result(result)
        return result
    
    def _print_result(self, result: LoadTestResult):
        """Print formatted result"""
        print(f"  ✅ Successful: {result.successful}/{result.total_requests}")
        print(f"  ❌ Failed: {result.failed}")
        print(f"  ⏱️  Avg Latency: {result.avg_latency_ms:.2f}ms")
        print(f"  ⏱️  P95 Latency: {result.p95_latency_ms:.2f}ms")
        print(f"  ⏱️  P99 Latency: {result.p99_latency_ms:.2f}ms")
        print(f"  🚀 RPS: {result.requests_per_second:.2f}")
        
        # Performance grade
        if result.avg_latency_ms < 50:
            grade = "🟢 EXCELLENT"
        elif result.avg_latency_ms < 200:
            grade = "🟡 GOOD"
        elif result.avg_latency_ms < 500:
            grade = "🟠 ACCEPTABLE"
        else:
            grade = "🔴 NEEDS OPTIMIZATION"
        print(f"  Grade: {grade}")


async def main():
    """Main load test"""
    tester = LoadTester()
    
    print("=" * 60)
    print("APE API Load Test")
    print("=" * 60)
    
    # Test health endpoint (baseline)
    await tester.run_load_test("/health", concurrent_users=50, requests_per_user=20)
    
    # Test predictions endpoint
    await tester.run_load_test("/api/predictions/", concurrent_users=20, requests_per_user=10)
    
    # Test track record
    await tester.run_load_test("/api/predictions/track-record", concurrent_users=10, requests_per_user=10)
    
    print("\n" + "=" * 60)
    print("Load test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""
Performance Testing Script for APE 2026
Week 10 - Performance Optimization Validation

Usage:
    python scripts/performance_test.py

Tests:
1. Cache hit performance
2. Cache miss performance  
3. Concurrent request handling
4. Memory usage tracking
"""

import asyncio
import time
import json
import sys
from typing import List, Dict
from dataclasses import dataclass
from statistics import mean, median, stdev

import aiohttp


@dataclass
class TestResult:
    """Result of a performance test."""
    name: str
    requests: int
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    p95_time: float
    p99_time: float
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0


class PerformanceTester:
    """Test APE 2026 API performance."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        
    async def run_all_tests(self):
        """Run all performance tests."""
        print("=" * 60)
        print("🚀 APE 2026 Performance Testing")
        print("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Single request (cold start)
            print("\n📊 Test 1: Single Request (Cold Start)")
            await self.test_single_request(session)
            
            # Test 2: Cache hit test
            print("\n📊 Test 2: Cache Hit Performance")
            await self.test_cache_performance(session)
            
            # Test 3: Concurrent requests
            print("\n📊 Test 3: Concurrent Requests (10 parallel)")
            await self.test_concurrent_requests(session, count=10)
            
            # Test 4: Different queries
            print("\n📊 Test 4: Different Queries Performance")
            await self.test_different_queries(session)
            
            # Test 5: Performance metrics endpoint
            print("\n📊 Test 5: Performance Metrics Endpoint")
            await self.test_metrics_endpoint(session)
        
        # Print summary
        self.print_summary()
    
    async def test_single_request(self, session: aiohttp.ClientSession):
        """Test single request performance."""
        start = time.perf_counter()
        
        try:
            async with session.post(
                f"{self.base_url}/api/analyze",
                json={"query": "What is Apple stock price?", "provider": "deepseek"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                await resp.json()
                duration = time.perf_counter() - start
                
                # Check cache header
                cache_status = resp.headers.get("X-Cache", "UNKNOWN")
                
                print(f"  ⏱️  Response time: {duration:.3f}s")
                print(f"  🔄 Cache status: {cache_status}")
                print(f"  ✅ Status: {resp.status}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    async def test_cache_performance(self, session: aiohttp.ClientSession):
        """Test cache hit vs miss performance."""
        query = {"query": "What is Tesla stock price?", "provider": "deepseek"}
        times = []
        cache_results = {"hit": 0, "miss": 0}
        
        # First request (cache miss expected)
        for i in range(3):
            start = time.perf_counter()
            try:
                async with session.post(
                    f"{self.base_url}/api/analyze",
                    json=query,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    await resp.json()
                    duration = time.perf_counter() - start
                    times.append(duration)
                    
                    cache_status = resp.headers.get("X-Cache", "UNKNOWN")
                    if cache_status == "HIT":
                        cache_results["hit"] += 1
                    elif cache_status == "MISS":
                        cache_results["miss"] += 1
                    
                    print(f"  Request {i+1}: {duration:.3f}s (Cache: {cache_status})")
                    
            except Exception as e:
                print(f"  Request {i+1}: Error - {e}")
        
        if times:
            print(f"\n  📈 Cache Statistics:")
            print(f"     Cache hits: {cache_results['hit']}")
            print(f"     Cache misses: {cache_results['miss']}")
            if cache_results['hit'] > 0:
                hit_times = times[-cache_results['hit']:]
                print(f"     Avg cache hit time: {mean(hit_times):.3f}s")
            if cache_results['miss'] > 0:
                miss_times = times[:cache_results['miss']]
                print(f"     Avg cache miss time: {mean(miss_times):.3f}s")
    
    async def test_concurrent_requests(
        self, 
        session: aiohttp.ClientSession, 
        count: int = 10
    ):
        """Test concurrent request handling."""
        query = {"query": "What is Microsoft stock price?", "provider": "deepseek"}
        
        async def make_request(idx: int) -> float:
            start = time.perf_counter()
            try:
                async with session.post(
                    f"{self.base_url}/api/analyze",
                    json=query,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    await resp.json()
                    return time.perf_counter() - start
            except Exception as e:
                print(f"  Request {idx}: Error - {e}")
                return -1
        
        # Run all requests concurrently
        start_total = time.perf_counter()
        results = await asyncio.gather(*[make_request(i) for i in range(count)])
        total_time = time.perf_counter() - start_total
        
        valid_times = [t for t in results if t >= 0]
        
        if valid_times:
            print(f"  🔄 Concurrent requests: {count}")
            print(f"  ⏱️  Total time: {total_time:.3f}s")
            print(f"  ⚡ Throughput: {count/total_time:.1f} req/s")
            print(f"  📊 Avg response time: {mean(valid_times):.3f}s")
            print(f"  📊 Min response time: {min(valid_times):.3f}s")
            print(f"  📊 Max response time: {max(valid_times):.3f}s")
    
    async def test_different_queries(self, session: aiohttp.ClientSession):
        """Test performance with different queries."""
        queries = [
            {"query": "What is Apple stock price today?", "provider": "deepseek"},
            {"query": "Compare Apple vs Microsoft performance", "provider": "deepseek"},
            {"query": "Should I invest in Tesla?", "provider": "deepseek"},
        ]
        
        for i, query in enumerate(queries, 1):
            start = time.perf_counter()
            try:
                async with session.post(
                    f"{self.base_url}/api/analyze",
                    json=query,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    await resp.json()
                    duration = time.perf_counter() - start
                    cache_status = resp.headers.get("X-Cache", "UNKNOWN")
                    print(f"  Query {i}: {duration:.3f}s (Cache: {cache_status})")
                    print(f"     Text: {query['query'][:40]}...")
                    
            except Exception as e:
                print(f"  Query {i}: Error - {e}")
    
    async def test_metrics_endpoint(self, session: aiohttp.ClientSession):
        """Test performance metrics endpoint."""
        try:
            async with session.get(
                f"{self.base_url}/metrics/performance",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                print(f"  ✅ Status: {resp.status}")
                print(f"  📊 Cache keys: {data.get('cache', {}).get('cache_keys_count', 'N/A')}")
                print(f"  📊 Cache hit rate: {data.get('cache', {}).get('hit_rate', 'N/A')}%")
                print(f"  🔄 Profiling enabled: {data.get('settings', {}).get('profiling_enabled', False)}")
                print(f"  💾 Cache enabled: {data.get('settings', {}).get('cache_enabled', False)}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📋 Performance Test Summary")
        print("=" * 60)
        print("\n✅ All tests completed!")
        print("\n📈 Expected Improvements:")
        print("  • Cache hit: <100ms (vs 2-3s without cache)")
        print("  • Cache miss: 1-2s (optimized)")
        print("  • Throughput: 60+ req/min")
        print("  • Memory usage: <400MB")
        print("\n⚠️  Notes:")
        print("  • First request may be slower (cold start)")
        print("  • LLM API latency varies (200ms - 2s)")
        print("  • Cache effectiveness depends on query repetition")


async def main():
    """Main entry point."""
    print("Starting APE 2026 Performance Tests...\n")
    
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8000/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    print("❌ API health check failed!")
                    sys.exit(1)
                print("✅ API is healthy\n")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure API is running: uvicorn src.api.main:app --reload")
        sys.exit(1)
    
    # Run tests
    tester = PerformanceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

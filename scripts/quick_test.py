#!/usr/bin/env python3
"""Quick performance test for APE 2026"""
import time
import requests

print("=" * 60)
print("🚀 APE 2026 Quick Performance Test")
print("=" * 60)

base_url = "http://localhost:8000"

# Test 1: Health check
print("\n📊 Test 1: Health Check")
try:
    start = time.time()
    r = requests.get(f"{base_url}/health", timeout=5)
    elapsed = time.time() - start
    print(f"  Status: {r.status_code}")
    print(f"  Time: {elapsed:.3f}s")
    data = r.json()
    print(f"  API Version: {data.get('version', 'unknown')}")
    print(f"  API Status: {data.get('status', 'unknown')}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 2: First analyze request
print("\n📊 Test 2: First Analyze Request")
query = {"query": "What is Apple stock price?", "provider": "deepseek"}
try:
    start = time.time()
    r = requests.post(f"{base_url}/api/analyze", json=query, timeout=60)
    elapsed = time.time() - start
    print(f"  Status: {r.status_code}")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  X-Cache: {r.headers.get('X-Cache', 'not set')}")
    print(f"  X-Process-Time: {r.headers.get('X-Process-Time', 'not set')}")
    data = r.json()
    print(f"  Response status: {data.get('status', 'unknown')}")
    print(f"  Query ID: {data.get('query_id', 'unknown')[:8]}...")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Second request (cache test)
print("\n📊 Test 3: Second Request (Cache Test)")
try:
    start = time.time()
    r = requests.post(f"{base_url}/api/analyze", json=query, timeout=10)
    elapsed = time.time() - start
    print(f"  Status: {r.status_code}")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  X-Cache: {r.headers.get('X-Cache', 'not set')}")
    if elapsed < 0.5 and r.headers.get('X-Cache') == 'HIT':
        print("  ✅ CACHE HIT! Super fast!")
    elif elapsed < 0.5:
        print("  ✅ Fast response!")
    else:
        print("  ⚠️  Slow - cache may not be working")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Performance metrics
print("\n📊 Test 4: Performance Metrics Endpoint")
try:
    r = requests.get(f"{base_url}/metrics/performance", timeout=5)
    print(f"  Status: {r.status_code}")
    data = r.json()
    settings = data.get("settings", {})
    print(f"  Cache enabled: {settings.get('cache_enabled', False)}")
    print(f"  Profiling enabled: {settings.get('profiling_enabled', False)}")
    cache = data.get("cache", {})
    if "cache_keys_count" in cache:
        print(f"  Cache keys count: {cache['cache_keys_count']}")
    if "hit_rate" in cache:
        print(f"  Cache hit rate: {cache['hit_rate']}%")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Tests completed!")
print("=" * 60)
print("\n📈 Expected Results:")
print("  - First request: 2-3s (cache MISS)")
print("  - Second request: <0.1s (cache HIT)")
print("  - Cache keys: >0")
print("  - X-Cache header: HIT/MISS")

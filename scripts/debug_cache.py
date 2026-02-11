#!/usr/bin/env python3
"""Debug cache behavior"""
import time
import requests
import redis

print("=" * 60)
print("🔍 Cache Debug Tool")
print("=" * 60)

base_url = "http://localhost:8000"

# Check Redis directly
print("\n📊 Checking Redis Cache:")
try:
    r = redis.Redis(host='localhost', port=6380, decode_responses=True)
    keys = r.keys("ape:cache:*")
    print(f"  Total cache keys: {len(keys)}")
    for key in keys[:3]:  # Show first 3
        ttl = r.ttl(key)
        print(f"  Key: {key[:40]}... TTL: {ttl}s")
except Exception as e:
    print(f"  ❌ Redis error: {e}")

# Make 3 identical requests
print("\n📊 Making 3 identical requests:")
query = {"query": "Debug cache test?", "provider": "deepseek"}

for i in range(3):
    print(f"\n  Request {i+1}:")
    start = time.time()
    try:
        resp = requests.post(f"{base_url}/api/analyze", json=query, timeout=60)
        elapsed = time.time() - start
        
        print(f"    Time: {elapsed:.3f}s")
        print(f"    Status: {resp.status_code}")
        print(f"    X-Cache: {resp.headers.get('X-Cache', 'NOT SET')}")
        print(f"    X-Process-Time: {resp.headers.get('X-Process-Time', 'NOT SET')}")
        
        # Check if response is actually from cache
        if resp.headers.get('X-Cache') == 'HIT' and elapsed > 1.0:
            print("    ⚠️  WARNING: Cache HIT but slow response!")
            print("    🔧 Cache middleware not working properly")
        elif resp.headers.get('X-Cache') == 'HIT' and elapsed < 0.5:
            print("    ✅ FAST! Cache working!")
            
    except Exception as e:
        print(f"    ❌ Error: {e}")

# Check Redis again
print("\n📊 Redis after requests:")
try:
    keys = r.keys("ape:cache:*")
    print(f"  Total cache keys: {len(keys)}")
except Exception as e:
    print(f"  ❌ Redis error: {e}")

print("\n" + "=" * 60)
print("Debug complete!")
print("=" * 60)

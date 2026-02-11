/**
 * k6 Load Test for APE 2026
 * Week 10 - Performance Optimization
 * 
 * Usage:
 *   k6 run scripts/load_test.js
 * 
 * Requirements:
 *   npm install -g k6
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const cacheHitRate = new Rate('cache_hits');
const responseTime = new Trend('response_time');
const slowRequests = new Counter('slow_requests');

// Test configuration
export const options = {
  stages: [
    // Ramp up
    { duration: '1m', target: 10 },   // 10 users
    { duration: '2m', target: 20 },   // 20 users
    // Steady state
    { duration: '3m', target: 30 },   // 30 users (peak)
    // Ramp down
    { duration: '1m', target: 10 },   // 10 users
    { duration: '1m', target: 0 },    // 0 users
  ],
  thresholds: {
    // Performance thresholds
    http_req_duration: ['p(95)<5000'],  // 95% under 5s
    http_req_duration: ['p(50)<2000'],  // 50% under 2s
    http_req_failed: ['rate<0.1'],      // <10% errors
    cache_hits: ['rate>0.7'],           // >70% cache hit rate
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test queries
const queries = [
  { query: 'What is Apple stock price?', provider: 'deepseek' },
  { query: 'What is Tesla stock price?', provider: 'deepseek' },
  { query: 'Compare Apple vs Microsoft', provider: 'deepseek' },
  { query: 'Should I invest in Amazon?', provider: 'deepseek' },
  { query: 'What is Google stock price?', provider: 'deepseek' },
];

export default function () {
  group('Health Check', () => {
    const healthRes = http.get(`${BASE_URL}/health`);
    check(healthRes, {
      'health status is 200': (r) => r.status === 200,
      'health response time < 500ms': (r) => r.timings.duration < 500,
    });
  });

  group('API Analysis', () => {
    // Pick random query
    const query = queries[Math.floor(Math.random() * queries.length)];
    
    const payload = JSON.stringify(query);
    const params = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const startTime = Date.now();
    const res = http.post(
      `${BASE_URL}/api/analyze`,
      payload,
      params
    );
    const duration = Date.now() - startTime;

    // Track response time
    responseTime.add(duration);

    // Check cache status
    const cacheHeader = res.headers['X-Cache'];
    const isCacheHit = cacheHeader === 'HIT';
    cacheHitRate.add(isCacheHit);

    // Track slow requests (>2s)
    if (duration > 2000) {
      slowRequests.add(1);
    }

    // Validate response
    check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 5s': (r) => r.timings.duration < 5000,
      'has query_id': (r) => JSON.parse(r.body).query_id !== undefined,
      'has status': (r) => JSON.parse(r.body).status !== undefined,
    });

    // Log cache status for debugging
    if (__ITER % 10 === 0) {
      console.log(`Query: ${query.query.substring(0, 30)}... | Cache: ${cacheHeader} | Time: ${duration}ms`);
    }
  });

  // Random sleep between 1-3 seconds (simulates think time)
  sleep(Math.random() * 2 + 1);
}

export function handleSummary(data) {
  return {
    'load_test_results.json': JSON.stringify({
      metrics: {
        http_req_duration: data.metrics.http_req_duration,
        http_req_failed: data.metrics.http_req_failed,
        cache_hits: data.metrics.cache_hits,
        response_time: data.metrics.response_time,
        slow_requests: data.metrics.slow_requests,
      },
      thresholds: data.thresholds,
      summary: {
        total_requests: data.metrics.http_reqs.count,
        failed_requests: data.metrics.http_req_failed.count,
        avg_response_time: data.metrics.http_req_duration.avg,
        p95_response_time: data.metrics.http_req_duration['p(95)'],
        cache_hit_rate: data.metrics.cache_hits ? data.metrics.cache_hits.rate : 0,
      },
    }, null, 2),
  };
}

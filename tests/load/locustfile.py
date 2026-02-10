"""
Load Testing for APE API

Week 2 Day 11: Production Readiness
Usage: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between
import random


class APIUser(HttpUser):
    """Simulated API user"""
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Called when user starts"""
        self.tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]
    
    @task(5)
    def health_check(self):
        """Health endpoint - most frequent"""
        self.client.get("/health")
    
    @task(3)
    def get_predictions(self):
        """Get predictions list"""
        ticker = random.choice(self.tickers)
        self.client.get(f"/api/predictions/?ticker={ticker}")
    
    @task(2)
    def get_corridor(self):
        """Get price corridor"""
        ticker = random.choice(self.tickers)
        self.client.get(f"/api/predictions/{ticker}/corridor?limit=10")
    
    @task(2)
    def get_track_record(self):
        """Get track record"""
        self.client.get("/api/predictions/track-record")
    
    @task(1)
    def submit_query(self):
        """Submit analysis query - less frequent (costs money)"""
        self.client.post("/api/query", json={
            "query": f"Analyze {random.choice(self.tickers)} stock performance"
        })


class PeakLoadUser(HttpUser):
    """High-frequency user for peak load testing"""
    wait_time = between(0.1, 0.5)  # 100-500ms between requests
    
    @task(10)
    def health_check(self):
        """Rapid health checks"""
        self.client.get("/health")
    
    @task(1)
    def readiness_check(self):
        """Readiness probe"""
        self.client.get("/ready")

"""Unit tests for price alert scheduler."""

import pytest

from src.alerts.scheduler import PriceAlertScheduler


@pytest.mark.asyncio
async def test_alert_scheduler_run_check(monkeypatch):
    class FakeStore:
        def __init__(self, db_url):
            self.db_url = db_url

    class FakeChecker:
        def __init__(self, store):
            self.store = store

        def check_active_alerts(self):
            return {
                "total_checked": 3,
                "triggered_count": 1,
                "notifications_sent": 1,
                "rows": [],
            }

    monkeypatch.setattr("src.alerts.scheduler.PriceAlertStore", FakeStore)
    monkeypatch.setattr("src.alerts.scheduler.PriceAlertChecker", FakeChecker)

    scheduler = PriceAlertScheduler()
    summary = await scheduler.run_check(db_url="postgresql://test")

    assert summary["total_checked"] == 3
    assert summary["triggered_count"] == 1
    assert summary["notifications_sent"] == 1
    assert scheduler.last_run_at is not None


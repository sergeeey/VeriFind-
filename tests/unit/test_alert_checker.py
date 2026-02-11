"""Unit tests for price alert checker and notifier integration."""

from datetime import datetime, timedelta, timezone

from src.alerts.price_alert_checker import PriceAlertChecker


def test_checker_triggers_and_sends_notification():
    class FakeStore:
        def __init__(self):
            self.checked = []
            self.notified = []

        def list_alerts(self, ticker=None, active_only=True):
            return [
                {"id": "a1", "ticker": "AAPL", "condition": "above", "target_price": 200},
                {"id": "a2", "ticker": "MSFT", "condition": "below", "target_price": 300},
            ]

        def mark_checked(self, alert_id, triggered):
            self.checked.append((alert_id, triggered))

        def mark_notified(self, alert_id):
            self.notified.append(alert_id)

    class FakeNotifier:
        def __init__(self):
            self.sent = []

        def notify_price_alert(self, alert, current_price):
            self.sent.append((alert["id"], current_price))
            return True

    store = FakeStore()
    notifier = FakeNotifier()

    checker = PriceAlertChecker(
        store=store,
        notifier=notifier,
        price_fetcher=lambda ticker: 210.0 if ticker == "AAPL" else 295.0,
    )
    summary = checker.check_active_alerts()

    assert summary["total_checked"] == 2
    assert summary["triggered_count"] == 2
    assert summary["notifications_sent"] == 2
    assert len(store.checked) == 2
    assert store.notified == ["a1", "a2"]
    assert len(notifier.sent) == 2


def test_checker_handles_no_price_data():
    class FakeStore:
        def list_alerts(self, ticker=None, active_only=True):
            return [{"id": "a1", "ticker": "AAPL", "condition": "above", "target_price": 200}]

        def mark_checked(self, alert_id, triggered):
            self.last = (alert_id, triggered)

        def mark_notified(self, alert_id):
            raise AssertionError("mark_notified should not run when alert is not triggered")

    class FakeNotifier:
        def notify_price_alert(self, alert, current_price):
            raise AssertionError("Notifier should not run when not triggered")

    checker = PriceAlertChecker(
        store=FakeStore(),
        notifier=FakeNotifier(),
        price_fetcher=lambda ticker: None,
    )
    summary = checker.check_active_alerts()

    assert summary["total_checked"] == 1
    assert summary["triggered_count"] == 0
    assert summary["notifications_sent"] == 0
    assert summary["rows"][0]["current_price"] is None


def test_checker_respects_notification_cooldown(monkeypatch):
    class FakeStore:
        def __init__(self):
            self.notified = []

        def list_alerts(self, ticker=None, active_only=True):
            return [
                {
                    "id": "a1",
                    "ticker": "AAPL",
                    "condition": "above",
                    "target_price": 200,
                    "last_notified_at": datetime.now(timezone.utc) - timedelta(minutes=10),
                }
            ]

        def mark_checked(self, alert_id, triggered):
            return None

        def mark_notified(self, alert_id):
            self.notified.append(alert_id)

    class FakeNotifier:
        def __init__(self):
            self.sent = 0

        def notify_price_alert(self, alert, current_price):
            self.sent += 1
            return True

    monkeypatch.setenv("ALERT_NOTIFICATION_COOLDOWN_MINUTES", "180")

    store = FakeStore()
    notifier = FakeNotifier()
    checker = PriceAlertChecker(
        store=store,
        notifier=notifier,
        price_fetcher=lambda ticker: 210.0,
    )

    summary = checker.check_active_alerts()

    assert summary["triggered_count"] == 1
    assert summary["notifications_sent"] == 0
    assert notifier.sent == 0
    assert store.notified == []


def test_checker_sends_notification_after_cooldown(monkeypatch):
    class FakeStore:
        def __init__(self):
            self.notified = []

        def list_alerts(self, ticker=None, active_only=True):
            return [
                {
                    "id": "a1",
                    "ticker": "AAPL",
                    "condition": "above",
                    "target_price": 200,
                    "last_notified_at": datetime.now(timezone.utc) - timedelta(minutes=400),
                }
            ]

        def mark_checked(self, alert_id, triggered):
            return None

        def mark_notified(self, alert_id):
            self.notified.append(alert_id)

    class FakeNotifier:
        def __init__(self):
            self.sent = 0

        def notify_price_alert(self, alert, current_price):
            self.sent += 1
            return True

    monkeypatch.setenv("ALERT_NOTIFICATION_COOLDOWN_MINUTES", "180")

    store = FakeStore()
    notifier = FakeNotifier()
    checker = PriceAlertChecker(
        store=store,
        notifier=notifier,
        price_fetcher=lambda ticker: 210.0,
    )

    summary = checker.check_active_alerts()

    assert summary["triggered_count"] == 1
    assert summary["notifications_sent"] == 1
    assert notifier.sent == 1
    assert store.notified == ["a1"]

"""Unit tests for price alert notifier channels."""

from src.alerts.notifier import PriceAlertNotifier


def _sample_alert():
    return {
        "id": "a1",
        "ticker": "AAPL",
        "condition": "above",
        "target_price": 200.0,
    }


def test_notifier_webhook_delivery(monkeypatch):
    class FakeResponse:
        status_code = 200

    calls = []

    def fake_post(url, json=None, timeout=5):
        calls.append((url, json, timeout))
        return FakeResponse()

    monkeypatch.setattr("src.alerts.notifier.requests.post", fake_post)

    notifier = PriceAlertNotifier(webhook_url="https://example.test/webhook")
    # Disable email path for this test
    notifier.smtp_server = None
    delivered = notifier.notify_price_alert(_sample_alert(), current_price=210.0)

    assert delivered is True
    assert len(calls) == 1
    assert calls[0][0] == "https://example.test/webhook"


def test_notifier_email_delivery(monkeypatch):
    smtp_calls = {"sent": 0, "login": 0, "starttls": 0}

    class FakeSMTP:
        def __init__(self, server, port, timeout=10):
            self.server = server
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            return None

        def starttls(self):
            smtp_calls["starttls"] += 1

        def login(self, username, password):
            smtp_calls["login"] += 1

        def send_message(self, message):
            smtp_calls["sent"] += 1

    monkeypatch.setattr("src.alerts.notifier.smtplib.SMTP", FakeSMTP)

    notifier = PriceAlertNotifier(webhook_url=None)
    notifier.smtp_server = "smtp.example.test"
    notifier.smtp_port = 587
    notifier.smtp_username = "alerts@example.test"
    notifier.smtp_password = "secret"
    notifier.email_from = "alerts@example.test"
    notifier.email_to = "team@example.test"

    delivered = notifier.notify_price_alert(_sample_alert(), current_price=210.0)

    assert delivered is True
    assert smtp_calls["starttls"] == 1
    assert smtp_calls["login"] == 1
    assert smtp_calls["sent"] == 1


def test_notifier_returns_false_when_no_channel_configured(monkeypatch):
    # Ensure webhook isn't called unexpectedly
    monkeypatch.setattr("src.alerts.notifier.requests.post", lambda *args, **kwargs: None)

    notifier = PriceAlertNotifier(webhook_url=None)
    notifier.smtp_server = None
    notifier.email_to = None
    notifier.email_from = None

    delivered = notifier.notify_price_alert(_sample_alert(), current_price=210.0)
    assert delivered is False


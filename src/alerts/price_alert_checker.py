"""Shared checker for manual and scheduled price alert evaluations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
import logging
import os

import yfinance as yf

from src.storage.price_alert_store import PriceAlertStore
from src.alerts.notifier import PriceAlertNotifier


logger = logging.getLogger(__name__)


def fetch_latest_price(ticker: str) -> Optional[float]:
    """Fetch latest close via yfinance."""
    try:
        frame = yf.Ticker(ticker).history(period="5d")
        if frame.empty:
            return None
        return float(frame["Close"].iloc[-1])
    except Exception:
        return None


class PriceAlertChecker:
    """Checks active price alerts against current market price."""

    def __init__(
        self,
        store: PriceAlertStore,
        notifier: Optional[PriceAlertNotifier] = None,
        price_fetcher: Callable[[str], Optional[float]] = fetch_latest_price,
    ):
        self.store = store
        self.notifier = notifier or PriceAlertNotifier()
        self.price_fetcher = price_fetcher
        self.cooldown_minutes = max(int(os.getenv("ALERT_NOTIFICATION_COOLDOWN_MINUTES", "180")), 0)

    def _normalize_ts(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except Exception:
                return None
        return None

    def _can_send_notification(self, alert: Dict[str, Any]) -> bool:
        if self.cooldown_minutes <= 0:
            return True
        last_notified_at = self._normalize_ts(alert.get("last_notified_at"))
        if not last_notified_at:
            return True
        return datetime.now(timezone.utc) - last_notified_at >= timedelta(minutes=self.cooldown_minutes)

    def check_active_alerts(self, ticker: Optional[str] = None) -> Dict[str, Any]:
        alerts = self.store.list_alerts(ticker=ticker, active_only=True)
        rows: List[Dict[str, Any]] = []
        triggered_count = 0
        notifications_sent = 0

        for alert in alerts:
            current_price = self.price_fetcher(alert["ticker"])
            triggered = False
            if current_price is not None:
                if alert["condition"] == "above":
                    triggered = current_price >= float(alert["target_price"])
                elif alert["condition"] == "below":
                    triggered = current_price <= float(alert["target_price"])

            self.store.mark_checked(alert["id"], triggered=triggered)
            if triggered:
                triggered_count += 1
                if self._can_send_notification(alert):
                    if self.notifier.notify_price_alert(alert=alert, current_price=float(current_price)):
                        notifications_sent += 1
                        self.store.mark_notified(alert["id"])

            rows.append(
                {
                    "id": str(alert["id"]),
                    "ticker": str(alert["ticker"]),
                    "condition": str(alert["condition"]),
                    "target_price": float(alert["target_price"]),
                    "current_price": (float(current_price) if current_price is not None else None),
                    "triggered": triggered,
                }
            )

        summary = {
            "total_checked": len(rows),
            "triggered_count": triggered_count,
            "notifications_sent": notifications_sent,
            "rows": rows,
        }
        logger.info(
            "Alert check complete: checked=%s triggered=%s notifications=%s",
            summary["total_checked"],
            summary["triggered_count"],
            summary["notifications_sent"],
        )
        return summary

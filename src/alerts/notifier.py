"""Notification channels for price alerts."""

from __future__ import annotations

from typing import Dict, Any
import logging
import os
import smtplib
from email.message import EmailMessage

import requests


logger = logging.getLogger(__name__)


class PriceAlertNotifier:
    """Dispatches alert events to configured notification channels."""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.email_to = os.getenv("ALERT_EMAIL_TO") or os.getenv("NOTIFICATION_EMAIL")
        self.email_from = os.getenv("ALERT_EMAIL_FROM") or self.smtp_username

    def _send_email(self, payload: Dict[str, Any]) -> bool:
        """Send alert notification by SMTP email if configured."""
        if not self.smtp_server or not self.email_to or not self.email_from:
            return False

        try:
            msg = EmailMessage()
            msg["Subject"] = f"[APE Alerts] {payload['ticker']} {payload['condition']} {payload['target_price']}"
            msg["From"] = self.email_from
            msg["To"] = self.email_to
            msg.set_content(
                "Price alert triggered.\n\n"
                f"Ticker: {payload['ticker']}\n"
                f"Condition: {payload['condition']}\n"
                f"Target Price: {payload['target_price']}\n"
                f"Current Price: {payload['current_price']}\n"
                f"Alert ID: {payload['alert_id']}\n"
            )

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as smtp:
                smtp.ehlo()
                if self.smtp_username and self.smtp_password:
                    smtp.starttls()
                    smtp.login(self.smtp_username, self.smtp_password)
                smtp.send_message(msg)
            return True
        except Exception as e:
            logger.warning("Alert email delivery failed: %s", e)
            return False

    def notify_price_alert(self, alert: Dict[str, Any], current_price: float) -> bool:
        """
        Send notification for a triggered alert.

        Returns True when at least one channel successfully accepted payload.
        """
        delivered = False
        payload = {
            "type": "price_alert_triggered",
            "alert_id": str(alert.get("id")),
            "ticker": str(alert.get("ticker")),
            "condition": str(alert.get("condition")),
            "target_price": float(alert.get("target_price")),
            "current_price": float(current_price),
        }

        # Webhook channel
        if self.webhook_url:
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=5)
                if 200 <= response.status_code < 300:
                    delivered = True
                else:
                    logger.warning(
                        "Alert webhook returned non-2xx: status=%s alert_id=%s",
                        response.status_code,
                        payload["alert_id"],
                    )
            except Exception as e:
                logger.warning("Alert webhook delivery failed: %s", e)

        # Email channel
        if self._send_email(payload):
            delivered = True

        # Always log for audit/debug visibility
        logger.info(
            "Price alert triggered: ticker=%s condition=%s target=%s current=%s",
            payload["ticker"],
            payload["condition"],
            payload["target_price"],
            payload["current_price"],
        )

        return delivered

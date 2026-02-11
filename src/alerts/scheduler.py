"""Background scheduler for automatic price alert checks."""

from __future__ import annotations

from datetime import datetime, UTC
import asyncio
import logging
from typing import Optional, Dict, Any

from src.alerts.price_alert_checker import PriceAlertChecker
from src.storage.price_alert_store import PriceAlertStore

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except Exception:  # pragma: no cover
    AsyncIOScheduler = None


logger = logging.getLogger(__name__)


class PriceAlertScheduler:
    """Runs periodic price alert checks and exposes health metadata."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.started_at: Optional[datetime] = None
        self.last_run_at: Optional[datetime] = None
        self.last_run_result: Optional[Dict[str, Any]] = None
        self.is_running: bool = False

    async def run_check(self, db_url: str) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()

        def _sync_check():
            store = PriceAlertStore(db_url=db_url)
            checker = PriceAlertChecker(store=store)
            return checker.check_active_alerts()

        summary = await loop.run_in_executor(None, _sync_check)
        self.last_run_at = datetime.now(UTC)
        self.last_run_result = {
            "total_checked": summary.get("total_checked", 0),
            "triggered_count": summary.get("triggered_count", 0),
            "notifications_sent": summary.get("notifications_sent", 0),
        }
        logger.info(
            "Price alert scheduler run complete: checked=%s triggered=%s notifications=%s",
            self.last_run_result["total_checked"],
            self.last_run_result["triggered_count"],
            self.last_run_result["notifications_sent"],
        )
        return self.last_run_result

    def start(self, db_url: str):
        if AsyncIOScheduler is None:
            logger.warning("APScheduler is not installed. Price alert scheduler disabled.")
            return
        if self.is_running:
            return

        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.scheduler.add_job(
            self.run_check,
            trigger="interval",
            id="price_alert_check",
            minutes=15,
            kwargs={"db_url": db_url},
            replace_existing=True,
        )
        self.scheduler.start()
        self.started_at = datetime.now(UTC)
        self.is_running = True
        logger.info("Price alert scheduler started (every 15 minutes)")

    def stop(self):
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Price alert scheduler stopped")

    def health(self) -> Dict[str, Any]:
        return {
            "running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_result": self.last_run_result,
            "apscheduler_available": AsyncIOScheduler is not None,
        }


price_alert_scheduler = PriceAlertScheduler()


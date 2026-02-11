"""Daily scheduler for prediction accuracy checks."""

from __future__ import annotations

from datetime import datetime, UTC
import asyncio
import logging
from typing import Optional, Dict, Any

from src.api.metrics import prediction_check_last_run_timestamp
from src.predictions.prediction_store import PredictionStore
from src.predictions.accuracy_tracker import AccuracyTracker

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except Exception:  # pragma: no cover - graceful fallback when dependency is missing
    AsyncIOScheduler = None

logger = logging.getLogger(__name__)


class PredictionScheduler:
    """Runs daily prediction checks and exposes runtime status."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.started_at: Optional[datetime] = None
        self.last_run_at: Optional[datetime] = None
        self.last_run_result: Optional[Dict[str, Any]] = None
        self.is_running: bool = False

    async def run_daily_check(self, db_url: str, days_until_target: int = 7) -> Dict[str, Any]:
        """Execute daily prediction check."""
        loop = asyncio.get_running_loop()

        def _sync_check():
            store = PredictionStore(db_url=db_url)
            tracker = AccuracyTracker(prediction_store=store)
            return tracker.run_daily_check(days_until_target=days_until_target)

        results = await loop.run_in_executor(None, _sync_check)
        successful = sum(1 for item in results if item.get("success"))
        summary = {
            "checked": len(results),
            "successful": successful,
            "failed": len(results) - successful,
        }

        self.last_run_at = datetime.now(UTC)
        self.last_run_result = summary
        prediction_check_last_run_timestamp.set(self.last_run_at.timestamp())
        logger.info(
            "Prediction scheduler run complete: "
            f"checked={summary['checked']}, successful={summary['successful']}, failed={summary['failed']}"
        )
        return summary

    def start(self, db_url: str):
        """Start scheduler if APScheduler is available."""
        if AsyncIOScheduler is None:
            logger.warning("APScheduler is not installed. Prediction scheduler disabled.")
            return

        if self.is_running:
            return

        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.scheduler.add_job(
            self.run_daily_check,
            trigger="cron",
            id="prediction_daily_check",
            hour=18,
            minute=0,
            kwargs={"db_url": db_url, "days_until_target": 7},
            replace_existing=True,
        )
        self.scheduler.start()
        self.started_at = datetime.now(UTC)
        self.is_running = True
        logger.info("Prediction scheduler started (daily at 18:00 UTC)")

    def stop(self):
        """Stop scheduler."""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Prediction scheduler stopped")

    def health(self) -> Dict[str, Any]:
        """Expose scheduler health and runtime details."""
        return {
            "running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_result": self.last_run_result,
            "apscheduler_available": AsyncIOScheduler is not None,
        }


prediction_scheduler = PredictionScheduler()

"""Price alerts API routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...alerts.price_alert_checker import PriceAlertChecker
from ...storage.price_alert_store import PriceAlertStore
from ..config import get_settings


router = APIRouter(prefix="/api/alerts", tags=["Alerts"])
logger = logging.getLogger(__name__)
settings = get_settings()

_alert_store: Optional[PriceAlertStore] = None


class PriceAlertCreateRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    condition: str = Field(..., pattern="^(above|below)$")
    target_price: float = Field(..., gt=0)


class PriceAlertResponse(BaseModel):
    id: str
    ticker: str
    condition: str
    target_price: float
    is_active: bool
    created_at: Optional[str] = None
    last_checked_at: Optional[str] = None
    last_triggered_at: Optional[str] = None
    last_notified_at: Optional[str] = None


class PriceAlertCheckRow(BaseModel):
    id: str
    ticker: str
    condition: str
    target_price: float
    current_price: Optional[float] = None
    triggered: bool


class PriceAlertCheckResponse(BaseModel):
    total_checked: int
    triggered_count: int
    notifications_sent: int = 0
    rows: List[PriceAlertCheckRow]


def get_alert_store() -> PriceAlertStore:
    global _alert_store
    if _alert_store is None:
        _alert_store = PriceAlertStore(settings.timescaledb_url)
    return _alert_store


def _normalize_alert(row: Dict[str, Any]) -> PriceAlertResponse:
    return PriceAlertResponse(
        id=str(row.get("id")),
        ticker=str(row.get("ticker")),
        condition=str(row.get("condition")),
        target_price=float(row.get("target_price")),
        is_active=bool(row.get("is_active", True)),
        created_at=str(row.get("created_at")) if row.get("created_at") else None,
        last_checked_at=str(row.get("last_checked_at")) if row.get("last_checked_at") else None,
        last_triggered_at=str(row.get("last_triggered_at")) if row.get("last_triggered_at") else None,
        last_notified_at=str(row.get("last_notified_at")) if row.get("last_notified_at") else None,
    )


@router.post("", response_model=PriceAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_price_alert(
    request: PriceAlertCreateRequest,
    store: PriceAlertStore = Depends(get_alert_store),
):
    """Create a price alert."""
    try:
        row = store.create_alert(
            ticker=request.ticker.upper(),
            condition=request.condition,
            target_price=request.target_price,
        )
        return _normalize_alert(row)
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create price alert",
        )


@router.get("", response_model=List[PriceAlertResponse])
async def list_price_alerts(
    ticker: Optional[str] = Query(default=None, min_length=1, max_length=10),
    active_only: bool = Query(default=True),
    store: PriceAlertStore = Depends(get_alert_store),
):
    """List price alerts."""
    try:
        rows = store.list_alerts(ticker=ticker, active_only=active_only)
        return [_normalize_alert(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to list alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list price alerts",
        )


@router.delete("/{alert_id}", status_code=status.HTTP_200_OK)
async def delete_price_alert(
    alert_id: str,
    store: PriceAlertStore = Depends(get_alert_store),
):
    """Delete an alert by id."""
    try:
        deleted = store.delete_alert(alert_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )
        return {"deleted": True, "alert_id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete price alert",
        )


@router.post("/check-now", response_model=PriceAlertCheckResponse)
async def check_price_alerts(
    ticker: Optional[str] = Query(default=None, min_length=1, max_length=10),
    store: PriceAlertStore = Depends(get_alert_store),
):
    """Check active alerts against latest market price."""
    try:
        checker = PriceAlertChecker(store=store)
        summary = checker.check_active_alerts(ticker=ticker)
        return PriceAlertCheckResponse(
            total_checked=summary["total_checked"],
            triggered_count=summary["triggered_count"],
            notifications_sent=summary.get("notifications_sent", 0),
            rows=[PriceAlertCheckRow(**row) for row in summary["rows"]],
        )
    except Exception as e:
        logger.error(f"Failed to check alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check price alerts",
        )

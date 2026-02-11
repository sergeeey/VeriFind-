"""Sensitivity analysis API routes."""

from __future__ import annotations

from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import yfinance as yf


router = APIRouter(prefix="/api/sensitivity", tags=["Sensitivity"])
logger = logging.getLogger(__name__)


class PriceSensitivityRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    position_size: float = Field(..., gt=0, description="Number of shares or units")
    base_price: Optional[float] = Field(None, gt=0)
    variation_pct: float = Field(20.0, gt=0, le=100, description="Total +/- range in percent")
    steps: int = Field(9, ge=3, le=51, description="Number of sweep points")


class PriceSensitivityScenario(BaseModel):
    shock_pct: float
    scenario_price: float
    pnl: float
    return_pct: float
    sign_flip: bool = False


class PriceSensitivityResponse(BaseModel):
    ticker: str
    base_price: float
    position_size: float
    variation_pct: float
    steps: int
    scenarios: List[PriceSensitivityScenario]
    sign_flip_detected: bool
    disclaimer: str = "This analysis is for informational purposes only..."


def _load_base_price(ticker: str) -> Optional[float]:
    """Get latest close price via yfinance."""
    try:
        frame = yf.Ticker(ticker).history(period="5d")
        if frame.empty:
            return None
        return float(frame["Close"].iloc[-1])
    except Exception:
        return None


@router.post("/price", response_model=PriceSensitivityResponse, status_code=status.HTTP_200_OK)
async def run_price_sensitivity(request: PriceSensitivityRequest):
    """Run price sweep sensitivity analysis and detect PnL sign flips."""
    ticker = request.ticker.strip().upper()
    base_price = request.base_price if request.base_price else _load_base_price(ticker)
    if base_price is None or base_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to load base price for {ticker}",
        )

    half_range = request.variation_pct
    if request.steps == 1:
        shock_values = [0.0]
    else:
        step_size = (2 * half_range) / (request.steps - 1)
        shock_values = [(-half_range + i * step_size) for i in range(request.steps)]

    scenarios: List[PriceSensitivityScenario] = []
    base_notional = base_price * request.position_size
    baseline_sign = 0
    sign_flip_detected = False

    for shock in shock_values:
        scenario_price = base_price * (1 + shock / 100)
        pnl = (scenario_price - base_price) * request.position_size
        ret = (pnl / base_notional * 100) if base_notional else 0.0
        current_sign = 0
        if pnl > 0:
            current_sign = 1
        elif pnl < 0:
            current_sign = -1
        if baseline_sign == 0 and current_sign != 0:
            baseline_sign = current_sign
        elif baseline_sign != 0 and current_sign != 0 and current_sign != baseline_sign:
            sign_flip_detected = True

        scenarios.append(
            PriceSensitivityScenario(
                shock_pct=round(shock, 4),
                scenario_price=round(float(scenario_price), 6),
                pnl=round(float(pnl), 6),
                return_pct=round(float(ret), 6),
                sign_flip=sign_flip_detected,
            )
        )

    logger.info(
        "Sensitivity run completed: ticker=%s, steps=%s, sign_flip_detected=%s",
        ticker,
        request.steps,
        sign_flip_detected,
    )

    return PriceSensitivityResponse(
        ticker=ticker,
        base_price=round(float(base_price), 6),
        position_size=request.position_size,
        variation_pct=request.variation_pct,
        steps=request.steps,
        scenarios=scenarios,
        sign_flip_detected=sign_flip_detected,
    )


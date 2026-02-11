"""Social/news sentiment API routes."""

from __future__ import annotations

from typing import Any, Dict, List
import logging
import re

from fastapi import APIRouter, HTTPException, Query, status
import yfinance as yf


router = APIRouter(prefix="/api/sentiment", tags=["Sentiment"])
logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "beat", "beats", "growth", "upgrade", "upside", "strong", "surge", "rally", "profit", "record"
}
NEGATIVE_WORDS = {
    "miss", "misses", "downgrade", "downside", "weak", "drop", "selloff", "loss", "lawsuit", "risk"
}


def _score_text(text: str) -> float:
    """Deterministic lexicon sentiment score in [-1, 1]."""
    tokens = re.findall(r"[A-Za-z]+", (text or "").lower())
    if not tokens:
        return 0.0
    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 6)


def _label(score: float) -> str:
    if score > 0.2:
        return "positive"
    if score < -0.2:
        return "negative"
    return "neutral"


@router.get("/{ticker}", status_code=status.HTTP_200_OK)
async def get_ticker_sentiment(
    ticker: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Compute deterministic sentiment from recent ticker news headlines.
    """
    token = ticker.strip().upper()
    try:
        raw_news = yf.Ticker(token).news or []
        items: List[Dict[str, Any]] = []
        for row in raw_news[:limit]:
            title = row.get("title") or ""
            score = _score_text(title)
            items.append(
                {
                    "title": title,
                    "publisher": row.get("publisher"),
                    "link": row.get("link"),
                    "published_at": row.get("providerPublishTime"),
                    "sentiment_score": score,
                    "sentiment_label": _label(score),
                }
            )

        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No news found for {token}",
            )

        avg_score = sum(item["sentiment_score"] for item in items) / len(items)
        return {
            "ticker": token,
            "count": len(items),
            "average_sentiment_score": round(avg_score, 6),
            "average_sentiment_label": _label(avg_score),
            "items": items,
            "method": "lexicon_headline_scoring_v1",
            "disclaimer": "This analysis is for informational purposes only...",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute sentiment for {token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute sentiment",
        )


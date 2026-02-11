"""Educational mode API routes."""

from __future__ import annotations

from typing import Dict, List
import re

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/educational", tags=["Educational"])


class EducationalExplainRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=4000)


class EducationalExplainResponse(BaseModel):
    detected_terms: List[str]
    definitions: Dict[str, str]
    limitations: List[str]
    disclaimer: str = "This analysis is for informational purposes only..."


TERM_DEFINITIONS: Dict[str, str] = {
    "sharpe": "Sharpe ratio measures return per unit of volatility risk. Higher is generally better.",
    "beta": "Beta estimates sensitivity to market moves. Beta > 1 implies higher market sensitivity.",
    "alpha": "Alpha approximates excess return vs benchmark after market risk adjustment.",
    "volatility": "Volatility measures dispersion of returns; higher values imply larger price swings.",
    "correlation": "Correlation measures co-movement between assets from -1 to 1.",
    "drawdown": "Drawdown is the peak-to-trough loss over a period.",
    "rsi": "RSI is a momentum oscillator (0-100) often used to assess overbought/oversold conditions.",
    "ema": "EMA is an exponentially weighted moving average emphasizing recent prices.",
    "p_value": "p-value estimates evidence against a null hypothesis; smaller values indicate stronger evidence.",
}


@router.post("/explain", response_model=EducationalExplainResponse)
async def explain_analysis_text(request: EducationalExplainRequest):
    """Explain detected financial terms and highlight interpretation limitations."""
    text_lower = request.text.lower()
    detected: List[str] = []
    definitions: Dict[str, str] = {}

    for term, explanation in TERM_DEFINITIONS.items():
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, text_lower):
            detected.append(term)
            definitions[term] = explanation

    limitations = [
        "Historical patterns can break under regime changes.",
        "Single-metric decisions can be misleading; combine multiple signals.",
        "Statistical relationships do not guarantee causation.",
    ]
    if not detected:
        limitations.append("No known educational terms detected in text; interpretation may require manual review.")

    return EducationalExplainResponse(
        detected_terms=detected,
        definitions=definitions,
        limitations=limitations,
    )


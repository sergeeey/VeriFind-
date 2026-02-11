"""SEC filings API routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import os

from fastapi import APIRouter, HTTPException, Query, status
import requests


router = APIRouter(prefix="/api/sec", tags=["SEC"])
logger = logging.getLogger(__name__)

_ticker_cik_cache: Optional[Dict[str, str]] = None


def _user_agent() -> str:
    return os.getenv("SEC_API_USER_AGENT", "APE2026/1.0 (research@example.com)")


def _load_ticker_cik_map() -> Dict[str, str]:
    global _ticker_cik_cache
    if _ticker_cik_cache is not None:
        return _ticker_cik_cache

    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": _user_agent(), "Accept": "application/json"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    payload = response.json()

    mapping: Dict[str, str] = {}
    for _, row in payload.items():
        ticker = str(row.get("ticker", "")).upper().strip()
        cik = str(row.get("cik_str", "")).strip()
        if ticker and cik:
            mapping[ticker] = cik
    _ticker_cik_cache = mapping
    return mapping


def _lookup_cik(ticker: str) -> Optional[str]:
    mapping = _load_ticker_cik_map()
    return mapping.get(ticker.upper())


def _fetch_submissions(cik: str) -> Dict[str, Any]:
    cik10 = str(cik).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    headers = {"User-Agent": _user_agent(), "Accept": "application/json"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


@router.get("/filings/{ticker}", status_code=status.HTTP_200_OK)
async def get_recent_filings(
    ticker: str,
    form: Optional[str] = Query(default=None, description="Form filter, e.g. 10-K or 10-Q"),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Get recent SEC filings metadata for ticker."""
    token = ticker.strip().upper()
    cik = _lookup_cik(token)
    if not cik:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CIK not found for ticker {token}",
        )

    try:
        submissions = _fetch_submissions(cik)
        recent = submissions.get("filings", {}).get("recent", {})

        forms = recent.get("form", []) or []
        accession_numbers = recent.get("accessionNumber", []) or []
        filing_dates = recent.get("filingDate", []) or []
        report_dates = recent.get("reportDate", []) or []
        primary_docs = recent.get("primaryDocument", []) or []

        rows: List[Dict[str, Any]] = []
        for idx, filing_form in enumerate(forms):
            if form and str(filing_form).upper() != form.upper():
                continue

            accession = accession_numbers[idx] if idx < len(accession_numbers) else None
            accession_nodash = str(accession).replace("-", "") if accession else None
            primary_doc = primary_docs[idx] if idx < len(primary_docs) else None

            filing_url = None
            if accession and accession_nodash and primary_doc:
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession_nodash}/{primary_doc}"
                )

            rows.append(
                {
                    "ticker": token,
                    "cik": str(cik).zfill(10),
                    "form": filing_form,
                    "filing_date": filing_dates[idx] if idx < len(filing_dates) else None,
                    "report_date": report_dates[idx] if idx < len(report_dates) else None,
                    "accession_number": accession,
                    "primary_document": primary_doc,
                    "filing_url": filing_url,
                }
            )

            if len(rows) >= limit:
                break

        return {
            "ticker": token,
            "cik": str(cik).zfill(10),
            "form_filter": form.upper() if form else None,
            "count": len(rows),
            "filings": rows,
            "source": "sec.gov submissions API",
            "disclaimer": "This analysis is for informational purposes only...",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch SEC filings for {token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch SEC filings",
        )


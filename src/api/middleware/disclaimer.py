"""Disclaimer middleware.

Week 12: Extracted from main.py God Object
"""

from fastapi import Request
from fastapi.responses import JSONResponse
import json
import logging

logger = logging.getLogger(__name__)

LEGAL_DISCLAIMER = {
    "text": (
        "This analysis is for informational purposes only and should not be considered "
        "financial advice. Past performance does not guarantee future results. "
        "Always consult a qualified financial advisor before making investment decisions."
    ),
    "version": "1.0",
    "effective_date": "2026-02-08",
}


async def add_disclaimer_to_json_responses(request: Request, call_next):
    """
    Add legal disclaimer to all JSON responses.
    
    Week 11 Day 3: Legal compliance requirement.
    """
    response = await call_next(request)
    
    # Only add disclaimer to JSON responses
    if response.headers.get("content-type", "").startswith("application/json"):
        # Skip for health/metrics endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return response
        
        # Read response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        try:
            # Parse JSON
            data = json.loads(response_body.decode())
            
            # Add disclaimer if not already present
            if isinstance(data, dict) and "disclaimer" not in data:
                data["disclaimer"] = LEGAL_DISCLAIMER
            
            # Re-encode response
            return JSONResponse(
                content=data,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json"
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            # If not valid JSON, return original response
            return JSONResponse(
                content=response_body.decode(),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    
    return response

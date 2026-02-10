"""API Middleware for APE 2026.

Week 12: Extracted from main.py God Object
"""

from .security import add_security_headers
from .disclaimer import add_disclaimer_to_json_responses
from .rate_limit import add_rate_limit_headers

__all__ = ["add_security_headers", "add_disclaimer_to_json_responses", "add_rate_limit_headers"]

"""API Middleware for APE 2026.

Week 12: Extracted from main.py God Object
"""

from .security import add_security_headers
from .disclaimer import add_disclaimer_to_json_responses

__all__ = ["add_security_headers", "add_disclaimer_to_json_responses"]

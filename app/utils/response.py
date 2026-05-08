"""Legacy response format helpers matching the Bestie handoff contract.

All endpoints should return JSON in the shape:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
from typing import Any, Optional


def success(data: Any = None, message: str = "Success") -> dict:
    """Return a legacy-format success response."""
    return {"status": "1", "data": data, "message": message}


def error(message: str = "Error", data: Any = None) -> dict:
    """Return a legacy-format error response."""
    return {"status": "0", "data": data, "message": message}

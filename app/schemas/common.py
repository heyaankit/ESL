"""Common Pydantic schemas shared across routers."""
from pydantic import BaseModel, Field
from typing import Any, Optional


class LegacyResponse(BaseModel):
    """Standard legacy response envelope used by all endpoints."""
    status: str = Field(..., pattern="^[01]$")
    data: Optional[Any] = None
    message: str = "Success"


class PaginatedRequest(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)

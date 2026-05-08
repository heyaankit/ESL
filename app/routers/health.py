"""Health router — backend health check endpoint.

All endpoints return the legacy response format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lesson import LessonItem
from app.services.ai_service import ai_service
from app.config import settings
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["health"])


# ---------------------------------------------------------------------------
# GET /health  — return backend health status
# ---------------------------------------------------------------------------

@router.get("/health")
def health_check(
    db: Session = Depends(get_db),
):
    """Return backend health status including AI, DB, and lesson counts."""
    try:
        # Count distinct lessons from lesson_items
        lesson_count = db.query(func.count(distinct(LessonItem.lesson))).scalar()
        lesson_count = lesson_count or 0
    except Exception as e:
        logger.error(f"Health check DB query failed: {e}")
        return error(message="Database connection failed")

    return success(
        data={
            "status": "ok",
            "openai_available": ai_service.is_available,
            "model_name": settings.openai_model,
            "lesson_count": lesson_count,
            "database": "connected",
            "version": "2.0.0",
        },
        message="Health check passed",
    )

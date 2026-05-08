"""Notifications router — manage user notifications with read/delete and admin push.

All endpoints return the legacy response format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Header, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import UserNotification
from app.models.user import User
from app.services.notification_service import notification_service
from app.config import settings
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["notifications"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _notification_to_dict(n: UserNotification) -> dict:
    """Serialise a UserNotification ORM object into a plain dict."""
    return {
        "id": n.id,
        "user_id": n.user_id,
        "title": n.title,
        "message": n.message,
        "notification_type": n.notification_type,
        "is_read": n.is_read,
        "read_at": str(n.read_at) if n.read_at else None,
        "is_deleted": n.is_deleted,
        "deleted_at": str(n.deleted_at) if n.deleted_at else None,
        "created_at": str(n.created_at) if n.created_at else None,
    }


# ---------------------------------------------------------------------------
# GET /notifications  — list notifications for a user with pagination
# ---------------------------------------------------------------------------

@router.get("/notifications")
def list_notifications(
    user_id: str = Query(..., description="User ID to fetch notifications for"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    include_deleted: bool = Query(False, description="Include soft-deleted notifications"),
    db: Session = Depends(get_db),
):
    """List stored notifications by user_id with pagination. Default exclude deleted."""
    query = db.query(UserNotification).filter(UserNotification.user_id == user_id)

    if not include_deleted:
        query = query.filter(UserNotification.is_deleted == False)  # noqa: E712

    # Order by newest first
    query = query.order_by(UserNotification.created_at.desc())

    total = query.count()
    offset = (page - 1) * limit
    notifications = query.offset(offset).limit(limit).all()

    return success(
        data={
            "notifications": [_notification_to_dict(n) for n in notifications],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if total > 0 else 0,
            },
        },
        message="Notifications fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /notifications/read  — mark notification as read
# ---------------------------------------------------------------------------

@router.post("/notifications/read")
def mark_notification_read(
    user_id: str = Form(..., description="User ID"),
    notification_id: int = Form(..., description="Notification ID to mark as read"),
    db: Session = Depends(get_db),
):
    """Mark notification as read, set read_at timestamp."""
    notification = (
        db.query(UserNotification)
        .filter(
            UserNotification.id == notification_id,
            UserNotification.user_id == user_id,
        )
        .first()
    )
    if not notification:
        return error(message="Notification not found")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)

    return success(
        data=_notification_to_dict(notification),
        message="Notification marked as read",
    )


# ---------------------------------------------------------------------------
# POST /notifications/delete  — soft-delete notification
# ---------------------------------------------------------------------------

@router.post("/notifications/delete")
def delete_notification(
    user_id: str = Form(..., description="User ID"),
    notification_id: int = Form(..., description="Notification ID to delete"),
    db: Session = Depends(get_db),
):
    """Soft-delete notification, set deleted_at timestamp."""
    notification = (
        db.query(UserNotification)
        .filter(
            UserNotification.id == notification_id,
            UserNotification.user_id == user_id,
        )
        .first()
    )
    if not notification:
        return error(message="Notification not found")

    notification.is_deleted = True
    notification.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)

    return success(
        data=_notification_to_dict(notification),
        message="Notification deleted successfully",
    )


# ---------------------------------------------------------------------------
# GET /notifications/unread-count  — return unread notification count
# ---------------------------------------------------------------------------

@router.get("/notifications/unread-count")
def unread_count(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Return unread notification count."""
    count = (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == user_id,
            UserNotification.is_read == False,  # noqa: E712
            UserNotification.is_deleted == False,  # noqa: E712
        )
        .count()
    )

    return success(
        data={"user_id": user_id, "unread_count": count},
        message="Unread count fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /admin/notifications/test-send  — admin: send test push notification
# ---------------------------------------------------------------------------

@router.post("/admin/notifications/test-send")
def admin_test_send(
    user_id: str = Form(..., description="Target user ID"),
    title: str = Form(..., description="Notification title"),
    message: str = Form(..., description="Notification message body"),
    x_admin_key: Optional[str] = Header(None, alias="x_admin_key"),
    db: Session = Depends(get_db),
):
    """Verify x_admin_key matches settings.admin_push_key, send test push, store notification."""
    # Verify admin key
    if not x_admin_key or x_admin_key != settings.admin_push_key:
        return error(message="Invalid or missing admin key")

    # Look up user and their FCM token
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return error(message="User not found")

    fcm_token = user.fcm_token

    # Send push notification via the notification service
    push_sent = False
    if fcm_token:
        push_sent = notification_service.send_push_notification(
            fcm_token=fcm_token,
            title=title,
            message=message,
            data={"type": "test", "user_id": user_id},
        )
    else:
        logger.warning(f"No FCM token for user {user_id}; skipping push delivery")

    # Store in UserNotification table
    notification = UserNotification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type="system",
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return success(
        data={
            "notification": _notification_to_dict(notification),
            "push_sent": push_sent,
        },
        message="Test notification sent and stored",
    )

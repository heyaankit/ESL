from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from datetime import datetime
from app.database import Base


class UserNotification(Base):
    """Persisted push notification inbox with read/delete timestamps."""
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    notification_type = Column(String, default="reminder")  # reminder, achievement, system
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

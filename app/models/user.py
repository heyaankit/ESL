from sqlalchemy import Column, String, Integer, DateTime, Boolean
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    viewed = Column(Boolean, default=False)
    correct = Column(Boolean, default=False)
    last_reviewed = Column(DateTime, default=datetime.utcnow)
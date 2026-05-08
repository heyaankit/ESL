from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from datetime import datetime
from app.database import Base


class PrivacyPolicy(Base):
    """Privacy policy content."""
    __tablename__ = "privacy_policy"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    version = Column(String, default="1.0")
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FAQ(Base):
    """Frequently asked questions."""
    __tablename__ = "faq"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContactUs(Base):
    """Contact us messages from users."""
    __tablename__ = "contact_us"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String, default="open")  # open, in_progress, resolved, closed
    created_at = Column(DateTime, default=datetime.utcnow)


class UserSubscription(Base):
    """User subscription status."""
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=True)  # ios, android, web
    plan = Column(String, default="free")  # free, premium, pro
    status = Column(String, default="active")  # active, expired, cancelled
    expiry_date = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Content(Base):
    """Learning content helper table for /learning/* endpoints."""
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    training_type = Column(String, nullable=False)
    word_type = Column(String, nullable=True)
    key = Column(String, nullable=True)
    value = Column(Text, nullable=True)
    language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

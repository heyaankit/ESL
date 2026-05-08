from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float
from datetime import datetime, timedelta
from app.database import Base
import random


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    password_hash = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    country_code = Column(String, nullable=True)
    name = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)
    fcm_token = Column(String, nullable=True)
    social_provider = Column(String, nullable=True)  # "google" etc.
    social_id = Column(String, nullable=True)
    mother_language = Column(String, default="Mongolian")
    learning_level = Column(String, default="beginner")
    last_login = Column(DateTime, nullable=True)
    next_notification = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    otp_code = Column(String, nullable=True)
    otp_expires = Column(DateTime, nullable=True)

    def generate_otp(self):
        """Generate 6-digit OTP."""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires = datetime.utcnow() + timedelta(minutes=5)
        return self.otp_code

    def verify_otp(self, code: str) -> bool:
        """Verify OTP code."""
        if not self.otp_code or not self.otp_expires:
            return False
        if datetime.utcnow() > self.otp_expires:
            return False
        return self.otp_code == code


class OTPStore(Base):
    """Separate OTP store for password reset flow."""
    __tablename__ = "otp_store"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, nullable=False, index=True)  # email or phone
    otp_code = Column(String, nullable=False)
    purpose = Column(String, default="password_reset")  # password_reset, verification
    verified = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    viewed = Column(Boolean, default=False)
    correct = Column(Boolean, default=False)
    response = Column(Text, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    last_reviewed = Column(DateTime, default=datetime.utcnow)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True, unique=True)
    mode = Column(String, default="mixed")  # mixed, conversation, exercise
    topics = Column(Text, nullable=True)  # JSON list of preferred topics
    avatar = Column(String, nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    difficulty = Column(String, default="beginner")
    daily_goal_minutes = Column(Integer, default=15)
    updated_at = Column(DateTime, default=datetime.utcnow)

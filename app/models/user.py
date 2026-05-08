from sqlalchemy import Column, String, Integer, DateTime, Boolean
from datetime import datetime, timedelta
from app.database import Base
import random


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    password_hash = Column(String, nullable=False)
    gender = Column(String, nullable=False)
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


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    viewed = Column(Boolean, default=False)
    correct = Column(Boolean, default=False)
    last_reviewed = Column(DateTime, default=datetime.utcnow)
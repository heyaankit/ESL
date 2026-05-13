from datetime import datetime, timedelta
from typing import Optional
import random
from collections import defaultdict
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User

security = HTTPBearer()

# In-memory rate limiter for OTP requests
# Maps user_id -> list of request timestamps
_otp_request_log: dict[str, list[datetime]] = defaultdict(list)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user_id = int(user_id_str)
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def create_user(username: str, db: Session, gender: str, password: str = None, email: str = None) -> User:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    last_user = db.query(User).order_by(User.user_id.desc()).first()
    next_user_id = (last_user.user_id + 1) if last_user else 1
    pwd_hash = get_password_hash(password) if password else ""
    new_user = User(user_id=next_user_id, username=username, gender=gender, password_hash=pwd_hash, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def verify_user(username: str, password: str, db: Session) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def check_otp_rate_limit(user_id: str) -> None:
    """Check if user has exceeded OTP request rate limit.

    Raises HTTPException 429 if rate limit is exceeded.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=1)

    # Clean up old entries
    _otp_request_log[user_id] = [
        ts for ts in _otp_request_log[user_id] if ts > cutoff
    ]

    if len(_otp_request_log[user_id]) >= settings.otp_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many OTP requests. Maximum {settings.otp_rate_limit_per_minute} per minute."
        )

    # Record this request
    _otp_request_log[user_id].append(now)


def generate_otp_for_user(user: User, db: Session) -> str:
    user.otp_code = str(random.randint(100000, 999999))
    user.otp_expires = datetime.utcnow() + timedelta(minutes=5)
    db.commit()
    return user.otp_code


def verify_user_otp(username: str, otp_code: str, db: Session) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not user.otp_code or not user.otp_expires:
        return None
    if datetime.utcnow() > user.otp_expires:
        return None
    if user.otp_code != otp_code:
        return None
    user.otp_code = None
    user.otp_expires = None
    db.commit()
    return user

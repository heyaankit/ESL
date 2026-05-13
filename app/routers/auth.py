"""Auth router — complete rewrite matching Bestie Live API Handoff Document.

All endpoints return the legacy response format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Form, File, UploadFile, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, OTPStore, UserPreferences
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    OTPRequest,
    OTPVerify,
    ChangePasswordRequest,
    ResetPasswordRequest,
    SetPasswordRequest,
    SocialLoginRequest,
)
from app.auth import (
    create_access_token,
    create_user,
    verify_user,
    generate_otp_for_user,
    verify_user_otp,
    check_otp_rate_limit,
    get_password_hash,
    verify_password,
)
from app.services.email import send_otp_email
from app.services.social_auth import social_auth_service
from app.config import settings
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_to_dict(user: User) -> dict:
    """Serialise a User ORM object into a plain dict for the legacy response."""
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "country_code": user.country_code,
        "gender": user.gender,
        "profile_pic": user.profile_pic,
        "fcm_token": user.fcm_token,
        "social_provider": user.social_provider,
        "social_id": user.social_id,
        "mother_language": user.mother_language,
        "learning_level": user.learning_level,
        "last_login": str(user.last_login) if user.last_login else None,
        "next_notification": str(user.next_notification) if user.next_notification else None,
        "created_at": str(user.created_at) if user.created_at else None,
    }


def _ensure_uploads_dir() -> str:
    """Ensure the uploads directory exists and return its path."""
    upload_dir = os.path.join(os.getcwd(), settings.upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


# ---------------------------------------------------------------------------
# 1. POST /register
# ---------------------------------------------------------------------------

@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user. Generates and sends OTP if email is available."""
    # Check if user already exists
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        return error(message="User already exists. Please login.")

    # Create the user via auth helper (generates user_id, sets username, gender, password_hash, email)
    user = create_user(
        username=request.username,
        db=db,
        gender=request.gender,
        password=request.password,
        email=request.email,
    )

    # Set additional fields from RegisterRequest
    if request.phone:
        user.phone = request.phone
    if request.country_code:
        user.country_code = request.country_code
    if request.name:
        user.name = request.name
    if request.fcm_token:
        user.fcm_token = request.fcm_token
    db.commit()
    db.refresh(user)

    # Generate OTP
    otp = generate_otp_for_user(user, db)

    # Attempt to send OTP via email
    otp_sent = False
    if user.email:
        otp_sent = send_otp_email(user.email, otp, user.user_id)

    if not otp_sent:
        logger.info(f"[DEV] OTP for {request.username}: {otp}")

    return success(
        data={
            "user_id": user.user_id,
            "username": user.username,
            "gender": user.gender,
            "otp_sent": otp_sent,
        },
        message="Registration successful",
    )


# ---------------------------------------------------------------------------
# 2. POST /login
# ---------------------------------------------------------------------------

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate a user with username/password and return a JWT."""
    user = verify_user(request.username, request.password, db)
    if not user:
        return error(message="Invalid username or password")

    # Update last_login and next_notification
    user.last_login = datetime.utcnow()
    user.next_notification = datetime.utcnow() + timedelta(
        minutes=settings.notification_scheduler_interval_minutes
    )

    db.commit()
    db.refresh(user)

    # Create JWT
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=access_token_expires,
    )

    return success(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "gender": user.gender,
            "user_id": user.user_id,
        },
    )


# ---------------------------------------------------------------------------
# 3. POST /profile  (form-data: user_id)
# ---------------------------------------------------------------------------

@router.post("/profile")
def get_profile_form(
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Fetch user profile by user_id (form-data)."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return error(message="User not found")

    return success(data=_user_to_dict(user))


# ---------------------------------------------------------------------------
# 4. POST /update_profile  (form-data + optional file)
# ---------------------------------------------------------------------------

@router.post("/update_profile")
def update_profile(
    user_id: str = Form(...),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    mother_language: Optional[str] = Form(None),
    learning_level: Optional[str] = Form(None),
    profile_pic: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Update user profile fields and optionally upload a profile picture."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return error(message="User not found")

    # Update scalar fields only when provided
    if name is not None:
        user.name = name
    if email is not None:
        user.email = email
    if phone is not None:
        user.phone = phone
    if country_code is not None:
        user.country_code = country_code
    if gender is not None:
        user.gender = gender
    if mother_language is not None:
        user.mother_language = mother_language
    if learning_level is not None:
        user.learning_level = learning_level

    # Handle profile picture upload
    if profile_pic is not None and profile_pic.filename:
        upload_dir = _ensure_uploads_dir()
        # Generate unique filename to avoid collisions
        ext = os.path.splitext(profile_pic.filename)[1]
        unique_name = f"{user_id}_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, unique_name)

        contents = profile_pic.file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Store relative path in DB
        user.profile_pic = f"{settings.upload_dir}/{unique_name}"

    db.commit()
    db.refresh(user)

    return success(data=_user_to_dict(user), message="Profile updated successfully")


# ---------------------------------------------------------------------------
# 5. GET /get_profile  (query: user_id)
# ---------------------------------------------------------------------------

@router.get("/get_profile")
def get_profile_query(
    user_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """Fetch full user profile by user_id (query parameter)."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return error(message="User not found")

    return success(data=_user_to_dict(user))


# ---------------------------------------------------------------------------
# 6. DELETE /user/delete/{user_id}  (form-data: password)
# ---------------------------------------------------------------------------

@router.delete("/user/delete/{user_id}")
def delete_user(
    user_id: str,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Verify password then delete user and all related data."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return error(message="User not found")

    if not verify_password(password, user.password_hash):
        return error(message="Invalid password")

    # Delete related records
    db.query(UserPreferences).filter(UserPreferences.user_id == user_id).delete()
    # Delete user itself
    db.delete(user)
    db.commit()

    return success(message="User deleted successfully")


# ---------------------------------------------------------------------------
# 7. POST /change_password  (JSON: ChangePasswordRequest)
# ---------------------------------------------------------------------------

@router.post("/change_password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
):
    """Verify old password and set a new one."""
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        return error(message="User not found")

    if not verify_password(request.old_password, user.password_hash):
        return error(message="Invalid old password")

    user.password_hash = get_password_hash(request.new_password)
    db.commit()

    return success(message="Password changed successfully")


# ---------------------------------------------------------------------------
# 8. POST /reset-password  (JSON: ResetPasswordRequest)
# ---------------------------------------------------------------------------

@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Find user by email or phone, generate OTP stored in OTPStore, send via email."""
    # Try to find user by email first, then by phone
    user = (
        db.query(User).filter(User.email == request.identifier).first()
        or db.query(User).filter(User.phone == request.identifier).first()
    )

    if not user:
        return error(message="No account found with this email or phone")

    if not user.email:
        return error(message="User has no email on file; cannot send OTP")

    # Create OTP entry in OTPStore
    otp_code = str(random.randint(100000, 999999))
    otp_entry = OTPStore(
        identifier=request.identifier,
        otp_code=otp_code,
        purpose="password_reset",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(otp_entry)
    db.commit()
    db.refresh(otp_entry)

    # Send OTP via email
    otp_sent = send_otp_email(user.email, otp_code, user.user_id)
    if not otp_sent:
        logger.info(f"[DEV] Reset OTP for {request.identifier}: {otp_code}")

    return success(
        message="OTP sent to your email" if otp_sent else "OTP generated. Check server logs.",
    )


# ---------------------------------------------------------------------------
# 9. POST /verify-otp  (JSON: OTPVerify)
# ---------------------------------------------------------------------------

@router.post("/verify-otp")
def verify_otp(
    request: OTPVerify,
    db: Session = Depends(get_db),
):
    """Verify OTP for a user and return a JWT."""
    user = verify_user_otp(request.username, request.otp_code, db)
    if not user:
        return error(message="Invalid or expired OTP")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=access_token_expires,
    )

    return success(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "gender": user.gender,
            "user_id": user.user_id,
        },
        message="OTP verified successfully",
    )


# ---------------------------------------------------------------------------
# 10. POST /set-password  (JSON: SetPasswordRequest)
# ---------------------------------------------------------------------------

@router.post("/set-password")
def set_password(
    request: SetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Verify OTP from OTPStore, then set a new password for the user."""
    # Look up the most recent unverified OTP entry for this identifier
    otp_entry = (
        db.query(OTPStore)
        .filter(
            OTPStore.identifier == request.identifier,
            OTPStore.verified == False,  # noqa: E712
            OTPStore.purpose == "password_reset",
            OTPStore.expires_at > datetime.utcnow(),
        )
        .order_by(OTPStore.created_at.desc())
        .first()
    )

    if not otp_entry or otp_entry.otp_code != request.otp_code:
        return error(message="Invalid or expired OTP")

    # Mark OTP as verified
    otp_entry.verified = True

    # Find the user by email or phone
    user = (
        db.query(User).filter(User.email == request.identifier).first()
        or db.query(User).filter(User.phone == request.identifier).first()
    )

    if not user:
        return error(message="User not found")

    user.password_hash = get_password_hash(request.new_password)
    db.commit()

    return success(message="Password set successfully")


# ---------------------------------------------------------------------------
# 11. POST /social-login  (JSON: SocialLoginRequest)
# ---------------------------------------------------------------------------

@router.post("/social-login")
def social_login(
    request: SocialLoginRequest,
    db: Session = Depends(get_db),
):
    """Verify social token, find or create user, return JWT + user data."""
    # Verify the social token
    if request.provider == "google":
        social_info = social_auth_service.verify_google_token(request.token)
    else:
        return error(message=f"Unsupported social provider: {request.provider}")

    if not social_info:
        return error(message="Social authentication failed")

    social_id = social_info.get("social_id")
    social_email = social_info.get("email")
    social_name = social_info.get("name")
    social_picture = social_info.get("picture")

    # Find existing user by social_id
    user = db.query(User).filter(User.social_id == social_id).first()

    if not user:
        # Also check by email in case they previously registered manually
        if social_email:
            user = db.query(User).filter(User.email == social_email).first()

        if user:
            # Link the social account to the existing user
            user.social_provider = request.provider
            user.social_id = social_id
            if social_picture and not user.profile_pic:
                user.profile_pic = social_picture
        else:
            # Create a brand new user
            # Generate a unique user_id from social_id to avoid collisions
            generated_user_id = f"{request.provider}_{social_id}"
            # Ensure it's not too long
            if len(generated_user_id) > 100:
                generated_user_id = f"{request.provider}_{uuid.uuid4().hex[:12]}"

            user = User(
                user_id=generated_user_id,
                password_hash="",  # No password for social users
                gender="male",  # Default; can be updated later
                email=social_email,
                name=social_name,
                profile_pic=social_picture,
                social_provider=request.provider,
                social_id=social_id,
            )
            db.add(user)

    # Update fcm_token if provided
    if request.fcm_token:
        user.fcm_token = request.fcm_token

    db.commit()
    db.refresh(user)

    # Create JWT
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=access_token_expires,
    )

    return success(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "gender": user.gender,
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "profile_pic": user.profile_pic,
            "social_provider": user.social_provider,
            "is_new_user": user.created_at is not None
            and (datetime.utcnow() - user.created_at).total_seconds() < 5,
        },
        message="Social login successful",
    )


# ---------------------------------------------------------------------------
# 12. POST /request-otp  (JSON: OTPRequest)
# ---------------------------------------------------------------------------

@router.post("/request-otp")
def request_otp(
    request: OTPRequest,
    db: Session = Depends(get_db),
):
    """Generate and send OTP to an existing user (with rate limiting)."""
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        return error(message="User not found. Please register first.")

    # Apply rate limiting — raises HTTP 429 if exceeded
    check_otp_rate_limit(request.username)

    # Generate OTP
    otp = generate_otp_for_user(user, db)

    # Send OTP via email
    otp_sent = False
    if user.email:
        otp_sent = send_otp_email(user.email, otp, user.user_id)

    if not otp_sent:
        logger.info(f"[DEV] OTP for {request.username}: {otp}")

    return success(
        message="OTP sent to your email" if otp_sent else "OTP generated. Check server logs.",
    )

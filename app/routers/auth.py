from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    Token, LoginRequest, RegisterRequest, 
    OTPRequest, OTPVerify, LoginResponse
)
from app.auth import (
    create_access_token, create_user, verify_user,
    generate_otp_for_user, verify_user_otp
)
from app.config import settings

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=LoginResponse)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.user_id == request.username).first()
    if existing:
        return LoginResponse(success=False, message="User already exists. Please login.")
    
    user = create_user(request.username, db, request.gender, request.password)
    
    otp = generate_otp_for_user(user, db)
    print(f"OTP for {request.username}: {otp}")
    
    return LoginResponse(
        success=True,
        message="Registration successful. Check server console for OTP.",
        user_id=user.user_id,
        username=user.user_id,
        gender=user.gender
    )


@router.post("/request-otp", response_model=LoginResponse)
def request_otp(
    request: OTPRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == request.username).first()
    if not user:
        return LoginResponse(success=False, message="User not found. Please register first.")
    
    otp = generate_otp_for_user(user, db)
    print(f"OTP for {request.username}: {otp}")
    
    return LoginResponse(
        success=True,
        message="New OTP sent. Check server console.",
        user_id=user.user_id,
        username=user.user_id,
        gender=user.gender
    )


@router.post("/verify-otp", response_model=Token)
def verify_otp(
    request: OTPVerify,
    db: Session = Depends(get_db)
):
    user = verify_user_otp(request.username, request.otp_code, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.user_id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "gender": user.gender}


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    user = verify_user(request.username, request.password, db)
    if not user:
        return LoginResponse(success=False, message="Invalid username or password")
    
    return LoginResponse(
        success=True,
        message="Login successful",
        user_id=user.user_id,
        username=user.user_id,
        gender=user.gender
    )
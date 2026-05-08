from pydantic import BaseModel, Field
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str
    gender: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    gender: str = Field(..., pattern="^(male|female)$")
    email: Optional[str] = None
    phone: Optional[str] = None
    country_code: Optional[str] = None
    name: Optional[str] = None
    fcm_token: Optional[str] = None


class OTPRequest(BaseModel):
    username: str = Field(..., min_length=1)


class OTPVerify(BaseModel):
    username: str = Field(..., min_length=1)
    otp_code: str = Field(..., min_length=6, max_length=6)


class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    gender: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)


class ResetPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=1)  # email or phone


class SetPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=1)
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=1)


class SocialLoginRequest(BaseModel):
    token: str = Field(..., min_length=1)
    provider: str = Field(default="google")
    fcm_token: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country_code: Optional[str] = None
    gender: Optional[str] = None
    mother_language: Optional[str] = None
    learning_level: Optional[str] = None

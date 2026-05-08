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
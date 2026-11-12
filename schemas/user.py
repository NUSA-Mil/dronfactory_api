import re
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field, field_validator
from schemas.common import BaseSchema, sanitize_xss
from schemas.role import RoleResponse

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 32


def validate_password_complexity(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Пароль должен быть длиной от {PASSWORD_MIN_LENGTH} до {PASSWORD_MAX_LENGTH} символов")

    if not re.search(r"[A-ZА-ЯЁ]", password):
        raise ValueError("Пароль должен содержать хотя бы одну заглавную букву (латиницей или кириллицей)")

    if not re.search(r"[a-zа-яё]", password):
        raise ValueError("Пароль должен содержать хотя бы одну строчную букву (латиницей или кириллицей)")

    if not re.search(r"\d", password):
        raise ValueError("Пароль должен содержать хотя бы одну цифру")

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/\\]", password):
        raise ValueError("Пароль должен содержать хотя бы один специальный символ (!@#$%^&*... и т.д.)")

    return password


class UserAddressCreate(BaseSchema):
    title: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    address_line: str = Field(..., min_length=5, max_length=255)
    comment: Optional[str] = Field(None, max_length=500)
    is_default: bool = False

    @field_validator("title", "city", "address_line", "comment", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class UserAddressResponse(UserAddressCreate):
    address_id: int
    user_id: int
    created_at: datetime


class UserCreate(BaseSchema):
    email: EmailStr
    password: str
    phone_number: Optional[str] = Field(None, max_length=30)
    full_name: Optional[str] = Field(None, max_length=200)
    role_id: Optional[int] = Field(1, description="ID роли (1 - Client, 4 - Admin)")

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_complexity(v)

    @field_validator("full_name", "phone_number", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=30)
    full_name: Optional[str] = Field(None, max_length=200)
    avatar_url: Optional[str] = None
    language: Optional[str] = Field(None, max_length=10)
    theme_mode: Optional[str] = Field(None, max_length=10)

    @field_validator("full_name", "phone_number", "language", "theme_mode", "avatar_url", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class UserChangePassword(BaseSchema):
    current_password: str = Field(..., min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class UserResponse(BaseSchema):
    user_id: int
    email: EmailStr
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role_id: int
    role: Optional[RoleResponse] = None
    is_active: bool
    is_verified: bool
    language: str
    theme_mode: str
    created_at: datetime

class OTPRequest(BaseSchema):
    email: EmailStr

class VerifyRegistrationRequest(BaseSchema):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseSchema):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_complexity(v)
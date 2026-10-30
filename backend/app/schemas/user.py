from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.roles import UserRole


class UserBase(BaseModel):
    full_name: str
    email: str = Field(..., min_length=3, max_length=255)
    username: Optional[str] = None
    is_active: bool = True

    @field_validator("username", mode="before")
    @classmethod
    def empty_username_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v


class UserCreate(UserBase):
    password: str = Field(min_length=8)
    role: UserRole

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip().upper()
        return v


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

    @field_validator("username", mode="before")
    @classmethod
    def empty_username_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("password", mode="before")
    @classmethod
    def empty_password_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip().upper()
        return v


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    created_at: datetime
    updated_at: datetime
    roles: list[RoleOut] = []


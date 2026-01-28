"""
用户相关的Pydantic数据模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """用户注册请求"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    department: Optional[str] = None


class UserLogin(BaseModel):
    """用户登录请求"""

    username: str
    password: str


class UserResponse(BaseModel):
    """用户信息响应"""

    id: str
    username: str
    email: str
    full_name: Optional[str]
    department: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """令牌响应"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

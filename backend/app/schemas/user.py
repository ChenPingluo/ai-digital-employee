# -*- coding: utf-8 -*-
"""
用户相关的 Pydantic 数据模式

定义用户注册、登录、响应和令牌等数据验证模式。
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    """
    用户注册请求模式
    
    用于验证用户注册时提交的数据。
    
    Attributes:
        username: 用户名，3-50个字符
        email: 电子邮箱，必须符合邮箱格式
        password: 密码，至少6个字符
        department: 部门名称，可选
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名，3-50个字符",
        examples=["zhangsan"]
    )
    email: EmailStr = Field(
        ...,
        description="用户电子邮箱",
        examples=["zhangsan@example.com"]
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="用户密码，至少6个字符",
        examples=["password123"]
    )
    department: Optional[str] = Field(
        None,
        max_length=100,
        description="用户所属部门",
        examples=["技术部"]
    )


class UserLogin(BaseModel):
    """
    用户登录请求模式
    
    用于验证用户登录时提交的凭据。
    
    Attributes:
        username: 用户名或邮箱
        password: 用户密码
    """
    username: str = Field(
        ...,
        description="用户名或邮箱",
        examples=["zhangsan"]
    )
    password: str = Field(
        ...,
        description="用户密码",
        examples=["password123"]
    )


class UserResponse(BaseModel):
    """
    用户信息响应模式
    
    用于返回用户信息给前端，不包含敏感信息（如密码）。
    
    Attributes:
        id: 用户唯一标识符
        username: 用户名
        email: 电子邮箱
        department: 部门名称
        role: 用户角色
        is_active: 账户是否激活
        created_at: 账户创建时间
        updated_at: 账户最后更新时间
    """
    # 配置：允许从 ORM 模型创建
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(
        ...,
        description="用户唯一标识符"
    )
    username: str = Field(
        ...,
        description="用户名"
    )
    email: str = Field(
        ...,
        description="用户电子邮箱"
    )
    department: Optional[str] = Field(
        None,
        description="用户所属部门"
    )
    role: str = Field(
        default="user",
        description="用户角色：user/admin/manager"
    )
    is_active: bool = Field(
        default=True,
        description="账户是否激活"
    )
    created_at: datetime = Field(
        ...,
        description="账户创建时间"
    )
    updated_at: datetime = Field(
        ...,
        description="账户最后更新时间"
    )


class Token(BaseModel):
    """
    JWT 令牌响应模式
    
    用于返回登录成功后的访问令牌。
    
    Attributes:
        access_token: JWT 访问令牌
        token_type: 令牌类型，固定为 "bearer"
        user: 当前登录用户信息
    """
    access_token: str = Field(
        ...,
        description="JWT 访问令牌"
    )
    token_type: str = Field(
        default="bearer",
        description="令牌类型"
    )
    user: UserResponse = Field(
        ...,
        description="当前登录用户信息"
    )


class TokenData(BaseModel):
    """
    JWT 令牌载荷数据模式
    
    用于解析 JWT 令牌中的用户信息。
    
    Attributes:
        user_id: 用户 ID
        username: 用户名
    """
    user_id: Optional[uuid.UUID] = Field(
        None,
        description="用户 ID"
    )
    username: Optional[str] = Field(
        None,
        description="用户名"
    )

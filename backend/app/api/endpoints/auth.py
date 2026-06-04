# -*- coding: utf-8 -*-
"""
认证接口模块

提供用户注册、登录和身份验证相关的 API 端点。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.middleware.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from app.middleware.rate_limiter import auth_limiter, check_rate_limit


# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户账户，用户名和邮箱必须唯一"
)
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册接口
    
    - **username**: 用户名
    - **email**: 电子邮箱
    - **password**: 密码
    - **department**: 部门名称
    """
    # 检查限流
    await check_rate_limit(
        request,
        limiter=auth_limiter,
        error_message="注册请求过于频繁，请稍后再试"
    )
    
    try:
        # 检查用户名是否已存在
        existing_user = await db.execute(
            select(User).where(
                or_(
                    User.username == user_data.username,
                    User.email == user_data.email
                )
            )
        )
        
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名或邮箱已被注册"
            )
        
        # 创建新用户
        hashed_password = get_password_hash(user_data.password)
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            department=user_data.department
        )
        
        db.add(new_user)
        await db.flush()
        await db.refresh(new_user)
        
        return new_user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    description="使用用户名/邮箱和密码登录，返回 JWT Token"
)
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录接口
    
    - username: 用户名或邮箱
    - password: 用户密码
    
    返回 JWT 访问令牌和用户信息
    """
    # 检查限流
    await check_rate_limit(
        request,
        limiter=auth_limiter,
        error_message="登录尝试过于频繁，请稍后再试"
    )
    
    try:
        # 查询用户
        result = await db.execute(
            select(User).where(
                or_(
                    User.username == credentials.username,
                    User.email == credentials.username
                )
            )
        )
        
        user = result.scalar_one_or_none()
        
        # 验证用户存在且密码正确
        if user is None or not verify_password(
            credentials.password,
            user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 检查用户是否激活
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用，请联系管理员"
            )
        
        # 创建访问令牌
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username
            }
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="获取当前已认证用户的详细信息"
)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息接口
    
    需要在请求头中携带有效的 Bearer Token
    
    Returns:
        当前用户的详细信息
    """
    return current_user


@router.post(
    "/refresh",
    response_model=Token,
    summary="刷新 Token",
    description="使用当前有效的 Token 获取新的访问令牌"
)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    刷新访问令牌接口
    
    在 Token 即将过期时调用，获取新的访问令牌。
    需要在请求头中携带当前有效的 Bearer Token。
    """
    try:
        # 创建新的访问令牌
        access_token = create_access_token(
            data={
                "sub": str(current_user.id),
                "username": current_user.username
            }
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(current_user)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刷新令牌失败: {str(e)}"
        )


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="修改密码",
    description="修改当前用户的登录密码"
)
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改密码接口
    
    - **old_password**: 当前密码
    - **new_password**: 新密码
    """
    try:
        # 验证旧密码
        if not verify_password(old_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )
        
        # 验证新密码长度
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新密码长度不能少于6个字符"
            )
        
        # 更新密码
        current_user.hashed_password = get_password_hash(new_password)
        await db.flush()
        
        return {"message": "密码修改成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改密码失败: {str(e)}"
        )

# -*- coding: utf-8 -*-
"""
JWT 认证中间件模块

提供 JWT Token 的创建、验证和用户身份提取功能。
用于保护需要认证的 API 端点。
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.user import TokenData


# ==================== 密码加密上下文 ====================
# 使用 bcrypt 算法进行密码哈希，自动处理盐值
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==================== Bearer Token 认证方案 ====================
# 用于从请求头中提取 Bearer Token
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    
    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的哈希密码
        
    Returns:
        bool: 密码匹配返回 True，否则返回 False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    将明文密码转换为 bcrypt 哈希值
    
    Args:
        password: 用户输入的明文密码
        
    Returns:
        str: bcrypt 加密后的密码哈希值
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT 访问令牌
    
    Args:
        data: 要编码到令牌中的数据（通常包含 user_id 和 username）
        expires_delta: 令牌过期时间，默认使用配置中的过期时间
        
    Returns:
        str: 编码后的 JWT 令牌字符串
    """
    # 复制数据，避免修改原始字典
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # 添加过期时间到令牌载荷
    to_encode.update({"exp": expire})
    
    # 使用配置的密钥和算法编码令牌
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    解码并验证 JWT 访问令牌
    
    Args:
        token: JWT 令牌字符串
        
    Returns:
        TokenData: 解码后的令牌数据，解码失败返回 None
    """
    try:
        # 解码令牌
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # 提取用户信息
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        
        if user_id is None:
            return None
            
        return TokenData(
            user_id=uuid.UUID(user_id),
            username=username
        )
        
    except JWTError:
        # JWT 解码或验证失败
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前认证用户（FastAPI 依赖注入）
    
    从请求头中提取 Bearer Token，验证并返回对应的用户对象。
    用于保护需要认证的 API 端点。
    
    Args:
        credentials: HTTP Bearer 认证凭据
        db: 数据库会话
        
    Returns:
        User: 当前认证的用户对象
        
    Raises:
        HTTPException: 认证失败时抛出 401 错误
    """
    # 定义认证失败异常
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 解码令牌
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    if token_data is None:
        raise credentials_exception
    
    # 查询用户
    try:
        result = await db.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise credentials_exception
            
        # 检查用户是否激活
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账户已被禁用"
            )
            
        return user
        
    except Exception as e:
        # 数据库查询异常
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户（确保用户已激活）
    
    Args:
        current_user: 当前认证的用户
        
    Returns:
        User: 当前活跃的用户对象
        
    Raises:
        HTTPException: 用户未激活时抛出 400 错误
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户未激活"
        )
    return current_user

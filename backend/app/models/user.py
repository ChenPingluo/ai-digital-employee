# -*- coding: utf-8 -*-
"""
用户模型模块

定义 User ORM 模型，映射数据库中的 users 表。
包含用户认证、角色权限和组织关系等字段。
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 类型检查时导入，避免循环导入
if TYPE_CHECKING:
    from app.models.todo import Todo
    from app.models.reservation import Reservation


class User(Base):
    """
    用户模型
    
    映射 users 表，存储系统用户的基本信息和认证凭据。
    支持与待办事项和会议室预约的一对多关系。
    
    Attributes:
        id: 用户唯一标识符，UUID 格式
        username: 用户登录名，系统内唯一
        email: 用户电子邮箱
        hashed_password: bcrypt 加密的密码
        department: 用户所属部门
        role: 用户角色 (user/admin/manager)
        is_active: 账户是否激活
        created_at: 账户创建时间
        updated_at: 账户最后更新时间
        todos: 用户的待办事项列表
        reservations: 用户的会议室预约列表
    """
    
    # 表名
    __tablename__ = "users"
    
    # ==================== 主键字段 ====================
    # 使用 UUID 作为主键，自动生成
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="用户唯一标识符"
    )
    
    # ==================== 认证字段 ====================
    # 用户名：唯一、非空，最大50字符
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户登录名"
    )
    
    # 电子邮箱：唯一、非空，最大100字符
    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="用户电子邮箱"
    )
    
    # 哈希密码：非空，最大255字符
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt加密的用户密码"
    )
    
    # ==================== 组织字段 ====================
    # 部门：可选，最大100字符
    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="用户所属部门"
    )
    
    # 角色：默认为普通用户
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        comment="用户角色：user/admin/manager"
    )
    
    # ==================== 状态字段 ====================
    # 账户激活状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="账户是否激活"
    )
    
    # ==================== 时间戳字段 ====================
    # 创建时间：自动设置为当前时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="账户创建时间"
    )
    
    # 更新时间：自动更新为当前时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="账户最后更新时间"
    )
    
    # ==================== 关系定义 ====================
    # 与待办事项的一对多关系
    # back_populates 建立双向关系
    # cascade 设置级联删除
    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # 与会议室预约的一对多关系
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        """返回用户的字符串表示"""
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

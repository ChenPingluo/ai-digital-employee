# -*- coding: utf-8 -*-
"""
待办事项模型模块

定义 Todo ORM 模型，映射数据库中的 todos 表。
支持任务优先级、状态管理和截止日期等功能。
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, SmallInteger, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 类型检查时导入，避免循环导入
if TYPE_CHECKING:
    from app.models.user import User


class Todo(Base):
    """
    待办事项模型
    
    映射 todos 表，存储用户的任务列表。
    支持优先级（0-3）、状态管理和截止日期。
    
    Attributes:
        id: 任务唯一标识符，UUID 格式
        user_id: 任务所属用户 ID
        title: 任务标题
        description: 任务详细描述
        priority: 任务优先级 (0-低, 1-中, 2-高, 3-紧急)
        status: 任务状态 (pending/in_progress/completed/cancelled)
        due_date: 任务截止日期
        created_at: 任务创建时间
        updated_at: 任务最后更新时间
        user: 关联的用户对象
    """
    
    # 表名
    __tablename__ = "todos"
    
    # 表级约束
    __table_args__ = (
        # 优先级范围检查约束
        CheckConstraint(
            "priority >= 0 AND priority <= 3",
            name="chk_todo_priority"
        ),
    )
    
    # ==================== 主键字段 ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="任务唯一标识符"
    )
    
    # ==================== 外键字段 ====================
    # 关联用户表，级联删除
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="任务所属用户ID"
    )
    
    # ==================== 任务内容字段 ====================
    # 任务标题：非空，最大200字符
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="任务标题"
    )
    
    # 任务描述：可选，长文本
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="任务详细描述"
    )
    
    # ==================== 任务属性字段 ====================
    # 优先级：0-低，1-中，2-高，3-紧急
    priority: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        comment="任务优先级：0-低，1-中，2-高，3-紧急"
    )
    
    # 任务状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="任务状态：pending/in_progress/completed/cancelled"
    )
    
    # 截止日期：可选
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="任务截止日期"
    )
    
    # ==================== 时间戳字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="任务创建时间"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="任务最后更新时间"
    )
    
    # ==================== 关系定义 ====================
    # 与用户的多对一关系
    user: Mapped["User"] = relationship(
        "User",
        back_populates="todos",
        lazy="noload"
    )
    
    def __repr__(self) -> str:
        """返回待办事项的字符串表示"""
        return f"<Todo(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def priority_label(self) -> str:
        """
        获取优先级的文字标签
        
        Returns:
            str: 优先级对应的中文标签
        """
        labels = {0: "低", 1: "中", 2: "高", 3: "紧急"}
        return labels.get(self.priority, "未知")
    
    @property
    def is_overdue(self) -> bool:
        """
        检查任务是否已逾期
        
        Returns:
            bool: 如果任务有截止日期且已过期，返回 True
        """
        if self.due_date is None:
            return False
        return datetime.now(self.due_date.tzinfo) > self.due_date

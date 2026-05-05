# -*- coding: utf-8 -*-
"""
会话与聊天消息模型模块

定义 Conversation 和 ChatMessageRecord ORM 模型，
映射数据库中的 conversations 和 chat_messages 表。
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 类型检查时导入，避免循环导入
if TYPE_CHECKING:
    from app.models.user import User


class Conversation(Base):
    """
    会话模型
    
    映射 conversations 表，存储用户的聊天会话。
    支持与聊天消息的一对多关系。
    
    Attributes:
        id: 会话唯一标识符，UUID 格式
        user_id: 会话所属用户 ID
        title: 会话标题
        created_at: 会话创建时间
        updated_at: 会话最后更新时间
        messages: 会话中的消息列表
        user: 关联的用户对象
    """
    
    # 表名
    __tablename__ = "conversations"
    
    # ==================== 主键字段 ====================
    # 使用 UUID 作为主键，自动生成
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="会话唯一标识符"
    )
    
    # ==================== 外键字段 ====================
    # 关联用户表，级联删除
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话所属用户ID"
    )
    
    # ==================== 会话内容字段 ====================
    # 会话标题：可选，最大200字符
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="会话标题"
    )
    
    # ==================== 时间戳字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="会话创建时间"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="会话最后更新时间"
    )
    
    # ==================== 关系定义 ====================
    # 与聊天消息的一对多关系
    messages: Mapped[List["ChatMessageRecord"]] = relationship(
        "ChatMessageRecord",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # 与用户的多对一关系
    user: Mapped["User"] = relationship(
        "User",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        """返回会话的字符串表示"""
        return f"<Conversation(id={self.id}, title={self.title})>"


class ChatMessageRecord(Base):
    """
    聊天消息记录模型
    
    映射 chat_messages 表，存储会话中的聊天消息。
    
    Attributes:
        id: 消息唯一标识符，UUID 格式
        conversation_id: 消息所属会话 ID
        role: 消息角色 (user/assistant/system)
        content: 消息内容
        created_at: 消息创建时间
        conversation: 关联的会话对象
    """
    
    # 表名
    __tablename__ = "chat_messages"
    
    # ==================== 主键字段 ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="消息唯一标识符"
    )
    
    # ==================== 外键字段 ====================
    # 关联会话表，级联删除
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="消息所属会话ID"
    )
    
    # ==================== 消息内容字段 ====================
    # 消息角色：user/assistant/system
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="消息角色：user/assistant/system"
    )
    
    # 消息内容：长文本
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容"
    )
    
    # ==================== 时间戳字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="消息创建时间"
    )
    
    # ==================== 关系定义 ====================
    # 与会话的多对一关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )
    
    def __repr__(self) -> str:
        """返回聊天消息的字符串表示"""
        return f"<ChatMessageRecord(id={self.id}, role={self.role})>"

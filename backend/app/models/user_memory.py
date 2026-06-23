# -*- coding: utf-8 -*-
"""
用户记忆模型模块

存储 AI 从对话中自动提取的用户长期记忆。
支持多种记忆类型：事实、偏好、事件、人物关系等。
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Float, Integer, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserMemory(Base):
    """
    用户长期记忆模型

    自动从对话中提取关键信息并持久化存储。
    支持记忆重要性评分、访问频率统计和自动过期。

    Attributes:
        id: 记忆唯一标识符
        user_id: 所属用户 ID
        memory_type: 记忆类型 (fact/preference/event/person/context)
        category: 分类标签 (work/tech/health/life/learning)
        content: 记忆内容（简洁陈述）
        source_conversation_id: 来源会话 ID
        importance: 重要性评分 (1-10)
        confidence: 置信度 (0-1)
        access_count: 访问次数
        last_accessed: 最后访问时间
        is_active: 是否活跃
        created_at / updated_at: 时间戳
    """

    __tablename__ = "user_memories"

    # ── 主键 ──
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="记忆唯一标识符"
    )

    # ── 用户关联 ──
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户ID"
    )

    # ── 记忆元数据 ──
    memory_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="fact",
        comment="记忆类型: fact/preference/event/person/context"
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="分类标签: work/tech/health/life/learning"
    )

    # ── 核心内容 ──
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="记忆内容（简洁陈述句）"
    )

    # 原始对话上下文
    context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="提取该记忆时的原始对话上下文"
    )

    source_conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="来源会话ID"
    )

    # ── 质量评分 ──
    importance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="重要性评分 (1-10)"
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.8,
        comment="置信度 (0.0-1.0)"
    )

    # ── 访问统计 ──
    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="访问次数"
    )

    last_accessed: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后访问时间"
    )

    # ── 状态 ──
    is_active: Mapped[bool] = mapped_column(
        default=True,
        comment="是否活跃（软删除标记）"
    )

    # ── 时间戳 ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

    # ── 复合索引 ──
    __table_args__ = (
        Index("idx_user_memories_user_type", "user_id", "memory_type"),
        Index("idx_user_memories_user_active", "user_id", "is_active"),
        Index("idx_user_memories_importance", "user_id", "importance"),
    )

    def __repr__(self) -> str:
        return f"<UserMemory(id={self.id}, type={self.memory_type}, content='{self.content[:50]}...')>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "memory_type": self.memory_type,
            "category": self.category,
            "content": self.content,
            "importance": self.importance,
            "confidence": self.confidence,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

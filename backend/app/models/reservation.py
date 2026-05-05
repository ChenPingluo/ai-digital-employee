# -*- coding: utf-8 -*-
"""
会议室预约模型模块

定义 Reservation ORM 模型，映射数据库中的 reservations 表。
支持时间冲突检测和预约状态管理。
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 类型检查时导入，避免循环导入
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.meeting_room import MeetingRoom


class Reservation(Base):
    """
    会议室预约模型
    
    映射 reservations 表，存储会议室预约记录。
    通过数据库级别的 EXCLUDE 约束防止时间冲突。
    
    Attributes:
        id: 预约唯一标识符，UUID 格式
        room_id: 预约的会议室 ID
        user_id: 预约人用户 ID
        title: 会议主题
        start_time: 会议开始时间
        end_time: 会议结束时间
        status: 预约状态 (confirmed/cancelled/completed)
        created_at: 预约创建时间
        updated_at: 预约最后更新时间
        room: 关联的会议室对象
        user: 关联的用户对象
    """
    
    # 表名
    __tablename__ = "reservations"
    
    # 表级约束
    __table_args__ = (
        # 时间有效性检查：结束时间必须晚于开始时间
        CheckConstraint(
            "end_time > start_time",
            name="chk_reservation_time"
        ),
        # 注意：EXCLUDE 约束在数据库级别定义（init.sql 中）
        # SQLAlchemy 不直接支持 EXCLUDE 约束的声明式定义
    )
    
    # ==================== 主键字段 ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="预约唯一标识符"
    )
    
    # ==================== 外键字段 ====================
    # 关联会议室表
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meeting_rooms.id", ondelete="CASCADE"),
        nullable=False,
        comment="预约的会议室ID"
    )
    
    # 关联用户表
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="预约人用户ID"
    )
    
    # ==================== 会议信息字段 ====================
    # 会议标题
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="会议主题"
    )
    
    # 会议开始时间
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="会议开始时间"
    )
    
    # 会议结束时间
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="会议结束时间"
    )
    
    # ==================== 状态字段 ====================
    # 预约状态：confirmed（已确认）, cancelled（已取消）, completed（已完成）
    status: Mapped[str] = mapped_column(
        String(20),
        default="confirmed",
        index=True,
        comment="预约状态：confirmed/cancelled/completed"
    )
    
    # ==================== 时间戳字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="预约创建时间"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="预约最后更新时间"
    )
    
    # ==================== 关系定义 ====================
    # 与会议室的多对一关系
    room: Mapped["MeetingRoom"] = relationship(
        "MeetingRoom",
        back_populates="reservations",
        lazy="noload"
    )
    
    # 与用户的多对一关系
    user: Mapped["User"] = relationship(
        "User",
        back_populates="reservations",
        lazy="noload"
    )
    
    def __repr__(self) -> str:
        """返回预约的字符串表示"""
        return f"<Reservation(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def duration_minutes(self) -> int:
        """
        计算会议时长（分钟）
        
        Returns:
            int: 会议持续时间（分钟）
        """
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
    
    @property
    def duration_display(self) -> str:
        """
        获取会议时长的友好显示格式
        
        Returns:
            str: 格式化的时长字符串，如"1小时30分钟"
        """
        minutes = self.duration_minutes
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if hours > 0 and remaining_minutes > 0:
            return f"{hours}小时{remaining_minutes}分钟"
        elif hours > 0:
            return f"{hours}小时"
        else:
            return f"{remaining_minutes}分钟"
    
    @property
    def is_upcoming(self) -> bool:
        """
        检查会议是否尚未开始
        
        Returns:
            bool: 如果会议尚未开始返回 True
        """
        return datetime.now(self.start_time.tzinfo) < self.start_time
    
    @property
    def is_ongoing(self) -> bool:
        """
        检查会议是否正在进行中
        
        Returns:
            bool: 如果会议正在进行中返回 True
        """
        now = datetime.now(self.start_time.tzinfo)
        return self.start_time <= now < self.end_time
    
    @property
    def is_past(self) -> bool:
        """
        检查会议是否已结束
        
        Returns:
            bool: 如果会议已结束返回 True
        """
        return datetime.now(self.end_time.tzinfo) >= self.end_time

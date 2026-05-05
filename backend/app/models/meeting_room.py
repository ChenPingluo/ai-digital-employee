# -*- coding: utf-8 -*-
"""
会议室模型模块

定义 MeetingRoom ORM 模型，映射数据库中的 meeting_rooms 表。
包含会议室的基本信息、设备配置和可用状态。
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 类型检查时导入，避免循环导入
if TYPE_CHECKING:
    from app.models.reservation import Reservation


class MeetingRoom(Base):
    """
    会议室模型
    
    映射 meeting_rooms 表，存储会议室资源信息。
    包含位置、容量、设备等详细配置。
    
    Attributes:
        id: 会议室唯一标识符，UUID 格式
        name: 会议室名称，如"A栋301会议室"
        location: 会议室位置描述
        capacity: 会议室最大容纳人数
        equipment: 会议室设备列表
        is_available: 会议室是否可预约
        created_at: 记录创建时间
        updated_at: 记录最后更新时间
        reservations: 会议室的预约列表
    """
    
    # 表名
    __tablename__ = "meeting_rooms"
    
    # ==================== 主键字段 ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="会议室唯一标识符"
    )
    
    # ==================== 基本信息字段 ====================
    # 会议室名称：唯一、非空
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="会议室名称"
    )
    
    # 会议室位置：可选
    location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="会议室位置描述"
    )
    
    # 容纳人数：非空
    capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="会议室最大容纳人数"
    )
    
    # ==================== 设备配置字段 ====================
    # 设备列表：使用 PostgreSQL 数组类型
    # 存储如：["投影仪", "白板", "视频会议设备"]
    equipment: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="会议室设备列表"
    )
    
    # ==================== 状态字段 ====================
    # 可用状态：是否可预约
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        comment="会议室是否可预约"
    )
    
    # ==================== 时间戳字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="记录创建时间"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="记录最后更新时间"
    )
    
    # ==================== 关系定义 ====================
    # 与预约的一对多关系
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="room",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    
    def __repr__(self) -> str:
        """返回会议室的字符串表示"""
        return f"<MeetingRoom(id={self.id}, name={self.name}, capacity={self.capacity})>"
    
    @property
    def equipment_display(self) -> str:
        """
        获取设备列表的展示字符串
        
        Returns:
            str: 设备名称以逗号分隔的字符串
        """
        if not self.equipment:
            return "无"
        return ", ".join(self.equipment)
    
    def has_equipment(self, equipment_name: str) -> bool:
        """
        检查会议室是否配备指定设备
        
        Args:
            equipment_name: 设备名称
            
        Returns:
            bool: 如果会议室配备该设备返回 True
        """
        if not self.equipment:
            return False
        return equipment_name in self.equipment

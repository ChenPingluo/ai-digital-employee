# -*- coding: utf-8 -*-
"""
会议室和预约相关的 Pydantic 数据模式

定义会议室信息、预约创建和响应等数据验证模式。
"""

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class MeetingRoomResponse(BaseModel):
    """
    会议室信息响应模式
    
    用于返回会议室信息给前端。
    
    Attributes:
        id: 会议室唯一标识符
        name: 会议室名称
        location: 会议室位置
        capacity: 最大容纳人数
        equipment: 设备列表
        is_available: 是否可预约
        created_at: 创建时间
        updated_at: 更新时间
    """
    # 配置：允许从 ORM 模型创建
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(
        ...,
        description="会议室唯一标识符"
    )
    name: str = Field(
        ...,
        description="会议室名称"
    )
    location: Optional[str] = Field(
        None,
        description="会议室位置描述"
    )
    capacity: int = Field(
        ...,
        description="会议室最大容纳人数"
    )
    equipment: Optional[List[str]] = Field(
        None,
        description="会议室设备列表"
    )
    is_available: bool = Field(
        default=True,
        description="会议室是否可预约"
    )
    created_at: datetime = Field(
        ...,
        description="记录创建时间"
    )
    updated_at: datetime = Field(
        ...,
        description="记录最后更新时间"
    )
    
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


class ReservationCreate(BaseModel):
    """
    会议室预约创建请求模式
    
    用于验证创建预约时提交的数据。
    
    Attributes:
        room_id: 要预约的会议室 ID
        title: 会议主题
        start_time: 会议开始时间
        end_time: 会议结束时间
    """
    room_id: uuid.UUID = Field(
        ...,
        description="要预约的会议室 ID"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="会议主题",
        examples=["项目周会"]
    )
    start_time: datetime = Field(
        ...,
        description="会议开始时间",
        examples=["2024-12-30T10:00:00+08:00"]
    )
    end_time: datetime = Field(
        ...,
        description="会议结束时间",
        examples=["2024-12-30T11:00:00+08:00"]
    )
    
    @model_validator(mode="after")
    def validate_time_range(self) -> "ReservationCreate":
        """
        验证时间范围
        
        确保结束时间晚于开始时间，且时长合理。
        """
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        
        # 检查会议时长（例如：不超过8小时）
        duration = (self.end_time - self.start_time).total_seconds() / 3600
        if duration > 8:
            raise ValueError("会议时长不能超过8小时")
        
        # 检查会议时长（例如：至少15分钟）
        if duration < 0.25:
            raise ValueError("会议时长不能少于15分钟")
        
        return self


class ReservationResponse(BaseModel):
    """
    会议室预约响应模式
    
    用于返回预约信息给前端。
    
    Attributes:
        id: 预约唯一标识符
        room_id: 会议室 ID
        user_id: 预约人 ID
        title: 会议主题
        start_time: 开始时间
        end_time: 结束时间
        status: 预约状态
        created_at: 创建时间
        updated_at: 更新时间
        room: 会议室信息（可选，嵌套返回）
    """
    # 配置：允许从 ORM 模型创建
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(
        ...,
        description="预约唯一标识符"
    )
    room_id: uuid.UUID = Field(
        ...,
        description="会议室 ID"
    )
    user_id: uuid.UUID = Field(
        ...,
        description="预约人 ID"
    )
    title: str = Field(
        ...,
        description="会议主题"
    )
    start_time: datetime = Field(
        ...,
        description="会议开始时间"
    )
    end_time: datetime = Field(
        ...,
        description="会议结束时间"
    )
    status: str = Field(
        ...,
        description="预约状态：confirmed/cancelled/completed"
    )
    created_at: datetime = Field(
        ...,
        description="预约创建时间"
    )
    updated_at: datetime = Field(
        ...,
        description="预约最后更新时间"
    )
    room: Optional[MeetingRoomResponse] = Field(
        None,
        description="会议室信息"
    )
    
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


class ReservationListResponse(BaseModel):
    """
    预约列表响应模式
    
    用于返回预约列表和分页信息。
    
    Attributes:
        items: 预约列表
        total: 总数量
        page: 当前页码
        page_size: 每页数量
    """
    items: List[ReservationResponse] = Field(
        ...,
        description="预约列表"
    )
    total: int = Field(
        ...,
        ge=0,
        description="总数量"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="当前页码"
    )
    page_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="每页数量"
    )


class MeetingRoomListResponse(BaseModel):
    """
    会议室列表响应模式
    
    用于返回会议室列表和分页信息。
    
    Attributes:
        items: 会议室列表
        total: 总数量
    """
    items: List[MeetingRoomResponse] = Field(
        ...,
        description="会议室列表"
    )
    total: int = Field(
        ...,
        ge=0,
        description="总数量"
    )

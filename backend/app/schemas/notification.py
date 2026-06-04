# -*- coding: utf-8 -*-
"""
提醒推送相关的 Pydantic 数据模式

定义提醒查询与推送事件的数据结构。
"""

from datetime import datetime
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class ReminderResponse(BaseModel):
    """
    单条提醒响应模式

    Attributes:
        reminder_id: 提醒事件唯一标识，用于前端去重
        type: 提醒类型
        source_type: 提醒来源类型
        source_id: 来源业务对象 ID
        title: 提醒标题
        message: 提醒内容
        event_time: 业务事件时间（待办截止时间 / 会议开始时间）
        minutes_until: 距离事件发生的分钟数，逾期为负数
        severity: 提醒严重级别
        metadata: 扩展信息
    """

    reminder_id: str = Field(..., description="提醒事件唯一标识")
    type: Literal["todo_due_soon", "todo_overdue", "meeting_starting"] = Field(
        ...,
        description="提醒类型"
    )
    source_type: Literal["todo", "reservation"] = Field(
        ...,
        description="提醒来源类型"
    )
    source_id: str = Field(..., description="来源业务对象 ID")
    title: str = Field(..., description="提醒标题")
    message: str = Field(..., description="提醒内容")
    event_time: datetime = Field(..., description="业务事件时间")
    minutes_until: int = Field(..., description="距离事件时间的分钟数")
    severity: Literal["info", "warning", "error"] = Field(
        ...,
        description="提醒严重级别"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="提醒扩展信息"
    )


class ReminderListResponse(BaseModel):
    """
    提醒列表响应模式

    Attributes:
        items: 提醒列表
        generated_at: 服务端生成时间
    """

    items: List[ReminderResponse] = Field(..., description="提醒列表")
    generated_at: datetime = Field(..., description="服务端生成时间")

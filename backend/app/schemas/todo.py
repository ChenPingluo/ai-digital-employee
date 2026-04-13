# -*- coding: utf-8 -*-
"""
待办事项相关的 Pydantic 数据模式

定义待办事项的创建、更新和响应等数据验证模式。
"""

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TodoCreate(BaseModel):
    """
    待办事项创建请求模式
    
    用于验证创建待办事项时提交的数据。
    
    Attributes:
        title: 任务标题，最大200个字符
        description: 任务描述，可选
        priority: 任务优先级（0-3）
        due_date: 截止日期，可选
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="任务标题",
        examples=["完成项目报告"]
    )
    description: Optional[str] = Field(
        None,
        description="任务详细描述",
        examples=["整理本季度的项目进展报告，包含数据分析和总结"]
    )
    priority: int = Field(
        default=0,
        ge=0,
        le=3,
        description="任务优先级：0-低，1-中，2-高，3-紧急",
        examples=[1]
    )
    due_date: Optional[datetime] = Field(
        None,
        description="任务截止日期",
        examples=["2024-12-31T18:00:00+08:00"]
    )
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """验证优先级范围"""
        if v < 0 or v > 3:
            raise ValueError("优先级必须在 0-3 之间")
        return v


class TodoUpdate(BaseModel):
    """
    待办事项更新请求模式
    
    用于验证更新待办事项时提交的数据。
    所有字段都是可选的，仅更新提供的字段。
    
    Attributes:
        title: 任务标题
        description: 任务描述
        priority: 任务优先级
        status: 任务状态
        due_date: 截止日期
    """
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="任务标题"
    )
    description: Optional[str] = Field(
        None,
        description="任务详细描述"
    )
    priority: Optional[int] = Field(
        None,
        ge=0,
        le=3,
        description="任务优先级：0-低，1-中，2-高，3-紧急"
    )
    status: Optional[str] = Field(
        None,
        description="任务状态：pending/in_progress/completed/cancelled"
    )
    due_date: Optional[datetime] = Field(
        None,
        description="任务截止日期"
    )
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """验证状态值是否有效"""
        if v is not None:
            valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
            if v not in valid_statuses:
                raise ValueError(f"状态必须是以下之一：{', '.join(valid_statuses)}")
        return v
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[int]) -> Optional[int]:
        """验证优先级范围"""
        if v is not None and (v < 0 or v > 3):
            raise ValueError("优先级必须在 0-3 之间")
        return v


class TodoResponse(BaseModel):
    """
    待办事项响应模式
    
    用于返回待办事项信息给前端。
    
    Attributes:
        id: 任务唯一标识符
        user_id: 任务所属用户 ID
        title: 任务标题
        description: 任务描述
        priority: 任务优先级
        status: 任务状态
        due_date: 截止日期
        created_at: 创建时间
        updated_at: 更新时间
    """
    # 配置：允许从 ORM 模型创建
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(
        ...,
        description="任务唯一标识符"
    )
    user_id: uuid.UUID = Field(
        ...,
        description="任务所属用户 ID"
    )
    title: str = Field(
        ...,
        description="任务标题"
    )
    description: Optional[str] = Field(
        None,
        description="任务详细描述"
    )
    priority: int = Field(
        ...,
        description="任务优先级：0-低，1-中，2-高，3-紧急"
    )
    status: str = Field(
        ...,
        description="任务状态"
    )
    due_date: Optional[datetime] = Field(
        None,
        description="任务截止日期"
    )
    created_at: datetime = Field(
        ...,
        description="任务创建时间"
    )
    updated_at: datetime = Field(
        ...,
        description="任务最后更新时间"
    )
    
    @property
    def priority_label(self) -> str:
        """
        获取优先级的文字标签
        
        Returns:
            str: 优先级对应的中文标签
        """
        labels = {0: "低", 1: "中", 2: "高", 3: "紧急"}
        return labels.get(self.priority, "未知")


class TodoListResponse(BaseModel):
    """
    待办事项列表响应模式
    
    用于返回待办事项列表和分页信息。
    
    Attributes:
        items: 待办事项列表
        total: 总数量
        page: 当前页码
        page_size: 每页数量
    """
    items: List[TodoResponse] = Field(
        ...,
        description="待办事项列表"
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

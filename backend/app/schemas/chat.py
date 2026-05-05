# -*- coding: utf-8 -*-
"""
聊天相关的 Pydantic 数据模式

定义 AI 对话的请求和响应数据验证模式。
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    聊天消息模式
    
    表示一条聊天消息，包含角色和内容。
    
    Attributes:
        role: 消息角色（user/assistant/system）
        content: 消息内容
        timestamp: 消息时间戳
    """
    role: str = Field(
        ...,
        description="消息角色：user（用户）、assistant（助手）、system（系统）",
        examples=["user"]
    )
    content: str = Field(
        ...,
        description="消息内容",
        examples=["帮我查一下明天的天气"]
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="消息时间戳"
    )


class ChatRequest(BaseModel):
    """
    聊天请求模式
    
    用于验证用户发送的聊天请求。
    
    Attributes:
        message: 用户发送的消息内容
        conversation_id: 会话 ID，用于维持对话上下文
        context: 额外的上下文信息
        history: 历史消息列表
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="用户发送的消息内容",
        examples=["帮我创建一个明天下午3点的会议提醒"]
    )
    conversation_id: Optional[str] = Field(
        None,
        description="会话 ID，用于维持对话上下文。如果为空，将创建新会话",
        examples=["conv_abc123"]
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="额外的上下文信息，如当前页面、用户偏好等"
    )
    history: Optional[List[ChatMessage]] = Field(
        None,
        description="历史消息列表，用于提供对话上下文"
    )


class ToolCall(BaseModel):
    """
    工具调用记录模式
    
    记录 AI 助手在处理请求过程中调用的工具。
    
    Attributes:
        tool_name: 工具名称
        tool_input: 工具输入参数
        tool_output: 工具输出结果
    """
    tool_name: str = Field(
        ...,
        description="工具名称",
        examples=["create_todo"]
    )
    tool_input: Dict[str, Any] = Field(
        ...,
        description="工具输入参数"
    )
    tool_output: Optional[Any] = Field(
        None,
        description="工具输出结果"
    )


class ChatResponse(BaseModel):
    """
    聊天响应模式
    
    用于返回 AI 助手的响应。
    
    Attributes:
        message: AI 助手的回复内容
        conversation_id: 会话 ID
        tool_calls: 本次请求中执行的工具调用列表
        metadata: 额外的元数据信息
    """
    message: str = Field(
        ...,
        description="AI 助手的回复内容",
        examples=["好的，我已经帮您创建了一个明天下午3点的会议提醒。"]
    )
    conversation_id: str = Field(
        ...,
        description="会话 ID",
        examples=["conv_abc123"]
    )
    tool_calls: Optional[List[ToolCall]] = Field(
        None,
        description="本次请求中执行的工具调用列表"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="额外的元数据信息，如处理时间、模型名称等"
    )


class StreamChatResponse(BaseModel):
    """
    流式聊天响应模式
    
    用于流式返回 AI 助手的响应片段。
    
    Attributes:
        delta: 本次响应的增量内容
        conversation_id: 会话 ID
        is_final: 是否为最后一个响应片段
        tool_call: 当前正在执行的工具调用
    """
    delta: str = Field(
        ...,
        description="本次响应的增量内容"
    )
    conversation_id: str = Field(
        ...,
        description="会话 ID"
    )
    is_final: bool = Field(
        default=False,
        description="是否为最后一个响应片段"
    )
    tool_call: Optional[ToolCall] = Field(
        None,
        description="当前正在执行的工具调用"
    )


class ConversationCreate(BaseModel):
    """
    会话创建请求模式
    
    Attributes:
        title: 会话标题，可选
    """
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """
    会话响应模式
    
    Attributes:
        id: 会话 ID
        title: 会话标题
        created_at: 创建时间
        updated_at: 更新时间
    """
    id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """
    消息响应模式
    
    Attributes:
        id: 消息 ID
        role: 消息角色
        content: 消息内容
        created_at: 创建时间
    """
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

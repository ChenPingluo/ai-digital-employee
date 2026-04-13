# -*- coding: utf-8 -*-
"""
Pydantic 数据模式包

包含所有 API 请求和响应的数据验证模式。
"""

from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.schemas.todo import TodoCreate, TodoUpdate, TodoResponse
from app.schemas.meeting import MeetingRoomResponse, ReservationCreate, ReservationResponse
from app.schemas.chat import ChatRequest, ChatResponse

__all__ = [
    # 用户相关
    "UserCreate",
    "UserLogin", 
    "UserResponse",
    "Token",
    # 待办事项相关
    "TodoCreate",
    "TodoUpdate",
    "TodoResponse",
    # 会议室相关
    "MeetingRoomResponse",
    "ReservationCreate",
    "ReservationResponse",
    # 聊天相关
    "ChatRequest",
    "ChatResponse"
]

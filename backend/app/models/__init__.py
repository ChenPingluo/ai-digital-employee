# -*- coding: utf-8 -*-
"""
数据库模型包

导出所有 SQLAlchemy ORM 模型，用于数据库表的映射和操作。
"""

from app.models.user import User
from app.models.todo import Todo
from app.models.meeting_room import MeetingRoom
from app.models.reservation import Reservation
from app.models.conversation import Conversation, ChatMessageRecord
from app.models.user_memory import UserMemory  # ✚ 新增：导入记忆模型

# 导出所有模型，便于统一导入
__all__ = [
    "User",
    "Todo", 
    "MeetingRoom",
    "Reservation",
    "Conversation",
    "ChatMessageRecord",
    "UserMemory",  # ✚ 新增
]

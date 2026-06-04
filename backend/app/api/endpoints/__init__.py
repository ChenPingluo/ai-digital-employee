# -*- coding: utf-8 -*-
"""
API 端点包

包含各功能模块的具体端点实现。
"""

from app.api.endpoints import auth
from app.api.endpoints import todos
from app.api.endpoints import meetings
from app.api.endpoints import chat
from app.api.endpoints import statistics
from app.api.endpoints import notifications

__all__ = [
    "auth",
    "todos",
    "meetings",
    "chat",
    "statistics",
    "notifications"
]

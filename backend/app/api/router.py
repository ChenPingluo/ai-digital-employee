# -*- coding: utf-8 -*-
"""
API 路由注册模块

集中注册所有 API 端点路由，统一管理路由前缀和标签。
"""

from fastapi import APIRouter

from app.api.endpoints import auth, todos, meetings, chat, statistics, notifications

# 所有 API 路由统一使用 /api/v1 前缀
api_router = APIRouter(prefix="/api/v1")

# 认证相关接口
api_router.include_router(
    auth.router,
    tags=["认证"]
)

# 待办事项接口
api_router.include_router(
    todos.router,
    tags=["待办事项"]
)

# 会议室预约接口
api_router.include_router(
    meetings.router,
    tags=["会议室预约"]
)

# AI 对话接口
api_router.include_router(
    chat.router,
    tags=["AI 对话"]
)

# 统计数据接口
api_router.include_router(
    statistics.router,
    tags=["统计数据"]
)

# 提醒推送接口
api_router.include_router(
    notifications.router,
    tags=["提醒推送"]
)

__all__ = ["api_router"]

# -*- coding: utf-8 -*-
"""
统计数据接口模块

提供待办事项和会议室使用统计的 API 端点。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services import todo_service, meeting_service
from app.middleware.auth import get_current_user


# 创建路由器
router = APIRouter(prefix="/statistics", tags=["统计数据"])


@router.get(
    "/todo-stats",
    summary="待办事项统计",
    description="获取当前用户的待办事项统计数据"
)
async def get_todo_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    待办事项统计接口
    
    返回按状态分组的待办事项统计：
    - pending: 待处理数量
    - in_progress: 进行中数量
    - completed: 已完成数量
    - cancelled: 已取消数量
    - total: 总数量
    - by_priority: 按优先级分组的未完成任务数量
    """
    try:
        stats = await todo_service.get_todo_stats(
            db=db,
            user_id=current_user.id
        )
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待办统计失败: {str(e)}"
        )


@router.get(
    "/meeting-stats",
    summary="会议室使用统计",
    description="获取会议室使用率统计数据"
)
async def get_meeting_stats(
    include_all_users: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    会议室使用统计接口
    
    返回按会议室分组的使用统计：
    - rooms: 各会议室的预约次数和总时长
    - total_reservations: 总预约次数
    - total_duration_hours: 总使用时长（小时）
    
    - **include_all_users**: 是否包含所有用户的数据（默认仅统计当前用户）
    """
    try:
        # 如果是管理员且请求全部数据，则不传 user_id
        user_id = None if include_all_users else current_user.id
        
        stats = await meeting_service.get_meeting_stats(
            db=db,
            user_id=user_id
        )
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会议统计失败: {str(e)}"
        )


@router.get(
    "/overview",
    summary="数据概览",
    description="获取用户的数据概览统计"
)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    数据概览接口
    
    返回用户的综合数据概览：
    - todo_stats: 待办事项统计
    - meeting_stats: 会议统计
    """
    try:
        # 获取待办统计
        todo_stats = await todo_service.get_todo_stats(
            db=db,
            user_id=current_user.id
        )
        
        # 获取会议统计
        meeting_stats = await meeting_service.get_meeting_stats(
            db=db,
            user_id=current_user.id
        )
        
        return {
            "status": "success",
            "data": {
                "user": {
                    "id": str(current_user.id),
                    "username": current_user.username,
                    "department": current_user.department
                },
                "todo_stats": todo_stats,
                "meeting_stats": meeting_stats
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据概览失败: {str(e)}"
        )

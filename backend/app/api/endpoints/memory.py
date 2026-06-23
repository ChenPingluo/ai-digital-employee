# -*- coding: utf-8 -*-
"""
记忆管理 API 接口模块

提供用户记忆的查询、搜索、删除和统计接口。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.middleware.auth import get_current_user
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["记忆管理"])


@router.get(
    "/memories",
    summary="获取用户记忆列表",
    description="获取当前用户的所有长期记忆，支持按类型筛选"
)
async def get_memories(
    memory_type: str = Query(None, description="记忆类型: fact/preference/event/person/context"),
    category: str = Query(None, description="分类标签: work/tech/health/life/learning"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户记忆列表"""
    memories = await MemoryService.get_user_memories(
        db=db,
        user_id=str(current_user.id),
        memory_type=memory_type,
        category=category,
        limit=limit
    )
    return [mem.to_dict() for mem in memories]


@router.get(
    "/memories/search",
    summary="搜索记忆",
    description="按关键词搜索用户记忆"
)
async def search_memories(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量上限"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """搜索记忆"""
    memories = await MemoryService.search_memories(
        db=db,
        user_id=str(current_user.id),
        query=q,
        limit=limit
    )
    return [mem.to_dict() for mem in memories]


@router.delete(
    "/memories/{memory_id}",
    summary="删除记忆",
    description="删除指定的记忆（软删除）"
)
async def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除记忆"""
    success = await MemoryService.delete_memory(
        db=db,
        memory_id=memory_id,
        user_id=str(current_user.id)
    )
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在或无权操作")
    return {"success": True}


@router.get(
    "/memories/stats",
    summary="记忆统计",
    description="获取用户记忆的统计信息"
)
async def get_memory_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取记忆统计"""
    stats = await MemoryService.get_memory_stats(db, str(current_user.id))
    return stats

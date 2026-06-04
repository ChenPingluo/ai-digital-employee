# -*- coding: utf-8 -*-
"""
待办事项接口模块

提供待办事项的 CRUD API 端点。
所有接口都需要认证，用户只能操作自己的待办事项。
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.todo import (
    TodoCreate,
    TodoUpdate,
    TodoResponse,
    TodoListResponse
)
from app.services import todo_service
from app.middleware.auth import get_current_user


# 创建路由器
router = APIRouter(prefix="/todos", tags=["待办事项"])


@router.get(
    "/",
    response_model=TodoListResponse,
    summary="获取待办事项列表",
    description="获取当前用户的待办事项列表，支持状态和优先级筛选"
)
async def get_todos(
    status: Optional[str] = Query(
        None,
        description="状态筛选：pending/in_progress/completed/cancelled"
    ),
    priority: Optional[int] = Query(
        None,
        ge=0,
        le=3,
        description="优先级筛选：0-低，1-中，2-高，3-紧急"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取待办事项列表接口
    
    支持的筛选条件：
    - status: 任务状态
    - priority: 任务优先级
    
    返回分页结果，按优先级降序、创建时间降序排列。
    """
    try:
        todos, total = await todo_service.get_todos(
            db=db,
            user_id=current_user.id,
            status=status,
            priority=priority,
            page=page,
            page_size=page_size
        )
        
        return TodoListResponse(
            items=[TodoResponse.model_validate(todo) for todo in todos],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待办事项列表失败: {str(e)}"
        )


@router.post(
    "/",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建待办事项",
    description="创建新的待办事项"
)
async def create_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建待办事项接口
    
    - **title**: 任务标题
    - **description**: 任务描述
    - **priority**: 优先级 0-3
    - **due_date**: 截止日期
    """
    try:
        todo = await todo_service.create_todo(
            db=db,
            user_id=current_user.id,
            todo_data=todo_data
        )
        
        return TodoResponse.model_validate(todo)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建待办事项失败: {str(e)}"
        )


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="获取单个待办事项",
    description="根据 ID 获取待办事项详情"
)
async def get_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取单个待办事项接口
    
    - **todo_id**: 待办事项 ID
    """
    try:
        todo = await todo_service.get_todo_by_id(
            db=db,
            user_id=current_user.id,
            todo_id=todo_id
        )
        
        if todo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="待办事项不存在或无权访问"
            )
        
        return TodoResponse.model_validate(todo)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待办事项失败: {str(e)}"
        )


@router.put(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="更新待办事项",
    description="更新指定的待办事项"
)
async def update_todo(
    todo_id: UUID,
    todo_data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新待办事项接口
    
    - **todo_id**: 待办事项 ID
    - 请求体中只需包含要更新的字段
    """
    try:
        todo = await todo_service.update_todo(
            db=db,
            user_id=current_user.id,
            todo_id=todo_id,
            todo_data=todo_data
        )
        
        if todo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="待办事项不存在或无权修改"
            )
        
        return TodoResponse.model_validate(todo)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新待办事项失败: {str(e)}"
        )


@router.patch(
    "/{todo_id}/status",
    response_model=TodoResponse,
    summary="更新待办状态",
    description="快捷更新待办事项的状态"
)
async def update_todo_status(
    todo_id: UUID,
    status_value: str = Query(
        ...,
        alias="status",
        description="新状态：pending/in_progress/completed/cancelled"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新待办状态接口
    
    快捷接口，仅更新状态字段。
    
    - **todo_id**: 待办事项 ID
    - **status**: 新状态值
    """
    try:
        todo = await todo_service.update_todo_status(
            db=db,
            user_id=current_user.id,
            todo_id=todo_id,
            status=status_value
        )
        
        if todo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="待办事项不存在或无权修改"
            )
        
        return TodoResponse.model_validate(todo)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新待办状态失败: {str(e)}"
        )


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除待办事项",
    description="删除指定的待办事项"
)
async def delete_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除待办事项接口
    
    - **todo_id**: 待办事项 ID
    
    删除成功返回 204 No Content
    """
    try:
        success = await todo_service.delete_todo(
            db=db,
            user_id=current_user.id,
            todo_id=todo_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="待办事项不存在或无权删除"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除待办事项失败: {str(e)}"
        )

# -*- coding: utf-8 -*-
"""
待办事项服务模块

提供待办事项的 CRUD 业务逻辑，包括创建、查询、更新和删除操作。
所有数据库操作均为异步实现。
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Todo
from app.schemas.todo import TodoCreate, TodoUpdate


async def create_todo(
    db: AsyncSession,
    user_id: uuid.UUID,
    todo_data: TodoCreate
) -> Todo:
    """
    创建新的待办事项
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        todo_data: 待办事项创建数据
        
    Returns:
        Todo: 创建成功的待办事项对象
        
    Raises:
        Exception: 数据库操作失败时抛出异常
    """
    try:
        # 创建 Todo 实例
        todo = Todo(
            user_id=user_id,
            title=todo_data.title,
            description=todo_data.description,
            priority=todo_data.priority,
            due_date=todo_data.due_date,
            status="pending"
        )
        
        # 添加到会话并刷新以获取生成的 ID
        db.add(todo)
        await db.flush()
        await db.refresh(todo)
        
        return todo
        
    except Exception as e:
        # 记录错误并重新抛出
        raise Exception(f"创建待办事项失败: {str(e)}")


async def get_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    page: int = 1,
    page_size: int = 10
) -> tuple[List[Todo], int]:
    """
    获取用户的待办事项列表
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        status: 状态筛选条件（可选）
        priority: 优先级筛选条件（可选）
        page: 当前页码
        page_size: 每页数量
        
    Returns:
        tuple[List[Todo], int]: (待办事项列表, 总数量)
    """
    try:
        # 构建基础查询条件
        conditions = [Todo.user_id == user_id]
        
        # 添加状态筛选
        if status:
            conditions.append(Todo.status == status)
        
        # 添加优先级筛选
        if priority is not None:
            conditions.append(Todo.priority == priority)
        
        # 查询总数
        count_query = select(func.count(Todo.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页查询
        offset = (page - 1) * page_size
        query = (
            select(Todo)
            .where(and_(*conditions))
            .order_by(Todo.priority.desc(), Todo.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        
        result = await db.execute(query)
        todos = result.scalars().all()
        
        return list(todos), total
        
    except Exception as e:
        raise Exception(f"查询待办事项列表失败: {str(e)}")


async def get_todo_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    todo_id: uuid.UUID
) -> Optional[Todo]:
    """
    根据 ID 获取单个待办事项
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID（用于权限验证）
        todo_id: 待办事项 ID
        
    Returns:
        Optional[Todo]: 待办事项对象，不存在或无权限时返回 None
    """
    try:
        query = select(Todo).where(
            and_(
                Todo.id == todo_id,
                Todo.user_id == user_id
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
        
    except Exception as e:
        raise Exception(f"查询待办事项失败: {str(e)}")


async def update_todo(
    db: AsyncSession,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
    todo_data: TodoUpdate
) -> Optional[Todo]:
    """
    更新待办事项
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID（用于权限验证）
        todo_id: 待办事项 ID
        todo_data: 更新数据
        
    Returns:
        Optional[Todo]: 更新后的待办事项对象，不存在或无权限时返回 None
    """
    try:
        # 查询待办事项
        todo = await get_todo_by_id(db, user_id, todo_id)
        
        if todo is None:
            return None
        
        # 更新提供的字段
        update_data = todo_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if value is not None:
                setattr(todo, field, value)
        
        # 更新修改时间
        todo.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(todo)
        
        return todo
        
    except Exception as e:
        raise Exception(f"更新待办事项失败: {str(e)}")


async def update_todo_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
    status: str
) -> Optional[Todo]:
    """
    更新待办事项状态（简化接口，用于 Agent 调用）
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        todo_id: 待办事项 ID
        status: 新状态
        
    Returns:
        Optional[Todo]: 更新后的待办事项对象
    """
    try:
        # 验证状态值
        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f"无效的状态值: {status}")
        
        # 查询待办事项
        todo = await get_todo_by_id(db, user_id, todo_id)
        
        if todo is None:
            return None
        
        # 更新状态
        todo.status = status
        todo.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(todo)
        
        return todo
        
    except Exception as e:
        raise Exception(f"更新待办状态失败: {str(e)}")


async def delete_todo(
    db: AsyncSession,
    user_id: uuid.UUID,
    todo_id: uuid.UUID
) -> bool:
    """
    删除待办事项
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID（用于权限验证）
        todo_id: 待办事项 ID
        
    Returns:
        bool: 删除成功返回 True，不存在或无权限返回 False
    """
    try:
        # 查询待办事项
        todo = await get_todo_by_id(db, user_id, todo_id)
        
        if todo is None:
            return False
        
        # 删除记录
        await db.delete(todo)
        await db.flush()
        
        return True
        
    except Exception as e:
        raise Exception(f"删除待办事项失败: {str(e)}")


async def get_todo_stats(
    db: AsyncSession,
    user_id: uuid.UUID
) -> dict:
    """
    获取待办事项统计数据
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        
    Returns:
        dict: 按状态分组的统计数据
    """
    try:
        # 按状态分组统计
        query = (
            select(Todo.status, func.count(Todo.id).label("count"))
            .where(Todo.user_id == user_id)
            .group_by(Todo.status)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        # 构建统计结果
        stats = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
            "total": 0
        }
        
        for status, count in rows:
            stats[status] = count
            stats["total"] += count
        
        # 添加优先级统计
        priority_query = (
            select(Todo.priority, func.count(Todo.id).label("count"))
            .where(
                and_(
                    Todo.user_id == user_id,
                    Todo.status.in_(["pending", "in_progress"])
                )
            )
            .group_by(Todo.priority)
        )
        
        priority_result = await db.execute(priority_query)
        priority_rows = priority_result.all()
        
        priority_labels = {0: "低", 1: "中", 2: "高", 3: "紧急"}
        stats["by_priority"] = {
            priority_labels.get(p, "未知"): c for p, c in priority_rows
        }
        
        return stats
        
    except Exception as e:
        raise Exception(f"获取待办统计失败: {str(e)}")

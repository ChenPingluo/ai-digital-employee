# -*- coding: utf-8 -*-
"""
待办事项 Langchain 工具模块

提供用于 AI Agent 的待办事项操作工具。
使用工厂函数模式，为每个用户创建绑定的工具实例。

重要：所有工具函数都是异步的，直接在同一事件循环中执行，
避免跨线程使用 AsyncSession。
"""

import uuid
from typing import List, Optional

from langchain.tools import StructuredTool
from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.datetime_utils import parse_user_datetime, to_beijing_time
from app.services import todo_service
from app.schemas.todo import TodoCreate, TodoUpdate


# ==================== 工具参数模式 ====================

class CreateTodoInput(BaseModel):
    """创建待办事项的参数模式"""
    title: str = Field(description="待办事项标题，简洁描述任务内容")
    description: str = Field(default="", description="详细描述（可选）")
    priority: int = Field(
        default=0,
        ge=0,
        le=3,
        description="优先级：0-低，1-中，2-高，3-紧急"
    )
    due_date: Optional[str] = Field(
        default=None,
        description="截止日期，ISO 格式如 '2024-12-31T18:00:00'"
    )


class ListTodosInput(BaseModel):
    """查询待办事项列表的参数模式"""
    status: Optional[str] = Field(
        default=None,
        description="状态筛选：pending（待处理）、in_progress（进行中）、completed（已完成）、cancelled（已取消）"
    )


class UpdateTodoStatusInput(BaseModel):
    """更新待办状态的参数模式"""
    todo_id: str = Field(description="待办事项 ID（UUID 格式）")
    status: str = Field(
        description="新状态：pending、in_progress、completed、cancelled"
    )


def get_todo_tools(user_id: str, db_session: AsyncSession) -> List[BaseTool]:
    """
    获取绑定用户 ID 的待办事项工具列表
    
    使用闭包模式将 user_id 和 db_session 绑定到工具函数中。
    所有工具函数都是异步的，直接 await service 方法。
    
    Args:
        user_id: 当前用户 ID
        db_session: 数据库会话
        
    Returns:
        List[BaseTool]: Langchain 工具列表
    """
    
    async def create_todo(
        title: str,
        description: str = "",
        priority: int = 0,
        due_date: Optional[str] = None
    ) -> str:
        """
        创建新的待办事项
        
        Args:
            title: 待办事项标题
            description: 详细描述
            priority: 优先级（0-低，1-中，2-高，3-紧急）
            due_date: 截止日期（ISO 格式）
            
        Returns:
            str: 操作结果描述
        """
        try:
            # 解析截止日期
            parsed_due_date = None
            if due_date:
                try:
                    parsed_due_date = parse_user_datetime(due_date)
                except ValueError:
                    return f"截止日期格式错误：{due_date}，请使用 ISO 格式如 '2024-12-31T18:00:00'"
            
            # 构建创建数据
            todo_data = TodoCreate(
                title=title,
                description=description,
                priority=priority,
                due_date=parsed_due_date
            )
            
            # 直接 await 异步操作，在同一事件循环中执行
            todo = await todo_service.create_todo(
                db=db_session,
                user_id=uuid.UUID(user_id),
                todo_data=todo_data
            )
            
            priority_labels = {0: "低", 1: "中", 2: "高", 3: "紧急"}
            priority_label = priority_labels.get(priority, "未知")
            
            result = f"  已创建待办事项：「{title}」\n"
            result += f"   优先级：{priority_label}\n"
            result += f"   ID：{todo.id}"
            if parsed_due_date:
                display_due_date = to_beijing_time(parsed_due_date)
                result += f"\n   截止日期：{display_due_date.strftime('%Y-%m-%d %H:%M')}"
            
            return result
            
        except Exception as e:
            return f"创建待办事项失败：{str(e)}"
    
    async def list_todos(status: Optional[str] = None) -> str:
        """
        查询待办事项列表
        
        Args:
            status: 状态筛选条件
            
        Returns:
            str: 待办事项列表描述
        """
        try:
            # 直接 await 异步操作
            todos, total = await todo_service.get_todos(
                db=db_session,
                user_id=uuid.UUID(user_id),
                status=status,
                page=1,
                page_size=20
            )
            
            if not todos:
                status_text = f"状态为「{status}」的" if status else ""
                return f" 暂无{status_text}待办事项"
            
            # 格式化输出
            priority_labels = {0: "低", 1: "中", 2: "高", 3: "紧急"}
            status_labels = {
                "pending": "待处理",
                "in_progress": "进行中",
                "completed": "已完成",
                "cancelled": "已取消"
            }
            
            result = f" 待办事项列表（共 {total} 项）：\n\n"
            
            for i, todo in enumerate(todos, 1):
                priority_label = priority_labels.get(todo.priority, "未知")
                status_label = status_labels.get(todo.status, todo.status)
                
                # 状态图标
                status_icon = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "cancelled": "❌"
                }.get(todo.status, "📌")
                
                result += f"{i}. {status_icon} {todo.title}\n"
                result += f"   状态：{status_label} | 优先级：{priority_label}\n"
                if todo.due_date:
                    display_due_date = to_beijing_time(todo.due_date)
                    result += f"   截止：{display_due_date.strftime('%Y-%m-%d %H:%M')}\n"
                result += f"   ID：{todo.id}\n\n"
            
            return result.strip()
            
        except Exception as e:
            return f" 查询待办事项失败：{str(e)}"
    
    async def update_todo_status(todo_id: str, status: str) -> str:
        """
        更新待办事项状态
        
        Args:
            todo_id: 待办事项 ID
            status: 新状态
            
        Returns:
            str: 操作结果描述
        """
        try:
            # 验证状态值
            valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
            if status not in valid_statuses:
                return f" 无效的状态值：{status}，有效值为：{', '.join(valid_statuses)}"
            
            # 直接 await 异步操作
            todo = await todo_service.update_todo_status(
                db=db_session,
                user_id=uuid.UUID(user_id),
                todo_id=uuid.UUID(todo_id),
                status=status
            )
            
            if todo is None:
                return f" 未找到待办事项（ID：{todo_id}）或无权修改"
            
            status_labels = {
                "pending": "待处理",
                "in_progress": "进行中",
                "completed": "已完成",
                "cancelled": "已取消"
            }
            status_label = status_labels.get(status, status)
            
            return f" 已将「{todo.title}」的状态更新为：{status_label}"
            
        except ValueError:
            return f" 无效的待办事项 ID：{todo_id}"
        except Exception as e:
            return f" 更新待办状态失败：{str(e)}"
    
    # 创建 Langchain 工具（支持异步函数）
    tools = [
        StructuredTool.from_function(
            func=create_todo,
            coroutine=create_todo,  # 指定异步协程
            name="create_todo",
            description="创建新的待办事项。需要提供标题，可选提供描述、优先级和截止日期。",
            args_schema=CreateTodoInput
        ),
        StructuredTool.from_function(
            func=list_todos,
            coroutine=list_todos,  # 指定异步协程
            name="list_todos",
            description="查询待办事项列表。可以按状态筛选：pending（待处理）、in_progress（进行中）、completed（已完成）、cancelled（已取消）。",
            args_schema=ListTodosInput
        ),
        StructuredTool.from_function(
            func=update_todo_status,
            coroutine=update_todo_status,  # 指定异步协程
            name="update_todo_status",
            description="更新待办事项的状态。需要提供待办事项 ID 和新状态。",
            args_schema=UpdateTodoStatusInput
        )
    ]
    
    return tools

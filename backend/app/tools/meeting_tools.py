# -*- coding: utf-8 -*-
"""
会议室预约 Langchain 工具模块

提供用于 AI Agent 的会议室预约操作工具。
使用工厂函数模式，为每个用户创建绑定的工具实例。

重要：所有工具函数都是异步的，直接在同一事件循环中执行，
避免跨线程使用 AsyncSession。
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from langchain.tools import StructuredTool
from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import meeting_service
from app.schemas.meeting import ReservationCreate


# ==================== 工具参数模式 ====================

class ListMeetingRoomsInput(BaseModel):
    """查询会议室列表的参数模式"""
    min_capacity: int = Field(
        default=0,
        ge=0,
        description="最小容纳人数，用于筛选足够大的会议室"
    )


class CreateReservationInput(BaseModel):
    """创建预约的参数模式"""
    room_id: str = Field(description="会议室 ID（UUID 格式）")
    title: str = Field(description="会议主题")
    start_time: str = Field(
        description="开始时间，ISO 格式如 '2024-12-31T10:00:00'"
    )
    end_time: str = Field(
        description="结束时间，ISO 格式如 '2024-12-31T11:00:00'"
    )


class ListMyReservationsInput(BaseModel):
    """查询我的预约的参数模式"""
    include_past: bool = Field(
        default=False,
        description="是否包含已过期的预约"
    )


# ==================== 工具工厂函数 ====================

def get_meeting_tools(user_id: str, db_session: AsyncSession) -> List[BaseTool]:
    """
    获取绑定用户 ID 的会议室工具列表
    
    所有工具函数都是异步的，直接 await service 方法。
    
    Args:
        user_id: 当前用户 ID
        db_session: 数据库会话
        
    Returns:
        List[BaseTool]: Langchain 工具列表
    """
    
    async def list_meeting_rooms(min_capacity: int = 0) -> str:
        """
        查询可用会议室列表
        
        Args:
            min_capacity: 最小容纳人数
            
        Returns:
            str: 会议室列表描述
        """
        try:
            # 直接 await 异步操作，在同一事件循环中执行
            rooms = await meeting_service.get_available_rooms(
                db=db_session,
                min_capacity=min_capacity
            )
            
            if not rooms:
                capacity_text = f"容纳 {min_capacity} 人以上的" if min_capacity > 0 else ""
                return f"🏢 暂无{capacity_text}可用会议室"
            
            result = f"🏢 可用会议室列表（共 {len(rooms)} 个）：\n\n"
            
            for room in rooms:
                equipment_str = ", ".join(room.equipment) if room.equipment else "无"
                result += f"📍 {room.name}\n"
                result += f"   位置：{room.location or '未指定'}\n"
                result += f"   容量：{room.capacity} 人\n"
                result += f"   设备：{equipment_str}\n"
                result += f"   ID：{room.id}\n\n"
            
            return result.strip()
            
        except Exception as e:
            return f"❌ 查询会议室失败：{str(e)}"
    
    async def create_reservation(
        room_id: str,
        title: str,
        start_time: str,
        end_time: str
    ) -> str:
        """
        创建会议室预约
        
        Args:
            room_id: 会议室 ID
            title: 会议主题
            start_time: 开始时间（ISO 格式）
            end_time: 结束时间（ISO 格式）
            
        Returns:
            str: 操作结果描述
        """
        try:
            # 解析时间
            try:
                parsed_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                parsed_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError as e:
                return f"❌ 时间格式错误：{str(e)}，请使用 ISO 格式如 '2024-12-31T10:00:00'"
            
            # 验证时间
            if parsed_end <= parsed_start:
                return "❌ 结束时间必须晚于开始时间"
            
            if parsed_start < datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None):
                return "❌ 开始时间不能早于当前时间"
            
            # 构建预约数据
            reservation_data = ReservationCreate(
                room_id=uuid.UUID(room_id),
                title=title,
                start_time=parsed_start,
                end_time=parsed_end
            )
            
            # 直接 await 异步操作
            reservation = await meeting_service.create_reservation(
                db=db_session,
                user_id=uuid.UUID(user_id),
                reservation_data=reservation_data
            )
            
            # 计算会议时长
            duration = (parsed_end - parsed_start).total_seconds() / 60
            hours = int(duration // 60)
            minutes = int(duration % 60)
            duration_str = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
            
            result = f"✅ 会议预约成功！\n\n"
            result += f"📋 会议主题：{title}\n"
            result += f"🕐 开始时间：{parsed_start.strftime('%Y-%m-%d %H:%M')}\n"
            result += f"🕑 结束时间：{parsed_end.strftime('%Y-%m-%d %H:%M')}\n"
            result += f"⏱️ 会议时长：{duration_str}\n"
            result += f"🔖 预约ID：{reservation.id}"
            
            return result
            
        except ValueError as e:
            if "时间冲突" in str(e) or "已被预约" in str(e):
                return f"❌ 预约失败：该时间段已被占用，请选择其他时间"
            return f"❌ 预约失败：{str(e)}"
        except Exception as e:
            return f"❌ 创建预约失败：{str(e)}"
    
    async def list_my_reservations(include_past: bool = False) -> str:
        """
        查询我的预约记录
        
        Args:
            include_past: 是否包含已过期的预约
            
        Returns:
            str: 预约列表描述
        """
        try:
            # 直接 await 异步操作
            reservations, total = await meeting_service.get_user_reservations(
                db=db_session,
                user_id=uuid.UUID(user_id),
                include_past=include_past,
                page=1,
                page_size=20
            )
            
            if not reservations:
                past_text = "（含历史记录）" if include_past else ""
                return f"📅 暂无会议预约记录{past_text}"
            
            # 状态图标和标签
            status_info = {
                "confirmed": ("✅", "已确认"),
                "cancelled": ("❌", "已取消"),
                "completed": ("☑️", "已完成")
            }
            
            result = f"📅 我的会议预约（共 {total} 个）：\n\n"
            
            for reservation in reservations:
                icon, status_label = status_info.get(
                    reservation.status,
                    ("📌", reservation.status)
                )
                
                # 计算时长
                duration = (reservation.end_time - reservation.start_time).total_seconds() / 60
                hours = int(duration // 60)
                minutes = int(duration % 60)
                duration_str = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
                
                result += f"{icon} {reservation.title}\n"
                result += f"   时间：{reservation.start_time.strftime('%Y-%m-%d %H:%M')} - {reservation.end_time.strftime('%H:%M')}\n"
                result += f"   时长：{duration_str}\n"
                result += f"   状态：{status_label}\n"
                if reservation.room:
                    result += f"   会议室：{reservation.room.name}\n"
                result += f"   预约ID：{reservation.id}\n\n"
            
            return result.strip()
            
        except Exception as e:
            return f"❌ 查询预约记录失败：{str(e)}"
    
    # 创建 Langchain 工具（支持异步函数）
    tools = [
        StructuredTool.from_function(
            func=list_meeting_rooms,
            coroutine=list_meeting_rooms,  # 指定异步协程
            name="list_meeting_rooms",
            description="查询可用的会议室列表。可以按最小容纳人数筛选，例如需要容纳10人的会议室。",
            args_schema=ListMeetingRoomsInput
        ),
        StructuredTool.from_function(
            func=create_reservation,
            coroutine=create_reservation,  # 指定异步协程
            name="create_reservation",
            description="预约会议室。需要提供会议室ID、会议主题、开始时间和结束时间。会自动检测时间冲突。",
            args_schema=CreateReservationInput
        ),
        StructuredTool.from_function(
            func=list_my_reservations,
            coroutine=list_my_reservations,  # 指定异步协程
            name="list_my_reservations",
            description="查看我的会议预约记录。可以选择是否包含已过期的历史预约。",
            args_schema=ListMyReservationsInput
        )
    ]
    
    return tools

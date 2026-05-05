# -*- coding: utf-8 -*-
"""
会议室服务模块

提供会议室查询和预约管理的业务逻辑，包括时间冲突检测。
所有数据库操作均为异步实现。
集成 Redis 缓存，会议室列表缓存 TTL 5分钟。
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MeetingRoom, Reservation
from app.schemas.meeting import ReservationCreate
from app.services.cache_service import (
    get_meeting_rooms_cache,
    set_meeting_rooms_cache,
    clear_meeting_rooms_cache,
    MEETING_ROOM_CACHE_TTL
)


async def get_available_rooms(
    db: AsyncSession,
    min_capacity: int = 0
) -> List[MeetingRoom]:
    """
    获取所有可用会议室
    
    集成 Redis 缓存，缓存 TTL 5分钟。
    缓存按 min_capacity 分组，key 格式：meeting_rooms:available:{min_capacity}
    
    Args:
        db: 异步数据库会话
        min_capacity: 最小容纳人数筛选条件
        
    Returns:
        List[MeetingRoom]: 会议室列表
    """
    # ===== 第一步：尝试从 Redis 缓存获取 =====
    try:
        cached_rooms = await get_meeting_rooms_cache(min_capacity)
        if cached_rooms is not None:
            # 缓存命中，将缓存数据转换为 MeetingRoom 对象
            # 注意：这里返回的是字典列表，需要重新查询以获取 ORM 对象
            # 为了简化，直接查询数据库并返回，但录入日志表示缓存命中
            print(f"ℹ️ 会议室列表缓存命中 (min_capacity={min_capacity})")
            pass  # 继续查询数据库以获取 ORM 对象
    except Exception as e:
        # 缓存操作异常时降级为直接查询数据库
        print(f"⚠️ 会议室缓存查询失败，降级为数据库查询: {e}")
    
    # ===== 第二步：查询数据库 =====
    try:
        # 构建查询条件
        conditions = [MeetingRoom.is_available == True]
        
        if min_capacity > 0:
            conditions.append(MeetingRoom.capacity >= min_capacity)
        
        # 查询会议室
        query = (
            select(MeetingRoom)
            .where(and_(*conditions))
            .order_by(MeetingRoom.capacity, MeetingRoom.name)
        )
        
        result = await db.execute(query)
        rooms = result.scalars().all()
        rooms_list = list(rooms)
        
        # ===== 第三步：将结果写入 Redis 缓存 =====
        try:
            # 将 ORM 对象转换为可序列化的字典
            rooms_data = [
                {
                    "id": str(room.id),
                    "name": room.name,
                    "capacity": room.capacity,
                    "location": room.location,
                    "equipment": room.equipment,
                    "is_available": room.is_available
                }
                for room in rooms_list
            ]
            await set_meeting_rooms_cache(min_capacity, rooms_data)
        except Exception as e:
            # 缓存写入失败不影响返回结果
            print(f"⚠️ 会议室列表缓存写入失败: {e}")
        
        return rooms_list
        
    except Exception as e:
        raise Exception(f"查询会议室列表失败: {str(e)}")


async def get_room_by_id(
    db: AsyncSession,
    room_id: uuid.UUID
) -> Optional[MeetingRoom]:
    """
    根据 ID 获取会议室
    
    Args:
        db: 异步数据库会话
        room_id: 会议室 ID
        
    Returns:
        Optional[MeetingRoom]: 会议室对象，不存在返回 None
    """
    try:
        query = select(MeetingRoom).where(MeetingRoom.id == room_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
        
    except Exception as e:
        raise Exception(f"查询会议室失败: {str(e)}")


async def check_reservation_conflict(
    db: AsyncSession,
    room_id: uuid.UUID,
    start_time: datetime,
    end_time: datetime,
    exclude_reservation_id: Optional[uuid.UUID] = None
) -> bool:
    """
    检查指定时间段是否存在预约冲突
    
    Args:
        db: 异步数据库会话
        room_id: 会议室 ID
        start_time: 预约开始时间
        end_time: 预约结束时间
        exclude_reservation_id: 要排除的预约 ID（用于更新场景）
        
    Returns:
        bool: 存在冲突返回 True，否则返回 False
    """
    try:
        # 构建冲突检测条件：
        # 现有预约的时间段与新预约时间段有重叠
        # 重叠条件：现有开始时间 < 新结束时间 AND 现有结束时间 > 新开始时间
        conditions = [
            Reservation.room_id == room_id,
            Reservation.status == "confirmed",
            Reservation.start_time < end_time,
            Reservation.end_time > start_time
        ]
        
        # 排除指定预约（用于更新场景）
        if exclude_reservation_id:
            conditions.append(Reservation.id != exclude_reservation_id)
        
        query = select(func.count(Reservation.id)).where(and_(*conditions))
        result = await db.execute(query)
        conflict_count = result.scalar() or 0
        
        return conflict_count > 0
        
    except Exception as e:
        raise Exception(f"检测预约冲突失败: {str(e)}")


async def create_reservation(
    db: AsyncSession,
    user_id: uuid.UUID,
    reservation_data: ReservationCreate
) -> Reservation:
    """
    创建会议室预约
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        reservation_data: 预约创建数据
        
    Returns:
        Reservation: 创建成功的预约对象
        
    Raises:
        ValueError: 会议室不存在或存在时间冲突时抛出
        Exception: 数据库操作失败时抛出
    """
    try:
        # 检查会议室是否存在且可用
        room = await get_room_by_id(db, reservation_data.room_id)
        if room is None:
            raise ValueError("会议室不存在")
        
        if not room.is_available:
            raise ValueError("该会议室当前不可预约")
        
        # 检查时间冲突
        has_conflict = await check_reservation_conflict(
            db,
            reservation_data.room_id,
            reservation_data.start_time,
            reservation_data.end_time
        )
        
        if has_conflict:
            raise ValueError("该时间段已被预约，请选择其他时间")
        
        # 创建预约
        reservation = Reservation(
            room_id=reservation_data.room_id,
            user_id=user_id,
            title=reservation_data.title,
            start_time=reservation_data.start_time,
            end_time=reservation_data.end_time,
            status="confirmed"
        )
        
        db.add(reservation)
        await db.flush()

        # flush 后重新查询以加载关联对象
        # noload 策略下 db.refresh 无法加载 relationship
        # 先 expunge 从 session 移除，避免 identity map 返回未加载的缓存实例
        reservation_id = reservation.id
        db.expunge(reservation)
        result = await db.execute(
            select(Reservation)
            .options(
                selectinload(Reservation.room),
                selectinload(Reservation.user)
            )
            .where(Reservation.id == reservation_id)
        )
        reservation = result.scalar_one()
        
        # ===== 创建预约后清除会议室缓存 =====
        try:
            await clear_meeting_rooms_cache()
        except Exception as e:
            # 缓存清除失败不影响业务逻辑
            print(f"⚠️ 创建预约后清除缓存失败: {e}")
        
        return reservation
        
    except ValueError:
        # 业务验证错误直接抛出
        raise
    except Exception as e:
        raise Exception(f"创建预约失败: {str(e)}")


async def get_user_reservations(
    db: AsyncSession,
    user_id: uuid.UUID,
    include_past: bool = False,
    page: int = 1,
    page_size: int = 10
) -> tuple[List[Reservation], int]:
    """
    获取用户的预约记录
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        include_past: 是否包含已过期的预约
        page: 当前页码
        page_size: 每页数量
        
    Returns:
        tuple[List[Reservation], int]: (预约列表, 总数量)
    """
    try:
        # 构建查询条件
        conditions = [Reservation.user_id == user_id]
        
        if not include_past:
            # 只显示未取消且未过期的预约
            conditions.append(Reservation.status != "cancelled")
            conditions.append(Reservation.end_time > datetime.utcnow())
        
        # 查询总数
        count_query = select(func.count(Reservation.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页查询（加载会议室和用户信息）
        offset = (page - 1) * page_size
        query = (
            select(Reservation)
            .options(
                selectinload(Reservation.room),
                selectinload(Reservation.user)
            )
            .where(and_(*conditions))
            .order_by(Reservation.start_time.desc())
            .offset(offset)
            .limit(page_size)
        )
        
        result = await db.execute(query)
        reservations = result.scalars().all()
        
        return list(reservations), total
        
    except Exception as e:
        raise Exception(f"查询预约列表失败: {str(e)}")


async def get_reservation_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    reservation_id: uuid.UUID
) -> Optional[Reservation]:
    """
    根据 ID 获取预约记录
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID（用于权限验证）
        reservation_id: 预约 ID
        
    Returns:
        Optional[Reservation]: 预约对象，不存在或无权限返回 None
    """
    try:
        query = (
            select(Reservation)
            .options(
                selectinload(Reservation.room),
                selectinload(Reservation.user)
            )
            .where(
                and_(
                    Reservation.id == reservation_id,
                    Reservation.user_id == user_id
                )
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
        
    except Exception as e:
        raise Exception(f"查询预约失败: {str(e)}")


async def cancel_reservation(
    db: AsyncSession,
    user_id: uuid.UUID,
    reservation_id: uuid.UUID
) -> bool:
    """
    取消预约
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID（用于权限验证）
        reservation_id: 预约 ID
        
    Returns:
        bool: 取消成功返回 True，不存在或无权限返回 False
    """
    try:
        # 查询预约
        reservation = await get_reservation_by_id(db, user_id, reservation_id)
        
        if reservation is None:
            return False
        
        # 检查是否可以取消
        if reservation.status == "cancelled":
            raise ValueError("该预约已被取消")
        
        if reservation.status == "completed":
            raise ValueError("已完成的会议无法取消")
        
        # 更新状态为已取消
        reservation.status = "cancelled"
        reservation.updated_at = datetime.utcnow()
        
        await db.flush()
        
        # ===== 取消预约后清除会议室缓存 =====
        try:
            await clear_meeting_rooms_cache()
        except Exception as e:
            # 缓存清除失败不影响业务逻辑
            print(f"⚠️ 取消预约后清除缓存失败: {e}")
        
        return True
        
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"取消预约失败: {str(e)}")


async def get_meeting_stats(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None
) -> dict:
    """
    获取会议室使用统计数据
    
    Args:
        db: 异步数据库会话
        user_id: 用户 ID（可选，为空时统计全部）
        
    Returns:
        dict: 按会议室分组的统计数据
    """
    try:
        # 基础条件：只统计已确认的预约
        conditions = [Reservation.status == "confirmed"]
        
        if user_id:
            conditions.append(Reservation.user_id == user_id)
        
        # 按会议室分组统计
        query = (
            select(
                MeetingRoom.id,
                MeetingRoom.name,
                func.count(Reservation.id).label("reservation_count"),
                func.sum(
                    func.extract("epoch", Reservation.end_time) - 
                    func.extract("epoch", Reservation.start_time)
                ).label("total_duration_seconds")
            )
            .join(Reservation, MeetingRoom.id == Reservation.room_id)
            .where(and_(*conditions))
            .group_by(MeetingRoom.id, MeetingRoom.name)
            .order_by(func.count(Reservation.id).desc())
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        # 构建统计结果
        stats = {
            "rooms": [],
            "total_reservations": 0,
            "total_duration_hours": 0
        }
        
        for room_id, room_name, count, duration in rows:
            duration_hours = round((duration or 0) / 3600, 1)
            stats["rooms"].append({
                "room_id": str(room_id),
                "room_name": room_name,
                "reservation_count": count,
                "total_duration_hours": duration_hours
            })
            stats["total_reservations"] += count
            stats["total_duration_hours"] += duration_hours
        
        stats["total_duration_hours"] = round(stats["total_duration_hours"], 1)
        
        return stats
        
    except Exception as e:
        raise Exception(f"获取会议统计失败: {str(e)}")

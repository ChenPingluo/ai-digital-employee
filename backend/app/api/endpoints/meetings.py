# -*- coding: utf-8 -*-
"""
会议室预约接口模块

提供会议室查询和预约管理的 API 端点。
所有接口都需要认证。
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.meeting import (
    MeetingRoomResponse,
    MeetingRoomListResponse,
    ReservationCreate,
    ReservationResponse,
    ReservationListResponse
)
from app.services import meeting_service
from app.middleware.auth import get_current_user


# 创建路由器
router = APIRouter(prefix="/meetings", tags=["会议室预约"])


@router.get(
    "/rooms",
    response_model=MeetingRoomListResponse,
    summary="获取会议室列表",
    description="获取所有可用的会议室，支持按容量筛选"
)
async def get_rooms(
    min_capacity: int = Query(
        0,
        ge=0,
        description="最小容纳人数"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议室列表接口
    
    - **min_capacity**: 最小容纳人数筛选条件
    
    返回所有可用的会议室列表，按容量和名称排序。
    """
    try:
        rooms = await meeting_service.get_available_rooms(
            db=db,
            min_capacity=min_capacity
        )
        
        return MeetingRoomListResponse(
            items=[MeetingRoomResponse.model_validate(room) for room in rooms],
            total=len(rooms)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会议室列表失败: {str(e)}"
        )


@router.get(
    "/rooms/{room_id}",
    response_model=MeetingRoomResponse,
    summary="获取会议室详情",
    description="根据 ID 获取会议室详细信息"
)
async def get_room(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议室详情接口
    
    - **room_id**: 会议室 ID
    """
    try:
        room = await meeting_service.get_room_by_id(
            db=db,
            room_id=room_id
        )
        
        if room is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会议室不存在"
            )
        
        return MeetingRoomResponse.model_validate(room)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会议室详情失败: {str(e)}"
        )


@router.post(
    "/reservations",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建预约",
    description="预约会议室，包含时间冲突检测"
)
async def create_reservation(
    reservation_data: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建会议室预约接口
    
    - **room_id**: 要预约的会议室 ID
    - **title**: 会议主题
    - **start_time**: 开始时间
    - **end_time**: 结束时间
    
    自动检测时间冲突，如有冲突返回 400 错误。
    """
    try:
        reservation = await meeting_service.create_reservation(
            db=db,
            user_id=current_user.id,
            reservation_data=reservation_data
        )
        
        return ReservationResponse.model_validate(reservation)
        
    except ValueError as e:
        # 业务验证错误（如时间冲突）
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建预约失败: {str(e)}"
        )


@router.get(
    "/reservations",
    response_model=ReservationListResponse,
    summary="获取我的预约",
    description="获取当前用户的会议室预约记录"
)
async def get_reservations(
    include_past: bool = Query(
        False,
        description="是否包含已过期的预约"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取我的预约列表接口
    
    - **include_past**: 是否包含已过期的预约
    
    返回当前用户的预约记录，按开始时间降序排列。
    """
    try:
        reservations, total = await meeting_service.get_user_reservations(
            db=db,
            user_id=current_user.id,
            include_past=include_past,
            page=page,
            page_size=page_size
        )
        
        return ReservationListResponse(
            items=[
                ReservationResponse.model_validate(r) for r in reservations
            ],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预约列表失败: {str(e)}"
        )


@router.get(
    "/reservations/{reservation_id}",
    response_model=ReservationResponse,
    summary="获取预约详情",
    description="根据 ID 获取预约详细信息"
)
async def get_reservation(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取预约详情接口
    
    - **reservation_id**: 预约 ID
    """
    try:
        reservation = await meeting_service.get_reservation_by_id(
            db=db,
            user_id=current_user.id,
            reservation_id=reservation_id
        )
        
        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="预约不存在或无权访问"
            )
        
        return ReservationResponse.model_validate(reservation)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预约详情失败: {str(e)}"
        )


@router.delete(
    "/reservations/{reservation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="取消预约",
    description="取消指定的会议室预约"
)
async def cancel_reservation(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取消预约接口
    
    - **reservation_id**: 预约 ID
    
    取消成功返回 204 No Content
    """
    try:
        success = await meeting_service.cancel_reservation(
            db=db,
            user_id=current_user.id,
            reservation_id=reservation_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="预约不存在或无权取消"
            )
        
        return None
        
    except ValueError as e:
        # 业务验证错误（如预约已取消）
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消预约失败: {str(e)}"
        )

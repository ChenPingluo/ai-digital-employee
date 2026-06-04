# -*- coding: utf-8 -*-
"""
提醒推送接口模块

提供提醒查询和 SSE 推送能力。
"""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.middleware.auth import get_current_user
from app.models import User
from app.schemas.notification import ReminderListResponse, ReminderResponse
from app.services.reminder_service import get_pending_reminders

logger = logging.getLogger(__name__)

STREAM_POLL_INTERVAL_SECONDS = 30

router = APIRouter(prefix="/notifications", tags=["提醒推送"])


@router.get(
    "/pending",
    response_model=ReminderListResponse,
    summary="获取当前提醒",
    description="获取当前用户待处理的提醒列表"
)
async def get_current_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的提醒列表。"""
    try:
        items = await get_pending_reminders(db, current_user.id)
        return ReminderListResponse(
            items=[ReminderResponse.model_validate(item) for item in items],
            generated_at=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提醒失败: {str(e)}"
        )


@router.get(
    "/stream",
    summary="流式提醒推送",
    description="使用 Server-Sent Events (SSE) 持续推送待办和会议提醒"
)
async def stream_reminders(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """基于 SSE 的提醒推送接口。"""
    user_id = current_user.id

    async def event_generator():
        sent_reminder_ids: set[str] = set()

        try:
            while True:
                if await request.is_disconnected():
                    logger.info("提醒流连接已断开: user_id=%s", user_id)
                    break

                async with async_session_maker() as session:
                    reminders = await get_pending_reminders(session, user_id)

                for item in reminders:
                    reminder = ReminderResponse.model_validate(item)
                    if reminder.reminder_id in sent_reminder_ids:
                        continue

                    sent_reminder_ids.add(reminder.reminder_id)
                    payload = json.dumps(
                        {
                            "type": "reminder",
                            "item": reminder.model_dump(mode="json"),
                        },
                        ensure_ascii=False
                    )
                    yield f"data: {payload}\n\n"

                heartbeat = datetime.utcnow().isoformat()
                yield f": keepalive {heartbeat}\n\n"
                await asyncio.sleep(STREAM_POLL_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("提醒流任务被取消: user_id=%s", user_id)
            raise
        except Exception as e:
            logger.error("提醒流处理失败: user_id=%s error=%s", user_id, str(e))
            error_payload = json.dumps(
                {
                    "type": "error",
                    "message": "提醒流处理失败",
                },
                ensure_ascii=False
            )
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

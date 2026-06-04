# -*- coding: utf-8 -*-
"""
提醒服务模块

基于待办事项截止时间和会议预约开始时间生成提醒事件。
支持在会议提醒中追加天气联动提示。
"""

import math
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Reservation, Todo
from app.services.weather_service import get_weather

TODO_REMINDER_LEAD_MINUTES = 30
TODO_OVERDUE_LOOKBACK_MINUTES = 60
MEETING_REMINDER_LEAD_MINUTES = 15
MEETING_STARTED_LOOKBACK_MINUTES = 10
HOT_TEMPERATURE_THRESHOLD = 35
COLD_TEMPERATURE_THRESHOLD = 5
HIGH_WIND_LEVEL_THRESHOLD = 6
SEVERITY_RANK = {
    "info": 0,
    "warning": 1,
    "error": 2,
}


def _utc_now() -> datetime:
    """返回 UTC 当前时间。"""
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime) -> datetime:
    """
    统一时间对象的时区表现。

    若数据库中存在无时区时间，则默认按 UTC 处理，避免比较时报错。
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _minutes_until(target_time: datetime, now: datetime) -> int:
    """计算目标时间与当前时间的分钟差，逾期时返回负数。"""
    delta_seconds = (_normalize_datetime(target_time) - _normalize_datetime(now)).total_seconds()
    if delta_seconds == 0:
        return 0
    rounded_minutes = math.ceil(abs(delta_seconds) / 60)
    return rounded_minutes if delta_seconds > 0 else -rounded_minutes


def _merge_severity(base: str, extra: str) -> str:
    """返回更高优先级的提醒级别。"""
    if SEVERITY_RANK.get(extra, 0) > SEVERITY_RANK.get(base, 0):
        return extra
    return base


def _parse_temperature(value: object) -> Optional[int]:
    """从天气温度字段中提取整数温度。"""
    if value is None:
        return None

    match = re.search(r"-?\d+", str(value))
    if not match:
        return None

    return int(match.group())


def _parse_wind_level(value: str) -> Optional[int]:
    """从风力描述中提取最高风级。"""
    if not value:
        return None

    matches = re.findall(r"\d+", value)
    if not matches:
        return None

    return max(int(item) for item in matches)


def _build_weather_context(weather_data: dict) -> Optional[dict]:
    """
    将天气数据转换为会议提醒可用的天气提示。

    仅在识别到降雨、低能见度、大风、极端高低温等情况时返回结果。
    """
    if not weather_data.get("success", False):
        return None

    weather_text = str(weather_data.get("weather") or "").strip()
    temperature_text = str(weather_data.get("temperature") or "").strip()
    wind_power = str(weather_data.get("wind_power") or "").strip()
    city = str(weather_data.get("city") or settings.WEATHER_REMINDER_CITY).strip()

    advice_parts: List[str] = []
    severity = "info"

    if any(keyword in weather_text for keyword in ["暴雨", "大暴雨", "雷", "冰雹", "台风"]):
        advice_parts.append("建议尽量提前出发，必要时调整出行方式")
        severity = _merge_severity(severity, "error")
    elif any(keyword in weather_text for keyword in ["雨", "雪", "雨夹雪"]):
        advice_parts.append("建议携带雨具并预留通勤时间")
        severity = _merge_severity(severity, "warning")

    if any(keyword in weather_text for keyword in ["雾", "霾", "沙"]):
        advice_parts.append("能见度较低，建议提前出发并注意路况")
        severity = _merge_severity(severity, "warning")

    wind_level = _parse_wind_level(wind_power)
    if "大风" in weather_text or (wind_level is not None and wind_level >= HIGH_WIND_LEVEL_THRESHOLD):
        advice_parts.append("外出注意防风，尽量减少户外停留")
        severity = _merge_severity(severity, "warning")

    temperature = _parse_temperature(temperature_text)
    if temperature is not None and temperature >= HOT_TEMPERATURE_THRESHOLD:
        advice_parts.append("气温较高，注意补水防晒")
        severity = _merge_severity(severity, "warning")
    elif temperature is not None and temperature <= COLD_TEMPERATURE_THRESHOLD:
        advice_parts.append("气温较低，注意保暖")
        severity = _merge_severity(severity, "warning")

    if not advice_parts:
        return None

    advice = "；".join(dict.fromkeys(advice_parts))
    return {
        "city": city,
        "weather": weather_text or "未知",
        "temperature": temperature_text or "N/A",
        "wind_power": wind_power,
        "advice": advice,
        "severity": severity,
    }


def _append_weather_message(message: str, weather_context: dict) -> str:
    """将天气联动提示拼接到原始会议提醒文案中。"""
    city = weather_context.get("city", settings.WEATHER_REMINDER_CITY)
    weather = weather_context.get("weather", "未知")
    temperature = weather_context.get("temperature", "N/A")

    weather_snapshot = f"当前{city}天气为{weather}"
    if temperature and temperature != "N/A":
        weather_snapshot += f"，气温 {temperature}°C"

    return f"{message} {weather_snapshot}，{weather_context['advice']}。"


def _build_todo_reminder(todo: Todo, now: datetime) -> dict:
    """将待办事项转换为提醒事件。"""
    due_date = _normalize_datetime(todo.due_date)
    minutes_until = _minutes_until(due_date, now)

    if minutes_until < 0:
        reminder_type = "todo_overdue"
        title = "待办已逾期"
        message = f"待办「{todo.title}」已逾期 {abs(minutes_until)} 分钟。"
        severity = "error"
    elif minutes_until == 0:
        reminder_type = "todo_due_soon"
        title = "待办马上到期"
        message = f"待办「{todo.title}」已到截止时间，请尽快处理。"
        severity = "warning"
    else:
        reminder_type = "todo_due_soon"
        title = "待办即将到期"
        message = f"待办「{todo.title}」将在 {minutes_until} 分钟后到期。"
        severity = "warning" if todo.priority >= 2 else "info"

    return {
        "reminder_id": f"todo:{todo.id}:{reminder_type}:{due_date.isoformat()}",
        "type": reminder_type,
        "source_type": "todo",
        "source_id": str(todo.id),
        "title": title,
        "message": message,
        "event_time": due_date,
        "minutes_until": minutes_until,
        "severity": severity,
        "metadata": {
            "status": todo.status,
            "priority": str(todo.priority),
        },
    }


def _build_meeting_reminder(
    reservation: Reservation,
    now: datetime,
    weather_context: Optional[dict] = None
) -> dict:
    """将会议预约转换为提醒事件。"""
    start_time = _normalize_datetime(reservation.start_time)
    minutes_until = _minutes_until(start_time, now)
    room_name = reservation.room.name if reservation.room else "未指定会议室"

    if minutes_until <= 0:
        title = "会议已经开始"
        message = f"会议「{reservation.title}」已经开始，地点：{room_name}。"
        severity = "warning"
    else:
        title = "会议即将开始"
        message = f"会议「{reservation.title}」将在 {minutes_until} 分钟后开始，地点：{room_name}。"
        severity = "warning" if minutes_until <= 5 else "info"
        if weather_context is not None:
            message = _append_weather_message(message, weather_context)
            severity = _merge_severity(severity, weather_context["severity"])

    metadata = {
        "room_name": room_name,
        "status": reservation.status,
    }
    if weather_context is not None and minutes_until > 0:
        metadata.update(
            {
                "weather_city": str(weather_context.get("city", "")),
                "weather": str(weather_context.get("weather", "")),
                "temperature": str(weather_context.get("temperature", "")),
                "weather_advice": str(weather_context.get("advice", "")),
            }
        )

    return {
        "reminder_id": f"reservation:{reservation.id}:meeting_starting:{start_time.isoformat()}",
        "type": "meeting_starting",
        "source_type": "reservation",
        "source_id": str(reservation.id),
        "title": title,
        "message": message,
        "event_time": start_time,
        "minutes_until": minutes_until,
        "severity": severity,
        "metadata": metadata,
    }


async def get_pending_reminders(
    db: AsyncSession,
    user_id: uuid.UUID
) -> List[dict]:
    """
    获取当前用户待处理的提醒事件列表。

    当前规则：
    - 待办：截止前 30 分钟内，或逾期 60 分钟内
    - 会议：开始前 15 分钟内，或开始后 10 分钟内
    """
    now = _utc_now()

    todo_window_end = now + timedelta(minutes=TODO_REMINDER_LEAD_MINUTES)
    todo_window_start = now - timedelta(minutes=TODO_OVERDUE_LOOKBACK_MINUTES)
    todo_result = await db.execute(
        select(Todo)
        .where(
            and_(
                Todo.user_id == user_id,
                Todo.status.in_(["pending", "in_progress"]),
                Todo.due_date.isnot(None),
                Todo.due_date >= todo_window_start,
                Todo.due_date <= todo_window_end,
            )
        )
        .order_by(Todo.due_date.asc(), Todo.priority.desc())
    )
    todos = todo_result.scalars().all()

    meeting_window_end = now + timedelta(minutes=MEETING_REMINDER_LEAD_MINUTES)
    meeting_window_start = now - timedelta(minutes=MEETING_STARTED_LOOKBACK_MINUTES)
    reservation_result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.room))
        .where(
            and_(
                Reservation.user_id == user_id,
                Reservation.status == "confirmed",
                Reservation.end_time > now,
                Reservation.start_time >= meeting_window_start,
                Reservation.start_time <= meeting_window_end,
            )
        )
        .order_by(Reservation.start_time.asc())
    )
    reservations = reservation_result.scalars().all()

    meeting_weather_context = None
    should_load_weather = (
        settings.SCHEDULE_WEATHER_REMINDER_ENABLED
        and bool((settings.WEATHER_REMINDER_CITY or "").strip())
        and any(_minutes_until(reservation.start_time, now) > 0 for reservation in reservations)
    )
    if should_load_weather:
        try:
            weather_data = await get_weather(settings.WEATHER_REMINDER_CITY)
            meeting_weather_context = _build_weather_context(weather_data)
        except Exception:
            meeting_weather_context = None

    reminders = [
        _build_todo_reminder(todo, now)
        for todo in todos
        if todo.due_date is not None
    ]
    reminders.extend(
        _build_meeting_reminder(reservation, now, meeting_weather_context)
        for reservation in reservations
    )
    reminders.sort(key=lambda item: item["event_time"])

    return reminders

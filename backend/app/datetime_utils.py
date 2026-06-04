# -*- coding: utf-8 -*-
"""
时间处理工具模块

统一处理用户输入的日期时间，默认将无时区时间解释为北京时间。
"""

from datetime import datetime, timedelta, timezone


BEIJING_TZ = timezone(timedelta(hours=8))


def normalize_user_datetime(value: datetime) -> datetime:
    """
    规范化用户输入时间。

    - 无时区时间：按北京时间解释，再转换为 UTC
    - 有时区时间：统一转换为 UTC
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TZ)
    return value.astimezone(timezone.utc)


def parse_user_datetime(value: str) -> datetime:
    """
    解析 ISO 时间字符串，并按用户语义做时区归一化。
    """
    parsed_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return normalize_user_datetime(parsed_value)


def to_beijing_time(value: datetime) -> datetime:
    """
    将时间统一转换为北京时间，用于界面和文本展示。
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BEIJING_TZ)

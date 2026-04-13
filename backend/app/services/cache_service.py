# -*- coding: utf-8 -*-
"""
Redis 缓存服务模块

提供统一的缓存读写接口，支持：
- 天气数据缓存（TTL 30分钟）
- 会议室列表缓存（TTL 5分钟）
- 用户会话上下文缓存（TTL 2小时）

特性：
- 异步 Redis 连接（使用 redis.asyncio）
- JSON 序列化/反序列化
- 连接失败时降级处理（不影响主业务）
- 完整的生命周期管理
"""

import json
from typing import Optional, Any, List
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.config import settings


# ==================== 全局 Redis 连接实例 ====================
# Redis 异步连接池，在应用启动时初始化
_redis_client: Optional[aioredis.Redis] = None


# ==================== 缓存 TTL 常量定义 ====================
# 天气数据缓存 TTL：30分钟
WEATHER_CACHE_TTL = 30 * 60

# 会议室列表缓存 TTL：5分钟
MEETING_ROOM_CACHE_TTL = 5 * 60

# 用户会话上下文缓存 TTL：2小时
SESSION_CONTEXT_CACHE_TTL = 2 * 60 * 60

# 默认缓存 TTL：5分钟
DEFAULT_CACHE_TTL = 5 * 60


async def init_redis() -> bool:
    """
    初始化 Redis 异步连接
    
    在应用启动时调用，创建 Redis 连接池。
    连接失败时不会抛出异常，只记录警告日志。
    
    Returns:
        bool: 连接成功返回 True，失败返回 False
    """
    global _redis_client
    
    try:
        # 创建 Redis 异步连接
        # decode_responses=True 自动将字节解码为字符串
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            # 连接超时时间（秒）
            socket_connect_timeout=5,
            # 操作超时时间（秒）
            socket_timeout=5,
            # 连接池最大连接数
            max_connections=20,
            # 健康检查间隔（秒）
            health_check_interval=30
        )
        
        # 测试连接是否正常
        await _redis_client.ping()
        print("✅ Redis 缓存服务连接成功")
        return True
        
    except RedisError as e:
        print(f"⚠️ Redis 连接失败，缓存功能将被禁用: {e}")
        _redis_client = None
        return False
    except Exception as e:
        print(f"⚠️ Redis 初始化异常: {e}")
        _redis_client = None
        return False


async def close_redis() -> None:
    """
    关闭 Redis 连接
    
    在应用关闭时调用，释放 Redis 连接资源。
    """
    global _redis_client
    
    if _redis_client is not None:
        try:
            await _redis_client.close()
            print("✅ Redis 连接已关闭")
        except Exception as e:
            print(f"⚠️ Redis 关闭异常: {e}")
        finally:
            _redis_client = None


def is_redis_available() -> bool:
    """
    检查 Redis 是否可用
    
    Returns:
        bool: Redis 连接可用返回 True，否则返回 False
    """
    return _redis_client is not None


async def get_cache(key: str) -> Optional[str]:
    """
    获取缓存值
    
    从 Redis 中获取指定 key 的缓存值。
    Redis 不可用或操作失败时返回 None（降级处理）。
    
    Args:
        key: 缓存键名
        
    Returns:
        Optional[str]: 缓存值，不存在或失败时返回 None
    """
    if _redis_client is None:
        return None
    
    try:
        value = await _redis_client.get(key)
        return value
    except RedisError as e:
        # Redis 操作失败时降级，不影响主业务
        print(f"⚠️ Redis GET 操作失败 [{key}]: {e}")
        return None
    except Exception as e:
        print(f"⚠️ 缓存读取异常 [{key}]: {e}")
        return None


async def set_cache(key: str, value: str, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    设置缓存值
    
    将值存入 Redis 并设置过期时间。
    Redis 不可用或操作失败时返回 False（降级处理）。
    
    Args:
        key: 缓存键名
        value: 缓存值（字符串）
        ttl: 过期时间（秒），默认5分钟
        
    Returns:
        bool: 操作成功返回 True，失败返回 False
    """
    if _redis_client is None:
        return False
    
    try:
        await _redis_client.set(key, value, ex=ttl)
        return True
    except RedisError as e:
        # Redis 操作失败时降级，不影响主业务
        print(f"⚠️ Redis SET 操作失败 [{key}]: {e}")
        return False
    except Exception as e:
        print(f"⚠️ 缓存写入异常 [{key}]: {e}")
        return False


async def delete_cache(key: str) -> bool:
    """
    删除缓存
    
    从 Redis 中删除指定 key 的缓存。
    
    Args:
        key: 缓存键名
        
    Returns:
        bool: 操作成功返回 True，失败返回 False
    """
    if _redis_client is None:
        return False
    
    try:
        await _redis_client.delete(key)
        return True
    except RedisError as e:
        print(f"⚠️ Redis DELETE 操作失败 [{key}]: {e}")
        return False
    except Exception as e:
        print(f"⚠️ 缓存删除异常 [{key}]: {e}")
        return False


async def delete_pattern(pattern: str) -> int:
    """
    按模式批量删除缓存
    
    使用 SCAN 命令匹配并删除符合模式的所有缓存键。
    使用 SCAN 而不是 KEYS 命令，避免阻塞 Redis。
    
    Args:
        pattern: 匹配模式（如 "meeting_rooms:*"）
        
    Returns:
        int: 删除的键数量
    """
    if _redis_client is None:
        return 0
    
    try:
        deleted_count = 0
        # 使用 SCAN 命令迭代匹配的键，避免 KEYS 命令阻塞
        cursor = 0
        while True:
            cursor, keys = await _redis_client.scan(
                cursor=cursor,
                match=pattern,
                count=100  # 每次扫描的数量
            )
            
            if keys:
                # 批量删除匹配的键
                await _redis_client.delete(*keys)
                deleted_count += len(keys)
            
            # cursor 为 0 表示扫描完成
            if cursor == 0:
                break
        
        return deleted_count
        
    except RedisError as e:
        print(f"⚠️ Redis 批量删除失败 [{pattern}]: {e}")
        return 0
    except Exception as e:
        print(f"⚠️ 批量删除缓存异常 [{pattern}]: {e}")
        return 0


# ==================== JSON 序列化缓存操作 ====================

async def get_cache_json(key: str) -> Optional[Any]:
    """
    获取 JSON 格式的缓存值
    
    从 Redis 获取值并自动反序列化为 Python 对象。
    
    Args:
        key: 缓存键名
        
    Returns:
        Optional[Any]: 反序列化后的对象，失败时返回 None
    """
    value = await get_cache(key)
    
    if value is None:
        return None
    
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        print(f"⚠️ 缓存 JSON 解析失败 [{key}]: {e}")
        return None


async def set_cache_json(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    设置 JSON 格式的缓存值
    
    将 Python 对象序列化为 JSON 后存入 Redis。
    
    Args:
        key: 缓存键名
        value: 要缓存的对象（可 JSON 序列化）
        ttl: 过期时间（秒）
        
    Returns:
        bool: 操作成功返回 True，失败返回 False
    """
    try:
        json_str = json.dumps(value, ensure_ascii=False)
        return await set_cache(key, json_str, ttl)
    except (TypeError, ValueError) as e:
        print(f"⚠️ 缓存 JSON 序列化失败 [{key}]: {e}")
        return False


# ==================== 便捷缓存函数 ====================

async def get_weather_cache(city: str) -> Optional[dict]:
    """
    获取天气数据缓存
    
    Args:
        city: 城市名称
        
    Returns:
        Optional[dict]: 缓存的天气数据
    """
    cache_key = f"weather:{city}"
    return await get_cache_json(cache_key)


async def set_weather_cache(city: str, weather_data: dict) -> bool:
    """
    设置天气数据缓存
    
    Args:
        city: 城市名称
        weather_data: 天气数据字典
        
    Returns:
        bool: 操作成功返回 True
    """
    cache_key = f"weather:{city}"
    return await set_cache_json(cache_key, weather_data, WEATHER_CACHE_TTL)


async def get_meeting_rooms_cache(min_capacity: int = 0) -> Optional[List[dict]]:
    """
    获取可用会议室列表缓存
    
    Args:
        min_capacity: 最小容纳人数
        
    Returns:
        Optional[List[dict]]: 缓存的会议室列表
    """
    cache_key = f"meeting_rooms:available:{min_capacity}"
    return await get_cache_json(cache_key)


async def set_meeting_rooms_cache(min_capacity: int, rooms_data: List[dict]) -> bool:
    """
    设置可用会议室列表缓存
    
    Args:
        min_capacity: 最小容纳人数
        rooms_data: 会议室数据列表
        
    Returns:
        bool: 操作成功返回 True
    """
    cache_key = f"meeting_rooms:available:{min_capacity}"
    return await set_cache_json(cache_key, rooms_data, MEETING_ROOM_CACHE_TTL)


async def clear_meeting_rooms_cache() -> int:
    """
    清除所有会议室相关缓存
    
    在创建/取消预约后调用，确保缓存数据一致性。
    
    Returns:
        int: 清除的缓存键数量
    """
    return await delete_pattern("meeting_rooms:*")


async def get_session_context(user_id: str, session_id: str) -> Optional[dict]:
    """
    获取用户会话上下文缓存
    
    Args:
        user_id: 用户 ID
        session_id: 会话 ID
        
    Returns:
        Optional[dict]: 缓存的会话上下文
    """
    cache_key = f"session:{user_id}:{session_id}"
    return await get_cache_json(cache_key)


async def set_session_context(
    user_id: str,
    session_id: str,
    context: dict
) -> bool:
    """
    设置用户会话上下文缓存
    
    Args:
        user_id: 用户 ID
        session_id: 会话 ID
        context: 会话上下文字典
        
    Returns:
        bool: 操作成功返回 True
    """
    cache_key = f"session:{user_id}:{session_id}"
    return await set_cache_json(cache_key, context, SESSION_CONTEXT_CACHE_TTL)

# -*- coding: utf-8 -*-
"""
限流器模块

提供基于 Redis 的分布式限流和内存限流两种实现。
支持滑动窗口算法，适用于多进程部署场景。

特性：
- Redis 滑动窗口算法实现限流）
- 单用户限流（默认10次/秒）和全局限流（默认500次/秒）
- FastAPI 中间件和依赖注入两种使用方式
- Redis 不可用时自动降级为内存限流
"""

import time
from collections import defaultdict
from functools import wraps
from threading import Lock
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.config import settings


class MemoryRateLimiter:
    """
    内存限流器
    
    基于滑动窗口算法实现的简单限流器，使用内存存储请求记录。
    线程安全，但不支持多进程或分布式部署。
    当 Redis 不可用时作为降级方案。
    
    Attributes:
        requests: 存储每个 IP 的请求时间戳列表
        lock: 线程锁，确保并发安全
        max_requests: 时间窗口内允许的最大请求数
        window_seconds: 时间窗口大小（秒）
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        """
        初始化限流器
        
        Args:
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        # 使用 defaultdict 自动为新 IP 创建空列表
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = Lock()
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def _clean_old_requests(self, ip: str, current_time: float) -> None:
        """
        清理过期的请求记录
        
        Args:
            ip: 客户端 IP 地址
            current_time: 当前时间戳
        """
        # 计算窗口开始时间
        window_start = current_time - self.window_seconds
        
        # 保留窗口内的请求记录
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > window_start
        ]
    
    def is_allowed(self, ip: str) -> Tuple[bool, int]:
        """
        检查指定 IP 是否允许请求
        
        Args:
            ip: 客户端 IP 地址
            
        Returns:
            Tuple[bool, int]: (是否允许, 剩余配额)
        """
        current_time = time.time()
        
        with self.lock:
            # 清理过期记录
            self._clean_old_requests(ip, current_time)
            
            # 获取当前窗口内的请求数
            request_count = len(self.requests[ip])
            
            if request_count >= self.max_requests:
                # 超过限制
                return False, 0
            
            # 记录本次请求
            self.requests[ip].append(current_time)
            
            # 返回剩余配额
            remaining = self.max_requests - request_count - 1
            return True, remaining
    
    def get_reset_time(self, ip: str) -> int:
        """
        获取限流重置剩余时间（秒）
        
        Args:
            ip: 客户端 IP 地址
            
        Returns:
            int: 距离限流重置的剩余秒数
        """
        if ip not in self.requests or not self.requests[ip]:
            return 0
        
        # 获取最早的请求时间
        oldest_request = min(self.requests[ip])
        reset_time = oldest_request + self.window_seconds - time.time()
        
        return max(0, int(reset_time))
    
    def clear(self, ip: str = None) -> None:
        """
        清除限流记录
        
        Args:
            ip: 要清除的 IP 地址，为 None 时清除所有记录
        """
        with self.lock:
            if ip:
                if ip in self.requests:
                    del self.requests[ip]
            else:
                self.requests.clear()

class RedisRateLimiter:
    """
    Redis 限流器
    
    基于 Redis 实现的分布式限流器，使用滑动窗口算法。
    支持多进程、多服务器部署场景。
    
    实现原理：
    - 使用 Redis Sorted Set 存储请求时间戳
    - Score 为请求时间戳，Member 为唯一标识
    - 通过 ZREMRANGEBYSCORE 清理过期记录
    - 通过 ZCARD 获取当前窗口内的请求数
    """
    
    def __init__(
        self,
        redis_client: aioredis.Redis,
        key_prefix: str = "rate_limit",
        max_requests: int = 100,
        window_seconds: int = 1
    ):
        """
        初始化 Redis 限流器
        
        Args:
            redis_client: Redis 异步客户端
            key_prefix: Redis key 前缀
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        检查指定标识是否允许请求
        
        使用 Redis 事务确保原子性操作。
        
        Args:
            identifier: 请求标识（如 IP 地址或用户 ID）
            
        Returns:
            Tuple[bool, int]: (是否允许, 剩余配额)
        """
        # 构建 Redis key
        key = f"{self.key_prefix}:{identifier}"
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # 使用 pipeline 执行多个命令
        pipe = self.redis.pipeline()
        
        # 移除过期的请求记录
        pipe.zremrangebyscore(key, "-inf", window_start)
        
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        
        # 添加当前请求
        # 使用时间戳+微秒作为 member 确保唯一性
        member = f"{current_time:.6f}"
        pipe.zadd(key, {member: current_time})
        
        # 设置 key 过期时间（窗口大小的两倍，确保数据自动清理）
        pipe.expire(key, self.window_seconds * 2)
        
        # 执行事务
        results = await pipe.execute()
        
        # results[1] 是 ZCARD 的结果
        current_count = results[1]
        
        if current_count >= self.max_requests:
            # 超过限制，移除刚添加的请求
            await self.redis.zrem(key, member)
            return False, 0
        
        remaining = self.max_requests - current_count - 1
        return True, remaining
    
    async def get_current_count(self, identifier: str) -> int:
        """
        获取当前窗口内的请求数
        
        Args:
            identifier: 请求标识
            
        Returns:
            int: 当前请求数
        """
        key = f"{self.key_prefix}:{identifier}"
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # 移除过期记录
        await self.redis.zremrangebyscore(key, "-inf", window_start)
        
        # 获取当前数量
        count = await self.redis.zcard(key)
        return count or 0

# 内存限流器
# 默认配置：每分钟 100 次请求
default_memory_limiter = MemoryRateLimiter(max_requests=100, window_seconds=60)

# API 接口限流器：每分钟 60 次请求
api_memory_limiter = MemoryRateLimiter(max_requests=60, window_seconds=60)

# 认证接口限流器：每分钟 10 次请求
auth_memory_limiter = MemoryRateLimiter(max_requests=10, window_seconds=60)

# AI 对话接口限流器：每分钟 20 次请求
chat_memory_limiter = MemoryRateLimiter(max_requests=20, window_seconds=60)

# Redis 限流器实例
_redis_user_limiter: Optional[RedisRateLimiter] = None
_redis_global_limiter: Optional[RedisRateLimiter] = None
_redis_client: Optional[aioredis.Redis] = None


async def init_rate_limiters(redis_client: aioredis.Redis) -> bool:
    """
    初始化 Redis 限流器
    
    在应用启动时调用，创建 Redis 限流器实例。
    
    Args:
        redis_client: Redis 异步客户端实例
        
    Returns:
        bool: 初始化成功返回 True
    """
    global _redis_user_limiter, _redis_global_limiter, _redis_client
    
    try:
        _redis_client = redis_client
        
        # 单用户限流器：每秒 10 次请求
        _redis_user_limiter = RedisRateLimiter(
            redis_client=redis_client,
            key_prefix="rate_limit:user",
            max_requests=settings.RATE_LIMIT_PER_USER,
            window_seconds=1
        )
        
        # 全局限流器：每秒 500 次请求
        _redis_global_limiter = RedisRateLimiter(
            redis_client=redis_client,
            key_prefix="rate_limit:global",
            max_requests=settings.RATE_LIMIT_GLOBAL,
            window_seconds=1
        )
        
        print("Redis 限流器初始化成功")
        return True
        
    except Exception as e:
        print(f"Redis 限流器初始化失败: {e}")
        return False


def is_redis_limiter_available() -> bool:
    """
    检查 Redis 限流器是否可用
    
    Returns:
        bool: Redis 限流器可用返回 True
    """
    return _redis_user_limiter is not None and _redis_global_limiter is not None


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP 地址
    
    优先从代理头中获取原始 IP，支持 X-Forwarded-For 和 X-Real-IP 头。
    
    Args:
        request: FastAPI Request 对象
        
    Returns:
        str: 客户端 IP 地址
    """
    # 优先从代理头获取
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 直接使用客户端 IP
    if request.client:
        return request.client.host
    
    return "unknown"

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 限流中间件
    
    在请求处理前进行限流检查，支持：
    - 单用户限流
    - 全局限流
    - Redis 不可用时自动降级到内存限流
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        中间件处理逻辑
        
        Args:
            request: HTTP 请求对象
            call_next: 下一个处理函数
            
        Returns:
            Response: HTTP 响应对象
        """
        # 跳过健康检查等路径
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # 获取客户端 IP
        client_ip = get_client_ip(request)
        
        if is_redis_limiter_available():
            try:
                # 检查全局限流
                global_allowed, _ = await _redis_global_limiter.is_allowed("all")
                if not global_allowed:
                    return self._create_rate_limit_response("服务器繁忙，请稍后重试", 1)
                
                # 检查单用户限流
                user_allowed, remaining = await _redis_user_limiter.is_allowed(client_ip)
                if not user_allowed:
                    return self._create_rate_limit_response("请求过于频繁，请稍后再试", 1)
                
                # 请求通过，继续处理
                response = await call_next(request)
                
                # 添加限流相关响应头
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_USER)
                
                return response
                
            except RedisError as e:
                # Redis 异常，降级到内存限流
                print(f"Redis 限流异常，降级到内存限流: {e}")
        
        allowed, remaining = default_memory_limiter.is_allowed(client_ip)
        
        if not allowed:
            reset_time = default_memory_limiter.get_reset_time(client_ip)
            return self._create_rate_limit_response("请求过于频繁，请稍后再试", reset_time)
        
        # 请求通过，继续处理
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _create_rate_limit_response(self, message: str, retry_after: int) -> Response:
        """
        创建限流响应
        
        Args:
            message: 错误消息
            retry_after: 重试等待时间
            
        Returns:
            Response: 429 响应对象
        """
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "status": "error",
                "code": 429,
                "message": message,
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Remaining": "0"
            }
        )

async def check_rate_limit(
    request: Request,
    limiter: MemoryRateLimiter = default_memory_limiter,
    error_message: str = "请求过于频繁，请稍后再试"
) -> None:
    """
    检查请求是否超过限流（用于依赖注入）
    
    优先使用 Redis 限流，Redis 不可用时降级到内存限流。
    
    Args:
        request: FastAPI Request 对象
        limiter: 备用内存限流器实例
        error_message: 超过限制时的错误消息
        
    Raises:
        HTTPException: 超过限制时抛出 429 错误
    """
    client_ip = get_client_ip(request)
    
    # 尝试使用 Redis 限流
    if is_redis_limiter_available():
        try:
            # 检查单用户限流
            allowed, _ = await _redis_user_limiter.is_allowed(client_ip)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"message": error_message, "retry_after": 1},
                    headers={"Retry-After": "1", "X-RateLimit-Remaining": "0"}
                )
            return
            
        except HTTPException:
            raise
        except RedisError as e:
            # Redis 异常，降级到内存限流
            print(f"Redis 限流检查异常，降级到内存限流: {e}")
    
    # 降级：使用内存限流
    allowed, remaining = limiter.is_allowed(client_ip)
    
    if not allowed:
        reset_time = limiter.get_reset_time(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": error_message, "retry_after": reset_time},
            headers={"Retry-After": str(reset_time), "X-RateLimit-Remaining": "0"}
        )


def rate_limit(
    limiter: MemoryRateLimiter = default_memory_limiter,
    error_message: str = "请求过于频繁，请稍后再试"
):
    """
    限流装饰器工厂函数
    
    用于装饰 FastAPI 路由处理函数，实现请求频率限制。
    优先使用 Redis 限流，Redis 不可用时降级到内存限流。
    
    Args:
        limiter: 备用内存限流器实例
        error_message: 超过限制时的错误消息
        
    Returns:
        装饰器函数
        
    Example:
        ```python
        @app.get("/api/resource")
        @rate_limit(limiter=api_memory_limiter)
        async def get_resource(request: Request):
            return {"data": "resource"}
        ```
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取 Request 对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request is None:
                request = kwargs.get("request")
            
            if request is None:
                # 如果没有找到 Request 对象，直接执行函数
                return await func(*args, **kwargs)
            
            # 获取客户端 IP
            client_ip = get_client_ip(request)
            
            # 尝试使用 Redis 限流
            if is_redis_limiter_available():
                try:
                    allowed, _ = await _redis_user_limiter.is_allowed(client_ip)
                    if not allowed:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail={"message": error_message, "retry_after": 1},
                            headers={"Retry-After": "1", "X-RateLimit-Remaining": "0"}
                        )
                    return await func(*args, **kwargs)
                    
                except HTTPException:
                    raise
                except RedisError as e:
                    print(f"Redis 限流装饰器异常，降级到内存限流: {e}")
            
            # 降级：使用内存限流
            allowed, remaining = limiter.is_allowed(client_ip)
            
            if not allowed:
                reset_time = limiter.get_reset_time(client_ip)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"message": error_message, "retry_after": reset_time},
                    headers={
                        "Retry-After": str(reset_time),
                        "X-RateLimit-Remaining": "0"
                    }
                )
            
            # 执行原函数
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# 保持向后兼容，使用相同的名称
default_limiter = default_memory_limiter
api_limiter = api_memory_limiter
auth_limiter = auth_memory_limiter
chat_limiter = chat_memory_limiter

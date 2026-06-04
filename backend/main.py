# -*- coding: utf-8 -*-

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from datetime import datetime, timezone
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings
from app.database import init_db, close_db, check_db_connection
from app.services.cache_service import init_redis, close_redis, is_redis_available, check_redis
from app.middleware.rate_limiter import RateLimitMiddleware, init_rate_limiters
from redis import asyncio as aioredis
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器

    处理应用启动和关闭时的初始化和清理工作。
    """

    print("AI 数字员工后端服务启动中...")

    # 初始化数据库
    try:
        await init_db()
        print("数据库连接初始化成功")
    except Exception as e:
        print(f"数据库初始化失败: {e}")

    # 初始化 Redis 缓存服务
    redis_connected = await init_redis()

    # 初始化 Redis 限流器
    if redis_connected:
        try:
            # 创建一个新的 Redis 连接用于限流器
            redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await init_rate_limiters(redis_client)
        except Exception as e:
            print(f"限流器初始化失败，将使用内存限流: {e}")
    else:
        print("Redis 不可用，限流器将使用内存模式")

    print(f"API 文档地址: http://localhost:8000/docs")
    print(f"ReDoc 文档地址: http://localhost:8000/redoc")

    yield  # 应用运行中

    print("\n" + "=" * 50)
    print("服务关闭中，正在清理资源...")

    # 关闭数据库连接池
    try:
        await close_db()
        print("数据库连接已关闭")
    except Exception as e:
        print(f"数据库关闭异常: {e}")

    # 关闭 Redis 连接
    try:
        await close_redis()
    except Exception as e:
        print(f"Redis 关闭异常: {e}")

    print("服务已安全关闭")

app = FastAPI(
    title="AI 数字员工后端服务",
    description="""
## 企业 AI 数字员工系统后端 API

提供以下功能：

### 用户认证
- 用户注册和登录
- JWT Token 认证

### 待办事项管理
- 创建、查询、更新、删除待办事项
- 支持状态和优先级筛选

### 会议室预约
- 查询可用会议室
- 创建和取消预约
- 自动时间冲突检测

### AI 对话
- 自然语言交互
- 多智能体任务处理

### 数据统计
- 待办事项统计
- 会议室使用统计
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

# 异常处理机制
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path)
        },
        headers=exc.headers
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "code": 422,
            "message": "请求数据验证失败",
            "errors": errors,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"未处理的异常: {type(exc).__name__}: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "path": str(request.url.path)
        }
    )

app.include_router(api_router)

@app.get("/", tags=["健康检查"])
async def root():
    """
    根路径健康检查

    用于检测服务是否正常运行。
    """
    return {
        "status": "ok",
        "service": "AI 数字员工后端服务",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口

    用于负载均衡器或监控系统检测服务状态。
    返回数据库和缓存的连接状态。
    """
    #1. 检查数据库
    db_healthy = await check_db_connection()

    # 2. 检查 Redis
    redis_healthy = await check_redis()

    # 3. 综合判断
    if db_healthy and redis_healthy:
        status = "healthy"
        http_status = 200
    elif db_healthy:
        status = "degraded"  # 数据库正常，Redis挂了
        http_status = 200    # 主业务仍可用
    else:
        status = "unhealthy"  #数据库挂了，服务基本不可用
        http_status = 503     # Service Unavailable

    return JSONResponse(
        status_code=http_status,
        content={
            "status": status,
            "database": "connected" if db_healthy else "disconnected",
            "cache": "connected" if redis_healthy else "disconnected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        workers=1,
        log_level="info"
    )

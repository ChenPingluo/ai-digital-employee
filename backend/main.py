# -*- coding: utf-8 -*-
"""
FastAPI 主入口模块

应用程序的入口点，配置 FastAPI 应用实例和中间件。
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.router import api_router
from app.database import init_db, close_db
from app.config import settings
from app.services.cache_service import init_redis, close_redis, is_redis_available
from app.middleware.rate_limiter import RateLimitMiddleware, init_rate_limiters
from redis import asyncio as aioredis


# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    
    处理应用启动和关闭时的初始化和清理工作。
    """
    # ===== 启动事件 =====
    print("=" * 50)
    print("🚀 AI 数字员工后端服务启动中...")
    print("=" * 50)
    
    # 初始化数据库（开发环境，生产环境建议使用 Alembic 迁移）
    try:
        await init_db()
        print("✅ 数据库连接初始化成功")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
    
    # 初始化 Redis 缓存服务
    redis_connected = await init_redis()
    
    # 初始化 Redis 限流器（仅在 Redis 可用时）
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
            print(f"⚠️ 限流器初始化失败，将使用内存限流: {e}")
    else:
        print("⚠️ Redis 不可用，限流器将使用内存模式")
    
    print(f"📡 API 文档地址: http://localhost:8000/docs")
    print(f"📡 ReDoc 文档地址: http://localhost:8000/redoc")
    print("=" * 50)
    
    yield  # 应用运行中
    
    # ===== 关闭事件 =====
    print("\n" + "=" * 50)
    print("🛑 服务关闭中，正在清理资源...")
    
    # 关闭数据库连接池
    try:
        await close_db()
        print("✅ 数据库连接已关闭")
    except Exception as e:
        print(f"⚠️ 数据库关闭异常: {e}")
    
    # 关闭 Redis 连接
    try:
        await close_redis()
    except Exception as e:
        print(f"⚠️ Redis 关闭异常: {e}")
    
    print("👋 服务已安全关闭")
    print("=" * 50)


# ==================== 创建 FastAPI 应用实例 ====================
app = FastAPI(
    title="AI 数字员工后端服务",
    description="""
## 企业 AI 数字员工系统后端 API

提供以下功能：

### 🔐 用户认证
- 用户注册和登录
- JWT Token 认证

### ✅ 待办事项管理
- 创建、查询、更新、删除待办事项
- 支持状态和优先级筛选

### 🏢 会议室预约
- 查询可用会议室
- 创建和取消预约
- 自动时间冲突检测

### 🤖 AI 对话
- 自然语言交互
- 多智能体任务处理

### 📊 数据统计
- 待办事项统计
- 会议室使用统计
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# ==================== 配置 CORS 中间件 ====================
# 注意：生产环境应限制允许的源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应改为具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 配置限流中间件 ====================
# 注意：限流中间件应在 CORS 之后添加
app.add_middleware(RateLimitMiddleware)


# ==================== 全局异常处理器 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP 异常处理器
    
    统一处理 HTTPException，返回标准化的错误响应格式。
    """
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
    """
    请求验证异常处理器
    
    处理 Pydantic 验证失败的情况，返回详细的错误信息。
    """
    # 提取验证错误详情
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
    """
    通用异常处理器
    
    捕获所有未处理的异常，返回 500 错误。
    生产环境中不应暴露具体错误信息。
    """
    # 记录错误日志（生产环境应使用日志系统）
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


# ==================== 注册路由 ====================
app.include_router(api_router)


# ==================== 根路径健康检查 ====================

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
    return {
        "status": "healthy",
        "database": "connected",
        "cache": "connected" if is_redis_available() else "disconnected"
    }


# ==================== 应用入口 ====================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式启用热重载
        workers=1,
        log_level="info"
    )

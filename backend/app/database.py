# -*- coding: utf-8 -*-
"""
数据库连接模块

使用 SQLAlchemy 2.0 的异步引擎和会话管理。
提供异步数据库连接池和依赖注入支持。
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from sqlalchemy import text
from app.config import settings


class Base(DeclarativeBase):
    """
    SQLAlchemy ORM 基类

    所有数据库模型都应继承此类。
    使用 SQLAlchemy 2.0 的 DeclarativeBase 作为基础。
    """
    pass


# ==================== 创建异步数据库引擎 ====================
# 使用 asyncpg 驱动的 PostgreSQL 异步连接
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    # 连接池大小：同时保持的数据库连接数
    pool_size=20,
    # 最大溢出连接数：当连接池满时，允许额外创建的临时连接数
    max_overflow=30,
    # 连接池回收时间（秒）：超过此时间的连接将被回收
    pool_recycle=3600,
    # 连接前预检：从池中获取连接时检查连接是否有效
    pool_pre_ping=True,
    # 打印 SQL 语句（开发调试用，生产环境应设为 False）
    echo=False,
)



# 使用 async_sessionmaker 创建会话工厂，用于生成数据库会话
async_session_maker = async_sessionmaker(
    bind=engine,
    # 会话类型为 AsyncSession
    class_=AsyncSession,
    # 不自动提交，需要显式调用 commit()
    autocommit=False,
    # 不自动刷新，需要显式调用 flush()
    autoflush=False,
    # 查询结果过期策略：提交后不自动过期对象
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    数据库会话依赖注入生成器

    用于 FastAPI 的依赖注入系统，为每个请求提供独立的数据库会话。
    会话在请求结束时自动关闭，确保资源正确释放。
    """
    async with async_session_maker() as session:
        try:
            # 将会话提供给调用者使用
            yield session
            # 请求处理成功后提交事务
            await session.commit()
        except Exception:
            # 发生异常时回滚事务
            await session.rollback()
            raise
        finally:
            # 确保会话被正确关闭
            await session.close()


async def init_db() -> None:
    """
    初始化数据库表结构

    在应用启动时调用，创建所有已定义的数据库表。
    注意：生产环境建议使用 Alembic 进行数据库迁移管理。
    """
    async with engine.begin() as conn:
        # 创建所有继承自 Base 的模型对应的表
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    关闭数据库连接池

    在应用关闭时调用，释放所有数据库连接资源。
    """
    await engine.dispose()

async def check_db_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"数据库健康检查失败: {e}")
        return False

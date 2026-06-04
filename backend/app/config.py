# -*- coding: utf-8 -*-
"""
应用配置模块

使用 pydantic-settings 的 BaseSettings 从环境变量和 .env 文件中读取配置。
支持所有必需的环境变量，包括数据库、Redis、JWT、LLM 和外部 API 配置。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    应用配置类

    通过 pydantic-settings 自动从环境变量和 .env 文件加载配置。
    所有配置项都有合理的默认值，但生产环境中应通过环境变量覆盖。
    """

    # ==================== 数据库配置 ====================
    # PostgreSQL 异步连接 URL，使用 asyncpg 驱动
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ai_employee"

    # ==================== Redis 配置 ====================
    # Redis 连接 URL，用于缓存和会话存储
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== 限流配置 ====================
    # 单用户每秒请求限制
    RATE_LIMIT_PER_USER: int = 10
    # 全局每秒请求限制
    RATE_LIMIT_GLOBAL: int = 500

    # ==================== JWT 认证配置 ====================
    # JWT 签名密钥，生产环境中必须更换为安全的随机字符串
    SECRET_KEY: str = "change-me-in-env"
    # JWT 签名算法
    ALGORITHM: str = "HS256"
    # 访问令牌过期时间，默认24小时
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ==================== OpenAI / LLM 配置 ====================
    # OpenAI API 密钥，可用于调用 OpenAI 或兼容 API
    OPENAI_API_KEY: str = "your-openai-api-key"
    # OpenAI API 基础 URL，支持本地部署的 Ollama 等服务
    OPENAI_API_BASE: str = "http://localhost:11434/v1"
    # 使用的 LLM 模型名称
    LLM_MODEL_NAME: str = "qwen2"

    # ==================== FastGPT 配置 ====================
    # FastGPT API URL，用于知识库问答
    FASTGPT_API_URL: str = "http://localhost:3000/api/v1/chat/completions"
    # FastGPT API 密钥
    FASTGPT_API_KEY: str = "your-fastgpt-api-key"

    # ==================== 天气 API 配置 ====================
    # 心知天气 API 密钥
    WEATHER_API_KEY: str = "your-weather-api-key"
    # 心知天气 API URL
    WEATHER_API_URL: str = "https://api.seniverse.com/v3/weather/now.json"
    # 是否启用天气与会议日程联动提醒
    SCHEDULE_WEATHER_REMINDER_ENABLED: bool = True
    # 天气联动提醒使用的城市
    WEATHER_REMINDER_CITY: str = "北京"

    # Pydantic Settings 配置
    model_config = SettingsConfigDict(
        # 从项目根目录的 .env 文件读取配置
        env_file=".env",
        # .env 文件编码
        env_file_encoding="utf-8",
        # 环境变量名称大小写敏感
        case_sensitive=True,
        # 允许从环境变量读取额外字段
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    获取应用配置单例

    使用 lru_cache 装饰器确保配置对象只创建一次，
    后续调用直接返回缓存的实例，提高性能。

    Returns:
        Settings: 应用配置实例
    """
    return Settings()


# 导出配置实例，便于直接导入使用
settings = get_settings()

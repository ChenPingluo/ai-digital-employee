# -*- coding: utf-8 -*-
"""
天气服务模块

使用心知天气 API 获取天气信息。
支持异步请求、异常处理和默认响应。
集成 Redis 缓存，TTL 30分钟，减少 API 调用次数。
"""

import httpx
from typing import Optional

from app.config import settings
from app.services.cache_service import (
    get_weather_cache,
    set_weather_cache,
    WEATHER_CACHE_TTL
)


async def get_weather(city: str) -> dict:
    """
    获取指定城市的天气信息
    
    使用心知天气 API 查询实时天气数据。
    集成 Redis 缓存，缓存 TTL 为 30 分钟。
    
    Args:
        city: 城市名称（中文或拼音，如"北京"或"beijing"）
        
    Returns:
        dict: 天气信息字典，包含以下字段：
            - city: 城市名称
            - weather: 天气状况（如"晴"、"多云"）
            - temperature: 当前温度（摄氏度）
            - humidity: 相对湿度（可选）
            - wind: 风力信息（可选）
            - update_time: 数据更新时间
            - from_cache: 是否来自缓存（布尔值）
            
    Example:
        >>> weather = await get_weather("北京")
        >>> print(weather)
        {'city': '北京', 'weather': '晴', 'temperature': '25', ...}
    """
    # ===== 第一步：尝试从 Redis 缓存获取 =====
    try:
        cached_data = await get_weather_cache(city)
        if cached_data is not None:
            # 缓存命中，添加标记后直接返回
            cached_data["from_cache"] = True
            return cached_data
    except Exception as e:
        # 缓存操作异常时降级为直接查询 API
        print(f"⚠️ 天气缓存查询失败，降级为 API 查询: {e}")
    
    # ===== 第二步：缓存未命中，调用天气 API =====
    try:
        # 构建请求参数
        params = {
            "key": settings.WEATHER_API_KEY,
            "location": city,
            "language": "zh-Hans",
            "unit": "c"  # 使用摄氏度
        }
        
        # 使用 httpx 异步客户端发送请求
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                settings.WEATHER_API_URL,
                params=params
            )
            
            # 检查 HTTP 响应状态
            if response.status_code != 200:
                return _get_error_response(
                    city,
                    f"天气服务暂时不可用（状态码：{response.status_code}）"
                )
            
            # 解析响应数据
            data = response.json()
            
            # 检查 API 返回状态
            if "results" not in data or len(data["results"]) == 0:
                return _get_error_response(
                    city,
                    "未找到该城市的天气信息"
                )
            
            # 提取天气数据
            result = data["results"][0]
            location = result.get("location", {})
            now = result.get("now", {})
            
            # 构建返回数据
            weather_data = {
                "city": location.get("name", city),
                "weather": now.get("text", "未知"),
                "temperature": now.get("temperature", "N/A"),
                "code": now.get("code", ""),
                "update_time": result.get("last_update", ""),
                "success": True,
                "from_cache": False
            }
            
            # ===== 第三步：将结果写入 Redis 缓存 =====
            try:
                await set_weather_cache(city, weather_data)
            except Exception as e:
                # 缓存写入失败不影响返回结果
                print(f"⚠️ 天气数据缓存写入失败: {e}")
            
            return weather_data
            
    except httpx.TimeoutException:
        # 请求超时
        return _get_error_response(city, "天气查询超时，请稍后重试")
        
    except httpx.RequestError as e:
        # 网络请求错误
        return _get_error_response(city, f"网络请求失败: {str(e)}")
        
    except Exception as e:
        # 其他异常
        return _get_error_response(city, f"获取天气信息失败: {str(e)}")


def _get_error_response(city: str, message: str) -> dict:
    """
    生成错误响应
    
    Args:
        city: 城市名称
        message: 错误消息
        
    Returns:
        dict: 包含错误信息的响应字典
    """
    return {
        "city": city,
        "weather": "未知",
        "temperature": "N/A",
        "message": message,
        "success": False
    }


def format_weather_response(weather_data: dict) -> str:
    """
    格式化天气数据为可读文本
    
    Args:
        weather_data: 天气信息字典
        
    Returns:
        str: 格式化的天气描述文本
    """
    if not weather_data.get("success", False):
        return weather_data.get("message", "获取天气信息失败")
    
    city = weather_data.get("city", "未知")
    weather = weather_data.get("weather", "未知")
    temperature = weather_data.get("temperature", "N/A")
    
    return f"{city}当前天气：{weather}，温度 {temperature}°C"


# ==================== 天气代码映射 ====================
# 心知天气 API 的天气代码对应的图标和描述
WEATHER_CODES = {
    "0": {"icon": "☀️", "desc": "晴"},
    "1": {"icon": "☁️", "desc": "多云"},
    "2": {"icon": "🌥️", "desc": "少云"},
    "3": {"icon": "🌤️", "desc": "晴间多云"},
    "4": {"icon": "☁️", "desc": "阴"},
    "5": {"icon": "🌨️", "desc": "薄雾"},
    "6": {"icon": "🌫️", "desc": "雾"},
    "7": {"icon": "🌧️", "desc": "阵雨"},
    "8": {"icon": "⛈️", "desc": "雷阵雨"},
    "9": {"icon": "⛈️", "desc": "雷阵雨伴有冰雹"},
    "10": {"icon": "🌧️", "desc": "小雨"},
    "11": {"icon": "🌧️", "desc": "中雨"},
    "12": {"icon": "🌧️", "desc": "大雨"},
    "13": {"icon": "🌧️", "desc": "暴雨"},
    "14": {"icon": "🌧️", "desc": "大暴雨"},
    "15": {"icon": "🌧️", "desc": "特大暴雨"},
    "16": {"icon": "🌨️", "desc": "阵雪"},
    "17": {"icon": "❄️", "desc": "小雪"},
    "18": {"icon": "❄️", "desc": "中雪"},
    "19": {"icon": "❄️", "desc": "大雪"},
    "20": {"icon": "❄️", "desc": "暴雪"},
    "21": {"icon": "🌫️", "desc": "霾"},
    "22": {"icon": "🌧️", "desc": "小到中雨"},
    "23": {"icon": "🌧️", "desc": "中到大雨"},
    "24": {"icon": "🌧️", "desc": "大到暴雨"},
    "25": {"icon": "🌧️", "desc": "暴雨到大暴雨"},
    "26": {"icon": "🌨️", "desc": "雨夹雪"},
    "99": {"icon": "❓", "desc": "未知"}
}


def get_weather_icon(code: str) -> str:
    """
    根据天气代码获取图标
    
    Args:
        code: 天气代码
        
    Returns:
        str: 对应的天气图标
    """
    weather_info = WEATHER_CODES.get(code, WEATHER_CODES["99"])
    return weather_info["icon"]

# -*- coding: utf-8 -*-
"""
天气查询 Langchain 工具模块

提供用于 AI Agent 的天气查询工具。
"""

import asyncio
from typing import List

from langchain.tools import StructuredTool
from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field

from app.services import weather_service


# ==================== 工具参数模式 ====================

class GetWeatherInput(BaseModel):
    """查询天气的参数模式"""
    city: str = Field(
        description="城市名称，支持中文（如'北京'）或拼音（如'beijing'）"
    )


# ==================== 工具函数 ====================

def get_weather(city: str) -> str:
    """
    查询指定城市的天气
    
    Args:
        city: 城市名称
        
    Returns:
        str: 天气信息描述
    """
    try:
        async def _get_weather():
            return await weather_service.get_weather(city)
        
        # 执行异步函数
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_weather())
                weather_data = future.result()
        except RuntimeError:
            weather_data = asyncio.run(_get_weather())
        
        # 检查是否成功
        if not weather_data.get("success", False):
            error_msg = weather_data.get("message", "查询失败")
            return f"❌ 天气查询失败：{error_msg}"
        
        # 格式化输出
        city_name = weather_data.get("city", city)
        province = weather_data.get("province", "")
        weather = weather_data.get("weather", "未知")
        temperature = weather_data.get("temperature", "N/A")
        humidity = weather_data.get("humidity")
        wind_direction = weather_data.get("wind_direction", "")
        wind_power = weather_data.get("wind_power", "")
        
        location_str = f"{province} {city_name}".strip() if province else city_name
        result = f"🌍 {location_str}天气\n\n"
        result += f"🌡️ 温度：{temperature}°C\n"
        result += f"☁️ 天气：{weather}\n"
        if humidity is not None:
            result += f"💧 湿度：{humidity}%\n"
        if wind_direction:
            result += f"🌬️ 风向：{wind_direction}"
            if wind_power:
                result += f" {wind_power}"
            result += "\n"
        
        # 添加更新时间（如果有）
        update_time = weather_data.get("update_time")
        if update_time:
            result += f"🕐 更新时间：{update_time}"
        
        return result
        
    except Exception as e:
        return f"❌ 天气查询异常：{str(e)}"


def get_weather_tools() -> List[BaseTool]:
    """
    获取天气查询工具列表
    
    天气工具不需要用户身份绑定，直接返回工具列表。
    
    Returns:
        List[BaseTool]: Langchain 工具列表
    """
    tools = [
        StructuredTool.from_function(
            func=get_weather,
            name="get_weather",
            description="查询指定城市的实时天气信息，包括温度和天气状况。支持中国城市名（如北京、上海）。",
            args_schema=GetWeatherInput
        )
    ]
    
    return tools

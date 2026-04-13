# -*- coding: utf-8 -*-
"""
FastGPT 知识库服务模块

调用 FastGPT API 进行企业知识库问答。
支持异步请求、超时控制和重试机制。
"""

import uuid
import httpx
from typing import Optional

from app.config import settings


# ==================== 配置常量 ====================
# 请求超时时间（秒）
REQUEST_TIMEOUT = 30.0
# 最大重试次数
MAX_RETRIES = 3
# 重试间隔（秒）
RETRY_DELAY = 1.0


async def query_fastgpt(
    question: str,
    chat_id: Optional[str] = None
) -> str:
    """
    调用 FastGPT API 进行知识库问答
    
    Args:
        question: 用户提问内容
        chat_id: 会话 ID，用于维持对话上下文（可选）
        
    Returns:
        str: FastGPT 返回的回答内容
        
    Example:
        >>> answer = await query_fastgpt("公司的报销流程是什么？")
        >>> print(answer)
        "公司报销流程如下：1. 填写报销单..."
    """
    # 如果没有提供 chat_id，生成一个新的
    if chat_id is None:
        chat_id = str(uuid.uuid4())
    
    # 构建请求体
    request_body = {
        "chatId": chat_id,
        "stream": False,
        "detail": False,
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ]
    }
    
    # 构建请求头
    headers = {
        "Authorization": f"Bearer {settings.FASTGPT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 重试逻辑
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            # 使用 httpx 异步客户端发送请求
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    settings.FASTGPT_API_URL,
                    json=request_body,
                    headers=headers
                )
                
                # 检查 HTTP 响应状态
                if response.status_code == 200:
                    return _parse_response(response.json())
                    
                elif response.status_code == 401:
                    return "知识库服务认证失败，请检查 API 密钥配置"
                    
                elif response.status_code == 429:
                    # 请求过于频繁，等待后重试
                    if attempt < MAX_RETRIES - 1:
                        import asyncio
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    return "知识库服务请求过于频繁，请稍后重试"
                    
                elif response.status_code >= 500:
                    # 服务器错误，重试
                    if attempt < MAX_RETRIES - 1:
                        import asyncio
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    return "知识库服务暂时不可用，请稍后重试"
                    
                else:
                    return f"知识库查询失败（状态码：{response.status_code}）"
                    
        except httpx.TimeoutException:
            last_error = "知识库查询超时"
            if attempt < MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(RETRY_DELAY)
                continue
                
        except httpx.RequestError as e:
            last_error = f"网络请求失败: {str(e)}"
            if attempt < MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(RETRY_DELAY)
                continue
                
        except Exception as e:
            last_error = f"知识库查询异常: {str(e)}"
            break
    
    # 所有重试都失败
    return last_error or "知识库查询失败，请稍后重试"


def _parse_response(response_data: dict) -> str:
    """
    解析 FastGPT API 响应
    
    FastGPT API 的响应格式类似 OpenAI：
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "回答内容"
                }
            }
        ]
    }
    
    Args:
        response_data: API 响应的 JSON 数据
        
    Returns:
        str: 提取的回答内容
    """
    try:
        # 尝试解析 OpenAI 格式的响应
        if "choices" in response_data:
            choices = response_data.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if content:
                    return content.strip()
        
        # 尝试解析其他可能的响应格式
        if "answer" in response_data:
            return response_data["answer"].strip()
        
        if "response" in response_data:
            return response_data["response"].strip()
        
        if "text" in response_data:
            return response_data["text"].strip()
        
        # 如果无法解析，返回原始响应
        return f"收到响应但无法解析：{str(response_data)[:200]}"
        
    except Exception as e:
        return f"解析响应失败: {str(e)}"


async def check_fastgpt_connection() -> bool:
    """
    检查 FastGPT 服务连接状态
    
    Returns:
        bool: 服务可用返回 True，否则返回 False
    """
    try:
        headers = {
            "Authorization": f"Bearer {settings.FASTGPT_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 发送一个简单的测试请求
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                settings.FASTGPT_API_URL,
                json={
                    "chatId": "test",
                    "stream": False,
                    "detail": False,
                    "messages": [{"role": "user", "content": "test"}]
                },
                headers=headers
            )
            
            # 只要不是网络错误就认为服务可用
            return response.status_code in [200, 400, 401, 403]
            
    except Exception:
        return False


def format_knowledge_response(answer: str, question: str) -> str:
    """
    格式化知识库查询响应
    
    Args:
        answer: 知识库返回的答案
        question: 用户的原始问题
        
    Returns:
        str: 格式化的响应文本
    """
    if not answer or answer.startswith("知识库"):
        # 查询失败的情况
        return f"抱歉，我暂时无法回答关于「{question}」的问题。{answer}"
    
    return answer

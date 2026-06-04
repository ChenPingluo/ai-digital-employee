# -*- coding: utf-8 -*-
"""
FastGPT 知识库服务模块

调用 FastGPT API 进行企业知识库问答。
支持异步请求、超时控制和重试机制。
"""

import asyncio
import uuid
import httpx
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from app.config import settings


# ==================== 配置常量 ====================
# 请求超时时间（秒）
REQUEST_TIMEOUT = 30.0
# 最大重试次数
MAX_RETRIES = 3
# 重试间隔（秒）
RETRY_DELAY = 1.0
PLACEHOLDER_API_KEYS = {"", "your-fastgpt-api-key"}


def resolve_fastgpt_chat_url(api_url: str) -> str:
    """
    将配置中的 FastGPT URL 规范化为真正的聊天补全接口。

    兼容以下几类输入：
    - http://host:3000
    - http://host:3000/api
    - http://host:3000/api/v1
    - http://host:3000/api/v1/chat/completions
    """
    raw_url = (api_url or "").strip()
    if not raw_url:
        return raw_url

    parsed = urlsplit(raw_url)
    path = parsed.path.rstrip("/")
    lower_path = path.lower()

    if lower_path.endswith("/chat/completions"):
        normalized_path = path
    elif lower_path.endswith("/api/v1"):
        normalized_path = f"{path}/chat/completions"
    elif lower_path.endswith("/v1"):
        normalized_path = f"{path}/chat/completions"
    elif lower_path.endswith("/api"):
        normalized_path = f"{path}/v1/chat/completions"
    elif path in {"", "/"}:
        normalized_path = "/api/v1/chat/completions"
    else:
        normalized_path = f"{path}/api/v1/chat/completions"

    return urlunsplit(
        (parsed.scheme, parsed.netloc, normalized_path, parsed.query, parsed.fragment)
    )


def _get_response_excerpt(response: httpx.Response, limit: int = 300) -> str:
    """提取响应体摘要，便于定位 FastGPT 错误。"""
    try:
        content = response.text.strip()
    except Exception:
        content = ""

    if not content:
        return "空响应体"
    if len(content) > limit:
        return f"{content[:limit]}..."
    return content


def _build_fastgpt_error_message(response: httpx.Response, request_url: str) -> str:
    """根据 HTTP 响应构建更可读的错误消息。"""
    status_code = response.status_code
    body_excerpt = _get_response_excerpt(response)
    lower_excerpt = body_excerpt.lower()

    if "app key rather than the account key" in lower_excerpt:
        return (
            "知识库服务返回了账号级 Key 错误。"
            "当前使用的是账户 Key，不是应用 Key。"
            "请到 FastGPT 对应应用页面生成并使用该应用自己的 API Key。"
        )

    if status_code in (401, 403):
        return (
            "知识库服务认证失败，请检查 FastGPT API Key 是否正确，"
            "并确认它是该应用可用的专用 Key。"
        )

    if status_code == 404:
        return (
            f"知识库服务地址无效，当前请求地址为：{request_url}。"
            "请确认服务器地址或反向代理路径是否正确。"
        )

    if status_code == 429:
        return "知识库服务请求过于频繁，请稍后重试。"

    if status_code >= 500:
        return (
            f"知识库服务返回 {status_code}。"
            f"请求地址：{request_url}。"
            f"响应摘要：{body_excerpt}。"
            "请优先检查 FastGPT 应用状态、服务端日志和 API Key 绑定关系。"
        )

    return (
        f"知识库查询失败（状态码：{status_code}）。"
        f"请求地址：{request_url}。"
        f"响应摘要：{body_excerpt}"
    )


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

    api_key = (settings.FASTGPT_API_KEY or "").strip()
    if api_key in PLACEHOLDER_API_KEYS:
        return "知识库服务未配置有效的 API Key"

    request_url = resolve_fastgpt_chat_url(settings.FASTGPT_API_URL)
    if not request_url:
        return "知识库服务未配置有效的 API URL"
    
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
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 重试逻辑
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            # 使用 httpx 异步客户端发送请求
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    request_url,
                    json=request_body,
                    headers=headers
                )
                
                # 检查 HTTP 响应状态
                if response.status_code == 200:
                    return _parse_response(response.json())

                if response.status_code == 429:
                    # 请求过于频繁，等待后重试
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        continue

                if response.status_code >= 500:
                    # 服务器错误，重试
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue

                return _build_fastgpt_error_message(response, request_url)
                    
        except httpx.TimeoutException:
            last_error = "知识库查询超时"
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
                
        except httpx.RequestError as e:
            last_error = f"网络请求失败: {str(e)}"
            if attempt < MAX_RETRIES - 1:
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
        api_key = (settings.FASTGPT_API_KEY or "").strip()
        request_url = resolve_fastgpt_chat_url(settings.FASTGPT_API_URL)
        if api_key in PLACEHOLDER_API_KEYS or not request_url:
            return False

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 发送一个简单的测试请求
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                request_url,
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

# -*- coding: utf-8 -*-
"""
对话交互接口模块

提供 AI 对话的 API 端点，接收用户自然语言输入并调用 Agent 处理。
"""

import uuid
import json
import re
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.middleware.auth import get_current_user
from app.middleware.rate_limiter import chat_limiter, check_rate_limit

# 日志配置
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/chat", tags=["AI 对话"])


@router.post(
    "/",
    response_model=ChatResponse,
    summary="发送对话消息",
    description="发送自然语言消息给 AI 助手，获取智能响应"
)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 对话接口
    
    接收用户的自然语言输入，通过 Router Agent 理解意图并执行相应操作。
    
    支持的功能：
    - 待办事项管理（创建、查询、更新状态）
    - 会议室预约（查询会议室、创建预约）
    - 天气查询
    - 企业知识库问答
    
    - **message**: 用户发送的消息内容
    - **conversation_id**: 会话 ID（可选，用于维持上下文）
    """
    # 检查限流
    await check_rate_limit(
        request,
        limiter=chat_limiter,
        error_message="对话请求过于频繁，请稍后再试"
    )
    
    try:
        # 导入 router_agent（延迟导入避免循环依赖）
        from app.agents.router_agent import process_message
        
        # 生成或使用现有会话 ID
        conversation_id = chat_request.conversation_id or str(uuid.uuid4())
        
        # 调用 Agent 处理消息
        response_message = await process_message(
            user_input=chat_request.message,
            user_id=str(current_user.id),
            db=db,
            conversation_id=conversation_id,
            history=chat_request.history
        )
        
        return ChatResponse(
            message=response_message,
            conversation_id=conversation_id,
            tool_calls=None,  # 可扩展：记录工具调用
            metadata={
                "user_id": str(current_user.id),
                "model": "router_agent"
            }
        )
        
    except Exception as e:
        # 记录错误日志（生产环境应使用日志系统）
        print(f"对话处理错误: {str(e)}")
        
        # 返回友好的错误信息
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对话处理失败，请稍后重试"
        )


@router.post(
    "/quick",
    response_model=ChatResponse,
    summary="快捷对话",
    description="简化的对话接口，直接返回 AI 响应"
)
async def quick_chat(
    request: Request,
    message: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    快捷对话接口
    
    简化的对话接口，适用于简单查询场景。
    
    - **message**: 用户消息（查询参数）
    """
    # 检查限流
    await check_rate_limit(
        request,
        limiter=chat_limiter,
        error_message="对话请求过于频繁，请稍后再试"
    )
    
    try:
        from app.agents.router_agent import process_message
        
        conversation_id = str(uuid.uuid4())
        
        response_message = await process_message(
            user_input=message,
            user_id=str(current_user.id),
            db=db,
            conversation_id=conversation_id
        )
        
        return ChatResponse(
            message=response_message,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        print(f"快捷对话处理错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="对话处理失败，请稍后重试"
        )


@router.post(
    "/stream",
    summary="流式对话",
    description="使用 Server-Sent Events (SSE) 返回流式响应"
)
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    流式对话接口 - 使用 Server-Sent Events (SSE) 返回流式响应
    
    接收用户的自然语言输入，通过 SSE 流式返回 AI 响应。
    
    - **message**: 用户发送的消息内容
    - **conversation_id**: 会话 ID（可选）
    """
    # 检查限流
    await check_rate_limit(
        request,
        limiter=chat_limiter,
        error_message="对话请求过于频繁，请稍后再试"
    )
    
    async def event_generator():
        """
        SSE 事件生成器
        
        将完整响应按句子/段落分块发送，模拟流式效果
        """
        try:
            # 延迟导入避免循环依赖
            from app.agents.router_agent import process_message
            
            # 调用 Router Agent 处理用户消息
            result = await process_message(
                user_input=chat_request.message,
                user_id=str(current_user.id),
                db=db,
                conversation_id=chat_request.conversation_id,
                history=chat_request.history
            )
            
            # 将完整响应按标点符号分块发送，模拟流式效果
            chunks = re.split(r'(?<=[\u3002\uff01\uff1f\n.!?])', result)
            
            for chunk in chunks:
                if chunk.strip():
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    # 短暂延迟模拟流式效果
                    await asyncio.sleep(0.05)
            
            # 发送结束标记
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"流式对话处理失败: {str(e)}")
            error_data = json.dumps({"error": f"处理失败: {str(e)}"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
        }
    )

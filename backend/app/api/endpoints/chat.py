# -*- coding: utf-8 -*-
"""
对话交互接口模块

提供 AI 对话的 API 端点，接收用户自然语言输入并调用 Agent 处理。
包含会话管理 CRUD 端点。
"""

import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage, ConversationCreate
from app.middleware.auth import get_current_user
from app.middleware.rate_limiter import chat_limiter, check_rate_limit
from app.services.conversation_service import ConversationService

# 日志配置
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/chat", tags=["AI 对话"])

@router.get(
    "/conversations",
    summary="获取会话列表",
    description="获取当前用户的所有会话列表"
)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的会话列表"""
    conversations = await ConversationService.get_user_conversations(db, str(current_user.id))
    return [
        {
            "id": str(conv.id),
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
        }
        for conv in conversations
    ]


@router.post(
    "/conversations",
    summary="创建新会话",
    description="创建一个新的聊天会话"
)
async def create_conversation(
    request_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新会话"""
    conv = await ConversationService.create_conversation(db, str(current_user.id), request_data.title)
    return {
        "id": str(conv.id),
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None
    }


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="获取会话消息历史",
    description="获取指定会话的所有消息记录"
)
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取会话消息历史"""
    messages = await ConversationService.get_conversation_history(db, conversation_id, str(current_user.id))
    return [
        {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }
        for msg in messages
    ]


@router.delete(
    "/conversations/{conversation_id}",
    summary="删除会话",
    description="删除指定的聊天会话及其所有消息"
)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除会话"""
    success = await ConversationService.delete_conversation(db, conversation_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True}


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
    - **conversation_id**: 会话 ID
    """
    # 检查限流
    await check_rate_limit(
        request,
        limiter=chat_limiter,
        error_message="对话请求过于频繁，请稍后再试"
    )
    
    try:
        # 导入 router_agent
        from app.agents.router_agent import process_message
        
        user_id = str(current_user.id)
        conversation_id = chat_request.conversation_id
        
        # 1. 处理会话：有 conversation_id 则验证，否则自动创建
        if conversation_id:
            # 验证会话存在且属于当前用户
            history_msgs = await ConversationService.get_conversation_history(
                db, conversation_id, user_id
            )
            # 如果返回空列表且会话不存在，需要额外检查
            # get_conversation_history 内部已验证归属，空列表可能是无消息或会话不存在
            # 这里通过尝试获取会话来确认
            convs = await ConversationService.get_user_conversations(db, user_id, limit=100)
            conv_exists = any(str(c.id) == conversation_id for c in convs)
            if not conv_exists:
                raise HTTPException(status_code=404, detail="会话不存在或无权访问")
        else:
            # 自动创建新会话，标题使用消息前20个字符
            title = chat_request.message[:20] + ("..." if len(chat_request.message) > 20 else "")
            conv = await ConversationService.create_conversation(db, user_id, title)
            conversation_id = str(conv.id)
            history_msgs = []
        
        # 2. 构建历史消息
        #    对于新会话，history_msgs 为空列表；对于已有会话，包含所有之前的消息
        history = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in history_msgs
        ] if history_msgs else []
        
        # 3. 保存用户消息到数据库
        await ConversationService.save_message(db, conversation_id, "user", chat_request.message)
        
        # 4. 调用 Agent 处理消息
        response_message = await process_message(
            user_input=chat_request.message,
            user_id=user_id,
            db=db,
            conversation_id=conversation_id,
            history=history if history else None
        )
        
        # 5. 保存 AI 回复到数据库
        await ConversationService.save_message(db, conversation_id, "assistant", response_message)
        
        return ChatResponse(
            message=response_message,
            conversation_id=conversation_id,
            tool_calls=None,
            metadata={
                "user_id": user_id,
                "model": "router_agent"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对话处理错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="对话处理失败，请稍后重试"
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
        logger.error(f"快捷对话处理错误: {str(e)}")
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
    自动存储和加载会话历史。
    
    - **message**: 用户发送的消息内容
    - **conversation_id**: 会话 ID（可选）
    """
    # 检查限流
    await check_rate_limit(
        request,
        limiter=chat_limiter,
        error_message="对话请求过于频繁，请稍后再试"
    )
    
    user_id = str(current_user.id)
    conversation_id = chat_request.conversation_id
    
    # 处理会话：有 conversation_id 则验证，否则自动创建
    try:
        if conversation_id:
            convs = await ConversationService.get_user_conversations(db, user_id, limit=100)
            conv_exists = any(str(c.id) == conversation_id for c in convs)
            if not conv_exists:
                raise HTTPException(status_code=404, detail="会话不存在或无权访问")
        else:
            title = chat_request.message[:20] + ("..." if len(chat_request.message) > 20 else "")
            conv = await ConversationService.create_conversation(db, user_id, title)
            conversation_id = str(conv.id)
        
        # 保存用户消息
        await ConversationService.save_message(db, conversation_id, "user", chat_request.message)
        
        # 加载历史消息
        history_msgs = await ConversationService.get_conversation_history(
            db, conversation_id, user_id, limit=50
        )
        
        # 转换为 ChatMessage 格式
        history = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in history_msgs[:-1]
        ] if len(history_msgs) > 1 else []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式对话会话处理错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="会话处理失败"
        )
    
    async def event_generator():
        """
        SSE 事件生成器
        
        直接消费后端 Agent 的真实流式输出。
        完成后保存完整的 AI 回复到数据库。
        """
        try:
            # 尽早发送 conversation_id，避免前端在长耗时处理中丢失会话定位
            meta_data = json.dumps({"conversation_id": conversation_id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            # 延迟导入避免循环依赖
            from app.agents.router_agent import stream_message

            assistant_chunks = []

            # 调用 Router Agent，直接透传真实流式文本
            async for chunk in stream_message(
                user_input=chat_request.message,
                user_id=user_id,
                db=db,
                conversation_id=conversation_id,
                history=history if history else None
            ):
                if await request.is_disconnected():
                    logger.info("客户端已断开流式连接: conversation_id=%s", conversation_id)
                    break

                assistant_chunks.append(chunk)
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            assistant_message = "".join(assistant_chunks)
            if assistant_message.strip():
                await ConversationService.save_message(db, conversation_id, "assistant", assistant_message)

            # 发送结束标记
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"流式对话处理失败: {str(e)}")
            error_data = json.dumps(
                {
                    "conversation_id": conversation_id,
                    "error": f"处理失败: {str(e)}"
                },
                ensure_ascii=False
            )
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

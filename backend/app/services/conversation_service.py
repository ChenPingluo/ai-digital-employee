# -*- coding: utf-8 -*-
"""
会话管理服务模块

提供会话和聊天消息的 CRUD 业务逻辑，包括创建、查询、更新和删除操作。
所有数据库操作均为异步实现。
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ChatMessageRecord


class ConversationService:
    """
    会话管理服务
    
    提供会话和聊天消息的增删改查方法。
    """

    @staticmethod
    async def create_conversation(db: AsyncSession, user_id: str, title: str = None) -> Conversation:
        """
        创建新会话
        
        Args:
            db: 异步数据库会话
            user_id: 用户 ID
            title: 会话标题，默认为"新对话"
            
        Returns:
            Conversation: 创建成功的会话对象
        """
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            title=title or f"新对话"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get_user_conversations(db: AsyncSession, user_id: str, limit: int = 50) -> List[Conversation]:
        """
        获取用户所有会话列表，按更新时间倒序
        
        Args:
            db: 异步数据库会话
            user_id: 用户 ID
            limit: 返回数量上限
            
        Returns:
            List[Conversation]: 会话列表
        """
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == uid)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_conversation_history(db: AsyncSession, conversation_id: str, user_id: str, limit: int = 50) -> List[ChatMessageRecord]:
        """
        获取指定会话的消息历史
        
        Args:
            db: 异步数据库会话
            conversation_id: 会话 ID
            user_id: 用户 ID（用于权限验证）
            limit: 返回数量上限
            
        Returns:
            List[ChatMessageRecord]: 消息列表
        """
        # 先验证会话属于该用户
        conv_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == uid
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            return []
        
        result = await db.execute(
            select(ChatMessageRecord)
            .where(ChatMessageRecord.conversation_id == conv_id)
            .order_by(ChatMessageRecord.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def save_message(db: AsyncSession, conversation_id: str, role: str, content: str) -> ChatMessageRecord:
        """
        保存单条消息
        
        Args:
            db: 异步数据库会话
            conversation_id: 会话 ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            
        Returns:
            ChatMessageRecord: 保存成功的消息对象
        """
        conv_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
        message = ChatMessageRecord(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            role=role,
            content=content
        )
        db.add(message)
        
        # 更新会话的 updated_at
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conv = conv_result.scalar_one_or_none()
        if conv:
            conv.updated_at = func.now()
        
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation_id: str, user_id: str) -> bool:
        """
        删除会话及其所有消息
        
        Args:
            db: 异步数据库会话
            conversation_id: 会话 ID
            user_id: 用户 ID（用于权限验证）
            
        Returns:
            bool: 删除成功返回 True，不存在或无权限返回 False
        """
        conv_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == uid
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            return False
        
        # 因为设置了 ON DELETE CASCADE，删除会话会自动删除消息
        await db.delete(conversation)
        await db.commit()
        return True

    @staticmethod
    async def update_conversation_title(db: AsyncSession, conversation_id: str, user_id: str, title: str) -> Optional[Conversation]:
        """
        更新会话标题
        
        Args:
            db: 异步数据库会话
            conversation_id: 会话 ID
            user_id: 用户 ID（用于权限验证）
            title: 新标题
            
        Returns:
            Optional[Conversation]: 更新后的会话对象，不存在或无权限时返回 None
        """
        conv_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == uid
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            return None
        
        conversation.title = title
        conversation.updated_at = func.now()
        await db.commit()
        await db.refresh(conversation)
        return conversation

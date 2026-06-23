# -*- coding: utf-8 -*-
"""
记忆服务模块

核心服务：自动提取、存储、检索和管理用户长期记忆。
采用"提取-存储-检索-淘汰"四阶段流水线。
"""

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.models.user_memory import UserMemory

logger = logging.getLogger(__name__)

# ── 配置常量 ──
MAX_MEMORIES_PER_USER = 200      # 每个用户最多记忆数
MAX_MEMORIES_IN_CONTEXT = 15     # 每次对话注入的最大记忆数
MEMORY_EXTRACTION_WINDOW = 10    # 每隔 N 轮对话触发一次提取
EXTRACTION_BATCH_SIZE = 5        # 每次提取时处理的最近消息数

# ── 记忆提取的系统提示词 ──
MEMORY_EXTRACTION_PROMPT = """你是一个用户记忆提取器。从以下对话中提取关于用户的**关键信息**，整理为简洁的记忆条目。

## 记忆类型
- **fact**: 用户陈述的事实信息（如"张三在字节跳动工作"）
- **preference**: 用户的偏好或习惯（如"喜欢用 Python 编程"）
- **event**: 用户提到的事件（如"下周要去北京出差"）
- **person**: 用户提到的人物关系（如"李四是我的直属上级"）
- **context**: 上下文信息（如"正在做毕业设计"）

## 规则
1. 只提取**用户自己**的信息，不要提取 AI 助手的信息
2. 每条记忆用一句简洁的陈述句表达
3. 为每条记忆标注重要性（1-10）和置信度（0-1）
4. 如果对话中没有新的有价值信息，返回空数组
5. 不要重复已有的记忆

## 已有记忆（避免重复）
{existing_memories}

## 对话内容
{conversation}

## 输出格式
请以 JSON 数组格式输出，每个元素包含：
- type: 记忆类型
- category: 分类标签（work/tech/health/life/learning/other）
- content: 记忆内容
- importance: 重要性（1-10）
- confidence: 置信度（0.0-1.0）

如果没有新记忆，返回 []
"""

# ── 记忆检索的系统提示词（用于判断相关记忆）──
MEMORY_RETRIEVAL_PROMPT = """你是一个记忆检索器。根据用户的当前问题，从以下记忆库中选出最相关的记忆。

## 用户当前问题
{user_query}

## 记忆库
{memory_list}

## 规则
1. 只选出与当前问题**直接相关**的记忆
2. 优先选择 importance 高且最近被访问的记忆
3. 最多返回 {max_count} 条
4. 如果没有相关记忆，返回空数组

## 输出格式
返回 JSON 数组，每个元素包含 memory_id 和 relevance（相关度 0-1）
"""


class MemoryService:
    """用户记忆服务"""

    # ── 创建记忆 ──
    @staticmethod
    async def create_memory(
        db: AsyncSession,
        user_id: str,
        memory_type: str,
        content: str,
        importance: int = 5,
        confidence: float = 0.8,
        category: Optional[str] = None,
        context: Optional[str] = None,
        source_conversation_id: Optional[str] = None
    ) -> UserMemory:
        """创建一条新记忆"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        sid = (
            uuid.UUID(source_conversation_id)
            if source_conversation_id and isinstance(source_conversation_id, str)
            else source_conversation_id
        )

        memory = UserMemory(
            user_id=uid,
            memory_type=memory_type,
            category=category,
            content=content,
            context=context,
            source_conversation_id=sid,
            importance=importance,
            confidence=confidence,
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)

        # 清理过多记忆
        await MemoryService._cleanup_old_memories(db, user_id)

        return memory

    # ── 批量创建 ──
    @staticmethod
    async def create_memories_batch(
        db: AsyncSession,
        user_id: str,
        memories: List[Dict[str, Any]],
        source_conversation_id: Optional[str] = None
    ) -> List[UserMemory]:
        """批量创建记忆"""
        results = []
        for mem in memories:
            result = await MemoryService.create_memory(
                db=db,
                user_id=user_id,
                memory_type=mem.get("type", "fact"),
                content=mem["content"],
                importance=mem.get("importance", 5),
                confidence=mem.get("confidence", 0.8),
                category=mem.get("category"),
                context=mem.get("context"),
                source_conversation_id=source_conversation_id,
            )
            results.append(result)
        return results

    # ── 获取用户记忆 ──
    @staticmethod
    async def get_user_memories(
        db: AsyncSession,
        user_id: str,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        min_importance: int = 0
    ) -> List[UserMemory]:
        """获取用户的记忆列表"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        conditions = [
            UserMemory.user_id == uid,
            UserMemory.is_active == True,
            UserMemory.importance >= min_importance,
        ]
        if memory_type:
            conditions.append(UserMemory.memory_type == memory_type)
        if category:
            conditions.append(UserMemory.category == category)

        result = await db.execute(
            select(UserMemory)
            .where(and_(*conditions))
            .order_by(desc(UserMemory.importance), desc(UserMemory.updated_at))
            .limit(limit)
        )
        return result.scalars().all()

    # ── 关键词搜索记忆 ──
    @staticmethod
    async def search_memories(
        db: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[UserMemory]:
        """关键词搜索用户记忆"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        result = await db.execute(
            select(UserMemory)
            .where(
                and_(
                    UserMemory.user_id == uid,
                    UserMemory.is_active == True,
                    UserMemory.content.ilike(f"%{query}%")
                )
            )
            .order_by(desc(UserMemory.importance))
            .limit(limit)
        )
        return result.scalars().all()

    # ── 获取相关记忆（用于注入对话上下文）──
    @staticmethod
    async def get_relevant_memories(
        db: AsyncSession,
        user_id: str,
        query: str,
        limit: int = MAX_MEMORIES_IN_CONTEXT
    ) -> List[UserMemory]:
        """
        获取与当前问题最相关的记忆。

        策略：
        1. 先按关键词匹配
        2. 补充最近更新的高重要性记忆
        3. 去重后按重要性排序
        """
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        # 第一步：关键词模糊匹配
        keywords = query.split()
        keyword_conditions = []
        for kw in keywords[:5]:  # 最多取前5个关键词
            if len(kw) >= 2:  # 忽略单字
                keyword_conditions.append(UserMemory.content.ilike(f"%{kw}%"))

        keyword_memories = []
        if keyword_conditions:
            result = await db.execute(
                select(UserMemory)
                .where(
                    and_(
                        UserMemory.user_id == uid,
                        UserMemory.is_active == True,
                        or_(*keyword_conditions)
                    )
                )
                .order_by(desc(UserMemory.importance))
                .limit(limit)
            )
            keyword_memories = result.scalars().all()

        # 第二步：补充高重要性记忆
        if len(keyword_memories) < limit:
            existing_ids = {m.id for m in keyword_memories}
            result = await db.execute(
                select(UserMemory)
                .where(
                    and_(
                        UserMemory.user_id == uid,
                        UserMemory.is_active == True,
                        UserMemory.importance >= 7,
                        UserMemory.id.notin_(existing_ids) if existing_ids else True
                    )
                )
                .order_by(desc(UserMemory.importance), desc(UserMemory.updated_at))
                .limit(limit - len(keyword_memories))
            )
            keyword_memories.extend(result.scalars().all())

        # 更新访问计数
        for mem in keyword_memories:
            mem.access_count += 1
            mem.last_accessed = datetime.now(timezone.utc)
        await db.commit()

        return keyword_memories[:limit]

    # ── 删除记忆 ──
    @staticmethod
    async def delete_memory(
        db: AsyncSession,
        memory_id: str,
        user_id: str
    ) -> bool:
        """软删除一条记忆"""
        mid = uuid.UUID(memory_id) if isinstance(memory_id, str) else memory_id
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        result = await db.execute(
            select(UserMemory).where(
                and_(UserMemory.id == mid, UserMemory.user_id == uid)
            )
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return False

        memory.is_active = False
        await db.commit()
        return True

    # ── 更新记忆 ──
    @staticmethod
    async def update_memory(
        db: AsyncSession,
        memory_id: str,
        user_id: str,
        **kwargs
    ) -> Optional[UserMemory]:
        """更新记忆属性"""
        mid = uuid.UUID(memory_id) if isinstance(memory_id, str) else memory_id
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        result = await db.execute(
            select(UserMemory).where(
                and_(UserMemory.id == mid, UserMemory.user_id == uid)
            )
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return None

        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)

        memory.updated_at = func.now()
        await db.commit()
        await db.refresh(memory)
        return memory

    # ── 格式化记忆为提示词 ──
    @staticmethod
    def format_memories_for_prompt(memories: List[UserMemory]) -> str:
        """将记忆列表格式化为可注入系统提示词的文本"""
        if not memories:
            return "暂无关于该用户的记忆。"

        lines = ["## 关于该用户的已知信息（长期记忆）\n"]
        for i, mem in enumerate(memories, 1):
            type_emoji = {
                "fact": "📌",
                "preference": "⭐",
                "event": "📅",
                "person": "👤",
                "context": "💡"
            }
            emoji = type_emoji.get(mem.memory_type, "📌")
            lines.append(f"{i}. {emoji} [{mem.memory_type}] {mem.content} (重要性: {mem.importance}/10)")

        return "\n".join(lines)

    # ── 提取记忆（核心方法）──
    @staticmethod
    async def extract_memories_from_conversation(
        db: AsyncSession,
        user_id: str,
        messages: List[Dict[str, str]],
        conversation_id: Optional[str] = None
    ) -> List[UserMemory]:
        """
        从对话中自动提取用户记忆。

        流程：
        1. 构建对话文本
        2. 获取已有记忆（去重参考）
        3. 调用 LLM 提取
        4. 解析结果并存储
        """
        if not messages:
            return []

        # 构建对话文本
        conversation_text = "\n".join([
            f"{'用户' if m['role'] == 'user' else 'AI'}: {m['content']}"
            for m in messages
        ])

        # 获取已有记忆
        existing = await MemoryService.get_user_memories(db, user_id, limit=50)
        existing_text = "\n".join([
            f"- [{m.memory_type}] {m.content}"
            for m in existing
        ]) if existing else "暂无已有记忆"

        # 调用 LLM 提取
        extraction_prompt = MEMORY_EXTRACTION_PROMPT.format(
            existing_memories=existing_text,
            conversation=conversation_text
        )

        content = ""
        try:
            llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model_name=settings.LLM_MODEL_NAME,
                temperature=0.3,
                max_tokens=1500,
            )

            response = await llm.ainvoke([
                SystemMessage(content="你是一个精准的用户信息提取器。只输出 JSON 数组，不要有其他内容。"),
                HumanMessage(content=extraction_prompt)
            ])

            # 解析 JSON
            content = response.content.strip()
            # 去除可能的 markdown 代码块标记
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3]

            extracted = json.loads(content)

            if not extracted or not isinstance(extracted, list):
                logger.info("本轮对话未提取到新记忆")
                return []

            # 存储提取的记忆
            results = await MemoryService.create_memories_batch(
                db=db,
                user_id=user_id,
                memories=extracted,
                source_conversation_id=conversation_id,
            )

            logger.info(f"成功提取 {len(results)} 条用户记忆: user_id={user_id}")
            return results

        except json.JSONDecodeError as e:
            logger.warning(f"记忆提取 JSON 解析失败: {e}, 原始内容: {content[:200]}")
            return []
        except Exception as e:
            logger.error(f"记忆提取失败: {e}")
            return []

    # ── 清理旧记忆 ──
    @staticmethod
    async def _cleanup_old_memories(db: AsyncSession, user_id: str):
        """当记忆数量超过上限时，清理低重要性且久未访问的记忆"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        # 统计当前记忆数
        count_result = await db.execute(
            select(func.count(UserMemory.id)).where(
                and_(UserMemory.user_id == uid, UserMemory.is_active == True)
            )
        )
        count = count_result.scalar()
        if count is None or count <= MAX_MEMORIES_PER_USER:
            return

        # 超出上限，删除低重要性记忆
        excess = count - MAX_MEMORIES_PER_USER
        result = await db.execute(
            select(UserMemory)
            .where(
                and_(UserMemory.user_id == uid, UserMemory.is_active == True)
            )
            .order_by(UserMemory.importance, UserMemory.last_accessed)
            .limit(excess)
        )
        to_delete = result.scalars().all()

        for mem in to_delete:
            mem.is_active = False

        await db.commit()
        logger.info(f"清理了 {len(to_delete)} 条低重要性记忆: user_id={user_id}")

    # ── 统计 ──
    @staticmethod
    async def get_memory_stats(db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        # 总记忆数
        total_result = await db.execute(
            select(func.count(UserMemory.id)).where(
                and_(UserMemory.user_id == uid, UserMemory.is_active == True)
            )
        )
        total = total_result.scalar() or 0

        # 按类型统计
        type_result = await db.execute(
            select(UserMemory.memory_type, func.count(UserMemory.id))
            .where(and_(UserMemory.user_id == uid, UserMemory.is_active == True))
            .group_by(UserMemory.memory_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        # 平均重要性
        avg_importance = await db.execute(
            select(func.avg(UserMemory.importance)).where(
                and_(UserMemory.user_id == uid, UserMemory.is_active == True)
            )
        )
        avg_imp = avg_importance.scalar() or 0

        return {
            "total": total,
            "by_type": by_type,
            "avg_importance": round(float(avg_imp), 2),
            "max_capacity": MAX_MEMORIES_PER_USER,
            "usage_percent": round(total / MAX_MEMORIES_PER_USER * 100, 1),
        }

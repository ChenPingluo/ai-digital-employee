# -*- coding: utf-8 -*-
"""
路由 Agent 模块（核心 — 整合长期记忆）

使用 Langchain 实现的多智能体路由系统。
负责理解用户意图并调用相应的工具完成任务。

在原有 Router Agent 基础上，新增：
1. 对话前自动检索相关记忆，注入系统提示词（个性化）
2. 对话后自动提取新记忆，持久化存储（学习）

记忆逻辑同时覆盖非流式（process_message）和流式（stream_message）两条路径：
前端实际使用的是流式接口（/chat/stream），因此流式路径同样会检索与提取记忆。
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncIterator, List, Optional
from urllib.parse import urlsplit

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.tools.todo_tools import get_todo_tools
from app.tools.meeting_tools import get_meeting_tools
from app.tools.weather_tools import get_weather_tools
from app.tools.fastgpt_tools import get_fastgpt_tools
from app.schemas.chat import ChatMessage

# ── 新增：记忆服务 ──
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# ── 系统提示词（增强版，含记忆占位符 {user_memories}）──
SYSTEM_PROMPT = """你是一个企业 AI 数字员工助手，名叫"Norma"。你的职责是帮助企业员工高效处理日常工作事务。

## 关于该用户（长期记忆）
{user_memories}

## 你的能力

1. **待办事项管理**
   - 创建新的待办事项（可设置优先级和截止日期）
   - 查询待办事项列表（可按状态筛选）
   - 更新待办事项状态（标记完成、进行中等）

2. **会议室预约**
   - 查询可用的会议室（可按容量筛选）
   - 创建会议室预约（会自动检测时间冲突）
   - 查看我的预约记录

3. **天气查询**
   - 查询指定城市的实时天气信息

4. **企业知识库**
   - 回答关于公司规章制度、流程、政策的问题
   - 提供企业内部知识的查询

## 工作原则

1. **个性化服务**：利用「关于该用户」中的记忆来提供个性化回答
   - 如果用户之前说过自己的偏好，请记住并应用
   - 如果用户提到过相关事件或人物，适当关联
   - 例如：用户之前说喜欢简洁回答，那就保持简洁
2. **友好专业**：用专业但亲切的语言与用户交流
3. **主动确认**：对于重要操作（如创建预约），先确认关键信息
4. **清晰反馈**：操作完成后给出明确的结果反馈
5. **智能理解**：理解用户的自然语言表达，提取关键信息
6. **适时建议**：在合适的时候提供有用的建议

## 交互示例

用户："帮我创建一个明天下午三点的会议"
你应该：
1. 询问会议主题
2. 确认会议室需求（人数/设备）
3. 查询可用会议室
4. 创建预约并反馈结果

用户："我有哪些待办事项"
你应该：直接调用工具查询并展示列表

用户："北京天气怎么样"
你应该：直接调用天气工具查询

## 注意事项

- 当前时间：{current_time}（北京时间），用户说的"明天"、"下周"等相对时间请基于此计算
- 信息不全：如果用户请求缺少必要信息，礼貌地询问
- 工具调用：根据用户需求选择正确的工具，一次只执行一个相关操作
- 错误处理：如果工具执行失败，向用户解释原因并提供替代方案

记住，你是用户的得力助手，让他们的工作更轻松高效！"""

# 记忆相关常量
MAX_MEMORIES_IN_CONTEXT = 15  # 每次对话注入的最大记忆数

# 太短/无实质信息的消息跳过提取，节省 LLM 成本
_TRIVIAL_KEYWORDS = {"你好", "您好", "hi", "hello", "谢谢", "感谢", "ok", "好的", "嗯", "在吗", "在"}


def _should_disable_deepseek_thinking() -> bool:
    """
    DeepSeek模型使用openai格式会出现 reasoning_content。
    但是当前 LangChain tools agent 不会在工具调用后自动回传 reasoning_content，
    会导致后续轮次触发 400 invalid_request_error。
    """
    model_name = (settings.LLM_MODEL_NAME or "").strip().lower()
    base_url = (settings.OPENAI_API_BASE or "").strip().lower()
    api_host = urlsplit(base_url).netloc.lower()

    return model_name.startswith("deepseek") or "deepseek" in api_host


def _build_llm_model_kwargs() -> dict:
    """按提供商生成额外的 LLM 请求参数。"""
    if _should_disable_deepseek_thinking():
        return {
            "extra_body": {
                "thinking": {
                    "type": "disabled"
                }
            }
        }

    return {}


def _get_current_time_str() -> str:
    """获取当前北京时间字符串"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz).strftime("%Y年%m月%d日 %H:%M（%A）")


def _format_system_prompt(current_time: str, user_memories: str) -> str:
    """格式化系统提示词，注入当前时间和用户记忆"""
    return SYSTEM_PROMPT.format(
        current_time=current_time,
        user_memories=user_memories
    )


async def _get_relevant_memories_text(
    db: AsyncSession,
    user_id: str,
    user_input: str
) -> str:
    """检索与当前问题相关的记忆，格式化为可注入提示词的文本"""
    try:
        memories = await MemoryService.get_relevant_memories(
            db=db,
            user_id=user_id,
            query=user_input,
            limit=MAX_MEMORIES_IN_CONTEXT
        )
        return MemoryService.format_memories_for_prompt(memories)
    except Exception as e:
        logger.warning(f"记忆检索失败，使用空记忆: {e}")
        return "暂无关于该用户的记忆。"


def _is_extraction_worthy(text: str) -> bool:
    """判断消息是否值得提取记忆（过滤无意义短语，节省成本）"""
    if not text:
        return False
    stripped = text.strip().lower()
    if len(stripped) < 4:
        return False
    if stripped in _TRIVIAL_KEYWORDS:
        return False
    return True


def _build_messages_for_extraction(
    history: Optional[List[ChatMessage]],
    user_input: str,
    assistant_output: str
) -> List[dict]:
    """收集最近几轮对话，用于记忆提取"""
    messages: List[dict] = []
    if history:
        messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in history[-4:]  # 最近4轮
        ])
    messages.append({"role": "user", "content": user_input})
    messages.append({"role": "assistant", "content": assistant_output})
    return messages


# 后台记忆提取任务引用集合，防止任务被 GC 回收
_bg_extraction_tasks: set = set()


async def _extract_memories_background(
    user_id: str,
    messages: List[dict],
    conversation_id: Optional[str]
) -> None:
    """
    在独立数据库会话中异步提取记忆。

    使用独立会话而非请求会话，避免：
    1. 阻塞流式响应的 [DONE] 发送
    2. 与请求会话的生命周期冲突
    """
    # 延迟导入避免循环依赖
    from app.database import async_session_maker

    try:
        async with async_session_maker() as db:
            await MemoryService.extract_memories_from_conversation(
                db=db,
                user_id=user_id,
                messages=messages,
                conversation_id=conversation_id
            )
            await db.commit()
    except Exception as e:
        logger.warning(f"后台记忆提取失败（不影响响应）: {e}")


def _schedule_memory_extraction(
    user_id: str,
    history: Optional[List[ChatMessage]],
    user_input: str,
    assistant_output: str,
    conversation_id: Optional[str]
) -> None:
    """如果本轮对话值得提取，则调度后台记忆提取任务"""
    if not _is_extraction_worthy(user_input):
        return

    messages = _build_messages_for_extraction(history, user_input, assistant_output)
    task = asyncio.create_task(
        _extract_memories_background(user_id, messages, conversation_id)
    )
    _bg_extraction_tasks.add(task)
    task.add_done_callback(_bg_extraction_tasks.discard)


def create_agent_executor(
    user_id: str,
    db_session: AsyncSession,
    streaming: bool = False,
    system_prompt: Optional[str] = None
) -> AgentExecutor:
    """
    创建 Agent 执行器

    为指定用户创建绑定了数据库会话和工具的 Agent。

    Args:
        user_id: 用户 ID
        db_session: 数据库会话
        streaming: 是否启用流式输出
        system_prompt: 可选的已格式化系统提示词。
            若为 None，则使用默认提示词（无记忆注入，含当前时间）。
            传入时通常已通过 _format_system_prompt 注入记忆。
    """
    # 初始化 LLM
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        model_name=settings.LLM_MODEL_NAME,
        temperature=0.7,
        streaming=streaming,
        max_tokens=2000,
        model_kwargs=_build_llm_model_kwargs()
    )

    # 工具
    tools = []
    tools.extend(get_todo_tools(user_id, db_session))
    tools.extend(get_meeting_tools(user_id, db_session))
    tools.extend(get_weather_tools())
    tools.extend(get_fastgpt_tools())

    # 确定系统提示词
    if system_prompt is None:
        system_prompt = _format_system_prompt(
            current_time=_get_current_time_str(),
            user_memories="暂无关于该用户的记忆。"
        )

    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # 创建 Agent
    agent = create_openai_tools_agent(llm, tools, prompt)

    # 创建执行器
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # 开发调试时打印详细日志
        handle_parsing_errors=True,
        max_iterations=5,  # 限制最大迭代次数
        return_intermediate_steps=False
    )

    return agent_executor


def _extract_stream_text(chunk: Any) -> str:
    """从 LangChain 的流式 chunk 中提取纯文本内容。"""
    if chunk is None:
        return ""

    content = getattr(chunk, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    return ""


def _extract_final_output(output: Any) -> str:
    """从 AgentExecutor 的最终输出中提取回复文本。"""
    if isinstance(output, str):
        return output

    if isinstance(output, dict):
        nested_output = output.get("output")
        if isinstance(nested_output, str):
            return nested_output
        if nested_output is not None:
            return _extract_final_output(nested_output)

    return ""


def convert_history_to_messages(
    history: Optional[List[ChatMessage]]
) -> List:
    """
    将聊天历史转换为 Langchain 消息格式

    Args:
        history: 聊天历史列表

    Returns:
        List: Langchain 消息列表
    """
    if not history:
        return []

    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            messages.append(SystemMessage(content=msg.content))

    return messages


def _get_friendly_error_message(error: Exception) -> str:
    """将底层异常转换为更稳定的用户可读错误信息。"""
    error_messages = {
        "rate limit": "请求过于频繁，请稍后再试。",
        "timeout": "处理超时，请稍后重试。",
        "connection": "网络连接问题，请检查网络后重试。",
    }

    error_str = str(error).lower()
    for key, message in error_messages.items():
        if key in error_str:
            return message

    return "抱歉，处理您的请求时遇到了问题。请稍后重试，或联系技术支持。"


async def stream_message(
    user_input: str,
    user_id: str,
    db: AsyncSession,
    conversation_id: Optional[str] = None,
    history: Optional[List[ChatMessage]] = None
) -> AsyncIterator[str]:
    """
    流式处理用户消息（增强版 — 含记忆检索与提取）

    直接消费 LangChain 事件流，将模型增量文本逐块向上游透传。
    流式开始前会检索相关记忆注入系统提示词；
    流式结束后会调度后台任务提取新记忆（不阻塞 [DONE]）。
    """
    del conversation_id  # 预留参数，便于与非流式调用保持一致

    try:
        # ── 对话前：检索相关记忆，注入系统提示词 ──
        memories_text = await _get_relevant_memories_text(db, user_id, user_input)
        system_prompt = _format_system_prompt(
            current_time=_get_current_time_str(),
            user_memories=memories_text
        )

        agent_executor = create_agent_executor(user_id, db, streaming=True, system_prompt=system_prompt)
        chat_history = convert_history_to_messages(history)

        root_event_name = agent_executor.get_name()
        streamed_any_chunk = False
        final_output = ""

        async for event in agent_executor.astream_events(
            {
                "input": user_input,
                "chat_history": chat_history
            },
            version="v1"
        ):
            event_name = event.get("event")

            if event_name == "on_chat_model_stream":
                chunk_text = _extract_stream_text(event.get("data", {}).get("chunk"))
                if chunk_text:
                    streamed_any_chunk = True
                    yield chunk_text
            elif event_name == "on_chain_end" and event.get("name") == root_event_name:
                final_output = _extract_final_output(event.get("data", {}).get("output"))

        if not streamed_any_chunk:
            fallback_output = final_output or "抱歉，我暂时无法处理您的请求。请稍后重试或换一种方式描述您的需求。"
            final_output = fallback_output
            yield fallback_output

        # ── 对话后：调度后台记忆提取（不阻塞响应）──
        _schedule_memory_extraction(
            user_id=user_id,
            history=history,
            user_input=user_input,
            assistant_output=final_output,
            conversation_id=None  # 流式上下文不直接持有 conversation_id
        )

    except Exception as e:
        logger.exception("Agent 流式处理错误")
        raise RuntimeError(_get_friendly_error_message(e)) from e


async def process_message(
    user_input: str,
    user_id: str,
    db: AsyncSession,
    conversation_id: Optional[str] = None,
    history: Optional[List[ChatMessage]] = None
) -> str:
    """
    处理用户消息（增强版 — 含记忆检索与提取）

    流程：
    1. 对话前：检索相关记忆，注入系统提示词
    2. 对话中：Agent 正常处理
    3. 对话后：提取新记忆（后台任务，不阻塞响应）
    """
    try:
        # ── 步骤 1：检索相关记忆并构建系统提示词 ──
        memories_text = await _get_relevant_memories_text(db, user_id, user_input)
        system_prompt = _format_system_prompt(
            current_time=_get_current_time_str(),
            user_memories=memories_text
        )

        # ── 步骤 2：创建 Agent（使用增强版提示词）──
        agent_executor = create_agent_executor(
            user_id, db, streaming=False, system_prompt=system_prompt
        )

        # 转换历史消息
        chat_history = convert_history_to_messages(history)

        # 调用 Agent
        result = await agent_executor.ainvoke({
            "input": user_input,
            "chat_history": chat_history
        })

        # 提取输出
        output = result.get("output", "")
        if not output:
            return "抱歉，我暂时无法处理您的请求。请稍后重试或换一种方式描述您的需求。"

        # ── 步骤 3：调度后台记忆提取（不阻塞响应）──
        _schedule_memory_extraction(
            user_id=user_id,
            history=history,
            user_input=user_input,
            assistant_output=output,
            conversation_id=conversation_id
        )

        return output

    except Exception as e:
        logger.exception("Agent 处理错误")
        return _get_friendly_error_message(e)

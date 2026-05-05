# -*- coding: utf-8 -*-
"""
路由 Agent 模块（核心）

使用 Langchain 实现的多智能体路由系统。
负责理解用户意图并调用相应的工具完成任务。
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

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


# ==================== 系统提示词 ====================
SYSTEM_PROMPT = """你是一个企业 AI 数字员工助手，名叫"小智"。你的职责是帮助企业员工高效处理日常工作事务。

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

1. **友好专业**：用专业但亲切的语言与用户交流
2. **主动确认**：对于重要操作（如创建预约），先确认关键信息
3. **清晰反馈**：操作完成后给出明确的结果反馈
4. **智能理解**：理解用户的自然语言表达，提取关键信息
5. **适时建议**：在合适的时候提供有用的建议

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


def create_agent_executor(
    user_id: str,
    db_session: AsyncSession
) -> AgentExecutor:
    """
    创建 Agent 执行器
    
    为指定用户创建绑定了数据库会话和工具的 Agent。
    
    Args:
        user_id: 用户 ID
        db_session: 数据库会话
        
    Returns:
        AgentExecutor: 配置好的 Agent 执行器
    """
    # 初始化 LLM
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        model_name=settings.LLM_MODEL_NAME,
        temperature=0.7,
        streaming=False,
        max_tokens=2000
    )
    
    # 收集所有工具
    tools = []
    
    # 添加待办事项工具（需要用户绑定）
    tools.extend(get_todo_tools(user_id, db_session))
    
    # 添加会议室工具（需要用户绑定）
    tools.extend(get_meeting_tools(user_id, db_session))
    
    # 添加天气工具（无需用户绑定）
    tools.extend(get_weather_tools())
    
    # 添加知识库工具（无需用户绑定）
    tools.extend(get_fastgpt_tools())
    
    # 获取当前北京时间，注入到系统提示词中
    beijing_tz = timezone(timedelta(hours=8))
    current_time = datetime.now(beijing_tz).strftime("%Y年%m月%d日 %H:%M（%A）")
    system_prompt_with_time = SYSTEM_PROMPT.format(current_time=current_time)
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_with_time),
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


async def process_message(
    user_input: str,
    user_id: str,
    db: AsyncSession,
    conversation_id: Optional[str] = None,
    history: Optional[List[ChatMessage]] = None
) -> str:
    """
    处理用户消息
    
    接收用户输入，通过 Agent 理解意图并执行相应操作。
    
    Args:
        user_input: 用户输入的消息
        user_id: 用户 ID
        db: 数据库会话
        conversation_id: 会话 ID（用于日志和追踪）
        history: 历史消息列表
        
    Returns:
        str: Agent 的响应消息
    """
    try:
        # 创建 Agent 执行器
        agent_executor = create_agent_executor(user_id, db)
        
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
        
        return output
        
    except Exception as e:
        # 记录错误（生产环境应使用日志系统）
        print(f"Agent 处理错误: {str(e)}")
        
        # 返回友好的错误消息
        error_messages = {
            "Rate limit": "请求过于频繁，请稍后再试。",
            "timeout": "处理超时，请稍后重试。",
            "connection": "网络连接问题，请检查网络后重试。",
        }
        
        error_str = str(e).lower()
        for key, msg in error_messages.items():
            if key.lower() in error_str:
                return msg
        
        return "抱歉，处理您的请求时遇到了问题。请稍后重试，或联系技术支持。"

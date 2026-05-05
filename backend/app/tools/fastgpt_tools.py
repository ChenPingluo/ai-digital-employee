# -*- coding: utf-8 -*-
"""
FastGPT 知识库查询 Langchain 工具模块

提供用于 AI Agent 的企业知识库查询工具。
"""

import asyncio
from typing import List

from langchain.tools import StructuredTool
from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field

from app.services import fastgpt_service


# ==================== 工具参数模式 ====================

class QueryKnowledgeBaseInput(BaseModel):
    """查询知识库的参数模式"""
    question: str = Field(
        description="要查询的问题，例如'公司的报销流程是什么？'、'年假政策是怎样的？'"
    )


# ==================== 工具函数 ====================

def query_knowledge_base(question: str) -> str:
    """
    查询企业知识库
    
    使用 FastGPT 知识库回答企业相关问题。
    
    Args:
        question: 用户问题
        
    Returns:
        str: 知识库的回答
    """
    try:
        async def _query():
            return await fastgpt_service.query_fastgpt(question)
        
        # 执行异步函数
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _query())
                answer = future.result()
        except RuntimeError:
            answer = asyncio.run(_query())
        
        # 检查是否为错误响应
        if answer.startswith("知识库"):
            return f"❌ {answer}"
        
        # 格式化输出
        result = f"📚 知识库查询结果\n\n"
        result += f"❓ 问题：{question}\n\n"
        result += f"💡 回答：\n{answer}"
        
        return result
        
    except Exception as e:
        return f"❌ 知识库查询异常：{str(e)}"


def get_fastgpt_tools() -> List[BaseTool]:
    """
    获取 FastGPT 知识库工具列表
    
    Returns:
        List[BaseTool]: Langchain 工具列表
    """
    tools = [
        StructuredTool.from_function(
            func=query_knowledge_base,
            name="query_knowledge_base",
            description="查询企业知识库，获取公司规章制度、流程说明、产品信息等企业内部知识。适用于询问报销流程、年假政策、公司制度等问题。",
            args_schema=QueryKnowledgeBaseInput
        )
    ]
    
    return tools

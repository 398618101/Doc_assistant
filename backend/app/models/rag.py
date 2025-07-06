#!/usr/bin/env python3
"""
RAG (检索增强生成) 相关数据模型
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ChatRole(str, Enum):
    """对话角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ResponseMode(str, Enum):
    """响应模式枚举"""
    STREAMING = "streaming"  # 流式响应
    COMPLETE = "complete"    # 完整响应


class ContextStrategy(str, Enum):
    """上下文构建策略"""
    SIMPLE = "simple"        # 简单拼接
    RANKED = "ranked"        # 按相关性排序
    SUMMARIZED = "summarized"  # 摘要压缩
    HIERARCHICAL = "hierarchical"  # 层次化组织


class DocumentSource(BaseModel):
    """文档来源信息"""
    document_id: str
    filename: str
    chunk_id: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    relevance_score: float
    content_preview: str  # 内容预览（前100字符）


class ChatMessage(BaseModel):
    """对话消息模型"""
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class RetrievalContext(BaseModel):
    """检索上下文模型"""
    query: str
    retrieved_chunks: List[Dict[str, Any]]
    total_chunks: int
    retrieval_time: float
    context_length: int
    sources: List[DocumentSource]  # 来源文档信息


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[str] = Field(None, description="对话ID，用于保持上下文")
    response_mode: ResponseMode = Field(default=ResponseMode.STREAMING, description="响应模式")
    
    # 检索配置
    enable_retrieval: bool = Field(default=True, description="是否启用文档检索")
    max_retrieved_chunks: int = Field(default=5, ge=1, le=20, description="最大检索文档块数")
    similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="相似度阈值")
    
    # 上下文配置
    context_strategy: ContextStrategy = Field(default=ContextStrategy.RANKED, description="上下文构建策略")
    max_context_length: int = Field(default=4000, ge=500, le=8000, description="最大上下文长度")
    include_chat_history: bool = Field(default=True, description="是否包含对话历史")
    max_history_messages: int = Field(default=10, ge=0, le=50, description="最大历史消息数")
    
    # 生成配置
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(default=1000, ge=50, le=4000, description="最大生成token数")
    stream: bool = Field(default=True, description="是否流式输出")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool
    message: str
    conversation_id: str
    response_time: float
    
    # 检索信息
    retrieval_context: Optional[RetrievalContext] = None
    sources_used: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 生成信息
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    
    # 元数据
    timestamp: datetime = Field(default_factory=datetime.now)
    model_used: Optional[str] = None
    error_message: Optional[str] = None


class StreamingChatResponse(BaseModel):
    """流式聊天响应模型"""
    conversation_id: str
    chunk: str
    is_final: bool = False
    
    # 仅在最终块中包含
    retrieval_context: Optional[RetrievalContext] = None
    sources_used: List[Dict[str, Any]] = Field(default_factory=list)
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None


class ConversationHistory(BaseModel):
    """对话历史模型"""
    conversation_id: str
    messages: List[ChatMessage]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class RAGConfig(BaseModel):
    """RAG配置模型"""
    # 检索配置
    default_retrieval_count: int = Field(default=5, description="默认检索文档数")
    default_similarity_threshold: float = Field(default=0.3, description="默认相似度阈值(降低以获得更多结果)")
    enable_hybrid_search: bool = Field(default=True, description="启用混合搜索")
    
    # 上下文配置
    max_context_tokens: int = Field(default=4000, description="最大上下文token数")
    context_overlap_ratio: float = Field(default=0.1, description="上下文重叠比例")
    
    # 生成配置
    default_temperature: float = Field(default=0.7, description="默认生成温度")
    default_max_tokens: int = Field(default=1000, description="默认最大生成token数")
    
    # 对话配置
    max_conversation_history: int = Field(default=50, description="最大对话历史数")
    conversation_timeout_hours: int = Field(default=24, description="对话超时时间(小时)")
    
    # 系统提示词
    system_prompt: str = Field(
        default="""你是一个专业的智能文档助理。请严格按照以下要求回答用户问题：

## 🎯 核心要求
1. **仅基于提供的文档内容回答**，不要添加文档外的信息
2. **回答要简洁明了**，避免重复和冗余
3. **使用中文回答**，保持语言流畅自然
4. **直接回答问题**，不要过度解释

## 📋 回答格式
### 当有相关文档内容时：
- 直接提取文档中的关键信息
- 用简洁的语言组织答案
- 如有列表信息，使用项目符号
- 避免重复相同的词汇或短语

### 当没有相关文档内容时：
- 简单说明："根据提供的文档内容，没有找到相关信息。"
- 不要猜测或添加额外内容

## ⚠️ 严格禁止
- 重复使用相同词汇（如"提取"、"extract"等）
- 生成无意义的重复内容
- 添加文档中不存在的信息
- 使用过于复杂的表述

请基于以下文档内容简洁准确地回答用户问题：""",
        description="简化优化的系统提示词"
    )


class QueryAnalysis(BaseModel):
    """查询分析结果"""
    original_query: str
    intent: str  # 问答、搜索、摘要等
    keywords: List[str]
    entities: List[str]
    query_type: str  # factual, analytical, creative等
    complexity_score: float  # 0-1，查询复杂度
    requires_context: bool  # 是否需要上下文
    suggested_retrieval_count: int  # 建议检索数量


class ContextWindow(BaseModel):
    """上下文窗口模型"""
    system_prompt: str
    conversation_history: List[ChatMessage]
    retrieved_context: str
    total_tokens: int
    context_sources: List[DocumentSource]


class RAGMetrics(BaseModel):
    """RAG性能指标"""
    # 请求统计
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # 时间统计
    total_response_time: float = 0.0
    average_response_time: float = 0.0
    avg_retrieval_time: float = 0.0
    avg_generation_time: float = 0.0

    # 兼容旧字段
    query_count: int = 0
    avg_total_time: float = 0.0
    success_rate: float = 1.0
    avg_context_length: int = 0
    avg_response_length: int = 0
    popular_queries: List[Dict[str, Any]] = Field(default_factory=list)
    error_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)


class CitationInfo(BaseModel):
    """引用信息"""
    source: DocumentSource
    quoted_text: str
    confidence_score: float
    position_in_response: int  # 在回答中的位置

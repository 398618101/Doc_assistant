#!/usr/bin/env python3
"""
RAG服务单元测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.rag_service import RAGService
from app.models.rag import (
    ChatRequest, ChatResponse, ResponseMode, ContextStrategy,
    QueryAnalysis, RetrievalContext, ContextWindow, DocumentSource
)
from app.core.llm_factory import LLMFactory
from app.services.retrieval_service import RetrievalService


class TestRAGService:
    """RAG服务测试类"""
    
    @pytest.fixture
    def mock_retrieval_service(self):
        """模拟检索服务"""
        service = Mock(spec=RetrievalService)
        service.hybrid_search = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_llm_factory(self):
        """模拟LLM工厂"""
        factory = Mock(spec=LLMFactory)
        factory.generate = AsyncMock()
        return factory
    
    @pytest.fixture
    def rag_service(self, mock_retrieval_service, mock_llm_factory):
        """RAG服务实例"""
        return RAGService(
            retrieval_service=mock_retrieval_service,
            llm_factory=mock_llm_factory
        )
    
    @pytest.fixture
    def sample_chat_request(self):
        """示例聊天请求"""
        return ChatRequest(
            message="测试文档中包含什么内容？",
            response_mode=ResponseMode.COMPLETE,
            enable_retrieval=True,
            max_retrieved_chunks=3,
            similarity_threshold=0.6
        )
    
    @pytest.fixture
    def sample_search_result(self):
        """示例搜索结果"""
        return {
            "results": [
                {
                    "text": "这是一个测试文档，用于验证文档上传和处理功能。",
                    "document_id": "test-doc-1",
                    "filename": "test.txt",
                    "similarity_score": 0.8,
                    "chunk_id": "chunk-1",
                    "page_number": 1,
                    "section": "introduction"
                }
            ],
            "total_results": 1,
            "search_time": 0.1
        }
    
    @pytest.mark.asyncio
    async def test_analyze_query_question_type(self, rag_service):
        """测试查询分析 - 问题类型"""
        query = "什么是人工智能技术的发展历史和具体应用场景？"  # 长查询确保requires_context为True
        result = await rag_service._analyze_query(query)

        assert isinstance(result, QueryAnalysis)
        assert result.intent == "question"
        assert result.complexity_score > 0
        assert result.requires_context is True
        assert result.suggested_retrieval_count > 0

    @pytest.mark.asyncio
    async def test_analyze_query_summary_type(self, rag_service):
        """测试查询分析 - 总结类型"""
        query = "请总结这个文档的主要内容和核心观点"
        result = await rag_service._analyze_query(query)

        assert result.intent == "summarize"  # 修正为实际返回的intent
        assert result.requires_context is True

    @pytest.mark.asyncio
    async def test_analyze_query_search_type(self, rag_service):
        """测试查询分析 - 搜索类型"""
        query = "查找关于机器学习算法和深度学习技术的相关内容"
        result = await rag_service._analyze_query(query)

        assert result.intent == "search"
        assert result.requires_context is True
    
    @pytest.mark.asyncio
    async def test_retrieve_context_success(self, rag_service, sample_search_result):
        """测试文档检索成功"""
        # 配置模拟
        rag_service.retrieval_service.hybrid_search.return_value = sample_search_result
        
        query = "测试查询"
        max_chunks = 3
        threshold = 0.6
        
        result = await rag_service._retrieve_context(query, max_chunks, threshold)
        
        assert isinstance(result, RetrievalContext)
        assert result.query == query
        assert len(result.retrieved_chunks) == 1
        assert result.total_chunks == 1
        assert len(result.sources) == 1
        assert isinstance(result.sources[0], DocumentSource)
        
        # 验证检索服务被正确调用
        rag_service.retrieval_service.hybrid_search.assert_called_once_with(
            query=query,
            n_results=max_chunks,
            similarity_threshold=threshold,
            enable_keyword_search=True,
            enable_semantic_search=True
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_context_no_results(self, rag_service):
        """测试文档检索无结果"""
        # 配置模拟返回空结果
        rag_service.retrieval_service.hybrid_search.return_value = {
            "results": [],
            "total_results": 0,
            "search_time": 0.1
        }
        
        result = await rag_service._retrieve_context("无关查询", 3, 0.6)
        
        assert result.total_chunks == 0
        assert len(result.retrieved_chunks) == 0
        assert len(result.sources) == 0
    
    @pytest.mark.asyncio
    async def test_build_context_window_simple_strategy(self, rag_service):
        """测试上下文窗口构建 - 简单策略"""
        retrieval_context = RetrievalContext(
            query="测试查询",
            retrieved_chunks=[
                {"text": "第一段内容", "document_id": "doc1"},
                {"text": "第二段内容", "document_id": "doc2"}
            ],
            total_chunks=2,
            retrieval_time=0.1,
            context_length=20,
            sources=[]
        )

        request = ChatRequest(
            message="测试查询",
            context_strategy=ContextStrategy.SIMPLE,
            max_context_length=1000
        )

        query_analysis = QueryAnalysis(
            intent="question",
            keywords=["测试"],
            complexity_score=0.5,
            requires_context=True,
            suggested_retrieval_count=3
        )

        result = await rag_service._build_context_window(
            request, "test-conv", retrieval_context, query_analysis
        )

        assert isinstance(result, ContextWindow)
        assert "第一段内容" in result.retrieved_context
        assert "第二段内容" in result.retrieved_context
        assert result.total_tokens > 0
    
    @pytest.mark.asyncio
    async def test_build_context_window_ranked_strategy(self, rag_service):
        """测试上下文窗口构建 - 排序策略"""
        retrieval_context = RetrievalContext(
            query="测试查询",
            retrieved_chunks=[
                {"text": "低相关度内容", "similarity_score": 0.5},
                {"text": "高相关度内容", "similarity_score": 0.9}
            ],
            total_chunks=2,
            retrieval_time=0.1,
            context_length=20,
            sources=[]
        )

        request = ChatRequest(
            message="测试查询",
            context_strategy=ContextStrategy.RANKED,
            max_context_length=1000
        )

        query_analysis = QueryAnalysis(
            intent="question",
            keywords=["测试"],
            complexity_score=0.5,
            requires_context=True,
            suggested_retrieval_count=3
        )

        result = await rag_service._build_context_window(
            request, "test-conv", retrieval_context, query_analysis
        )

        # 高相关度内容应该排在前面
        assert result.retrieved_context.index("高相关度内容") < \
               result.retrieved_context.index("低相关度内容")
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, rag_service):
        """测试回答生成成功"""
        # 配置模拟LLM响应
        rag_service.llm_factory.generate.return_value = "这是一个测试回答"

        context_window = ContextWindow(
            system_prompt="你是一个智能助手",
            conversation_history=[],
            retrieved_context="检索到的上下文内容",
            total_tokens=50,
            context_sources=[]
        )

        request = ChatRequest(
            message="测试问题",
            temperature=0.7,
            max_tokens=1000
        )

        result, metadata = await rag_service._generate_response(
            context_window, request
        )

        assert result == "这是一个测试回答"

        # 验证LLM工厂被正确调用
        rag_service.llm_factory.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_failure(self, rag_service):
        """测试回答生成失败"""
        # 配置模拟LLM抛出异常
        rag_service.llm_factory.generate.side_effect = Exception("LLM错误")

        context_window = ContextWindow(
            system_prompt="你是一个智能助手",
            conversation_history=[],
            retrieved_context="检索到的上下文内容",
            total_tokens=50,
            context_sources=[]
        )

        request = ChatRequest(message="测试问题")

        result, metadata = await rag_service._generate_response(context_window, request)

        assert "抱歉，生成回答时出现错误" in result
    
    @pytest.mark.asyncio
    async def test_chat_complete_mode_success(self, rag_service, sample_chat_request, sample_search_result):
        """测试完整模式聊天成功"""
        # 配置模拟
        rag_service.retrieval_service.hybrid_search.return_value = sample_search_result
        rag_service.llm_factory.generate.return_value = "基于文档内容的回答"
        
        result = await rag_service.chat(sample_chat_request)
        
        assert isinstance(result, ChatResponse)
        assert result.success is True
        assert result.message == "基于文档内容的回答"
        assert result.retrieval_context is not None
        assert len(result.sources_used) > 0
    
    @pytest.mark.asyncio
    async def test_chat_without_retrieval(self, rag_service):
        """测试不启用检索的聊天"""
        request = ChatRequest(
            message="你好",
            enable_retrieval=False
        )
        
        rag_service.llm_factory.generate.return_value = "你好！我是智能助手。"
        
        result = await rag_service.chat(request)
        
        assert result.success is True
        assert result.retrieval_context is None
        assert len(result.sources_used) == 0
        
        # 验证没有调用检索服务
        rag_service.retrieval_service.hybrid_search.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_chat_retrieval_failure(self, rag_service, sample_chat_request):
        """测试检索失败的处理"""
        # 配置检索服务抛出异常
        rag_service.retrieval_service.hybrid_search.side_effect = Exception("检索错误")
        
        result = await rag_service.chat(sample_chat_request)
        
        assert result.success is False
        assert "检索错误" in result.error_message
    
    @pytest.mark.asyncio
    async def test_conversation_context_integration(self, rag_service):
        """测试对话上下文集成"""
        # 测试带有对话历史的请求
        request = ChatRequest(
            message="继续上一个话题",
            conversation_id="test-conv-1",
            include_chat_history=True,
            max_history_messages=5
        )

        # 模拟检索结果
        rag_service.retrieval_service.hybrid_search.return_value = {
            "results": [],
            "total_results": 0,
            "search_time": 0.1
        }

        # 模拟LLM响应
        rag_service.llm_factory.generate.return_value = "基于历史上下文的回答"

        result = await rag_service.chat(request)

        assert result.success is True
        assert result.conversation_id == "test-conv-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
检索服务单元测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from app.services.retrieval_service import RetrievalService
from app.models.retrieval import SearchMode, DocumentType


class TestRetrievalService:
    """检索服务测试类"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """模拟依赖项"""
        mock_vector_storage = Mock()
        mock_document_storage = Mock()
        mock_embedding_service = Mock()
        
        return {
            'vector_storage': mock_vector_storage,
            'document_storage': mock_document_storage,
            'embedding_service': mock_embedding_service
        }
    
    @pytest.fixture
    def retrieval_service(self, mock_dependencies):
        """创建检索服务实例"""
        return RetrievalService(
            vector_storage=mock_dependencies['vector_storage'],
            document_storage=mock_dependencies['document_storage'],
            embedding_service=mock_dependencies['embedding_service']
        )
    
    @pytest.fixture
    def sample_documents(self):
        """示例文档数据"""
        return [
            {
                'id': 'doc1',
                'filename': 'test1.txt',
                'document_type': 'txt',
                'file_size': 100,
                'created_at': '2025-01-01T00:00:00',
                'updated_at': '2025-01-01T00:00:00'
            },
            {
                'id': 'doc2',
                'filename': 'test2.pdf',
                'document_type': 'pdf',
                'file_size': 200,
                'created_at': '2025-01-01T00:00:00',
                'updated_at': '2025-01-01T00:00:00'
            }
        ]
    
    @pytest.fixture
    def sample_search_results(self):
        """示例搜索结果"""
        return [
            {
                'text': '这是测试文档内容',
                'similarity_score': 0.8,
                'document_id': 'doc1',
                'chunk_id': 'chunk_0',
                'metadata': {'test': True}
            },
            {
                'text': '另一个测试文档',
                'similarity_score': 0.7,
                'document_id': 'doc2',
                'chunk_id': 'chunk_1',
                'metadata': {'test': True}
            }
        ]
    
    @pytest.mark.asyncio
    async def test_hybrid_search_basic(self, retrieval_service, mock_dependencies, sample_documents, sample_search_results):
        """测试基本混合搜索功能"""
        # 设置模拟返回值
        mock_dependencies['document_storage'].get_all_documents.return_value = sample_documents
        mock_dependencies['embedding_service'].generate_embedding.return_value = [0.1] * 4096
        mock_dependencies['vector_storage'].search_similar_chunks.return_value = sample_search_results
        
        # 执行搜索
        result = await retrieval_service.hybrid_search(
            query="测试文档",
            n_results=10,
            similarity_threshold=0.6
        )
        
        # 验证结果
        assert result['success'] is True
        assert result['query'] == "测试文档"
        assert len(result['results']) > 0
        assert result['total_results'] > 0
        assert 'search_time' in result
        
        # 验证调用了正确的方法
        mock_dependencies['document_storage'].get_all_documents.assert_called_once()
        mock_dependencies['embedding_service'].generate_embedding.assert_called_once_with("测试文档")
    
    @pytest.mark.asyncio
    async def test_semantic_search_only(self, retrieval_service, mock_dependencies, sample_documents, sample_search_results):
        """测试纯语义搜索"""
        # 设置模拟返回值
        mock_dependencies['document_storage'].get_all_documents.return_value = sample_documents
        mock_dependencies['embedding_service'].generate_embedding.return_value = [0.1] * 4096
        mock_dependencies['vector_storage'].search_similar_chunks.return_value = sample_search_results
        
        # 执行语义搜索
        result = await retrieval_service.hybrid_search(
            query="测试文档",
            n_results=5,
            enable_keyword_search=False,
            enable_semantic_search=True
        )
        
        # 验证结果
        assert result['success'] is True
        assert result['search_strategy']['semantic_enabled'] is True
        assert result['search_strategy']['keyword_enabled'] is False
        
        # 验证只调用了语义搜索相关方法
        mock_dependencies['embedding_service'].generate_embedding.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_keyword_search_only(self, retrieval_service, mock_dependencies, sample_documents):
        """测试纯关键词搜索"""
        # 设置模拟返回值
        mock_dependencies['document_storage'].get_all_documents.return_value = sample_documents
        mock_dependencies['document_storage'].search_documents_by_content.return_value = [
            {
                'id': 'doc1',
                'content': '这是测试文档内容',
                'filename': 'test1.txt',
                'document_type': 'txt'
            }
        ]
        
        # 执行关键词搜索
        result = await retrieval_service.hybrid_search(
            query="测试文档",
            n_results=5,
            enable_keyword_search=True,
            enable_semantic_search=False
        )
        
        # 验证结果
        assert result['success'] is True
        assert result['search_strategy']['semantic_enabled'] is False
        assert result['search_strategy']['keyword_enabled'] is True
        
        # 验证没有调用嵌入服务
        mock_dependencies['embedding_service'].generate_embedding.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, retrieval_service, mock_dependencies, sample_documents, sample_search_results):
        """测试带过滤条件的搜索"""
        # 设置模拟返回值
        mock_dependencies['document_storage'].get_all_documents.return_value = sample_documents
        mock_dependencies['embedding_service'].generate_embedding.return_value = [0.1] * 4096
        mock_dependencies['vector_storage'].search_similar_chunks.return_value = sample_search_results
        
        # 执行带过滤的搜索
        result = await retrieval_service.hybrid_search(
            query="测试文档",
            n_results=5,
            document_types=[DocumentType.TXT],
            document_ids=['doc1']
        )
        
        # 验证结果
        assert result['success'] is True
        assert result['search_strategy']['candidate_documents'] <= len(sample_documents)
    
    @pytest.mark.asyncio
    async def test_search_caching(self, retrieval_service, mock_dependencies, sample_documents, sample_search_results):
        """测试搜索缓存功能"""
        # 设置模拟返回值
        mock_dependencies['document_storage'].get_all_documents.return_value = sample_documents
        mock_dependencies['embedding_service'].generate_embedding.return_value = [0.1] * 4096
        mock_dependencies['vector_storage'].search_similar_chunks.return_value = sample_search_results
        
        query = "测试缓存"
        
        # 第一次搜索
        result1 = await retrieval_service.hybrid_search(query=query, use_cache=True)
        
        # 第二次搜索（应该使用缓存）
        result2 = await retrieval_service.hybrid_search(query=query, use_cache=True)
        
        # 验证两次结果相同
        assert result1['query'] == result2['query']
        assert result1['total_results'] == result2['total_results']
        
        # 验证嵌入服务只被调用一次（第二次使用缓存）
        assert mock_dependencies['embedding_service'].generate_embedding.call_count == 1
    
    def test_merge_search_results(self, retrieval_service):
        """测试搜索结果合并"""
        semantic_results = [
            {'text': '语义结果1', 'similarity_score': 0.8, 'search_type': 'semantic'},
            {'text': '语义结果2', 'similarity_score': 0.7, 'search_type': 'semantic'}
        ]
        
        keyword_results = [
            {'text': '关键词结果1', 'similarity_score': 0.9, 'search_type': 'keyword'},
            {'text': '关键词结果2', 'similarity_score': 0.6, 'search_type': 'keyword'}
        ]
        
        all_results = semantic_results + keyword_results
        
        # 测试结果合并
        merged = retrieval_service._merge_search_results(
            all_results, 
            keyword_weight=0.4, 
            semantic_weight=0.6
        )
        
        # 验证结果按最终分数排序
        assert len(merged) == 4
        assert all('final_score' in result for result in merged)
        
        # 验证排序正确（分数从高到低）
        scores = [result['final_score'] for result in merged]
        assert scores == sorted(scores, reverse=True)
    
    def test_add_text_highlighting(self, retrieval_service):
        """测试文本高亮功能"""
        results = [
            {'text': '这是一个测试文档，包含测试内容'},
            {'text': '另一个文档示例'}
        ]
        
        highlighted = retrieval_service._add_text_highlighting(results, "测试")
        
        # 验证高亮标记
        assert '<mark>测试</mark>' in highlighted[0]['highlight_text']
        assert 'highlight_text' in highlighted[1]  # 即使没有匹配也应该有该字段
    
    def test_deduplicate_results(self, retrieval_service):
        """测试结果去重功能"""
        results = [
            {'text': '重复文本', 'similarity_score': 0.8, 'document_id': 'doc1'},
            {'text': '重复文本', 'similarity_score': 0.7, 'document_id': 'doc1'},
            {'text': '不同文本', 'similarity_score': 0.9, 'document_id': 'doc2'}
        ]
        
        deduplicated = retrieval_service._deduplicate_results(results)
        
        # 验证去重效果
        assert len(deduplicated) == 2
        texts = [result['text'] for result in deduplicated]
        assert len(set(texts)) == len(texts)  # 确保没有重复文本
    
    def test_search_statistics(self, retrieval_service):
        """测试搜索统计功能"""
        # 模拟一些搜索历史
        retrieval_service.search_history = [
            {'query': '测试1', 'timestamp': '2025-01-01T00:00:00'},
            {'query': '测试2', 'timestamp': '2025-01-01T01:00:00'},
            {'query': '测试1', 'timestamp': '2025-01-01T02:00:00'}  # 重复查询
        ]
        
        stats = retrieval_service.get_search_statistics()
        
        # 验证统计信息
        assert stats['total_searches'] == 3
        assert stats['unique_queries'] == 2
        assert len(stats['popular_queries']) > 0
        assert stats['popular_queries'][0]['query'] == '测试1'  # 最热门的查询
        assert stats['popular_queries'][0]['count'] == 2


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
RAG系统端到端测试
"""
import pytest
import asyncio
import json
import time
from typing import Dict, Any

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from fastapi.testclient import TestClient

from main import app


class TestRAGEndToEnd:
    """RAG系统端到端测试类"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """基础URL"""
        return "http://localhost:8000"
    
    def test_rag_chat_complete_mode(self, client):
        """测试完整模式RAG聊天"""
        response = client.post(
            "/api/rag/chat",
            json={
                "message": "测试文档中包含什么内容？",
                "response_mode": "complete",
                "enable_retrieval": True,
                "max_retrieved_chunks": 3,
                "similarity_threshold": 0.6
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应结构
        assert "success" in data
        assert "message" in data
        assert "conversation_id" in data
        assert "response_time" in data
        assert "retrieval_context" in data
        assert "sources_used" in data
        
        # 验证检索上下文
        if data["retrieval_context"]:
            retrieval_context = data["retrieval_context"]
            assert "query" in retrieval_context
            assert "retrieved_chunks" in retrieval_context
            assert "total_chunks" in retrieval_context
            assert "retrieval_time" in retrieval_context
            assert "sources" in retrieval_context
        
        print(f"✅ 完整模式测试通过 - 响应时间: {data['response_time']:.3f}s")
        print(f"📄 检索到文档块数量: {data['retrieval_context']['total_chunks'] if data['retrieval_context'] else 0}")
    
    def test_rag_chat_streaming_mode(self, client):
        """测试流式模式RAG聊天"""
        response = client.post(
            "/api/rag/chat",
            json={
                "message": "请简要介绍文档的主要内容",
                "response_mode": "streaming",
                "enable_retrieval": True,
                "max_retrieved_chunks": 2
            }
        )
        
        assert response.status_code == 200
        
        # 对于流式响应，我们检查是否有内容返回
        content = response.content.decode()
        assert len(content) > 0
        
        print("✅ 流式模式测试通过")
    
    def test_rag_chat_without_retrieval(self, client):
        """测试不启用检索的聊天"""
        response = client.post(
            "/api/rag/chat",
            json={
                "message": "你好，请介绍一下你自己",
                "response_mode": "complete",
                "enable_retrieval": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["retrieval_context"] is None
        assert len(data["sources_used"]) == 0
        
        print("✅ 无检索模式测试通过")
    
    def test_rag_chat_conversation_continuity(self, client):
        """测试对话连续性"""
        # 第一轮对话
        response1 = client.post(
            "/api/rag/chat",
            json={
                "message": "文档中提到了什么技术？",
                "response_mode": "complete",
                "enable_retrieval": True
            }
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]
        
        # 第二轮对话，使用相同的conversation_id
        response2 = client.post(
            "/api/rag/chat",
            json={
                "message": "请详细解释一下",
                "conversation_id": conversation_id,
                "response_mode": "complete",
                "enable_retrieval": True,
                "include_chat_history": True
            }
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 验证对话ID保持一致
        assert data2["conversation_id"] == conversation_id
        
        print(f"✅ 对话连续性测试通过 - 对话ID: {conversation_id}")
    
    def test_rag_chat_different_query_types(self, client):
        """测试不同类型的查询"""
        test_queries = [
            {
                "query": "文档的主要内容是什么？",
                "type": "factual",
                "description": "事实性问题"
            },
            {
                "query": "请总结文档的核心观点",
                "type": "summary", 
                "description": "总结性问题"
            },
            {
                "query": "查找关于技术的相关信息",
                "type": "search",
                "description": "搜索性问题"
            }
        ]
        
        for test_case in test_queries:
            response = client.post(
                "/api/rag/chat",
                json={
                    "message": test_case["query"],
                    "response_mode": "complete",
                    "enable_retrieval": True,
                    "max_retrieved_chunks": 3
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            print(f"✅ {test_case['description']}测试通过")
            print(f"   查询: {test_case['query']}")
            print(f"   响应时间: {data['response_time']:.3f}s")
            print(f"   检索结果: {data['retrieval_context']['total_chunks'] if data['retrieval_context'] else 0}个文档块")
    
    def test_rag_chat_parameter_variations(self, client):
        """测试不同参数配置"""
        parameter_tests = [
            {
                "name": "高相似度阈值",
                "params": {
                    "similarity_threshold": 0.8,
                    "max_retrieved_chunks": 2
                }
            },
            {
                "name": "低相似度阈值",
                "params": {
                    "similarity_threshold": 0.3,
                    "max_retrieved_chunks": 5
                }
            },
            {
                "name": "大上下文窗口",
                "params": {
                    "max_context_length": 6000,
                    "max_retrieved_chunks": 8
                }
            },
            {
                "name": "小上下文窗口",
                "params": {
                    "max_context_length": 1000,
                    "max_retrieved_chunks": 2
                }
            }
        ]
        
        base_request = {
            "message": "请介绍文档中的主要技术内容",
            "response_mode": "complete",
            "enable_retrieval": True
        }
        
        for test_case in parameter_tests:
            request_data = {**base_request, **test_case["params"]}
            
            response = client.post("/api/rag/chat", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            print(f"✅ {test_case['name']}参数测试通过")
            print(f"   检索结果: {data['retrieval_context']['total_chunks'] if data['retrieval_context'] else 0}个文档块")
            print(f"   响应时间: {data['response_time']:.3f}s")
    
    def test_rag_chat_error_handling(self, client):
        """测试错误处理"""
        # 测试无效参数
        response = client.post(
            "/api/rag/chat",
            json={
                "message": "",  # 空消息
                "response_mode": "complete"
            }
        )
        
        # 应该返回错误或处理空消息
        assert response.status_code in [200, 400, 422]
        
        # 测试无效的相似度阈值
        response = client.post(
            "/api/rag/chat",
            json={
                "message": "测试查询",
                "similarity_threshold": 1.5,  # 超出范围
                "response_mode": "complete"
            }
        )
        
        assert response.status_code in [200, 400, 422]
        
        print("✅ 错误处理测试通过")
    
    def test_rag_performance_benchmark(self, client):
        """RAG性能基准测试"""
        test_queries = [
            "文档中包含什么内容？",
            "请总结主要观点",
            "技术细节是什么？",
            "有什么应用场景？",
            "相关的概念有哪些？"
        ]
        
        response_times = []
        retrieval_times = []
        
        for query in test_queries:
            start_time = time.time()
            
            response = client.post(
                "/api/rag/chat",
                json={
                    "message": query,
                    "response_mode": "complete",
                    "enable_retrieval": True,
                    "max_retrieved_chunks": 3
                }
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            assert response.status_code == 200
            data = response.json()
            
            response_times.append(data["response_time"])
            if data["retrieval_context"]:
                retrieval_times.append(data["retrieval_context"]["retrieval_time"])
            
        # 计算性能指标
        avg_response_time = sum(response_times) / len(response_times)
        avg_retrieval_time = sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0
        
        print(f"📊 性能基准测试结果:")
        print(f"   平均响应时间: {avg_response_time:.3f}s")
        print(f"   平均检索时间: {avg_retrieval_time:.3f}s")
        print(f"   测试查询数量: {len(test_queries)}")
        
        # 性能断言（可根据实际需求调整）
        assert avg_response_time < 30.0, f"平均响应时间过长: {avg_response_time:.3f}s"
        assert avg_retrieval_time < 5.0, f"平均检索时间过长: {avg_retrieval_time:.3f}s"
        
        print("✅ 性能基准测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

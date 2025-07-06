#!/usr/bin/env python3
"""
Prompt优化测试
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


class TestPromptOptimization:
    """Prompt优化测试类"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    def test_prompt_quality_comparison(self, client):
        """测试不同prompt策略的回答质量"""
        
        test_queries = [
            {
                "query": "文档中包含哪些技术内容？",
                "expected_keywords": ["中文文本处理", "英文文本处理", "文件上传", "文本提取", "文档存储", "文档分块"],
                "description": "技术内容查询"
            },
            {
                "query": "这个文档的主要用途是什么？",
                "expected_keywords": ["测试", "验证", "文档上传", "处理功能"],
                "description": "用途查询"
            },
            {
                "query": "文档中提到了哪些测试功能？",
                "expected_keywords": ["文件上传功能", "文本提取功能", "文档存储功能", "文档分块功能"],
                "description": "功能列表查询"
            }
        ]
        
        results = []
        
        for test_case in test_queries:
            print(f"\n🔍 测试查询: {test_case['query']}")
            
            response = client.post(
                "/api/rag/chat",
                json={
                    "message": test_case["query"],
                    "response_mode": "complete",
                    "enable_retrieval": True,
                    "similarity_threshold": 0.3,
                    "max_retrieved_chunks": 3,
                    "temperature": 0.1  # 降低温度以获得更稳定的输出
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 分析回答质量
            answer = data["message"]
            retrieval_info = data["retrieval_context"]
            
            # 检查是否包含预期关键词
            found_keywords = []
            for keyword in test_case["expected_keywords"]:
                if keyword in answer:
                    found_keywords.append(keyword)
            
            # 检查回答是否有重复内容（质量问题指标）
            words = answer.split()
            word_count = len(words)
            unique_words = len(set(words))
            repetition_ratio = 1 - (unique_words / word_count) if word_count > 0 else 0
            
            # 检查回答长度是否合理
            answer_length = len(answer)
            
            result = {
                "query": test_case["query"],
                "description": test_case["description"],
                "answer": answer,
                "answer_length": answer_length,
                "found_keywords": found_keywords,
                "keyword_coverage": len(found_keywords) / len(test_case["expected_keywords"]),
                "repetition_ratio": repetition_ratio,
                "retrieval_chunks": retrieval_info["total_chunks"] if retrieval_info else 0,
                "response_time": data["response_time"],
                "quality_score": self._calculate_quality_score(
                    len(found_keywords) / len(test_case["expected_keywords"]),
                    repetition_ratio,
                    answer_length
                )
            }
            
            results.append(result)
            
            # 打印分析结果
            print(f"📊 回答分析:")
            print(f"   长度: {answer_length} 字符")
            print(f"   关键词覆盖: {len(found_keywords)}/{len(test_case['expected_keywords'])} ({result['keyword_coverage']:.1%})")
            print(f"   重复率: {repetition_ratio:.1%}")
            print(f"   检索块数: {result['retrieval_chunks']}")
            print(f"   质量评分: {result['quality_score']:.2f}/10")
            print(f"   响应时间: {data['response_time']:.3f}s")
            
            if repetition_ratio > 0.5:
                print(f"⚠️  警告: 回答重复率过高 ({repetition_ratio:.1%})")
            
            if len(found_keywords) == 0:
                print(f"⚠️  警告: 未找到预期关键词")
            
            print(f"💬 回答内容: {answer[:200]}{'...' if len(answer) > 200 else ''}")
        
        # 计算总体质量指标
        avg_quality = sum(r["quality_score"] for r in results) / len(results)
        avg_keyword_coverage = sum(r["keyword_coverage"] for r in results) / len(results)
        avg_repetition = sum(r["repetition_ratio"] for r in results) / len(results)
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        
        print(f"\n📈 总体质量评估:")
        print(f"   平均质量评分: {avg_quality:.2f}/10")
        print(f"   平均关键词覆盖率: {avg_keyword_coverage:.1%}")
        print(f"   平均重复率: {avg_repetition:.1%}")
        print(f"   平均响应时间: {avg_response_time:.3f}s")
        
        # 质量断言
        assert avg_quality >= 3.0, f"平均质量评分过低: {avg_quality:.2f}/10"
        assert avg_repetition <= 0.7, f"平均重复率过高: {avg_repetition:.1%}"
        assert avg_keyword_coverage >= 0.2, f"关键词覆盖率过低: {avg_keyword_coverage:.1%}"
        
        return results
    
    def _calculate_quality_score(self, keyword_coverage: float, repetition_ratio: float, answer_length: int) -> float:
        """计算回答质量评分 (0-10分)"""
        
        # 关键词覆盖率评分 (0-4分)
        keyword_score = keyword_coverage * 4
        
        # 重复率评分 (0-3分，重复率越低分数越高)
        repetition_score = max(0, 3 * (1 - repetition_ratio))
        
        # 长度评分 (0-3分)
        if answer_length < 50:
            length_score = 0.5  # 太短
        elif answer_length < 200:
            length_score = 2.0  # 合适
        elif answer_length < 500:
            length_score = 3.0  # 详细
        elif answer_length < 1000:
            length_score = 2.5  # 较长但可接受
        else:
            length_score = 1.0  # 过长
        
        total_score = keyword_score + repetition_score + length_score
        return min(10.0, total_score)
    
    def test_different_temperature_settings(self, client):
        """测试不同温度设置对回答质量的影响"""
        
        query = "文档中包含哪些主要内容？"
        temperatures = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        results = []
        
        for temp in temperatures:
            print(f"\n🌡️ 测试温度: {temp}")
            
            response = client.post(
                "/api/rag/chat",
                json={
                    "message": query,
                    "response_mode": "complete",
                    "enable_retrieval": True,
                    "similarity_threshold": 0.3,
                    "temperature": temp
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            answer = data["message"]
            
            # 分析回答变化
            words = answer.split()
            word_count = len(words)
            unique_words = len(set(words))
            repetition_ratio = 1 - (unique_words / word_count) if word_count > 0 else 0
            
            result = {
                "temperature": temp,
                "answer": answer,
                "answer_length": len(answer),
                "word_count": word_count,
                "unique_words": unique_words,
                "repetition_ratio": repetition_ratio,
                "response_time": data["response_time"]
            }
            
            results.append(result)
            
            print(f"   回答长度: {len(answer)} 字符")
            print(f"   重复率: {repetition_ratio:.1%}")
            print(f"   响应时间: {data['response_time']:.3f}s")
            print(f"   回答预览: {answer[:100]}{'...' if len(answer) > 100 else ''}")
        
        # 找出最佳温度设置
        best_temp = min(results, key=lambda x: x["repetition_ratio"])
        print(f"\n🎯 推荐温度设置: {best_temp['temperature']} (重复率: {best_temp['repetition_ratio']:.1%})")
        
        return results
    
    def test_context_length_impact(self, client):
        """测试上下文长度对回答质量的影响"""
        
        query = "请详细介绍文档的内容和功能"
        context_lengths = [500, 1000, 2000, 4000]
        
        results = []
        
        for max_length in context_lengths:
            print(f"\n📏 测试上下文长度: {max_length}")
            
            response = client.post(
                "/api/rag/chat",
                json={
                    "message": query,
                    "response_mode": "complete",
                    "enable_retrieval": True,
                    "similarity_threshold": 0.3,
                    "max_context_length": max_length,
                    "temperature": 0.1
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            answer = data["message"]
            retrieval_info = data["retrieval_context"]
            
            result = {
                "max_context_length": max_length,
                "actual_context_length": retrieval_info["context_length"] if retrieval_info else 0,
                "answer": answer,
                "answer_length": len(answer),
                "retrieval_chunks": retrieval_info["total_chunks"] if retrieval_info else 0,
                "response_time": data["response_time"]
            }
            
            results.append(result)
            
            print(f"   实际上下文长度: {result['actual_context_length']}")
            print(f"   回答长度: {len(answer)} 字符")
            print(f"   检索块数: {result['retrieval_chunks']}")
            print(f"   响应时间: {data['response_time']:.3f}s")
        
        return results


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

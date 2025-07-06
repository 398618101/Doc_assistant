#!/usr/bin/env python3
"""
查询分析器
智能分析用户查询，提供检索策略建议
"""
import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.core.llm_factory import LLMFactory
from app.models.rag import QueryAnalysis


class QueryAnalyzer:
    """查询分析器"""
    
    def __init__(self):
        self.llm_factory = LLMFactory()
        
        # 查询意图分类
        self.intent_patterns = {
            "question": [r"什么是", r"如何", r"怎么", r"为什么", r"哪里", r"谁", r"何时", r"\?", r"？"],
            "search": [r"查找", r"搜索", r"找到", r"寻找", r"检索"],
            "summary": [r"总结", r"概括", r"摘要", r"归纳", r"梳理"],
            "comparison": [r"比较", r"对比", r"区别", r"差异", r"相同", r"不同"],
            "analysis": [r"分析", r"评估", r"解释", r"说明", r"阐述"],
            "recommendation": [r"建议", r"推荐", r"意见", r"方案", r"策略"]
        }
        
        # 实体类型模式
        self.entity_patterns = {
            "person": [r"[张李王刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤]\w*"],
            "organization": [r"\w*公司", r"\w*企业", r"\w*机构", r"\w*组织", r"\w*部门"],
            "location": [r"\w*市", r"\w*省", r"\w*区", r"\w*县", r"\w*镇", r"\w*村"],
            "time": [r"\d{4}年", r"\d{1,2}月", r"\d{1,2}日", r"今天", r"昨天", r"明天", r"最近"],
            "technology": [r"API", r"数据库", r"算法", r"系统", r"平台", r"框架", r"技术"],
            "document_type": [r"文档", r"报告", r"手册", r"论文", r"简历", r"合同"]
        }
        
        # 查询分析提示词
        self.analysis_prompt = """你是一个专业的查询分析专家。请分析以下用户查询，提供详细的分析结果。

用户查询: {query}

请按以下JSON格式返回分析结果：
{{
    "intent": "查询意图类型",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "entities": ["实体1", "实体2"],
    "query_type": "查询类型",
    "complexity_score": 0.8,
    "requires_context": true,
    "suggested_retrieval_count": 5,
    "suggested_categories": ["分类1", "分类2"],
    "reasoning": "分析理由"
}}

查询意图类型：
- question: 问答类查询
- search: 搜索类查询  
- summary: 摘要类查询
- comparison: 比较类查询
- analysis: 分析类查询
- recommendation: 建议类查询

查询类型：
- factual: 事实性查询
- analytical: 分析性查询
- creative: 创造性查询
- procedural: 程序性查询

复杂度评分：0-1之间，1表示最复杂
建议检索数量：1-10之间的整数
建议分类：可能相关的文档分类"""

    async def analyze_query(self, query: str) -> QueryAnalysis:
        """分析用户查询"""
        try:
            # 1. 基础分析
            basic_analysis = self._basic_analysis(query)
            
            # 2. LLM深度分析
            llm_analysis = await self._llm_analysis(query)
            
            # 3. 融合分析结果
            final_analysis = self._merge_analysis(basic_analysis, llm_analysis)
            
            logger.info(f"查询分析完成: {query[:50]}... -> 意图: {final_analysis.intent}, 复杂度: {final_analysis.complexity_score:.2f}")
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"查询分析失败: {str(e)}")
            # 返回默认分析结果
            return self._default_analysis(query)
    
    def _basic_analysis(self, query: str) -> QueryAnalysis:
        """基础查询分析"""
        analysis = QueryAnalysis(
            original_query=query,
            intent="question",
            keywords=[],
            entities=[],
            query_type="factual",
            complexity_score=0.5,
            requires_context=True,
            suggested_retrieval_count=5
        )
        
        # 意图识别
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    analysis.intent = intent
                    break
            if analysis.intent == intent:
                break
        
        # 实体提取
        entities = []
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, query)
                entities.extend(matches)
        analysis.entities = list(set(entities))
        
        # 关键词提取（简单版本）
        keywords = self._extract_keywords_simple(query)
        analysis.keywords = keywords
        
        # 复杂度评估
        complexity = self._assess_complexity(query)
        analysis.complexity_score = complexity
        
        # 建议检索数量
        if complexity > 0.8:
            analysis.suggested_retrieval_count = 8
        elif complexity > 0.6:
            analysis.suggested_retrieval_count = 6
        elif complexity > 0.4:
            analysis.suggested_retrieval_count = 4
        else:
            analysis.suggested_retrieval_count = 3
        
        return analysis
    
    async def _llm_analysis(self, query: str) -> Optional[Dict[str, Any]]:
        """LLM深度分析"""
        try:
            prompt = self.analysis_prompt.format(query=query)
            
            llm = self.llm_factory.get_llm()
            response = await llm.acomplete(prompt)
            
            # 解析LLM响应
            analysis_data = self._parse_llm_response(response.text)
            return analysis_data
            
        except Exception as e:
            logger.error(f"LLM查询分析失败: {str(e)}")
            return None
    
    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
        
        return None
    
    def _merge_analysis(self, basic: QueryAnalysis, llm_data: Optional[Dict[str, Any]]) -> QueryAnalysis:
        """融合基础分析和LLM分析结果"""
        if not llm_data:
            return basic
        
        # 使用LLM结果更新基础分析
        if "intent" in llm_data:
            basic.intent = llm_data["intent"]
        
        if "keywords" in llm_data and llm_data["keywords"]:
            # 合并关键词，去重
            all_keywords = basic.keywords + llm_data["keywords"]
            basic.keywords = list(set(all_keywords))[:10]  # 限制数量
        
        if "entities" in llm_data and llm_data["entities"]:
            all_entities = basic.entities + llm_data["entities"]
            basic.entities = list(set(all_entities))[:10]
        
        if "query_type" in llm_data:
            basic.query_type = llm_data["query_type"]
        
        if "complexity_score" in llm_data:
            # 取平均值
            basic.complexity_score = (basic.complexity_score + float(llm_data["complexity_score"])) / 2
        
        if "requires_context" in llm_data:
            basic.requires_context = llm_data["requires_context"]
        
        if "suggested_retrieval_count" in llm_data:
            # 取较大值
            basic.suggested_retrieval_count = max(
                basic.suggested_retrieval_count, 
                int(llm_data["suggested_retrieval_count"])
            )
        
        return basic
    
    def _default_analysis(self, query: str) -> QueryAnalysis:
        """默认分析结果"""
        return QueryAnalysis(
            original_query=query,
            intent="question",
            keywords=self._extract_keywords_simple(query),
            entities=[],
            query_type="factual",
            complexity_score=0.5,
            requires_context=True,
            suggested_retrieval_count=5
        )
    
    def _extract_keywords_simple(self, query: str) -> List[str]:
        """简单关键词提取"""
        # 移除停用词和标点符号
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
        
        # 简单分词（基于空格和标点）
        words = re.findall(r'[\w]+', query)
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        return keywords[:10]  # 限制数量
    
    def _assess_complexity(self, query: str) -> float:
        """评估查询复杂度"""
        complexity = 0.0
        
        # 长度因子
        length_factor = min(len(query) / 100, 0.3)
        complexity += length_factor
        
        # 问号数量
        question_marks = query.count('?') + query.count('？')
        complexity += min(question_marks * 0.1, 0.2)
        
        # 复杂词汇
        complex_words = ["分析", "比较", "评估", "解释", "总结", "归纳", "对比", "区别"]
        for word in complex_words:
            if word in query:
                complexity += 0.1
        
        # 逻辑连接词
        logical_words = ["并且", "或者", "但是", "然而", "因此", "所以", "如果", "那么"]
        for word in logical_words:
            if word in query:
                complexity += 0.15
        
        return min(complexity, 1.0)
    
    def get_query_hash(self, query: str) -> str:
        """获取查询哈希值"""
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def suggest_categories(self, query: str, keywords: List[str]) -> List[str]:
        """建议相关文档分类"""
        suggested = []
        
        # 基于关键词匹配分类
        category_keywords = {
            "tech-docs": ["技术", "API", "开发", "编程", "系统", "架构"],
            "research": ["研究", "报告", "分析", "数据", "调研"],
            "manual": ["手册", "指南", "操作", "使用", "说明"],
            "academic": ["论文", "学术", "期刊", "研究", "实验"],
            "business": ["商业", "财务", "营销", "计划", "合同"],
            "legal": ["法律", "法规", "合同", "协议", "条款"]
        }
        
        query_lower = query.lower()
        keywords_lower = [k.lower() for k in keywords]
        
        for category, cat_keywords in category_keywords.items():
            score = 0
            for keyword in cat_keywords:
                if keyword in query_lower:
                    score += 2
                for user_keyword in keywords_lower:
                    if keyword in user_keyword or user_keyword in keyword:
                        score += 1
            
            if score > 0:
                suggested.append((category, score))
        
        # 按分数排序，返回前3个
        suggested.sort(key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in suggested[:3]]


# 全局查询分析器实例
query_analyzer = QueryAnalyzer()

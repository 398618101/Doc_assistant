#!/usr/bin/env python3
"""
文档自动分类服务
使用LLM进行智能文档分类和标签生成
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.core.llm_factory import get_llm_factory
from app.models.document import Document, DocumentMetadata


class ClassificationResult:
    """分类结果"""
    def __init__(self):
        self.category: str = "other"
        self.subcategory: Optional[str] = None
        self.confidence: float = 0.0
        self.auto_tags: List[str] = []
        self.keywords: List[str] = []
        self.summary: str = ""
        self.language: str = "zh"
        self.reasoning: str = ""


class DocumentClassifier:
    """文档自动分类器"""

    def __init__(self):
        self.llm_factory = get_llm_factory()
        
        # 预定义分类
        self.predefined_categories = {
            "tech-docs": {
                "name": "技术文档",
                "keywords": ["API", "技术", "开发", "编程", "代码", "架构", "系统", "接口", "文档"],
                "patterns": [r"API\s*文档", r"技术\s*规范", r"开发\s*指南", r"系统\s*设计"]
            },
            "research": {
                "name": "研究报告", 
                "keywords": ["研究", "报告", "分析", "调研", "数据", "统计", "结论", "建议"],
                "patterns": [r"研究\s*报告", r"调研\s*分析", r"市场\s*分析", r"数据\s*报告"]
            },
            "manual": {
                "name": "操作手册",
                "keywords": ["手册", "指南", "操作", "使用", "说明", "流程", "步骤", "教程"],
                "patterns": [r"操作\s*手册", r"使用\s*指南", r"用户\s*手册", r"操作\s*流程"]
            },
            "resume": {
                "name": "个人简历",
                "keywords": ["简历", "履历", "工作经历", "教育背景", "技能", "项目经验"],
                "patterns": [r"个人\s*简历", r"求职\s*简历", r"工作\s*履历", r"个人\s*信息"]
            },
            "academic": {
                "name": "学术论文",
                "keywords": ["论文", "期刊", "学术", "研究", "摘要", "关键词", "参考文献", "实验"],
                "patterns": [r"学术\s*论文", r"期刊\s*文章", r"会议\s*论文", r"研究\s*论文"]
            },
            "business": {
                "name": "商业文档",
                "keywords": ["商业", "计划", "合同", "财务", "预算", "营销", "销售", "商务"],
                "patterns": [r"商业\s*计划", r"财务\s*报告", r"营销\s*方案", r"合同\s*文件"]
            },
            "legal": {
                "name": "法律文件",
                "keywords": ["法律", "法规", "条例", "合同", "协议", "条款", "法条", "规定"],
                "patterns": [r"法律\s*文件", r"合同\s*协议", r"法规\s*条例", r"法律\s*条款"]
            }
        }
        
        # 分类提示词模板
        self.classification_prompt = """你是一个专业的文档分类专家。请根据以下文档内容进行智能分类。

## 可选分类类别：
1. tech-docs (技术文档) - API文档、技术规范、开发指南等
2. research (研究报告) - 研究报告、调研分析、数据分析等  
3. manual (操作手册) - 用户手册、操作指南、使用说明等
4. resume (个人简历) - 个人简历、求职材料、履历等
5. academic (学术论文) - 学术论文、期刊文章、会议论文等
6. business (商业文档) - 商业计划、财务报告、合同等
7. legal (法律文件) - 法律条文、合同协议、法规等
8. other (其他) - 不属于以上类别的文档

## 文档信息：
文件名: {filename}
文件类型: {file_type}
文档内容预览: {content_preview}

## 请按以下JSON格式返回分类结果：
{{
    "category": "分类ID",
    "confidence": 0.95,
    "reasoning": "分类理由",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "tags": ["标签1", "标签2", "标签3"],
    "summary": "文档摘要（50字以内）",
    "language": "zh"
}}

要求：
1. confidence为0-1之间的浮点数，表示分类置信度
2. reasoning简要说明分类依据
3. keywords提取3-5个关键词
4. tags生成2-4个描述性标签
5. summary生成简洁的文档摘要
6. 如果无法确定分类，使用"other"并说明原因"""

    async def classify_document(self, document: Document) -> ClassificationResult:
        """对文档进行自动分类"""
        result = ClassificationResult()
        
        try:
            # 1. 基于规则的预分类
            rule_result = self._classify_by_rules(document)
            
            # 2. 基于LLM的智能分类
            llm_result = await self._classify_by_llm(document)
            
            # 3. 融合分类结果
            result = self._merge_classification_results(rule_result, llm_result)
            
            logger.info(f"文档分类完成: {document.filename} -> {result.category} (置信度: {result.confidence:.2f})")
            
        except Exception as e:
            logger.error(f"文档分类失败: {str(e)}")
            # 返回默认分类
            result.category = "other"
            result.confidence = 0.0
            result.reasoning = f"分类失败: {str(e)}"
        
        return result
    
    def _classify_by_rules(self, document: Document) -> ClassificationResult:
        """基于规则的分类"""
        result = ClassificationResult()
        
        # 获取文档内容和文件名
        content = (document.content or "").lower()
        filename = document.original_filename.lower()
        
        max_score = 0
        best_category = "other"
        
        # 遍历所有预定义分类
        for category_id, category_info in self.predefined_categories.items():
            score = 0
            
            # 关键词匹配
            for keyword in category_info["keywords"]:
                if keyword.lower() in content or keyword.lower() in filename:
                    score += 1
            
            # 模式匹配
            for pattern in category_info["patterns"]:
                if re.search(pattern, content, re.IGNORECASE) or re.search(pattern, filename, re.IGNORECASE):
                    score += 2
            
            if score > max_score:
                max_score = score
                best_category = category_id
        
        result.category = best_category
        result.confidence = min(max_score / 10.0, 1.0)  # 规则分类置信度相对较低
        result.reasoning = f"基于规则匹配，得分: {max_score}"
        
        return result
    
    async def _classify_by_llm(self, document: Document) -> ClassificationResult:
        """基于LLM的智能分类"""
        result = ClassificationResult()
        
        try:
            # 准备内容预览（限制长度以节省token）
            content_preview = document.content[:2000] if document.content else ""
            if len(document.content or "") > 2000:
                content_preview += "..."
            
            # 构建提示词
            prompt = self.classification_prompt.format(
                filename=document.original_filename,
                file_type=document.document_type,
                content_preview=content_preview
            )
            
            # 调用LLM
            llm_manager = await self.llm_factory.get_client()
            response = await llm_manager.generate(prompt, max_tokens=500, temperature=0.1)
            
            # 解析LLM响应
            response_text = response.get('text', '') if isinstance(response, dict) else str(response)
            classification_data = self._parse_llm_response(response_text)
            
            if classification_data:
                result.category = classification_data.get("category", "other")
                result.confidence = float(classification_data.get("confidence", 0.0))
                result.reasoning = classification_data.get("reasoning", "")
                result.keywords = classification_data.get("keywords", [])
                result.auto_tags = classification_data.get("tags", [])
                result.summary = classification_data.get("summary", "")
                result.language = classification_data.get("language", "zh")
            
        except Exception as e:
            logger.error(f"LLM分类失败: {str(e)}")
            result.confidence = 0.0
            result.reasoning = f"LLM分类失败: {str(e)}"
        
        return result
    
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
    
    def _merge_classification_results(self, rule_result: ClassificationResult, llm_result: ClassificationResult) -> ClassificationResult:
        """融合规则分类和LLM分类结果"""
        result = ClassificationResult()
        
        # 选择置信度更高的分类结果
        if llm_result.confidence > rule_result.confidence:
            result = llm_result
            # 如果LLM分类置信度不高，但规则分类有结果，进行融合
            if llm_result.confidence < 0.7 and rule_result.confidence > 0.3:
                result.reasoning += f" (规则分类建议: {rule_result.category})"
        else:
            result = rule_result
            # 补充LLM的详细信息
            if llm_result.keywords:
                result.keywords = llm_result.keywords
            if llm_result.auto_tags:
                result.auto_tags = llm_result.auto_tags
            if llm_result.summary:
                result.summary = llm_result.summary
        
        # 确保分类有效
        if result.category not in self.predefined_categories:
            result.category = "other"
        
        return result
    
    def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """提取关键词"""
        if not content:
            return []
        
        # 简单的关键词提取（可以后续优化为更复杂的算法）
        import jieba
        import jieba.analyse
        
        try:
            # 使用jieba提取关键词
            keywords = jieba.analyse.extract_tags(content, topK=max_keywords, withWeight=False)
            return keywords
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            return []
    
    def generate_summary(self, content: str, max_length: int = 100) -> str:
        """生成文档摘要"""
        if not content:
            return ""
        
        # 简单的摘要生成（取前几句话）
        sentences = re.split(r'[。！？\n]', content)
        summary = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(summary + sentence) <= max_length:
                summary += sentence + "。"
            else:
                break
        
        return summary.strip()


# 全局分类器实例
document_classifier = DocumentClassifier()

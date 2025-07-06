#!/usr/bin/env python3
"""
Prompt构建服务 - 从RAG服务中提取的prompt相关功能
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.models.rag import (
    ChatMessage, ChatRole, RetrievalContext, ContextWindow, 
    QueryAnalysis, ContextStrategy
)


class PromptBuilder:
    """Prompt构建器"""
    
    def __init__(self):
        self.system_prompts = {
            'default': """你是一个智能文档助理，专门帮助用户理解和分析文档内容。

核心能力：
1. 基于提供的文档内容回答问题
2. 提供准确、有用的信息
3. 引用具体的文档来源
4. 承认知识局限性

回答原则：
- 优先使用检索到的文档内容
- 保持客观和准确
- 提供具体的引用信息
- 如果文档中没有相关信息，明确说明""",
            
            'analysis': """你是一个专业的文档分析师，擅长深度分析和总结文档内容。

分析重点：
1. 提取关键信息和要点
2. 分析文档结构和逻辑
3. 识别重要概念和关系
4. 提供深入的见解

请基于提供的文档内容进行专业分析。""",
            
            'summary': """你是一个文档摘要专家，能够快速提取文档的核心内容。

摘要要求：
1. 突出主要观点和结论
2. 保持信息的完整性
3. 使用清晰简洁的语言
4. 按重要性排序信息

请为提供的文档内容生成高质量摘要。"""
        }
    
    def build_system_prompt(self, prompt_type: str = 'default') -> str:
        """构建系统提示词"""
        return self.system_prompts.get(prompt_type, self.system_prompts['default'])
    
    def build_context_prompt(
        self, 
        retrieval_context: RetrievalContext,
        strategy: ContextStrategy = ContextStrategy.RANKED
    ) -> str:
        """构建上下文提示词"""
        if not retrieval_context.retrieved_chunks:
            return "没有找到相关的文档内容。"

        context_parts = []

        # 根据策略排序文档块
        sorted_chunks = self._sort_chunks_by_strategy(retrieval_context.retrieved_chunks, strategy)
        
        for i, chunk in enumerate(sorted_chunks, 1):
            # 构建单个文档块的上下文
            chunk_context = f"""
文档 {i}:
来源: {chunk.get('document_metadata', {}).get('filename', '未知文件')}
相关度: {chunk.get('similarity_score', chunk.get('final_score', 0)):.3f}
内容: {chunk.get('text', chunk.get('content', ''))}
"""
            context_parts.append(chunk_context.strip())
        
        return "\n\n".join(context_parts)
    
    def build_conversation_context(
        self, 
        messages: List[ChatMessage], 
        max_messages: int = 10
    ) -> str:
        """构建对话上下文"""
        if not messages:
            return ""
        
        # 获取最近的消息
        recent_messages = messages[-max_messages:]
        
        context_parts = []
        for msg in recent_messages:
            role_name = "用户" if msg.role == ChatRole.USER else "助手"
            context_parts.append(f"{role_name}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def build_complete_prompt(
        self,
        user_query: str,
        retrieval_context: Optional[RetrievalContext] = None,
        conversation_history: Optional[List[ChatMessage]] = None,
        prompt_type: str = 'default',
        strategy: ContextStrategy = ContextStrategy.RANKED
    ) -> str:
        """构建完整的提示词"""
        prompt_parts = []
        
        # 1. 系统提示词
        system_prompt = self.build_system_prompt(prompt_type)
        prompt_parts.append(f"系统指令:\n{system_prompt}")
        
        # 2. 文档上下文
        if retrieval_context and retrieval_context.retrieved_chunks:
            context_prompt = self.build_context_prompt(retrieval_context, strategy)
            prompt_parts.append(f"相关文档内容:\n{context_prompt}")
        
        # 3. 对话历史
        if conversation_history:
            history_context = self.build_conversation_context(conversation_history)
            if history_context:
                prompt_parts.append(f"对话历史:\n{history_context}")
        
        # 4. 用户问题
        prompt_parts.append(f"用户问题: {user_query}")
        
        # 5. 回答指导
        prompt_parts.append("""
请基于以上信息回答用户问题。要求：
1. 优先使用提供的文档内容
2. 如果文档中没有相关信息，请明确说明
3. 提供具体的引用来源
4. 保持回答的准确性和有用性
""")
        
        return "\n\n".join(prompt_parts)
    
    def _sort_chunks_by_strategy(
        self, 
        chunks: List[Dict[str, Any]], 
        strategy: ContextStrategy
    ) -> List[Dict[str, Any]]:
        """根据策略排序文档块"""
        if strategy == ContextStrategy.RANKED:
            # 按相关度排序
            return sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)
        elif strategy == ContextStrategy.HIERARCHICAL:
            # 按层次结构排序
            return sorted(chunks, key=lambda x: x.get('timestamp', ''), reverse=True)
        elif strategy == ContextStrategy.SUMMARIZED:
            # 按摘要重要性排序
            return sorted(chunks, key=lambda x: (x.get('source', ''), -x.get('score', 0)))
        else:
            return chunks
    
    def optimize_prompt_length(
        self, 
        prompt: str, 
        max_tokens: int = 4000
    ) -> str:
        """优化提示词长度"""
        # 简单的长度控制，实际应该使用tokenizer
        estimated_tokens = len(prompt.split()) * 1.3  # 粗略估算
        
        if estimated_tokens <= max_tokens:
            return prompt
        
        # 如果太长，尝试缩短
        lines = prompt.split('\n')
        target_lines = int(len(lines) * (max_tokens / estimated_tokens))
        
        # 保留重要部分
        important_sections = []
        current_section = []
        
        for line in lines:
            if line.startswith(('系统指令:', '用户问题:', '请基于')):
                if current_section:
                    important_sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            important_sections.append('\n'.join(current_section))
        
        # 如果还是太长，进一步缩短文档内容部分
        if len('\n\n'.join(important_sections).split()) * 1.3 > max_tokens:
            for i, section in enumerate(important_sections):
                if '相关文档内容:' in section:
                    # 缩短文档内容
                    lines = section.split('\n')
                    important_sections[i] = '\n'.join(lines[:target_lines//2])
                    break
        
        return '\n\n'.join(important_sections)
    
    def extract_citations(self, response: str) -> List[str]:
        """从回答中提取引用信息"""
        # 查找引用模式，如 [文档1]、(来源: xxx) 等
        citation_patterns = [
            r'\[文档\s*(\d+)\]',
            r'\(来源:\s*([^)]+)\)',
            r'引用:\s*([^\n]+)',
            r'参考:\s*([^\n]+)'
        ]
        
        citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            citations.extend(matches)
        
        return list(set(citations))  # 去重

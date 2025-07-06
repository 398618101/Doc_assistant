"""
文档分块服务 - 智能文本分割
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger


class ChunkingService:
    """文档分块服务"""
    
    def __init__(self):
        """初始化分块服务"""
        self.default_chunk_size = 1000
        self.default_overlap = 200
        self.min_chunk_size = 100
        self.max_chunk_size = 4000
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = None, 
        overlap: int = None,
        document_id: str = "",
        document_type: str = ""
    ) -> List[Dict[str, Any]]:
        """
        将文本分割成块
        
        Args:
            text: 要分块的文本
            chunk_size: 块大小（字符数）
            overlap: 重叠大小（字符数）
            document_id: 文档ID
            document_type: 文档类型
            
        Returns:
            分块结果列表，每个元素包含文本和元数据
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，跳过分块")
            return []
        
        # 使用默认值
        chunk_size = chunk_size or self.default_chunk_size
        overlap = overlap or self.default_overlap
        
        # 验证参数
        chunk_size = max(self.min_chunk_size, min(chunk_size, self.max_chunk_size))
        overlap = max(0, min(overlap, chunk_size // 2))
        
        logger.info(f"开始文档分块: 文本长度={len(text)}, 块大小={chunk_size}, 重叠={overlap}")
        
        # 预处理文本
        text = self._preprocess_text(text)
        
        # 根据文档类型选择分块策略
        if document_type.lower() == "md":
            chunks = self._chunk_markdown(text, chunk_size, overlap)
        else:
            chunks = self._chunk_by_sentences(text, chunk_size, overlap)
        
        # 生成元数据
        chunk_data = []
        for i, chunk_text in enumerate(chunks):
            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunk_data.append({
                    "text": chunk_text.strip(),
                    "metadata": {
                        "document_id": document_id,
                        "chunk_index": i,
                        "chunk_size": len(chunk_text),
                        "document_type": document_type,
                        "total_chunks": len(chunks)
                    }
                })
        
        logger.info(f"文档分块完成: 生成 {len(chunk_data)} 个有效块")
        return chunk_data
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除多余的空白字符，但保留段落结构
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # 多个空行合并为两个
        text = re.sub(r'[ \t]+', ' ', text)  # 多个空格/制表符合并为一个空格
        
        return text.strip()
    
    def _chunk_by_sentences(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """基于句子的智能分块"""
        # 按句子分割
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return [text]
        
        chunks = []
        current_chunk = ""
        current_size = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sentence_size = len(sentence)
            
            # 如果当前句子本身就超过块大小，直接作为一个块
            if sentence_size > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                    current_size = 0
                chunks.append(sentence)
                i += 1
                continue
            
            # 如果添加当前句子会超过块大小
            if current_size + sentence_size > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    
                    # 处理重叠
                    if overlap > 0:
                        overlap_text = self._get_overlap_text(current_chunk, overlap)
                        current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                        current_size = len(current_chunk)
                    else:
                        current_chunk = sentence
                        current_size = sentence_size
                else:
                    current_chunk = sentence
                    current_size = sentence_size
            else:
                # 添加句子到当前块
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_size += sentence_size + (1 if current_chunk != sentence else 0)
            
            i += 1
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_markdown(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Markdown文档的智能分块"""
        # 按标题层级分割
        sections = self._split_markdown_sections(text)
        
        chunks = []
        for section in sections:
            if len(section) <= chunk_size:
                chunks.append(section)
            else:
                # 大段落继续按句子分块
                sub_chunks = self._chunk_by_sentences(section, chunk_size, overlap)
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 中英文句子分割正则表达式
        sentence_pattern = r'[.!?。！？]+[\s]*|[\n]+'
        sentences = re.split(sentence_pattern, text)
        
        # 清理空句子
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _split_markdown_sections(self, text: str) -> List[str]:
        """按Markdown标题分割文档"""
        # 按标题分割（# ## ### 等）
        sections = re.split(r'\n(?=#{1,6}\s)', text)
        
        # 清理空段落
        sections = [s.strip() for s in sections if s.strip()]
        
        return sections
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """获取文本末尾的重叠部分"""
        if len(text) <= overlap_size:
            return text
        
        # 尝试在单词边界处截断
        overlap_text = text[-overlap_size:]
        
        # 找到第一个空格，避免截断单词
        first_space = overlap_text.find(' ')
        if first_space > 0:
            overlap_text = overlap_text[first_space + 1:]
        
        return overlap_text
    
    def get_chunk_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取分块统计信息"""
        if not chunks:
            return {
                "total_chunks": 0,
                "total_characters": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0
            }
        
        chunk_sizes = [len(chunk["text"]) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_characters": sum(chunk_sizes),
            "avg_chunk_size": sum(chunk_sizes) // len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes)
        }


# 全局实例
chunking_service = ChunkingService()

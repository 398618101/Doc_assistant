#!/usr/bin/env python3
"""
增强的向量存储服务
支持多层索引、文档关联分析和智能检索
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

import chromadb
from chromadb.config import Settings

from app.core.config import get_settings
from app.services.vector_storage import VectorStorage
from app.models.document import Document


class DocumentRelation:
    """文档关联关系"""
    def __init__(self):
        self.source_document_id: str = ""
        self.target_document_id: str = ""
        self.relation_type: str = ""  # similar/reference/topic/temporal
        self.confidence: float = 0.0
        self.metadata: Dict[str, Any] = {}


class EnhancedVectorStorage(VectorStorage):
    """增强的向量存储服务"""
    
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.db_path = Path(self.settings.UPLOAD_DIR).parent / "documents.db"
        
        # 关键词索引（内存中的倒排索引）
        self.keyword_index: Dict[str, List[str]] = {}
        
        # 分类索引
        self.category_index: Dict[str, List[str]] = {}
        
        # 文档关联图
        self.relation_graph: Dict[str, List[DocumentRelation]] = {}
        
        # 初始化索引
        self._load_indexes()
    
    def _load_indexes(self):
        """加载索引数据"""
        try:
            self._load_keyword_index()
            self._load_category_index()
            self._load_relation_graph()
            logger.info("增强索引加载完成")
        except Exception as e:
            logger.error(f"索引加载失败: {str(e)}")
    
    def _load_keyword_index(self):
        """加载关键词索引"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, keywords FROM documents 
                    WHERE keywords IS NOT NULL AND keywords != ''
                """)
                
                for doc_id, keywords_json in cursor.fetchall():
                    try:
                        keywords = json.loads(keywords_json)
                        for keyword in keywords:
                            if keyword not in self.keyword_index:
                                self.keyword_index[keyword] = []
                            self.keyword_index[keyword].append(doc_id)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"关键词索引加载失败: {str(e)}")
    
    def _load_category_index(self):
        """加载分类索引"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, category FROM documents 
                    WHERE category IS NOT NULL AND category != ''
                """)
                
                for doc_id, category in cursor.fetchall():
                    if category not in self.category_index:
                        self.category_index[category] = []
                    self.category_index[category].append(doc_id)
                    
        except Exception as e:
            logger.error(f"分类索引加载失败: {str(e)}")
    
    def _load_relation_graph(self):
        """加载文档关联图"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT source_document_id, target_document_id, relation_type, 
                           confidence, metadata FROM document_relations
                """)
                
                for row in cursor.fetchall():
                    source_id, target_id, rel_type, confidence, metadata_json = row
                    
                    relation = DocumentRelation()
                    relation.source_document_id = source_id
                    relation.target_document_id = target_id
                    relation.relation_type = rel_type
                    relation.confidence = confidence
                    
                    try:
                        relation.metadata = json.loads(metadata_json) if metadata_json else {}
                    except json.JSONDecodeError:
                        relation.metadata = {}
                    
                    if source_id not in self.relation_graph:
                        self.relation_graph[source_id] = []
                    self.relation_graph[source_id].append(relation)
                    
        except Exception as e:
            logger.error(f"关联图加载失败: {str(e)}")
    
    async def build_comprehensive_index(self, document: Document):
        """为文档构建综合索引"""
        try:
            # 1. 构建语义向量索引（继承自父类）
            if document.content and document.is_vectorized:
                logger.info(f"文档 {document.id} 已有向量索引")
            
            # 2. 构建关键词索引
            await self._build_keyword_index(document)
            
            # 3. 构建分类索引
            await self._build_category_index(document)
            
            # 4. 分析文档关联
            await self._analyze_document_relations(document)
            
            logger.info(f"文档 {document.id} 综合索引构建完成")
            
        except Exception as e:
            logger.error(f"综合索引构建失败: {str(e)}")
    
    async def _build_keyword_index(self, document: Document):
        """构建关键词索引"""
        try:
            # 从数据库获取关键词
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT keywords FROM documents WHERE id = ?
                """, (document.id,))
                
                row = cursor.fetchone()
                if row and row[0]:
                    keywords = json.loads(row[0])
                    
                    # 更新内存索引
                    for keyword in keywords:
                        if keyword not in self.keyword_index:
                            self.keyword_index[keyword] = []
                        if document.id not in self.keyword_index[keyword]:
                            self.keyword_index[keyword].append(document.id)
                            
        except Exception as e:
            logger.error(f"关键词索引构建失败: {str(e)}")
    
    async def _build_category_index(self, document: Document):
        """构建分类索引"""
        try:
            if document.category:
                if document.category not in self.category_index:
                    self.category_index[document.category] = []
                if document.id not in self.category_index[document.category]:
                    self.category_index[document.category].append(document.id)
                    
        except Exception as e:
            logger.error(f"分类索引构建失败: {str(e)}")
    
    async def _analyze_document_relations(self, document: Document):
        """分析文档关联关系"""
        try:
            # 1. 基于相似度的关联
            await self._find_similar_documents(document)
            
            # 2. 基于主题的关联
            await self._find_topic_related_documents(document)
            
            # 3. 基于时间的关联
            await self._find_temporal_related_documents(document)
            
        except Exception as e:
            logger.error(f"文档关联分析失败: {str(e)}")
    
    async def _find_similar_documents(self, document: Document, threshold: float = 0.8):
        """查找相似文档"""
        try:
            if not document.is_vectorized:
                return
            
            # 使用向量相似度查找相似文档
            similar_results = self.search_similar_chunks(
                query_text=document.content[:1000] if document.content else "",
                max_results=10,
                similarity_threshold=threshold,
                document_ids=[document.id]  # 排除自身
            )
            
            # 保存相似关系
            for result in similar_results:
                if result.get('document_id') != document.id:
                    await self._save_document_relation(
                        source_id=document.id,
                        target_id=result.get('document_id'),
                        relation_type="similar",
                        confidence=result.get('similarity_score', 0.0),
                        metadata={"method": "vector_similarity"}
                    )
                    
        except Exception as e:
            logger.error(f"相似文档查找失败: {str(e)}")
    
    async def _find_topic_related_documents(self, document: Document):
        """查找主题相关文档"""
        try:
            if not document.category:
                return
            
            # 查找同类别文档
            category_docs = self.category_index.get(document.category, [])
            
            for doc_id in category_docs:
                if doc_id != document.id:
                    await self._save_document_relation(
                        source_id=document.id,
                        target_id=doc_id,
                        relation_type="topic",
                        confidence=0.6,
                        metadata={"category": document.category}
                    )
                    
        except Exception as e:
            logger.error(f"主题相关文档查找失败: {str(e)}")
    
    async def _find_temporal_related_documents(self, document: Document):
        """查找时间相关文档"""
        try:
            # 查找同一时间段的文档
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id FROM documents 
                    WHERE id != ? 
                    AND ABS(julianday(created_at) - julianday(?)) <= 7
                    ORDER BY ABS(julianday(created_at) - julianday(?))
                    LIMIT 5
                """, (document.id, document.created_at.isoformat(), document.created_at.isoformat()))
                
                for (doc_id,) in cursor.fetchall():
                    await self._save_document_relation(
                        source_id=document.id,
                        target_id=doc_id,
                        relation_type="temporal",
                        confidence=0.4,
                        metadata={"time_window": "7_days"}
                    )
                    
        except Exception as e:
            logger.error(f"时间相关文档查找失败: {str(e)}")
    
    async def _save_document_relation(self, source_id: str, target_id: str, 
                                    relation_type: str, confidence: float, 
                                    metadata: Dict[str, Any]):
        """保存文档关联关系"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO document_relations 
                    (id, source_document_id, target_document_id, relation_type, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{source_id}_{target_id}_{relation_type}",
                    source_id, target_id, relation_type, confidence,
                    json.dumps(metadata)
                ))
                conn.commit()
                
            # 更新内存关联图
            if source_id not in self.relation_graph:
                self.relation_graph[source_id] = []
            
            # 检查是否已存在相同关联
            existing = False
            for relation in self.relation_graph[source_id]:
                if (relation.target_document_id == target_id and 
                    relation.relation_type == relation_type):
                    relation.confidence = confidence
                    relation.metadata = metadata
                    existing = True
                    break
            
            if not existing:
                relation = DocumentRelation()
                relation.source_document_id = source_id
                relation.target_document_id = target_id
                relation.relation_type = relation_type
                relation.confidence = confidence
                relation.metadata = metadata
                self.relation_graph[source_id].append(relation)
                
        except Exception as e:
            logger.error(f"保存文档关联失败: {str(e)}")
    
    def search_by_keywords(self, keywords: List[str], max_results: int = 10) -> List[str]:
        """基于关键词搜索文档"""
        document_scores = {}
        
        for keyword in keywords:
            if keyword in self.keyword_index:
                for doc_id in self.keyword_index[keyword]:
                    if doc_id not in document_scores:
                        document_scores[doc_id] = 0
                    document_scores[doc_id] += 1
        
        # 按分数排序
        sorted_docs = sorted(document_scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in sorted_docs[:max_results]]
    
    def search_by_category(self, categories: List[str]) -> List[str]:
        """基于分类搜索文档"""
        document_ids = []
        
        for category in categories:
            if category in self.category_index:
                document_ids.extend(self.category_index[category])
        
        return list(set(document_ids))
    
    def get_related_documents(self, document_id: str, 
                            relation_types: Optional[List[str]] = None,
                            min_confidence: float = 0.0) -> List[DocumentRelation]:
        """获取相关文档"""
        if document_id not in self.relation_graph:
            return []
        
        relations = self.relation_graph[document_id]
        
        # 过滤条件
        filtered_relations = []
        for relation in relations:
            if relation.confidence >= min_confidence:
                if not relation_types or relation.relation_type in relation_types:
                    filtered_relations.append(relation)
        
        # 按置信度排序
        filtered_relations.sort(key=lambda x: x.confidence, reverse=True)
        return filtered_relations
    
    def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return {
            "keyword_index_size": len(self.keyword_index),
            "category_index_size": len(self.category_index),
            "relation_graph_size": len(self.relation_graph),
            "total_relations": sum(len(relations) for relations in self.relation_graph.values()),
            "categories": list(self.category_index.keys()),
            "top_keywords": sorted(self.keyword_index.keys(), 
                                 key=lambda k: len(self.keyword_index[k]), 
                                 reverse=True)[:10]
        }


# 全局增强向量存储实例
enhanced_vector_storage = EnhancedVectorStorage()

"""
向量存储服务 - ChromaDB集成
"""
import os
import uuid
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
from loguru import logger

from app.core.config import get_settings
from app.models.document import Document, DocumentChunk


class VectorStorage:
    """ChromaDB向量存储服务"""
    
    def __init__(self):
        """初始化ChromaDB客户端"""
        self.settings = get_settings()
        self.client = None
        self.collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化ChromaDB客户端和集合"""
        try:
            # 创建向量数据库目录
            vector_db_path = Path("../vector_db")
            vector_db_path.mkdir(exist_ok=True)
            
            # 初始化ChromaDB客户端（本地持久化存储）
            self.client = chromadb.PersistentClient(
                path=str(vector_db_path),
                settings=Settings(
                    anonymized_telemetry=False,  # 禁用遥测
                    allow_reset=True
                )
            )
            
            # 创建或获取文档集合
            collection_name = "documents"
            try:
                self.collection = self.client.get_collection(name=collection_name)
                logger.info(f"已连接到现有向量集合: {collection_name}")
            except Exception:
                # 集合不存在，创建新集合
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={
                        "description": "智能文档助理系统文档向量集合",
                        "created_by": "intelligent-doc-assistant",
                        "hnsw:space": "cosine"  # 使用余弦相似度
                    }
                )
                logger.info(f"已创建新向量集合: {collection_name}")
            
            logger.info("ChromaDB向量存储初始化成功")
            
        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {str(e)}")
            raise Exception(f"向量数据库初始化失败: {str(e)}")
    
    def add_document_chunks(
        self, 
        document_id: str, 
        chunks: List[str], 
        embeddings: List[List[float]], 
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """添加文档分块到向量数据库"""
        try:
            if not chunks or not embeddings or len(chunks) != len(embeddings):
                raise ValueError("文档分块、嵌入向量和元数据数量不匹配")
            
            # 生成唯一ID
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
            
            # 添加到ChromaDB
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadata
            )
            
            logger.info(f"已添加 {len(chunks)} 个文档分块到向量数据库，文档ID: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加文档分块失败: {str(e)}")
            return False
    
    def search_similar_chunks(
        self, 
        query_embedding: List[float], 
        n_results: int = 5,
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """搜索相似的文档分块"""
        try:
            # 构建查询条件
            where_condition = None
            if document_ids:
                where_condition = {"document_id": {"$in": document_ids}}
            
            # 执行相似性搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_condition,
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化结果
            formatted_results = {
                "chunks": results["documents"][0] if results["documents"] else [],
                "metadata": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "total_results": len(results["documents"][0]) if results["documents"] else 0
            }
            
            logger.info(f"向量搜索完成，返回 {formatted_results['total_results']} 个结果")
            return formatted_results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            return {"chunks": [], "metadata": [], "distances": [], "total_results": 0}
    
    def delete_document_chunks(self, document_id: str) -> bool:
        """删除指定文档的所有分块"""
        try:
            # 查询该文档的所有分块ID
            results = self.collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            
            if results["ids"]:
                # 删除分块
                self.collection.delete(ids=results["ids"])
                logger.info(f"已删除文档 {document_id} 的 {len(results['ids'])} 个分块")
                return True
            else:
                logger.info(f"文档 {document_id} 没有找到向量分块")
                return True
                
        except Exception as e:
            logger.error(f"删除文档分块失败: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取向量集合统计信息"""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": self.collection.name,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {str(e)}")
            return {
                "total_chunks": 0,
                "collection_name": "unknown",
                "status": "error",
                "error": str(e)
            }
    
    def reset_collection(self) -> bool:
        """重置向量集合（谨慎使用）"""
        try:
            self.client.delete_collection(name=self.collection.name)
            self.collection = self.client.create_collection(
                name="documents",
                metadata={
                    "description": "智能文档助理系统文档向量集合",
                    "created_by": "intelligent-doc-assistant",
                    "hnsw:space": "cosine"
                }
            )
            logger.warning("向量集合已重置")
            return True
        except Exception as e:
            logger.error(f"重置向量集合失败: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 尝试获取集合信息
            count = self.collection.count()
            logger.info(f"向量数据库健康检查通过，当前分块数: {count}")
            return True
        except Exception as e:
            logger.error(f"向量数据库健康检查失败: {str(e)}")
            return False


# 全局实例
vector_storage = VectorStorage()

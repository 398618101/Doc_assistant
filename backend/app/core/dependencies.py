#!/usr/bin/env python3
"""
FastAPI依赖注入
"""
from typing import Optional
from fastapi import Depends

from app.services.document_storage import DocumentStorage
from app.services.vector_storage import VectorStorage
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.rag_service import RAGService
from app.core.llm_factory import LLMFactory


# 全局服务实例
_document_storage: Optional[DocumentStorage] = None
_vector_storage: Optional[VectorStorage] = None
_embedding_service: Optional[EmbeddingService] = None
_retrieval_service: Optional[RetrievalService] = None
_rag_service: Optional[RAGService] = None


def get_document_storage() -> DocumentStorage:
    """获取文档存储服务"""
    global _document_storage
    if _document_storage is None:
        _document_storage = DocumentStorage()
    return _document_storage


def get_vector_storage() -> VectorStorage:
    """获取向量存储服务"""
    global _vector_storage
    if _vector_storage is None:
        _vector_storage = VectorStorage()
    return _vector_storage


def get_embedding_service() -> EmbeddingService:
    """获取嵌入服务"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_retrieval_service() -> RetrievalService:
    """获取检索服务"""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service


def get_llm_factory() -> LLMFactory:
    """获取LLM工厂"""
    from app.core.llm_factory import llm_factory
    return llm_factory


def get_rag_service(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    llm_factory: LLMFactory = Depends(get_llm_factory)
) -> RAGService:
    """获取RAG服务"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(
            retrieval_service=retrieval_service,
            llm_factory=llm_factory
        )
    return _rag_service

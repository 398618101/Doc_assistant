"""
向量化API端点
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.services.vector_storage import vector_storage
from app.services.embedding_service import embedding_service
from app.services.chunking_service import chunking_service
from app.services.document_storage import DocumentStorage
from app.models.document import DocumentStatus


router = APIRouter(prefix="/api/vectorization", tags=["vectorization"])
document_storage = DocumentStorage()


class VectorizeRequest(BaseModel):
    """向量化请求"""
    document_id: str
    chunk_size: int = 1000
    chunk_overlap: int = 200
    force_reprocess: bool = False


class VectorizeResponse(BaseModel):
    """向量化响应"""
    success: bool
    document_id: str
    message: str
    chunks_processed: int = 0
    embeddings_generated: int = 0
    processing_time: Optional[float] = None


class SearchRequest(BaseModel):
    """向量搜索请求"""
    query: str
    n_results: int = 5
    document_ids: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """向量搜索响应"""
    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time: Optional[float] = None


@router.post("/vectorize", response_model=VectorizeResponse)
async def vectorize_document(request: VectorizeRequest, background_tasks: BackgroundTasks):
    """向量化文档"""
    start_time = datetime.now()
    
    try:
        # 获取文档
        document = await document_storage.get_document(request.document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 检查文档是否已处理
        if not document.content and document.status != DocumentStatus.PROCESSED:
            raise HTTPException(status_code=400, detail="文档尚未处理，请先处理文档内容")
        
        # 检查是否已向量化
        if document.is_vectorized and not request.force_reprocess:
            return VectorizeResponse(
                success=True,
                document_id=request.document_id,
                message="文档已向量化，跳过处理",
                chunks_processed=document.chunk_count or 0,
                embeddings_generated=document.chunk_count or 0
            )
        
        # 启动后台向量化任务
        background_tasks.add_task(
            _vectorize_document_background,
            request.document_id,
            request.chunk_size,
            request.chunk_overlap,
            request.force_reprocess
        )
        
        return VectorizeResponse(
            success=True,
            document_id=request.document_id,
            message="向量化任务已启动，正在后台处理",
            processing_time=(datetime.now() - start_time).total_seconds()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"向量化文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"向量化失败: {str(e)}")


async def _vectorize_document_background(
    document_id: str, 
    chunk_size: int, 
    chunk_overlap: int, 
    force_reprocess: bool
):
    """后台向量化任务"""
    try:
        logger.info(f"开始向量化文档: {document_id}")
        
        # 获取文档
        document = await document_storage.get_document(document_id)
        if not document:
            logger.error(f"文档不存在: {document_id}")
            return
        
        # 如果强制重新处理，先删除现有向量
        if force_reprocess and document.is_vectorized:
            vector_storage.delete_document_chunks(document_id)
        
        # 文档分块
        chunks_data = chunking_service.chunk_text(
            text=document.content,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            document_id=document_id,
            document_type=document.document_type
        )
        
        if not chunks_data:
            logger.warning(f"文档 {document_id} 分块结果为空")
            return
        
        # 提取文本和元数据
        chunk_texts = [chunk["text"] for chunk in chunks_data]
        chunk_metadata = [chunk["metadata"] for chunk in chunks_data]
        
        # 生成嵌入向量
        embeddings = await embedding_service.generate_embeddings_batch(chunk_texts)
        
        # 过滤成功的嵌入
        valid_chunks = []
        valid_embeddings = []
        valid_metadata = []
        
        for i, embedding in enumerate(embeddings):
            if embedding is not None:
                valid_chunks.append(chunk_texts[i])
                valid_embeddings.append(embedding)
                valid_metadata.append(chunk_metadata[i])
        
        if not valid_embeddings:
            logger.error(f"文档 {document_id} 没有生成有效的嵌入向量")
            return
        
        # 存储到向量数据库
        success = vector_storage.add_document_chunks(
            document_id=document_id,
            chunks=valid_chunks,
            embeddings=valid_embeddings,
            metadata=valid_metadata
        )
        
        if success:
            # 更新文档状态
            document.is_vectorized = True
            document.chunk_count = len(valid_chunks)
            document.vector_collection = "documents"
            await document_storage.update_document(document)
            
            logger.info(f"文档 {document_id} 向量化完成: {len(valid_chunks)} 个分块")
        else:
            logger.error(f"文档 {document_id} 向量存储失败")
            
    except Exception as e:
        logger.error(f"后台向量化任务失败: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """向量搜索文档"""
    start_time = datetime.now()
    
    try:
        # 生成查询嵌入
        query_embedding = await embedding_service.generate_embedding(request.query)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="查询向量生成失败")
        
        # 执行向量搜索
        search_results = vector_storage.search_similar_chunks(
            query_embedding=query_embedding,
            n_results=request.n_results,
            document_ids=request.document_ids
        )
        
        # 格式化结果
        formatted_results = []
        for i in range(len(search_results["chunks"])):
            result = {
                "text": search_results["chunks"][i],
                "metadata": search_results["metadata"][i],
                "similarity_score": 1 - search_results["distances"][i],  # 转换为相似度分数
                "distance": search_results["distances"][i]
            }
            formatted_results.append(result)
        
        return SearchResponse(
            success=True,
            query=request.query,
            results=formatted_results,
            total_results=search_results["total_results"],
            processing_time=(datetime.now() - start_time).total_seconds()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"向量搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/stats")
async def get_vectorization_stats():
    """获取向量化统计信息"""
    try:
        # 向量数据库统计
        vector_stats = vector_storage.get_collection_stats()
        
        # 嵌入服务健康检查
        embedding_health = await embedding_service.health_check()
        
        return {
            "success": True,
            "vector_database": vector_stats,
            "embedding_service": embedding_health,
            "embedding_dimension": embedding_service.get_embedding_dimension()
        }
        
    except Exception as e:
        logger.error(f"获取向量化统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/document/{document_id}")
async def delete_document_vectors(document_id: str):
    """删除文档的向量数据"""
    try:
        success = vector_storage.delete_document_chunks(document_id)
        
        if success:
            # 更新文档状态
            document = await document_storage.get_document(document_id)
            if document:
                document.is_vectorized = False
                document.chunk_count = 0
                document.vector_collection = None
                await document_storage.update_document(document)
            
            return {"success": True, "message": f"文档 {document_id} 的向量数据已删除"}
        else:
            raise HTTPException(status_code=500, detail="删除向量数据失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档向量失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

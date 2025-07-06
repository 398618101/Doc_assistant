"""
增强的文档检索API端点
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from loguru import logger
import asyncio

from app.services.retrieval_service import retrieval_service
from app.models.retrieval import (
    AdvancedSearchRequest, AdvancedSearchResponse,
    SearchSuggestionRequest, SearchSuggestionResponse,
    SearchStatisticsResponse,
    BatchSearchRequest, BatchSearchResponse,
    DocumentClusterRequest, DocumentClusterResponse,
    SearchMode, SortBy, SortOrder
)
from app.models.document import DocumentType


router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/search", response_model=AdvancedSearchResponse)
async def advanced_search(request: AdvancedSearchRequest):
    """
    高级文档搜索
    支持语义搜索、关键词搜索和混合搜索模式
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"开始高级搜索: 查询='{request.query}', 模式={request.search_mode}")
        
        # 验证权重配置
        if request.search_mode == SearchMode.HYBRID:
            if abs(request.keyword_weight + request.semantic_weight - 1.0) > 0.01:
                raise HTTPException(
                    status_code=400, 
                    detail="混合搜索模式下，关键词权重和语义权重之和必须等于1.0"
                )
        
        # 构建日期范围
        date_range = None
        if request.date_from or request.date_to:
            date_range = (
                request.date_from or datetime.min,
                request.date_to or datetime.max
            )
        
        # 执行搜索
        search_result = await retrieval_service.hybrid_search(
            query=request.query,
            n_results=request.n_results,
            similarity_threshold=request.similarity_threshold,
            document_ids=request.document_ids,
            document_types=request.document_types,
            date_range=date_range,
            tags=request.tags,
            enable_keyword_search=(request.search_mode in [SearchMode.KEYWORD, SearchMode.HYBRID]),
            enable_semantic_search=(request.search_mode in [SearchMode.SEMANTIC, SearchMode.HYBRID]),
            keyword_weight=request.keyword_weight,
            semantic_weight=request.semantic_weight,
            include_metadata=request.include_metadata,
            deduplicate=request.deduplicate
        )
        
        if not search_result['success']:
            raise HTTPException(status_code=500, detail=search_result.get('error', '搜索失败'))
        
        # 转换为响应格式
        response = AdvancedSearchResponse(
            success=True,
            query=request.query,
            results=search_result['results'],
            total_results=search_result['total_results'],
            search_time=search_result['search_time'],
            search_strategy=search_result.get('search_strategy', {})
        )
        
        logger.info(f"高级搜索完成: 查询='{request.query}', 结果数={response.total_results}, 耗时={response.search_time:.3f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"高级搜索失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/search/simple")
async def simple_search(
    query: str = Query(..., description="搜索查询"),
    n_results: int = Query(10, ge=1, le=50, description="返回结果数量"),
    search_mode: SearchMode = Query(SearchMode.HYBRID, description="搜索模式"),
    document_types: Optional[List[DocumentType]] = Query(None, description="文档类型过滤")
):
    """
    简化的搜索接口
    适用于快速搜索场景
    """
    try:
        # 构建搜索请求
        search_request = AdvancedSearchRequest(
            query=query,
            n_results=n_results,
            search_mode=search_mode,
            document_types=document_types
        )
        
        # 执行搜索
        return await advanced_search(search_request)
        
    except Exception as e:
        logger.error(f"简单搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/search/batch", response_model=BatchSearchResponse)
async def batch_search(request: BatchSearchRequest):
    """
    批量搜索
    支持同时搜索多个查询
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"开始批量搜索: {len(request.queries)} 个查询")
        
        if len(request.queries) > 50:
            raise HTTPException(status_code=400, detail="批量搜索最多支持50个查询")
        
        # 创建搜索任务
        search_tasks = []
        for query in request.queries:
            search_req = request.search_config.model_copy()
            search_req.query = query
            search_tasks.append(advanced_search(search_req))
        
        # 并发执行搜索
        semaphore = asyncio.Semaphore(request.max_concurrent)
        
        async def limited_search(task):
            async with semaphore:
                try:
                    return await task
                except Exception as e:
                    logger.error(f"批量搜索中的单个查询失败: {str(e)}")
                    return AdvancedSearchResponse(
                        success=False,
                        query="",
                        results=[],
                        total_results=0,
                        search_time=0.0,
                        error=str(e)
                    )
        
        results = await asyncio.gather(*[limited_search(task) for task in search_tasks])
        
        # 统计结果
        successful_queries = sum(1 for r in results if r.success)
        failed_queries = len(results) - successful_queries
        total_time = (datetime.now() - start_time).total_seconds()
        
        response = BatchSearchResponse(
            success=True,
            results=results,
            total_queries=len(request.queries),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            total_time=total_time
        )
        
        logger.info(f"批量搜索完成: 总查询={len(request.queries)}, 成功={successful_queries}, 失败={failed_queries}, 耗时={total_time:.3f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量搜索失败: {str(e)}")


@router.post("/suggestions", response_model=SearchSuggestionResponse)
async def get_search_suggestions(request: SearchSuggestionRequest):
    """
    获取搜索建议
    基于历史查询和文档内容提供搜索建议
    """
    try:
        logger.info(f"获取搜索建议: '{request.partial_query}'")
        
        suggestions = []
        
        # 基于历史查询的建议
        if request.include_history:
            history_suggestions = _get_history_suggestions(
                request.partial_query, 
                request.max_suggestions // 2
            )
            suggestions.extend(history_suggestions)
        
        # 基于文档内容的建议（简化实现）
        content_suggestions = _get_content_suggestions(
            request.partial_query,
            request.max_suggestions - len(suggestions)
        )
        suggestions.extend(content_suggestions)
        
        # 按分数排序并限制数量
        suggestions = sorted(suggestions, key=lambda x: x.score, reverse=True)
        suggestions = suggestions[:request.max_suggestions]
        
        response = SearchSuggestionResponse(
            success=True,
            suggestions=suggestions,
            total_suggestions=len(suggestions)
        )
        
        logger.info(f"搜索建议完成: 返回 {len(suggestions)} 个建议")
        return response
        
    except Exception as e:
        logger.error(f"获取搜索建议失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取建议失败: {str(e)}")


@router.get("/statistics", response_model=SearchStatisticsResponse)
async def get_search_statistics():
    """
    获取搜索统计信息
    包括热门查询、搜索趋势等
    """
    try:
        logger.info("获取搜索统计信息")
        
        stats = retrieval_service.get_search_statistics()
        
        response = SearchStatisticsResponse(
            success=True,
            total_searches=stats['total_searches'],
            popular_queries=stats['popular_queries'],
            search_trends=stats['search_trends'],
            cache_size=stats['cache_size']
        )
        
        logger.info(f"搜索统计信息获取完成: 总搜索={stats['total_searches']}, 缓存大小={stats['cache_size']}")
        return response
        
    except Exception as e:
        logger.error(f"获取搜索统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/cache")
async def clear_search_cache():
    """
    清空搜索缓存
    """
    try:
        logger.info("清空搜索缓存")
        retrieval_service.clear_cache()
        return {"success": True, "message": "搜索缓存已清空"}
        
    except Exception as e:
        logger.error(f"清空搜索缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空缓存失败: {str(e)}")


def _get_history_suggestions(partial_query: str, max_suggestions: int) -> List:
    """基于历史查询获取建议"""
    # 简化实现，实际应该从搜索历史中匹配
    suggestions = []
    
    # 这里可以实现更复杂的历史查询匹配逻辑
    # 目前返回空列表
    
    return suggestions


def _get_content_suggestions(partial_query: str, max_suggestions: int) -> List:
    """基于文档内容获取建议"""
    # 简化实现，实际应该从文档内容中提取相关词汇
    suggestions = []
    
    # 这里可以实现基于文档内容的建议逻辑
    # 例如：提取高频词汇、相关术语等
    
    return suggestions

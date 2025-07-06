#!/usr/bin/env python3
"""
RAG (检索增强生成) API端点
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from loguru import logger
import json
import asyncio

from app.models.rag import (
    ChatRequest, ChatResponse, StreamingChatResponse, 
    ConversationHistory, RAGMetrics, RAGConfig
)
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from app.core.llm_factory import LLMFactory
from app.core.dependencies import get_retrieval_service, get_llm_factory


router = APIRouter(prefix="/api/rag", tags=["RAG"])

# 全局RAG服务实例
_rag_service: Optional[RAGService] = None


async def get_rag_service(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    llm_factory: LLMFactory = Depends(get_llm_factory)
) -> RAGService:
    """获取RAG服务实例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(
            retrieval_service=retrieval_service,
            llm_factory=llm_factory
        )
        logger.info("RAG服务实例已创建")
    return _rag_service


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    rag_service: RAGService = Depends(get_rag_service)
) -> ChatResponse:
    """
    智能问答接口
    
    支持基于文档内容的智能问答，包括：
    - 文档检索和上下文构建
    - 对话历史管理
    - 多种生成配置
    """
    try:
        logger.info(f"收到RAG聊天请求: {request.message[:100]}...")
        
        # 处理聊天请求
        response = await rag_service.chat(request)
        
        # 后台任务：清理过期对话
        background_tasks.add_task(rag_service.cleanup_expired_conversations)
        
        logger.info(f"RAG聊天请求处理完成: 成功={response.success}")
        return response
        
    except Exception as e:
        error_msg = f"RAG聊天处理失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    流式智能问答接口
    
    支持实时流式响应，适用于：
    - 长文本生成
    - 实时对话体验
    - 渐进式内容展示
    """
    try:
        logger.info(f"收到流式RAG聊天请求: {request.message[:100]}...")
        
        async def generate_stream():
            """生成流式响应"""
            try:
                async for chunk_response in rag_service.stream_chat(request):
                    # 将响应转换为JSON格式
                    chunk_data = chunk_response.model_dump()
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                
                # 发送结束标记
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                error_response = StreamingChatResponse(
                    conversation_id=request.conversation_id or "error",
                    chunk=f"错误: {str(e)}",
                    is_final=True
                )
                yield f"data: {json.dumps(error_response.model_dump(), ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        error_msg = f"流式RAG聊天处理失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation_history(
    conversation_id: str,
    rag_service: RAGService = Depends(get_rag_service)
) -> ConversationHistory:
    """
    获取对话历史
    
    返回指定对话ID的完整对话历史记录
    """
    try:
        logger.info(f"获取对话历史: {conversation_id}")
        
        history = rag_service.get_conversation_history(conversation_id)
        if not history:
            raise HTTPException(status_code=404, detail="对话历史不存在")
        
        logger.info(f"对话历史获取成功: {len(history.messages)} 条消息")
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"获取对话历史失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/conversations/{conversation_id}")
async def clear_conversation_history(
    conversation_id: str,
    rag_service: RAGService = Depends(get_rag_service)
) -> Dict[str, Any]:
    """
    清除对话历史
    
    删除指定对话ID的所有历史记录
    """
    try:
        logger.info(f"清除对话历史: {conversation_id}")
        
        success = rag_service.clear_conversation_history(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="对话历史不存在")
        
        logger.info(f"对话历史清除成功: {conversation_id}")
        return {
            "success": True,
            "message": "对话历史已清除",
            "conversation_id": conversation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"清除对话历史失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/metrics", response_model=RAGMetrics)
async def get_rag_metrics(
    rag_service: RAGService = Depends(get_rag_service)
) -> RAGMetrics:
    """
    获取RAG性能指标
    
    返回系统性能统计信息，包括：
    - 查询统计
    - 响应时间
    - 成功率
    - 错误统计
    """
    try:
        logger.info("获取RAG性能指标")
        
        metrics = rag_service.get_metrics()
        
        logger.info(f"RAG指标获取成功: 查询数={metrics.query_count}, 成功率={metrics.success_rate:.2%}")
        return metrics
        
    except Exception as e:
        error_msg = f"获取RAG指标失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/config", response_model=Dict[str, Any])
async def update_rag_config(
    config: RAGConfig,
    rag_service: RAGService = Depends(get_rag_service)
) -> Dict[str, Any]:
    """
    更新RAG配置
    
    动态更新RAG服务的配置参数
    """
    try:
        logger.info("更新RAG配置")
        
        # 更新配置
        rag_service.config = config
        
        logger.info("RAG配置更新成功")
        return {
            "success": True,
            "message": "RAG配置已更新",
            "config": config.model_dump()
        }
        
    except Exception as e:
        error_msg = f"更新RAG配置失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/config", response_model=RAGConfig)
async def get_rag_config(
    rag_service: RAGService = Depends(get_rag_service)
) -> RAGConfig:
    """
    获取当前RAG配置
    
    返回当前使用的RAG配置参数
    """
    try:
        logger.info("获取RAG配置")
        
        config = rag_service.config
        
        logger.info("RAG配置获取成功")
        return config
        
    except Exception as e:
        error_msg = f"获取RAG配置失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/test")
async def test_rag_system(
    rag_service: RAGService = Depends(get_rag_service)
) -> Dict[str, Any]:
    """
    测试RAG系统
    
    执行系统健康检查和基本功能测试
    """
    try:
        logger.info("开始RAG系统测试")
        
        # 测试基本问答功能
        test_request = ChatRequest(
            message="测试问题：系统是否正常工作？",
            enable_retrieval=True,
            max_retrieved_chunks=3,
            response_mode="complete"
        )
        
        start_time = asyncio.get_event_loop().time()
        response = await rag_service.chat(test_request)
        end_time = asyncio.get_event_loop().time()
        
        test_result = {
            "success": response.success,
            "response_time": end_time - start_time,
            "retrieval_enabled": response.retrieval_context is not None,
            "sources_found": len(response.sources_used) if response.sources_used else 0,
            "conversation_id": response.conversation_id,
            "message_length": len(response.message),
            "timestamp": response.timestamp.isoformat()
        }
        
        logger.info(f"RAG系统测试完成: 成功={test_result['success']}")
        return test_result
        
    except Exception as e:
        error_msg = f"RAG系统测试失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

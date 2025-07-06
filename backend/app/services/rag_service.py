#!/usr/bin/env python3
"""
RAG (检索增强生成) 服务 - 重构后的简化版本
"""
import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from loguru import logger

from app.models.rag import (
    ChatRequest, ChatResponse, StreamingChatResponse,
    ChatMessage, ChatRole, RetrievalContext, QueryAnalysis,
    RAGConfig, DocumentSource, CitationInfo, ContextStrategy
)
from app.services.retrieval_service import RetrievalService
from app.services.prompt_builder import PromptBuilder
from app.services.conversation_manager import ConversationManager
from app.services.document_storage import DocumentStorage
from app.core.llm_factory import LLMFactory


class RAGService:
    """RAG检索增强生成服务 - 重构后的简化版本"""
    
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_factory: LLMFactory,
        config: Optional[RAGConfig] = None
    ):
        self.retrieval_service = retrieval_service
        self.llm_factory = llm_factory
        self.config = config or RAGConfig()

        # 初始化子服务
        self.prompt_builder = PromptBuilder()
        self.conversation_manager = ConversationManager()
        self.document_storage = DocumentStorage()  # 添加文档存储服务

        logger.info("RAG服务初始化完成")
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """处理聊天请求"""
        start_time = time.time()
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        try:
            logger.info(f"开始处理RAG聊天请求: {request.message[:50]}...")
            
            # 1. 智能查询分析和自动化检索
            retrieval_context = None
            if request.enable_retrieval:
                retrieval_context = await self._intelligent_retrieve_context(request.message)
                logger.info(f"智能检索完成: 找到 {len(retrieval_context.retrieved_chunks) if retrieval_context else 0} 个相关文档块")
            
            # 2. 获取对话历史
            conversation_history = self.conversation_manager.get_recent_messages(
                conversation_id, limit=10
            )
            
            # 3. 构建提示词
            prompt = self.prompt_builder.build_complete_prompt(
                user_query=request.message,
                retrieval_context=retrieval_context,
                conversation_history=conversation_history,
                prompt_type='default'
            )
            
            # 4. 生成回答
            response_text, generation_info = await self._generate_response(prompt, request)
            logger.info(f"回答生成完成: {len(response_text)} 字符")
            
            # 5. 更新对话历史
            self.conversation_manager.add_message(conversation_id, ChatRole.USER, request.message)
            self.conversation_manager.add_message(conversation_id, ChatRole.ASSISTANT, response_text)
            
            # 6. 构建响应
            response_time = time.time() - start_time
            response = ChatResponse(
                success=True,
                message=response_text,
                conversation_id=conversation_id,
                response_time=response_time,
                retrieval_context=retrieval_context,
                sources_used=await self._extract_sources(retrieval_context) if retrieval_context else [],
                tokens_used=generation_info.get('tokens_used'),
                finish_reason=generation_info.get('finish_reason'),
                model_used=generation_info.get('model_used')
            )
            
            # 7. 更新指标
            self.conversation_manager.update_metrics(response_time, True)
            
            logger.info(f"RAG聊天请求处理完成: {response_time:.3f}s")
            return response
            
        except Exception as e:
            error_msg = f"RAG聊天处理失败: {str(e)}"
            logger.error(error_msg)
            
            response_time = time.time() - start_time
            self.conversation_manager.update_metrics(response_time, False)
            
            return ChatResponse(
                success=False,
                message="抱歉，处理您的请求时出现了错误，请稍后重试。",
                conversation_id=conversation_id,
                response_time=response_time,
                error_message=error_msg
            )
    
    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[StreamingChatResponse, None]:
        """流式聊天处理"""
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        try:
            logger.info(f"开始流式RAG聊天: {request.message[:50]}...")
            
            # 1. 文档检索
            retrieval_context = None
            if request.enable_retrieval:
                retrieval_context = await self._retrieve_context(
                    request.message,
                    max_chunks=request.max_retrieved_chunks,
                    similarity_threshold=request.similarity_threshold
                )
            
            # 2. 获取对话历史
            conversation_history = self.conversation_manager.get_recent_messages(
                conversation_id, limit=10
            )
            
            # 3. 构建提示词
            prompt = self.prompt_builder.build_complete_prompt(
                user_query=request.message,
                retrieval_context=retrieval_context,
                conversation_history=conversation_history,
                prompt_type='default'
            )
            
            # 4. 流式生成回答
            full_response = ""
            async for chunk in self._stream_generate_response(prompt, request):
                full_response += chunk
                yield StreamingChatResponse(
                    conversation_id=conversation_id,
                    chunk=chunk,
                    is_complete=False,
                    retrieval_context=retrieval_context if chunk == "" else None  # 只在第一个chunk发送context
                )
            
            # 5. 发送完成信号
            yield StreamingChatResponse(
                conversation_id=conversation_id,
                chunk="",
                is_complete=True,
                sources_used=await self._extract_sources(retrieval_context) if retrieval_context else []
            )
            
            # 6. 更新对话历史
            self.conversation_manager.add_message(conversation_id, ChatRole.USER, request.message)
            self.conversation_manager.add_message(conversation_id, ChatRole.ASSISTANT, full_response)
            
            logger.info("流式RAG聊天完成")
            
        except Exception as e:
            logger.error(f"流式RAG聊天失败: {str(e)}")
            yield StreamingChatResponse(
                conversation_id=conversation_id,
                chunk="",
                is_complete=True,
                error_message=f"处理请求时出现错误: {str(e)}"
            )
    
    async def _retrieve_context(
        self, 
        query: str, 
        max_chunks: int = 5,
        similarity_threshold: float = 0.7
    ) -> Optional[RetrievalContext]:
        """检索相关文档上下文"""
        try:
            search_results = await self.retrieval_service.hybrid_search(
                query=query,
                n_results=max_chunks,
                similarity_threshold=similarity_threshold
            )
            
            if not search_results or not search_results.get('results'):
                return None
            
            # 计算上下文长度
            context_length = sum(len(chunk.get('text', '')) for chunk in search_results['results'])

            # 提取来源文档信息
            sources = []
            for chunk in search_results['results']:
                metadata = chunk.get('metadata', {})
                if metadata.get('document_id'):
                    source = DocumentSource(
                        document_id=metadata['document_id'],
                        filename=metadata.get('filename', '未知文件'),
                        chunk_id=chunk.get('id', ''),
                        page_number=metadata.get('page_number'),
                        section=metadata.get('section'),
                        relevance_score=chunk.get('score', 0.0),
                        content_preview=chunk.get('text', '')[:100]
                    )
                    sources.append(source)

            return RetrievalContext(
                query=query,
                retrieved_chunks=search_results['results'],
                total_chunks=len(search_results['results']),
                retrieval_time=search_results.get('search_time', 0),
                context_length=context_length,
                sources=sources
            )
            
        except Exception as e:
            logger.error(f"文档检索失败: {str(e)}")
            return None
    
    async def _generate_response(self, prompt: str, request: ChatRequest) -> tuple[str, Dict[str, Any]]:
        """生成回答"""
        try:
            llm_provider = await self.llm_factory.get_provider()

            response = await llm_provider.generate(
                prompt=prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=False
            )

            return response.content, {
                'tokens_used': response.usage.get('total_tokens') if response.usage else None,
                'finish_reason': response.finish_reason,
                'model_used': response.model
            }

        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            raise
    
    async def _stream_generate_response(self, prompt: str, request: ChatRequest) -> AsyncGenerator[str, None]:
        """流式生成回答"""
        try:
            llm_provider = await self.llm_factory.get_provider()
            
            async for chunk in llm_provider.generate_stream(
                prompt=prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"流式生成回答失败: {str(e)}")
            yield f"生成回答时出现错误: {str(e)}"
    
    async def _extract_sources(self, retrieval_context: Optional[RetrievalContext]) -> List[Dict[str, Any]]:
        """提取文档来源信息"""
        if not retrieval_context or not retrieval_context.retrieved_chunks:
            return []

        sources = []
        seen_documents = set()  # 避免重复文档

        for chunk in retrieval_context.retrieved_chunks:
            # 获取元数据
            metadata = chunk.get('metadata', {})
            document_id = metadata.get('document_id') or chunk.get('document_id')

            # 避免重复添加同一文档
            if document_id and document_id not in seen_documents:
                seen_documents.add(document_id)

                # 从数据库获取完整的文档信息
                try:
                    document = await self.document_storage.get_document(document_id)
                    if document:
                        filename = document.original_filename
                        document_type = document.document_type
                        document_category = document.category or '未分类'
                        author = document.metadata.author if document.metadata else None
                        title = document.metadata.title if document.metadata else None
                        created_at = document.created_at.isoformat() if document.created_at else None
                    else:
                        # 如果数据库中没有找到文档，使用元数据
                        filename = metadata.get('filename') or chunk.get('filename', '未知文件')
                        document_type = metadata.get('document_type', 'unknown')
                        document_category = metadata.get('document_category', '未分类')
                        author = metadata.get('author')
                        title = metadata.get('title')
                        created_at = metadata.get('created_at')
                except Exception as e:
                    logger.warning(f"获取文档信息失败 {document_id}: {e}")
                    # 使用元数据作为备选
                    filename = metadata.get('filename') or chunk.get('filename', '未知文件')
                    document_type = metadata.get('document_type', 'unknown')
                    document_category = metadata.get('document_category', '未分类')
                    author = metadata.get('author')
                    title = metadata.get('title')
                    created_at = metadata.get('created_at')

                source_info = {
                    'document_id': document_id,
                    'filename': filename,
                    'document_type': document_type,
                    'document_category': document_category,
                    'relevance_score': chunk.get('similarity_score', chunk.get('score', 0)),
                    'chunk_id': chunk.get('id', chunk.get('chunk_id', '')),
                    'content_preview': chunk.get('text', '')[:100] if chunk.get('text') else '',
                    'page_number': metadata.get('page_number'),
                    'section': metadata.get('section'),
                    'created_at': created_at,
                    'author': author,
                    'title': title
                }
                sources.append(source_info)

        # 按相关性分数排序
        sources.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return sources
    
    # 代理方法到子服务
    def get_conversation_history(self, conversation_id: str):
        """获取对话历史"""
        return self.conversation_manager.get_conversation(conversation_id)
    
    def clear_conversation_history(self, conversation_id: str) -> bool:
        """清除对话历史"""
        return self.conversation_manager.clear_conversation(conversation_id)
    
    def get_metrics(self):
        """获取性能指标"""
        return self.conversation_manager.get_metrics()
    
    async def cleanup_expired_conversations(self):
        """清理过期的对话"""
        return self.conversation_manager.cleanup_expired_conversations()

    async def _intelligent_retrieve_context(self, query: str) -> Optional[RetrievalContext]:
        """智能检索上下文"""
        try:
            # 延迟导入以避免循环依赖
            from app.services.query_analyzer import query_analyzer
            from app.services.enhanced_vector_storage import enhanced_vector_storage

            # 1. 查询分析
            query_analysis = await query_analyzer.analyze_query(query)
            logger.info(f"查询分析完成: 意图={query_analysis.intent}, 复杂度={query_analysis.complexity_score:.2f}")

            # 2. 多策略检索
            all_chunks = []

            # 2.1 语义向量检索
            vector_chunks = await self._semantic_retrieval(
                query,
                max_results=query_analysis.suggested_retrieval_count
            )
            all_chunks.extend(vector_chunks)

            # 2.2 关键词检索
            if query_analysis.keywords:
                keyword_doc_ids = enhanced_vector_storage.search_by_keywords(
                    query_analysis.keywords,
                    max_results=5
                )
                keyword_chunks = await self._get_chunks_by_document_ids(keyword_doc_ids)
                all_chunks.extend(keyword_chunks)

            # 2.3 分类过滤检索
            suggested_categories = query_analyzer.suggest_categories(query, query_analysis.keywords)
            if suggested_categories:
                category_doc_ids = enhanced_vector_storage.search_by_category(suggested_categories)
                category_chunks = await self._get_chunks_by_document_ids(category_doc_ids)
                all_chunks.extend(category_chunks)

            # 3. 去重和排序
            unique_chunks = self._deduplicate_chunks(all_chunks)
            ranked_chunks = self._rank_chunks(unique_chunks, query_analysis)

            # 4. 限制结果数量
            final_chunks = ranked_chunks[:query_analysis.suggested_retrieval_count]

            # 5. 构建检索上下文
            if final_chunks:
                retrieval_context = RetrievalContext(
                    query=query,
                    retrieved_chunks=final_chunks,
                    total_chunks_found=len(unique_chunks),
                    retrieval_time=0.0,  # 实际时间会在调用处计算
                    strategy_used=ContextStrategy.INTELLIGENT,
                    query_analysis=query_analysis
                )

                logger.info(f"智能检索完成: 最终选择 {len(final_chunks)} 个文档块")
                return retrieval_context

            return None

        except Exception as e:
            logger.error(f"智能检索失败: {str(e)}")
            # 降级到基础检索
            return await self._retrieve_context(query, max_chunks=5, similarity_threshold=0.7)

    async def _semantic_retrieval(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """语义向量检索"""
        try:
            from app.services.enhanced_vector_storage import enhanced_vector_storage

            results = enhanced_vector_storage.search_similar_chunks(
                query_text=query,
                max_results=max_results,
                similarity_threshold=0.6
            )

            return results

        except Exception as e:
            logger.error(f"语义检索失败: {str(e)}")
            return []

    async def _get_chunks_by_document_ids(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """根据文档ID获取文档块"""
        try:
            from app.services.enhanced_vector_storage import enhanced_vector_storage

            chunks = []
            for doc_id in document_ids:
                doc_chunks = enhanced_vector_storage.get_document_chunks(doc_id)
                chunks.extend(doc_chunks[:2])  # 每个文档最多取2个块

            return chunks

        except Exception as e:
            logger.error(f"根据文档ID获取块失败: {str(e)}")
            return []

    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重文档块"""
        seen_ids = set()
        unique_chunks = []

        for chunk in chunks:
            chunk_id = chunk.get('id') or chunk.get('chunk_id')
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(chunk)

        return unique_chunks

    def _rank_chunks(self, chunks: List[Dict[str, Any]], query_analysis: QueryAnalysis) -> List[Dict[str, Any]]:
        """对文档块进行智能排序"""
        try:
            # 基于多个因素进行排序
            def calculate_score(chunk):
                score = 0.0

                # 1. 相似度分数（如果有）
                similarity = chunk.get('similarity_score', 0.5)
                score += similarity * 0.4

                # 2. 关键词匹配分数
                content = chunk.get('content', '').lower()
                keyword_matches = sum(1 for keyword in query_analysis.keywords
                                    if keyword.lower() in content)
                keyword_score = min(keyword_matches / max(len(query_analysis.keywords), 1), 1.0)
                score += keyword_score * 0.3

                # 3. 文档分类匹配分数
                doc_category = chunk.get('document_category', '')
                suggested_categories = getattr(query_analysis, 'suggested_categories', [])
                category_score = 1.0 if doc_category in suggested_categories else 0.5
                score += category_score * 0.2

                # 4. 文档新鲜度分数
                doc_date = chunk.get('document_created_at')
                if doc_date:
                    from datetime import datetime, timedelta
                    try:
                        created_date = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                        days_old = (datetime.now() - created_date).days
                        freshness_score = max(0, 1 - days_old / 365)  # 一年内的文档得分更高
                        score += freshness_score * 0.1
                    except:
                        pass

                return score

            # 按分数排序
            ranked_chunks = sorted(chunks, key=calculate_score, reverse=True)
            return ranked_chunks

        except Exception as e:
            logger.error(f"文档块排序失败: {str(e)}")
            return chunks

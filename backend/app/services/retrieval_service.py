"""
增强的文档检索服务
提供高级搜索、过滤、排序和聚合功能
"""
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from loguru import logger
import re
import asyncio
from collections import defaultdict, Counter

from app.services.vector_storage import vector_storage
from app.services.embedding_service import embedding_service
from app.services.document_storage import DocumentStorage
from app.models.document import Document, DocumentType, DocumentStatus


class RetrievalService:
    """增强的文档检索服务"""
    
    def __init__(self):
        self.document_storage = DocumentStorage()
        self.search_history = []  # 搜索历史
        self.query_cache = {}  # 查询缓存
        self.cache_ttl = 300  # 缓存5分钟
        
    async def hybrid_search(
        self,
        query: str,
        n_results: int = 10,
        similarity_threshold: float = 0.7,
        document_ids: Optional[List[str]] = None,
        document_types: Optional[List[DocumentType]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        tags: Optional[List[str]] = None,
        enable_keyword_search: bool = True,
        enable_semantic_search: bool = True,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
        include_metadata: bool = True,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """
        混合检索：结合关键词搜索和语义搜索
        
        Args:
            query: 搜索查询
            n_results: 返回结果数量
            similarity_threshold: 相似度阈值
            document_ids: 限制搜索的文档ID列表
            document_types: 限制搜索的文档类型
            date_range: 日期范围过滤
            tags: 标签过滤
            enable_keyword_search: 启用关键词搜索
            enable_semantic_search: 启用语义搜索
            keyword_weight: 关键词搜索权重
            semantic_weight: 语义搜索权重
            include_metadata: 包含元数据
            deduplicate: 去重
        """
        start_time = datetime.now()
        
        try:
            # 记录搜索历史
            self._record_search_history(query, {
                'n_results': n_results,
                'similarity_threshold': similarity_threshold,
                'document_types': document_types,
                'enable_keyword_search': enable_keyword_search,
                'enable_semantic_search': enable_semantic_search
            })
            
            # 检查缓存
            cache_key = self._generate_cache_key(query, n_results, similarity_threshold, 
                                               document_ids, document_types)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"返回缓存的搜索结果: {query}")
                return cached_result
            
            # 获取候选文档
            candidate_documents = await self._get_candidate_documents(
                document_ids, document_types, date_range, tags
            )
            
            if not candidate_documents:
                return self._empty_search_result(query, start_time)
            
            candidate_doc_ids = [doc.id for doc in candidate_documents]
            
            # 执行搜索
            results = []
            
            if enable_semantic_search:
                semantic_results = await self._semantic_search(
                    query, n_results * 2, candidate_doc_ids
                )
                results.extend(semantic_results)
            
            if enable_keyword_search:
                keyword_results = await self._keyword_search(
                    query, n_results * 2, candidate_documents
                )
                results.extend(keyword_results)
            
            # 合并和排序结果
            if enable_semantic_search and enable_keyword_search:
                results = self._merge_search_results(
                    results, keyword_weight, semantic_weight
                )
            
            # 过滤低相似度结果
            results = [r for r in results if r.get('similarity_score', 0) >= similarity_threshold]
            
            # 去重
            if deduplicate:
                results = self._deduplicate_results(results)
            
            # 排序和限制结果数量
            results = sorted(results, key=lambda x: x.get('final_score', x.get('similarity_score', 0)), reverse=True)
            results = results[:n_results]
            
            # 增强元数据
            if include_metadata:
                results = await self._enhance_results_metadata(results, candidate_documents)

            # 添加文本高亮
            results = self._add_text_highlighting(results, query)
            
            # 构建响应
            response = {
                'success': True,
                'query': query,
                'results': results,
                'total_results': len(results),
                'search_time': (datetime.now() - start_time).total_seconds(),
                'search_strategy': {
                    'semantic_enabled': enable_semantic_search,
                    'keyword_enabled': enable_keyword_search,
                    'similarity_threshold': similarity_threshold,
                    'candidate_documents': len(candidate_documents)
                }
            }
            
            # 缓存结果
            self._cache_result(cache_key, response)
            
            logger.info(f"混合搜索完成: 查询='{query}', 结果数={len(results)}, 耗时={response['search_time']:.3f}s")
            return response
            
        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                'success': False,
                'query': query,
                'results': [],
                'total_results': 0,
                'search_time': (datetime.now() - start_time).total_seconds(),
                'error': str(e)
            }
    
    async def _semantic_search(
        self, 
        query: str, 
        n_results: int, 
        document_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        try:
            # 生成查询嵌入
            query_embedding = await embedding_service.generate_embedding(query)
            if not query_embedding:
                logger.warning("查询嵌入生成失败，跳过语义搜索")
                return []
            
            # 执行向量搜索
            search_results = vector_storage.search_similar_chunks(
                query_embedding=query_embedding,
                n_results=n_results,
                document_ids=document_ids
            )
            
            # 格式化结果
            results = []
            for i in range(len(search_results["chunks"])):
                result = {
                    "text": search_results["chunks"][i],
                    "metadata": search_results["metadata"][i],
                    "similarity_score": 1 - search_results["distances"][i],
                    "distance": search_results["distances"][i],
                    "search_type": "semantic",
                    "chunk_id": search_results["metadata"][i].get("chunk_id", f"chunk_{i}"),
                    "document_id": search_results["metadata"][i].get("document_id", "unknown")
                }
                results.append(result)
            
            logger.info(f"语义搜索完成: 返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            return []
    
    async def _keyword_search(
        self, 
        query: str, 
        n_results: int, 
        documents: List[Document]
    ) -> List[Dict[str, Any]]:
        """关键词搜索"""
        try:
            # 提取关键词
            keywords = self._extract_keywords(query)
            if not keywords:
                return []
            
            results = []
            
            for doc in documents:
                if not doc.content:
                    continue
                
                # 计算关键词匹配分数
                keyword_score = self._calculate_keyword_score(doc.content, keywords)
                if keyword_score > 0:
                    # 找到匹配的文本片段
                    matched_snippets = self._find_matching_snippets(doc.content, keywords)
                    
                    for snippet in matched_snippets[:3]:  # 每个文档最多3个片段
                        result = {
                            "text": snippet["text"],
                            "metadata": {
                                "document_id": doc.id,
                                "filename": doc.filename,
                                "document_type": doc.document_type,
                                "matched_keywords": snippet["matched_keywords"]
                            },
                            "similarity_score": keyword_score,
                            "search_type": "keyword",
                            "document_id": doc.id,
                            "snippet_start": snippet["start"],
                            "snippet_end": snippet["end"]
                        }
                        results.append(result)
            
            # 按关键词匹配分数排序
            results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)
            results = results[:n_results]
            
            logger.info(f"关键词搜索完成: 返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            return []

    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询中的关键词"""
        # 简单的关键词提取，可以后续使用更高级的NLP技术
        try:
            import jieba
        except ImportError:
            # 如果jieba不可用，使用简单的空格分词
            words = query.split()
            return [word.strip() for word in words if len(word.strip()) > 1]

        # 分词
        words = list(jieba.cut(query))

        # 过滤停用词和短词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        keywords = [word.strip() for word in words if len(word.strip()) > 1 and word.strip() not in stop_words]

        return keywords

    def _calculate_keyword_score(self, content: str, keywords: List[str]) -> float:
        """计算关键词匹配分数"""
        if not content or not keywords:
            return 0.0

        content_lower = content.lower()
        total_score = 0.0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 计算关键词出现次数
            count = content_lower.count(keyword_lower)
            if count > 0:
                # 基于TF-IDF的简单评分
                tf = count / len(content.split())
                score = tf * (1 + len(keyword) / 10)  # 长词权重更高
                total_score += score

        # 归一化分数
        return min(total_score, 1.0)

    def _find_matching_snippets(self, content: str, keywords: List[str], snippet_length: int = 200) -> List[Dict[str, Any]]:
        """找到包含关键词的文本片段"""
        snippets = []
        content_lower = content.lower()

        for keyword in keywords:
            keyword_lower = keyword.lower()
            start = 0

            while True:
                pos = content_lower.find(keyword_lower, start)
                if pos == -1:
                    break

                # 确定片段范围
                snippet_start = max(0, pos - snippet_length // 2)
                snippet_end = min(len(content), pos + len(keyword) + snippet_length // 2)

                snippet_text = content[snippet_start:snippet_end]

                # 检查是否已有相似片段
                is_duplicate = False
                for existing in snippets:
                    if abs(existing["start"] - snippet_start) < snippet_length // 2:
                        is_duplicate = True
                        # 合并关键词
                        existing["matched_keywords"] = list(set(existing["matched_keywords"] + [keyword]))
                        break

                if not is_duplicate:
                    snippets.append({
                        "text": snippet_text,
                        "start": snippet_start,
                        "end": snippet_end,
                        "matched_keywords": [keyword]
                    })

                start = pos + 1

        # 按匹配关键词数量排序
        snippets = sorted(snippets, key=lambda x: len(x["matched_keywords"]), reverse=True)
        return snippets

    def _merge_search_results(
        self,
        results: List[Dict[str, Any]],
        keyword_weight: float,
        semantic_weight: float
    ) -> List[Dict[str, Any]]:
        """合并关键词搜索和语义搜索结果"""
        # 按文档ID和文本内容分组
        grouped_results = defaultdict(list)

        for result in results:
            key = f"{result.get('document_id', 'unknown')}_{hash(result.get('text', ''))}"
            grouped_results[key].append(result)

        merged_results = []

        for group in grouped_results.values():
            if len(group) == 1:
                # 只有一种搜索类型的结果
                result = group[0]
                result['final_score'] = result.get('similarity_score', 0)
                merged_results.append(result)
            else:
                # 合并多种搜索类型的结果
                semantic_result = next((r for r in group if r.get('search_type') == 'semantic'), None)
                keyword_result = next((r for r in group if r.get('search_type') == 'keyword'), None)

                base_result = semantic_result or keyword_result

                semantic_score = semantic_result.get('similarity_score', 0) if semantic_result else 0
                keyword_score = keyword_result.get('similarity_score', 0) if keyword_result else 0

                # 计算加权分数
                final_score = semantic_score * semantic_weight + keyword_score * keyword_weight

                base_result['final_score'] = final_score
                base_result['search_type'] = 'hybrid'
                base_result['semantic_score'] = semantic_score
                base_result['keyword_score'] = keyword_score

                merged_results.append(base_result)

        return merged_results

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重搜索结果"""
        seen_texts = set()
        deduplicated = []

        for result in results:
            text = result.get('text', '')
            # 使用文本的前100个字符作为去重标识
            text_key = text[:100].strip()

            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduplicated.append(result)

        return deduplicated

    async def _get_candidate_documents(
        self,
        document_ids: Optional[List[str]] = None,
        document_types: Optional[List[DocumentType]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        tags: Optional[List[str]] = None
    ) -> List[Document]:
        """获取候选文档"""
        try:
            # 如果指定了文档ID，直接获取这些文档
            if document_ids:
                documents = []
                for doc_id in document_ids:
                    doc = await self.document_storage.get_document(doc_id)
                    if doc and doc.is_vectorized:
                        documents.append(doc)
                return documents

            # 否则根据条件筛选文档
            all_documents, _ = await self.document_storage.list_documents(
                page=1,
                page_size=1000,  # 获取大量文档进行筛选
                status=DocumentStatus.PROCESSED
            )

            # 过滤条件
            filtered_documents = []
            for doc in all_documents:
                # 必须已向量化
                if not doc.is_vectorized:
                    continue

                # 文档类型过滤
                if document_types and doc.document_type not in document_types:
                    continue

                # 日期范围过滤
                if date_range:
                    start_date, end_date = date_range
                    if doc.created_at < start_date or doc.created_at > end_date:
                        continue

                # 标签过滤
                if tags:
                    doc_tags = doc.metadata.tags if doc.metadata else []
                    if not any(tag in doc_tags for tag in tags):
                        continue

                filtered_documents.append(doc)

            logger.info(f"候选文档筛选完成: {len(filtered_documents)} 个文档")
            return filtered_documents

        except Exception as e:
            logger.error(f"获取候选文档失败: {str(e)}")
            return []

    async def _enhance_results_metadata(
        self,
        results: List[Dict[str, Any]],
        documents: List[Document]
    ) -> List[Dict[str, Any]]:
        """增强搜索结果的元数据"""
        doc_dict = {doc.id: doc for doc in documents}

        for result in results:
            doc_id = result.get('document_id')
            if doc_id and doc_id in doc_dict:
                doc = doc_dict[doc_id]
                result['document_metadata'] = {
                    'filename': doc.filename,
                    'document_type': doc.document_type,
                    'file_size': doc.file_size,
                    'created_at': doc.created_at.isoformat(),
                    'updated_at': doc.updated_at.isoformat(),
                    'tags': doc.metadata.tags if doc.metadata else [],
                    'author': doc.metadata.author if doc.metadata else None,
                    'title': doc.metadata.title if doc.metadata else None
                }

        return results

    def _record_search_history(self, query: str, params: Dict[str, Any]):
        """记录搜索历史"""
        self.search_history.append({
            'query': query,
            'timestamp': datetime.now(),
            'params': params
        })

        # 保持历史记录在合理范围内
        if len(self.search_history) > 1000:
            self.search_history = self.search_history[-500:]

    def _generate_cache_key(self, *args) -> str:
        """生成缓存键"""
        import hashlib
        key_str = str(args)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        if cache_key in self.query_cache:
            cached_item = self.query_cache[cache_key]
            if datetime.now() - cached_item['timestamp'] < timedelta(seconds=self.cache_ttl):
                return cached_item['result']
            else:
                # 缓存过期，删除
                del self.query_cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """缓存搜索结果"""
        self.query_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }

        # 清理过期缓存
        if len(self.query_cache) > 100:
            current_time = datetime.now()
            expired_keys = [
                key for key, item in self.query_cache.items()
                if current_time - item['timestamp'] > timedelta(seconds=self.cache_ttl)
            ]
            for key in expired_keys:
                del self.query_cache[key]

    def _empty_search_result(self, query: str, start_time: datetime) -> Dict[str, Any]:
        """返回空搜索结果"""
        return {
            'success': True,
            'query': query,
            'results': [],
            'total_results': 0,
            'search_time': (datetime.now() - start_time).total_seconds(),
            'message': '没有找到匹配的文档'
        }

    def get_search_statistics(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        if not self.search_history:
            return {
                'total_searches': 0,
                'popular_queries': [],
                'search_trends': {}
            }

        # 统计热门查询
        query_counter = Counter([item['query'] for item in self.search_history])
        popular_queries = query_counter.most_common(10)

        # 统计搜索趋势（按天）
        search_trends = defaultdict(int)
        for item in self.search_history:
            date_key = item['timestamp'].strftime('%Y-%m-%d')
            search_trends[date_key] += 1

        return {
            'total_searches': len(self.search_history),
            'popular_queries': [{'query': q, 'count': c} for q, c in popular_queries],
            'search_trends': dict(search_trends),
            'cache_size': len(self.query_cache)
        }

    def clear_cache(self):
        """清空缓存"""
        self.query_cache.clear()
        logger.info("搜索缓存已清空")

    def _add_text_highlighting(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """为搜索结果添加文本高亮"""
        try:
            # 提取查询关键词
            keywords = self._extract_keywords(query)
            if not keywords:
                return results

            for result in results:
                text = result.get('text', '')
                if not text:
                    continue

                # 创建高亮文本
                highlighted_text = self._highlight_keywords_in_text(text, keywords)
                result['highlight_text'] = highlighted_text

                # 如果是关键词搜索结果，确保匹配的关键词信息存在
                if result.get('search_type') == 'keyword' and 'matched_keywords' not in result:
                    matched_keywords = [kw for kw in keywords if kw.lower() in text.lower()]
                    result['matched_keywords'] = matched_keywords

            return results

        except Exception as e:
            logger.error(f"添加文本高亮失败: {str(e)}")
            return results

    def _highlight_keywords_in_text(self, text: str, keywords: List[str]) -> str:
        """在文本中高亮关键词"""
        try:
            highlighted_text = text

            # 按关键词长度排序，先处理长关键词避免部分匹配问题
            sorted_keywords = sorted(keywords, key=len, reverse=True)

            for keyword in sorted_keywords:
                if not keyword:
                    continue

                # 使用正则表达式进行不区分大小写的替换
                import re
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                highlighted_text = pattern.sub(
                    lambda m: f"<mark>{m.group()}</mark>",
                    highlighted_text
                )

            return highlighted_text

        except Exception as e:
            logger.error(f"关键词高亮失败: {str(e)}")
            return text

    async def get_document_similarity_matrix(self, document_ids: List[str]) -> Dict[str, Any]:
        """计算文档间的相似度矩阵"""
        try:
            logger.info(f"计算文档相似度矩阵: {len(document_ids)} 个文档")

            # 获取文档的向量表示
            document_vectors = {}

            for doc_id in document_ids:
                # 获取文档的所有分块向量
                search_results = vector_storage.search_similar_chunks(
                    query_embedding=[0.0] * 4096,  # 占位符，实际不使用
                    n_results=1000,
                    document_ids=[doc_id]
                )

                if search_results['chunks']:
                    # 简化：使用第一个分块的向量作为文档向量
                    # 实际应该计算所有分块向量的平均值
                    document_vectors[doc_id] = search_results.get('embeddings', [[]])[0]

            # 计算相似度矩阵
            similarity_matrix = {}
            for doc_id1 in document_ids:
                similarity_matrix[doc_id1] = {}
                for doc_id2 in document_ids:
                    if doc_id1 == doc_id2:
                        similarity_matrix[doc_id1][doc_id2] = 1.0
                    elif doc_id1 in document_vectors and doc_id2 in document_vectors:
                        # 计算余弦相似度
                        similarity = self._calculate_cosine_similarity(
                            document_vectors[doc_id1],
                            document_vectors[doc_id2]
                        )
                        similarity_matrix[doc_id1][doc_id2] = similarity
                    else:
                        similarity_matrix[doc_id1][doc_id2] = 0.0

            return {
                'success': True,
                'similarity_matrix': similarity_matrix,
                'document_count': len(document_ids)
            }

        except Exception as e:
            logger.error(f"计算文档相似度矩阵失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'similarity_matrix': {},
                'document_count': 0
            }

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        try:
            import numpy as np

            # 转换为numpy数组
            v1 = np.array(vec1)
            v2 = np.array(vec2)

            # 计算余弦相似度
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)

            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0

            similarity = dot_product / (norm_v1 * norm_v2)
            return float(similarity)

        except Exception as e:
            logger.error(f"计算余弦相似度失败: {str(e)}")
            return 0.0


# 创建全局检索服务实例
retrieval_service = RetrievalService()

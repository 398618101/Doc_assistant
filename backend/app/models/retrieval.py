"""
增强检索功能的数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from app.models.document import DocumentType


class SearchMode(str, Enum):
    """搜索模式"""
    SEMANTIC = "semantic"  # 纯语义搜索
    KEYWORD = "keyword"    # 纯关键词搜索
    HYBRID = "hybrid"      # 混合搜索


class SortBy(str, Enum):
    """排序方式"""
    RELEVANCE = "relevance"      # 相关性
    DATE = "date"               # 日期
    FILENAME = "filename"       # 文件名
    FILE_SIZE = "file_size"     # 文件大小


class SortOrder(str, Enum):
    """排序顺序"""
    ASC = "asc"   # 升序
    DESC = "desc" # 降序


class AdvancedSearchRequest(BaseModel):
    """高级搜索请求"""
    query: str = Field(..., description="搜索查询")
    
    # 搜索配置
    search_mode: SearchMode = Field(default=SearchMode.HYBRID, description="搜索模式")
    n_results: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="相似度阈值")
    
    # 权重配置（仅在混合模式下有效）
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="关键词搜索权重")
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="语义搜索权重")
    
    # 过滤条件
    document_ids: Optional[List[str]] = Field(default=None, description="限制搜索的文档ID列表")
    document_types: Optional[List[DocumentType]] = Field(default=None, description="文档类型过滤")
    tags: Optional[List[str]] = Field(default=None, description="标签过滤")
    
    # 日期范围过滤
    date_from: Optional[datetime] = Field(default=None, description="开始日期")
    date_to: Optional[datetime] = Field(default=None, description="结束日期")
    
    # 文件大小过滤
    min_file_size: Optional[int] = Field(default=None, description="最小文件大小（字节）")
    max_file_size: Optional[int] = Field(default=None, description="最大文件大小（字节）")
    
    # 排序配置
    sort_by: SortBy = Field(default=SortBy.RELEVANCE, description="排序方式")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序顺序")
    
    # 结果配置
    include_metadata: bool = Field(default=True, description="包含文档元数据")
    include_snippets: bool = Field(default=True, description="包含匹配片段")
    snippet_length: int = Field(default=200, ge=50, le=500, description="片段长度")
    deduplicate: bool = Field(default=True, description="去重结果")
    
    # 缓存配置
    use_cache: bool = Field(default=True, description="使用缓存")


class SearchResult(BaseModel):
    """搜索结果项"""
    # 基本信息
    text: str = Field(..., description="匹配的文本内容")
    similarity_score: float = Field(..., description="相似度分数")
    document_id: str = Field(..., description="文档ID")
    
    # 搜索相关
    search_type: str = Field(..., description="搜索类型")
    final_score: Optional[float] = Field(default=None, description="最终综合分数")
    semantic_score: Optional[float] = Field(default=None, description="语义搜索分数")
    keyword_score: Optional[float] = Field(default=None, description="关键词搜索分数")
    
    # 位置信息
    chunk_id: Optional[str] = Field(default=None, description="分块ID")
    snippet_start: Optional[int] = Field(default=None, description="片段开始位置")
    snippet_end: Optional[int] = Field(default=None, description="片段结束位置")
    
    # 匹配信息
    matched_keywords: Optional[List[str]] = Field(default=None, description="匹配的关键词")
    highlight_text: Optional[str] = Field(default=None, description="高亮显示的文本")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="基础元数据")
    document_metadata: Optional[Dict[str, Any]] = Field(default=None, description="文档元数据")


class AdvancedSearchResponse(BaseModel):
    """高级搜索响应"""
    success: bool = Field(..., description="搜索是否成功")
    query: str = Field(..., description="原始查询")
    results: List[SearchResult] = Field(..., description="搜索结果列表")
    total_results: int = Field(..., description="结果总数")
    search_time: float = Field(..., description="搜索耗时（秒）")
    
    # 搜索策略信息
    search_strategy: Dict[str, Any] = Field(default_factory=dict, description="搜索策略信息")
    
    # 分页信息（如果适用）
    page: Optional[int] = Field(default=None, description="当前页码")
    page_size: Optional[int] = Field(default=None, description="每页大小")
    total_pages: Optional[int] = Field(default=None, description="总页数")
    
    # 错误信息
    error: Optional[str] = Field(default=None, description="错误信息")
    warnings: Optional[List[str]] = Field(default=None, description="警告信息")


class SearchSuggestionRequest(BaseModel):
    """搜索建议请求"""
    partial_query: str = Field(..., description="部分查询文本")
    max_suggestions: int = Field(default=5, ge=1, le=20, description="最大建议数量")
    include_history: bool = Field(default=True, description="包含历史查询")


class SearchSuggestion(BaseModel):
    """搜索建议项"""
    text: str = Field(..., description="建议文本")
    type: str = Field(..., description="建议类型")
    score: float = Field(..., description="建议分数")
    frequency: Optional[int] = Field(default=None, description="历史频次")


class SearchSuggestionResponse(BaseModel):
    """搜索建议响应"""
    success: bool = Field(..., description="请求是否成功")
    suggestions: List[SearchSuggestion] = Field(..., description="建议列表")
    total_suggestions: int = Field(..., description="建议总数")


class SearchStatisticsResponse(BaseModel):
    """搜索统计响应"""
    success: bool = Field(..., description="请求是否成功")
    total_searches: int = Field(..., description="总搜索次数")
    popular_queries: List[Dict[str, Any]] = Field(..., description="热门查询")
    search_trends: Dict[str, int] = Field(..., description="搜索趋势")
    cache_size: int = Field(..., description="缓存大小")
    
    # 性能统计
    average_search_time: Optional[float] = Field(default=None, description="平均搜索时间")
    cache_hit_rate: Optional[float] = Field(default=None, description="缓存命中率")


class BatchSearchRequest(BaseModel):
    """批量搜索请求"""
    queries: List[str] = Field(..., description="查询列表")
    search_config: AdvancedSearchRequest = Field(..., description="搜索配置")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="最大并发数")


class BatchSearchResponse(BaseModel):
    """批量搜索响应"""
    success: bool = Field(..., description="批量搜索是否成功")
    results: List[AdvancedSearchResponse] = Field(..., description="搜索结果列表")
    total_queries: int = Field(..., description="查询总数")
    successful_queries: int = Field(..., description="成功查询数")
    failed_queries: int = Field(..., description="失败查询数")
    total_time: float = Field(..., description="总耗时")


class DocumentClusterRequest(BaseModel):
    """文档聚类请求"""
    document_ids: Optional[List[str]] = Field(default=None, description="文档ID列表")
    cluster_count: int = Field(default=5, ge=2, le=20, description="聚类数量")
    algorithm: str = Field(default="kmeans", description="聚类算法")


class DocumentCluster(BaseModel):
    """文档聚类结果"""
    cluster_id: int = Field(..., description="聚类ID")
    document_ids: List[str] = Field(..., description="文档ID列表")
    cluster_center: Optional[List[float]] = Field(default=None, description="聚类中心")
    keywords: List[str] = Field(..., description="聚类关键词")
    summary: Optional[str] = Field(default=None, description="聚类摘要")


class DocumentClusterResponse(BaseModel):
    """文档聚类响应"""
    success: bool = Field(..., description="聚类是否成功")
    clusters: List[DocumentCluster] = Field(..., description="聚类结果")
    total_documents: int = Field(..., description="文档总数")
    processing_time: float = Field(..., description="处理时间")
    algorithm_used: str = Field(..., description="使用的算法")
    error: Optional[str] = Field(default=None, description="错误信息")

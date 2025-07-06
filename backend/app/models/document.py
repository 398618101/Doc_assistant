"""
文档相关数据模型
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from pathlib import Path


class DocumentStatus(str, Enum):
    """文档状态枚举"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentType(str, Enum):
    """文档类型枚举"""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    MD = "md"
    IMAGE = "image"
    OTHER = "other"


class DocumentMetadata(BaseModel):
    """文档元数据"""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """文档分块"""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)


class Document(BaseModel):
    """文档模型"""
    id: str
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    file_hash: str
    document_type: DocumentType
    mime_type: str
    status: DocumentStatus = DocumentStatus.UPLOADING
    
    # 内容相关
    content: Optional[str] = None
    content_preview: Optional[str] = None  # 前500字符预览
    
    # 元数据
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    
    # 处理信息
    processing_info: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    # 向量化信息
    is_vectorized: bool = False
    vector_collection: Optional[str] = None
    chunk_count: int = 0

    # 分类信息
    category: Optional[str] = None  # 主分类
    subcategory: Optional[str] = None  # 子分类
    auto_tags: Optional[str] = None  # JSON格式存储自动生成的标签
    manual_tags: Optional[str] = None  # JSON格式存储用户手动添加的标签
    classification_confidence: float = 0.0  # 分类置信度
    classification_method: str = "auto"  # auto/manual/hybrid
    keywords: Optional[str] = None  # JSON格式存储提取的关键词
    summary: Optional[str] = None  # 文档摘要
    language: str = "zh"  # 文档语言
    classification_at: Optional[datetime] = None  # 分类时间

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(use_enum_values=True)


class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    tags: List[str] = Field(default_factory=list)
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)
    auto_process: bool = True
    auto_vectorize: bool = True


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    success: bool
    document_id: str
    filename: str
    file_size: int
    status: DocumentStatus
    message: str


class DocumentListRequest(BaseModel):
    """文档列表请求"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[DocumentStatus] = None
    document_type: Optional[DocumentType] = None
    search_query: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    success: bool
    documents: List[Document]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentProcessRequest(BaseModel):
    """文档处理请求"""
    force_reprocess: bool = False
    extract_metadata: bool = True
    create_chunks: bool = True
    generate_embeddings: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200


class DocumentProcessResponse(BaseModel):
    """文档处理响应"""
    success: bool
    document_id: str
    status: DocumentStatus
    message: str
    processing_info: Dict[str, Any] = Field(default_factory=dict)


class DocumentSearchRequest(BaseModel):
    """文档搜索请求"""
    query: str
    document_ids: Optional[List[str]] = None
    document_types: Optional[List[DocumentType]] = None
    tags: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    include_content: bool = True


class DocumentSearchResult(BaseModel):
    """文档搜索结果"""
    document_id: str
    chunk_id: Optional[str] = None
    filename: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSearchResponse(BaseModel):
    """文档搜索响应"""
    success: bool
    query: str
    results: List[DocumentSearchResult]
    total_results: int
    search_time: float

"""
文档存储管理器
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from loguru import logger

from app.core.config import get_settings
from app.models.document import Document, DocumentStatus, DocumentType, DocumentChunk


class DocumentStorage:
    """文档存储管理器 - 使用SQLite作为元数据存储"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_path = Path(self.settings.UPLOAD_DIR).parent / "documents.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    content TEXT,
                    content_preview TEXT,
                    metadata TEXT,
                    processing_info TEXT,
                    error_message TEXT,
                    is_vectorized BOOLEAN DEFAULT FALSE,
                    vector_collection TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    start_char INTEGER NOT NULL,
                    end_char INTEGER NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)")
            
            conn.commit()
        
        logger.info(f"文档数据库已初始化: {self.db_path}")
    
    def _dict_factory(self, cursor, row):
        """SQLite行工厂函数"""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    
    def _document_from_dict(self, data: Dict) -> Document:
        """从字典创建Document对象"""
        # 解析JSON字段
        if data.get('metadata'):
            data['metadata'] = json.loads(data['metadata'])
        if data.get('processing_info'):
            data['processing_info'] = json.loads(data['processing_info'])
        
        # 转换时间戳
        for field in ['created_at', 'updated_at', 'processed_at']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        return Document(**data)
    
    async def save_document(self, document: Document) -> bool:
        """保存文档"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO documents (
                        id, filename, original_filename, file_path, file_size, file_hash,
                        document_type, mime_type, status, content, content_preview,
                        metadata, processing_info, error_message, is_vectorized,
                        vector_collection, chunk_count, created_at, updated_at, processed_at,
                        category, subcategory, auto_tags, manual_tags, classification_confidence,
                        classification_method, keywords, summary, language, classification_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document.id, document.filename, document.original_filename,
                    document.file_path, document.file_size, document.file_hash,
                    document.document_type, document.mime_type, document.status,
                    document.content, document.content_preview,
                    json.dumps(document.metadata.model_dump(), default=str),
                    json.dumps(document.processing_info, default=str),
                    document.error_message, document.is_vectorized,
                    document.vector_collection, document.chunk_count,
                    document.created_at.isoformat(), document.updated_at.isoformat(),
                    document.processed_at.isoformat() if document.processed_at else None,
                    document.category, document.subcategory, document.auto_tags, document.manual_tags,
                    document.classification_confidence, document.classification_method,
                    document.keywords, document.summary, document.language,
                    document.classification_at.isoformat() if document.classification_at else None
                ))
                conn.commit()
            
            logger.info(f"文档已保存: {document.id}")
            return True
            
        except Exception as e:
            logger.error(f"保存文档失败: {str(e)}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """获取文档"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = self._dict_factory
                cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._document_from_dict(row)
                return None
                
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return None
    
    async def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[DocumentStatus] = None,
        document_type: Optional[DocumentType] = None,
        search_query: Optional[str] = None
    ) -> tuple[List[Document], int]:
        """列出文档"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = self._dict_factory
                
                # 构建查询条件
                conditions = []
                params = []
                
                if status:
                    conditions.append("status = ?")
                    params.append(status)

                if document_type:
                    conditions.append("document_type = ?")
                    params.append(document_type)
                
                if search_query:
                    conditions.append("(original_filename LIKE ? OR content LIKE ?)")
                    params.extend([f"%{search_query}%", f"%{search_query}%"])
                
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                
                # 获取总数
                count_query = f"SELECT COUNT(*) as total FROM documents{where_clause}"
                cursor = conn.execute(count_query, params)
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                offset = (page - 1) * page_size
                query = f"""
                    SELECT * FROM documents{where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """
                cursor = conn.execute(query, params + [page_size, offset])
                rows = cursor.fetchall()
                
                documents = [self._document_from_dict(row) for row in rows]
                return documents, total
                
        except Exception as e:
            logger.error(f"列出文档失败: {str(e)}")
            return [], 0
    
    async def update_document_status(
        self, 
        document_id: str, 
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """更新文档状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                update_fields = ["status = ?", "updated_at = ?"]
                params = [status, datetime.now().isoformat()]
                
                if error_message is not None:
                    update_fields.append("error_message = ?")
                    params.append(error_message)
                
                if status == DocumentStatus.PROCESSED:
                    update_fields.append("processed_at = ?")
                    params.append(datetime.now().isoformat())
                
                params.append(document_id)
                
                query = f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()
            
            logger.info(f"文档状态已更新: {document_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"更新文档状态失败: {str(e)}")
            return False

    async def update_document(self, document: Document) -> bool:
        """更新文档信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 构建更新字段
                update_fields = [
                    "status = ?",
                    "is_vectorized = ?",
                    "vector_collection = ?",
                    "chunk_count = ?",
                    "updated_at = ?"
                ]

                params = [
                    document.status,
                    document.is_vectorized,
                    document.vector_collection,
                    document.chunk_count,
                    datetime.now().isoformat(),
                    document.id  # WHERE条件的参数
                ]

                query = f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()

            logger.info(f"文档信息已更新: {document.id}")
            return True

        except Exception as e:
            logger.error(f"更新文档信息失败: {str(e)}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 删除文档块
                conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
                # 删除文档
                conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                conn.commit()
            
            logger.info(f"文档已删除: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False
    
    async def save_document_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """保存文档块"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for chunk in chunks:
                    conn.execute("""
                        INSERT OR REPLACE INTO document_chunks (
                            chunk_id, document_id, content, chunk_index,
                            start_char, end_char, metadata, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        chunk.chunk_id, chunk.document_id, chunk.content,
                        chunk.chunk_index, chunk.start_char, chunk.end_char,
                        json.dumps(chunk.metadata, default=str),
                        chunk.created_at.isoformat()
                    ))
                conn.commit()
            
            logger.info(f"已保存 {len(chunks)} 个文档块")
            return True
            
        except Exception as e:
            logger.error(f"保存文档块失败: {str(e)}")
            return False
    
    async def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """获取文档块"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = self._dict_factory
                cursor = conn.execute("""
                    SELECT * FROM document_chunks 
                    WHERE document_id = ? 
                    ORDER BY chunk_index
                """, (document_id,))
                rows = cursor.fetchall()
                
                chunks = []
                for row in rows:
                    if row.get('metadata'):
                        row['metadata'] = json.loads(row['metadata'])
                    if row.get('created_at'):
                        row['created_at'] = datetime.fromisoformat(row['created_at'])
                    chunks.append(DocumentChunk(**row))
                
                return chunks
                
        except Exception as e:
            logger.error(f"获取文档块失败: {str(e)}")
            return []

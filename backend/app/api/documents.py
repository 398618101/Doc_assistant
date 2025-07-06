"""
文档管理API端点
"""
import uuid
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import get_settings
from app.models.document import (
    Document, DocumentType, DocumentStatus, DocumentMetadata,
    DocumentUploadRequest, DocumentUploadResponse,
    DocumentListRequest, DocumentListResponse,
    DocumentProcessRequest, DocumentProcessResponse
)
from app.services.document_processor import DocumentProcessor
from app.services.document_storage import DocumentStorage


router = APIRouter(prefix="/api/documents", tags=["documents"])

# 全局实例
document_processor = DocumentProcessor()
document_storage = DocumentStorage()


async def process_document_async(document_id: str, request: DocumentProcessRequest):
    """异步处理文档"""
    try:
        logger.info(f"开始异步处理文档: {document_id}")

        # 获取文档
        document = await document_storage.get_document(document_id)
        if not document:
            logger.error(f"文档不存在: {document_id}")
            return

        # 更新状态为处理中
        document.status = DocumentStatus.PROCESSING
        await document_storage.save_document(document)
        logger.info(f"文档 {document_id} 状态更新为处理中")

        # 处理文档
        if document.file_path and Path(document.file_path).exists():
            # 提取内容和元数据
            content, metadata = await document_processor.extract_text_and_metadata(
                Path(document.file_path),
                document.document_type
            )

            # 更新文档
            document.content = document_processor.clean_text(content)
            document.content_preview = document_processor.create_content_preview(document.content)
            document.metadata = metadata
            document.status = DocumentStatus.PROCESSED
            document.processed_at = datetime.now()

            # 保存更新
            await document_storage.save_document(document)
            logger.info(f"文档 {document_id} 处理完成")

            # 创建文档块（如果需要）
            if request.create_chunks and document.content:
                chunks = await create_document_chunks(document)
                logger.info(f"文档 {document_id} 已创建 {len(chunks)} 个文档块")
        else:
            logger.error(f"文档文件不存在: {document.file_path}")
            document.status = DocumentStatus.ERROR
            document.error_message = "文档文件不存在"
            await document_storage.save_document(document)

    except Exception as e:
        logger.error(f"异步处理文档失败 {document_id}: {str(e)}")
        try:
            # 更新错误状态
            document = await document_storage.get_document(document_id)
            if document:
                document.status = DocumentStatus.FAILED
                document.error_message = str(e)
                await document_storage.save_document(document)
        except Exception as save_error:
            logger.error(f"保存错误状态失败: {str(save_error)}")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    tags: str = Form(""),
    custom_metadata: str = Form("{}"),
    auto_process: bool = Form(True),
    auto_vectorize: bool = Form(True)
):
    """上传文档"""
    try:
        # 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 验证文件
        is_valid, message = document_processor.validate_file(file.filename, file_size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # 保存文件
        file_id, file_path, mime_type = await document_processor.save_uploaded_file(
            file_content, file.filename
        )
        
        # 计算文件哈希
        file_hash = document_processor.get_file_hash(Path(file_path))
        
        # 检测文档类型
        document_type = document_processor.detect_document_type(file.filename, mime_type)
        
        # 解析标签和自定义元数据
        import json
        try:
            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
            custom_metadata_dict = json.loads(custom_metadata) if custom_metadata else {}
        except json.JSONDecodeError:
            custom_metadata_dict = {}
        
        # 创建文档对象
        document = Document(
            id=file_id,
            filename=Path(file_path).name,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            document_type=document_type,
            mime_type=mime_type,
            status=DocumentStatus.UPLOADING,
            metadata=DocumentMetadata(tags=tags_list, custom_fields=custom_metadata_dict)
        )
        
        # 保存到数据库
        success = await document_storage.save_document(document)
        if not success:
            raise HTTPException(status_code=500, detail="保存文档失败")
        
        # 如果需要自动处理，启动处理任务
        if auto_process:
            logger.info(f"文档 {file_id} 将进行自动处理")
            try:
                # 创建处理请求
                process_request = DocumentProcessRequest(
                    force_reprocess=False,
                    create_chunks=True,
                    extract_metadata=True
                )

                # 异步处理文档
                import asyncio
                asyncio.create_task(process_document_async(file_id, process_request))
                logger.info(f"文档 {file_id} 自动处理任务已启动")

            except Exception as e:
                logger.error(f"启动文档自动处理失败: {str(e)}")
        
        return DocumentUploadResponse(
            success=True,
            document_id=file_id,
            filename=file.filename,
            file_size=file_size,
            status=DocumentStatus.UPLOADING,
            message="文件上传成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/categories/stats")
async def get_category_stats():
    """获取文档分类统计信息"""
    try:
        # 获取所有文档
        documents, _ = await document_storage.list_documents(page=1, page_size=1000)

        # 统计各分类的文档数量
        category_stats = {}
        for doc in documents:
            # 使用数据库中的分类字段，如果没有则使用默认值
            category = getattr(doc, 'category', None) or "未分类"

            if category not in category_stats:
                category_stats[category] = {
                    "category": category,
                    "count": 0,
                    "total_size": 0,
                    "latest_update": None
                }

            category_stats[category]["count"] += 1
            category_stats[category]["total_size"] += doc.file_size or 0

            # 更新最新更新时间
            if doc.updated_at:
                if not category_stats[category]["latest_update"] or doc.updated_at > category_stats[category]["latest_update"]:
                    category_stats[category]["latest_update"] = doc.updated_at

        return {
            "success": True,
            "category_stats": list(category_stats.values()),
            "total_documents": len(documents)
        }
    except Exception as e:
        logger.error(f"获取分类统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分类统计失败: {str(e)}")


@router.get("/categories/{category}")
async def get_documents_by_category(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """根据分类获取文档列表"""
    try:
        # 获取所有文档
        all_documents, _ = await document_storage.list_documents(page=1, page_size=1000)

        # 筛选指定分类的文档
        filtered_documents = []
        for doc in all_documents:
            # 使用数据库中的分类字段，处理None值
            doc_category = getattr(doc, 'category', None) or "未分类"
            if doc_category == category:
                filtered_documents.append(doc)

        # 分页处理
        total = len(filtered_documents)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_documents = filtered_documents[start_idx:end_idx]

        total_pages = (total + page_size - 1) // page_size

        return {
            "success": True,
            "documents": page_documents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "category": category
        }

    except Exception as e:
        logger.error(f"获取分类文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[DocumentStatus] = Query(None),
    document_type: Optional[DocumentType] = Query(None),
    search_query: Optional[str] = Query(None)
):
    """获取文档列表"""
    try:
        documents, total = await document_storage.list_documents(
            page=page,
            page_size=page_size,
            status=status,
            document_type=document_type,
            search_query=search_query
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return DocumentListResponse(
            success=True,
            documents=documents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/{document_id}")
async def get_document(document_id: str):
    """获取单个文档详情"""
    try:
        document = await document_storage.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return {
            "success": True,
            "document": document
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档失败: {str(e)}")


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
async def process_document(document_id: str, request: DocumentProcessRequest):
    """处理文档（提取文本、元数据等）"""
    try:
        # 获取文档
        document = await document_storage.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 检查是否需要重新处理
        if document.status == DocumentStatus.PROCESSED and not request.force_reprocess:
            return DocumentProcessResponse(
                success=True,
                document_id=document_id,
                status=document.status,
                message="文档已处理完成"
            )
        
        # 更新状态为处理中
        await document_storage.update_document_status(document_id, DocumentStatus.PROCESSING)
        
        try:
            # 提取文本和元数据
            if request.extract_metadata:
                content, metadata = await document_processor.extract_text_and_metadata(
                    Path(document.file_path), document.document_type
                )
                
                # 更新文档
                document.content = document_processor.clean_text(content)
                document.content_preview = document_processor.create_content_preview(document.content)
                document.metadata = metadata
                document.status = DocumentStatus.PROCESSED
                document.processed_at = datetime.now()
                
                # 保存更新
                await document_storage.save_document(document)
            
            # 执行文档分类
            try:
                from app.services.document_classifier import DocumentClassifier
                classifier = DocumentClassifier()
                classification_result = await classifier.classify_document(document)

                # 更新文档分类信息
                document.category = classification_result.category
                document.subcategory = classification_result.subcategory
                document.classification_confidence = classification_result.confidence
                document.classification_method = "auto"
                document.classification_at = datetime.now()

                # 设置标签和关键词
                if classification_result.auto_tags:
                    import json
                    document.auto_tags = json.dumps(classification_result.auto_tags, ensure_ascii=False)
                if classification_result.keywords:
                    document.keywords = json.dumps(classification_result.keywords, ensure_ascii=False)
                if classification_result.summary:
                    document.summary = classification_result.summary

                document.language = classification_result.language

                logger.info(f"文档分类完成: {document.filename} -> {classification_result.category} (置信度: {classification_result.confidence:.2f})")

            except Exception as e:
                logger.error(f"文档分类失败: {str(e)}")
                # 设置默认分类
                document.category = "other"
                document.classification_confidence = 0.0
                document.classification_method = "auto"
                document.classification_at = datetime.now()

            # 创建文档块（如果需要）
            if request.create_chunks and document.content:
                chunks = await create_document_chunks(document)
                if chunks:
                    await document_storage.save_document_chunks(chunks)
                    document.chunk_count = len(chunks)
                    await document_storage.save_document(document)

            # 保存最终的文档信息（包含分类结果）
            await document_storage.save_document(document)

            return DocumentProcessResponse(
                success=True,
                document_id=document_id,
                status=DocumentStatus.PROCESSED,
                message="文档处理完成",
                processing_info={
                    "content_length": len(document.content) if document.content else 0,
                    "chunk_count": document.chunk_count
                }
            )
            
        except Exception as e:
            # 处理失败，更新状态
            await document_storage.update_document_status(
                document_id, DocumentStatus.FAILED, str(e)
            )
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """删除文档"""
    try:
        # 获取文档信息
        document = await document_storage.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 删除物理文件
        try:
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"删除物理文件失败: {str(e)}")
        
        # 从数据库删除
        success = await document_storage.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除文档失败")
        
        return {
            "success": True,
            "message": "文档已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.post("/reclassify-all")
async def reclassify_all_documents():
    """重新分类所有文档"""
    try:
        # 获取所有已处理的文档
        all_documents, _ = await document_storage.list_documents(page=1, page_size=1000)
        processed_documents = [doc for doc in all_documents if doc.status == DocumentStatus.PROCESSED]

        if not processed_documents:
            return {
                "success": True,
                "message": "没有需要重新分类的文档",
                "processed_count": 0
            }

        # 导入分类器
        from app.services.document_classifier import DocumentClassifier
        classifier = DocumentClassifier()

        processed_count = 0
        failed_count = 0

        for document in processed_documents:
            try:
                # 执行文档分类
                classification_result = await classifier.classify_document(document)

                # 更新文档分类信息
                document.category = classification_result.category
                document.subcategory = classification_result.subcategory
                document.classification_confidence = classification_result.confidence
                document.classification_method = "manual"  # 标记为手动触发
                document.classification_at = datetime.now()

                # 设置标签和关键词
                if classification_result.auto_tags:
                    import json
                    document.auto_tags = json.dumps(classification_result.auto_tags, ensure_ascii=False)
                if classification_result.keywords:
                    document.keywords = json.dumps(classification_result.keywords, ensure_ascii=False)
                if classification_result.summary:
                    document.summary = classification_result.summary

                document.language = classification_result.language

                # 保存更新
                await document_storage.save_document(document)
                processed_count += 1

                logger.info(f"文档重新分类完成: {document.filename} -> {classification_result.category}")

            except Exception as e:
                logger.error(f"文档重新分类失败: {document.filename} - {str(e)}")
                failed_count += 1

        return {
            "success": True,
            "message": f"批量重新分类完成",
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total_documents": len(processed_documents)
        }

    except Exception as e:
        logger.error(f"批量重新分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量重新分类失败: {str(e)}")


@router.post("/{document_id}/reclassify")
async def reclassify_document(document_id: str):
    """重新分类单个文档"""
    try:
        # 获取文档
        document = await document_storage.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(status_code=400, detail="只能对已处理的文档进行重新分类")

        # 导入分类器
        from app.services.document_classifier import DocumentClassifier
        classifier = DocumentClassifier()

        # 执行文档分类
        classification_result = await classifier.classify_document(document)

        # 更新文档分类信息
        old_category = document.category
        document.category = classification_result.category
        document.subcategory = classification_result.subcategory
        document.classification_confidence = classification_result.confidence
        document.classification_method = "manual"  # 标记为手动触发
        document.classification_at = datetime.now()

        # 设置标签和关键词
        if classification_result.auto_tags:
            import json
            document.auto_tags = json.dumps(classification_result.auto_tags, ensure_ascii=False)
        if classification_result.keywords:
            document.keywords = json.dumps(classification_result.keywords, ensure_ascii=False)
        if classification_result.summary:
            document.summary = classification_result.summary

        document.language = classification_result.language

        # 保存更新
        await document_storage.save_document(document)

        logger.info(f"文档重新分类完成: {document.filename} {old_category} -> {classification_result.category}")

        return {
            "success": True,
            "message": "文档重新分类完成",
            "document_id": document_id,
            "old_category": old_category,
            "new_category": classification_result.category,
            "confidence": classification_result.confidence
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档重新分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档重新分类失败: {str(e)}")


async def create_document_chunks(document: Document) -> List:
    """创建文档分块"""
    from app.models.document import DocumentChunk
    
    if not document.content:
        return []
    
    chunks = []
    chunk_size = 1000  # 每块1000字符
    overlap = 200      # 重叠200字符
    
    content = document.content
    start = 0
    chunk_index = 0
    
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunk_content = content[start:end]
        
        chunk = DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document.id,
            content=chunk_content,
            chunk_index=chunk_index,
            start_char=start,
            end_char=end,
            metadata={
                "document_type": document.document_type,
                "filename": document.original_filename
            }
        )
        
        chunks.append(chunk)
        chunk_index += 1
        
        # 计算下一个块的起始位置（考虑重叠）
        start = end - overlap if end < len(content) else end
    
    return chunks

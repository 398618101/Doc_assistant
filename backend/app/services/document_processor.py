"""
文档处理服务
"""
import os
import hashlib
import mimetypes
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid

from loguru import logger
import chardet
from PyPDF2 import PdfReader
import pdfplumber
from docx import Document as DocxDocument
import markdown

from app.core.config import get_settings
from app.models.document import (
    Document, DocumentType, DocumentStatus, DocumentMetadata,
    DocumentChunk
)


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.upload_dir = Path(self.settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def detect_document_type(self, filename: str, mime_type: str) -> DocumentType:
        """检测文档类型"""
        ext = Path(filename).suffix.lower()
        
        if ext == '.pdf':
            return DocumentType.PDF
        elif ext in ['.docx']:
            return DocumentType.DOCX
        elif ext in ['.doc']:
            return DocumentType.DOC
        elif ext in ['.txt']:
            return DocumentType.TXT
        elif ext in ['.md', '.markdown']:
            return DocumentType.MD
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return DocumentType.IMAGE
        else:
            return DocumentType.OTHER
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """验证文件"""
        # 检查文件扩展名
        ext = Path(filename).suffix.lower().lstrip('.')
        if ext not in self.settings.ALLOWED_EXTENSIONS:
            return False, f"不支持的文件类型: {ext}"

        # 检查是否为暂不支持的格式
        unsupported_formats = ['doc', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']
        if ext in unsupported_formats:
            if ext == 'doc':
                return False, "暂不支持.doc格式文件，请转换为.docx格式后重新上传。支持的格式：PDF、DOCX、TXT、Markdown"
            else:
                return False, f"暂不支持{ext.upper()}格式文件。支持的格式：PDF、DOCX、TXT、Markdown"

        # 检查文件大小
        if file_size > self.settings.MAX_FILE_SIZE:
            max_size_mb = self.settings.MAX_FILE_SIZE / (1024 * 1024)
            return False, f"文件大小超过限制: {max_size_mb}MB"

        return True, "文件验证通过"
    
    async def save_uploaded_file(
        self, 
        file_content: bytes, 
        original_filename: str
    ) -> Tuple[str, str, str]:
        """保存上传的文件"""
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        ext = Path(original_filename).suffix
        filename = f"{file_id}{ext}"
        file_path = self.upload_dir / filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        
        logger.info(f"文件已保存: {filename} ({len(file_content)} bytes)")
        return file_id, str(file_path), mime_type
    
    def extract_text_from_pdf(self, file_path: Path) -> Tuple[str, DocumentMetadata]:
        """从PDF提取文本和元数据"""
        text_content = ""
        metadata = DocumentMetadata()
        
        try:
            # 使用pdfplumber提取文本（更好的文本提取）
            with pdfplumber.open(file_path) as pdf:
                metadata.page_count = len(pdf.pages)
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
            
            # 使用PyPDF2提取元数据
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                if pdf_reader.metadata:
                    metadata.title = pdf_reader.metadata.get('/Title')
                    metadata.author = pdf_reader.metadata.get('/Author')
                    metadata.subject = pdf_reader.metadata.get('/Subject')
                    metadata.creator = pdf_reader.metadata.get('/Creator')
                    metadata.producer = pdf_reader.metadata.get('/Producer')
                    
                    # 处理日期
                    creation_date = pdf_reader.metadata.get('/CreationDate')
                    if creation_date:
                        try:
                            # PDF日期格式通常是 D:YYYYMMDDHHmmSSOHH'mm'
                            date_str = str(creation_date).replace("D:", "")[:14]
                            metadata.creation_date = datetime.strptime(date_str, "%Y%m%d%H%M%S")
                        except:
                            pass
            
        except Exception as e:
            logger.error(f"PDF文本提取失败: {str(e)}")
            raise Exception(f"PDF处理失败: {str(e)}")
        
        return text_content.strip(), metadata
    
    def extract_text_from_docx(self, file_path: Path) -> Tuple[str, DocumentMetadata]:
        """从DOCX提取文本和元数据"""
        text_content = ""
        metadata = DocumentMetadata()
        
        try:
            doc = DocxDocument(file_path)
            
            # 提取文本
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            # 提取元数据
            core_props = doc.core_properties
            metadata.title = core_props.title
            metadata.author = core_props.author
            metadata.subject = core_props.subject
            metadata.creator = core_props.author
            metadata.creation_date = core_props.created
            metadata.modification_date = core_props.modified
            
            # 计算字数
            metadata.word_count = len(text_content.split())
            
        except Exception as e:
            logger.error(f"DOCX文本提取失败: {str(e)}")
            raise Exception(f"DOCX处理失败: {str(e)}")
        
        return text_content.strip(), metadata
    
    def extract_text_from_txt(self, file_path: Path) -> Tuple[str, DocumentMetadata]:
        """从TXT提取文本"""
        metadata = DocumentMetadata()

        try:
            # 对于大文件，只读取前1MB进行编码检测以提高性能
            max_detect_size = 1024 * 1024  # 1MB

            with open(file_path, 'rb') as f:
                raw_data = f.read(max_detect_size)
                encoding_result = chardet.detect(raw_data)
                detected_encoding = encoding_result.get('encoding', 'utf-8')
                confidence = encoding_result.get('confidence', 0)

            # 编码优先级列表，优先尝试常见编码
            encodings_to_try = []

            # 如果检测置信度高，优先使用检测到的编码
            if confidence > 0.7 and detected_encoding:
                encodings_to_try.append(detected_encoding)

            # 添加常见编码作为备选
            common_encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin1']
            for enc in common_encodings:
                if enc not in encodings_to_try:
                    encodings_to_try.append(enc)

            text_content = None
            used_encoding = None

            # 尝试不同编码读取文件
            for encoding in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        text_content = f.read()
                    used_encoding = encoding
                    logger.info(f"成功使用编码 {encoding} 读取TXT文件: {file_path.name}")
                    break
                except (UnicodeDecodeError, UnicodeError) as e:
                    logger.debug(f"编码 {encoding} 读取失败: {str(e)}")
                    continue

            if text_content is None:
                # 最后尝试：使用utf-8编码并忽略错误
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    text_content = f.read()
                used_encoding = 'utf-8 (with errors replaced)'
                logger.warning(f"使用UTF-8编码并替换错误字符读取文件: {file_path.name}")

            # 基本统计
            metadata.word_count = len(text_content.split())
            metadata.custom_fields = {'encoding_used': used_encoding}

        except Exception as e:
            logger.error(f"TXT文本提取失败: {str(e)}")
            raise Exception(f"TXT处理失败: {str(e)}")

        return text_content.strip(), metadata
    
    def extract_text_from_md(self, file_path: Path) -> Tuple[str, DocumentMetadata]:
        """从Markdown提取文本"""
        metadata = DocumentMetadata()
        
        try:
            # 读取Markdown文件
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 转换为HTML然后提取纯文本
            html = markdown.markdown(md_content)
            # 简单的HTML标签移除（可以使用BeautifulSoup做更好的处理）
            import re
            text_content = re.sub(r'<[^>]+>', '', html)
            
            # 基本统计
            metadata.word_count = len(text_content.split())
            
        except Exception as e:
            logger.error(f"Markdown文本提取失败: {str(e)}")
            raise Exception(f"Markdown处理失败: {str(e)}")
        
        return text_content.strip(), metadata
    
    async def extract_text_and_metadata(
        self,
        file_path: Path,
        document_type: DocumentType
    ) -> Tuple[str, DocumentMetadata]:
        """根据文档类型提取文本和元数据"""
        if document_type == DocumentType.PDF:
            return self.extract_text_from_pdf(file_path)
        elif document_type == DocumentType.DOCX:
            return self.extract_text_from_docx(file_path)
        elif document_type == DocumentType.DOC:
            # DOC格式需要特殊处理，暂时不支持
            raise Exception(f"暂不支持.doc格式文件，请转换为.docx格式后重新上传。支持的格式：PDF、DOCX、TXT、Markdown")
        elif document_type == DocumentType.TXT:
            return self.extract_text_from_txt(file_path)
        elif document_type == DocumentType.MD:
            return self.extract_text_from_md(file_path)
        elif document_type == DocumentType.IMAGE:
            raise Exception(f"暂不支持图片格式文件的文本提取。支持的格式：PDF、DOCX、TXT、Markdown")
        elif document_type == DocumentType.OTHER:
            raise Exception(f"不支持的文档格式。支持的格式：PDF、DOCX、TXT、Markdown")
        else:
            raise Exception(f"未知的文档类型: {document_type}。支持的格式：PDF、DOCX、TXT、Markdown")
    
    def create_content_preview(self, content: str, max_length: int = 500) -> str:
        """创建内容预览"""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        import re
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    async def classify_and_enhance_document(self, document: Document) -> Document:
        """对文档进行分类和增强处理"""
        try:
            # 延迟导入以避免循环依赖
            from app.services.document_classifier import document_classifier

            # 执行文档分类
            classification_result = await document_classifier.classify_document(document)

            # 更新文档信息
            document.category = classification_result.category
            document.subcategory = classification_result.subcategory
            document.classification_confidence = classification_result.confidence
            document.classification_method = "auto"
            document.classification_at = datetime.now()

            # 设置标签
            if classification_result.auto_tags:
                document.auto_tags = json.dumps(classification_result.auto_tags, ensure_ascii=False)

            # 设置关键词
            if classification_result.keywords:
                document.keywords = json.dumps(classification_result.keywords, ensure_ascii=False)

            # 设置摘要
            if classification_result.summary:
                document.summary = classification_result.summary

            # 设置语言
            document.language = classification_result.language

            logger.info(f"文档分类完成: {document.filename} -> {classification_result.category} (置信度: {classification_result.confidence:.2f})")

        except Exception as e:
            logger.error(f"文档分类失败: {str(e)}")
            # 设置默认分类
            document.category = "other"
            document.classification_confidence = 0.0
            document.classification_method = "auto"
            document.classification_at = datetime.now()

        return document

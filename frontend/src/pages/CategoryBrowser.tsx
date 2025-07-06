import React, { useState } from 'react';
import { Modal, Typography, Space } from 'antd';
import DocumentCategoryBrowser from '../components/DocumentCategoryBrowser';
import AdvancedSearch from '../components/AdvancedSearch';
import type { Document } from '../services/api';

const { Title } = Typography;

const CategoryBrowser: React.FC = () => {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [searchResults, setSearchResults] = useState<Document[]>([]);
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);

  // 处理文档选择
  const handleDocumentSelect = (document: Document) => {
    setSelectedDocument(document);
    setPreviewVisible(true);
  };

  // 处理分类筛选
  const handleCategoryFilter = (category: string) => {
    console.log('筛选分类:', category);
  };

  // 处理高级搜索
  const handleAdvancedSearch = (filters: any, results: Document[]) => {
    setSearchResults(results);
    setIsSearchMode(true);
    setSearchLoading(false);
  };

  // 重置搜索
  const handleSearchReset = () => {
    setSearchResults([]);
    setIsSearchMode(false);
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>文档分类浏览</Title>
        <p style={{ color: '#666', fontSize: 16 }}>
          按文档类别浏览和管理您的文档，支持智能分类和快速筛选
        </p>
      </div>

      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 高级搜索组件 */}
        <AdvancedSearch
          onSearch={handleAdvancedSearch}
          onReset={handleSearchReset}
          loading={searchLoading}
        />

        {/* 文档浏览组件 */}
        <DocumentCategoryBrowser
          onDocumentSelect={handleDocumentSelect}
          onCategoryFilter={handleCategoryFilter}
        />
      </Space>

      {/* 文档预览模态框 */}
      <Modal
        title={selectedDocument?.original_filename}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        {selectedDocument && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <p><strong>文件名:</strong> {selectedDocument.original_filename}</p>
              <p><strong>文件类型:</strong> {selectedDocument.document_type}</p>
              <p><strong>文件大小:</strong> {formatFileSize(selectedDocument.file_size)}</p>
              <p><strong>创建时间:</strong> {formatDate(selectedDocument.created_at)}</p>
              <p><strong>更新时间:</strong> {formatDate(selectedDocument.updated_at)}</p>
              <p><strong>分类:</strong> {(selectedDocument as any).category || '未分类'}</p>
              <p><strong>向量化状态:</strong> {selectedDocument.is_vectorized ? '已完成' : '未完成'}</p>
              {selectedDocument.chunk_count > 0 && (
                <p><strong>文档块数:</strong> {selectedDocument.chunk_count}</p>
              )}
            </div>

            {/* 自动标签 */}
            {(selectedDocument as any).auto_tags && (
              <div style={{ marginBottom: 16 }}>
                <strong>自动标签:</strong>
                <div style={{ marginTop: 8 }}>
                  {JSON.parse((selectedDocument as any).auto_tags || '[]').map((tag: string) => (
                    <span
                      key={tag}
                      style={{
                        display: 'inline-block',
                        background: '#f0f0f0',
                        padding: '2px 8px',
                        borderRadius: 4,
                        margin: '2px 4px 2px 0',
                        fontSize: 12
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 文档摘要 */}
            {(selectedDocument as any).summary && (
              <div style={{ marginBottom: 16 }}>
                <strong>文档摘要:</strong>
                <div style={{ 
                  marginTop: 8, 
                  padding: 12, 
                  background: '#f9f9f9', 
                  borderRadius: 4,
                  lineHeight: 1.6
                }}>
                  {(selectedDocument as any).summary}
                </div>
              </div>
            )}

            {/* 内容预览 */}
            {selectedDocument.content_preview && (
              <div>
                <strong>内容预览:</strong>
                <div style={{ 
                  marginTop: 8, 
                  padding: 12, 
                  background: '#f9f9f9', 
                  borderRadius: 4,
                  maxHeight: 300,
                  overflow: 'auto',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap'
                }}>
                  {selectedDocument.content_preview}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CategoryBrowser;

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Upload,
  message,
  Space,
  Tag,
  Popconfirm,
  Modal,
  Typography,
  Row,
  Col,
  Statistic,
  Progress,
  Tooltip,
} from 'antd';
import {
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileMarkdownOutlined,
  ReloadOutlined,
  CloudUploadOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadProps } from 'antd';
import { documentAPI } from '../services/api';
import type { Document } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;

const DocumentManager: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [vectorizingIds, setVectorizingIds] = useState<Set<string>>(new Set());
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // 获取文档列表
  const fetchDocuments = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await documentAPI.getDocuments(page, pageSize);
      setDocuments(response.documents);
      setPagination({
        current: page,
        pageSize,
        total: response.total,
      });
    } catch (error) {
      message.error('获取文档列表失败');
      console.error('获取文档列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 删除文档
  const handleDelete = async (documentId: string) => {
    try {
      await documentAPI.deleteDocument(documentId);
      message.success('文档删除成功');
      fetchDocuments(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error('文档删除失败');
      console.error('文档删除失败:', error);
    }
  };

  // 预览文档
  const handlePreview = async (document: Document) => {
    setSelectedDocument(document);
    setPreviewVisible(true);
  };

  // 向量化文档
  const handleVectorize = async (documentId: string) => {
    setVectorizingIds(prev => new Set(prev).add(documentId));
    try {
      await documentAPI.vectorizeDocument(documentId, true);
      message.success('文档向量化任务已启动');
      // 延迟刷新以等待向量化完成
      setTimeout(() => {
        fetchDocuments(pagination.current, pagination.pageSize);
        setVectorizingIds(prev => {
          const newSet = new Set(prev);
          newSet.delete(documentId);
          return newSet;
        });
      }, 3000);
    } catch (error) {
      message.error('文档向量化失败');
      console.error('文档向量化失败:', error);
      setVectorizingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(documentId);
        return newSet;
      });
    }
  };

  // 批量向量化未向量化的文档
  const handleBatchVectorize = async () => {
    const unvectorizedDocs = documents.filter(
      doc => !doc.is_vectorized && doc.status === 'processed'
    );

    if (unvectorizedDocs.length === 0) {
      message.info('没有需要向量化的文档');
      return;
    }

    Modal.confirm({
      title: '批量向量化确认',
      content: `确定要向量化 ${unvectorizedDocs.length} 个文档吗？这可能需要一些时间。`,
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        const batchIds = unvectorizedDocs.map(doc => doc.id);
        setVectorizingIds(prev => new Set([...prev, ...batchIds]));

        let successCount = 0;
        let failCount = 0;

        for (const doc of unvectorizedDocs) {
          try {
            await documentAPI.vectorizeDocument(doc.id, true);
            successCount++;
          } catch (error) {
            failCount++;
            console.error(`文档 ${doc.filename} 向量化失败:`, error);
          }
        }

        message.success(`批量向量化完成：成功 ${successCount} 个，失败 ${failCount} 个`);

        // 延迟刷新
        setTimeout(() => {
          fetchDocuments(pagination.current, pagination.pageSize);
          setVectorizingIds(new Set());
        }, 5000);
      }
    });
  };

  // 获取文件图标
  const getFileIcon = (documentType: string) => {
    switch (documentType.toLowerCase()) {
      case 'pdf':
        return <FilePdfOutlined style={{ color: '#ff4d4f' }} />;
      case 'docx':
      case 'doc':
        return <FileWordOutlined style={{ color: '#1890ff' }} />;
      case 'md':
        return <FileMarkdownOutlined style={{ color: '#52c41a' }} />;
      default:
        return <FileTextOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap = {
      uploading: { color: 'processing', text: '上传中' },
      processing: { color: 'processing', text: '处理中' },
      processed: { color: 'success', text: '已处理' },
      error: { color: 'error', text: '错误' },
    };
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 表格列配置
  const columns: ColumnsType<Document> = [
    {
      title: '文档',
      dataIndex: 'original_filename',
      key: 'filename',
      render: (text, record) => (
        <Space>
          {getFileIcon(record.document_type)}
          <span className="text-ellipsis" style={{ maxWidth: 200 }}>
            {text}
          </span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'document_type',
      key: 'type',
      width: 80,
      render: (type) => <Tag>{type.toUpperCase()}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'size',
      width: 100,
      render: (size) => formatFileSize(size),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => getStatusTag(status),
    },
    {
      title: '向量化状态',
      dataIndex: 'is_vectorized',
      key: 'vectorized',
      width: 120,
      render: (isVectorized, record) => {
        const isVectorizing = vectorizingIds.has(record.id);

        if (isVectorizing) {
          return (
            <Tag icon={<SyncOutlined spin />} color="processing">
              处理中
            </Tag>
          );
        }

        if (isVectorized) {
          return (
            <Tag icon={<CheckCircleOutlined />} color="success">
              已完成 ({record.chunk_count || 0}块)
            </Tag>
          );
        }

        if (record.status !== 'processed') {
          return (
            <Tag icon={<ExclamationCircleOutlined />} color="warning">
              待处理
            </Tag>
          );
        }

        return (
          <Button
            size="small"
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => handleVectorize(record.id)}
            loading={isVectorizing}
          >
            向量化
          </Button>
        );
      },
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => {
        const isVectorizing = vectorizingIds.has(record.id);

        return (
          <Space>
            <Tooltip title="预览">
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => handlePreview(record)}
                disabled={!record.content}
              />
            </Tooltip>

            {!record.is_vectorized && record.status === 'processed' && (
              <Tooltip title="向量化文档">
                <Button
                  size="small"
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={() => handleVectorize(record.id)}
                  loading={isVectorizing}
                />
              </Tooltip>
            )}

            <Popconfirm
              title="确定要删除这个文档吗？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="删除">
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  // 上传配置
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    accept: '.pdf,.docx,.doc,.txt,.md',
    showUploadList: false,
    customRequest: async ({ file, onSuccess, onError }) => {
      setUploading(true);
      try {
        const response = await documentAPI.uploadDocument(file as File, ['上传']);
        message.success(`${response.filename} 上传成功`);
        onSuccess?.(response);
        fetchDocuments(pagination.current, pagination.pageSize);
      } catch (error) {
        message.error(`${(file as File).name} 上传失败`);
        onError?.(error as Error);
      } finally {
        setUploading(false);
      }
    },
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // 统计数据
  const stats = {
    total: documents.length,
    processed: documents.filter(doc => doc.status === 'processed').length,
    vectorized: documents.filter(doc => doc.is_vectorized).length,
    processing: documents.filter(doc => doc.status === 'processing' || doc.status === 'uploading').length,
  };

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="总文档数" value={stats.total} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="已处理" value={stats.processed} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="已向量化" value={stats.vectorized} prefix={<CloudUploadOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="处理中" value={stats.processing} prefix={<ReloadOutlined spin={stats.processing > 0} />} />
          </Card>
        </Col>
      </Row>

      {/* 上传区域 */}
      <Card style={{ marginBottom: 24 }}>
        <Dragger {...uploadProps} disabled={uploading}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 PDF、Word、文本、Markdown 格式文档。支持批量上传。
          </p>
        </Dragger>
      </Card>

      {/* 文档列表 */}
      <Card
        title="文档列表"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handleBatchVectorize}
              loading={vectorizingIds.size > 0}
              disabled={documents.filter(doc => !doc.is_vectorized && doc.status === 'processed').length === 0}
            >
              批量向量化
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchDocuments(pagination.current, pagination.pageSize)}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            onChange: (page, pageSize) => {
              fetchDocuments(page, pageSize);
            },
          }}
          scroll={{ x: 800 }}
        />
      </Card>

      {/* 文档预览模态框 */}
      <Modal
        title={`预览: ${selectedDocument?.original_filename}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        {selectedDocument && (
          <div>
            <Paragraph>
              <Text strong>文件类型:</Text> {selectedDocument.document_type.toUpperCase()}
            </Paragraph>
            <Paragraph>
              <Text strong>文件大小:</Text> {formatFileSize(selectedDocument.file_size)}
            </Paragraph>
            <Paragraph>
              <Text strong>状态:</Text> {getStatusTag(selectedDocument.status)}
            </Paragraph>
            {selectedDocument.content && (
              <div>
                <Text strong>内容预览:</Text>
                <div
                  style={{
                    maxHeight: 400,
                    overflow: 'auto',
                    padding: 16,
                    background: '#f5f5f5',
                    borderRadius: 6,
                    marginTop: 8,
                  }}
                >
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                    {selectedDocument.content_preview || selectedDocument.content}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DocumentManager;

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  List,
  Tag,
  Button,
  Space,
  Typography,
  Empty,
  Spin,
  Badge,
  Tooltip,
  Input,
  Select,
  DatePicker,
  Modal,
  message,
} from 'antd';
import {
  FileTextOutlined,
  BookOutlined,
  ToolOutlined,
  UserOutlined,
  ExperimentOutlined,
  ShopOutlined,
  BankOutlined,
  FolderOutlined,
  QuestionCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  CalendarOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { Document } from '../services/api';
import { documentAPI } from '../services/api';

const { Title, Text } = Typography;
const { Search } = Input;
const { Option } = Select;
const { RangePicker } = DatePicker;

// 动态分类配置生成函数
const getDynamicCategoryConfig = (category: string) => {
  // 如果在预定义配置中存在，直接返回
  if (DOCUMENT_CATEGORIES[category as keyof typeof DOCUMENT_CATEGORIES]) {
    return DOCUMENT_CATEGORIES[category as keyof typeof DOCUMENT_CATEGORIES];
  }

  // 为未知分类生成动态配置
  const colors = ['#1890ff', '#52c41a', '#fa8c16', '#eb2f96', '#722ed1', '#13c2c2', '#f5222d', '#faad14'];
  const icons = [
    <FileTextOutlined />, <BookOutlined />, <ToolOutlined />, <UserOutlined />,
    <ExperimentOutlined />, <ShopOutlined />, <BankOutlined />, <FolderOutlined />
  ];

  // 根据分类名称生成一致的颜色和图标
  const hash = category.split('').reduce((a, b) => {
    a = ((a << 5) - a) + b.charCodeAt(0);
    return a & a;
  }, 0);

  const colorIndex = Math.abs(hash) % colors.length;
  const iconIndex = Math.abs(hash) % icons.length;

  return {
    name: category,
    icon: icons[iconIndex],
    color: colors[colorIndex],
    description: `${category}类型的文档`
  };
};

// 文档分类配置
const DOCUMENT_CATEGORIES = {
  'tech-docs': {
    name: '技术文档',
    icon: <ToolOutlined />,
    color: '#1890ff',
    description: 'API文档、技术规范、开发指南等'
  },
  'research': {
    name: '研究报告',
    icon: <ExperimentOutlined />,
    color: '#52c41a',
    description: '研究报告、调研分析、数据分析等'
  },
  'manual': {
    name: '操作手册',
    icon: <BookOutlined />,
    color: '#fa8c16',
    description: '用户手册、操作指南、使用说明等'
  },
  'resume': {
    name: '个人简历',
    icon: <UserOutlined />,
    color: '#eb2f96',
    description: '个人简历、求职材料、履历等'
  },
  'academic': {
    name: '学术论文',
    icon: <FileTextOutlined />,
    color: '#722ed1',
    description: '学术论文、期刊文章、会议论文等'
  },
  'business': {
    name: '商业文档',
    icon: <ShopOutlined />,
    color: '#13c2c2',
    description: '商业计划、财务报告、合同等'
  },
  'legal': {
    name: '法律文件',
    icon: <BankOutlined />,
    color: '#f5222d',
    description: '法律条文、合同协议、法规等'
  },
  'other': {
    name: '其他文档',
    icon: <FolderOutlined />,
    color: '#8c8c8c',
    description: '未分类或其他类型文档'
  },
  '未分类': {
    name: '未分类',
    icon: <QuestionCircleOutlined />,
    color: '#d9d9d9',
    description: '尚未进行分类的文档'
  }
};

interface CategoryStats {
  category: string;
  count: number;
  totalSize: number;
  lastUpdated: string;
}

interface DocumentCategoryBrowserProps {
  onDocumentSelect?: (document: Document) => void;
  onCategoryFilter?: (category: string) => void;
}

const DocumentCategoryBrowser: React.FC<DocumentCategoryBrowserProps> = ({
  onDocumentSelect,
  onCategoryFilter
}) => {
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [categoryStats, setCategoryStats] = useState<CategoryStats[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'size'>('date');
  const [dateRange, setDateRange] = useState<[any, any] | null>(null);
  const [reclassifyLoading, setReclassifyLoading] = useState(false);
  const [reclassifyingDocId, setReclassifyingDocId] = useState<string | null>(null);
  const [showReclassifyModal, setShowReclassifyModal] = useState(false);

  // 加载分类统计数据
  const loadCategoryStats = async () => {
    try {
      const response = await documentAPI.getCategoryStats();
      if (response.success) {
        const stats = response.category_stats.map(stat => ({
          category: stat.category,
          count: stat.count,
          totalSize: stat.total_size,
          lastUpdated: stat.latest_update
        }));
        setCategoryStats(stats);
      }
    } catch (error) {
      console.error('加载分类统计失败:', error);
    }
  };

  // 加载指定分类的文档
  const loadDocumentsByCategory = async (category: string) => {
    setLoading(true);
    try {
      const response = await documentAPI.getDocumentsByCategory(category, 1, 100);
      if (response.success) {
        setDocuments(response.documents);
      }
    } catch (error) {
      console.error('加载分类文档失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载所有文档（用于显示全部）
  const loadAllDocuments = async () => {
    setLoading(true);
    try {
      const response = await documentAPI.getDocuments(1, 100);
      if (response.success) {
        setDocuments(response.documents);
      }
    } catch (error) {
      console.error('加载文档失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 重新分类所有文档
  const handleReclassifyAll = () => {
    setShowReclassifyModal(true);
  };

  // 确认重新分类所有文档
  const confirmReclassifyAll = async () => {
    setShowReclassifyModal(false);
    setReclassifyLoading(true);
    try {
      const response = await documentAPI.reclassifyAllDocuments();
      if (response.success) {
        message.success(`重新分类完成！处理了 ${response.processed_count} 个文档，失败 ${response.failed_count} 个`);
        // 刷新数据
        await loadCategoryStats();
        if (selectedCategory) {
          await loadDocumentsByCategory(selectedCategory);
        } else {
          await loadAllDocuments();
        }
      } else {
        message.error('重新分类失败');
      }
    } catch (error) {
      console.error('重新分类失败:', error);
      message.error('重新分类失败，请稍后重试');
    } finally {
      setReclassifyLoading(false);
    }
  };

  // 重新分类单个文档
  const handleReclassifyDocument = async (documentId: string) => {
    setReclassifyingDocId(documentId);
    try {
      const response = await documentAPI.reclassifyDocument(documentId);
      if (response.success) {
        message.success(`文档重新分类完成：${response.old_category || '未分类'} → ${response.new_category}`);
        // 刷新数据
        await loadCategoryStats();
        if (selectedCategory) {
          await loadDocumentsByCategory(selectedCategory);
        } else {
          await loadAllDocuments();
        }
      } else {
        message.error('重新分类失败');
      }
    } catch (error) {
      console.error('重新分类失败:', error);
      message.error('重新分类失败，请稍后重试');
    } finally {
      setReclassifyingDocId(null);
    }
  };

  // 处理分类选择
  const handleCategorySelect = async (category: string) => {
    setSelectedCategory(category);
    if (category === '') {
      // 显示所有文档
      await loadAllDocuments();
    } else {
      // 显示指定分类的文档
      await loadDocumentsByCategory(category);
    }
    onCategoryFilter(category);
  };

  // 过滤文档
  const getFilteredDocuments = () => {
    let filtered = documents;

    // 按分类过滤
    if (selectedCategory) {
      filtered = filtered.filter(doc => (doc as any).category === selectedCategory);
    }

    // 按关键词过滤
    if (searchKeyword) {
      const keyword = searchKeyword.toLowerCase();
      filtered = filtered.filter(doc => 
        doc.filename.toLowerCase().includes(keyword) ||
        doc.original_filename.toLowerCase().includes(keyword) ||
        (doc.content_preview && doc.content_preview.toLowerCase().includes(keyword))
      );
    }

    // 按日期范围过滤
    if (dateRange && dateRange[0] && dateRange[1]) {
      const [startDate, endDate] = dateRange;
      filtered = filtered.filter(doc => {
        const docDate = new Date(doc.created_at);
        return docDate >= startDate.toDate() && docDate <= endDate.toDate();
      });
    }

    // 排序
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.original_filename.localeCompare(b.original_filename);
        case 'size':
          return b.file_size - a.file_size;
        case 'date':
        default:
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
    });

    return filtered;
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
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  useEffect(() => {
    // 初始化时加载分类统计和所有文档
    loadCategoryStats();
    loadAllDocuments();
  }, []);

  const filteredDocuments = getFilteredDocuments();

  return (
    <div style={{ padding: '0 0 24px 0' }}>
      {/* 分类统计卡片 */}
      <Card
        title="文档分类统计"
        style={{ marginBottom: 24 }}
        extra={
          <Button
            type="primary"
            icon={<SyncOutlined />}
            loading={reclassifyLoading}
            onClick={handleReclassifyAll}
            size="small"
          >
            全面重新分析
          </Button>
        }
      >
        <Row gutter={[16, 16]}>
          {categoryStats.map(stat => {
            const categoryConfig = getDynamicCategoryConfig(stat.category);
            return (
              <Col xs={12} sm={8} md={6} lg={4} xl={3} key={stat.category}>
                <Card
                  hoverable
                  size="small"
                  style={{
                    borderColor: selectedCategory === stat.category ? categoryConfig.color : undefined,
                    backgroundColor: selectedCategory === stat.category ? `${categoryConfig.color}10` : undefined
                  }}
                  onClick={() => {
                    const newCategory = selectedCategory === stat.category ? '' : stat.category;
                    handleCategorySelect(newCategory);
                  }}
                >
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: categoryConfig.color, marginBottom: 8 }}>
                      {categoryConfig.icon}
                    </div>
                    <div style={{ marginBottom: 4 }}>
                      <Text strong>{categoryConfig.name}</Text>
                    </div>
                    <Badge count={stat.count} style={{ backgroundColor: categoryConfig.color }} />
                    <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                      {formatFileSize(stat.totalSize)}
                    </div>
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      </Card>

      {/* 搜索和过滤工具栏 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="搜索文档名称或内容..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onSearch={setSearchKeyword}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="排序方式"
              value={sortBy}
              onChange={setSortBy}
              style={{ width: '100%' }}
            >
              <Option value="date">按日期</Option>
              <Option value="name">按名称</Option>
              <Option value="size">按大小</Option>
            </Select>
          </Col>
          <Col xs={12} sm={6} md={6}>
            <RangePicker
              placeholder={['开始日期', '结束日期']}
              value={dateRange}
              onChange={setDateRange}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={6}>
            <Space>
              <Button
                icon={<FilterOutlined />}
                onClick={() => {
                  setSearchKeyword('');
                  setDateRange(null);
                  handleCategorySelect('');
                }}
              >
                清除筛选
              </Button>
              <Text type="secondary">
                共 {filteredDocuments.length} 个文档
              </Text>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 文档列表 */}
      <Card title={selectedCategory ? `${getDynamicCategoryConfig(selectedCategory).name} 文档` : '所有文档'}>
        <Spin spinning={loading}>
          {filteredDocuments.length > 0 ? (
            <List
              dataSource={filteredDocuments}
              renderItem={(doc) => {
                const categoryConfig = getDynamicCategoryConfig((doc as any).category || 'other');
                return (
                  <List.Item
                    actions={[
                      <Button
                        type="link"
                        onClick={() => onDocumentSelect?.(doc)}
                      >
                        查看详情
                      </Button>,
                      <Button
                        type="link"
                        icon={<ReloadOutlined />}
                        loading={reclassifyingDocId === doc.id}
                        onClick={() => handleReclassifyDocument(doc.id)}
                        disabled={doc.status !== 'processed'}
                      >
                        重新分类
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <div style={{ fontSize: 24, color: categoryConfig.color }}>
                          {categoryConfig.icon}
                        </div>
                      }
                      title={
                        <Space>
                          <Text strong>{doc.original_filename}</Text>
                          <Tag color={categoryConfig.color} size="small">
                            {categoryConfig.name}
                          </Tag>
                          {(doc as any).auto_tags && JSON.parse((doc as any).auto_tags || '[]').map((tag: string) => (
                            <Tag key={tag} size="small">{tag}</Tag>
                          ))}
                        </Space>
                      }
                      description={
                        <div>
                          <div style={{ marginBottom: 4 }}>
                            {doc.content_preview && (
                              <Text type="secondary" ellipsis>
                                {doc.content_preview}
                              </Text>
                            )}
                          </div>
                          <Space size="middle">
                            <Text type="secondary">
                              <CalendarOutlined /> {formatDate(doc.created_at)}
                            </Text>
                            <Text type="secondary">
                              大小: {formatFileSize(doc.file_size)}
                            </Text>
                            {doc.is_vectorized && (
                              <Tag color="green" size="small">已向量化</Tag>
                            )}
                          </Space>
                        </div>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          ) : (
            <Empty description="暂无文档" />
          )}
        </Spin>
      </Card>

      {/* 重新分类确认对话框 */}
      <Modal
        title="确认重新分类"
        open={showReclassifyModal}
        onOk={confirmReclassifyAll}
        onCancel={() => setShowReclassifyModal(false)}
        okText="确定"
        cancelText="取消"
        confirmLoading={reclassifyLoading}
      >
        <p>这将对所有已处理的文档重新进行智能分类，可能需要一些时间。确定要继续吗？</p>
      </Modal>
    </div>
  );
};

export default DocumentCategoryBrowser;

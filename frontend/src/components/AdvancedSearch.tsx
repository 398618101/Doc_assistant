import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Space,
  Collapse,
  Tag,
  Typography,
  Row,
  Col,
  Slider,
  Switch,
  Tooltip,
  message,
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  ClearOutlined,
  DownOutlined,
  UpOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type { Document } from '../services/api';
import { documentAPI } from '../services/api';

const { Option } = Select;
const { RangePicker } = DatePicker;
const { TextArea } = Input;
const { Text } = Typography;
const { Panel } = Collapse;

// 文档分类选项
const DOCUMENT_CATEGORIES = [
  { value: 'tech-docs', label: '技术文档', color: '#1890ff' },
  { value: 'research', label: '研究报告', color: '#52c41a' },
  { value: 'manual', label: '操作手册', color: '#fa8c16' },
  { value: 'resume', label: '个人简历', color: '#eb2f96' },
  { value: 'academic', label: '学术论文', color: '#722ed1' },
  { value: 'business', label: '商业文档', color: '#13c2c2' },
  { value: 'legal', label: '法律文件', color: '#f5222d' },
  { value: 'other', label: '其他文档', color: '#8c8c8c' },
];

// 文档类型选项
const DOCUMENT_TYPES = [
  { value: 'pdf', label: 'PDF文档' },
  { value: 'docx', label: 'Word文档' },
  { value: 'txt', label: '文本文件' },
  { value: 'md', label: 'Markdown文档' },
];

// 排序选项
const SORT_OPTIONS = [
  { value: 'relevance', label: '相关度' },
  { value: 'date_desc', label: '最新优先' },
  { value: 'date_asc', label: '最旧优先' },
  { value: 'name_asc', label: '名称A-Z' },
  { value: 'name_desc', label: '名称Z-A' },
  { value: 'size_desc', label: '大小(大到小)' },
  { value: 'size_asc', label: '大小(小到大)' },
];

interface SearchFilters {
  keyword?: string;
  categories?: string[];
  documentTypes?: string[];
  dateRange?: [any, any] | null;
  sizeRange?: [number, number];
  tags?: string[];
  isVectorized?: boolean;
  minRelevanceScore?: number;
  sortBy?: string;
  semanticSearch?: boolean;
  exactMatch?: boolean;
}

interface AdvancedSearchProps {
  onSearch: (filters: SearchFilters, results: Document[]) => void;
  onReset: () => void;
  loading?: boolean;
}

const AdvancedSearch: React.FC<AdvancedSearchProps> = ({
  onSearch,
  onReset,
  loading = false
}) => {
  const [form] = Form.useForm();
  const [expanded, setExpanded] = useState(false);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  // 加载可用标签
  const loadAvailableTags = async () => {
    try {
      // 这里应该调用API获取所有可用标签
      // 暂时使用模拟数据
      const mockTags = ['技术', '报告', '手册', '研究', '分析', '设计', '开发', '测试'];
      setAvailableTags(mockTags);
    } catch (error) {
      console.error('加载标签失败:', error);
    }
  };

  // 加载搜索历史
  const loadSearchHistory = () => {
    const history = localStorage.getItem('search_history');
    if (history) {
      setSearchHistory(JSON.parse(history));
    }
  };

  // 保存搜索历史
  const saveSearchHistory = (keyword: string) => {
    if (!keyword.trim()) return;
    
    const newHistory = [keyword, ...searchHistory.filter(h => h !== keyword)].slice(0, 10);
    setSearchHistory(newHistory);
    localStorage.setItem('search_history', JSON.stringify(newHistory));
  };

  // 执行搜索
  const handleSearch = async (values: any) => {
    try {
      const filters: SearchFilters = {
        keyword: values.keyword?.trim(),
        categories: values.categories,
        documentTypes: values.documentTypes,
        dateRange: values.dateRange,
        sizeRange: values.sizeRange,
        tags: values.tags,
        isVectorized: values.isVectorized,
        minRelevanceScore: values.minRelevanceScore,
        sortBy: values.sortBy || 'relevance',
        semanticSearch: values.semanticSearch !== false,
        exactMatch: values.exactMatch === true,
      };

      // 保存搜索历史
      if (filters.keyword) {
        saveSearchHistory(filters.keyword);
      }

      // 调用搜索API
      const response = await documentAPI.getDocuments(1, 100); // 获取文档列表
      if (response.success) {
        // 这里应该根据filters过滤结果
        // 暂时返回所有文档
        onSearch(filters, response.documents);
        message.success(`找到 ${response.documents.length} 个相关文档`);
      }
    } catch (error) {
      console.error('搜索失败:', error);
      message.error('搜索失败，请重试');
    }
  };

  // 重置搜索
  const handleReset = () => {
    form.resetFields();
    onReset();
  };

  // 快速搜索历史
  const handleHistorySearch = (keyword: string) => {
    form.setFieldsValue({ keyword });
    handleSearch({ keyword });
  };

  useEffect(() => {
    loadAvailableTags();
    loadSearchHistory();
  }, []);

  return (
    <Card
      title={
        <Space>
          <SearchOutlined />
          <span>高级搜索</span>
          <Button
            type="text"
            size="small"
            icon={expanded ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '收起' : '展开'}
          </Button>
        </Space>
      }
      size="small"
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSearch}
        initialValues={{
          sortBy: 'relevance',
          semanticSearch: true,
          sizeRange: [0, 100],
          minRelevanceScore: 0,
        }}
      >
        {/* 基础搜索 */}
        <Row gutter={16}>
          <Col xs={24} sm={16} md={18}>
            <Form.Item name="keyword" label="搜索关键词">
              <Input
                placeholder="输入关键词搜索文档内容..."
                allowClear
                suffix={
                  <Tooltip title="支持多个关键词，用空格分隔">
                    <QuestionCircleOutlined style={{ color: '#999' }} />
                  </Tooltip>
                }
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Form.Item label=" ">
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SearchOutlined />}
                  loading={loading}
                >
                  搜索
                </Button>
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleReset}
                >
                  重置
                </Button>
              </Space>
            </Form.Item>
          </Col>
        </Row>

        {/* 搜索历史 */}
        {searchHistory.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>搜索历史:</Text>
            <div style={{ marginTop: 4 }}>
              {searchHistory.slice(0, 5).map((keyword, index) => (
                <Tag
                  key={index}
                  style={{ cursor: 'pointer', marginBottom: 4 }}
                  onClick={() => handleHistorySearch(keyword)}
                >
                  {keyword}
                </Tag>
              ))}
            </div>
          </div>
        )}

        {/* 高级选项 */}
        {expanded && (
          <Collapse ghost>
            <Panel header="筛选条件" key="filters">
              <Row gutter={16}>
                <Col xs={24} sm={12} md={8}>
                  <Form.Item name="categories" label="文档分类">
                    <Select
                      mode="multiple"
                      placeholder="选择文档分类"
                      allowClear
                    >
                      {DOCUMENT_CATEGORIES.map(cat => (
                        <Option key={cat.value} value={cat.value}>
                          <Tag color={cat.color} size="small">{cat.label}</Tag>
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12} md={8}>
                  <Form.Item name="documentTypes" label="文档类型">
                    <Select
                      mode="multiple"
                      placeholder="选择文档类型"
                      allowClear
                    >
                      {DOCUMENT_TYPES.map(type => (
                        <Option key={type.value} value={type.value}>
                          {type.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12} md={8}>
                  <Form.Item name="sortBy" label="排序方式">
                    <Select placeholder="选择排序方式">
                      {SORT_OPTIONS.map(option => (
                        <Option key={option.value} value={option.value}>
                          {option.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item name="dateRange" label="创建时间">
                    <RangePicker
                      style={{ width: '100%' }}
                      placeholder={['开始日期', '结束日期']}
                    />
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Form.Item name="tags" label="文档标签">
                    <Select
                      mode="tags"
                      placeholder="选择或输入标签"
                      allowClear
                    >
                      {availableTags.map(tag => (
                        <Option key={tag} value={tag}>{tag}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item name="sizeRange" label="文件大小 (MB)">
                    <Slider
                      range
                      min={0}
                      max={100}
                      marks={{
                        0: '0MB',
                        25: '25MB',
                        50: '50MB',
                        75: '75MB',
                        100: '100MB+'
                      }}
                    />
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Form.Item name="minRelevanceScore" label="最低相关度 (%)">
                    <Slider
                      min={0}
                      max={100}
                      marks={{
                        0: '0%',
                        50: '50%',
                        100: '100%'
                      }}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Panel>

            <Panel header="搜索选项" key="options">
              <Row gutter={16}>
                <Col xs={24} sm={8}>
                  <Form.Item name="semanticSearch" valuePropName="checked">
                    <Space>
                      <Switch size="small" />
                      <span>语义搜索</span>
                      <Tooltip title="使用AI理解搜索意图，提供更智能的搜索结果">
                        <QuestionCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={8}>
                  <Form.Item name="exactMatch" valuePropName="checked">
                    <Space>
                      <Switch size="small" />
                      <span>精确匹配</span>
                      <Tooltip title="只返回完全匹配关键词的结果">
                        <QuestionCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={8}>
                  <Form.Item name="isVectorized" valuePropName="checked">
                    <Space>
                      <Switch size="small" />
                      <span>仅已向量化</span>
                      <Tooltip title="只搜索已经向量化的文档">
                        <QuestionCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  </Form.Item>
                </Col>
              </Row>
            </Panel>
          </Collapse>
        )}
      </Form>
    </Card>
  );
};

export default AdvancedSearch;

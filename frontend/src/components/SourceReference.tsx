import React, { useState } from 'react';
import {
  Tag,
  Tooltip,
  Modal,
  Typography,
  Space,
  Button,
  Divider,
  Progress,
  Card,
} from 'antd';
import {
  FileTextOutlined,
  LinkOutlined,
  EyeOutlined,
  PercentageOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import {
  useResponsive,
  getResponsiveModalWidth,
  getResponsiveFontSize,
  getResponsiveSpacing
} from '../utils/responsive';

const { Text, Paragraph } = Typography;

interface SourceItem {
  filename?: string;
  document_id?: string;
  chunk_id?: string;
  content?: string;
  content_preview?: string;
  relevance_score?: number;
  similarity_score?: number;
  document_category?: string;
  created_at?: string;
  page_number?: number;
  chunk_index?: number;
}

interface SourceReferenceProps {
  sources: SourceItem[];
  style?: React.CSSProperties;
}

const SourceReference: React.FC<SourceReferenceProps> = ({ sources, style }) => {
  const [selectedSource, setSelectedSource] = useState<SourceItem | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const { isMobile, isTablet, windowWidth } = useResponsive();

  // 获取文档类型图标和颜色
  const getDocumentTypeInfo = (category?: string) => {
    const categoryMap: { [key: string]: { color: string; name: string } } = {
      'tech-docs': { color: '#1890ff', name: '技术文档' },
      'research': { color: '#52c41a', name: '研究报告' },
      'manual': { color: '#fa8c16', name: '操作手册' },
      'resume': { color: '#eb2f96', name: '个人简历' },
      'academic': { color: '#722ed1', name: '学术论文' },
      'business': { color: '#13c2c2', name: '商业文档' },
      'legal': { color: '#f5222d', name: '法律文件' },
    };
    return categoryMap[category || ''] || { color: '#8c8c8c', name: '其他文档' };
  };

  // 格式化相关度分数
  const formatRelevanceScore = (score?: number) => {
    if (!score) return 0;
    return Math.round(score * 100);
  };

  // 格式化日期
  const formatDate = (dateString?: string) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('zh-CN');
  };

  // 高亮关键词
  const highlightKeywords = (text: string, keywords: string[] = []) => {
    if (!keywords.length) return text;
    
    let highlightedText = text;
    keywords.forEach(keyword => {
      const regex = new RegExp(`(${keyword})`, 'gi');
      highlightedText = highlightedText.replace(
        regex,
        '<mark style="background-color: #fff3cd; padding: 1px 2px; border-radius: 2px;">$1</mark>'
      );
    });
    
    return highlightedText;
  };

  // 处理来源点击
  const handleSourceClick = (source: SourceItem) => {
    setSelectedSource(source);
    setModalVisible(true);
  };

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <>
      <div style={{ 
        marginTop: 12, 
        padding: 8, 
        background: 'rgba(24, 144, 255, 0.05)', 
        borderRadius: 6,
        border: '1px solid rgba(24, 144, 255, 0.1)',
        ...style 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
          <LinkOutlined style={{ fontSize: 12, color: '#1890ff', marginRight: 4 }} />
          <Text style={{ fontSize: 12, color: '#1890ff', fontWeight: 500 }}>
            参考来源 ({sources.length} 个文档片段)
          </Text>
        </div>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(auto-fill, minmax(${isMobile ? '120px' : '140px'}, 1fr))`,
          gap: getResponsiveSpacing(4, 6, 8)
        }}>
          {sources.map((source, index) => {
            const typeInfo = getDocumentTypeInfo(source.document_category);
            const relevanceScore = formatRelevanceScore(source.relevance_score || source.similarity_score);

            return (
              <Tooltip
                key={index}
                title={
                  <div style={{ maxWidth: isMobile ? 280 : 350 }}>
                    <div style={{ marginBottom: 8 }}>
                      <Text strong style={{ color: 'white', fontSize: getResponsiveFontSize(12, 13, 14) }}>
                        {source.filename || '未知文档'}
                      </Text>
                    </div>

                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <div>
                        <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: window.innerWidth < 768 ? 11 : 12 }}>
                          <PercentageOutlined style={{ marginRight: 4 }} />
                          相关度: {relevanceScore}%
                        </Text>
                      </div>

                      {source.document_category && (
                        <div>
                          <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: window.innerWidth < 768 ? 11 : 12 }}>
                            分类: {typeInfo.name}
                          </Text>
                        </div>
                      )}

                      {source.page_number && (
                        <div>
                          <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: window.innerWidth < 768 ? 11 : 12 }}>
                            页码: 第 {source.page_number} 页
                          </Text>
                        </div>
                      )}

                      {source.content_preview && (
                        <div style={{ marginTop: 8 }}>
                          <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 11 }}>
                            内容预览:
                          </Text>
                          <div style={{
                            marginTop: 4,
                            padding: 6,
                            background: 'rgba(0,0,0,0.2)',
                            borderRadius: 4,
                            fontSize: 10,
                            lineHeight: 1.4,
                            color: 'rgba(255,255,255,0.9)'
                          }}>
                            {source.content_preview.substring(0, window.innerWidth < 768 ? 120 : 200)}
                            {source.content_preview.length > (window.innerWidth < 768 ? 120 : 200) && '...'}
                          </div>
                        </div>
                      )}

                      <div style={{ marginTop: 8, textAlign: 'center' }}>
                        <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 10 }}>
                          点击查看完整内容
                        </Text>
                      </div>
                    </Space>
                  </div>
                }
                placement="top"
              >
                <Tag
                  icon={<FileTextOutlined />}
                  color={typeInfo.color}
                  style={{
                    cursor: 'pointer',
                    fontSize: window.innerWidth < 768 ? 10 : 11,
                    padding: window.innerWidth < 768 ? '1px 4px' : '2px 6px',
                    margin: 0,
                    borderRadius: 4,
                    transition: 'all 0.2s ease',
                    width: '100%',
                    textAlign: 'center',
                    display: 'block',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}
                  onClick={() => handleSourceClick(source)}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    width: '100%'
                  }}>
                    <span style={{
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      minWidth: 0
                    }}>
                      {(source.filename || '未知文档').length > (window.innerWidth < 768 ? 8 : 12)
                        ? `${(source.filename || '未知文档').substring(0, window.innerWidth < 768 ? 8 : 12)}...`
                        : (source.filename || '未知文档')
                      }
                    </span>
                    <span style={{
                      marginLeft: 4,
                      opacity: 0.8,
                      fontWeight: 'bold',
                      flexShrink: 0
                    }}>
                      {relevanceScore}%
                    </span>
                  </div>
                </Tag>
              </Tooltip>
            );
          })}
        </div>
        
        {sources.length > 3 && (
          <div style={{ marginTop: 6, textAlign: 'center' }}>
            <Text style={{ fontSize: 11, color: '#666' }}>
              基于 {sources.length} 个相关文档片段生成回答
            </Text>
          </div>
        )}
      </div>

      {/* 来源详情模态框 */}
      <Modal
        title={
          <Space>
            <FileTextOutlined />
            <span>{selectedSource?.filename || '文档详情'}</span>
          </Space>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={getResponsiveModalWidth('95%', 600, 700)}
        style={{ top: isMobile ? 10 : 20 }}
      >
        {selectedSource && (
          <div>
            {/* 文档信息卡片 */}
            <Card size="small" style={{ marginBottom: 16 }}>
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  flexDirection: window.innerWidth < 768 ? 'column' : 'row',
                  gap: window.innerWidth < 768 ? 8 : 0
                }}>
                  <Space direction={window.innerWidth < 768 ? 'vertical' : 'horizontal'} size={4}>
                    <Text strong style={{ fontSize: window.innerWidth < 768 ? 12 : 14 }}>相关度评分:</Text>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Progress
                        percent={formatRelevanceScore(selectedSource.relevance_score || selectedSource.similarity_score)}
                        size="small"
                        style={{ width: window.innerWidth < 768 ? 80 : 100 }}
                      />
                      <Text style={{ fontSize: window.innerWidth < 768 ? 12 : 14 }}>
                        {formatRelevanceScore(selectedSource.relevance_score || selectedSource.similarity_score)}%
                      </Text>
                    </div>
                  </Space>

                  {selectedSource.document_category && (
                    <Tag
                      color={getDocumentTypeInfo(selectedSource.document_category).color}
                      style={{ fontSize: window.innerWidth < 768 ? 11 : 12 }}
                    >
                      {getDocumentTypeInfo(selectedSource.document_category).name}
                    </Tag>
                  )}
                </div>
                
                <Space wrap>
                  {selectedSource.page_number && (
                    <Text type="secondary">
                      <FileTextOutlined style={{ marginRight: 4 }} />
                      第 {selectedSource.page_number} 页
                    </Text>
                  )}
                  
                  {selectedSource.chunk_index !== undefined && (
                    <Text type="secondary">
                      片段 #{selectedSource.chunk_index + 1}
                    </Text>
                  )}
                  
                  {selectedSource.created_at && (
                    <Text type="secondary">
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {formatDate(selectedSource.created_at)}
                    </Text>
                  )}
                </Space>
              </Space>
            </Card>

            <Divider orientation="left">引用内容</Divider>
            
            {/* 文档内容 */}
            <div style={{ 
              maxHeight: 400, 
              overflow: 'auto',
              padding: 16,
              background: '#fafafa',
              borderRadius: 6,
              border: '1px solid #e8e8e8'
            }}>
              <Paragraph style={{ 
                lineHeight: 1.8,
                fontSize: 14,
                margin: 0,
                whiteSpace: 'pre-wrap'
              }}>
                {selectedSource.content || selectedSource.content_preview || '暂无内容预览'}
              </Paragraph>
            </div>
            
            {selectedSource.content && selectedSource.content.length > 500 && (
              <div style={{ marginTop: 8, textAlign: 'center' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  * 显示部分内容，完整内容请查看原文档
                </Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </>
  );
};

export default SourceReference;

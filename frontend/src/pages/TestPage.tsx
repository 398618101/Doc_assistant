import React, { useState, useEffect } from 'react';
import { Card, Button, Typography, Space, Alert } from 'antd';
import { documentAPI } from '../services/api';

const { Title, Text } = Typography;

const TestPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const testCategoryStats = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      console.log('开始测试分类统计API...');
      const response = await documentAPI.getCategoryStats();
      console.log('API响应:', response);
      setResult(response);
    } catch (err: any) {
      console.error('API调用失败:', err);
      setError(err.message || '未知错误');
    } finally {
      setLoading(false);
    }
  };

  const testCategoryDocuments = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      console.log('开始测试分类文档API...');
      const response = await documentAPI.getDocumentsByCategory('tech-docs');
      console.log('API响应:', response);
      setResult(response);
    } catch (err: any) {
      console.error('API调用失败:', err);
      setError(err.message || '未知错误');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('TestPage组件已加载');
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <Title level={2}>前端API测试页面</Title>
      
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card title="API测试">
          <Space>
            <Button 
              type="primary" 
              onClick={testCategoryStats}
              loading={loading}
            >
              测试分类统计API
            </Button>
            <Button 
              onClick={testCategoryDocuments}
              loading={loading}
            >
              测试分类文档API
            </Button>
          </Space>
        </Card>

        {error && (
          <Alert
            message="错误"
            description={error}
            type="error"
            showIcon
          />
        )}

        {result && (
          <Card title="API响应结果">
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '10px', 
              borderRadius: '4px',
              overflow: 'auto',
              maxHeight: '400px'
            }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </Card>
        )}
      </Space>
    </div>
  );
};

export default TestPage;

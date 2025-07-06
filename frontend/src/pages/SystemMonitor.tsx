import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Badge,
  Typography,
  Space,
  Button,
  Alert,
  Descriptions,
  Progress,
  Tag,
  Spin,
  message,
} from 'antd';
import {
  DatabaseOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  ApiOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { systemAPI } from '../services/api';
import type { SystemStatus } from '../services/api';

const { Title, Text } = Typography;

const SystemMonitor: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<string>('');

  // 获取系统状态
  const fetchSystemStatus = async () => {
    setLoading(true);
    try {
      const status = await systemAPI.getSystemStatus();
      setSystemStatus(status);
      setLastUpdateTime(new Date().toLocaleString('zh-CN'));
    } catch (error) {
      message.error('获取系统状态失败');
      console.error('获取系统状态失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 健康检查
  const performHealthCheck = async () => {
    try {
      await systemAPI.healthCheck();
      message.success('系统健康检查通过');
      fetchSystemStatus();
    } catch (error) {
      message.error('系统健康检查失败');
      console.error('健康检查失败:', error);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
    // 设置定时刷新
    const interval = setInterval(fetchSystemStatus, 30000); // 30秒刷新一次
    return () => clearInterval(interval);
  }, []);

  if (!systemStatus) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text>正在加载系统状态...</Text>
        </div>
      </div>
    );
  }

  // 获取状态颜色和图标
  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'success':
        return <Badge status="success" text="正常" />;
      case 'warning':
        return <Badge status="warning" text="警告" />;
      case 'error':
      case 'failed':
        return <Badge status="error" text="错误" />;
      default:
        return <Badge status="default" text={status} />;
    }
  };

  // 计算向量化进度
  const getVectorizationProgress = () => {
    const { total_chunks } = systemStatus.vector_database;
    if (total_chunks === 0) return 0;
    // 这里可以根据实际需求计算进度
    return total_chunks > 0 ? 100 : 0;
  };

  return (
    <div>
      {/* 页面标题和操作 */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>系统监控</Title>
        <Space>
          <Text type="secondary">最后更新: {lastUpdateTime}</Text>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchSystemStatus}
            loading={loading}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={performHealthCheck}
          >
            健康检查
          </Button>
        </Space>
      </div>

      {/* 系统状态概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="向量数据库"
              value={systemStatus.vector_database.total_chunks}
              prefix={<DatabaseOutlined />}
              suffix="个文档块"
            />
            <div style={{ marginTop: 8 }}>
              {getStatusBadge(systemStatus.vector_database.status)}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Embedding服务"
              value={systemStatus.embedding_service.status === 'healthy' ? '在线' : '离线'}
              prefix={<CloudServerOutlined />}
            />
            <div style={{ marginTop: 8 }}>
              {getStatusBadge(systemStatus.embedding_service.status)}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="向量维度"
              value={systemStatus.embedding_dimension}
              prefix={<ThunderboltOutlined />}
              suffix="维"
            />
            <div style={{ marginTop: 8 }}>
              <Tag color="blue">高维向量</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="LM Studio"
              value={systemStatus.embedding_service.lm_studio_connected ? '已连接' : '未连接'}
              prefix={<RobotOutlined />}
            />
            <div style={{ marginTop: 8 }}>
              {systemStatus.embedding_service.lm_studio_connected ? (
                <Badge status="success" text="连接正常" />
              ) : (
                <Badge status="error" text="连接失败" />
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 详细状态信息 */}
      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <Card title="向量数据库状态" style={{ marginBottom: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="集合名称">
                {systemStatus.vector_database.collection_name}
              </Descriptions.Item>
              <Descriptions.Item label="文档块数量">
                {systemStatus.vector_database.total_chunks}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {getStatusBadge(systemStatus.vector_database.status)}
              </Descriptions.Item>
            </Descriptions>
            
            <div style={{ marginTop: 16 }}>
              <Text strong>向量化进度</Text>
              <Progress
                percent={getVectorizationProgress()}
                status={systemStatus.vector_database.total_chunks > 0 ? 'success' : 'normal'}
                style={{ marginTop: 8 }}
              />
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Embedding服务状态" style={{ marginBottom: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="服务提供者">
                <Tag color="blue">{systemStatus.embedding_service.provider.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型名称">
                {systemStatus.embedding_service.embedding_model}
              </Descriptions.Item>
              <Descriptions.Item label="计算设备">
                <Tag color={systemStatus.embedding_service.device.includes('GPU') ? 'green' : 'orange'}>
                  {systemStatus.embedding_service.device}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="LM Studio连接">
                {systemStatus.embedding_service.lm_studio_connected ? (
                  <Tag color="success">已连接</Tag>
                ) : (
                  <Tag color="error">未连接</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="模型可用性">
                {systemStatus.embedding_service.embedding_model_available ? (
                  <Tag color="success">可用</Tag>
                ) : (
                  <Tag color="error">不可用</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* 可用模型列表 */}
      <Card title="可用模型列表">
        <div style={{ marginBottom: 16 }}>
          <Text strong>当前使用模型: </Text>
          <Tag color="blue">{systemStatus.embedding_service.embedding_model}</Tag>
        </div>
        
        <div>
          <Text strong>所有可用模型:</Text>
          <div style={{ marginTop: 8 }}>
            {systemStatus.embedding_service.available_models.map((model, index) => (
              <Tag
                key={index}
                color={model === systemStatus.embedding_service.embedding_model ? 'blue' : 'default'}
                style={{ marginBottom: 4 }}
              >
                {model}
                {model === systemStatus.embedding_service.embedding_model && ' (当前)'}
              </Tag>
            ))}
          </div>
        </div>
      </Card>

      {/* 系统警告 */}
      {(!systemStatus.embedding_service.lm_studio_connected || 
        !systemStatus.embedding_service.embedding_model_available) && (
        <Alert
          message="系统警告"
          description="检测到部分服务异常，可能影响系统功能。请检查LM Studio连接状态和模型可用性。"
          type="warning"
          showIcon
          style={{ marginTop: 16 }}
          action={
            <Button size="small" onClick={performHealthCheck}>
              重新检查
            </Button>
          }
        />
      )}

      {/* 系统正常提示 */}
      {systemStatus.embedding_service.lm_studio_connected && 
       systemStatus.embedding_service.embedding_model_available && 
       systemStatus.vector_database.status === 'healthy' && (
        <Alert
          message="系统运行正常"
          description="所有服务状态良好，系统功能正常运行。"
          type="success"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}
    </div>
  );
};

export default SystemMonitor;

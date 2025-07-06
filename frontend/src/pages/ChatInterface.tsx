import React, { useState, useRef, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Avatar,
  List,
  Tag,
  Spin,
  Empty,
  Collapse,
  Tooltip,
  message,
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { chatAPI } from '../services/api';
import type { ChatMessage, ChatResponse } from '../services/api';
import SourceReference from '../components/SourceReference';
import MarkdownRenderer from '../components/MarkdownRenderer';

const { TextArea } = Input;
const { Text, Title, Paragraph } = Typography;
const { Panel } = Collapse;

interface ConversationMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: any[];
  responseTime?: number;
  retrievalContext?: any;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 发送消息
  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: ConversationMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const chatMessage: ChatMessage = {
        message: inputValue,
        response_mode: 'complete',
        enable_retrieval: true, // 始终启用智能检索
        conversation_id: conversationId || undefined,
      };

      const response: ChatResponse = await chatAPI.sendMessage(chatMessage);

      if (!conversationId) {
        setConversationId(response.conversation_id);
      }

      const assistantMessage: ConversationMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.message,
        timestamp: response.timestamp,
        sources: response.sources_used,
        responseTime: response.response_time,
        retrievalContext: response.retrieval_context,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      message.error('发送消息失败');
      console.error('发送消息失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 清空对话
  const handleClearChat = () => {
    setMessages([]);
    setConversationId('');
  };

  // 渲染消息
  const renderMessage = (msg: ConversationMessage) => {
    const isUser = msg.type === 'user';
    
    return (
      <div
        key={msg.id}
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: 16,
        }}
      >
        <div
          style={{
            maxWidth: '70%',
            display: 'flex',
            flexDirection: isUser ? 'row-reverse' : 'row',
            alignItems: 'flex-start',
            gap: 8,
          }}
        >
          <Avatar
            icon={isUser ? <UserOutlined /> : <RobotOutlined />}
            style={{
              backgroundColor: isUser ? '#1890ff' : '#52c41a',
              flexShrink: 0,
            }}
          />
          <div
            style={{
              backgroundColor: isUser ? '#1890ff' : '#f6f6f6',
              color: isUser ? 'white' : 'black',
              padding: '12px 16px',
              borderRadius: 12,
              maxWidth: '100%',
            }}
          >
            <div style={{ marginBottom: 4 }}>
              {isUser ? (
                <Text style={{ color: 'white' }}>
                  {msg.content}
                </Text>
              ) : (
                <MarkdownRenderer
                  content={msg.content}
                  style={{ color: 'inherit' }}
                />
              )}
            </div>
            
            <div style={{ fontSize: 12, opacity: 0.7, marginTop: 8 }}>
              <Space size={16}>
                <span>
                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                  {new Date(msg.timestamp).toLocaleTimeString('zh-CN')}
                </span>
                {msg.responseTime && (
                  <span>响应时间: {msg.responseTime.toFixed(2)}s</span>
                )}
              </Space>
            </div>

            {/* 显示检索来源 */}
            {!isUser && msg.sources && msg.sources.length > 0 && (
              <SourceReference sources={msg.sources} />
            )}

            {/* 显示检索详情 */}
            {!isUser && msg.retrievalContext && (
              <Collapse
                ghost
                size="small"
                style={{ marginTop: 8 }}
                items={[
                  {
                    key: '1',
                    label: (
                      <Text style={{ fontSize: 12, color: isUser ? 'white' : 'inherit' }}>
                        检索详情 ({msg.retrievalContext.total_chunks} 个文档块)
                      </Text>
                    ),
                    children: (
                      <div style={{ fontSize: 12 }}>
                        <p>检索时间: {msg.retrievalContext.retrieval_time?.toFixed(2)}s</p>
                        <p>上下文长度: {msg.retrievalContext.context_length} 字符</p>
                        {msg.retrievalContext.retrieved_chunks?.map((chunk: any, index: number) => (
                          <div key={index} style={{ marginBottom: 8, padding: 8, background: 'rgba(0,0,0,0.05)', borderRadius: 4 }}>
                            <Text style={{ fontSize: 11 }}>
                              相似度: {(chunk.similarity_score * 100).toFixed(1)}%
                            </Text>
                            <div style={{ marginTop: 4 }}>
                              <Text style={{ fontSize: 11 }}>
                                {chunk.text?.substring(0, 100)}...
                              </Text>
                            </div>
                          </div>
                        ))}
                      </div>
                    ),
                  },
                ]}
              />
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
      {/* 工具栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Text strong style={{ color: '#1890ff' }}>智能文档问答</Text>
            <Text type="secondary" style={{ marginLeft: 12 }}>
              基于您的文档库进行智能问答，自动检索相关内容
            </Text>
          </div>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={handleClearChat}
          >
            清空对话
          </Button>
        </div>
      </Card>

      {/* 消息列表 */}
      <Card
        style={{ flex: 1, marginBottom: 16, overflow: 'hidden' }}
        styles={{ body: { height: '100%', padding: 16, overflow: 'auto' } }}
      >
        {messages.length === 0 ? (
          <Empty
            description="开始与智能文档助理对话吧！"
            style={{ marginTop: '20%' }}
          />
        ) : (
          <div>
            {messages.map(renderMessage)}
            {loading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />
                  <div
                    style={{
                      backgroundColor: '#f6f6f6',
                      padding: '12px 16px',
                      borderRadius: 12,
                    }}
                  >
                    <Spin size="small" />
                    <Text style={{ marginLeft: 8 }}>正在思考中...</Text>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </Card>

      {/* 输入区域 */}
      <Card>
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="输入您的问题..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            disabled={loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSendMessage}
            loading={loading}
            disabled={!inputValue.trim()}
          >
            发送
          </Button>
        </Space.Compact>
        <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
          按 Enter 发送，Shift + Enter 换行
        </div>
      </Card>
    </div>
  );
};

export default ChatInterface;

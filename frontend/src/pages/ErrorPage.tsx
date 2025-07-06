import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Result, Button } from 'antd';

interface RouteError {
  statusText?: string;
  message?: string;
  status?: number;
}

const ErrorPage: React.FC = () => {
  // 使用更兼容的错误处理方式
  const error: RouteError = {
    status: 404,
    statusText: '页面未找到',
    message: '抱歉，您访问的页面不存在。'
  };
  const navigate = useNavigate();

  const getErrorInfo = () => {
    if (error?.status === 404) {
      return {
        status: '404' as const,
        title: '页面未找到',
        subTitle: '抱歉，您访问的页面不存在。',
      };
    }

    return {
      status: 'error' as const,
      title: '出现错误',
      subTitle: error?.statusText || error?.message || '发生了未知错误',
    };
  };

  const { status, title, subTitle } = getErrorInfo();

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5',
      }}
    >
      <Result
        status={status}
        title={title}
        subTitle={subTitle}
        extra={[
          <Button type="primary" key="home" onClick={() => navigate('/')}>
            返回首页
          </Button>,
          <Button key="back" onClick={() => navigate(-1)}>
            返回上页
          </Button>,
        ]}
      />
    </div>
  );
};

export default ErrorPage;

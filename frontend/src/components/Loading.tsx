import React from 'react';
import { Spin, Typography } from 'antd';

const { Text } = Typography;

interface LoadingProps {
  tip?: string;
  size?: 'small' | 'default' | 'large';
  style?: React.CSSProperties;
}

const Loading: React.FC<LoadingProps> = ({ 
  tip = '加载中...', 
  size = 'large',
  style = {}
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 50,
        ...style,
      }}
    >
      <Spin size={size} />
      <Text style={{ marginTop: 16, color: '#8c8c8c' }}>
        {tip}
      </Text>
    </div>
  );
};

export default Loading;

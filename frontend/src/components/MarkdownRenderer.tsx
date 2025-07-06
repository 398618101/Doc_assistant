import React from 'react';
import { Typography } from 'antd';

const { Text } = Typography;

interface MarkdownRendererProps {
  content: string;
  style?: React.CSSProperties;
}

/**
 * Markdown渲染组件
 * 
 * 当react-markdown依赖安装完成后，将使用完整的Markdown渲染
 * 目前提供基础的文本格式化支持
 */
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, style }) => {
  // 基础文本格式化函数
  const formatText = (text: string): React.ReactNode => {
    // 处理换行
    const lines = text.split('\n');
    const formattedLines: React.ReactNode[] = [];

    lines.forEach((line, lineIndex) => {
      if (line.trim() === '') {
        formattedLines.push(<br key={`br-${lineIndex}`} />);
        return;
      }

      // 处理标题
      if (line.startsWith('###')) {
        formattedLines.push(
          <h3 key={lineIndex} style={{ margin: '16px 0 8px 0', fontSize: '16px', fontWeight: 'bold' }}>
            {line.replace(/^###\s*/, '')}
          </h3>
        );
      } else if (line.startsWith('##')) {
        formattedLines.push(
          <h2 key={lineIndex} style={{ margin: '20px 0 12px 0', fontSize: '18px', fontWeight: 'bold' }}>
            {line.replace(/^##\s*/, '')}
          </h2>
        );
      } else if (line.startsWith('#')) {
        formattedLines.push(
          <h1 key={lineIndex} style={{ margin: '24px 0 16px 0', fontSize: '20px', fontWeight: 'bold' }}>
            {line.replace(/^#\s*/, '')}
          </h1>
        );
      }
      // 处理无序列表
      else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        formattedLines.push(
          <div key={lineIndex} style={{ margin: '4px 0', paddingLeft: '16px' }}>
            <span style={{ marginRight: '8px' }}>•</span>
            {formatInlineText(line.replace(/^\s*[-*]\s*/, ''))}
          </div>
        );
      }
      // 处理有序列表
      else if (/^\s*\d+\.\s/.test(line)) {
        const match = line.match(/^\s*(\d+)\.\s(.*)$/);
        if (match) {
          formattedLines.push(
            <div key={lineIndex} style={{ margin: '4px 0', paddingLeft: '16px' }}>
              <span style={{ marginRight: '8px' }}>{match[1]}.</span>
              {formatInlineText(match[2])}
            </div>
          );
        }
      }
      // 处理引用块
      else if (line.trim().startsWith('> ')) {
        formattedLines.push(
          <div 
            key={lineIndex} 
            style={{ 
              margin: '8px 0', 
              paddingLeft: '16px', 
              borderLeft: '4px solid #d9d9d9',
              backgroundColor: '#fafafa',
              padding: '8px 16px',
              fontStyle: 'italic'
            }}
          >
            {formatInlineText(line.replace(/^\s*>\s*/, ''))}
          </div>
        );
      }
      // 处理代码块
      else if (line.trim().startsWith('```')) {
        // 简单处理，实际应该处理多行代码块
        formattedLines.push(
          <div 
            key={lineIndex}
            style={{
              margin: '8px 0',
              padding: '12px',
              backgroundColor: '#f6f8fa',
              border: '1px solid #e1e4e8',
              borderRadius: '6px',
              fontFamily: 'Monaco, Consolas, "Courier New", monospace',
              fontSize: '14px'
            }}
          >
            {line.replace(/```/g, '')}
          </div>
        );
      }
      // 普通段落
      else {
        formattedLines.push(
          <p key={lineIndex} style={{ margin: '8px 0', lineHeight: '1.6' }}>
            {formatInlineText(line)}
          </p>
        );
      }
    });

    return formattedLines;
  };

  // 处理行内格式
  const formatInlineText = (text: string): React.ReactNode => {
    // 处理粗体 **text**
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // 处理斜体 *text*
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // 处理行内代码 `code`
    formatted = formatted.replace(/`(.*?)`/g, '<code style="background-color: #f6f8fa; padding: 2px 4px; border-radius: 3px; font-family: Monaco, Consolas, \'Courier New\', monospace; font-size: 85%;">$1</code>');
    
    // 处理链接 [text](url)
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #1890ff; text-decoration: none;">$1</a>');

    // 如果包含HTML标签，使用dangerouslySetInnerHTML
    if (formatted.includes('<')) {
      return <span dangerouslySetInnerHTML={{ __html: formatted }} />;
    }
    
    return formatted;
  };

  return (
    <div style={{ ...style }}>
      {formatText(content)}
    </div>
  );
};

export default MarkdownRenderer;

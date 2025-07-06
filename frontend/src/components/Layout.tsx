import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout as AntLayout,
  Menu,
  Typography,
  theme,
  Drawer,
  Button,
} from 'antd';
import {
  FileTextOutlined,
  MessageOutlined,
  DashboardOutlined,
  MenuOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  // 菜单项配置
  const menuItems: MenuProps['items'] = [
    {
      key: '/documents',
      icon: <FileTextOutlined />,
      label: '文档管理',
      onClick: () => {
        navigate('/documents');
        setMobileDrawerOpen(false);
      },
    },
    {
      key: '/categories',
      icon: <AppstoreOutlined />,
      label: '分类浏览',
      onClick: () => {
        navigate('/categories');
        setMobileDrawerOpen(false);
      },
    },
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: '智能对话',
      onClick: () => {
        navigate('/chat');
        setMobileDrawerOpen(false);
      },
    },
    {
      key: '/system',
      icon: <DashboardOutlined />,
      label: '系统监控',
      onClick: () => {
        navigate('/system');
        setMobileDrawerOpen(false);
      },
    },
  ];

  // 获取当前页面标题
  const getPageTitle = () => {
    const path = location.pathname;
    switch (path) {
      case '/documents':
        return '文档管理';
      case '/categories':
        return '分类浏览';
      case '/chat':
        return '智能对话';
      case '/system':
        return '系统监控';
      default:
        return '智能文档助理';
    }
  };

  // 侧边栏内容
  const siderContent = (
    <>
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
          {collapsed ? '文档AI' : '智能文档助理'}
        </Title>
      </div>
      <Menu
        theme="light"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        style={{ borderRight: 0 }}
      />
    </>
  );

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      {/* 桌面端侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        breakpoint="lg"
        collapsedWidth="80"
        onBreakpoint={(broken) => {
          if (broken) {
            setCollapsed(true);
          }
        }}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
        }}
        className="desktop-sider"
      >
        {siderContent}
      </Sider>

      {/* 移动端抽屉 */}
      <Drawer
        title="智能文档助理"
        placement="left"
        onClose={() => setMobileDrawerOpen(false)}
        open={mobileDrawerOpen}
        styles={{ body: { padding: 0 } }}
        className="mobile-drawer"
      >
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Drawer>

      <AntLayout style={{ marginLeft: collapsed ? 80 : 200 }}>
        <Header
          style={{
            padding: '0 16px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
            position: 'sticky',
            top: 0,
            zIndex: 99,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => {
                if (window.innerWidth <= 992) {
                  setMobileDrawerOpen(true);
                } else {
                  setCollapsed(!collapsed);
                }
              }}
              style={{ marginRight: 16 }}
            />
            <Title level={3} style={{ margin: 0 }}>
              {getPageTitle()}
            </Title>
          </div>
        </Header>

        <Content
          style={{
            margin: '16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </AntLayout>

      <style>{`
        @media (max-width: 992px) {
          .desktop-sider {
            display: none !important;
          }
          .ant-layout {
            margin-left: 0 !important;
          }
        }
        @media (min-width: 993px) {
          .mobile-drawer {
            display: none !important;
          }
        }
      `}</style>
    </AntLayout>
  );
};

export default Layout;

import { useState, useEffect } from 'react';

// 断点定义
export const BREAKPOINTS = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

// 屏幕尺寸类型
export type ScreenSize = keyof typeof BREAKPOINTS;

// 获取当前屏幕尺寸
export const getCurrentScreenSize = (): ScreenSize => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.xxl) return 'xxl';
  if (width >= BREAKPOINTS.xl) return 'xl';
  if (width >= BREAKPOINTS.lg) return 'lg';
  if (width >= BREAKPOINTS.md) return 'md';
  if (width >= BREAKPOINTS.sm) return 'sm';
  return 'xs';
};

// 检查是否为移动设备
export const isMobile = (): boolean => {
  return window.innerWidth < BREAKPOINTS.md;
};

// 检查是否为平板设备
export const isTablet = (): boolean => {
  return window.innerWidth >= BREAKPOINTS.md && window.innerWidth < BREAKPOINTS.lg;
};

// 检查是否为桌面设备
export const isDesktop = (): boolean => {
  return window.innerWidth >= BREAKPOINTS.lg;
};

// 响应式Hook
export const useResponsive = () => {
  const [screenSize, setScreenSize] = useState<ScreenSize>(getCurrentScreenSize());
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  const [windowHeight, setWindowHeight] = useState(window.innerHeight);

  useEffect(() => {
    const handleResize = () => {
      const newWidth = window.innerWidth;
      const newHeight = window.innerHeight;
      
      setWindowWidth(newWidth);
      setWindowHeight(newHeight);
      setScreenSize(getCurrentScreenSize());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    screenSize,
    windowWidth,
    windowHeight,
    isMobile: windowWidth < BREAKPOINTS.md,
    isTablet: windowWidth >= BREAKPOINTS.md && windowWidth < BREAKPOINTS.lg,
    isDesktop: windowWidth >= BREAKPOINTS.lg,
    isSmallScreen: windowWidth < BREAKPOINTS.lg,
    isLargeScreen: windowWidth >= BREAKPOINTS.xl,
  };
};

// 响应式样式工具
export const getResponsiveStyle = (
  mobileStyle: React.CSSProperties,
  tabletStyle?: React.CSSProperties,
  desktopStyle?: React.CSSProperties
): React.CSSProperties => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg && desktopStyle) {
    return { ...mobileStyle, ...desktopStyle };
  }
  
  if (width >= BREAKPOINTS.md && tabletStyle) {
    return { ...mobileStyle, ...tabletStyle };
  }
  
  return mobileStyle;
};

// 响应式值工具
export const getResponsiveValue = <T>(
  mobileValue: T,
  tabletValue?: T,
  desktopValue?: T
): T => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg && desktopValue !== undefined) {
    return desktopValue;
  }
  
  if (width >= BREAKPOINTS.md && tabletValue !== undefined) {
    return tabletValue;
  }
  
  return mobileValue;
};

// 响应式网格列数
export const getResponsiveColumns = (
  xs: number,
  sm?: number,
  md?: number,
  lg?: number,
  xl?: number,
  xxl?: number
): number => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.xxl && xxl !== undefined) return xxl;
  if (width >= BREAKPOINTS.xl && xl !== undefined) return xl;
  if (width >= BREAKPOINTS.lg && lg !== undefined) return lg;
  if (width >= BREAKPOINTS.md && md !== undefined) return md;
  if (width >= BREAKPOINTS.sm && sm !== undefined) return sm;
  return xs;
};

// 响应式间距
export const getResponsiveSpacing = (
  mobile: number | string,
  tablet?: number | string,
  desktop?: number | string
): number | string => {
  return getResponsiveValue(mobile, tablet, desktop);
};

// 响应式字体大小
export const getResponsiveFontSize = (
  mobile: number,
  tablet?: number,
  desktop?: number
): number => {
  return getResponsiveValue(mobile, tablet, desktop);
};

// 响应式模态框宽度
export const getResponsiveModalWidth = (
  mobilePercent: string = '95%',
  tabletWidth: number = 600,
  desktopWidth: number = 800
): string | number => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return desktopWidth;
  if (width >= BREAKPOINTS.md) return tabletWidth;
  return mobilePercent;
};

// 响应式卡片间距
export const getResponsiveCardSpacing = (): [number, number] => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return [24, 24];
  if (width >= BREAKPOINTS.md) return [16, 16];
  return [12, 12];
};

// 响应式表格滚动
export const getResponsiveTableScroll = (): { x?: number | string; y?: number | string } => {
  const width = window.innerWidth;
  
  if (width < BREAKPOINTS.md) {
    return { x: 800 };
  }
  
  return {};
};

// 响应式工具栏布局
export const getResponsiveToolbarLayout = (): 'horizontal' | 'vertical' => {
  return window.innerWidth < BREAKPOINTS.md ? 'vertical' : 'horizontal';
};

// 响应式搜索框宽度
export const getResponsiveSearchWidth = (): string => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return '400px';
  if (width >= BREAKPOINTS.md) return '300px';
  return '100%';
};

// 响应式侧边栏宽度
export const getResponsiveSiderWidth = (): number => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.xl) return 280;
  if (width >= BREAKPOINTS.lg) return 240;
  return 200;
};

// 响应式内容区域内边距
export const getResponsiveContentPadding = (): string => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return '24px';
  if (width >= BREAKPOINTS.md) return '16px';
  return '12px';
};

// 响应式按钮尺寸
export const getResponsiveButtonSize = (): 'small' | 'middle' | 'large' => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return 'middle';
  if (width >= BREAKPOINTS.md) return 'middle';
  return 'small';
};

// 响应式标签尺寸
export const getResponsiveTagSize = (): 'small' | 'default' => {
  return window.innerWidth < BREAKPOINTS.md ? 'small' : 'default';
};

// 响应式头像尺寸
export const getResponsiveAvatarSize = (): number => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return 40;
  if (width >= BREAKPOINTS.md) return 36;
  return 32;
};

// 响应式图标尺寸
export const getResponsiveIconSize = (): number => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return 16;
  if (width >= BREAKPOINTS.md) return 14;
  return 12;
};

// 响应式行高
export const getResponsiveLineHeight = (): number => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.lg) return 1.6;
  if (width >= BREAKPOINTS.md) return 1.5;
  return 1.4;
};

// 响应式最大宽度
export const getResponsiveMaxWidth = (): string => {
  const width = window.innerWidth;
  
  if (width >= BREAKPOINTS.xxl) return '1400px';
  if (width >= BREAKPOINTS.xl) return '1200px';
  if (width >= BREAKPOINTS.lg) return '992px';
  return '100%';
};

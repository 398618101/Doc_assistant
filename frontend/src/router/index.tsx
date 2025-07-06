import { createBrowserRouter, Navigate } from 'react-router-dom';
import Layout from '../components/Layout';
import DocumentManager from '../pages/DocumentManager';
import CategoryBrowser from '../pages/CategoryBrowser';
import ChatInterface from '../pages/ChatInterface';
import SystemMonitor from '../pages/SystemMonitor';
import TestPage from '../pages/TestPage';
import ErrorPage from '../pages/ErrorPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    errorElement: <ErrorPage />,
    children: [
      {
        index: true,
        element: <Navigate to="/documents" replace />,
      },
      {
        path: 'documents',
        element: <DocumentManager />,
      },
      {
        path: 'categories',
        element: <CategoryBrowser />,
      },
      {
        path: 'chat',
        element: <ChatInterface />,
      },
      {
        path: 'system',
        element: <SystemMonitor />,
      },
      {
        path: 'test',
        element: <TestPage />,
      },
    ],
  },
]);

export default router;

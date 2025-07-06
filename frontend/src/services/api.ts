import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';

// API基础配置
const API_BASE_URL = 'http://localhost:8000';

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API请求: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`API响应: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API响应错误:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// 文档相关接口
export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number;
  file_hash: string;
  document_type: string;
  mime_type: string;
  status: 'uploading' | 'processing' | 'processed' | 'error';
  content?: string;
  content_preview?: string;
  metadata: {
    title?: string;
    author?: string;
    word_count?: number;
    page_count?: number;
    tags: string[];
    [key: string]: any;
  };
  is_vectorized: boolean;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  processed_at?: string;
  error_message?: string;
  // 新增分类相关字段
  category?: string;
  subcategory?: string;
  auto_tags?: string; // JSON字符串
  classification_confidence?: number;
  classification_method?: string;
  summary?: string;
}

export interface DocumentListResponse {
  success: boolean;
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UploadResponse {
  success: boolean;
  document_id: string;
  filename: string;
  message: string;
}

// RAG聊天相关接口
export interface ChatMessage {
  message: string;
  response_mode?: 'simple' | 'complete';
  enable_retrieval?: boolean;
  max_retrieved_chunks?: number;
  conversation_id?: string;
}

export interface ChatResponse {
  success: boolean;
  message: string;
  conversation_id: string;
  response_time: number;
  retrieval_context: {
    query: string;
    retrieved_chunks: any[];
    total_chunks: number;
    retrieval_time: number;
    context_length: number;
    sources: any[];
  };
  sources_used: any[];
  tokens_used?: number;
  finish_reason: string;
  timestamp: string;
  model_used: string;
  error_message?: string;
}

// 系统状态相关接口
export interface SystemStatus {
  success: boolean;
  vector_database: {
    total_chunks: number;
    collection_name: string;
    status: string;
  };
  embedding_service: {
    status: string;
    provider: string;
    lm_studio_connected: boolean;
    embedding_model_available: boolean;
    available_models: string[];
    embedding_model: string;
    device: string;
  };
  embedding_dimension: number;
}

// API方法
export const documentAPI = {
  // 获取文档列表
  getDocuments: (page = 1, pageSize = 20): Promise<DocumentListResponse> =>
    apiClient.get(`/api/documents/?page=${page}&page_size=${pageSize}`).then(res => res.data),

  // 上传文档
  uploadDocument: (file: File, tags: string[] = []): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tags', JSON.stringify(tags));
    
    return apiClient.post('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then(res => res.data);
  },

  // 删除文档
  deleteDocument: (documentId: string): Promise<{ success: boolean; message: string }> =>
    apiClient.delete(`/api/documents/${documentId}`).then(res => res.data),

  // 获取文档详情
  getDocument: (documentId: string): Promise<{ success: boolean; document: Document }> =>
    apiClient.get(`/api/documents/${documentId}`).then(res => res.data),

  // 向量化文档
  vectorizeDocument: (documentId: string, forceReprocess = false): Promise<any> =>
    apiClient.post('/api/vectorization/vectorize', {
      document_id: documentId,
      chunk_size: 500,
      chunk_overlap: 100,
      force_reprocess: forceReprocess,
    }).then(res => res.data),

  // 获取分类统计
  getCategoryStats: (): Promise<{
    success: boolean;
    category_stats: Array<{
      category: string;
      count: number;
      total_size: number;
      latest_update: string;
    }>;
    total_documents: number;
  }> =>
    apiClient.get('/api/documents/categories/stats').then(res => res.data),

  // 根据分类获取文档列表
  getDocumentsByCategory: (
    category: string,
    page = 1,
    pageSize = 20
  ): Promise<{
    success: boolean;
    documents: Document[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
    category: string;
  }> =>
    apiClient.get(`/api/documents/categories/${category}?page=${page}&page_size=${pageSize}`).then(res => res.data),

  // 重新分类所有文档
  reclassifyAllDocuments: (): Promise<{
    success: boolean;
    message: string;
    processed_count: number;
    failed_count: number;
    total_documents: number;
  }> =>
    apiClient.post('/api/documents/reclassify-all').then(res => res.data),

  // 重新分类单个文档
  reclassifyDocument: (documentId: string): Promise<{
    success: boolean;
    message: string;
    document_id: string;
    old_category: string;
    new_category: string;
    confidence: number;
  }> =>
    apiClient.post(`/api/documents/${documentId}/reclassify`).then(res => res.data),
};

export const chatAPI = {
  // 发送聊天消息
  sendMessage: (message: ChatMessage): Promise<ChatResponse> =>
    apiClient.post('/api/rag/chat', message).then(res => res.data),

  // 获取对话历史（如果后端支持）
  getConversationHistory: (conversationId: string): Promise<any> =>
    apiClient.get(`/api/rag/conversations/${conversationId}`).then(res => res.data),
};

export const systemAPI = {
  // 获取系统状态
  getSystemStatus: (): Promise<SystemStatus> =>
    apiClient.get('/api/vectorization/stats').then(res => res.data),

  // 健康检查
  healthCheck: (): Promise<{ status: string; timestamp: string }> =>
    apiClient.get('/health').then(res => res.data),
};

export default apiClient;

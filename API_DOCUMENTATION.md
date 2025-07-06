# 智能文档助理系统 - API文档

## 1. API概览

### 1.1 基础信息
- **基础URL**: `http://localhost:8000`
- **API版本**: v1.0.0
- **认证方式**: 无需认证 (本地部署)
- **数据格式**: JSON
- **字符编码**: UTF-8

### 1.2 响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2025-07-05T10:30:00Z"
}
```

### 1.3 错误响应
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": {}
  },
  "timestamp": "2025-07-05T10:30:00Z"
}
```

## 2. 文档管理API

### 2.1 上传文档
```http
POST /api/documents/upload
Content-Type: multipart/form-data

file: [文件数据]
category: "技术文档" (可选)
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "document_id": "uuid-string",
    "original_filename": "example.pdf",
    "file_size": 1024000,
    "document_type": "pdf",
    "category": "技术文档",
    "status": "processing",
    "created_at": "2025-07-05T10:30:00Z"
  }
}
```

### 2.2 获取文档列表
```http
GET /api/documents?page=1&size=20&category=技术文档&search=关键词
```

**查询参数**:
- `page`: 页码 (默认: 1)
- `size`: 每页数量 (默认: 20, 最大: 100)
- `category`: 分类过滤 (可选)
- `search`: 搜索关键词 (可选)

**响应示例**:
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "id": "uuid-string",
        "original_filename": "example.pdf",
        "category": "技术文档",
        "file_size": 1024000,
        "status": "completed",
        "created_at": "2025-07-05T10:30:00Z",
        "metadata": {
          "title": "文档标题",
          "author": "作者",
          "page_count": 10
        }
      }
    ],
    "total": 100,
    "page": 1,
    "size": 20,
    "total_pages": 5
  }
}
```

### 2.3 获取文档详情
```http
GET /api/documents/{document_id}
```

### 2.4 删除文档
```http
DELETE /api/documents/{document_id}
```

### 2.5 更新文档分类
```http
PUT /api/documents/{document_id}/category
Content-Type: application/json

{
  "category": "新分类",
  "subcategory": "子分类"
}
```

## 3. RAG聊天API

### 3.1 发送聊天消息
```http
POST /api/rag/chat
Content-Type: application/json

{
  "message": "请介绍人工智能在水务行业的应用",
  "conversation_id": "uuid-string",
  "retrieval_config": {
    "top_k": 5,
    "similarity_threshold": 0.7,
    "category_filter": ["技术文档"]
  }
}
```

**请求参数**:
- `message`: 用户消息 (必需)
- `conversation_id`: 对话ID (可选，新对话时自动生成)
- `retrieval_config`: 检索配置 (可选)

**响应示例**:
```json
{
  "success": true,
  "data": {
    "response": "# 人工智能在水务行业的应用\n\n## 技术方案\n...",
    "conversation_id": "uuid-string",
    "message_id": "uuid-string",
    "sources_used": [
      {
        "document_id": "uuid-string",
        "filename": "水务加人工智能专刊.pdf",
        "relevance_score": 0.85,
        "chunk_content": "相关文档片段...",
        "page_number": 5
      }
    ],
    "retrieval_stats": {
      "total_chunks_searched": 1000,
      "relevant_chunks_found": 5,
      "search_time_ms": 150,
      "generation_time_ms": 8500
    }
  }
}
```

### 3.2 获取对话历史
```http
GET /api/rag/conversations/{conversation_id}/messages?limit=50
```

### 3.3 获取对话列表
```http
GET /api/rag/conversations?page=1&size=20
```

### 3.4 删除对话
```http
DELETE /api/rag/conversations/{conversation_id}
```

## 4. 检索API

### 4.1 文档检索
```http
POST /api/retrieval/search
Content-Type: application/json

{
  "query": "人工智能应用",
  "top_k": 10,
  "similarity_threshold": 0.6,
  "filters": {
    "category": ["技术文档", "研究报告"],
    "document_type": ["pdf", "docx"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2025-12-31"
    }
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "document_id": "uuid-string",
        "chunk_id": "uuid-string",
        "content": "相关文档内容片段...",
        "similarity_score": 0.85,
        "document_info": {
          "filename": "example.pdf",
          "category": "技术文档",
          "page_number": 5
        }
      }
    ],
    "total_results": 25,
    "search_time_ms": 120
  }
}
```

### 4.2 相似文档推荐
```http
GET /api/retrieval/similar/{document_id}?top_k=5
```

## 5. 向量化API

### 5.1 文档向量化
```http
POST /api/vectorization/process/{document_id}
```

### 5.2 获取向量化状态
```http
GET /api/vectorization/status/{document_id}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "document_id": "uuid-string",
    "status": "completed",
    "progress": 100,
    "chunks_processed": 45,
    "total_chunks": 45,
    "processing_time_ms": 15000,
    "error_message": null
  }
}
```

### 5.3 批量向量化
```http
POST /api/vectorization/batch
Content-Type: application/json

{
  "document_ids": ["uuid1", "uuid2", "uuid3"],
  "force_reprocess": false
}
```

## 6. 系统监控API

### 6.1 系统健康检查
```http
GET /api/health
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-07-05T10:30:00Z",
    "services": {
      "database": "healthy",
      "vector_db": "healthy",
      "llm_service": "healthy",
      "embedding_service": "healthy"
    },
    "system_info": {
      "cpu_usage": 25.5,
      "memory_usage": 68.2,
      "disk_usage": 45.8,
      "uptime_seconds": 86400
    }
  }
}
```

### 6.2 系统统计
```http
GET /api/stats
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "documents": {
      "total_count": 150,
      "by_category": {
        "技术文档": 45,
        "研究报告": 30,
        "操作手册": 25
      },
      "by_type": {
        "pdf": 80,
        "docx": 40,
        "txt": 30
      }
    },
    "conversations": {
      "total_count": 25,
      "total_messages": 150,
      "avg_messages_per_conversation": 6
    },
    "performance": {
      "avg_search_time_ms": 180,
      "avg_generation_time_ms": 7500,
      "total_searches": 500
    }
  }
}
```

## 7. 错误代码

### 7.1 通用错误代码
- `VALIDATION_ERROR`: 参数验证失败
- `NOT_FOUND`: 资源不存在
- `INTERNAL_ERROR`: 服务器内部错误
- `RATE_LIMIT_EXCEEDED`: 请求频率超限

### 7.2 文档相关错误
- `FILE_TOO_LARGE`: 文件大小超限
- `UNSUPPORTED_FORMAT`: 不支持的文件格式
- `PROCESSING_FAILED`: 文档处理失败
- `DOCUMENT_NOT_FOUND`: 文档不存在

### 7.3 RAG相关错误
- `LLM_SERVICE_UNAVAILABLE`: LLM服务不可用
- `EMBEDDING_FAILED`: 向量化失败
- `RETRIEVAL_FAILED`: 检索失败
- `GENERATION_TIMEOUT`: 生成超时

## 8. 使用示例

### 8.1 完整工作流示例 (Python)
```python
import requests
import json

# 1. 上传文档
def upload_document(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            'http://localhost:8000/api/documents/upload',
            files=files
        )
    return response.json()

# 2. 等待处理完成
def wait_for_processing(document_id):
    while True:
        response = requests.get(
            f'http://localhost:8000/api/vectorization/status/{document_id}'
        )
        status = response.json()['data']['status']
        if status == 'completed':
            break
        time.sleep(2)

# 3. 进行RAG聊天
def chat_with_rag(message, conversation_id=None):
    data = {
        'message': message,
        'conversation_id': conversation_id
    }
    response = requests.post(
        'http://localhost:8000/api/rag/chat',
        json=data
    )
    return response.json()

# 使用示例
doc_result = upload_document('example.pdf')
document_id = doc_result['data']['document_id']

wait_for_processing(document_id)

chat_result = chat_with_rag('请总结这个文档的主要内容')
print(chat_result['data']['response'])
```

### 8.2 JavaScript/TypeScript示例
```typescript
// API客户端类
class DocumentAssistantAPI {
  private baseURL = 'http://localhost:8000';

  async uploadDocument(file: File, category?: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (category) formData.append('category', category);

    const response = await fetch(`${this.baseURL}/api/documents/upload`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  }

  async chatWithRAG(message: string, conversationId?: string): Promise<any> {
    const response = await fetch(`${this.baseURL}/api/rag/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId
      })
    });
    return response.json();
  }

  async getDocuments(page = 1, size = 20): Promise<any> {
    const response = await fetch(
      `${this.baseURL}/api/documents?page=${page}&size=${size}`
    );
    return response.json();
  }
}

// 使用示例
const api = new DocumentAssistantAPI();

// 上传文档
const fileInput = document.getElementById('file') as HTMLInputElement;
const file = fileInput.files[0];
const uploadResult = await api.uploadDocument(file, '技术文档');

// RAG聊天
const chatResult = await api.chatWithRAG('请介绍这个文档的主要内容');
console.log(chatResult.data.response);
```

---

**API版本**: v1.0.0  
**最后更新**: 2025年7月5日  
**维护团队**: AI开发团队

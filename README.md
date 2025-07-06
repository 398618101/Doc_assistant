# 智能文档助理系统 (Intelligent Document Assistant System)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![React](https://img.shields.io/badge/React-18.2+-61DAFB.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-0.9+-FF6B35.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**基于RAG技术的本地化智能文档管理和问答系统**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [技术架构](#-技术架构) • [部署指南](#-部署指南) • [API文档](#-api文档)

</div>

## 📖 项目简介

智能文档助理系统是一个基于RAG (Retrieval-Augmented Generation) 技术的本地化文档管理和智能问答平台。系统支持多种文档格式的上传、自动分类、语义检索和智能对话，完全本地部署，保护数据隐私。

### 🎯 核心价值
- 🔒 **隐私保护**: 完全本地化部署，数据不离开本地环境
- 🤖 **智能问答**: 基于文档内容的准确问答和知识检索
- 📚 **文档管理**: 自动分类、标签生成、语义检索
- ⚡ **高性能**: GPU加速推理，毫秒级检索响应

## ✨ 功能特性

### 📄 多格式文档支持
- **文档格式**: PDF、DOCX、DOC、TXT、Markdown
- **图片识别**: PNG、JPG、JPEG (OCR文字识别)（开发中）
- **文件大小**: 支持最大100MB文档上传
- **批量处理**: 支持多文档同时上传和处理

### 🤖 RAG智能聊天
- **检索增强生成**: 基于文档内容的上下文感知对话
- **文档引用**: 自动显示答案来源和相关性评分
- **Markdown渲染**: 支持格式化回答 (标题、列表、代码块等)
- **对话历史**: 自动保存和管理对话记录

### 🏷️ 智能文档分类
- **自动分类**: AI驱动的文档内容分析和分类
- **预定义类别**: 技术文档、研究报告、操作手册等8大类
- **标签生成**: 自动提取关键词和生成标签
- **手动调整**: 支持用户手动重分类和标签编辑

### 🔍 语义检索系统
- **向量数据库**: ChromaDB高性能向量存储
- **混合检索**: 语义相似度 + 关键词匹配
- **智能排序**: 多因子综合排序算法
- **实时索引**: 文档上传后自动向量化和索引

### 🖥️ 现代化界面
- **响应式设计**: 支持桌面端和移动端
- **Ant Design**: 企业级UI组件库
- **实时反馈**: 上传进度、处理状态实时显示
- **主题支持**: 明暗主题切换

## 🏗️ 技术架构

### 前端技术栈
- **框架**: React 18.2+ + TypeScript 5.0+
- **构建工具**: Vite 4.4+ (快速构建和热重载)
- **UI库**: Ant Design 5.0+ (企业级组件)
- **路由**: React Router DOM 6.0+
- **HTTP客户端**: Axios 1.0+

### 后端技术栈
- **Web框架**: FastAPI 0.100+ (高性能异步API)
- **AI框架**: LlamaIndex 0.9+ (RAG框架)
- **数据库**: SQLite (关系数据) + ChromaDB (向量数据)
- **文档处理**: PyPDF2, python-docx, pdfplumber
- **OCR引擎**: OpenCV + Transformers + PyTorch

### AI模型集成
- **主要LLM**: LM Studio (qwen2.5-14b-instruct)
- **备用LLM**: Ollama (qwen2.5vl:7b)
- **嵌入模型**: text-embedding-qwen3-embedding-8b
- **GPU加速**: CUDA支持，提升推理性能

### 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   后端API       │    │   AI服务层      │
│  React + TS     │◄──►│  FastAPI        │◄──►│  LM Studio      │
│  Ant Design     │    │  Python 3.11+   │    │  Ollama         │
│  Vite构建       │    │  异步处理       │    │  qwen2.5-14b    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │   数据存储层    │              │
         │              │  SQLite + JSON  │              │
         │              │  ChromaDB向量库 │              │
         │              │  文件系统存储   │              │
         └──────────────┴─────────────────┴──────────────┘
```

## 🚀 快速开始

### 环境要求
- **操作系统**: Linux/Windows/macOS
- **Python**: 3.11+ (推荐3.11.5)
- **Node.js**: 18.0+ (推荐18.17.0)
- **内存**: 8GB+ (推荐16GB+)
- **存储**: 10GB+ 可用空间
- **GPU**: NVIDIA GPU (可选，用于加速)

### 安装步骤

#### 1. 克隆项目
```bash
git clone <repository-url>
cd intelligent-doc-assistant
```

#### 2. 后端环境配置
```bash
# 创建Python虚拟环境
python3.11 -m venv llamaindex
source llamaindex/bin/activate  # Linux/macOS
# llamaindex\Scripts\activate  # Windows

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 创建必要目录
mkdir -p ../uploads ../vector_db ../logs
```

#### 3. 前端环境配置
```bash
cd frontend
npm install
```

#### 4. AI模型配置

**LM Studio配置**:
1. 下载并安装 [LM Studio](https://lmstudio.ai/)
2. 下载 qwen2.5-14b-instruct 模型（或者你喜欢的模型）
3. 启动本地服务器 (默认端口1234)
4. 修改 `backend/app/core/config.py` 中的 `LM_STUDIO_BASE_URL`

**Ollama配置** (可选):
```bash
# 安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull qwen2.5vl:7b
ollama serve
```

### 启动系统

#### 启动后端服务
```bash
cd backend
source ../llamaindex/bin/activate
python main.py
```
后端服务将在 http://localhost:8000 启动

#### 启动前端服务
```bash
cd frontend
npm run dev
```
前端服务将在 http://localhost:5173 启动

### 访问系统
打开浏览器访问: http://localhost:5173

## 📁 项目结构

```
intelligent-doc-assistant/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API路由层
│   │   │   ├── documents.py   # 文档管理API
│   │   │   ├── rag.py         # RAG聊天API
│   │   │   └── retrieval.py   # 检索API
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 应用配置
│   │   │   └── llm_factory.py # LLM工厂类
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务服务层
│   │   │   ├── rag_service.py          # RAG服务
│   │   │   ├── document_processor.py  # 文档处理
│   │   │   ├── vector_storage.py      # 向量存储
│   │   │   └── document_classifier.py # 文档分类
│   │   └── utils/             # 工具函数
│   ├── main.py                # FastAPI应用入口
│   └── requirements.txt       # Python依赖
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # 通用组件
│   │   │   ├── MarkdownRenderer.tsx    # Markdown渲染
│   │   │   └── SourceReference.tsx     # 来源引用
│   │   ├── pages/             # 页面组件
│   │   │   ├── DocumentManager.tsx     # 文档管理
│   │   │   ├── ChatInterface.tsx       # 聊天界面
│   │   │   └── CategoryBrowser.tsx     # 分类浏览
│   │   ├── services/          # API服务
│   │   └── router/            # 路由配置
│   ├── package.json           # 依赖管理
│   └── vite.config.ts         # Vite配置
├── uploads/                    # 上传文件存储
├── vector_db/                  # ChromaDB向量数据库
├── documents.db               # SQLite数据库
└── docs/                      # 项目文档
    ├── PROJECT_TECHNICAL_SUMMARY.md  # 技术总结
    ├── API_DOCUMENTATION.md          # API文档
    ├── USER_GUIDE.md                 # 用户指南
    └── DEPLOYMENT_GUIDE.md           # 部署指南
```

## 📖 使用说明

### 文档上传流程
1. **进入文档管理页面**
   - 点击顶部导航栏的 **"文档管理"**
   - 进入文档管理界面

2. **上传文档**
   ```
   支持格式: PDF, DOCX, DOC, TXT, MD, PNG, JPG, JPEG
   文件大小: 最大100MB
   上传方式: 拖拽上传 或 点击选择文件
   ```

3. **自动处理流程**
   ```
   文档上传 → 格式检测 → 内容提取 → OCR识别 →
   智能分类 → 文本分块 → 向量化 → 索引存储
   ```

4. **查看处理结果**
   - 实时显示处理进度
   - 查看文档元数据和分类结果
   - 确认向量化完成状态

### RAG智能聊天使用
1. **开始对话**
   - 点击 **"RAG聊天"** 进入聊天界面
   - 系统自动创建新对话或继续历史对话

2. **提问技巧**
   ```
   ✅ 具体明确: "请介绍人工智能在水务行业的具体应用案例"
   ✅ 指定格式: "请用列表形式总结文档的主要观点"
   ✅ 限定范围: "根据技术文档，说明系统的架构设计"
   ❌ 模糊问题: "介绍一下AI"
   ```

3. **查看回答**
   - 支持Markdown格式渲染 (标题、列表、代码块、表格)
   - 自动显示文档引用来源
   - 查看相关性评分和页码信息
   - 点击引用可跳转到原文档

4. **对话管理**
   - 自动保存对话历史
   - 支持多个独立对话
   - 可以删除或重命名对话

### 文档分类和检索
1. **自动分类系统**
   ```
   📚 技术文档    📊 研究报告    📖 操作手册    📄 商业文档
   🎓 学术论文    ⚖️ 法律文件    👤 个人简历    📁 其他文档
   ```

2. **分类浏览**
   - 点击 **"分类浏览"** 查看文档分类统计
   - 点击分类名称查看该分类下的所有文档
   - 支持树形结构浏览 (主分类 → 子分类)

3. **高级搜索**
   - 关键词搜索: 支持中英文全文检索
   - 语义搜索: 基于向量相似度的智能匹配
   - 过滤条件: 按分类、格式、时间范围筛选
   - 排序选项: 按相关性、时间、大小排序

### 系统监控和管理
1. **健康状态检查**
   - 实时显示系统运行状态
   - 监控CPU、内存、磁盘使用情况
   - 检查AI服务连接状态

2. **性能统计**
   - 文档处理统计 (总数、分类分布、处理状态)
   - 聊天使用统计 (对话数、消息数、平均响应时间)
   - 系统性能指标 (检索速度、生成速度)

## 🐳 部署指南

### Docker部署 (推荐)

#### 1. 使用docker-compose
```bash
# 克隆项目
git clone https://github.com/398618101/Doc_assistant
cd intelligent-doc-assistant

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 2. 访问服务
- 前端: http://localhost:5173
- 后端API: http://localhost:8000

### 生产环境部署
详细的生产环境部署指南请参考: [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

包含以下内容:
- Nginx反向代理配置
- SSL证书配置
- 系统服务配置
- 监控和日志配置
- 备份和恢复策略

## 📚 API文档

### 主要API端点

#### 文档管理
- `POST /api/documents/upload` - 上传文档
- `GET /api/documents` - 获取文档列表
- `DELETE /api/documents/{id}` - 删除文档

#### RAG聊天
- `POST /api/rag/chat` - 发送聊天消息
- `GET /api/rag/conversations` - 获取对话列表

#### 检索服务
- `POST /api/retrieval/search` - 文档检索
- `GET /api/retrieval/similar/{id}` - 相似文档推荐

### 完整API文档
详细的API文档请参考: [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

## 🤝 贡献指南

### 开发环境设置
1. Fork 项目到你的GitHub账户
2. 克隆你的Fork到本地
3. 按照 [快速开始](#-快速开始) 设置开发环境
4. 创建新的功能分支: `git checkout -b feature/your-feature`

### 代码规范
- **Python**: 遵循PEP 8规范，使用black格式化
- **TypeScript**: 遵循ESLint规则，使用Prettier格式化
- **提交信息**: 使用约定式提交格式

### 提交流程
1. 确保所有测试通过
2. 提交代码: `git commit -m "feat: add new feature"`
3. 推送到你的Fork: `git push origin feature/your-feature`
4. 创建Pull Request

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 📞 技术支持

- **项目文档**: [docs/](docs/)
- **用户指南**: [USER_GUIDE.md](docs/USER_GUIDE.md)
- **技术总结**: [PROJECT_TECHNICAL_SUMMARY.md](docs/PROJECT_TECHNICAL_SUMMARY.md)
- **问题反馈**: 请在GitHub Issues中提交

## 🌟 致谢

感谢以下开源项目的支持:
- [LlamaIndex](https://github.com/run-llama/llama_index) - RAG框架
- [FastAPI](https://github.com/tiangolo/fastapi) - 高性能Web框架
- [React](https://github.com/facebook/react) - 前端框架
- [Ant Design](https://github.com/ant-design/ant-design) - UI组件库
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个Star！**



</div>

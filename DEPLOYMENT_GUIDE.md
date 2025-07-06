# 智能文档助理系统 - 部署和维护指南

## 1. 系统要求

### 1.1 硬件要求

#### 最低配置
- **CPU**: 4核心 2.0GHz+
- **内存**: 8GB RAM
- **存储**: 20GB 可用空间
- **网络**: 本地网络连接

#### 推荐配置
- **CPU**: 8核心 3.0GHz+ (支持AVX指令集)
- **内存**: 16GB+ RAM
- **GPU**: NVIDIA GPU 8GB+ VRAM (可选，用于加速)
- **存储**: 50GB+ SSD存储
- **网络**: 千兆网络

### 1.2 软件要求

#### 操作系统
- **Linux**: Ubuntu 20.04+, CentOS 8+, Debian 11+
- **Windows**: Windows 10/11 (WSL2推荐)
- **macOS**: macOS 11.0+

#### 运行时环境
- **Python**: 3.11+ (推荐3.11.5)
- **Node.js**: 18.0+ (推荐18.17.0)
- **Git**: 2.30+

#### 可选组件
- **Docker**: 20.10+ (容器化部署)
- **NVIDIA Docker**: GPU支持
- **Nginx**: 反向代理 (生产环境)

## 2. 环境准备

### 2.1 Python环境配置

#### 安装Python 3.11
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# CentOS/RHEL
sudo dnf install python3.11 python3.11-devel

# macOS (使用Homebrew)
brew install python@3.11

# Windows (使用官方安装包)
# 下载并安装 Python 3.11 from python.org
```

#### 创建虚拟环境
```bash
# 创建虚拟环境
python3.11 -m venv llamaindex

# 激活虚拟环境
# Linux/macOS
source llamaindex/bin/activate

# Windows
llamaindex\Scripts\activate
```

### 2.2 Node.js环境配置

#### 安装Node.js
```bash
# 使用NodeSource仓库 (Linux)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 使用NVM (推荐)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# macOS (使用Homebrew)
brew install node@18

# Windows (使用官方安装包)
# 下载并安装 Node.js 18 from nodejs.org
```

### 2.3 GPU支持配置 (可选)

#### NVIDIA驱动安装
```bash
# Ubuntu
sudo apt install nvidia-driver-535
sudo reboot

# 验证安装
nvidia-smi
```

#### CUDA工具包安装
```bash
# Ubuntu 22.04
wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda_12.2.0_535.54.03_linux.run
sudo sh cuda_12.2.0_535.54.03_linux.run

# 添加环境变量
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

## 3. 系统部署

### 3.1 源码部署

#### 步骤1: 获取源码
```bash
# 克隆项目 (如果有Git仓库)
git clone <repository-url> intelligent-doc-assistant
cd intelligent-doc-assistant

# 或者解压源码包
tar -xzf intelligent-doc-assistant.tar.gz
cd intelligent-doc-assistant
```

#### 步骤2: 后端部署
```bash
cd backend

# 激活虚拟环境
source ../llamaindex/bin/activate

# 安装依赖
pip install -r requirements.txt

# 创建必要目录
mkdir -p ../uploads ../vector_db ../logs

# 初始化数据库
python -c "from app.core.migration_manager import MigrationManager; MigrationManager().run_migrations()"

# 启动后端服务
python main.py
```

#### 步骤3: 前端部署
```bash
cd frontend

# 安装依赖
npm install

# 开发模式启动
npm run dev

# 或生产构建
npm run build
npm run preview
```

### 3.2 Docker部署

#### 步骤1: 创建Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源码
COPY . .

# 构建应用
RUN npm run build

# 暴露端口
EXPOSE 5173

# 启动命令
CMD ["npm", "run", "preview"]
```

#### 步骤2: 创建docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./vector_db:/app/vector_db
      - ./documents.db:/app/documents.db
    environment:
      - DEBUG=false
      - LM_STUDIO_BASE_URL=http://host.docker.internal:1234
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

#### 步骤3: 启动容器
```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 4. AI模型配置

### 4.1 LM Studio配置

#### 安装LM Studio
1. 下载LM Studio: https://lmstudio.ai/
2. 安装并启动LM Studio
3. 下载qwen2.5-14b-instruct模型
4. 启动本地服务器 (默认端口1234)

#### 配置连接
```python
# backend/app/core/config.py
LM_STUDIO_BASE_URL = "http://192.168.1.3:1234"  # 修改为实际IP
LM_STUDIO_MODEL_NAME = "qwen2.5-14b-instruct"
```

### 4.2 Ollama配置

#### 安装Ollama
```bash
# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# macOS
brew install ollama

# Windows
# 下载并安装 Ollama from ollama.ai
```

#### 下载模型
```bash
# 下载主要模型
ollama pull qwen2.5vl:7b

# 下载嵌入模型
ollama pull dengcao/Qwen3-Embedding-8B:Q8_0

# 启动服务
ollama serve
```

## 5. 生产环境配置

### 5.1 Nginx反向代理

#### 安装Nginx
```bash
# Ubuntu/Debian
sudo apt install nginx

# CentOS/RHEL
sudo dnf install nginx
```

#### 配置文件
```nginx
# /etc/nginx/sites-available/intelligent-doc-assistant
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 增加超时时间 (RAG响应可能较慢)
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # 文件上传大小限制
    client_max_body_size 100M;
}
```

#### 启用配置
```bash
sudo ln -s /etc/nginx/sites-available/intelligent-doc-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5.2 SSL证书配置

#### 使用Let's Encrypt
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 5.3 系统服务配置

#### 创建systemd服务
```ini
# /etc/systemd/system/doc-assistant-backend.service
[Unit]
Description=Intelligent Document Assistant Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/intelligent-doc-assistant/backend
Environment=PATH=/opt/intelligent-doc-assistant/llamaindex/bin
ExecStart=/opt/intelligent-doc-assistant/llamaindex/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/doc-assistant-frontend.service
[Unit]
Description=Intelligent Document Assistant Frontend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/intelligent-doc-assistant/frontend
ExecStart=/usr/bin/npm run preview
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 启用服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable doc-assistant-backend
sudo systemctl enable doc-assistant-frontend
sudo systemctl start doc-assistant-backend
sudo systemctl start doc-assistant-frontend
```

## 6. 监控和日志

### 6.1 日志配置

#### 后端日志
```python
# backend/app/core/config.py
LOG_LEVEL = "INFO"
LOG_FILE = "../logs/app.log"
LOG_ROTATION = "1 day"
LOG_RETENTION = "30 days"
```

#### 日志轮转
```bash
# /etc/logrotate.d/intelligent-doc-assistant
/opt/intelligent-doc-assistant/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload doc-assistant-backend
    endscript
}
```

### 6.2 性能监控

#### 系统监控脚本
```bash
#!/bin/bash
# monitor.sh

# 检查服务状态
check_service() {
    if systemctl is-active --quiet $1; then
        echo "✅ $1 is running"
    else
        echo "❌ $1 is not running"
        systemctl restart $1
    fi
}

# 检查端口
check_port() {
    if nc -z localhost $1; then
        echo "✅ Port $1 is open"
    else
        echo "❌ Port $1 is closed"
    fi
}

# 检查磁盘空间
check_disk() {
    usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $usage -gt 80 ]; then
        echo "⚠️ Disk usage is ${usage}%"
    else
        echo "✅ Disk usage is ${usage}%"
    fi
}

echo "=== System Health Check ==="
check_service doc-assistant-backend
check_service doc-assistant-frontend
check_port 8000
check_port 5173
check_disk
```

## 7. 备份和恢复

### 7.1 数据备份

#### 自动备份脚本
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/intelligent-doc-assistant"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
cp /opt/intelligent-doc-assistant/documents.db $BACKUP_DIR/documents_$DATE.db

# 备份向量数据库
tar -czf $BACKUP_DIR/vector_db_$DATE.tar.gz /opt/intelligent-doc-assistant/vector_db

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/intelligent-doc-assistant/uploads

# 清理旧备份 (保留30天)
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

#### 定时备份
```bash
# 添加到crontab
crontab -e
# 每天凌晨2点备份
0 2 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1
```

### 7.2 系统恢复

#### 恢复步骤
```bash
# 1. 停止服务
sudo systemctl stop doc-assistant-backend
sudo systemctl stop doc-assistant-frontend

# 2. 恢复数据库
cp /backup/intelligent-doc-assistant/documents_YYYYMMDD_HHMMSS.db /opt/intelligent-doc-assistant/documents.db

# 3. 恢复向量数据库
cd /opt/intelligent-doc-assistant
tar -xzf /backup/intelligent-doc-assistant/vector_db_YYYYMMDD_HHMMSS.tar.gz

# 4. 恢复上传文件
tar -xzf /backup/intelligent-doc-assistant/uploads_YYYYMMDD_HHMMSS.tar.gz

# 5. 重启服务
sudo systemctl start doc-assistant-backend
sudo systemctl start doc-assistant-frontend
```

## 8. 故障排除

### 8.1 常见问题

#### 后端服务无法启动
```bash
# 检查日志
journalctl -u doc-assistant-backend -f

# 检查端口占用
netstat -tlnp | grep 8000

# 检查Python环境
source /opt/intelligent-doc-assistant/llamaindex/bin/activate
python -c "import fastapi; print('FastAPI OK')"
```

#### 前端无法访问
```bash
# 检查Node.js进程
ps aux | grep node

# 检查端口
netstat -tlnp | grep 5173

# 重新构建
cd /opt/intelligent-doc-assistant/frontend
npm run build
```

#### LLM服务连接失败
```bash
# 检查LM Studio连接
curl http://192.168.1.3:1234/v1/models

# 检查Ollama连接
curl http://localhost:11434/api/tags
```

### 8.2 性能优化

#### 数据库优化
```sql
-- 创建索引
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);

-- 清理旧数据
DELETE FROM messages WHERE created_at < datetime('now', '-90 days');
```

#### 向量数据库优化
```python
# 定期重建索引
from app.services.vector_storage import VectorStorage

vector_storage = VectorStorage()
await vector_storage.rebuild_index()
```

---

**部署指南版本**: v1.0.0  
**最后更新**: 2025年7月5日  
**维护团队**: AI开发团队

-- 智能文档分类功能数据库迁移脚本
-- 版本: 001
-- 描述: 添加文档分类、标签和智能索引相关表结构

-- 1. 扩展documents表，添加分类相关字段
ALTER TABLE documents ADD COLUMN category TEXT DEFAULT '未分类';
ALTER TABLE documents ADD COLUMN subcategory TEXT;
ALTER TABLE documents ADD COLUMN auto_tags TEXT; -- JSON格式存储自动生成的标签
ALTER TABLE documents ADD COLUMN manual_tags TEXT; -- JSON格式存储用户手动添加的标签
ALTER TABLE documents ADD COLUMN classification_confidence REAL DEFAULT 0.0;
ALTER TABLE documents ADD COLUMN classification_method TEXT DEFAULT 'auto'; -- auto/manual/hybrid
ALTER TABLE documents ADD COLUMN keywords TEXT; -- JSON格式存储提取的关键词
ALTER TABLE documents ADD COLUMN summary TEXT; -- 文档摘要
ALTER TABLE documents ADD COLUMN language TEXT DEFAULT 'zh'; -- 文档语言
ALTER TABLE documents ADD COLUMN classification_at TIMESTAMP; -- 分类时间

-- 2. 创建文档分类表
CREATE TABLE IF NOT EXISTS document_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    parent_id TEXT,
    description TEXT,
    icon TEXT, -- 分类图标
    color TEXT, -- 分类颜色
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    document_count INTEGER DEFAULT 0, -- 该分类下的文档数量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES document_categories(id) ON DELETE SET NULL
);

-- 3. 创建文档标签表
CREATE TABLE IF NOT EXISTS document_tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT, -- 标签所属分类
    description TEXT,
    color TEXT, -- 标签颜色
    usage_count INTEGER DEFAULT 0, -- 使用次数
    is_system BOOLEAN DEFAULT FALSE, -- 是否为系统标签
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 创建文档-标签关联表
CREATE TABLE IF NOT EXISTS document_tag_relations (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    confidence REAL DEFAULT 1.0, -- 标签置信度
    source TEXT DEFAULT 'auto', -- auto/manual
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES document_tags(id) ON DELETE CASCADE,
    UNIQUE(document_id, tag_id)
);

-- 5. 创建文档关联表（用于存储文档间的关联关系）
CREATE TABLE IF NOT EXISTS document_relations (
    id TEXT PRIMARY KEY,
    source_document_id TEXT NOT NULL,
    target_document_id TEXT NOT NULL,
    relation_type TEXT NOT NULL, -- similar/reference/topic/temporal
    confidence REAL DEFAULT 0.0,
    metadata TEXT, -- JSON格式存储关联元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (target_document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(source_document_id, target_document_id, relation_type)
);

-- 6. 创建查询历史表（用于优化检索）
CREATE TABLE IF NOT EXISTS query_history (
    id TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_hash TEXT NOT NULL, -- 查询文本的哈希值
    intent TEXT, -- 查询意图
    keywords TEXT, -- JSON格式存储提取的关键词
    entities TEXT, -- JSON格式存储提取的实体
    retrieved_documents TEXT, -- JSON格式存储检索到的文档ID
    user_feedback INTEGER, -- 用户反馈评分 1-5
    response_time REAL, -- 响应时间（秒）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 创建系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    config_type TEXT DEFAULT 'string', -- string/integer/float/boolean/json
    is_editable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 插入预定义分类
INSERT OR IGNORE INTO document_categories (id, name, description, icon, color, sort_order) VALUES
('tech-docs', '技术文档', '技术相关的文档，包括API文档、技术规范等', 'CodeOutlined', '#1890ff', 1),
('research', '研究报告', '学术研究、市场调研、分析报告等', 'ExperimentOutlined', '#52c41a', 2),
('manual', '操作手册', '用户手册、操作指南、流程文档等', 'BookOutlined', '#fa8c16', 3),
('resume', '个人简历', '个人简历、求职相关文档', 'UserOutlined', '#eb2f96', 4),
('academic', '学术论文', '学术论文、期刊文章、会议论文等', 'ReadOutlined', '#722ed1', 5),
('business', '商业文档', '商业计划、合同、财务报告等', 'DollarOutlined', '#13c2c2', 6),
('legal', '法律文件', '法律条文、合同、法规文件等', 'SafetyOutlined', '#f5222d', 7),
('other', '其他', '未分类或其他类型的文档', 'FileOutlined', '#8c8c8c', 99);

-- 9. 插入预定义标签
INSERT OR IGNORE INTO document_tags (id, name, category, description, color, is_system) VALUES
('tag-important', '重要', 'priority', '重要文档标记', '#f5222d', TRUE),
('tag-draft', '草稿', 'status', '草稿状态文档', '#faad14', TRUE),
('tag-final', '最终版', 'status', '最终版本文档', '#52c41a', TRUE),
('tag-confidential', '机密', 'security', '机密文档标记', '#722ed1', TRUE),
('tag-public', '公开', 'security', '公开文档标记', '#1890ff', TRUE),
('tag-archived', '已归档', 'status', '已归档文档', '#8c8c8c', TRUE);

-- 10. 插入系统配置
INSERT OR IGNORE INTO system_config (key, value, description, config_type) VALUES
('classification.enabled', 'true', '是否启用自动分类功能', 'boolean'),
('classification.confidence_threshold', '0.7', '分类置信度阈值', 'float'),
('classification.max_tags', '10', '每个文档最大标签数量', 'integer'),
('retrieval.default_chunk_count', '5', '默认检索文档块数量', 'integer'),
('retrieval.similarity_threshold', '0.7', '相似度阈值', 'float'),
('indexing.enable_keyword_index', 'true', '是否启用关键词索引', 'boolean'),
('indexing.enable_relation_analysis', 'true', '是否启用文档关联分析', 'boolean');

-- 11. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_classification_confidence ON documents(classification_confidence);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_document_tag_relations_document_id ON document_tag_relations(document_id);
CREATE INDEX IF NOT EXISTS idx_document_tag_relations_tag_id ON document_tag_relations(tag_id);
CREATE INDEX IF NOT EXISTS idx_document_relations_source ON document_relations(source_document_id);
CREATE INDEX IF NOT EXISTS idx_document_relations_target ON document_relations(target_document_id);
CREATE INDEX IF NOT EXISTS idx_query_history_query_hash ON query_history(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at);

-- 12. 创建视图以简化查询
CREATE VIEW IF NOT EXISTS document_with_classification AS
SELECT 
    d.*,
    dc.name as category_name,
    dc.description as category_description,
    dc.icon as category_icon,
    dc.color as category_color,
    GROUP_CONCAT(dt.name) as tag_names
FROM documents d
LEFT JOIN document_categories dc ON d.category = dc.id
LEFT JOIN document_tag_relations dtr ON d.id = dtr.document_id
LEFT JOIN document_tags dt ON dtr.tag_id = dt.id
GROUP BY d.id;

-- 迁移完成标记
INSERT OR IGNORE INTO system_config (key, value, description) VALUES
('migration.001_classification', 'completed', '分类功能迁移完成标记');

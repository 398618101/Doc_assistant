"""
应用配置管理
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """应用设置"""
    
    # 应用基础配置
    APP_NAME: str = "智能文档助理"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # LM Studio配置
    LM_STUDIO_BASE_URL: str = "http://192.168.1.3:1234"
    LM_STUDIO_API_KEY: str = ""
    LM_STUDIO_MODEL_NAME: str = "default"
    LM_STUDIO_EMBEDDING_MODEL: str = "text-embedding-qwen3-embedding-8b"
    
    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_NAME: str = "qwen2.5vl:7b"
    
    # 默认LLM提供者
    DEFAULT_LLM_PROVIDER: str = "ollama"
    
    # 向量数据库配置
    CHROMA_PERSIST_DIRECTORY: str = "../vector_db"
    CHROMA_COLLECTION_NAME: str = "documents"
    
    # 文件存储配置
    UPLOAD_DIR: str = "../uploads"
    MAX_FILE_SIZE: str = "100MB"
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "doc", "txt", "md", "png", "jpg", "jpeg"]
    
    # Embedding模型配置
    EMBEDDING_PROVIDER: str = "lm_studio"  # 可选: "lm_studio", "ollama"
    EMBEDDING_MODEL_NAME: str = "text-embedding-qwen3-embedding-8b"
    EMBEDDING_DEVICE: str = "cuda"  # 使用GPU加速
    # 备用Ollama embedding模型
    OLLAMA_EMBEDDING_MODEL: str = "dengcao/Qwen3-Embedding-8B:Q8_0"
    
    # OCR配置
    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "chi_sim+eng"
    OCR_DPI: int = 300
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    @validator("ALLOWED_EXTENSIONS", pre=True)
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("MAX_FILE_SIZE")
    def parse_file_size(cls, v):
        """解析文件大小配置"""
        if isinstance(v, str):
            v = v.upper()
            if v.endswith("MB"):
                return int(v[:-2]) * 1024 * 1024
            elif v.endswith("GB"):
                return int(v[:-2]) * 1024 * 1024 * 1024
            elif v.endswith("KB"):
                return int(v[:-2]) * 1024
        return int(v)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """获取应用设置"""
    return settings

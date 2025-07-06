"""
LLM提供者基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """LLM响应模型"""
    content: str
    model: str
    usage: Optional[Dict] = None
    finish_reason: Optional[str] = None


class EmbeddingResponse(BaseModel):
    """Embedding响应模型"""
    embeddings: List[List[float]]
    model: str
    usage: Optional[Dict] = None


class BaseLLMProvider(ABC):
    """LLM提供者基类"""
    
    def __init__(self, base_url: str, api_key: str = "", model_name: str = "default"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self._is_available = None
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> LLMResponse:
        """生成文本"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        pass
    
    @abstractmethod
    async def get_embedding(
        self, 
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResponse:
        """获取文本嵌入向量"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """列出可用模型"""
        pass
    
    async def is_available(self) -> bool:
        """检查提供者是否可用"""
        if self._is_available is None:
            self._is_available = await self.health_check()
        return self._is_available
    
    def reset_availability(self):
        """重置可用性状态"""
        self._is_available = None

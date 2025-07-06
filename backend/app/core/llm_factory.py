"""
LLM工厂和管理器
"""
from typing import Dict, Optional, AsyncGenerator
from loguru import logger

from app.core.config import get_settings
from app.services.llm_providers import BaseLLMProvider, LMStudioProvider, OllamaProvider
from app.services.llm_providers.base import LLMResponse


class LLMManager:
    """LLM管理器 - 支持多个提供者和自动切换"""
    
    def __init__(self):
        self.settings = get_settings()
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.current_provider_name = self.settings.DEFAULT_LLM_PROVIDER
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化所有LLM提供者"""
        # 初始化LM Studio提供者
        self.providers["lm_studio"] = LMStudioProvider(
            base_url=self.settings.LM_STUDIO_BASE_URL,
            api_key=self.settings.LM_STUDIO_API_KEY,
            model_name=self.settings.LM_STUDIO_MODEL_NAME
        )
        
        # 初始化Ollama提供者
        self.providers["ollama"] = OllamaProvider(
            base_url=self.settings.OLLAMA_BASE_URL,
            api_key="",  # Ollama通常不需要API key
            model_name=self.settings.OLLAMA_MODEL_NAME
        )
        
        logger.info(f"已初始化LLM提供者: {list(self.providers.keys())}")
        logger.info(f"当前默认提供者: {self.current_provider_name}")
    
    async def get_current_provider(self) -> BaseLLMProvider:
        """获取当前可用的提供者"""
        # 首先尝试当前设置的提供者
        current_provider = self.providers.get(self.current_provider_name)
        if current_provider and await current_provider.is_available():
            return current_provider
        
        # 如果当前提供者不可用，尝试其他提供者
        logger.warning(f"当前提供者 {self.current_provider_name} 不可用，尝试切换到其他提供者")
        
        for name, provider in self.providers.items():
            if name != self.current_provider_name:
                if await provider.is_available():
                    logger.info(f"自动切换到提供者: {name}")
                    self.current_provider_name = name
                    return provider
        
        # 如果所有提供者都不可用
        raise Exception("所有LLM提供者都不可用，请检查服务状态")
    
    async def switch_provider(self, provider_name: str) -> bool:
        """手动切换提供者"""
        if provider_name not in self.providers:
            logger.error(f"未知的提供者: {provider_name}")
            return False
        
        provider = self.providers[provider_name]
        if await provider.is_available():
            self.current_provider_name = provider_name
            logger.info(f"已切换到提供者: {provider_name}")
            return True
        else:
            logger.error(f"提供者 {provider_name} 不可用")
            return False
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False,
        provider_name: Optional[str] = None
    ) -> Dict:
        """生成文本 - 返回字典格式以兼容RAG服务"""
        if provider_name:
            # 使用指定的提供者
            provider = self.providers.get(provider_name)
            if not provider:
                raise Exception(f"未知的提供者: {provider_name}")
            if not await provider.is_available():
                raise Exception(f"提供者 {provider_name} 不可用")
        else:
            # 使用当前可用的提供者
            provider = await self.get_current_provider()

        try:
            response = await provider.generate(prompt, max_tokens, temperature, stream)
            # 转换为字典格式
            return {
                'text': response.content,
                'model': response.model,
                'usage': response.usage or {},
                'finish_reason': response.finish_reason
            }
        except Exception as e:
            logger.error(f"文本生成失败: {str(e)}")
            # 重置提供者可用性状态，下次会重新检查
            provider.reset_availability()
            raise
    
    async def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        provider_name: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """流式生成文本 - 返回字典格式以兼容RAG服务"""
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                raise Exception(f"未知的提供者: {provider_name}")
            if not await provider.is_available():
                raise Exception(f"提供者 {provider_name} 不可用")
        else:
            provider = await self.get_current_provider()

        try:
            async for chunk in provider.generate_stream(prompt, max_tokens, temperature):
                yield {'text': chunk}
        except Exception as e:
            logger.error(f"流式文本生成失败: {str(e)}")
            provider.reset_availability()
            raise

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        provider_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成文本 - 保持原有接口兼容性"""
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                raise Exception(f"未知的提供者: {provider_name}")
            if not await provider.is_available():
                raise Exception(f"提供者 {provider_name} 不可用")
        else:
            provider = await self.get_current_provider()

        try:
            async for chunk in provider.generate_stream(prompt, max_tokens, temperature):
                yield chunk
        except Exception as e:
            logger.error(f"流式文本生成失败: {str(e)}")
            provider.reset_availability()
            raise
    
    async def get_embedding(
        self, 
        texts: list, 
        model: Optional[str] = None,
        provider_name: Optional[str] = None
    ):
        """获取文本嵌入向量"""
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                raise Exception(f"未知的提供者: {provider_name}")
            if not await provider.is_available():
                raise Exception(f"提供者 {provider_name} 不可用")
        else:
            provider = await self.get_current_provider()
        
        try:
            return await provider.get_embedding(texts, model)
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {str(e)}")
            provider.reset_availability()
            raise
    
    async def get_provider_status(self) -> Dict[str, bool]:
        """获取所有提供者的状态"""
        status = {}
        for name, provider in self.providers.items():
            status[name] = await provider.health_check()
        return status
    
    async def list_available_models(self) -> Dict[str, list]:
        """列出所有提供者的可用模型"""
        models = {}
        for name, provider in self.providers.items():
            if await provider.is_available():
                models[name] = await provider.list_models()
            else:
                models[name] = []
        return models
    
    def get_current_provider_name(self) -> str:
        """获取当前提供者名称"""
        return self.current_provider_name


class LLMFactory:
    """LLM工厂类 - 为RAG服务提供统一接口"""

    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    async def get_client(self):
        """获取LLM客户端"""
        return self.llm_manager

    async def get_provider(self, provider_name: Optional[str] = None):
        """获取指定的LLM提供者"""
        if provider_name:
            return self.llm_manager.providers.get(provider_name)
        return await self.llm_manager.get_current_provider()

    def get_available_providers(self) -> list:
        """获取可用的提供者列表"""
        return list(self.llm_manager.providers.keys())


# 创建全局LLM管理器实例
llm_manager = LLMManager()

# 创建全局LLM工厂实例
llm_factory = LLMFactory(llm_manager)


def get_llm_manager() -> LLMManager:
    """获取LLM管理器实例"""
    return llm_manager


def get_llm_factory() -> LLMFactory:
    """获取LLM工厂实例"""
    return llm_factory

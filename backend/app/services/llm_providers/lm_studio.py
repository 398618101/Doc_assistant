"""
LM Studio提供者实现
"""
import json
import asyncio
from typing import List, Optional, AsyncGenerator
import aiohttp
from loguru import logger

from .base import BaseLLMProvider, LLMResponse, EmbeddingResponse


class LMStudioProvider(BaseLLMProvider):
    """LM Studio提供者"""
    
    def __init__(self, base_url: str, api_key: str = "", model_name: str = "default"):
        super().__init__(base_url, api_key, model_name)
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5分钟超时
    
    async def generate(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> LLMResponse:
        """生成文本"""
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        return LLMResponse(
                            content=content,
                            model=data.get("model", self.model_name),
                            usage=data.get("usage"),
                            finish_reason=data["choices"][0].get("finish_reason")
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"LM Studio API错误: {response.status} - {error_text}")
                        raise Exception(f"LM Studio API错误: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("LM Studio API请求超时")
            raise Exception("LM Studio API请求超时")
        except Exception as e:
            logger.error(f"LM Studio API请求失败: {str(e)}")
            raise
    
    async def generate_stream(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data_str = line[6:]  # 移除 'data: ' 前缀
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if 'choices' in data and len(data['choices']) > 0:
                                        delta = data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            yield delta['content']
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        logger.error(f"LM Studio流式API错误: {response.status} - {error_text}")
                        raise Exception(f"LM Studio流式API错误: {response.status}")
                        
        except Exception as e:
            logger.error(f"LM Studio流式API请求失败: {str(e)}")
            raise
    
    async def get_embedding(
        self, 
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResponse:
        """获取文本嵌入向量"""
        url = f"{self.base_url}/v1/embeddings"
        
        payload = {
            "model": model or self.model_name,
            "input": texts
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        embeddings = [item["embedding"] for item in data["data"]]
                        
                        return EmbeddingResponse(
                            embeddings=embeddings,
                            model=data.get("model", model or self.model_name),
                            usage=data.get("usage")
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"LM Studio Embedding API错误: {response.status} - {error_text}")
                        raise Exception(f"LM Studio Embedding API错误: {response.status}")
                        
        except Exception as e:
            logger.error(f"LM Studio Embedding API请求失败: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            url = f"{self.base_url}/v1/models"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"LM Studio健康检查失败: {str(e)}")
            return False
    
    async def list_models(self) -> List[str]:
        """列出可用模型"""
        try:
            url = f"{self.base_url}/v1/models"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["id"] for model in data.get("data", [])]
                    else:
                        logger.error(f"获取LM Studio模型列表失败: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"获取LM Studio模型列表异常: {str(e)}")
            return []

"""
Ollama提供者实现
"""
import json
import asyncio
from typing import List, Optional, AsyncGenerator
import aiohttp
from loguru import logger

from .base import BaseLLMProvider, LLMResponse, EmbeddingResponse


class OllamaProvider(BaseLLMProvider):
    """Ollama提供者"""
    
    def __init__(self, base_url: str, api_key: str = "", model_name: str = "llama2"):
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
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            },
            "stream": stream
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("response", "")
                        
                        return LLMResponse(
                            content=content,
                            model=data.get("model", self.model_name),
                            usage=None,  # Ollama不返回usage信息
                            finish_reason="stop" if data.get("done", False) else None
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API错误: {response.status} - {error_text}")
                        raise Exception(f"Ollama API错误: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("Ollama API请求超时")
            raise Exception("Ollama API请求超时")
        except Exception as e:
            logger.error(f"Ollama API请求失败: {str(e)}")
            raise
    
    async def generate_stream(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            },
            "stream": True
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line:
                                try:
                                    data = json.loads(line)
                                    if 'response' in data:
                                        yield data['response']
                                    if data.get('done', False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama流式API错误: {response.status} - {error_text}")
                        raise Exception(f"Ollama流式API错误: {response.status}")
                        
        except Exception as e:
            logger.error(f"Ollama流式API请求失败: {str(e)}")
            raise
    
    async def get_embedding(
        self, 
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResponse:
        """获取文本嵌入向量"""
        url = f"{self.base_url}/api/embeddings"
        
        # Ollama的embedding API一次只能处理一个文本
        embeddings = []
        embedding_model = model or self.model_name
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                for text in texts:
                    payload = {
                        "model": embedding_model,
                        "prompt": text
                    }
                    
                    async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                        if response.status == 200:
                            data = await response.json()
                            embeddings.append(data.get("embedding", []))
                        else:
                            error_text = await response.text()
                            logger.error(f"Ollama Embedding API错误: {response.status} - {error_text}")
                            raise Exception(f"Ollama Embedding API错误: {response.status}")
                
                return EmbeddingResponse(
                    embeddings=embeddings,
                    model=embedding_model,
                    usage=None  # Ollama不返回usage信息
                )
                        
        except Exception as e:
            logger.error(f"Ollama Embedding API请求失败: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Ollama健康检查失败: {str(e)}")
            return False
    
    async def list_models(self) -> List[str]:
        """列出可用模型"""
        try:
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        return [model["name"] for model in models]
                    else:
                        logger.error(f"获取Ollama模型列表失败: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"获取Ollama模型列表异常: {str(e)}")
            return []

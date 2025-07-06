"""
嵌入服务 - 集成Ollama嵌入模型
"""
import asyncio
import aiohttp
import json
from typing import List, Optional, Dict, Any
from loguru import logger

from app.core.config import get_settings


class EmbeddingService:
    """嵌入向量生成服务"""

    def __init__(self):
        """初始化嵌入服务"""
        self.settings = get_settings()
        self.provider = self.settings.EMBEDDING_PROVIDER
        self.ollama_base_url = "http://localhost:11434"
        self.lm_studio_base_url = self.settings.LM_STUDIO_BASE_URL

        # 根据提供者选择模型
        if self.provider == "lm_studio":
            self.embedding_model = self.settings.LM_STUDIO_EMBEDDING_MODEL
        else:
            self.embedding_model = self.settings.OLLAMA_EMBEDDING_MODEL

        self.max_chunk_size = 8192  # 最大文本长度
        self._model_loaded = False

        logger.info(f"Embedding服务初始化: 提供者={self.provider}, 模型={self.embedding_model}")
    
    async def _ensure_model_loaded(self) -> bool:
        """确保嵌入模型已加载"""
        if self._model_loaded:
            return True

        if self.provider == "lm_studio":
            return await self._check_lm_studio_model()
        else:
            return await self._check_ollama_model()

    async def _check_lm_studio_model(self) -> bool:
        """检查LM Studio模型"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.lm_studio_base_url}/v1/models") as response:
                    if response.status == 200:
                        models_data = await response.json()
                        model_ids = [model["id"] for model in models_data.get("data", [])]

                        if self.embedding_model in model_ids:
                            self._model_loaded = True
                            logger.info(f"LM Studio嵌入模型 {self.embedding_model} 已就绪 (GPU加速)")
                            return True
                        else:
                            logger.error(f"LM Studio中未找到嵌入模型 {self.embedding_model}")
                            logger.info(f"可用模型: {model_ids}")
                            return False
                    else:
                        logger.error(f"无法连接到LM Studio服务: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"检查LM Studio嵌入模型失败: {str(e)}")
            return False

    async def _check_ollama_model(self) -> bool:
        """检查Ollama模型"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/tags") as response:
                    if response.status == 200:
                        models_data = await response.json()
                        model_names = [model["name"] for model in models_data.get("models", [])]

                        if self.embedding_model in model_names:
                            self._model_loaded = True
                            logger.info(f"Ollama嵌入模型 {self.embedding_model} 已就绪")
                            return True
                        else:
                            logger.warning(f"Ollama嵌入模型 {self.embedding_model} 未找到，尝试拉取...")
                            return await self._pull_model()
                    else:
                        logger.error(f"无法连接到Ollama服务: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"检查Ollama嵌入模型失败: {str(e)}")
            return False
    
    async def _pull_model(self) -> bool:
        """拉取嵌入模型"""
        try:
            async with aiohttp.ClientSession() as session:
                pull_data = {"name": self.embedding_model}
                async with session.post(
                    f"{self.ollama_base_url}/api/pull",
                    json=pull_data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5分钟超时
                ) as response:
                    if response.status == 200:
                        logger.info(f"嵌入模型 {self.embedding_model} 拉取成功")
                        self._model_loaded = True
                        return True
                    else:
                        logger.error(f"拉取嵌入模型失败: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"拉取嵌入模型异常: {str(e)}")
            return False
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成单个文本的嵌入向量"""
        if not await self._ensure_model_loaded():
            logger.error("嵌入模型未就绪")
            return None

        # 截断过长的文本
        if len(text) > self.max_chunk_size:
            text = text[:self.max_chunk_size]
            logger.warning(f"文本过长，已截断到 {self.max_chunk_size} 字符")

        if self.provider == "lm_studio":
            return await self._generate_embedding_lm_studio(text)
        else:
            return await self._generate_embedding_ollama(text)

    async def _generate_embedding_lm_studio(self, text: str) -> Optional[List[float]]:
        """使用LM Studio生成嵌入向量"""
        try:
            async with aiohttp.ClientSession() as session:
                embed_data = {
                    "model": self.embedding_model,
                    "input": text
                }

                async with session.post(
                    f"{self.lm_studio_base_url}/v1/embeddings",
                    json=embed_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        embeddings = result.get("data", [])
                        if embeddings and len(embeddings) > 0:
                            embedding = embeddings[0].get("embedding")
                            if embedding:
                                logger.debug(f"LM Studio生成嵌入向量成功，维度: {len(embedding)} (GPU加速)")
                                return embedding
                        logger.error("LM Studio嵌入响应中没有找到向量数据")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"LM Studio生成嵌入向量失败: {response.status}, {error_text}")
                        return None
        except Exception as e:
            logger.error(f"LM Studio生成嵌入向量异常: {str(e)}")
            return None

    async def _generate_embedding_ollama(self, text: str) -> Optional[List[float]]:
        """使用Ollama生成嵌入向量"""
        try:
            async with aiohttp.ClientSession() as session:
                embed_data = {
                    "model": self.embedding_model,
                    "prompt": text
                }

                async with session.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json=embed_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        embedding = result.get("embedding")
                        if embedding:
                            logger.debug(f"Ollama生成嵌入向量成功，维度: {len(embedding)}")
                            return embedding
                        else:
                            logger.error("Ollama嵌入响应中没有找到向量数据")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama生成嵌入向量失败: {response.status}, {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Ollama生成嵌入向量异常: {str(e)}")
            return None
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量生成嵌入向量"""
        if not texts:
            return []
        
        logger.info(f"开始批量生成 {len(texts)} 个文本的嵌入向量")
        
        # 并发生成嵌入向量（限制并发数避免过载）
        semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
        
        async def generate_with_semaphore(text: str) -> Optional[List[float]]:
            async with semaphore:
                return await self.generate_embedding(text)
        
        tasks = [generate_with_semaphore(text) for text in texts]
        embeddings = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_embeddings = []
        success_count = 0
        for i, embedding in enumerate(embeddings):
            if isinstance(embedding, Exception):
                logger.error(f"第 {i+1} 个文本嵌入生成失败: {str(embedding)}")
                processed_embeddings.append(None)
            elif embedding is None:
                logger.error(f"第 {i+1} 个文本嵌入生成返回空值")
                processed_embeddings.append(None)
            else:
                processed_embeddings.append(embedding)
                success_count += 1
        
        logger.info(f"批量嵌入生成完成: {success_count}/{len(texts)} 成功")
        return processed_embeddings
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if self.provider == "lm_studio":
            return await self._health_check_lm_studio()
        else:
            return await self._health_check_ollama()

    async def _health_check_lm_studio(self) -> Dict[str, Any]:
        """LM Studio健康检查"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.lm_studio_base_url}/v1/models",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        models_data = await response.json()
                        model_ids = [model["id"] for model in models_data.get("data", [])]

                        return {
                            "status": "healthy",
                            "provider": "lm_studio",
                            "lm_studio_connected": True,
                            "embedding_model_available": self.embedding_model in model_ids,
                            "available_models": model_ids,
                            "embedding_model": self.embedding_model,
                            "device": "GPU (CUDA)"
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "provider": "lm_studio",
                            "lm_studio_connected": False,
                            "error": f"LM Studio响应状态: {response.status}"
                        }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "lm_studio",
                "lm_studio_connected": False,
                "error": str(e)
            }

    async def _health_check_ollama(self) -> Dict[str, Any]:
        """Ollama健康检查"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        models_data = await response.json()
                        model_names = [model["name"] for model in models_data.get("models", [])]

                        return {
                            "status": "healthy",
                            "provider": "ollama",
                            "ollama_connected": True,
                            "embedding_model_available": self.embedding_model in model_names,
                            "available_models": model_names,
                            "embedding_model": self.embedding_model
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "provider": "ollama",
                            "ollama_connected": False,
                            "error": f"Ollama响应状态: {response.status}"
                        }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "ollama_connected": False,
                "error": str(e)
            }
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量维度"""
        if self.provider == "lm_studio" and "qwen3-embedding-8b" in self.embedding_model.lower():
            return 4096  # Qwen3-Embedding-8B的实际维度
        else:
            return 768  # 默认维度


# 全局实例
embedding_service = EmbeddingService()

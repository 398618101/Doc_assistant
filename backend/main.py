"""
智能文档助理 - FastAPI主应用
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn

from app.core.config import get_settings
from app.core.llm_factory import get_llm_manager
from app.api import documents, vectorization, retrieval, rag


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="基于LlamaIndex和LM Studio/Ollama的智能文档助理系统",
        debug=settings.DEBUG
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174"
        ],  # React开发服务器
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 创建必要的目录
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # 配置日志
    logger.add(
        settings.LOG_FILE,
        rotation="10 MB",
        retention="7 days",
        level=settings.LOG_LEVEL
    )

    # 注册API路由
    app.include_router(documents.router)
    app.include_router(vectorization.router)
    app.include_router(retrieval.router)
    app.include_router(rag.router)

    return app


# 创建应用实例
app = create_app()


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("智能文档助理系统启动中...")
    
    # 检查LLM提供者状态
    llm_manager = get_llm_manager()
    provider_status = await llm_manager.get_provider_status()
    
    logger.info("LLM提供者状态:")
    for provider, status in provider_status.items():
        status_text = "可用" if status else "不可用"
        logger.info(f"  {provider}: {status_text}")
    
    # 检查是否有可用的提供者
    if not any(provider_status.values()):
        logger.warning("警告: 没有可用的LLM提供者！")
    else:
        logger.info(f"当前使用的提供者: {llm_manager.get_current_provider_name()}")
    
    logger.info("智能文档助理系统启动完成!")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("智能文档助理系统正在关闭...")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能文档助理系统",
        "version": get_settings().APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    llm_manager = get_llm_manager()
    provider_status = await llm_manager.get_provider_status()
    
    return {
        "status": "healthy",
        "providers": provider_status,
        "current_provider": llm_manager.get_current_provider_name()
    }


@app.get("/api/models")
async def list_models():
    """列出所有可用模型"""
    try:
        llm_manager = get_llm_manager()
        models = await llm_manager.list_available_models()
        return {
            "success": True,
            "models": models,
            "current_provider": llm_manager.get_current_provider_name()
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/switch-provider")
async def switch_provider(provider_data: dict):
    """切换LLM提供者"""
    provider_name = provider_data.get("provider")
    if not provider_name:
        raise HTTPException(status_code=400, detail="缺少provider参数")
    
    try:
        llm_manager = get_llm_manager()
        success = await llm_manager.switch_provider(provider_name)
        
        if success:
            return {
                "success": True,
                "message": f"已切换到提供者: {provider_name}",
                "current_provider": llm_manager.get_current_provider_name()
            }
        else:
            raise HTTPException(status_code=400, detail=f"无法切换到提供者: {provider_name}")
            
    except Exception as e:
        logger.error(f"切换提供者失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

"""
FastAPI主应用入口
麻醉科血气分析Web应用 - 简化版（无数据库，无用户认证）
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.core.config import settings
from app.api.v1.endpoints import analysis

# 创建临时文件上传目录
os.makedirs(settings.upload_dir, exist_ok=True)

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI驱动的围术期血气分析辅助决策系统（简化版，无数据存储）",
    debug=settings.debug,
)

# 配置CORS，允许所有来源（前端跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 健康检查和根路由 =====

@app.get("/")
async def root():
    """根路径，检查API是否正常运行"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "status": "running",
        "features": ["OCR血气识别", "AI围术期分析"]
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "blood-gas-analyzer",
        "has_gemini_key": bool(settings.gemini_api_key)
    }


# ===== 注册API路由 =====

# 血气分析相关路由
app.include_router(
    analysis.router,
    prefix="/api/v1",
    tags=["血气分析"]
)


# ===== 错误处理 =====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return {
        "success": False,
        "error": str(exc),
        "detail": "服务器出错了"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式热重载
    )

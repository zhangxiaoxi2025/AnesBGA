"""
应用配置管理
简化版：不需要数据库和用户认证
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基本配置
    app_name: str = "麻醉科血气分析助手"
    app_version: str = "0.1.0"
    debug: bool = True

    # Gemini API配置
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3-flash-preview"  # 2026年1月最新预览版

    # 文件上传配置
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    upload_dir: str = "./temp_uploads"  # 临时文件目录，用完就删

    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()

# 固定配置项（不从.env读取，避免解析问题）
ALLOWED_FILE_TYPES = ["jpg", "jpeg", "png"]
CORS_ORIGINS = ["*"]  # 允许所有来源

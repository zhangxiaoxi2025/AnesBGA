"""
数据库会话管理
这个SB模块必须严格管理数据库连接，别tm泄漏连接
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from ..core.config import settings

# 创建数据库引擎
# SQLite需要特殊配置check_same_thread，PostgreSQL不需要
engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    用完必须tm关闭，否则连接池会爆
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

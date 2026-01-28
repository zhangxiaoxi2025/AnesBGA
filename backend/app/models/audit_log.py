"""
审计日志模型
这个SB表用于记录所有敏感操作，医疗数据安全合规要求
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..database.base import Base


class AuditLog(Base):
    """审计日志表，记录所有敏感操作"""

    __tablename__ = "audit_logs"

    # UUID主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 操作者
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # 操作详情
    action = Column(String(50), nullable=False, index=True)  # CREATE, READ, UPDATE, DELETE
    resource_type = Column(String(50), nullable=False, index=True)  # User, BloodGasRecord等
    resource_id = Column(String(100), index=True)  # 操作的资源ID

    # 额外信息
    ip_address = Column(String(45))  # IPv4或IPv6地址
    user_agent = Column(String(500))  # 用户代理
    details = Column(String(1000))  # 操作详情描述

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog(action={self.action}, resource_type={self.resource_type})>"

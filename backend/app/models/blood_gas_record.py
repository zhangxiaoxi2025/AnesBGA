"""
血气分析记录模型
这个SB表是核心业务表，必须完整存储所有血气数据
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..database.base import Base


class BloodGasRecord(Base):
    """血气分析记录表"""

    __tablename__ = "blood_gas_records"

    # UUID主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 用户信息
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # 患者信息（匿名化）
    patient_id = Column(String(50), index=True)  # 患者ID（可用哈希或编码）
    patient_age = Column(Integer)
    patient_gender = Column(String(10))

    # === 血气指标 ===
    ph = Column(Float)  # pH值
    pco2 = Column(Float)  # 二氧化碳分压
    po2 = Column(Float)  # 氧分压
    hco3 = Column(Float)  # 碳酸氢根
    base_excess = Column(Float)  # 碱过量
    lactate = Column(Float)  # 乳酸
    sao2 = Column(Float)  # 氧饱和度
    # 可扩展的其他指标
    other_blood_gas = Column(JSON)

    # === 生命体征 ===
    blood_pressure_systolic = Column(Integer)  # 收缩压
    blood_pressure_diastolic = Column(Integer)  # 舒张压
    heart_rate = Column(Integer)  # 心率
    temperature = Column(Float)  # 体温
    spo2 = Column(Integer)  # 血氧饱和度(%)
    respiratory_rate = Column(Integer)  # 呼吸频率

    # === 麻醉参数 ===
    anesthesia_type = Column(String(50))  # 麻醉方式
    intubated = Column(String(10))  # 是否气管插管
    medications = Column(JSON)  # 用药记录
    anesthesia_notes = Column(Text)  # 麻醉备注

    # === OCR相关 ===
    ocr_image_url = Column(Text)  # 原始报告图片URL
    ocr_confidence = Column(Float)  # OCR识别置信度（0-1）
    ocr_raw_text = Column(Text)  # OCR原始识别文本

    # === AI分析 ===
    ai_analysis = Column(JSON)  # AI分析结果（结构化JSON）
    ai_analysis_text = Column(Text)  # AI分析文本结果

    # === 时间戳 ===
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<BloodGasRecord(id={self.id}, patient_id={self.patient_id})>"

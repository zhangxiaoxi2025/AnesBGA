"""
血气分析相关的Pydantic数据模型
这个SB文件必须确保所有数据验证都没问题
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BloodGasData(BaseModel):
    """血气指标数据"""

    ph: Optional[float] = Field(None, ge=6.5, le=8.0)
    pco2: Optional[float] = Field(None, ge=0, le=200)
    po2: Optional[float] = Field(None, ge=0, le=300)
    hco3: Optional[float] = Field(None, ge=5, le=40)
    base_excess: Optional[float] = Field(None, ge=-30, le=20)
    lactate: Optional[float] = Field(None, ge=0, le=20)
    sao2: Optional[float] = Field(None, ge=0, le=100)


class VitalSigns(BaseModel):
    """生命体征数据"""

    blood_pressure_systolic: Optional[int] = Field(None, ge=50, le=250)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=30, le=150)
    heart_rate: Optional[int] = Field(None, ge=30, le=200)
    temperature: Optional[float] = Field(None, ge=35.0, le=42.0)
    spo2: Optional[int] = Field(None, ge=70, le=100)
    respiratory_rate: Optional[int] = Field(None, ge=8, le=40)


class AnesthesiaParams(BaseModel):
    """麻醉参数"""

    anesthesia_type: Optional[str] = None  # 全身麻醉/椎管内/神经阻滞/局部
    intubated: Optional[str] = None  # 是/否
    medications: Optional[list] = None  # 用药列表
    anesthesia_notes: Optional[str] = None


class BloodGasRecordCreate(BaseModel):
    """创建血气记录的请求"""

    patient_id: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None

    # 血气数据
    blood_gas_data: Optional[BloodGasData] = None

    # 生命体征
    vital_signs: Optional[VitalSigns] = None

    # 麻醉参数
    anesthesia_params: Optional[AnesthesiaParams] = None

    # OCR相关
    ocr_image_url: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_raw_text: Optional[str] = None


class BloodGasRecordResponse(BloodGasRecordCreate):
    """血气记录响应"""

    id: str
    user_id: str
    ai_analysis: Optional[dict] = None
    ai_analysis_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BloodGasAnalysisRequest(BaseModel):
    """AI分析请求"""

    record_id: str


class BloodGasAnalysisResponse(BaseModel):
    """AI分析响应 - 支持量化计算建议"""

    analysis_id: str
    assessment: Optional[dict] = None  # 评估结果 - 改为Optional
    findings: Optional[list] = None  # 发现列表 - 改为Optional
    recommendations: Optional[list] = None  # 建议列表 - 改为Optional
    alerts: Optional[list] = None  # 警告列表 - 改为Optional
    disclaimer: Optional[str] = None  # 免责声明 - 改为Optional
    generated_at: datetime

    # 新增：量化计算建议
    acid_correction: Optional[dict] = None  # 酸中毒纠正
    alkalosis_management: Optional[dict] = None  # 碱中毒管理
    transfusion_guidance: Optional[dict] = None  # 输血指导
    electrolyte_correction: Optional[dict] = None  # 电解质纠正
    safety_warning: Optional[str] = None  # 安全警示

"""
血气分析API端点
简化版：不需要用户认证和数据库
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from typing import Optional
import json

from ....schemas.blood_gas import (
    BloodGasAnalysisRequest,
    BloodGasAnalysisResponse
)
from ....services.gemini_service import get_gemini_service
from ....core.config import settings

router = APIRouter()


@router.post("/ocr")
async def ocr_blood_gas_image(file: UploadFile = File(...), weight: Optional[str] = Form(None)):
    """
    上传血气报告图片，使用Gemini Vision进行OCR识别

    请求：
        - file: 血气报告图片（jpg/jpeg/png）
        - weight: 患者体重（可选，用于后续分析计算）

    返回：
        - 识别到的血气指标（JSON格式）
    """
    try:
        # 检查文件类型
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="艹！只支持jpg、jpeg、png格式的图片"
            )

        # 检查文件大小
        contents = await file.read()
        if len(contents) > settings.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"图片太大了，最大{settings.max_upload_size/1024/1024}MB"
            )

        # 调用Gemini OCR服务
        gemini_svc = get_gemini_service()
        result = await gemini_svc.ocr_blood_gas_report(contents)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result["error"]
            )

        return {
            "success": True,
            "ocr_result": result["data"],
            "weight": float(weight) if weight else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR识别出错：{str(e)}"
        )


@router.post("/analyze", response_model=BloodGasAnalysisResponse)
async def analyze_blood_gas(
    blood_gas_json: str = Form(...),
    vital_signs_json: Optional[str] = Form(None),
    anesthesia_json: Optional[str] = Form(None),
    weight: Optional[str] = Form(None)
):
    """
    分析血气数据，生成AI建议

    请求（都是JSON字符串格式）：
        - blood_gas_json: 血气数据（必需）
        - vital_signs_json: 生命体征数据（可选）
        - anesthesia_json: 麻醉参数（可选）
        - weight: 患者体重（可选，用于药量计算）

    返回：
        - 分析结果和建议
    """
    try:
        # 解析JSON数据
        blood_gas_data = json.loads(blood_gas_json) if blood_gas_json else {}
        vital_signs = json.loads(vital_signs_json) if vital_signs_json else None
        anesthesia_params = json.loads(anesthesia_json) if anesthesia_json else None

        # 强制类型转换 - 防止字符串类型的体重导致计算错误
        try:
            weight_value = float(weight) if weight else None
        except (ValueError, TypeError):
            weight_value = None

        # 检查是否至少有血气数据
        if not blood_gas_data or not any(blood_gas_data.values()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="艹！你tm得至少提供一个血气指标啊"
            )

        # 调用Gemini AI分析服务
        gemini_svc = get_gemini_service()
        result = await gemini_svc.analyze_blood_gas(
            blood_gas_data=blood_gas_data,
            vital_signs=vital_signs,
            anesthesia_params=anesthesia_params,
            weight=weight_value
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result["error"]
            )

        # 构造响应 - 安全获取所有字段，增加空值保护
        analysis_data = result.get("data", {})

        # 安全获取嵌套字段，避免 AI 返回空数据时崩溃
        def safe_get(data, key, default=None):
            """安全获取字典值，处理 None 和缺失键的情况"""
            if data is None:
                return default
            value = data.get(key) if isinstance(data, dict) else default
            if value is None:
                return default
            return value

        # 构建评估字典
        assessment = safe_get(analysis_data, "assessment", {})
        if not assessment or not isinstance(assessment, dict):
            assessment = {
                "acid_base_status": "数据不完整",
                "primary_disorder": "无法判断",
                "compensation_status": "无法判断",
                "severity": "未知",
                "oxygenation": "无法评估",
                "risk_level": "中风险",
                "clinical_summary": "血气数据不完整，无法给出完整评估"
            }

        return BloodGasAnalysisResponse(
            analysis_id="temp_" + str(hash(str(blood_gas_data)))[-10:],
            assessment=assessment,
            findings=safe_get(analysis_data, "findings", []),
            recommendations=safe_get(analysis_data, "recommendations", []),
            alerts=safe_get(analysis_data, "alerts", []),
            disclaimer=safe_get(analysis_data, "disclaimer", "以上分析基于AI算法，仅供临床参考。具体治疗方案必须由具有执业资格的主治医生根据患者整体情况决定。本系统不承担任何医疗责任。"),
            generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            # 新增字段 - 增加空值保护
            acid_correction=safe_get(analysis_data, "acid_correction"),
            alkalosis_management=safe_get(analysis_data, "alkalosis_management"),
            transfusion_guidance=safe_get(analysis_data, "transfusion_guidance"),
            electrolyte_correction=safe_get(analysis_data, "electrolyte_correction"),
            safety_warning=safe_get(analysis_data, "safety_warning")
        )

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"JSON格式错误：{str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析出错：{str(e)}"
        )

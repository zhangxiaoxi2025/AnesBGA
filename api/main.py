"""
Vercel Serverless Function - 血气分析后端
"""
import json
import os
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import base64
import io
from PIL import Image

# Vercel ASGI 适配器 - 直接导出 app
# Vercel 会自动用 ASGI 服务器运行这个 app
app = FastAPI(title="AnesGuardian API")

# 允许跨域（Vercel 前端）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 数据模型 ============

class BloodGasAnalysisResponse(BaseModel):
    """AI分析响应"""
    analysis_id: str
    assessment: Optional[dict] = None
    findings: Optional[list] = None
    recommendations: Optional[list] = None
    alerts: Optional[list] = None
    disclaimer: Optional[str] = None
    generated_at: datetime
    acid_correction: Optional[dict] = None
    alkalosis_management: Optional[dict] = None
    transfusion_guidance: Optional[dict] = None
    electrolyte_correction: Optional[dict] = None
    safety_warning: Optional[str] = None

# ============ AI 分析函数 ============

ANALYSIS_SYSTEM_PROMPT = """你是资深麻醉医师，分析血气数据并给出量化建议。

【输出格式】只返回JSON：
{{{{
  "assessment": {{
    "acid_base_status": "酸碱状态",
    "severity": "轻/中/重/正常",
    "oxygenation": "正常/低氧/轻度低氧",
    "risk_level": "低/中/高风险",
    "clinical_summary": "一句话总结"
  }},
  "acid_correction": {{
    "condition": "代谢性酸中毒（pH {...}，BE {...}）",
    "nahco3_5_percent_ml": NaHCO3毫升数,
    "recommendation": "首次半量给药"
  }},
  "findings": [{{"category":"酸碱平衡", "parameter":"pH", "value":...}}],
  "recommendations": [{{"priority":"高/中/低", "action":"具体措施", "detail":"剂量和时间"}}],
  "alerts": [{{"level":"警告", "message":"严重酸中毒"}}],
  "safety_warning": "需根据实际循环波动动态调整"
}}}}

【计算规则】
- 代谢性酸中毒：NaHCO3(ml) = |BE| × 体重 × 0.3 / 0.6
- 首次给半量，复查后调整

只返回JSON。"""


async def analyze_with_gemini(blood_gas_data: dict, weight: Optional[float] = None,
                               vital_signs: Optional[dict] = None,
                               anesthesia: Optional[dict] = None) -> dict:
    """使用 Gemini API 分析血气数据"""
    import httpx

    # 从环境变量读取 API Key
    api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 环境变量未设置")

    # 使用更快的模型
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # 格式化血气数据
    bg_parts = []
    for name, field in [("pH", "ph"), ("PO2", "po2"), ("PCO2", "pco2"), ("Na+", "na"),
                        ("K+", "k"), ("HCO3-", "hco3_act"), ("BEecf", "be_ecf"), ("THbc", "thbc")]:
        val = blood_gas_data.get(field)
        if val is not None:
            bg_parts.append(f"{name}: {val}")

    user_prompt = f"""血气数据: {', '.join(bg_parts) if bg_parts else '数据不完整'}
体重: {weight}kg{'（可用）' if weight else '（未提供）'}
请按格式返回JSON分析结果。"""

    # 调用 Gemini API
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    request_body = {{
        "contents": [{{"parts": [{{"text": user_prompt}}]}}],
        "system_instruction": {{
            "parts": [{{"text": ANALYSIS_SYSTEM_PROMPT}}]
        }},
        "generationConfig": {{
            "temperature": 0.2,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json"
        }}
    }}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            api_url,
            json=request_body,
            headers={{"Content-Type": "application/json"}}
        )

    if response.status_code != 200:
        raise ValueError(f"API调用失败 ({response.status_code}): {response.text}")

    response_data = response.json()

    # 检查错误
    if "error" in response_data:
        raise ValueError(f"Gemini API错误: {response_data['error']['message']}")

    # 提取文本内容
    result_text = ""
    if response_data.get("candidates"):
        candidate = response_data["candidates"][0]
        if "content" in candidate and "parts" in candidate["content"]:
            for part in candidate["content"]["parts"]:
                if "text" in part:
                    result_text = part["text"]
                    break

    # 去掉markdown代码块标记
    result_text = result_text.strip()
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    elif result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()

    # 解析JSON
    try:
        analysis_result = json.loads(result_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {str(e)}，原始响应: {result_text[:500]}")

    return analysis_result

# ============ OCR 识别函数 ============

OCR_PROMPT = """你是专业的血气分析报告 OCR 识别系统。

【重要规则 - 违反将导致严重后果】
1. 严禁捏造：看不清、被遮挡或不存在的指标必须返回 null，不准凭空猜测数字
2. 禁止推算：只提取肉眼可见的数值，不准用公式推算任何指标
3. 宁缺毋滥：宁可返回 null，也不准编造数据

【必须识别的 18 个指标清单】
请提取以下指标（如果图中没有或看不清，返回 null）：

| 序号 | 字段名 | 中文名 | 正常范围参考 |
|------|--------|--------|--------------|
| 1 | ph | pH值 | 7.35-7.45 |
| 2 | po2 | 氧分压 (mmHg) | 80-100 |
| 3 | pco2 | 二氧化碳分压 (mmHg) | 35-45 |
| 4 | na | 钠 Na+ (mmol/L) | 135-145 |
| 5 | k | 钾 K+ (mmol/L) | 3.5-5.5 |
| 6 | ca | 离子钙 Ca++ (mmol/L) | 1.10-1.35 |
| 7 | glu | 葡萄糖 GLU (mmol/L) | 3.9-6.1 |
| 8 | lac | 乳酸 LAC (mmol/L) | 0.5-2.2 |
| 9 | hct | 红细胞压积 HCT (%) | 35-50 |
| 10 | ca_74 | 校正钙 Ca++7.4 (mmol/L) | 1.10-1.35 |
| 11 | hco3_act | 碳酸氢盐 HCO3- (mmol/L) | 22-27 |
| 12 | hco3_std | 标准碳酸氢盐 HCO3s (mmol/L) | 22-27 |
| 13 | ctco2 | 总二氧化碳 ctCO2 (mmol/L) | 23-28 |
| 14 | be_ecf | 细胞外液碱剩余 BEecf (mmol/L) | -2~+2 |
| 15 | be_b | 剩余碱 BE(B) (mmol/L) | -2~+2 |
| 16 | so2c | 氧饱和度 SO2c (%) | 95-100 |
| 17 | thbc | 总血红蛋白 THbc (g/L) | 120-175 |
| 18 | temp | 体温 Temp (°C) | 36.0-37.5 |

【返回格式要求】
只返回纯 JSON 对象，不要任何 markdown 标记：

{
  "ph": 数值或null,
  "po2": 数值或null,
  "pco2": 数值或null,
  "na": 数值或null,
  "k": 数值或null,
  "ca": 数值或null,
  "glu": 数值或null,
  "lac": 数值或null,
  "hct": 数值或null,
  "ca_74": 数值或null,
  "hco3_act": 数值或null,
  "hco3_std": 数值或null,
  "ctco2": 数值或null,
  "be_ecf": 数值或null,
  "be_b": 数值或null,
  "so2c": 数值或null,
  "thbc": 数值或null,
  "temp": 数值或null,
  "missing_fields": ["字段名1", "字段名2"]  // 识别不到或看不清的字段列表
}

【重要】missing_fields 必须列出所有识别不到或被遮挡的字段名，即使你返回了部分数据。
"""

async def ocr_with_gemini(image_bytes: bytes) -> dict:
    """使用 Gemini Vision API 识别血气报告"""
    import httpx

    # 从环境变量读取 API Key
    api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 环境变量未设置")

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # 将图片转为 base64
    image = Image.open(io.BytesIO(image_bytes))
    buffered = io.BytesIO()
    image_format = image.format if image.format else 'JPEG'
    image.save(buffered, format=image_format, quality=95)
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # MIME 类型
    if image_format == 'JPEG':
        mime_type = 'image/jpeg'
    elif image_format == 'PNG':
        mime_type = 'image/png'
    else:
        mime_type = 'image/jpeg'

    # 调用 Gemini Vision API
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [
                {"text": OCR_PROMPT},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": img_base64
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, timeout=60.0)
        response.raise_for_status()
        result = response.json()

    # 解析响应
    if result.get("candidates") and result["candidates"][0].get("content"):
        result_text = result["candidates"][0]["content"]["parts"][0]["text"]
        # 清理可能的 markdown 格式
        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        ocr_result = json.loads(result_text)
        ocr_result["extracted_at"] = datetime.utcnow().isoformat()
        return ocr_result

    raise ValueError("OCR 识别失败：API 返回无效响应")

# ============ API 端点 ============

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "AnesGuardian API", "version": "1.0.0"}

@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/ocr")
async def ocr_blood_gas(file: UploadFile = File(...), weight: Optional[str] = Form(None)):
    """
    OCR 识别血气报告图片

    参数：
        - file: 血气报告图片文件（必需）
        - weight: 患者体重（可选，用于药量计算）
    """
    try:
        # 读取图片文件
        image_bytes = await file.read()

        # 检查文件大小（最大 10MB）
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图片文件大小不能超过 10MB"
            )

        # 检查文件类型
        if not file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只支持 JPG/PNG 格式的图片"
            )

        # 调用 OCR
        ocr_result = await ocr_with_gemini(image_bytes)

        return {
            "success": True,
            "ocr_result": ocr_result
        }

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OCR 结果解析失败：{str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR 识别失败：{str(e)}"
        )

@app.post("/api/v1/analyze")
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
    """
    try:
        # 解析JSON数据
        blood_gas_data = json.loads(blood_gas_json) if blood_gas_json else {}
        vital_signs_data = json.loads(vital_signs_json) if vital_signs_json else None
        anesthesia_data = json.loads(anesthesia_json) if anesthesia_json else None
        weight_value = float(weight) if weight else None

        # 检查是否至少有血气数据
        if not blood_gas_data or not any(blood_gas_data.values()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供血气数据"
            )

        # 调用 AI 分析（传递所有参数）
        result = await analyze_with_gemini(blood_gas_data, weight_value, vital_signs_data, anesthesia_data)

        # 构造响应
        return BloodGasAnalysisResponse(
            analysis_id="vercel_" + str(hash(str(blood_gas_data)))[-10:],
            assessment=result["assessment"],
            findings=result["findings"],
            recommendations=result["recommendations"],
            alerts=result["alerts"],
            disclaimer=result["disclaimer"],
            generated_at=datetime.now(datetime.timezone.utc),
            acid_correction=result["acid_correction"],
            alkalosis_management=result["alkalosis_management"],
            transfusion_guidance=result["transfusion_guidance"],
            electrolyte_correction=result["electrolyte_correction"],
            safety_warning=result["safety_warning"]
        )

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

# Vercel 直接运行 FastAPI，不需要 WSGI 适配器
# 导出 app 对象供 Vercel 使用

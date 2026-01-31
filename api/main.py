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

ANALYSIS_SYSTEM_PROMPT = """你是**资深主任麻醉医师**，拥有30年围术期管理经验。

【你的职责】
基于血气分析18项指标、患者体重和生命体征，给出**量化、具体、可执行**的临床建议。

{'【重要】患者体重: {weight} kg' if '{weight}' else '【注意】患者体重未提供，无法进行精确药量计算，请提示用户补充'}

----

## 一、酸碱平衡纠正

### A. 代谢性酸中毒 (pH < 7.35 且 BE < -3)
**计算公式**: NaHCO3 (mmol) = |BE| × weight × 0.3
**5%碳酸氢钠**: 1ml = 0.6mmol NaHCO3

**量化建议**:
- 计算所需NaHCO3 mmol数
- 换算为5%碳酸氢钠ml数
- 建议"首次给半量，根据血气复查调整"

### B. 代谢性碱中毒 (pH > 7.45)
**类型判断**:
- HCO3-升高为主 → 代谢性碱中毒
- PaCO2升高为主 → 呼吸性碱中毒代偿

**处理建议**:
- 结合Cl-水平：Cl- < 98 → 生理盐水补液
- 结合K+水平：K+ < 3.5 → 补钾治疗
- 呼吸机参数调整（如适用）

----

## 二、贫血与输血指导

**目标值**: THbc ≥ 100 g/L（或根据手术风险调整70-100）
**红细胞悬液**: 1U ≈ 提升Hb 5-10 g/L

**量化计算**:
- 需要提升: max(0, 100 - 当前THbc) g/L
- 估算红细胞悬液: 向上取整(需要提升 / 7) U

----

## 三、电解质纠正

### K+ 补钾
- 正常范围: 3.5-5.5 mmol/L
- 公式: 所需K+ (mmol) = (目标差值) × 体重(kg) × 0.3
- KCl规格: 1g KCl ≈ 13.4 mmol K+

### Ca++ 补钙
- 正常范围: 1.10-1.35 mmol/L
- 葡萄糖酸钙: 1g ≈ 2.2 mmol Ca++

----

## 四、输出格式要求

只返回JSON，结构如下：

{{{{
  "assessment": {{
    "acid_base_status": "酸碱状态描述",
    "primary_disorder": "原发性紊乱类型",
    "compensation_status": "代偿状态",
    "severity": "轻度/中度/重度",
    "oxygenation": "氧合状态",
    "risk_level": "低风险/中风险/高风险",
    "clinical_summary": "一句话临床总结"
  }},
  "acid_correction": {{
    "condition": "满足条件描述或不满足",
    "be_value": BE值,
    "calculated_na_hco3_mmol": 计算的NaHCO3 mmol数,
    "nahco3_5_percent_ml": 5%碳酸氢钠ml数,
    "recommendation": "首次半量给药建议",
    "formula_used": "NaHCO3 (mmol) = |BE| × weight × 0.3",
    "weight_used": 体重,
    "calculation_basis": "计算依据描述"
  }},
  "alkalosis_management": {{
    "condition": "满足条件描述或不满足",
    "type": "代谢性/呼吸性/混合性",
    "cl_level": Cl-值,
    "k_level": K+值,
    "fluid_therapy": "补液建议",
    "ventilation_adjustment": "呼吸机参数建议（如适用）"
  }},
  "transfusion_guidance": {{
    "condition": "满足条件描述或不满足",
    "current_thbc": 当前THbc值,
    "target_thbc": 目标值,
    "hemoglobin_deficit": 血红蛋白缺口,
    "prbc_units_estimated": 估算红细胞悬液U数,
    "clinical_reminders": ["临床提醒列表"]
  }},
  "electrolyte_correction": {{
    "potassium": {{
      "current_k": 当前K+值,
      "normal_range": "3.5-5.5",
      "deficit": 缺口值,
      "kcl_recommendation": "KCl补液建议（ml或g）",
      "formula": "所需K+ (mmol) = (目标-当前) × 体重 × 0.3"
    }},
    "calcium": {{
      "current_ca": 当前Ca++值,
      "normal_range": "1.10-1.35",
      "deficit": 缺口值,
      "calcium_recommendation": "补钙建议（葡萄糖酸钙ml或g）"
    }}
  }},
  "findings": [
    {{
      "category": "酸碱平衡/氧合/通气/电解质/血液学",
      "parameter": "指标名称",
      "value": 数值,
      "reference": "正常范围",
      "deviation": "偏离程度",
      "interpretation": "临床意义",
      "severity": "normal/mild/moderate/severe"
    }}
  ],
  "recommendations": [
    {{
      "priority": "高/中/低",
      "category": "治疗/监测/预防",
      "action": "具体措施",
      "detail": "详细说明（含剂量、时间、目标值）",
      "rationale": "医学依据"
    }}
  ],
  "alerts": [
    {{
      "level": "警告/注意/信息",
      "message": "警告信息",
      "recommendation": "建议措施"
    }}
  ],
  "safety_warning": "临床医师需根据实际失血量及循环波动动态调整",
  "disclaimer": "以上分析基于AI算法，仅供临床参考。具体治疗方案必须由具有执业资格的主治医生根据患者整体情况决定。本系统不承担任何医疗责任。"
}}}}

----

## 五、重要规则

1. **公式透明**: 所有计算必须说明计算依据
2. **缺失处理**: 如果没有体重，在酸碱纠正建议首行提示"请补充患者体重以获取精准药量计算"
3. **安全警示**: 所有计算结果后必须附带"临床医师需根据实际失血量及循环波动动态调整"
4. **数据驱动**: 所有建议必须有数据支撑
5. **宁缺毋滥**: 无法计算时返回null或提示，不准编造

只返回JSON，不要任何其他内容。"""


def _format_blood_gas(data: dict) -> str:
    """格式化血气数据"""
    fields = [
        ("pH", "ph"), ("PO2", "po2"), ("PCO2", "pco2"), ("Na+", "na"),
        ("K+", "k"), ("Ca++", "ca"), ("GLU", "glu"), ("LAC", "lac"),
        ("HCT", "hct"), ("HCO3-", "hco3_act"), ("BEecf", "be_ecf"),
        ("THbc", "thbc")
    ]
    return "\n".join([f"- **{name}**: {data.get(field, 'N/A')}" for name, field in fields if data.get(field) is not None])


def _format_vital_signs(data: dict) -> str:
    """格式化生命体征"""
    if not data:
        return "未提供"
    return f"""- 收缩压: {data.get('blood_pressure_systolic', 'N/A')} mmHg
- 舒张压: {data.get('blood_pressure_diastolic', 'N/A')} mmHg
- 心率: {data.get('heart_rate', 'N/A')} bpm
- SpO2: {data.get('spo2', 'N/A')}%"""


def _format_anesthesia(data: dict) -> str:
    """格式化麻醉参数"""
    if not data:
        return "未提供"
    return f"""- 麻醉方式: {data.get('anesthesia_type', 'N/A')}
- 气管插管: {data.get('intubated', 'N/A')}
- 用药: {data.get('medications', 'N/A')}"""


async def analyze_with_gemini(blood_gas_data: dict, weight: Optional[float] = None,
                               vital_signs: Optional[dict] = None,
                               anesthesia: Optional[dict] = None) -> dict:
    """使用 Gemini API 分析血气数据"""
    import httpx

    # 从环境变量读取 API Key
    api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 环境变量未设置")

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # 构造系统提示词（替换体重占位符）
    system_prompt = ANALYSIS_SYSTEM_PROMPT.replace("{weight}", str(weight) if weight else "未提供")

    # 构建用户提示词
    user_prompt = f"""请分析以下患者数据：

## 血气分析18项指标
{_format_blood_gas(blood_gas_data)}

## 生命体征
{_format_vital_signs(vital_signs)}

## 麻醉参数
{_format_anesthesia(anesthesia)}

## 患者体重
{weight} kg {'(可用于精确药量计算)' if weight else '(未提供，无法进行精确药量计算)'}

---

请按照上述系统提示词的格式，返回完整的JSON分析结果。

只返回JSON，不要任何其他内容。"""

    # 调用 Gemini API
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    request_body = {{
        "contents": [{{"parts": [{{"text": user_prompt}}]}}],
        "system_instruction": {{
            "parts": [{{"text": system_prompt}}]
        }},
        "generationConfig": {{
            "temperature": 0.3,
            "maxOutputTokens": 16384,
            "responseMimeType": "application/json"
        }}
    }}

    async with httpx.AsyncClient(timeout=120.0) as client:
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
        raise ValueError(f"JSON解析失败: {{str(e)}}，原始响应: {{result_text[:500]}}")

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

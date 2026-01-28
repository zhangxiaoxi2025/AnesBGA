"""
Gemini AI服务
使用HTTP API直接调用，支持gemini-2.5-flash
"""
import httpx
import json
import base64
import traceback
from typing import Optional, Dict, Any
from PIL import Image
import io
import asyncio
from ..core.config import settings


class GeminiService:
    """Gemini AI服务类 - 使用HTTP API调用"""

    def __init__(self):
        """初始化Gemini服务"""
        if not settings.gemini_api_key:
            raise ValueError("艹！Gemini API Key没配置，赶紧去.env文件里填上！")

        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        # Gemini 3 Flash 支持 1M token 上下文
        self.context_window = 1_000_000
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def ocr_blood_gas_report(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        OCR识别血气报告 - Vision API

        Args:
            image_bytes: 图片字节数据

        Returns:
            识别结果字典
        """
        try:
            # 打开图片
            image = Image.open(io.BytesIO(image_bytes))

            # 将图片转为base64
            buffered = io.BytesIO()
            image_format = image.format if image.format else 'JPEG'
            image.save(buffered, format=image_format, quality=95)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # MIME类型 - Python 3.13兼容写法
            if image_format == 'JPEG':
                mime_type = 'image/jpeg'
            elif image_format == 'PNG':
                mime_type = 'image/png'
            else:
                mime_type = 'image/jpeg'  # 默认用jpeg

            # 构造提示词 - 严格识别 18 个指标，严禁捏造
            prompt = """你是专业的血气分析报告 OCR 识别系统。

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
  "confidence": 0.0-1.0,
  "missing_fields": ["字段名列表，看不清的"]
}

【识别规则】
- 只提取图中明确显示的数值
- 看不清的指标必须返回 null，并在 missing_fields 中列出
- 如果单位不是标准单位（如 kPa 代替 mmHg），请注明或换算
- confidence 基于 OCR 清晰度和数据完整性综合评估

只返回 JSON，不要其他任何内容。"""

            # 极简请求体 - 避免 422 兼容性问题
            request_body = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": img_base64}}
                    ]
                }]
            }

            # 调用HTTP API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    params={"key": self.api_key},
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )

            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except:
                    pass
                return {
                    "success": False,
                    "data": None,
                    "error": f"API调用失败 ({response.status_code}): {error_detail}"
                }

            # 解析响应
            response_data = response.json()

            # 检查错误
            if "error" in response_data:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Gemini API错误: {response_data['error']['message']}"
                }

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

            # 调试：打印原始响应
            print(f"=== Gemini OCR Raw Response ===")
            print(f"Response length: {len(result_text)}")
            print(f"Response preview: {result_text[:200]}...")
            print(f"=== End Response ===")

            # 解析JSON
            try:
                ocr_result = json.loads(result_text)
            except json.JSONDecodeError as e:
                # 如果JSON解析失败，返回原始文本
                return {
                    "success": False,
                    "data": None,
                    "error": f"JSON解析失败: {str(e)}\n原始响应: {result_text[:500]}"
                }

            # 添加时间戳
            from datetime import datetime
            ocr_result["extracted_at"] = datetime.utcnow().isoformat()

            return {
                "success": True,
                "data": ocr_result,
                "error": None
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "data": None,
                "error": "API调用超时，请重试"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"OCR识别失败：{str(e)}"
            }

    async def analyze_blood_gas(
        self,
        blood_gas_data: Dict[str, Any],
        vital_signs: Optional[Dict[str, Any]] = None,
        anesthesia_params: Optional[Dict[str, Any]] = None,
        weight: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        AI分析血气数据，给出围术期量化建议

        Args:
            blood_gas_data: 血气数据（18项指标）
            vital_signs: 生命体征（可选）
            anesthesia_params: 麻醉参数（可选）
            weight: 患者体重（kg，用于药量计算）

        Returns:
            分析结果字典（含量化建议）
        """
        try:
            # 构造系统提示词
            system_prompt = f"""你是**资深主任麻醉医师**，拥有30年围术期管理经验。

【你的职责】
基于血气分析18项指标、患者体重和生命体征，给出**量化、具体、可执行**的临床建议。

{'【重要】患者体重: {weight} kg' if weight else '【注意】患者体重未提供，无法进行精确药量计算，请提示用户补充'}

---

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

---

## 二、贫血与输血指导

**目标值**: THbc ≥ 100 g/L（或根据手术风险调整70-100）
**红细胞悬液**: 1U ≈ 提升Hb 5-10 g/L

**量化计算**:
- 当前THbc: {blood_gas_data.get('thbc', '未识别')} g/L
- 目标THbc: 100 g/L
- 需要提升: max(0, 100 - 当前THbc) g/L
- 估算红细胞悬液: 向上取整(需要提升 / 7) U

**临床提醒**:
- 关注术中出血量
- 评估循环状态
- 氧供需平衡

---

## 三、电解质纠正

### K+ 补钾
- 正常范围: 3.5-5.5 mmol/L
- 公式: 所需K+ (mmol) = (目标差值) × 体重(kg) × 0.3
- KCl规格: 1g KCl ≈ 13.4 mmol K+

### Ca++ 补钙
- 正常范围: 1.10-1.35 mmol/L
- 葡萄糖酸钙: 1g ≈ 2.2 mmol Ca++
- 氯化钙: 1g ≈ 6.8 mmol Ca++

---

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

---

## 五、重要规则

1. **公式透明**: 所有计算必须说明计算依据（如"基于BE值为-10，体重60kg..."）
2. **缺失处理**: 如果没有体重，在酸碱纠正建议首行提示"请补充患者体重以获取精准药量计算"
3. **安全警示**: 所有计算结果后必须附带"临床医师需根据实际失血量及循环波动动态调整"
4. **数据驱动**: 所有建议必须有数据支撑
5. **宁缺毋滥**: 无法计算时返回null或提示，不准编造

只返回JSON，不要任何其他内容。"""

            # 构建用户提示词（只包含数据）
            user_prompt = f"""请分析以下患者数据：

## 血气分析18项指标
{self._format_blood_gas(blood_gas_data)}

## 生命体征
{self._format_vital_signs(vital_signs)}

## 麻醉参数
{self._format_anesthesia(anesthesia_params)}

## 患者体重
{weight} kg {'(可用于精确药量计算)' if weight else '(未提供，无法进行精确药量计算)'}

---

请按照上述系统提示词的格式，返回完整的JSON分析结果。

只返回JSON，不要任何其他内容。"""

            # 构建请求体 - 使用 system_instruction 传递系统提示词
            request_body = {
                "contents": [{
                    "parts": [{"text": user_prompt}]
                }],
                "system_instruction": {
                    "parts": [{"text": system_prompt}]
                },
                "generationConfig": {
                    "temperature": 0.3,  # 适中的温度保证专业性和创造性
                    "maxOutputTokens": 16384,  # 增加到16K，避免JSON截断
                    "topP": 0.9,
                    "responseMimeType": "application/json"
                }
            }

            # 调用HTTP API
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url,
                    params={"key": self.api_key},
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )

            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except:
                    pass
                return {
                    "success": False,
                    "data": None,
                    "error": f"API调用失败 ({response.status_code}): {error_detail}"
                }

            # 解析响应
            response_data = response.json()

            # 检查错误
            if "error" in response_data:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Gemini API错误: {response_data['error']['message']}"
                }

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

            # 打印 AI 原始响应，方便调试
            print(f"=== Gemini Analysis Raw Response ===")
            print(f"Response length: {len(result_text)}")
            print(f"Response preview: {result_text[:500]}...")
            print(f"=== End Response ===")

            # 解析JSON
            try:
                analysis_result = json.loads(result_text)
                # 添加模型信息
                from datetime import datetime
                if "model_info" not in analysis_result:
                    analysis_result["model_info"] = {
                        "model": self.model,
                        "context_window": self.context_window,
                        "analysis_timestamp": datetime.utcnow().isoformat()
                    }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "data": None,
                    "error": f"JSON解析失败: {str(e)}\n原始响应: {result_text[:500]}"
                }

            return {
                "success": True,
                "data": analysis_result,
                "error": None
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "data": None,
                "error": "AI分析超时，请重试"
            }
        except Exception as e:
            # 打印详细错误日志，方便调试
            print(f"!!! GEMINI SERVICE ERROR !!!")
            print(f"Traceback: {traceback.format_exc()}")
            print(f"Error: {str(e)}")
            print(f"Blood gas data keys: {list(blood_gas_data.keys()) if blood_gas_data else 'None'}")
            print(f"Weight: {weight}")
            print(f"!!! END ERROR !!!")
            return {
                "success": False,
                "data": None,
                "error": f"AI分析失败：{str(e)}"
            }

    def _format_blood_gas(self, data: Dict[str, Any]) -> str:
        """格式化血气数据为文本"""
        if not data:
            return "未提供血气数据"

        lines = ["### 血气分析指标"]
        # 核心指标
        if data.get("ph"):
            ph_val = float(data["ph"])
            ph_status = "异常" if ph_val < 7.35 or ph_val > 7.45 else "正常"
            lines.append(f"- pH: {data['ph']} ({ph_status})")
        if data.get("po2"):
            po2_val = float(data["po2"])
            po2_status = "异常" if po2_val < 80 else "正常"
            lines.append(f"- PO2: {data['po2']} mmHg ({po2_status})")
        if data.get("pco2"):
            pco2_val = float(data["pco2"])
            pco2_status = "异常" if pco2_val < 35 or pco2_val > 45 else "正常"
            lines.append(f"- PCO2: {data['pco2']} mmHg ({pco2_status})")
        # 电解质
        if data.get("na"):
            lines.append(f"- Na+: {data['na']} mmol/L")
        if data.get("k"):
            lines.append(f"- K+: {data['k']} mmol/L")
        if data.get("ca"):
            lines.append(f"- Ca++: {data['ca']} mmol/L")
        if data.get("ca_74"):
            lines.append(f"- Ca++7.4: {data['ca_74']} mmol/L")
        # 酸碱
        if data.get("hco3_act"):
            lines.append(f"- HCO3-: {data['hco3_act']} mmol/L")
        if data.get("hco3_std"):
            lines.append(f"- HCO3s: {data['hco3_std']} mmol/L")
        if data.get("ctco2"):
            lines.append(f"- ctCO2: {data['ctco2']} mmol/L")
        if data.get("be_ecf"):
            lines.append(f"- BEecf: {data['be_ecf']} mmol/L")
        if data.get("be_b"):
            lines.append(f"- BE(B): {data['be_b']} mmol/L")
        # 氧合
        if data.get("so2c"):
            so2c_val = float(data["so2c"])
            so2c_status = "异常" if so2c_val < 95 else "正常"
            lines.append(f"- SO2c: {data['so2c']}% ({so2c_status})")
        # 乳酸和血糖
        if data.get("lac"):
            lac_val = float(data["lac"])
            lac_status = "异常" if lac_val > 2.2 else "正常"
            lines.append(f"- LAC: {data['lac']} mmol/L ({lac_status})")
        if data.get("glu"):
            lines.append(f"- GLU: {data['glu']} mmol/L")
        # 血液学
        if data.get("hct"):
            lines.append(f"- HCT: {data['hct']}%")
        if data.get("thbc"):
            lines.append(f"- THbc: {data['thbc']} g/L")
        # 体温
        if data.get("temp"):
            lines.append(f"- Temp: {data['temp']} °C")

        if len(lines) == 1:
            return "未提供血气数据"

        # 添加识别置信度
        if data.get("confidence"):
            lines.append(f"\nOCR识别置信度: {data['confidence']:.1%}")

        return "\n".join(lines)

    def _format_vital_signs(self, data: Optional[Dict[str, Any]]) -> str:
        """格式化生命体征为文本"""
        if not data:
            return "未提供生命体征数据"

        lines = ["### 生命体征"]
        if data.get("blood_pressure_systolic") and data.get("blood_pressure_diastolic"):
            bp = f"{data['blood_pressure_systolic']}/{data['blood_pressure_diastolic']} mmHg"
            lines.append(f"- **血压**: {bp}")
        if data.get("heart_rate"):
            hr = data['heart_rate']
            hr_status = "⚠️ 异常" if hr < 60 or hr > 100 else "✅ 正常"
            lines.append(f"- **心率**: {hr} bpm {hr_status}")
        if data.get("temperature"):
            temp = data['temperature']
            temp_status = "⚠️ 异常" if temp < 36.0 or temp > 37.5 else "✅ 正常"
            lines.append(f"- **体温**: {temp} °C {temp_status}")
        if data.get("spo2"):
            spo2 = data['spo2']
            spo2_status = "⚠️ 异常" if spo2 < 95 else "✅ 正常"
            lines.append(f"- **SpO2**: {spo2}% {spo2_status}")
        if data.get("respiratory_rate"):
            rr = data['respiratory_rate']
            rr_status = "⚠️ 异常" if rr < 12 or rr > 20 else "✅ 正常"
            lines.append(f"- **呼吸频率**: {rr} 次/分 {rr_status}")

        return "\n".join(lines) if len(lines) > 1 else "未提供生命体征数据"

    def _format_anesthesia(self, data: Optional[Dict[str, Any]]) -> str:
        """格式化麻醉参数为文本"""
        if not data:
            return "未提供麻醉参数"

        lines = ["### 麻醉参数"]
        if data.get("anesthesia_type"):
            lines.append(f"- **麻醉方式**: {data['anesthesia_type']}")
        if data.get("intubated"):
            lines.append(f"- **气管插管**: {'是' if data['intubated'] else '否'}")
        if data.get("position"):
            lines.append(f"- **手术体位**: {data['position']}")
        if data.get("surgery_type"):
            lines.append(f"- **手术类型**: {data['surgery_type']}")
        if data.get("medications"):
            meds = data['medications']
            if isinstance(meds, list):
                lines.append(f"- **用药**: {', '.join(meds)}")
            else:
                lines.append(f"- **用药**: {meds}")
        if data.get("fluid_input"):
            lines.append(f"- **液体输入**: {data['fluid_input']} ml")
        if data.get("blood_loss"):
            lines.append(f"- **失血量**: {data['blood_loss']} ml")
        if data.get("urine_output"):
            lines.append(f"- **尿量**: {data['urine_output']} ml")
        if data.get("notes"):
            lines.append(f"- **备注**: {data['notes']}")

        return "\n".join(lines) if len(lines) > 1 else "未提供麻醉参数"


# 创建全局服务实例（延迟初始化，避免启动时API Key未加载）
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """获取Gemini服务实例（单例模式）"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service

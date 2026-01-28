# 🩺 麻醉科血气分析助手

AI驱动的围术期血气分析辅助决策系统（简化版）

## ✨ 特点

- 📸 **拍照/上传** - 手机拍照血气报告或上传图片
- 🔍 **OCR识别** - Gemini Vision API自动识别血气指标
- 🤖 **AI分析** - Gemini 2.0 Flash生成专业分析建议
- 💓 **可选补充** - 生命体征和麻醉参数录入
- 📱 **移动优先** - 响应式设计，手机网页使用
- 🚀 **无需登录** - 打开即用，不存储任何数据

## 🎯 使用流程

```
1. 打开网页
   ↓
2. 拍照/上传血气报告
   ↓
3. OCR自动识别
   ↓
4. （可选）填写生命体征和麻醉参数
   ↓
5. AI分析
   ↓
6. 查看结果（风险评估、临床发现、处理建议）
   ↓
7. 用完关闭，不留痕迹
```

## 🚀 快速开始

### 1. 前置要求

- **Node.js** 18+ （前端）
- **Python** 3.11+ （后端）
- **Gemini API Key** （**必需！**）

### 2. 获取Gemini API Key

1. 访问 https://aistudio.google.com/app/apikey
2. 点击"Create API Key"
3. 复制生成的Key

### 3. 配置环境

```bash
# 1. 复制环境变量文件
cp .env.example .env

# 2. 编辑.env文件，填入你的Gemini API Key
GEMINI_API_KEY=你的API_Key
```

### 4. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端启动成功后会显示：
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**访问后端API文档**：http://localhost:8000/docs

### 5. 启动前端

打开**新的终端**：

```bash
cd frontend
npm install
npm run dev
```

前端启动成功后会显示：
```
  ➜  Local:   http://localhost:5173/
```

**打开浏览器访问**：http://localhost:5173

## 📁 项目结构

```
.
├── frontend/                 # React前端（移动端优先）
│   ├── src/
│   │   ├── App.tsx           # 主页面（上传、OCR、填表、结果）
│   │   ├── App.css           # 样式
│   │   └── index.css         # Tailwind CSS
│   └── package.json
│
├── backend/                  # FastAPI后端（无数据库）
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   └── analysis.py   # OCR和AI分析API
│   │   ├── services/
│   │   │   └── gemini_service.py  # Gemini服务
│   │   ├── schemas/
│   │   │   └── blood_gas.py  # 数据模型
│   │   └── core/
│   │       └── config.py     # 配置管理
│   ├── main.py               # 应用入口
│   └── requirements.txt
│
├── .env.example              # 环境变量模板
└── README.md                 # 项目文档
```

## 🔌 API端点

### POST /api/v1/ocr
上传血气报告图片，OCR识别

**请求**：
- 文件：血气报告图片（jpg/jpeg/png）

**响应**：
```json
{
  "success": true,
  "ocr_result": {
    "ph": 7.35,
    "pco2": 45.2,
    "po2": 95.0,
    "hco3": 24.5,
    "base_excess": -2.1,
    "lactate": 1.2,
    "sao2": 97,
    "confidence": 0.92
  }
}
```

### POST /api/v1/analyze
AI分析血气数据

**请求**：
- `blood_gas_json` (JSON字符串) - 血气数据
- `vital_signs_json` (可选, JSON字符串) - 生命体征
- `anesthesia_json` (可选, JSON字符串) - 麻醉参数

**响应**：
```json
{
  "analysis_id": "temp_xxx",
  "assessment": {
    "acid_base": "代谢性酸中毒",
    "oxygenation": "氧合良好",
    "risk_level": "中风险"
  },
  "findings": [...],
  "recommendations": [...],
  "alerts": [...],
  "disclaimer": "建议仅供参考..."
}
```

## ⚙️ 配置说明

### .env配置项

```bash
# Gemini API配置（必需）
GEMINI_API_KEY=你的密钥
GEMINI_MODEL=gemini-2.0-flash-exp

# 文件上传配置
MAX_UPLOAD_SIZE=10485760          # 10MB
UPLOAD_DIR=./temp_uploads          # 临时文件目录
ALLOWED_FILE_TYPES=jpg,jpeg,png

# CORS配置
CORS_ORIGINS=*                     # 允许所有来源
```

## 🧪 测试

### 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/health

# 预期响应
{
  "status": "healthy",
  "service": "blood-gas-analyzer",
  "has_gemini_key": true
}
```

### 测试OCR

```bash
curl -X POST http://localhost:8000/api/v1/ocr \
  -F "file=@/path/to/blood_gas_report.jpg"
```

## 📱 移动端使用

1. 后端和前端都启动后
2. 手机和电脑在同一WiFi
3. 查看电脑的局域网IP（如：192.168.1.100）
4. 手机浏览器访问：`http://192.168.1.100:5173`

或使用ngrok/localtunnel暴露到公网：

```bash
npm install -g localtunnel
lt --port 5173
```

## ⚠️ 免责声明

**这是辅助决策工具，AI建议仅供临床参考！**

- 最终诊疗决策由医生负责
- 不替代专业医疗判断
- 数据不存储，用完即走
- 仅供学习和研究使用

## 🔧 故障排除

### 问题1：后端启动失败

**错误**：`ValueError: 艹！Gemini API Key没配置`

**解决**：检查`.env`文件是否存在且`GEMINI_API_KEY`已填写

### 问题2：前端无法连接后端

**错误**：`网络错误：Failed to fetch`

**解决**：
1. 检查后端是否在运行（http://localhost:8000/health）
2. 检查CORS配置
3. 检查防火墙设置

### 问题3：OCR识别失败

**错误**：`OCR识别失败`

**解决**：
1. 检查Gemini API Key是否有效
2. 检查图片清晰度
3. 确认是血气分析报告

### 问题4：AI分析很慢

**原因**：Gemini API响应时间取决于网络和服务器负载

**解决**：耐心等待，通常10-30秒

## 🚀 部署

### Railway部署（推荐）

1. 注册Railway账号：https://railway.app
2. 连接GitHub仓库
3. 设置环境变量`GEMINI_API_KEY`
4. 一键部署

详细部署文档即将补充...

## 👨‍💻 开发者

- 前端：React 18 + TypeScript + Tailwind CSS
- 后端：FastAPI + Python 3.11
- AI：Google Gemini 2.0 Flash API

## 📄 许可证

MIT License

---

**老王提醒**：
- 医疗应用，谨慎使用！
- Gemini API有免费额度，别tm浪费
- 有问题提issue，老王我看到就回

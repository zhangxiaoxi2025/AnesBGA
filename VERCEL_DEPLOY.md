# Vercel 部署指南

本项目已配置为可在 Vercel 上部署。

## 部署步骤

### 1. 准备工作

确保你已经安装了 Vercel CLI：
```bash
npm install -g vercel
```

或者你可以直接通过 GitHub 集成部署。

### 2. GitHub 上传代码

1. 在 GitHub 创建新仓库
2. 上传代码：
```bash
cd "/Users/emma/Desktop/list 1/simple 1"
git init
git add .
git commit -m "Initial commit: AnesGuardian blood gas analysis app"
git remote add origin https://github.com/你的用户名/anesguardian.git
git push -u origin main
```

### 3. Vercel 部署

**方式一：通过 Vercel 网站**

1. 访问 https://vercel.com
2. 使用 GitHub 登录
3. 点击 "Add New Project"
4. 选择刚才创建的 GitHub 仓库
5. 配置环境变量：
   - `GEMINI_API_KEY` = 你的 Gemini API Key
   - `GEMINI_MODEL` = gemini-2.5-flash
6. 点击 "Deploy"

**方式二：通过 Vercel CLI**

```bash
cd "/Users/emma/Desktop/list 1/simple 1"
vercel login
vercel --prod
```

### 4. 验证部署

部署完成后，访问 Vercel 提供的 URL，测试以下功能：

1. ✅ 上传血气报告图片
2. ✅ OCR 识别指标
3. ✅ AI 分析并给出建议

## 环境变量

在 Vercel 项目设置中配置以下环境变量：

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `GEMINI_API_KEY` | ✅ | - | Gemini API Key，从 https://aistudio.google.com/app/apikey 获取 |
| `GEMINI_MODEL` | ❌ | gemini-2.5-flash | Gemini 模型名称 |
| `MAX_UPLOAD_SIZE` | ❌ | 5242880 | 最大上传文件大小（字节） |

## 项目结构

```
/anesguardian
├── api/                    # Vercel Serverless Functions
│   ├── main.py            # FastAPI 应用
│   └── requirements.txt   # Python 依赖
├── frontend/              # React 前端
│   ├── src/              # 源代码
│   ├── dist/             # 构建输出（部署时）
│   └── package.json
├── vercel.json           # Vercel 配置文件
└── README.md
```

## 本地开发

```bash
# 1. 安装依赖
cd frontend && npm install

# 2. 启动前端开发服务器
npm run dev

# 3. 在另一个终端启动后端（如果需要本地测试）
cd /Users/emma/Desktop/list\ 1/simple\ 1
source venv/bin/activate
cd backend && python main.py
```

## 故障排除

### 1. API 返回 500 错误

检查 Vercel 环境变量中 `GEMINI_API_KEY` 是否正确配置。

### 2. CORS 错误

确保在 Vercel 项目设置中添加了正确的域名到允许列表。

### 3. 构建失败

确保 `frontend/dist` 目录已正确生成：
```bash
cd frontend && npm run build
```

## 技术栈

- **前端**: React + TypeScript + Vite + Tailwind CSS
- **后端**: FastAPI (Vercel Serverless Functions)
- **AI**: Google Gemini API (OCR + 血气分析)
- **部署**: Vercel

## 许可证

MIT License

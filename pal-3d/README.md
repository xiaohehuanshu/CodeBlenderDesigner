# Pal 3D - Frontend

AI for Making 建筑空间设计 Agent 的前端展示与交互界面。基于 React + Three.js 构建，支持 3D 模型在线预览、AI 对话式设计推演。

## 技术栈

- **React 19** + TypeScript
- **Vite 6** 构建
- **Tailwind CSS 4** 样式
- **React Three Fiber** + **@react-three/drei** 3D 渲染
- **React Router 7** 路由

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式（端口 3000）
npm run dev

# 生产构建
npm run build
npm run preview
```

## 文件格式要求

### 3D 模型

| 格式 | 用途 | 说明 |
|------|------|------|
| **GLB** (glTF Binary) | 3D 模型展示 | **唯一支持的 3D 格式**。通过 `useGLTF()` 加载，放置于 `public/` 目录 |

GLB 文件使用示例：

```tsx
import { useGLTF } from '@react-three/drei';

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

// 引用 public/ 目录下的 GLB 文件
<Model url="/test.glb" />
```

> 后端 LangGraph Agent 在生成 Blender 脚本后，会自动调用 Blender 导出 GLB 文件。前端通过 `/api/glb/{session_id}` 获取。

### 图片

| 格式 | 用途 |
|------|------|
| PNG / JPG / JPEG / WebP / BMP | 参考图片（后端 Node 3 视觉分析输入） |

前端展示图片使用标准 `<img>` 标签或 Unsplash 外链。

### 其他后端输入文件

| 格式 | 用途 | 说明 |
|------|------|------|
| **.blend** | Blender 项目文件 | 作为几何上下文输入，后端通过 Blender 后台模式提取几何信息 |
| **.md** (Markdown) | 设计规则文件 | 后端 Node 4 解析设计约束与规范（单文件 < 24KB） |
| **.py** | Blender Python 脚本 | 后端生成、前端可通过 API 下载 |

## 后端对接

### 架构关系

```
┌─────────────────┐         ┌──────────────────────────────┐
│   Pal 3D 前端    │  HTTP   │   LangGraph Agent 后端        │
│   (port 3000)   │ ──────> │   (FastAPI, port 8002/8000)  │
│                 │         │                              │
│  React + Three  │  SSE    │  8-Node LangGraph Pipeline   │
│  3D Viewer      │ <────── │  Blender Bridge + LLM        │
└─────────────────┘         └──────────────────────────────┘
```

### 开发环境代理

Vite 开发服务器已配置 API 代理（`vite.config.ts`）：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8002',  // 转发到后端
      changeOrigin: true,
    },
  },
}
```

启动后端时确保运行在 `localhost:8002`，前端所有 `/api/*` 请求会自动代理。

### 后端 API 接口

后端（`langgraph_agent/`）提供以下接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/generate` | 主接口：提交设计需求，触发 8 节点 Agent 流水线，生成 Blender 脚本 + GLB |
| `GET` | `/glb/{session_id}` | 下载生成的 GLB 3D 模型文件 |
| `GET` | `/script/{session_id}` | 下载生成的 Blender Python 脚本 |
| `GET` | `/trace/{session_id}` | 下载执行追踪日志（JSONL 格式） |
| `WebSocket` | `/ws/{session_id}` | 实时事件推送（生成进度、完成、错误） |
| `GET` | `/health` | 服务健康检查 |

### 核心请求：`POST /generate`

```json
{
  "user_input": "设计一个120平方米的茶室，包含半室外平台",
  "session_id": "session_1680000000",
  "thread_id": "thread_1680000000",
  "image_dir": ["/path/to/ref_images"],
  "markdown_path": ["/path/to/design_rules.md"],
  "blend_file": "/path/to/site_context.blend",
  "export_glb": true,
  "validate_generated_script": true,
  "node_switches": {
    "skip_internet_research": false,
    "skip_image_analysis": false,
    "skip_markdown_analysis": false,
    "skip_geometry_constraints": false
  }
}
```

**响应：**

```json
{
  "session_id": "session_1680000000",
  "route_decision": "new_generation",
  "generated_script_path": "/outputs/scripts/session_1680000000.py",
  "glb_path": "/outputs/generated_glb/session_1680000000.glb",
  "execution_log": ["..."],
  "errors": [],
  "consolidated_prompt": "...",
  "refined_design_brief": "..."
}
```

### 前端 Explore 页面的 SSE 接口

`Explore.tsx` 使用 SSE (Server-Sent Events) 流式接收 Agent 处理进度：

```
POST /api/chat/stream
Content-Type: application/json

{
  "messages": [{"role": "user", "content": "设计提示词"}],
  "session_id": "session_xxx",
  "thread_id": "thread_xxx"
}
```

**SSE 响应格式：**

```
data: {"type": "start"}
data: {"type": "progress", "content": "正在分析参考图片...", "node": "node3_image_analysis"}
data: {"type": "progress", "content": "正在生成脚本...", "node": "node7_script_generation"}
data: {"type": "complete", "content": "最终设计结果文本"}
data: {"type": "error", "content": "错误信息"}
```

> **注意：** 此 SSE 接口需要在后端额外实现或通过中间层适配。当前后端原生提供的是 `/generate` + WebSocket 模式。

### 后端配置

后端依赖以下环境变量（配置在 `langgraph_agent/.env`）：

```env
# LLM API Keys
DASHSCOPE_API_KEY=your_dashscope_key       # 通义千问（需求分析、视觉、搜索）
OPENAI_API_KEY=your_openai_key              # OpenAI 兼容 API（代码生成）
OPENAI_BASE_URL=https://your-api-endpoint/v1
OPENAI_MODEL=gpt-5.4

# Blender
BLENDER_EXECUTABLE=/path/to/blender.exe     # Blender 可执行文件路径

# Server
PALX_API_HOST=0.0.0.0
PALX_API_PORT=8002
PALX_CORS_ORIGINS=http://localhost:3000
```

### 后端启动

```bash
cd langgraph_agent
pip install -r requirements.txt
python ../main.py
```

## 项目结构

```
pal-3d/
├── public/
│   └── test.glb            # 默认 3D 模型文件
├── src/
│   ├── components/         # 通用组件（Navbar, Footer）
│   ├── data/
│   │   └── cases.ts        # 案例数据（硬编码）
│   ├── pages/
│   │   ├── Home.tsx        # 首页 + 3D 模型卡片
│   │   ├── Explore.tsx     # AI 对话设计（调用后端 API）
│   │   ├── Cases.tsx       # 案例列表
│   │   ├── CaseDetail.tsx  # 案例详情
│   │   ├── Viewer.tsx      # GLB 模型查看器
│   │   ├── Workflow.tsx    # 工作流说明
│   │   ├── Docs.tsx        # API 文档
│   │   ├── About.tsx       # 关于
│   │   └── ...
│   ├── App.tsx             # 路由入口
│   └── main.tsx            # 应用入口
├── vite.config.ts          # Vite 配置（含 API 代理）
├── .env.example            # 环境变量模板
└── package.json
```

## License

Private - All rights reserved.

## PalX Blender

PalX Blender 现在分成两层：

- `langgraph_agent/`
  - LangGraph 建筑空间设计 Agent
  - 负责需求收集、设计 brief 综合、Blender 脚本生成、运行时校验与 GLB 导出
- `making_frontend/`
  - Next.js 控制台
  - 负责会话输入、生成日志、GLB 浏览器预览、脚本与 trace 下载

## 当前完成状态

- 已保留原有 CLI 工作流，入口仍然是 `langgraph_agent/run_agent.py`
- 新增 Web API 封装，复用 CLI 的单轮运行逻辑
- 前端已改为对接真实后端能力：
  - `POST /generate`
  - `GET /ws/{session_id}`
  - `GET /glb/{session_id}`
  - `GET /script/{session_id}`
  - `GET /trace/{session_id}`
- 去掉了原先前端里未落地的 `update_params` / STL 占位逻辑

## 后端启动

1. 安装 Python 依赖

```bash
python -m pip install -e .\langgraph_agent
```

2. 复制环境变量模板

```bash
copy .\langgraph_agent\.env.example .\langgraph_agent\.env
```

3. 按需填写 API Key / Blender 路径

关键项：

- `DASHSCOPE_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `BLENDER_EXECUTABLE`

4. 启动 API

```bash
python .\main.py
```

默认监听：

- `http://localhost:8000`

## 前端启动

1. 安装依赖

```bash
cd .\making_frontend
npm install
```

2. 配置 API 地址

```bash
copy .\.env.local.example .\.env.local
```

默认值：

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

3. 启动前端

```bash
npm run dev
```

默认访问：

- `http://localhost:3000`

## 说明

- 后端 Web API 为当前前端控制台服务，但没有替代 CLI；CLI 仍适合单独调试 agent。
- 当前 API 为了避免 trace 全局状态互相污染，生成任务在服务端按单任务串行执行。
- GLB、脚本、trace 下载接口都按 `session_id` 解析最新产物。

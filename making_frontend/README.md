## PalX Frontend

PalX 前端是一个 Next.js 控制台，用来连接 `langgraph_agent` 的 Web API。

当前页面能力：

- 输入设计需求并触发后端生成
- 通过 WebSocket 显示当前会话状态
- 预览后端导出的 GLB
- 下载本轮脚本与 trace
- 展示 design brief 基线字段、精炼 brief 与 consolidated prompt

## 启动

1. 安装依赖

```bash
npm install
```

2. 配置 API 地址

```bash
copy .env.local.example .env.local
```

默认内容：

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

3. 启动开发环境

```bash
npm run dev
```

## 约定

- `NEXT_PUBLIC_API_BASE` 默认指向本地 Python API 服务
- 如果后端没有导出 GLB，中心视口会保持空场景
- 当前前端不再假设后端支持参数滑块、STL 导出或 `/update_params`

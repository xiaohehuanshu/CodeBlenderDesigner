# LangGraph 建筑空间设计 Agent

这个项目位于 `langgraph_agent/`，面向“需求收集 -> 多源信息整理 -> design_brief 综合 -> Blender 脚本生成 -> 多轮修改”的工作流。

当前推荐入口：

- `run_agent.py`

## 功能概览

工作流包含 7 个核心节点，每个节点都可独立开关：

1. `node1_collect_requirements`
   - 判断当前输入更像 `new_generation`、`modify_existing` 还是 `end`
2. `node2_internet_research`
   - 可选调用 Qwen 做联网研究
3. `node3_image_analysis`
   - 可选分析本地参考图
4. `node4_markdown_analysis`
   - 可选读取本地 Markdown 规则
5. `node5_geometry_constraints`
   - 可选从 Blender 场景中提取几何约束
6. `node6_prompt_synthesis`
   - 统一整理节点 1-5 的信息，形成当前轮 `design_brief`
7. `node7_script_generation`
   - 统一使用 GPT-5.4 ReAct agent 生成 Blender 脚本
   - ReAct 路径使用 `stream(values)`，终端会逐步打印 agent 消息和 tool 返回预览

交互式 `modify_existing` 轮次下，`node2`、`node3`、`node4` 默认直接复用首轮已生成的数据；
只有当用户当前轮明确要求“重新联网研究 / 重新分析图片 / 重新读取 Markdown 规则”时，才会真正重跑这些节点。

额外能力：

- 会话记忆保存在 `outputs/memory/<session_id>.json`
- 节点 2 的联网研究结果保存在 `outputs/internet_research/<session_id>/`
- 节点 7 支持多轮修改
- 终端会保留 `[NODE]` 级别进度日志
- 默认不打印发送给 GPT-5.4 的完整 prompt，避免干扰正常使用

## 目录结构

```text
langgraph_agent/
├── blender/
│   └── collect_geometry_context.py
├── inputs/
│   ├── images/
│   │   └── case_001/
│   └── rules/
│       ├── common/
│       └── case_001/
├── outputs/
│   ├── generated_scripts/
│   ├── internet_research/
│   ├── memory/
│   └── traces/
├── src/
│   └── langgraph_space_agent/
│       ├── blender_bridge.py
│       ├── cli.py
│       ├── config.py
│       ├── graph.py
│       ├── llm_clients.py
│       ├── nodes/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── node1_collect_requirements.py
│       │   ├── node2_internet_research.py
│       │   ├── node3_image_analysis.py
│       │   ├── node4_markdown_analysis.py
│       │   ├── node5_geometry_constraints.py
│       │   ├── node6_prompt_synthesis.py
│       │   └── node7_script_generation.py
│       ├── prompts.py
│       ├── state.py
│       └── utils.py
├── .env.example
├── prompt_case_001.json
├── request_case_001.json
├── pyproject.toml
├── README.md
├── clean_agent_workspace.py
├── run_agent.py
└── run_case_001.bat
```

说明：

- 节点实现已经从单个 `nodes.py` 拆分到 `src/langgraph_space_agent/nodes/`
- `graph.py` 仍通过 `from .nodes import DesignAgentNodes` 对外使用节点
- 目前正式编号为 `node5_geometry_constraints` 与 `node6_prompt_synthesis`；旧的 `node_switches` 键名仍会自动映射
- `prompt_case_001.json` 现在是可选首轮输入源，不再是默认必需项

## 环境准备

1. 安装依赖

```bash
pip install -e .
```

2. 复制环境变量模板

```bash
copy .env.example .env
```

建议至少配置：

- `DASHSCOPE_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `BLENDER_EXECUTABLE`

说明：

- 节点 1/2/4/5 默认使用 Qwen 文本模型
- 节点 3 默认使用 Qwen 多模态模型
- 节点 7 默认使用 OpenAI 兼容接口
- 某些 key 未配置时，对应节点会走降级逻辑，不会直接崩溃

## 配置优先级

优先级如下：

1. 命令行参数
2. `request_*.json`
3. `config.py`

也就是说：

- `request_case_001.json` 会覆盖 `config.py` 里的默认值
- 命令行会覆盖 `request_case_001.json`

## 首轮输入与模式开关

现在有两个独立开关：

1. 首轮输入来源
   - `use_prompt_file_for_first_turn`
   - `true`：首轮从 `prompt_file` 读取
   - `false`：启动后在终端 `input()` 输入
2. 单轮/多轮
   - `interactive`
   - `true`：首轮完成后进入后续修改交互
   - `false`：只运行一轮

默认示例 `request_case_001.json`：

```json
{
  "prompt_file": "d:/ON_GOING/vs_code/langgraph_agent/prompt_case_001.json",
  "use_prompt_file_for_first_turn": false,
  "session_id": "case_001",
  "thread_id": "case_001",
  "interactive": true,
  "image_dir": "d:/ON_GOING/vs_code/langgraph_agent/inputs/images/case_001",
  "markdown_path": [
    "d:/ON_GOING/vs_code/langgraph_agent/inputs/rules/common",
    "d:/ON_GOING/vs_code/langgraph_agent/inputs/rules/case_001"
  ],
  "geometry_context_path": null,
  "blender_executable": "E:/Software/Blender/blender.exe",
  "blend_file": "d:/ON_GOING/vs_code/langgraph_agent/outputs/blend_files/case_001_working.blend",
  "output_dir": "d:/ON_GOING/vs_code/langgraph_agent/outputs",
  "auto_execute_generated_script": false,
  "node_switches": {
    "global_enabled": true,
    "node1_collect_requirements": true,
    "node2_internet_research": true,
    "node3_image_analysis": false,
    "node4_markdown_analysis": true,
    "node5_geometry_constraints": false,
    "node6_prompt_synthesis": true,
    "node7_script_generation": true
  }
}
```

含义：

- `use_prompt_file_for_first_turn: false`
  - 程序启动后要求用户在终端输入首轮设计条件
- `use_prompt_file_for_first_turn: true`
  - 程序首轮从 `prompt_file` 指向的 JSON 中读取 `user_input`
- `interactive: true`
  - 首轮完成后继续进入修改交互
- `interactive: false`
  - 单轮运行

### `blend_file` 怎么配

- `blend_file` 指的是 Blender 场景文件，也就是你的 `.blend` 工作文件，不是 Python 项目文件。
- 如果当前任务是 `new_generation`，没有 `blend_file` 也可以运行；这时脚本预检会退回空白 Blender 场景。
- 如果当前任务是 `modify_existing`，强烈建议配置 `blend_file`；这样脚本会在真实场景上下文中做后台预检，更容易发现对象名、集合、材质、已有体块关系等问题。
- 推荐把当前正在修改的方案场景保存到 `request_case_001.json` 里配置的路径，例如：
  - `d:/ON_GOING/vs_code/langgraph_agent/outputs/blend_files/case_001_working.blend`
- 一旦该文件存在，`modify_existing` 的预检会优先基于这个场景文件运行。
- 为了安全，预检不会直接在原始 `.blend` 上运行；当前实现会先复制一个临时副本，再在副本上执行脚本验证。
- 如果 `blend_file` 路径已配置但文件还不存在，系统会自动回退到空白场景预检。

## 启动方式

### 最简单的方式

如果项目目录下存在 `request_case_001.json`，可以直接运行：

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py
```

### 单轮运行

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py --request-file d:\ON_GOING\vs_code\langgraph_agent\request_case_001.json --single-turn
```

如需临时跳过生成脚本的 Blender 预检，可以加：

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py --request-file d:\ON_GOING\vs_code\langgraph_agent\request_case_001.json --single-turn --skip-script-validation
```

### 强制交互模式

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py --request-file d:\ON_GOING\vs_code\langgraph_agent\request_case_001.json --interactive
```

### 强制首轮从 `prompt_file` 读取

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py --request-file d:\ON_GOING\vs_code\langgraph_agent\request_case_001.json --use-prompt-file-first-turn
```

### 强制首轮走终端输入

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py --request-file d:\ON_GOING\vs_code\langgraph_agent\request_case_001.json --stdin-first-turn
```

### 直接传入首轮 prompt

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py --prompt "生成一个现代感文化中心体块方案" --session-id case_001
```

说明：

- `--prompt` 优先级最高，会直接作为首轮输入
- `--prompt-file` 会把对应文件作为首轮输入源，并自动等价于 `--use-prompt-file-first-turn`
- 如果没有 `--prompt`，也没有启用 `prompt_file` 首轮，则程序会在启动后等待终端输入

### 临时关闭节点

```bash
python d:\ON_GOING\vs_code\langgraph_agent\run_agent.py --request-file d:\ON_GOING\vs_code\langgraph_agent\request_case_001.json --disable-node2 --disable-node3
```

## 多轮修改怎么输入

如果开启的是交互模式：

1. 程序先拿到首轮设计条件
2. 先跑完第一轮脚本生成
3. 然后进入后续修改交互

例如：

```text
You> 生成一个文化中心体块方案，要求有现代感和几何纯粹性
You> 入口再明确一些，保留当前主体体块关系
You> 顶部收分克制一点，减少侧向挑出
You> 先别动基座，只调整主楼比例
You> end
```

这些后续输入会再次进入 `node1` 判断，并在 `modify_existing` 模式下继续生成下一轮脚本。

如果不用交互模式，也可以：

- 重新运行程序并重新输入首轮设计条件
- 或者用 `--prompt "..."` / `--prompt-file ...`

## 当前 prompt 组织方式

现在真正送给 GPT-5.4 的上下文，主要分为几类：

1. 固定的 `system_prompt`
   - 放角色、硬性约束和输出格式要求
2. 轻量 `user_prompt`
   - 会把“当前轮用户输入”放在最前面，并显式标为最高优先级
3. `design_brief`
   - 当前轮唯一权威设计要求
4. `previous_script_overview`
   - 仅在 `modify_existing` 且确有需要时使用
5. `search_previous_script`
   - 仅在明确需要某段旧代码时按需取片段
6. `get_last_run_status` / `get_recent_conversation_summary`
   - 仅在确有连续性需求时再调用

默认不会把以下内容整份塞进同一轮请求：

- 整份旧脚本
- 整份 session memory
- 多轮历史 `design_brief` 套娃

### 当前轮用户输入优先级

## Node7 代码生成策略更新

当前 `node7_script_generation` 已改成“先计划、再分批生成”的主路径，而不是单次长输出整份脚本：

1. 先对 `node6` 产出的统一 `design_brief` 做一次 Qwen 精炼。
   - 目标是去重、压缩、保留刚性约束和当前轮最高优先级用户输入。
   - 如果 Qwen 不可用或精炼结果异常，会自动回退到原始 `design_brief`。
2. 再让 GPT 先输出一个很短的 planner JSON。
   - planner 只负责判断适合分成 `1 / 2 / 3` 段，并写清每段职责、完成标准、预计长度。
3. 最后程序按 planner 结果逐段生成代码片段。
   - 简单任务可以 1 段完成。
   - 一般任务默认 2 段。
   - 更复杂的 `modify_existing` 或需要明显分层收尾的任务可以走 3 段。

这样做的目的：

- 降低单次请求体积和单次响应时长，减少 60 秒附近的网关超时风险。
- 让当前轮用户输入在最终代码生成阶段更靠前、更明确。
- 如果后续某一段失败，也能回退到“上一段已通过编译的脚本”，而不是整轮完全失败。

`node7` 仍然保留：

- 本地静态校验
- Blender 运行时校验
- 校验失败时跳过自动执行
- 全部脚本落盘到 `outputs/generated_scripts/`

node7 现在会在 prompt 里明确声明：

- 当前轮用户输入是最高优先级
- 如果它和旧摘要、旧脚本、连续性信息冲突，优先服从当前轮用户输入

这样做是为了避免多轮修改时，最新一轮要求被历史上下文淹没。

### node7 当前策略

- 先用 Qwen 精炼 `design_brief`
- 再用 GPT 输出 planner JSON，决定分成 `1 / 2 / 3` 段
- 程序端会对 planner 结果做仲裁
  - 例如 planner 选了 `1` 段，但当前是 `modify_existing`、有几何约束、或上下文明显偏复杂时，会自动提升到 `2` 段
- 在 `modify_existing` 下，node7 会额外把“旧脚本概览 + 旧脚本关键片段”一起提供给模型，用来增强方案延续性
- 每一段生成完都会先本地组装成完整脚本并做 Python 编译检查
- 生成脚本写盘后，默认会先做 Python 编译检查，并在可用时追加 Blender 后台预检
- 如果 Blender 预检失败，错误会写入 `validation_report`，且会阻止自动执行继续运行错误脚本
- 如果 planner 或分段生成失败，则退回占位脚本，避免整轮崩溃

## design_brief 当前策略

`design_brief` 现在是单层结构，核心包括：

- 当前活跃指令
  - 当前轮用户修改要求优先级最高
- 当前基线简报
  - 来自上一轮有效 `design_brief` 的基线字段
- 本轮更新摘要
  - 只记录本轮哪些字段有更新

补充规则：

- `new_generation` 不再把上一轮项目的基线字段当作当前轮默认种子
- 如果当前轮没有明确要求住宅、别墅或其他居住类项目，综合结果默认保持在通用“建筑”层级，不再默认推成住宅/别墅

在 `modify_existing` 且节点 1-4/6 没有新增上下文时：

- 会尽量复用上一轮基线
- 不再重复嵌套旧 `design_brief`

## 调试输出

终端默认会保留这些关键信息：

- `[NODE]`
  - 节点开始、跳过、完成、tool call 等进度
- `[GPT-5.4 PROMPT]`
  - 仅在显式开启 debug 时打印发给 GPT-5.4 的完整请求内容

如果想临时开启完整 prompt 打印，可以设置：

```bash
set PRINT_LLM_PROMPTS=true
```

如果想临时开启 CLI 启动诊断，也可以设置：

```bash
set PRINT_CLI_DIAGNOSTICS=true
```

当前不再默认打印：

- `[RUN]` 级别整轮开始/结束日志
- 大量无关 metrics 噪声
- `[CLI] Startup configuration` 这类启动诊断信息

## 输出位置

### 生成脚本

```text
outputs/generated_scripts/
```

### trace

```text
outputs/traces/<session_id>/
```

### memory

```text
outputs/memory/<session_id>.json
```

### 联网研究结果

```text
outputs/internet_research/<session_id>/
├── node2_summary_latest.md
├── node2_summary_latest.json
└── history/
    ├── <timestamp>_node2.md
    └── <timestamp>_node2.json
```

## Blender 几何约束说明

`blender/collect_geometry_context.py` 负责：

- 识别编辑模式下被选中的面
- 计算设计范围的包围盒、中心、面积和法向信息
- 识别未选中的周边环境几何
- 输出给节点 6 / 节点 7 使用的 JSON 上下文

`BLENDER_EXECUTABLE` 只会在需要几何导出或自动执行脚本时使用，不会在每次运行时都强制启动 Blender。

## 一键清理

如果想清空旧的生成脚本、trace、memory、联网研究结果和 Python 缓存，可以运行：

```bash
python d:\ON_GOING\vs_code\langgraph_agent\clean_agent_workspace.py --yes
```

默认会清理：

- `outputs/generated_scripts`
- `outputs/internet_research`
- `outputs/memory`
- `outputs/traces`
- 项目内的 `__pycache__`、`.pyc` 等缓存

默认不会删除：

- `inputs/images`
- `inputs/rules`
- `.env`
- `prompt_case_001.json`
- `request_case_001.json`

如果确实想把输入资料一起清空，再显式加：

```bash
python d:\ON_GOING\vs_code\langgraph_agent\clean_agent_workspace.py --include-inputs --yes
```

如果想临时只删一部分，可以用 `--only`：

```bash
python d:\ON_GOING\vs_code\langgraph_agent\clean_agent_workspace.py --only generated_scripts,memory,traces --yes
```

如果想在默认基础上排除一部分，可以用 `--skip`：

```bash
python d:\ON_GOING\vs_code\langgraph_agent\clean_agent_workspace.py --skip compiled_python,cache_dirs --yes
```

## VS Code

也可以直接在 VS Code 里运行 [run_agent.py](d:/ON_GOING/vs_code/langgraph_agent/run_agent.py)。

项目里已经提供了 [launch.json](d:/ON_GOING/vs_code/langgraph_agent/.vscode/launch.json)。

## 备注

- `run_agent.py` 是当前唯一推荐入口
- 默认建议把多轮修改放在交互模式里完成
- 如果继续压缩 prompt，优先方向仍然是“按需取上下文”，而不是把整份历史继续塞回主请求

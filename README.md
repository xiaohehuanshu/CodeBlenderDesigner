# LangGraph 建筑空间设计 Agent

一个面向建筑体块与空间方案生成的 LangGraph 工作流。项目把需求收集、多源上下文整理、`design_brief` 综合、Blender 脚本生成、运行时校验和多轮修改串成了一条可配置流水线。

当前推荐入口是 `run_agent.py`。

## 项目在做什么

这套 Agent 主要解决的是下面这类流程：

1. 输入首轮设计要求，或者基于已有方案继续修改。
2. 按需读取联网研究、参考图片、Markdown 规则、几何约束。
3. 综合出当前轮唯一有效的 `design_brief`。
4. 生成 Blender Python 脚本。
5. 对脚本做静态检查、Blender 运行时校验、失败诊断与自动修复。
6. 在交互模式下继续接收下一轮修改要求。

`node1` 会先判断当前输入属于哪一类：

- `new_generation`
- `modify_existing`
- `end`

## 工作流节点

当前图中共有 8 个节点，执行顺序定义在 `src/langgraph_space_agent/graph.py`：

1. `node1_collect_requirements`
   - 识别当前轮任务类型，决定是首轮生成、继续修改还是结束。
2. `node2_internet_research`
   - 按需调用 Qwen 做联网研究，结果写入 `outputs/internet_research/`。
3. `node3_image_analysis`
   - 分析本地参考图，提取体块、风格、空间特征等信息。
4. `node4_markdown_analysis`
   - 读取本地 Markdown 规则或约束说明。
5. `node5_geometry_constraints`
   - 从 Blender 场景或外部 JSON 中提取几何上下文。
6. `node6_prompt_synthesis`
   - 汇总前置节点信息，形成当前轮 `design_brief`。
7. `node7_script_generation`
   - 用 GPT 风格代码生成链路产出 Blender 脚本，并先做静态校验。
8. `node8_runtime_debug`
   - 对脚本做 Blender 运行时验证；失败时尝试诊断、快速修复和自动补丁修复；通过后可按配置自动执行脚本。

交互式 `modify_existing` 模式下，部分前置上下文会优先复用上一轮结果，而不是每一轮都从头重算。

## 核心特性

- 多轮交互修改：首轮生成后可以持续输入修订要求，直到输入 `end`。
- 上下文可裁剪：联网研究、图片分析、规则分析、几何约束都能单独开关。
- `design_brief` 统一收口：当前轮用户输入会被提升为最高优先级。
- 代码生成分阶段：生成链路会优先控制上下文长度和失败回退。
- 运行时自检：支持 Python 编译检查、Blender 后台校验、失败诊断与自动修复。
- 会话记忆落盘：多轮修改过程会写入 `outputs/memory/<session_id>.json`。
- Trace 落盘：每轮运行会生成 trace，便于回放和调试。

## 快速开始

下面默认你已经进入项目根目录 `langgraph_agent/`。

### 1. 安装依赖

```bash
python -m pip install -e .
```

如果启动时提示缺少依赖，也可以再次执行这条命令。

### 2. 手动创建 `.env`

当前仓库里没有现成的 `.env.example`，需要你自己新建一个 `.env` 文件。最常用的环境变量如下：

```env
DASHSCOPE_API_KEY=your_dashscope_key
OPENAI_API_KEY=your_openai_compatible_key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_MODEL=gpt-5.4
BLENDER_EXECUTABLE=E:/Software/Blender/blender.exe
```

常见说明：

- `DASHSCOPE_API_KEY`
  - 供 Qwen 相关节点使用，主要覆盖 node1 到 node6 的文本/多模态分析链路。
- `OPENAI_API_KEY`
  - 供脚本生成和运行时修复链路使用。
- `OPENAI_BASE_URL`
  - 默认值写在 `src/langgraph_space_agent/config.py`。
- `BLENDER_EXECUTABLE`
  - 用于几何导出、脚本运行时校验和自动执行；如果不配置，系统会尝试自动探测 Windows 常见安装路径。

### 3. 修改请求文件

默认示例文件是 `request_case_001.json`。

建议至少确认这些字段：

- `session_id`
- `thread_id`
- `interactive`
- `image_dir`
- `markdown_path`
- `blend_file`
- `output_dir`
- `auto_execute_generated_script`
- `node_switches`

推荐写法示例：

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
  "blend_file": "d:/ON_GOING/vs_code/langgraph_agent/outputs/blend_files/case_001_working.blend",
  "output_dir": "d:/ON_GOING/vs_code/langgraph_agent/outputs",
  "auto_execute_generated_script": false,
  "node_switches": {
    "global_enabled": true,
    "node1_collect_requirements": true,
    "node2_internet_research": false,
    "node3_image_analysis": true,
    "node4_markdown_analysis": true,
    "node5_geometry_constraints": true,
    "node6_prompt_synthesis": true,
    "node7_script_generation": true,
    "node8_runtime_debug": true
  }
}
```

兼容性说明：

- 旧键名 `node5_prompt_synthesis` 和 `node6_geometry_constraints` 仍会自动映射到新键名。
- 最终优先级是：命令行参数 > `request_*.json` > `config.py` 默认值。

### 4. 运行

最简单的方式：

```bash
python run_agent.py
```

如果没有传 `--request-file` / `--prompt` / `--prompt-file`，入口程序会默认尝试读取当前目录下的 `request_case_001.json`。

## 常用启动方式

### 使用请求文件运行

```bash
python run_agent.py --request-file request_case_001.json
```

### 强制单轮运行

```bash
python run_agent.py --request-file request_case_001.json --single-turn
```

### 强制进入交互模式

```bash
python run_agent.py --request-file request_case_001.json --interactive
```

### 直接传入首轮 prompt

```bash
python run_agent.py --prompt "生成一个现代感文化中心体块方案" --session-id case_001
```

### 首轮从 `prompt_file` 读取

```bash
python run_agent.py --request-file request_case_001.json --use-prompt-file-first-turn
```

或者直接：

```bash
python run_agent.py --prompt-file prompt_case_001.json --session-id case_001
```

### 强制首轮走终端输入

```bash
python run_agent.py --request-file request_case_001.json --stdin-first-turn
```

### 临时跳过脚本运行时校验

```bash
python run_agent.py --request-file request_case_001.json --skip-script-validation
```

### 临时关闭部分节点

```bash
python run_agent.py --request-file request_case_001.json --disable-node2 --disable-node5
```

也可以直接关闭整条工作流：

```bash
python run_agent.py --request-file request_case_001.json --disable-all-nodes
```

## 多轮修改模式

当 `interactive=true` 或命令行显式传入 `--interactive` 时：

1. 程序先完成首轮生成。
2. 然后进入交互循环。
3. 你每输入一条修订要求，都会再触发一轮 `modify_existing` 判断与脚本生成。
4. 输入 `end` 结束会话。

示例：

```text
You> 生成一个文化中心体块方案，强调现代感与几何纯粹性
You> 入口再明确一些，保留当前主体体块关系
You> 顶部收分克制一点，减少侧向挑出
You> 先别动基座，只调整主楼比例
You> end
```

## `blend_file` 应该怎么配

`blend_file` 指向的是 Blender 场景文件，不是 Python 文件。

建议这样理解：

- 如果当前轮是 `new_generation`
  - 没有 `blend_file` 也能运行。
  - 运行时校验会回退到空白场景或仅做 Python 编译检查。
- 如果当前轮是 `modify_existing`
  - 强烈建议提供 `blend_file`。
  - 运行时校验会优先在该场景副本上执行，以减少直接污染原始工程的风险。

推荐把当前正在修改的方案保存到：

```text
outputs/blend_files/<session_id>_working.blend
```

## 默认配置和实际启用规则

框架默认值定义在 `src/langgraph_space_agent/config.py` 中。

当前默认节点开关是：

- `node1_collect_requirements = true`
- `node2_internet_research = false`
- `node3_image_analysis = true`
- `node4_markdown_analysis = true`
- `node5_geometry_constraints = true`
- `node6_prompt_synthesis = true`
- `node7_script_generation = true`
- `node8_runtime_debug = true`

但如果你传入了 `request_case_001.json`，以请求文件中的配置为准。

## 输出目录

常见输出都在 `outputs/` 下：

- `outputs/generated_scripts/`
  - 生成的 Blender Python 脚本。
- `outputs/blend_files/`
  - 建议存放当前工作中的 `.blend` 文件。
- `outputs/internet_research/<session_id>/`
  - 联网研究结果与历史记录。
- `outputs/memory/<session_id>.json`
  - 会话记忆和上一轮结果摘要。
- `outputs/traces/<session_id>/`
  - 每轮 trace 事件日志。

## 调试输出

默认终端会保留 `[NODE]` 级别的进度信息。

如果你想额外打印完整 LLM 请求内容：

```bash
set PRINT_LLM_PROMPTS=true
```

如果你想打印 CLI 启动诊断：

```bash
set PRINT_CLI_DIAGNOSTICS=true
```

如果你想打印最终结果摘要：

```bash
set PRINT_CLI_FINAL_RESULT_SUMMARY=true
```

## 目录结构

下面是和当前代码更贴近的精简结构：

```text
langgraph_agent/
├── blender/
│   └── collect_geometry_context.py
├── inputs/
│   ├── images/
│   └── rules/
├── outputs/
│   ├── blend_files/
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
│       ├── state.py
│       ├── tracing.py
│       ├── utils.py
│       └── nodes/
│           ├── base.py
│           ├── node1_collect_requirements.py
│           ├── node2_internet_research.py
│           ├── node3_image_analysis.py
│           ├── node4_markdown_analysis.py
│           ├── node5_geometry_constraints.py
│           ├── node6_brief_refinement.py
│           ├── node6_prompt_synthesis.py
│           ├── node7_script_generation.py
│           └── node8_runtime_debug.py
├── .vscode/
│   └── launch.json
├── clean_agent_workspace.py
├── prompt_case_001.json
├── pyproject.toml
├── README.md
├── request_case_001.json
└── run_agent.py
```

## VS Code 运行

项目已经提供了 `.vscode/launch.json`，可以直接在 VS Code 中使用：

- `LangGraph Agent: Single Run (Recommended)`
- `LangGraph Agent: Interactive (Recommended)`

## 清理工作区

`clean_agent_workspace.py` 可以帮助你清理历史输出和缓存。

默认清理：

- `outputs/generated_scripts`
- `outputs/internet_research`
- `outputs/memory`
- `outputs/traces`
- `__pycache__`
- `.pyc` / `.pyo`

默认不会清理：

- `inputs/images`
- `inputs/rules`
- `.env`

常用命令：

```bash
python clean_agent_workspace.py --yes
```

只预览，不真正删除：

```bash
python clean_agent_workspace.py --dry-run
```

连输入资料一起清理：

```bash
python clean_agent_workspace.py --include-inputs --yes
```

只清理指定项目：

```bash
python clean_agent_workspace.py --only generated_scripts,memory,traces --yes
```

查看所有支持的清理目标：

```bash
python clean_agent_workspace.py --list-targets
```

## 适合什么时候用这个项目

这套工作流更适合下面几类场景：

- 你已经有较明确的空间或体块设计要求，希望快速生成 Blender 建模脚本。
- 你希望把联网研究、图片分析、规则约束和几何上下文一起纳入生成过程。
- 你需要围绕同一个方案做多轮、连续、可追踪的修改。
- 你希望脚本生成后还能自动做一次 Blender 运行时自检，而不是只停留在文本层面。

## 备注

- `run_agent.py` 是当前唯一推荐入口。
- 如果你准备提交到 GitHub，README 里这套命令默认都以项目根目录为执行位置。
- 如果后续继续精简 prompt，优先方向仍然应该是“按需取上下文”，而不是把整份历史全部塞回模型输入。

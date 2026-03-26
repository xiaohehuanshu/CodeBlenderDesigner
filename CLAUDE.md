# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PalX Blender — a LangGraph-based AI agent for architectural space design that generates Blender Python scripts from natural language design requirements. The main code lives in `langgraph_agent/`. `Forehead/` and `docs/` are currently empty placeholder directories.

## Development Commands

All commands run from the `langgraph_agent/` directory.

```bash
# Install dependencies (editable install)
pip install -e .

# Run the agent (uses request_case_001.json if present)
python run_agent.py

# Single-turn run
python run_agent.py --request-file request_case_001.json --single-turn

# Skip Blender script validation
python run_agent.py --single-turn --skip-script-validation

# Interactive multi-turn mode
python run_agent.py --interactive

# Pass prompt directly
python run_agent.py --prompt "生成一个现代感文化中心体块方案" --session-id case_001

# Disable specific nodes
python run_agent.py --disable-node2 --disable-node3

# Clean outputs (traces, memory, generated scripts, caches)
python clean_agent_workspace.py --yes

# Clean everything including inputs
python clean_agent_workspace.py --include-inputs --yes
```

## Architecture

### Graph Pipeline (8 nodes, linear with one conditional exit)

```
START → node1 → [should_end?] → END
              → node2 → node3 → node4 → node5 → node6 → node7 → node8 → END
```

- **node1** (`node1_collect_requirements`): Classifies input as `new_generation`, `modify_existing`, or `end`
- **node2** (`node2_internet_research`): Optional web research via Qwen with search
- **node3** (`node3_image_analysis`): Optional reference image analysis via Qwen vision model
- **node4** (`node4_markdown_analysis`): Optional local markdown rules ingestion
- **node5** (`node5_geometry_constraints`): Optional Blender scene geometry extraction
- **node6** (`node6_prompt_synthesis` + `node6_brief_refinement`): Synthesizes all context into a single `design_brief`
- **node7** (`node7_script_generation`): Multi-stage Blender script generation (planner → staged generation → compile check)
- **node8** (`node8_runtime_debug` + `node8_debug_diagnosis` + `node8_debug_repair`): Blender runtime validation and auto-repair

Each node can be independently toggled via `node_switches`. In `modify_existing` mode, nodes 2-4 reuse previous results unless the user explicitly requests a refresh.

### Key Design Patterns

**Mixin-based node composition**: `DesignAgentNodes` (in `nodes/__init__.py`) is composed from 11 mixins plus a base class. All nodes share the same `self.settings`, `self.qwen`, `self.openai_chat_model`, and `self.openai_codegen` clients initialized in `DesignAgentNodesBase`.

**State graph**: Uses LangGraph's `StateGraph` with `AgentState` (a `TypedDict`). State flows linearly through nodes; `execution_log` and `errors` use `Annotated[list, operator.add]` for append-only accumulation.

**Two LLM backends**:
- **Qwen** (DashScope): Nodes 1, 2, 4, 5, 6 text tasks; node 3 vision tasks
- **OpenAI-compatible** (default GPT-5.4): Node 7 script generation via ReAct agent with tool use

**Node7 staged generation**: Instead of a single long output, it plans → generates in 1-3 segments → assembles → validates (Python compile check, then optional Blender runtime validation).

### Configuration Priority

CLI args > `request_*.json` > `config.py` (which reads from `.env`)

### Key Directories

- `src/langgraph_space_agent/` — Core package (graph, nodes, LLM clients, state, config, tracing)
- `blender/` — Blender helper scripts (geometry context exporter)
- `inputs/images/` — Reference images per case
- `inputs/rules/` — Markdown design rules (common + per-case)
- `outputs/generated_scripts/` — Generated Blender scripts
- `outputs/memory/` — Session memory JSON files
- `outputs/traces/` — JSONL trace logs

## Environment Variables

Required keys in `.env` (rooted at `langgraph_agent/../.env`):
- `DASHSCOPE_API_KEY` — Qwen API (nodes 1-6)
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` — GPT-5.4 compatible endpoint (node 7)
- `BLENDER_EXECUTABLE` — Path to blender.exe (for validation/execution)
- `OPENAI_MODEL` — Model name (default: `gpt-5.4`)

Debug toggles:
- `PRINT_LLM_PROMPTS=true` — Print full GPT-5.4 request payloads
- `PRINT_CLI_DIAGNOSTICS=true` — Print startup configuration
- `PRINT_CLI_FINAL_RESULT_SUMMARY=true` — Print detailed result at end

## Language

Code comments, prompts, and user-facing text are primarily in Chinese (中文). The `design_brief` and all LLM interactions use Chinese. CLI help text and docstrings may be in English.

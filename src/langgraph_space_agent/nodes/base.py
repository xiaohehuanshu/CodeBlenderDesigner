from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from ..config import AgentSettings, NodeSwitches
from ..llm_clients import OpenAICodegenClient, OpenAICompatibleChatModel, QwenClient
from ..tracing import trace_event
from ..utils import clean_code_fence, compact_text, merge_node_result, text_stats


DESIGN_BRIEF_MAX_CHARS = 3500
DESIGN_BRIEF_FIELD_SPECS = (
    ("prompt_collection", "项目目标", 600),
    ("research_summary", "联网研究总结", 240),
    ("image_summary", "图片风格总结", 240),
    ("markdown_summary", "Markdown 文本总结", 240),
    ("geometry_summary", "几何约束", 1500),
)
DESIGN_BRIEF_FIELD_LIMITS = {
    field_key: max_chars for field_key, _label, max_chars in DESIGN_BRIEF_FIELD_SPECS
}
PROMPT_COLLECTION_MAX_CHARS = DESIGN_BRIEF_FIELD_LIMITS["prompt_collection"]
MAX_ACTIVE_USER_INSTRUCTIONS = 3
ACTIVE_USER_INSTRUCTION_MAX_CHARS = 240
ACTIVE_USER_INSTRUCTION_TOTAL_MAX_CHARS = 720


class DesignAgentNodesBase:

    def __init__(self, settings: AgentSettings):
        self.settings = settings
        self.qwen = QwenClient(
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
            text_model=settings.qwen_text_model,
            vision_model=settings.qwen_vision_model,
            enable_web_search=settings.enable_qwen_web_search,
        )
        self.openai_chat_model = OpenAICompatibleChatModel(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model_name=settings.openai_model,
            temperature=0.1,
        )
        self.openai_codegen = OpenAICodegenClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
        )
        self.project_root = Path(__file__).resolve().parents[2]
        self.geometry_exporter = self.project_root / "blender" / "collect_geometry_context.py"

    @staticmethod
    def _emit(message: str) -> None:
        print(f"[NODE] {message}", flush=True)
        trace_event("node.log", message=message)

    @staticmethod
    def _emit_substep(node_name: str, step_name: str, status: str, detail: str = "", **payload: Any) -> None:
        normalized_detail = compact_text(str(detail or "").strip(), 260)
        message = f"{node_name}.{step_name} {status}"
        if normalized_detail:
            message += f": {normalized_detail}"
        print(f"[NODE] {message}", flush=True)
        trace_event(
            "node.substep",
            node_name=node_name,
            step_name=step_name,
            status=status,
            detail=normalized_detail or None,
            **payload,
        )

    def _emit_text_metrics(self, prefix: str, **text_payloads: str | None) -> dict[str, dict[str, int]]:
        metrics = {label: text_stats(value) for label, value in text_payloads.items()}
        trace_event("node.text_metrics", metric_group=prefix, metrics=metrics)
        return metrics

    @staticmethod
    def _extract_tool_result_function_names(content: str, *, max_items: int = 6) -> list[str]:
        normalized = clean_code_fence(content or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return []
        try:
            tree = ast.parse(normalized)
        except SyntaxError:
            return []

        names: list[str] = []
        seen: set[str] = set()
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = str(node.name or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
            if len(names) >= max_items:
                break
        return names

    def _emit_tool_result_metrics(self, tool_name: str, content: str) -> None:
        metrics = text_stats(content)
        trace_event("node.tool_result_metrics", tool_name=tool_name, metrics=metrics)
        function_names = self._extract_tool_result_function_names(content)
        if function_names:
            detail = compact_text(", ".join(function_names), 180)
            self._emit(f"tool result: {tool_name} functions={detail}")
            return
        self._emit(f"tool result: {tool_name}")

    def _emit_text_block(self, title: str, content: str, *, event_name: str = "node.text_dump", **extra: Any) -> None:
        normalized = content or ""
        trace_event(event_name, title=title, content=normalized, metrics=text_stats(normalized), **extra)

    def _switches(self, state: dict[str, Any]) -> NodeSwitches:
        return NodeSwitches.model_validate(state.get("node_switches", {}))

    def _request(self, state: dict[str, Any]) -> dict[str, Any]:
        return dict(state.get("request", {}))

    @staticmethod
    def _user_explicitly_requests_refresh(user_input: str, refresh_markers: tuple[str, ...]) -> bool:
        text = (user_input or "").strip().lower()
        if not text:
            return False
        negation_prefixes = ("不用", "不必", "不要", "无需", "不需要", "先别", "别")
        for marker in refresh_markers:
            normalized_marker = marker.lower()
            if normalized_marker not in text:
                continue
            if any(f"{prefix}{normalized_marker}" in text for prefix in negation_prefixes):
                continue
            return True
        return False

    def _should_reuse_previous_summary(
        self,
        state: dict[str, Any],
        *,
        summary_key: str,
        refresh_markers: tuple[str, ...],
    ) -> tuple[bool, str]:
        route_decision = str(state.get("route_decision") or "")
        if route_decision != "modify_existing":
            return False, ""

        memory = state.get("session_memory", {}) or {}
        previous_summary = compact_text(str(memory.get(summary_key) or ""), 1000)
        if not previous_summary:
            return False, ""

        user_input = str(state.get("user_input") or "")
        if self._user_explicitly_requests_refresh(user_input, refresh_markers):
            return False, ""

        return True, previous_summary

    def _node_skipped(
        self,
        state: dict[str, Any],
        node_name: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._emit(f"{node_name} skipped: {message}")
        payload = {"status": "skipped", "message": message}
        if extra:
            payload.update(extra)
        return {
            "node_results": merge_node_result(state.get("node_results"), node_name, payload),
            "execution_log": [f"{node_name}: {message}"],
        }

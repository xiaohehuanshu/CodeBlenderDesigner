from __future__ import annotations

import json
from typing import Any

from ..tracing import trace_phase
from ..utils import compact_text, ensure_directory, merge_node_result, now_stamp
from .base import ACTIVE_USER_INSTRUCTION_MAX_CHARS, PROMPT_COLLECTION_MAX_CHARS
from .node2_prompts import NODE2_RESEARCH_SYSTEM_PROMPT



class Node2InternetResearchMixin:

    NODE2_REFRESH_MARKERS = (
        "重新联网研究",
        "重新研究",
        "重新调研",
        "重新检索",
        "刷新研究",
        "更新研究",
        "重跑node2",
        "rerun node2",
        "rerun research",
        "refresh research",
        "research again",
    )

    def _build_node2_research_prompt(self, state: dict[str, Any]) -> tuple[str, str]:
        route_decision = str(state.get("route_decision") or "new_generation")
        current_user_input = compact_text(str(state.get("user_input") or "").strip(), PROMPT_COLLECTION_MAX_CHARS)
        design_prompt = compact_text(
            str(state.get("prompt_collection") or state.get("user_input", "")).strip(),
            PROMPT_COLLECTION_MAX_CHARS,
        )
        memory = state.get("session_memory", {}) or {}
        base_values = memory.get("design_brief_base_values") or {}
        baseline_goal = ""
        if isinstance(base_values, dict):
            baseline_goal = compact_text(str(base_values.get("prompt_collection") or "").strip(), 320)

        active_user_instructions: list[str] = []
        for instruction in list(memory.get("design_brief_active_user_instructions") or [])[:3]:
            normalized = compact_text(str(instruction or "").strip(), ACTIVE_USER_INSTRUCTION_MAX_CHARS)
            if normalized and normalized not in active_user_instructions:
                active_user_instructions.append(normalized)

        lines = [
            "请围绕以下建筑设计任务进行互联网研究，并输出面向后续 Blender 建筑生成的可执行总结。",
            "",
            "优先级要求：",
            "1. 当前轮用户原始输入是最高优先级研究依据。",
            "2. 如果用户明确提到建筑类型、业态、风格、场地、体量倾向、空间体验或材料气质，研究必须优先围绕这些信息展开。",
            "3. 不要把明确的设计类型或风格要求泛化成宽泛的通用建筑建议。",
            "4. 输出应优先服务当前任务，不要堆砌无关案例。",
            "",
            f"当前模式：{route_decision}",
            "",
            "当前轮用户原始输入：",
            current_user_input or "无",
        ]
        if design_prompt and design_prompt != current_user_input:
            lines.extend(
                [
                    "",
                    "当前轮提炼后的需求摘要：",
                    design_prompt,
                ]
            )
        if route_decision == "modify_existing":
            if baseline_goal:
                lines.extend(
                    [
                        "",
                        "当前方案基线目标：",
                        baseline_goal,
                    ]
                )
            if active_user_instructions:
                lines.extend(
                    [
                        "",
                        "当前仍生效的最近修改意图：",
                        "；".join(active_user_instructions),
                    ]
                )
        lines.extend(
            [
                "",
                "研究输出时请特别回答：",
                "1. 与当前用户输入直接对应的建筑类型、功能原型与空间组织。",
                "2. 与当前用户输入直接对应的风格、形体、比例和材料倾向。",
                "3. 如果用户提到湖边、山地、街角、滨水、庭院等具体环境，请给出对应环境策略。",
                "4. 给出可以直接转译为 Blender 体量生成的要点，不要只停留在抽象描述。",
            ]
        )
        return design_prompt or current_user_input, "\n".join(lines).strip()

    def node2_internet_research(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node2_internet_research started")
        switches = self._switches(state)
        request = self._request(state)
        if not switches.enabled("node2_internet_research"):
            return self._node_skipped(state, "node2_internet_research", "节点关闭，跳过互联网研究。", {"summary": ""})

        should_reuse, previous_summary = self._should_reuse_previous_summary(
            state,
            summary_key="last_research_summary",
            refresh_markers=self.NODE2_REFRESH_MARKERS,
        )
        if should_reuse:
            note = "modify_existing 轮次默认复用首轮联网研究结果；本轮未检测到明确的重新研究指令。"
            self._emit("node2 reusing previous research summary")
            return {
                "research_summary": previous_summary,
                "node_results": merge_node_result(
                    state.get("node_results"),
                    "node2_internet_research",
                    {
                        "status": "reused",
                        "summary": previous_summary,
                        "note": note,
                        "source": "session_memory.last_research_summary",
                    },
                ),
                "execution_log": [f"node2_internet_research: {note}"],
            }

        design_prompt, research_prompt = self._build_node2_research_prompt(state)

        if self.qwen.is_available:
            try:
                with trace_phase("node2_internet_research.generate_summary", with_search=True):
                    summary = self.qwen.chat_text(
                        system_prompt=(
                            NODE2_RESEARCH_SYSTEM_PROMPT
                            + "\n\n额外要求："
                            + " 请优先响应用户输入中明确出现的建筑类型、功能业态、风格倾向、场地特征与空间体验关键词。"
                            + " 如果用户明确说了茶室、文化中心、展馆、流线型、现代主义、滨水、二层、水平延展等具体词语，请围绕这些词做定向研究，不要泛化。"
                            + " 内容尽量精炼，优先保留最关键的设计依据与可执行结论，总字数控制在1000字以内。"
                        ),
                        user_content=research_prompt,
                        with_search=True,
                    )
                status = "completed"
                note = "已使用 Qwen 联网研究。"
            except Exception as exc:
                summary = f"互联网研究失败，保留空摘要。错误：{compact_text(str(exc), 200)}"
                status = "error"
                note = summary
        else:
            summary = "未配置 DASHSCOPE_API_KEY，节点 2 未执行真实联网研究。"
            status = "fallback"
            note = summary

        summary = compact_text(summary, 1000)

        artifact_paths = self._persist_node2_research_artifacts(
            request=request,
            status=status,
            design_prompt=design_prompt,
            research_prompt=research_prompt,
            summary=summary,
            note=note,
        )
        self._emit(f"node2_internet_research completed: status={status}")
        self._emit(f"node2 artifact latest_md={artifact_paths['latest_markdown_path']}")

        patch: dict[str, Any] = {
            "research_summary": summary,
            "node_results": merge_node_result(
                state.get("node_results"),
                "node2_internet_research",
                {
                    "status": status,
                    "summary": summary,
                    "note": note,
                    **artifact_paths,
                },
            ),
            "execution_log": [
                f"node2_internet_research: {note}",
                f"node2_internet_research: research artifacts saved to {artifact_paths['latest_markdown_path']}",
            ],
        }
        if status == "error":
            patch["errors"] = [summary]
        return patch

    def _persist_node2_research_artifacts(
        self,
        *,
        request: dict[str, Any],
        status: str,
        design_prompt: str,
        research_prompt: str,
        summary: str,
        note: str,
    ) -> dict[str, str]:
        output_dir = ensure_directory(request.get("output_dir") or self.settings.default_output_dir)
        session_id = request.get("session_id", "default")
        internet_research_dir = ensure_directory(output_dir / "internet_research" / session_id)
        history_dir = ensure_directory(internet_research_dir / "history")
        timestamp = now_stamp()

        payload = {
            "session_id": session_id,
            "timestamp": timestamp,
            "status": status,
            "design_prompt": design_prompt,
            "research_prompt": research_prompt,
            "summary": summary,
            "note": note,
            "model": self.settings.qwen_text_model,
            "base_url": self.settings.qwen_base_url,
            "enable_web_search": self.settings.enable_qwen_web_search,
        }
        markdown = self._build_node2_research_markdown(payload)

        latest_markdown_path = internet_research_dir / "node2_summary_latest.md"
        latest_json_path = internet_research_dir / "node2_summary_latest.json"
        history_markdown_path = history_dir / f"{timestamp}_node2.md"
        history_json_path = history_dir / f"{timestamp}_node2.json"

        latest_markdown_path.write_text(markdown, encoding="utf-8")
        history_markdown_path.write_text(markdown, encoding="utf-8")
        latest_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        history_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "latest_markdown_path": str(latest_markdown_path),
            "latest_json_path": str(latest_json_path),
            "history_markdown_path": str(history_markdown_path),
            "history_json_path": str(history_json_path),
        }

    @staticmethod
    def _build_node2_research_markdown(payload: dict[str, Any]) -> str:
        return f"""# Node2 Internet Research Summary

## Metadata

- session_id: {payload.get("session_id", "default")}
- timestamp: {payload.get("timestamp", "")}
- status: {payload.get("status", "")}
- model: {payload.get("model", "")}
- enable_web_search: {payload.get("enable_web_search", False)}

## Design Prompt

{payload.get("design_prompt", "")}

## Research Prompt

{payload.get("research_prompt", "")}

## Summary

{payload.get("summary", "")}

## Note

{payload.get("note", "")}
"""

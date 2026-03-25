from __future__ import annotations

from typing import Any

from ..tracing import trace_phase
from ..utils import compact_text, load_markdown_bundle, merge_node_result
from .node4_prompts import NODE4_MARKDOWN_SYSTEM_PROMPT



class Node4MarkdownAnalysisMixin:

    NODE4_REFRESH_MARKERS = (
        "重新分析markdown",
        "重新读取markdown",
        "重新读取规则",
        "重新读取文本规则",
        "重新分析规则",
        "刷新markdown分析",
        "更新markdown分析",
        "重跑node4",
        "rerun node4",
        "rerun markdown analysis",
        "refresh markdown analysis",
        "read markdown again",
    )

    def node4_markdown_analysis(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node4_markdown_analysis started")
        switches = self._switches(state)
        request = self._request(state)
        if not switches.enabled("node4_markdown_analysis"):
            return self._node_skipped(state, "node4_markdown_analysis", "节点关闭，跳过 Markdown 分析。", {"summary": ""})

        should_reuse, previous_summary = self._should_reuse_previous_summary(
            state,
            summary_key="last_markdown_summary",
            refresh_markers=self.NODE4_REFRESH_MARKERS,
        )
        if should_reuse:
            note = "modify_existing 轮次默认复用首轮 Markdown 分析结果；本轮未检测到明确的重新规则分析指令。"
            self._emit("node4 reusing previous markdown summary")
            return {
                "markdown_summary": previous_summary,
                "node_results": merge_node_result(
                    state.get("node_results"),
                    "node4_markdown_analysis",
                    {
                        "status": "reused",
                        "summary": previous_summary,
                        "note": note,
                        "source": "session_memory.last_markdown_summary",
                    },
                ),
                "execution_log": [f"node4_markdown_analysis: {note}"],
            }

        markdown_text, markdown_files = load_markdown_bundle(request.get("markdown_path"))
        if not markdown_text:
            return self._node_skipped(state, "node4_markdown_analysis", "未找到 Markdown 内容。", {"summary": ""})

        if self.qwen.is_available:
            try:
                with trace_phase("node4_markdown_analysis.generate_summary", file_count=len(markdown_files)):
                    summary = self.qwen.chat_text(
                        system_prompt=(
                            NODE4_MARKDOWN_SYSTEM_PROMPT
                            + "\n\n额外要求：只保留最影响建筑生成的规则、约束和偏好，避免重复转述原文，总字数控制在1000字以内。"
                        ),
                        user_content=markdown_text,
                        with_search=False,
                    )
                status = "completed"
                note = f"已总结 {len(markdown_files)} 个 Markdown 文件。"
            except Exception as exc:
                summary = f"Markdown 总结失败。错误：{compact_text(str(exc), 200)}"
                status = "error"
                note = summary
        else:
            summary = "未配置 DASHSCOPE_API_KEY，使用本地截断文本作为摘要：\n" + compact_text(markdown_text, 1000)
            status = "fallback"
            note = summary
        summary = compact_text(summary, 1000)
        self._emit(f"node4_markdown_analysis completed: status={status}, file_count={len(markdown_files)}")

        patch: dict[str, Any] = {
            "markdown_summary": summary,
            "node_results": merge_node_result(
                state.get("node_results"),
                "node4_markdown_analysis",
                {"status": status, "summary": summary, "files": markdown_files},
            ),
            "execution_log": [f"node4_markdown_analysis: {note}"],
        }
        if status == "error":
            patch["errors"] = [summary]
        return patch

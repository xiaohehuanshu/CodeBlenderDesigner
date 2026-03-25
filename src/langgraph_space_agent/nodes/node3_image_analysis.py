from __future__ import annotations

from pathlib import Path
from typing import Any

from ..tracing import trace_phase
from ..utils import compact_text, list_image_files, merge_node_result
from .node3_prompts import NODE3_IMAGE_ANALYSIS_SYSTEM_PROMPT



class Node3ImageAnalysisMixin:

    NODE3_REFRESH_MARKERS = (
        "重新分析图片",
        "重新分析图像",
        "重新看图",
        "重新读图",
        "重新做图片分析",
        "刷新图片分析",
        "更新图片分析",
        "重跑node3",
        "rerun node3",
        "rerun image analysis",
        "refresh image analysis",
        "analyze images again",
    )

    def node3_image_analysis(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node3_image_analysis started")
        switches = self._switches(state)
        request = self._request(state)
        if not switches.enabled("node3_image_analysis"):
            return self._node_skipped(state, "node3_image_analysis", "节点关闭，跳过图片分析。", {"summary": ""})

        should_reuse, previous_summary = self._should_reuse_previous_summary(
            state,
            summary_key="last_image_analysis_summary",
            refresh_markers=self.NODE3_REFRESH_MARKERS,
        )
        if should_reuse:
            note = "modify_existing 轮次默认复用首轮图片分析结果；本轮未检测到明确的重新图片分析指令。"
            self._emit("node3 reusing previous image analysis summary")
            return {
                "image_analysis_summary": previous_summary,
                "node_results": merge_node_result(
                    state.get("node_results"),
                    "node3_image_analysis",
                    {
                        "status": "reused",
                        "summary": previous_summary,
                        "note": note,
                        "source": "session_memory.last_image_analysis_summary",
                    },
                ),
                "execution_log": [f"node3_image_analysis: {note}"],
            }

        image_paths = [str(path) for path in list_image_files(request.get("image_dir"))]
        if not image_paths:
            return self._node_skipped(state, "node3_image_analysis", "未找到可分析的图片。", {"summary": ""})

        if self.qwen.is_available:
            try:
                user_prompt = f"""
请综合分析这些建筑参考图片，面向后续 Blender 建筑体量生成，提炼整体空间与风格语言。
当前设计任务：
{state.get("prompt_collection") or state.get("user_input", "")}
""".strip()
                with trace_phase("node3_image_analysis.generate_summary", image_count=len(image_paths)):
                    summary = self.qwen.analyze_images(
                        system_prompt=(
                            NODE3_IMAGE_ANALYSIS_SYSTEM_PROMPT
                            + "\n\n额外要求：不要逐张展开描述，请统一归纳整体空间特征、立面语言和细部特征，总字数控制在1000字以内。"
                        ),
                        user_prompt=user_prompt,
                        image_paths=image_paths,
                    )
                status = "completed"
                note = f"已分析 {len(image_paths)} 张图片。"
            except Exception as exc:
                summary = f"图片分析失败。错误：{compact_text(str(exc), 200)}"
                status = "error"
                note = summary
        else:
            names = ", ".join(Path(path).name for path in image_paths)
            summary = f"未配置 DASHSCOPE_API_KEY，无法做多模态分析。已识别图片文件：{names}"
            status = "fallback"
            note = summary
        summary = compact_text(summary, 1000)
        self._emit(f"node3_image_analysis completed: status={status}, image_count={len(image_paths)}")

        patch: dict[str, Any] = {
            "image_analysis_summary": summary,
            "node_results": merge_node_result(
                state.get("node_results"),
                "node3_image_analysis",
                {
                    "status": status,
                    "summary": summary,
                    "image_count": len(image_paths),
                    "image_paths": image_paths,
                },
            ),
            "execution_log": [f"node3_image_analysis: {note}"],
        }
        if status == "error":
            patch["errors"] = [summary]
        return patch

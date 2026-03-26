from __future__ import annotations

from pathlib import Path
from typing import Any

from ..blender_bridge import export_geometry_context
from ..utils import compact_text, ensure_directory, load_json_file, merge_node_result, summarize_geometry_context



class Node5GeometryConstraintsMixin:

    def node5_geometry_constraints(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node5_geometry_constraints started")
        switches = self._switches(state)
        request = self._request(state)
        if not switches.enabled("node5_geometry_constraints"):
            return self._node_skipped(state, "node5_geometry_constraints", "节点关闭，跳过几何约束采集。", {"summary": ""})

        geometry_context_path = request.get("geometry_context_path")
        geometry_context: dict[str, Any] = {}
        source_message = ""

        if geometry_context_path and Path(geometry_context_path).exists():
            geometry_context = load_json_file(geometry_context_path, default={})
            source_message = f"已读取现有几何上下文：{geometry_context_path}"
            self._emit(f"node5 loaded geometry context from {geometry_context_path}")
        else:
            blender_executable = request.get("blender_executable") or self.settings.blender_executable
            blend_file = request.get("blend_file")
            if blend_file:
                output_dir = ensure_directory(request.get("output_dir") or self.settings.default_output_dir)
                derived_output = output_dir / f"geometry_context_{request.get('session_id', 'default')}.json"
                try:
                    self._emit("node5 exporting geometry context via Blender background mode")
                    geometry_context, source_message = export_geometry_context(
                        blender_executable=blender_executable,
                        blend_file=blend_file,
                        exporter_script=str(self.geometry_exporter),
                        output_json_path=str(derived_output),
                    )
                except Exception as exc:
                    message = f"Blender 几何上下文导出失败：{compact_text(str(exc), 200)}"
                    return {
                        "geometry_summary": "",
                        "node_results": merge_node_result(
                            state.get("node_results"),
                            "node5_geometry_constraints",
                            {"status": "error", "summary": "", "message": message},
                        ),
                        "execution_log": [f"node5_geometry_constraints: {message}"],
                        "errors": [message],
                    }
            else:
                return self._node_skipped(
                    state,
                    "node5_geometry_constraints",
                    "未提供 geometry_context_path，也未提供 blend 文件。",
                    {"summary": ""},
                )

        geometry_summary = summarize_geometry_context(geometry_context)
        self._emit("node5_geometry_constraints completed")
        return {
            "geometry_context": geometry_context,
            "geometry_summary": geometry_summary,
            "node_results": merge_node_result(
                state.get("node_results"),
                "node5_geometry_constraints",
                {
                    "status": "completed",
                    "summary": geometry_summary,
                    "message": source_message or "已获得几何约束。",
                },
            ),
            "execution_log": [f"node5_geometry_constraints: {source_message or '已获得几何约束。'}"],
        }

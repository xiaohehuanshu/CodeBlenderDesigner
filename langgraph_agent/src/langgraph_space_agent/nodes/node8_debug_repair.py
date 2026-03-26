from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


class Node8RuntimeRepairMixin:
    def _audit_runtime_patch_scope(
        self,
        *,
        applied_functions: list[str] | None,
        diagnosis_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        applied = self._normalize_string_list(applied_functions or [], max_items=12)
        diagnosis_payload = diagnosis_payload or {}
        target_functions = self._normalize_string_list(diagnosis_payload.get("target_functions") or [], max_items=8)
        supporting_functions = self._normalize_string_list(
            diagnosis_payload.get("supporting_functions") or [],
            max_items=8,
        )
        allowed = set(target_functions + supporting_functions + ["generate_building"])
        touched_targets = [name for name in applied if name in target_functions]
        touched_supporting = [name for name in applied if name in supporting_functions]
        off_target = [name for name in applied if name not in allowed]

        if not applied:
            status = "empty"
            summary = "No top-level functions were patched."
        elif target_functions and touched_targets and not off_target:
            status = "aligned"
            summary = "Patched functions align with the diagnosed target scope."
        elif target_functions and (touched_targets or touched_supporting):
            status = "expanded"
            summary = "Patched the diagnosed area, but also expanded beyond the preferred minimal scope."
        elif supporting_functions and touched_supporting and not off_target:
            status = "support_only"
            summary = "Patched supporting helpers without directly replacing a target function."
        elif off_target:
            status = "off_target"
            summary = "Patch scope drifted away from the diagnosed target functions."
        else:
            status = "unclear"
            summary = "Patch scope could not be cleanly matched to the diagnosed target functions."

        return {
            "status": status,
            "summary": summary,
            "applied_functions": applied,
            "target_functions": target_functions,
            "supporting_functions": supporting_functions,
            "touched_target_functions": touched_targets,
            "touched_supporting_functions": touched_supporting,
            "off_target_functions": off_target,
        }

    @staticmethod
    def _rewrite_reused_boolean_cutters_in_block(block_text: str) -> tuple[str, list[dict[str, Any]]]:
        pattern = re.compile(
            r"(?P<indent>^[ \t]*)add_boolean_difference\(\s*(?P<target>[^,\n]+?)\s*,\s*(?P<cutter>[A-Za-z_][A-Za-z0-9_]*)\s*(?:,\s*keep_cutter\s*=\s*(?P<keep>True|False))?\s*\)\s*$",
            re.M,
        )
        matches = list(pattern.finditer(block_text))
        if not matches:
            return block_text, []

        grouped: dict[str, list[re.Match[str]]] = {}
        for match in matches:
            cutter_name = str(match.group("cutter") or "").strip()
            if not cutter_name:
                continue
            grouped.setdefault(cutter_name, []).append(match)

        replacements: list[tuple[int, int, str]] = []
        metrics: list[dict[str, Any]] = []
        for cutter_name, cutter_matches in grouped.items():
            if len(cutter_matches) <= 1:
                continue
            for index, match in enumerate(cutter_matches):
                desired_keep = "False" if index == len(cutter_matches) - 1 else "True"
                current_keep = match.group("keep")
                if current_keep == desired_keep:
                    continue
                replacement = (
                    f"{match.group('indent')}add_boolean_difference("
                    f"{str(match.group('target') or '').strip()}, {cutter_name}, keep_cutter={desired_keep})"
                )
                replacements.append((match.start(), match.end(), replacement))
                metrics.append(
                    {
                        "cutter_name": cutter_name,
                        "occurrence_index": index + 1,
                        "occurrence_count": len(cutter_matches),
                        "new_keep_cutter": desired_keep == "True",
                    }
                )

        if not replacements:
            return block_text, []

        updated = block_text
        for start, end, replacement in reversed(replacements):
            updated = updated[:start] + replacement + updated[end:]
        return updated, metrics

    def _apply_structrna_boolean_reuse_repair(
        self,
        *,
        script_text: str,
        runtime_validation_result: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        failure_text = "\n".join(
            part
            for part in [
                str(runtime_validation_result.get("runtime_error_excerpt") or "").strip(),
                str(runtime_validation_result.get("stderr_preview") or "").strip(),
                str(runtime_validation_result.get("message") or "").strip(),
            ]
            if part
        ).lower()
        if "structrna of type object has been removed" not in failure_text:
            return script_text, []

        updated_script = script_text
        all_metrics: list[dict[str, Any]] = []
        safe_boolean_helper = """
def add_boolean_difference(target, cutter, keep_cutter=False):
    if target is None or cutter is None:
        return target

    cutter_name = getattr(cutter, "name", "")
    live_cutter = bpy.data.objects.get(cutter_name) if cutter_name else None
    if cutter_name and live_cutter is None:
        return target

    modifier = target.modifiers.new(name="BooleanCut", type="BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.ops.object.select_all(action="DESELECT")

    if not keep_cutter and live_cutter is not None:
        live_cutter.hide_set(True)
        live_cutter.hide_render = True
    return target
""".strip()
        existing_helper_source = self._extract_top_level_function_source(updated_script, "add_boolean_difference")
        if existing_helper_source and existing_helper_source.strip() != safe_boolean_helper:
            updated_script = self._upsert_top_level_function(
                updated_script,
                function_name="add_boolean_difference",
                function_code=safe_boolean_helper,
            )
            all_metrics.append({"function_name": "add_boolean_difference", "repair_kind": "safe_boolean_helper"})

        try:
            tree = ast.parse(updated_script)
        except SyntaxError:
            return updated_script, all_metrics

        replacements: list[tuple[int, int, str]] = []
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            offsets = self._ast_node_offsets(updated_script, node)
            if not offsets:
                continue
            start, end = offsets
            function_source = updated_script[start:end]
            updated_source, metrics = self._rewrite_reused_boolean_cutters_in_block(function_source)
            if not metrics:
                continue
            replacements.append((start, end, updated_source))
            for item in metrics:
                all_metrics.append({"function_name": node.name, **item})

        if not replacements:
            return updated_script, all_metrics

        for start, end, replacement in reversed(replacements):
            updated_script = updated_script[:start] + replacement + updated_script[end:]
        return updated_script, all_metrics

    def _try_high_confidence_fast_fix(
        self,
        *,
        script_text: str,
        runtime_validation_result: dict[str, Any],
        diagnosis_payload: dict[str, Any],
    ) -> tuple[str, str, list[dict[str, Any]]]:
        fast_fix_kind = str(diagnosis_payload.get("fast_fix_kind") or "none").strip()
        confidence = str(diagnosis_payload.get("confidence") or "low").strip()
        if fast_fix_kind != "structrna_boolean_lifecycle" or confidence not in {"high", "medium"}:
            return script_text, "none", []

        repaired_script, metrics = self._apply_structrna_boolean_reuse_repair(
            script_text=script_text,
            runtime_validation_result=runtime_validation_result,
        )
        if not metrics or repaired_script == script_text:
            return script_text, fast_fix_kind, []
        return repaired_script, fast_fix_kind, metrics

    def _revalidate_runtime_debug_candidate(
        self,
        *,
        script_text: str,
        target_path: Path,
        route_decision: str,
        request: dict[str, Any],
        label: str,
    ) -> tuple[str, dict[str, Any], list[str], bool]:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(script_text, encoding="utf-8")

        static_validation_report = self._validate_generated_script(
            script=script_text,
            route_decision=route_decision,
        )
        sections = [f"INFO: {label}", static_validation_report]
        static_validation_passed = "FAIL:" not in static_validation_report
        if static_validation_passed:
            runtime_validation_result = self._validate_generated_script_runtime(
                script_path=str(target_path),
                blender_executable=request.get("blender_executable") or self.settings.blender_executable,
                blend_file=request.get("blend_file"),
                route_decision=route_decision,
                timeout_seconds=request.get("script_validation_timeout_seconds")
                or self.settings.script_validation_timeout_seconds,
            )
            sections.append(self._format_runtime_validation_report(runtime_validation_result))
        else:
            runtime_validation_result = self._build_static_validation_failure_result(
                validation_report=static_validation_report,
                message=f"FAIL: Static validation failed during {label}.",
            )
            sections.append(runtime_validation_result["message"])
        return static_validation_report, runtime_validation_result, sections, static_validation_passed

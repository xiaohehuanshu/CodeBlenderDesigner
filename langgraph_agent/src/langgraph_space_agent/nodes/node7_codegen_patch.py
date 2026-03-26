from __future__ import annotations

import ast
import json
import re
import textwrap
from typing import Any

from ..tracing import trace_phase
from ..utils import clean_code_fence, compact_text, text_stats
from .base import PROMPT_COLLECTION_MAX_CHARS
from .codegen_shared import (
    CONTINUITY_CONTEXT_MAX_CHARS,
    GENERATION_SCOPE_CONCEPT,
    GENERATION_SCOPE_DETAIL,
    GENERATION_SCOPE_FACADE,
    PATCH_REWRITE_SENTINEL,
    PREVIOUS_SCRIPT_FULL_REWRITE_CONTEXT_MAX_CHARS,
    PREVIOUS_SCRIPT_PATCH_CONTEXT_MAX_CHARS,
    PREVIOUS_SCRIPT_PATCH_HELPER_MAX_CHARS,
    PREVIOUS_SCRIPT_PATCH_IMPORT_MAX_LINES,
    PREVIOUS_SCRIPT_PATCH_MAIN_MAX_CHARS,
)
from .node7_codegen_prompts import FULL_SCRIPT_SYSTEM_PROMPT, LOCAL_PATCH_SYSTEM_PROMPT, RUNTIME_REPAIR_SYSTEM_PROMPT


class Node7CodegenPatchMixin:
    @staticmethod
    def _normalize_patch_response_text(text: str) -> str:
        normalized = clean_code_fence(text or "")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
        return normalized

    @classmethod
    def _parse_local_patch_response(cls, response_text: str) -> dict[str, Any]:
        normalized = cls._normalize_patch_response_text(response_text)
        if not normalized:
            return {"strategy": "empty", "imports": [], "functions": []}
        if PATCH_REWRITE_SENTINEL in normalized:
            return {"strategy": "full_script_rewrite", "imports": [], "functions": []}

        try:
            tree = ast.parse(normalized)
        except SyntaxError as exc:
            raise RuntimeError(
                f"局部补丁响应无法解析为顶层模块：{exc.msg} (line {exc.lineno}, offset {exc.offset})"
            ) from exc

        imports: list[str] = []
        functions: list[dict[str, str]] = []
        for node in tree.body:
            offsets = cls._ast_node_offsets(normalized, node)
            if not offsets:
                continue
            start, end = offsets
            source = normalized[start:end].strip()
            if not source:
                continue
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(source)
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({"name": node.name, "code": source})

        return {"strategy": "local_patch", "imports": imports, "functions": functions}

    @staticmethod
    def _upsert_import_lines(script_text: str, import_lines: list[str]) -> str:
        if not import_lines:
            return script_text

        normalized = script_text.replace("\r\n", "\n").replace("\r", "\n")
        existing_imports = {
            line.strip()
            for line in normalized.splitlines()
            if re.match(r"^(?:from\s+\S+\s+import\s+.+|import\s+.+)$", line.strip())
        }
        additions = [line.strip() for line in import_lines if line.strip() and line.strip() not in existing_imports]
        if not additions:
            return normalized

        lines = normalized.splitlines()
        insert_index = 0
        while insert_index < len(lines) and (
            lines[insert_index].startswith("#!")
            or not lines[insert_index].strip()
            or lines[insert_index].strip().startswith("#")
            or lines[insert_index].startswith("from __future__ import")
        ):
            insert_index += 1
        while insert_index < len(lines) and re.match(
            r"^(?:from\s+\S+\s+import\s+.+|import\s+.+)$", lines[insert_index].strip()
        ):
            insert_index += 1

        injected_lines = lines[:insert_index] + additions
        if insert_index < len(lines) and lines[insert_index].strip():
            injected_lines.append("")
        injected_lines.extend(lines[insert_index:])
        return "\n".join(injected_lines).strip() + "\n"

    @staticmethod
    def _find_last_generate_building_call_offset(script_text: str) -> int | None:
        last_offset: int | None = None
        for match in re.finditer(r"(?m)^generate_building\(\)\s*$", script_text):
            last_offset = match.start()
        return last_offset

    def _upsert_top_level_function(self, script_text: str, *, function_name: str, function_code: str) -> str:
        normalized_script = script_text.replace("\r\n", "\n").replace("\r", "\n")
        normalized_function = self._normalize_patch_response_text(function_code).strip()
        if not normalized_function.startswith(f"def {function_name}("):
            raise RuntimeError(f"局部补丁没有返回完整的 {function_name} 顶层函数定义。")

        span = self._find_top_level_function_span(normalized_script, function_name)
        if span:
            start, end = span
            prefix = normalized_script[:start].rstrip()
            suffix = normalized_script[end:].lstrip("\n")
            updated = prefix + "\n\n" + normalized_function + "\n"
            if suffix:
                updated += "\n" + suffix
            return updated.strip() + "\n"

        if function_name != "generate_building":
            generate_span = self._find_top_level_function_span(normalized_script, "generate_building")
            if generate_span:
                insert_at = generate_span[0]
            else:
                insert_at = self._find_last_generate_building_call_offset(normalized_script) or len(normalized_script)
        else:
            insert_at = self._find_last_generate_building_call_offset(normalized_script) or len(normalized_script)

        prefix = normalized_script[:insert_at].rstrip()
        suffix = normalized_script[insert_at:].lstrip("\n")
        updated = prefix + "\n\n" + normalized_function + "\n"
        if suffix:
            updated += "\n" + suffix
        return updated.strip() + "\n"

    @staticmethod
    def _ensure_generate_building_invocation(script_text: str) -> str:
        normalized = script_text.replace("\r\n", "\n").replace("\r", "\n").rstrip()
        if re.search(r"(?m)^generate_building\(\)\s*$", normalized):
            return normalized + "\n"
        return normalized + "\n\n\ngenerate_building()\n"

    @staticmethod
    def _build_scope_directive(*, generation_scope: str, route_decision: str) -> str:
        round_policy = (
            "Round policy: this is a new_generation round. Default to concept-level massing unless the user clearly asked for facade articulation or detail."
            if route_decision == "new_generation"
            else "Round policy: this is a modify_existing round. Inherit the current script maturity by default; do not automatically regress to pure massing or expand to full detail."
        )
        scope_policy_map = {
            GENERATION_SCOPE_CONCEPT: (
                "Scope directive: concept_massing. Focus on primary and secondary volumes, entry emphasis, roof silhouette, major voids, and only necessary large openings. Avoid repeated windows, dense curtain-wall grids, louvers, railings, and similar high-frequency details unless explicitly requested."
            ),
            GENERATION_SCOPE_FACADE: (
                "Scope directive: facade_articulation. Preserve the current massing and refine major openings, facade zoning, solid-vs-glass balance, canopies, shading, and material relationships. Do not automatically expand into dense repeated detail."
            ),
            GENERATION_SCOPE_DETAIL: (
                "Scope directive: detail_enhancement. Preserve the current massing and facade logic. Refine only the locally required detail-level elements such as windows, curtain-wall grids, louvers, railings, canopies, and material accents. Use the smallest necessary change scope."
            ),
        }
        return "\n".join([round_policy, scope_policy_map.get(generation_scope, scope_policy_map[GENERATION_SCOPE_CONCEPT])])

    def _build_local_patch_prompt(
        self,
        *,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
        continuity_context: str,
        previous_script_patch_context: str,
    ) -> str:
        user_block = compact_text(current_user_input.strip(), PROMPT_COLLECTION_MAX_CHARS) or "<empty>"
        scope_directive = self._build_scope_directive(
            generation_scope=generation_scope,
            route_decision="modify_existing",
        )
        sections = [
            "当前轮用户输入：",
            user_block,
            "",
            "精炼后的 design_brief：",
            refined_design_brief,
            "",
            "Generation scope directive:",
            scope_directive,
        ]
        if geometry_summary:
            sections.extend(["", "几何与场地限制：", compact_text(geometry_summary, 1500)])
        if continuity_context:
            sections.extend(["", "连续性摘要：", compact_text(continuity_context, CONTINUITY_CONTEXT_MAX_CHARS)])
        sections.extend(
            [
                "",
                "旧脚本关键上下文：",
                previous_script_patch_context,
                "",
                "输出要求：",
                "1. 优先只输出需要新增或替换的 import 与顶层函数定义。",
                "2. 如果只需要修改 generate_building()，那就只输出这个函数。",
                "3. 如果需要新增 helper，请先输出 helper，再输出更新后的 generate_building()。",
                "4. 不要输出未改动的旧函数。",
                f"5. 如果局部补丁明显不合适，只输出：{PATCH_REWRITE_SENTINEL}",
            ]
        )
        return "\n".join(sections).strip()

    def _run_local_patch_codegen(
        self,
        *,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
        continuity_context: str,
        previous_script_path: str | None,
        system_prompt: str = LOCAL_PATCH_SYSTEM_PROMPT,
        generation_mode: str = "modify_existing_local_patch",
        trace_phase_name: str = "node7_script_generation.local_patch",
        prompt_metrics_label: str = "node7 local patch prompt stats",
        tool_result_label: str = "node7_local_patch_response",
    ) -> tuple[str, str, dict[str, Any]]:
        path, previous_script_text, error = self._load_previous_script_text(previous_script_path)
        if error:
            raise RuntimeError(error)
        assert path is not None and previous_script_text is not None

        previous_script_patch_context = self._build_previous_script_patch_context(previous_script_path)
        patch_prompt = self._build_local_patch_prompt(
            current_user_input=current_user_input,
            refined_design_brief=refined_design_brief,
            generation_scope=generation_scope,
            geometry_summary=geometry_summary,
            continuity_context=continuity_context,
            previous_script_patch_context=previous_script_patch_context,
        )
        self._emit_text_metrics(prompt_metrics_label, local_patch_prompt=patch_prompt)

        with trace_phase(trace_phase_name):
            response_text = self.openai_codegen.client.chat_text(
                system_prompt=system_prompt,
                user_content=patch_prompt,
                temperature=0.1,
            )
        self._emit_tool_result_metrics(tool_result_label, response_text)
        parsed = self._parse_local_patch_response(response_text)
        if parsed["strategy"] == "full_script_rewrite":
            raise RuntimeError("模型判断本轮更适合整份脚本重写。")
        if not parsed["functions"]:
            raise RuntimeError("局部补丁响应未返回任何可替换的顶层函数。")

        updated_script = previous_script_text
        updated_script = self._upsert_import_lines(updated_script, parsed["imports"])

        ordered_functions = sorted(
            parsed["functions"],
            key=lambda item: (str(item.get("name") or "").strip() == "generate_building",),
        )

        applied_functions: list[str] = []
        compile_reports: list[dict[str, Any]] = []
        for function_item in ordered_functions:
            function_name = str(function_item.get("name") or "").strip()
            function_code = str(function_item.get("code") or "").strip()
            if not function_name or not function_code:
                continue
            updated_script = self._upsert_top_level_function(
                updated_script,
                function_name=function_name,
                function_code=function_code,
            )
            updated_script = self._ensure_generate_building_invocation(updated_script)
            compiles, compile_message = self._compile_script(updated_script)
            compile_reports.append(
                {
                    "function_name": function_name,
                    "compile_ok": compiles,
                    "compile_error": compile_message,
                }
            )
            if not compiles:
                raise RuntimeError(f"局部补丁替换 {function_name} 后脚本无法编译：{compile_message}")
            applied_functions.append(function_name)

        updated_script = self._ensure_generate_building_invocation(updated_script)
        compiles, compile_message = self._compile_script(updated_script)
        if not compiles:
            raise RuntimeError(f"局部补丁组装后的脚本无法通过编译：{compile_message}")

        return (
            updated_script,
            generation_mode,
            {
                "patch_import_count": len(parsed["imports"]),
                "patch_function_count": len(applied_functions),
                "applied_functions": applied_functions,
                "compile_reports": compile_reports,
                "previous_script_path": str(path),
                "response_stats": text_stats(response_text),
            },
        )

    @staticmethod
    def _summarize_runtime_failure(runtime_validation_result: dict[str, Any]) -> dict[str, Any]:
        raw_message = str(runtime_validation_result.get("message") or "").strip()
        raw_stdout_preview = str(runtime_validation_result.get("stdout_preview") or "").strip()
        raw_stderr_preview = str(runtime_validation_result.get("runtime_error_excerpt") or runtime_validation_result.get("stderr_preview") or "").strip()

        message = compact_text(raw_message, 260)
        stdout_preview = compact_text(raw_stdout_preview, 500)
        stderr_preview = compact_text(raw_stderr_preview, 1600)
        combined = "\n".join(part for part in [raw_message, raw_stderr_preview, raw_stdout_preview] if part).strip()

        exception_line = ""
        for line in combined.splitlines():
            stripped = line.strip()
            if stripped.startswith(
                (
                    "ReferenceError:",
                    "ValueError:",
                    "RuntimeError:",
                    "TypeError:",
                    "AttributeError:",
                    "KeyError:",
                    "IndexError:",
                )
            ):
                exception_line = stripped
                break

        traceback_functions: list[str] = []
        for match in re.finditer(r'^\s*File\s+"[^"]+",\s+line\s+\d+,\s+in\s+([A-Za-z_][A-Za-z0-9_]*)\s*$', combined, re.M):
            function_name = str(match.group(1) or "").strip()
            if not function_name or function_name in traceback_functions:
                continue
            traceback_functions.append(function_name)

        heuristics: list[str] = []
        lowered = combined.lower()
        if "structrna of type object has been removed" in lowered:
            heuristics.append(
                "A Blender object reference is being reused after removal or invalidation. Common cause: one boolean cutter is deleted after the first use and then reused again."
            )
        if "support object" in lowered and "not grounded" in lowered:
            heuristics.append(
                "A support or plinth object is floating above ground. Fix the geometry semantics or placement instead of deleting the grounding validator."
            )
        if "fill_mode" in lowered and "full" in lowered:
            heuristics.append("An invalid Blender enum is being used. Replace the incompatible API call instead of bypassing the code.")
        if "use_auto_smooth" in lowered:
            heuristics.append("This may be a Blender API compatibility issue. Remove or guard unsupported mesh properties.")

        traceback_excerpt = ""
        marker = "Traceback (most recent call last):"
        if marker in combined:
            trace_block = combined.split(marker, 1)[1]
            trace_lines = [marker] + [line.rstrip() for line in trace_block.splitlines()[:12] if line.strip()]
            traceback_excerpt = compact_text("\n".join(trace_lines), 1000)

        return {
            "message": message,
            "exception_line": exception_line,
            "traceback_functions": traceback_functions,
            "heuristics": heuristics,
            "traceback_excerpt": traceback_excerpt,
        }

    def _build_runtime_repair_user_input(
        self,
        *,
        original_user_input: str,
        runtime_validation_result: dict[str, Any],
        attempt_index: int,
        diagnosis_payload: dict[str, Any] | None = None,
        failure_delta: dict[str, Any] | None = None,
    ) -> str:
        failure = self._summarize_runtime_failure(runtime_validation_result)
        diagnosis_payload = diagnosis_payload or {}
        failure_delta = failure_delta or {}
        sections = [
            f"Automatic runtime repair attempt {attempt_index}.",
            "Patch the current generated Blender script so it passes runtime validation with the smallest necessary local change.",
            "",
            "Original user request:",
            compact_text(original_user_input.strip(), PROMPT_COLLECTION_MAX_CHARS) or "<empty>",
        ]
        if failure["message"]:
            sections.extend(["", "Runtime validation summary:", failure["message"]])
        if failure["exception_line"]:
            sections.extend(["", "Primary exception:", failure["exception_line"]])
        if failure["traceback_functions"]:
            sections.extend(["", "Functions directly implicated by the traceback:", ", ".join(failure["traceback_functions"])])
        if diagnosis_payload.get("root_cause_summary"):
            sections.extend(["", "Structured diagnosis:", compact_text(str(diagnosis_payload["root_cause_summary"]), 400)])
        if diagnosis_payload.get("repair_strategy"):
            sections.extend(["", "Repair strategy:", compact_text(str(diagnosis_payload["repair_strategy"]), 500)])
        if diagnosis_payload.get("repair_scope_summary"):
            sections.extend(
                ["", "Repair scope summary:", compact_text(str(diagnosis_payload["repair_scope_summary"]), 500)]
            )
        target_functions = [str(item).strip() for item in (diagnosis_payload.get("target_functions") or []) if str(item).strip()]
        if target_functions:
            sections.extend(["", "Patch target functions:", ", ".join(target_functions)])
        supporting_functions = [
            str(item).strip()
            for item in (diagnosis_payload.get("supporting_functions") or [])
            if str(item).strip()
        ]
        if supporting_functions:
            sections.extend(["", "Supporting helpers to inspect if needed:", ", ".join(supporting_functions)])
        do_not_touch = [str(item).strip() for item in (diagnosis_payload.get("do_not_touch") or []) if str(item).strip()]
        if do_not_touch:
            sections.extend(["", "Do-not-touch scope:", ", ".join(do_not_touch)])
        repair_checklist = [str(item).strip() for item in (diagnosis_payload.get("repair_checklist") or []) if str(item).strip()]
        if repair_checklist:
            sections.extend(["", "Repair checklist:"] + [f"- {item}" for item in repair_checklist[:6]])
        if failure_delta.get("summary"):
            sections.extend(["", "Failure delta after previous repair:", compact_text(str(failure_delta["summary"]), 500)])
        if failure["traceback_excerpt"]:
            sections.extend(["", "Traceback excerpt:", failure["traceback_excerpt"]])
        if failure["heuristics"]:
            sections.extend(["", "Repair heuristics:"] + [f"- {item}" for item in failure["heuristics"]])
        sections.extend(
            [
                "",
                "Repair rules:",
                "1. Fix the root cause. Do not merely delete validators, suppress errors, or skip failing branches unless absolutely necessary.",
                "2. Preserve the design intent, massing logic, naming, helper boundaries, and object organization.",
                "3. Patch the traceback-implicated functions first. Do not change unrelated facade/detail helpers unless the traceback shows they are involved.",
                "4. If a boolean cutter or support object is reused incorrectly, repair the object lifecycle or geometry semantics instead of rewriting the whole script.",
            ]
        )
        return "\n".join(sections).strip()

    def _build_runtime_repair_focus_context(
        self,
        *,
        current_script_path: str,
        runtime_validation_result: dict[str, Any],
        target_function_names: list[str] | None = None,
    ) -> str:
        failure = self._summarize_runtime_failure(runtime_validation_result)
        if target_function_names is None:
            target_function_names = [
                name
                for name in failure.get("traceback_functions") or []
                if name and name != "<module>"
            ]
        else:
            target_function_names = [name for name in target_function_names if name and name != "<module>"]
        if not target_function_names:
            return ""

        path, current_script_text, error = self._load_previous_script_text(current_script_path)
        if error:
            return ""
        assert path is not None and current_script_text is not None

        blocks: list[str] = [f"Runtime repair target script: {path.name}"]
        for function_name in target_function_names[:6]:
            function_source = self._extract_top_level_function_source(current_script_text, function_name)
            if not function_source:
                continue
            blocks.extend(["", f"[target function] {function_name}", compact_text(function_source, 1800)])
        return compact_text("\n".join(blocks).strip(), PREVIOUS_SCRIPT_PATCH_CONTEXT_MAX_CHARS)

    def _run_runtime_repair_codegen(
        self,
        *,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
        continuity_context: str,
        current_script_path: str,
        runtime_validation_result: dict[str, Any],
        attempt_index: int,
        diagnosis_payload: dict[str, Any] | None = None,
        failure_delta: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        failure = self._summarize_runtime_failure(runtime_validation_result)
        diagnosis_payload = diagnosis_payload or {}
        failure_delta = failure_delta or {}
        target_functions = [
            str(item).strip()
            for item in (diagnosis_payload.get("target_functions") or diagnosis_payload.get("implicated_functions") or failure.get("traceback_functions") or [])
            if str(item).strip()
        ]
        supporting_functions = [
            str(item).strip()
            for item in (diagnosis_payload.get("supporting_functions") or [])
            if str(item).strip()
        ]
        repair_continuity_parts = [continuity_context.strip()] if continuity_context.strip() else []
        if failure["message"]:
            repair_continuity_parts.append("Current runtime failure summary:\n" + failure["message"])
        if failure["exception_line"]:
            repair_continuity_parts.append("Current primary exception:\n" + failure["exception_line"])
        if failure["traceback_functions"]:
            repair_continuity_parts.append(
                "Functions implicated by traceback:\n" + ", ".join(failure["traceback_functions"])
            )
        if failure["traceback_excerpt"]:
            repair_continuity_parts.append("Current traceback excerpt:\n" + failure["traceback_excerpt"])
        focus_context = self._build_runtime_repair_focus_context(
            current_script_path=current_script_path,
            runtime_validation_result=runtime_validation_result,
            target_function_names=target_functions + [name for name in supporting_functions if name not in target_functions],
        )
        if focus_context:
            repair_continuity_parts.append("Current script focus context:\n" + focus_context)
        if diagnosis_payload.get("repair_strategy"):
            repair_continuity_parts.append(
                "Diagnosis repair strategy:\n" + compact_text(str(diagnosis_payload["repair_strategy"]), 600)
            )
        if diagnosis_payload.get("minimal_patch_scope"):
            repair_continuity_parts.append(
                "Diagnosis minimal patch scope:\n" + compact_text(str(diagnosis_payload["minimal_patch_scope"]), 600)
            )
        if diagnosis_payload.get("repair_scope_summary"):
            repair_continuity_parts.append(
                "Diagnosis repair scope summary:\n" + compact_text(str(diagnosis_payload["repair_scope_summary"]), 600)
            )
        traceback_line_contexts = diagnosis_payload.get("traceback_line_contexts") or []
        if traceback_line_contexts:
            blocks: list[str] = []
            for item in traceback_line_contexts[:4]:
                function_name = str(item.get("function_name") or "").strip() or "<unknown>"
                line_number = item.get("line_number")
                context = compact_text(str(item.get("context") or ""), 700)
                if not context:
                    continue
                blocks.append(f"[{function_name} line {line_number}]\n{context}")
            if blocks:
                repair_continuity_parts.append("Exact code windows around traceback lines:\n" + "\n\n".join(blocks))
        if failure_delta.get("summary"):
            repair_continuity_parts.append(
                "Failure delta after previous repair:\n" + compact_text(str(failure_delta["summary"]), 600)
            )
        repair_continuity = "\n\n".join(part for part in repair_continuity_parts if part).strip()

        repair_user_input = self._build_runtime_repair_user_input(
            original_user_input=current_user_input,
            runtime_validation_result=runtime_validation_result,
            attempt_index=attempt_index,
            diagnosis_payload=diagnosis_payload,
            failure_delta=failure_delta,
        )
        updated_script, _mode, metrics = self._run_local_patch_codegen(
            current_user_input=repair_user_input,
            refined_design_brief=refined_design_brief,
            generation_scope=generation_scope,
            geometry_summary=geometry_summary,
            continuity_context=repair_continuity,
            previous_script_path=current_script_path,
            system_prompt=RUNTIME_REPAIR_SYSTEM_PROMPT,
            generation_mode="runtime_repair_local_patch",
            trace_phase_name=f"node8_runtime_debug.runtime_repair_patch_{attempt_index}",
            prompt_metrics_label=f"node8 runtime repair prompt stats attempt {attempt_index}",
            tool_result_label=f"node8_runtime_repair_response_attempt_{attempt_index}",
        )
        return updated_script, "runtime_repair_local_patch", {
            **metrics,
            "attempt_index": attempt_index,
            "failure_summary": failure["message"],
            "exception_line": failure["exception_line"],
            "diagnosis_failure_kind": diagnosis_payload.get("failure_kind"),
            "diagnosis_target_functions": target_functions,
        }

    @staticmethod
    def _sanitize_full_script(script_text: str) -> str:
        normalized = clean_code_fence(script_text or "")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized + ("\n" if normalized else "")

    def _build_new_generation_scaffold(self) -> str:
        base_scaffold = self._build_local_scaffold()
        helper_block, separator, _rest = base_scaffold.partition("def generate_building():")
        if not separator:
            raise RuntimeError("Unable to derive helper scaffold for new_generation codegen.")

        semantic_block = textwrap.dedent(
            """
            def build_primary_massing(*, collection, primary_masses, secondary_masses, solid_mat, glass_mat, accent_mat):
                # Filled by scaffold patch loop.
                return None


            def build_secondary_massing(*, collection, primary_masses, secondary_masses, solid_mat, glass_mat, accent_mat):
                # Filled by scaffold patch loop.
                return None


            def build_entry_and_roof(*, collection, primary_masses, secondary_masses, solid_mat, glass_mat, accent_mat):
                # Filled by scaffold patch loop.
                return None


            def build_major_openings(*, collection, primary_masses, secondary_masses, solid_mat, glass_mat, accent_mat):
                # Filled by scaffold patch loop or later modify_existing patches.
                return None


            def build_facade_articulation(*, collection, primary_masses, secondary_masses, solid_mat, glass_mat, accent_mat):
                # Filled by scaffold patch loop or later modify_existing patches.
                return None


            def apply_materials(*, primary_masses, secondary_masses, solid_mat, glass_mat, accent_mat):
                # Filled by scaffold patch loop.
                return None


            def generate_building():
                random.seed(7)
                collection = ensure_collection("CultureCenter_Massing")
                clear_collection_objects(collection)

                solid_mat = ensure_material("Mat_Concrete", (0.72, 0.74, 0.76, 1.0), roughness=0.58, metallic=0.0)
                glass_mat = ensure_material("Mat_Glass", (0.58, 0.73, 0.82, 1.0), roughness=0.08, metallic=0.0)
                accent_mat = ensure_material("Mat_Accent", (0.88, 0.63, 0.22, 1.0), roughness=0.34, metallic=0.12)

                primary_masses = []
                secondary_masses = []

                build_primary_massing(
                    collection=collection,
                    primary_masses=primary_masses,
                    secondary_masses=secondary_masses,
                    solid_mat=solid_mat,
                    glass_mat=glass_mat,
                    accent_mat=accent_mat,
                )
                build_secondary_massing(
                    collection=collection,
                    primary_masses=primary_masses,
                    secondary_masses=secondary_masses,
                    solid_mat=solid_mat,
                    glass_mat=glass_mat,
                    accent_mat=accent_mat,
                )
                build_entry_and_roof(
                    collection=collection,
                    primary_masses=primary_masses,
                    secondary_masses=secondary_masses,
                    solid_mat=solid_mat,
                    glass_mat=glass_mat,
                    accent_mat=accent_mat,
                )
                build_major_openings(
                    collection=collection,
                    primary_masses=primary_masses,
                    secondary_masses=secondary_masses,
                    solid_mat=solid_mat,
                    glass_mat=glass_mat,
                    accent_mat=accent_mat,
                )
                build_facade_articulation(
                    collection=collection,
                    primary_masses=primary_masses,
                    secondary_masses=secondary_masses,
                    solid_mat=solid_mat,
                    glass_mat=glass_mat,
                    accent_mat=accent_mat,
                )
                apply_materials(
                    primary_masses=primary_masses,
                    secondary_masses=secondary_masses,
                    solid_mat=solid_mat,
                    glass_mat=glass_mat,
                    accent_mat=accent_mat,
                )

                for obj in primary_masses + secondary_masses:
                    if obj is None:
                        continue
                    try:
                        obj.select_set(False)
                    except Exception:
                        pass
                return collection


            generate_building()
            """
        ).strip()
        return helper_block.rstrip() + "\n\n\n" + semantic_block + "\n"

    def _build_scaffold_patch_plan(
        self,
        *,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
    ) -> dict[str, Any]:
        complexity = 0
        if geometry_summary:
            complexity += 1
        if len(refined_design_brief) > 780:
            complexity += 1
        if len(refined_design_brief) > 1020:
            complexity += 1

        if generation_scope == GENERATION_SCOPE_FACADE:
            steps = [
                {
                    "id": 1,
                    "name": "primary_massing",
                    "target_functions": ["build_primary_massing"],
                    "goal": "Establish the primary building massing and the overall silhouette.",
                    "done_when": "The main massing, proportion, and major flowing outline are clear.",
                    "target_chars": 1200,
                },
                {
                    "id": 2,
                    "name": "secondary_massing",
                    "target_functions": ["build_secondary_massing"],
                    "goal": "Add secondary masses, subtractions, terraces, and supporting spatial relations.",
                    "done_when": "Primary and secondary masses form a stable hierarchy.",
                    "target_chars": 1100,
                },
                {
                    "id": 3,
                    "name": "entry_roof_openings",
                    "target_functions": ["build_entry_and_roof", "build_major_openings"],
                    "goal": "Complete entry emphasis, roof resolution, and major openings.",
                    "done_when": "Entry identity, roof silhouette, and large opening logic are readable.",
                    "target_chars": 1200,
                },
                {
                    "id": 4,
                    "name": "facade_materials",
                    "target_functions": ["build_facade_articulation", "apply_materials"],
                    "goal": "Refine facade articulation, solid-vs-glass balance, shading/canopy cues, and material relationships.",
                    "done_when": "Facade-level expression is coherent without over-expanding into dense repeated detail.",
                    "target_chars": 1200,
                },
            ]
            return {
                "step_count": len(steps),
                "reason": "Facade scope requested: use scaffold patch to complete massing first and then controlled facade articulation.",
                "steps": steps,
            }

        if generation_scope == GENERATION_SCOPE_DETAIL:
            steps = [
                {
                    "id": 1,
                    "name": "primary_massing",
                    "target_functions": ["build_primary_massing"],
                    "goal": "Establish the primary building massing and the overall silhouette.",
                    "done_when": "The main massing, proportion, and major flowing outline are clear.",
                    "target_chars": 1200,
                },
                {
                    "id": 2,
                    "name": "secondary_massing",
                    "target_functions": ["build_secondary_massing"],
                    "goal": "Add secondary masses, subtractions, terraces, and supporting spatial relations.",
                    "done_when": "Primary and secondary masses form a stable hierarchy.",
                    "target_chars": 1100,
                },
                {
                    "id": 3,
                    "name": "entry_roof",
                    "target_functions": ["build_entry_and_roof"],
                    "goal": "Complete entry emphasis and roof resolution before detail enrichment.",
                    "done_when": "Entry identity and roof silhouette are clear and stable.",
                    "target_chars": 1000,
                },
                {
                    "id": 4,
                    "name": "major_openings",
                    "target_functions": ["build_major_openings"],
                    "goal": "Add the major openings and large facade cuts required by the concept.",
                    "done_when": "The large opening logic is established without dense repeated window detail.",
                    "target_chars": 1000,
                },
                {
                    "id": 5,
                    "name": "facade_detail_materials",
                    "target_functions": ["build_facade_articulation", "apply_materials"],
                    "goal": "Add only the necessary detail-level articulation and finish the material hierarchy.",
                    "done_when": "Requested detail cues are present while the script remains controlled and patch-friendly.",
                    "target_chars": 1100,
                },
            ]
            return {
                "step_count": len(steps),
                "reason": "Detail scope requested: keep the scaffold patch loop incremental, with massing first and detail added only in the final steps.",
                "steps": steps,
            }

        if complexity <= 0:
            steps = [
                {
                    "id": 1,
                    "name": "massing_core",
                    "target_functions": ["build_primary_massing", "build_secondary_massing"],
                    "goal": "完成文化中心的主体与次级体块，建立三层流线型现代感体量关系。",
                    "done_when": "主次体量、退台或切削关系已经成立，脚本保留进一步补丁空间。",
                    "target_chars": 1500,
                },
                {
                    "id": 2,
                    "name": "entry_materials",
                    "target_functions": ["build_entry_and_roof", "apply_materials"],
                    "goal": "补足入口识别、顶部收束和基础材质表达，形成完整且可继续补丁的首轮方案。",
                    "done_when": "入口、顶部和材质表达可读，整体方案达到可执行状态。",
                    "target_chars": 1300,
                },
            ]
            reason = "任务较简单，采用 2 步 scaffold patch：先体量，再入口与材质。"
        elif complexity <= 2:
            steps = [
                {
                    "id": 1,
                    "name": "primary_massing",
                    "target_functions": ["build_primary_massing"],
                    "goal": "完成文化中心的主体三层主控体量。",
                    "done_when": "主体体量的比例、流线轮廓和层次关系清晰。",
                    "target_chars": 1200,
                },
                {
                    "id": 2,
                    "name": "secondary_massing",
                    "target_functions": ["build_secondary_massing"],
                    "goal": "补足次级体量、退台、切削或辅助构件关系。",
                    "done_when": "次级体量与主控体量形成稳定主次关系。",
                    "target_chars": 1100,
                },
                {
                    "id": 3,
                    "name": "entry_materials",
                    "target_functions": ["build_entry_and_roof", "apply_materials"],
                    "goal": "补足入口识别、顶部处理和基础材质映射。",
                    "done_when": "方案具备入口识别、顶部收束和基础材质表达。",
                    "target_chars": 1200,
                },
            ]
            reason = "任务中等复杂，采用 3 步 scaffold patch：主体、次级、入口与材质。"
        else:
            steps = [
                {
                    "id": 1,
                    "name": "primary_massing",
                    "target_functions": ["build_primary_massing"],
                    "goal": "完成主控体量与三层基本轮廓。",
                    "done_when": "主控体量和主要流线轮廓已经成立。",
                    "target_chars": 1200,
                },
                {
                    "id": 2,
                    "name": "secondary_massing",
                    "target_functions": ["build_secondary_massing"],
                    "goal": "补足次级体量、退台、切削与辅助构件。",
                    "done_when": "次级体量已经与主控体量形成清晰层次。",
                    "target_chars": 1100,
                },
                {
                    "id": 3,
                    "name": "entry_and_roof",
                    "target_functions": ["build_entry_and_roof"],
                    "goal": "补足入口识别、门厅雨棚和顶部收束处理。",
                    "done_when": "入口与顶部语言已经明确并符合现代流线意向。",
                    "target_chars": 1000,
                },
                {
                    "id": 4,
                    "name": "materials_finish",
                    "target_functions": ["apply_materials"],
                    "goal": "将主次体量材质关系整理到位，完成首轮表达。",
                    "done_when": "材质分配与首轮收尾完成，脚本可直接执行。",
                    "target_chars": 900,
                },
            ]
            reason = "任务较复杂，采用 4 步 scaffold patch：主体、次级、入口顶部、材质收尾。"

        return {
            "step_count": len(steps),
            "reason": reason,
            "steps": steps,
        }

    def _build_scaffold_patch_context(self, *, current_script: str, target_functions: list[str]) -> str:
        normalized = current_script.replace("\r\n", "\n").replace("\r", "\n").strip()
        imports = self._extract_import_lines(normalized, limit=PREVIOUS_SCRIPT_PATCH_IMPORT_MAX_LINES)
        generate_building_source = self._extract_top_level_function_source(normalized, "generate_building")
        target_sources: list[str] = []
        for function_name in target_functions:
            function_source = self._extract_top_level_function_source(normalized, function_name)
            if function_source:
                target_sources.append(function_source)

        payload = [
            "当前 scaffold 概览：",
            json.dumps(
                {
                    "stats": text_stats(normalized),
                    "target_functions": target_functions,
                },
                ensure_ascii=False,
                indent=2,
            ),
            "",
            "当前 imports：",
            "\n".join(imports) or "<none>",
            "",
            "当前 generate_building()：",
            compact_text(generate_building_source, PREVIOUS_SCRIPT_PATCH_MAIN_MAX_CHARS) or "<missing>",
            "",
            "当前目标函数：",
            compact_text("\n\n".join(target_sources), PREVIOUS_SCRIPT_PATCH_HELPER_MAX_CHARS) or "<missing>",
        ]
        return compact_text("\n".join(payload).strip(), PREVIOUS_SCRIPT_PATCH_CONTEXT_MAX_CHARS)

    def _build_scaffold_patch_prompt(
        self,
        *,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
        helper_contract: str,
        patch_plan: dict[str, Any],
        current_step: dict[str, Any],
        completed_steps: list[dict[str, Any]],
        current_script: str,
    ) -> str:
        user_block = compact_text(current_user_input.strip(), PROMPT_COLLECTION_MAX_CHARS) or "<empty>"
        plan_summary = json.dumps(
            {
                "step_count": patch_plan["step_count"],
                "reason": patch_plan["reason"],
                "steps": [
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "target_functions": item["target_functions"],
                        "goal": item["goal"],
                        "done_when": item["done_when"],
                        "target_chars": item["target_chars"],
                    }
                    for item in patch_plan["steps"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        scope_directive = self._build_scope_directive(
            generation_scope=generation_scope,
            route_decision="new_generation",
        )
        sections = [
            "这是 new_generation 的 scaffold_patch_first 模式。",
            "你不是从零重写整份脚本，而是基于一个稳定可编译 scaffold，按步骤增量补全目标函数。",
            "",
            "当前轮用户输入：",
            user_block,
            "",
            "精炼后的 design_brief：",
            refined_design_brief,
            "",
            "Generation scope directive:",
            scope_directive,
        ]
        if geometry_summary:
            sections.extend(["", "几何与场地约束：", compact_text(geometry_summary, 1500)])
        sections.extend(
            [
                "",
                "总体补丁计划：",
                compact_text(plan_summary, 1800),
                "",
                "当前步骤：",
                json.dumps(
                    {
                        "id": current_step["id"],
                        "name": current_step["name"],
                        "target_functions": current_step["target_functions"],
                        "goal": current_step["goal"],
                        "done_when": current_step["done_when"],
                        "target_chars": current_step["target_chars"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "",
                "已完成步骤：",
                "\n".join(
                    f"- {item['id']}. {item['name']}: {item['goal']}" for item in completed_steps
                )
                or "<none>",
                "",
                "可用辅助函数：",
                helper_contract,
                "",
                "当前 scaffold 关键上下文：",
                self._build_scaffold_patch_context(
                    current_script=current_script,
                    target_functions=list(current_step["target_functions"]),
                ),
                "",
                "输出要求：",
                "1. 只输出需要新增或替换的顶层 Python 代码块。",
                "2. 优先只更新当前步骤的 target_functions；如确有必要，可新增被这些函数直接调用的 helper。",
                "3. 除非当前步骤明确要求，否则不要重写 generate_building() 或无关函数。",
                "4. 尽量保留当前 target_functions 的函数签名与参数结构。",
                "5. 允许输出 import，但不要输出解释、Markdown 或代码块围栏。",
                f"6. 如果你认为必须整份重写，才输出一行：{PATCH_REWRITE_SENTINEL}",
            ]
        )
        return "\n".join(sections).strip()

    def _should_use_new_generation_full_script_quick_path(
        self,
        *,
        request: dict[str, Any],
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
    ) -> bool:
        request_flag = request.get("enable_new_generation_full_script_quick_path")
        if request_flag is None:
            request_flag = getattr(self.settings, "enable_new_generation_full_script_quick_path", False)
        if not request_flag:
            return False
        if generation_scope != GENERATION_SCOPE_CONCEPT:
            return False
        if geometry_summary.strip():
            return False
        if len(current_user_input.strip()) > 80:
            return False
        if len(refined_design_brief.strip()) > 700:
            return False
        return True

    def _run_scaffold_patch_codegen(
        self,
        *,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
    ) -> tuple[str, str, dict[str, Any]]:
        working_script = self._build_new_generation_scaffold()
        compiles, compile_message = self._compile_script(working_script)
        if not compiles:
            raise RuntimeError(f"new_generation scaffold failed to compile: {compile_message}")

        helper_contract = self._build_helper_contract()
        patch_plan = self._build_scaffold_patch_plan(
            refined_design_brief=refined_design_brief,
            generation_scope=generation_scope,
            geometry_summary=geometry_summary,
        )
        plan_source = "local_heuristic"
        self._emit_substep("node7", "scaffold", "completed", "stable_slots=6")
        self._emit_substep(
            "node7",
            "scaffold_patch_plan",
            "completed",
            f"step_count={patch_plan['step_count']}, source={plan_source}",
        )
        self._emit_tool_result_metrics(
            "node7_scaffold_patch_plan",
            json.dumps(patch_plan, ensure_ascii=False, indent=2),
        )

        completed_steps: list[dict[str, Any]] = []
        step_metrics: list[dict[str, Any]] = []
        last_compiled_script = working_script

        for step in patch_plan["steps"]:
            step_name = f"patch{step['id']}_{step['name']}"
            step_prompt = self._build_scaffold_patch_prompt(
                current_user_input=current_user_input,
                refined_design_brief=refined_design_brief,
                generation_scope=generation_scope,
                geometry_summary=geometry_summary,
                helper_contract=helper_contract,
                patch_plan=patch_plan,
                current_step=step,
                completed_steps=completed_steps,
                current_script=working_script,
            )
            self._emit_substep("node7", step_name, "started")
            self._emit_text_metrics(f"node7 {step_name} prompt stats", user_prompt=step_prompt)
            with trace_phase(f"node7_script_generation.{step_name}"):
                response_text = self.openai_codegen.client.chat_text(
                    system_prompt=LOCAL_PATCH_SYSTEM_PROMPT,
                    user_content=step_prompt,
                    temperature=0.1,
                )
            self._emit_tool_result_metrics(step_name, response_text)
            parsed = self._parse_local_patch_response(response_text)

            if parsed["strategy"] == "full_script_rewrite":
                if completed_steps:
                    self._emit_substep("node7", step_name, "failed", PATCH_REWRITE_SENTINEL)
                    return (
                        last_compiled_script,
                        "new_generation_scaffold_patch_partial_generation_fallback",
                        {
                            "plan_source": plan_source,
                            "plan": patch_plan,
                            "completed_step_count": len(completed_steps),
                            "step_metrics": step_metrics,
                            "failed_step": step["id"],
                            "failed_step_name": step_name,
                            "generation_error": PATCH_REWRITE_SENTINEL,
                        },
                    )
                raise RuntimeError("Scaffold patch loop requested a full script rewrite.")

            if not parsed["functions"]:
                if completed_steps:
                    self._emit_substep("node7", step_name, "failed", "empty_patch_response")
                    return (
                        last_compiled_script,
                        "new_generation_scaffold_patch_partial_generation_fallback",
                        {
                            "plan_source": plan_source,
                            "plan": patch_plan,
                            "completed_step_count": len(completed_steps),
                            "step_metrics": step_metrics,
                            "failed_step": step["id"],
                            "failed_step_name": step_name,
                            "generation_error": "empty_patch_response",
                        },
                    )
                raise RuntimeError("Scaffold patch step returned no top-level functions.")

            updated_script = self._upsert_import_lines(working_script, parsed["imports"])
            ordered_functions = sorted(
                parsed["functions"],
                key=lambda item: (str(item.get("name") or "").strip() == "generate_building",),
            )
            applied_functions: list[str] = []
            compile_reports: list[dict[str, Any]] = []
            for function_item in ordered_functions:
                function_name = str(function_item.get("name") or "").strip()
                function_code = str(function_item.get("code") or "").strip()
                if not function_name or not function_code:
                    continue
                updated_script = self._upsert_top_level_function(
                    updated_script,
                    function_name=function_name,
                    function_code=function_code,
                )
                updated_script = self._ensure_generate_building_invocation(updated_script)
                compiles, compile_message = self._compile_script(updated_script)
                compile_reports.append(
                    {
                        "function_name": function_name,
                        "compile_ok": compiles,
                        "compile_error": compile_message,
                    }
                )
                if not compiles:
                    if completed_steps:
                        self._emit_substep("node7", step_name, "failed", f"compile_error={compile_message}")
                        return (
                            last_compiled_script,
                            "new_generation_scaffold_patch_partial_compile_fallback",
                            {
                                "plan_source": plan_source,
                                "plan": patch_plan,
                                "completed_step_count": len(completed_steps),
                                "step_metrics": step_metrics,
                                "failed_step": step["id"],
                                "failed_step_name": step_name,
                                "compile_error": compile_message,
                            },
                        )
                    raise RuntimeError(f"Scaffold patch step {step_name} failed to compile: {compile_message}")
                applied_functions.append(function_name)

            working_script = updated_script
            last_compiled_script = working_script
            completed_steps.append(step)
            step_metric = {
                "id": step["id"],
                "name": step["name"],
                "target_functions": list(step["target_functions"]),
                "target_chars": step["target_chars"],
                "patch_import_count": len(parsed["imports"]),
                "patch_function_count": len(applied_functions),
                "applied_functions": applied_functions,
                "compile_reports": compile_reports,
                "response_stats": text_stats(response_text),
            }
            step_metrics.append(step_metric)
            self._emit_substep(
                "node7",
                step_name,
                "completed",
                f"updated_functions={len(applied_functions)}, imports={len(parsed['imports'])}",
            )

        return (
            working_script,
            "new_generation_scaffold_patch",
            {
                "plan_source": plan_source,
                "plan": patch_plan,
                "completed_step_count": len(completed_steps),
                "step_metrics": step_metrics,
                "scaffold_stats": text_stats(last_compiled_script),
            },
        )

    def _build_full_script_prompt(
        self,
        *,
        route_decision: str,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
        continuity_context: str,
        previous_script_patch_context: str,
    ) -> str:
        user_block = compact_text(current_user_input.strip(), PROMPT_COLLECTION_MAX_CHARS) or "<empty>"
        scope_directive = self._build_scope_directive(
            generation_scope=generation_scope,
            route_decision=route_decision,
        )
        sections = [
            f"当前模式：{route_decision}",
            "",
            "当前轮用户输入：",
            user_block,
            "",
            "精炼后的 design_brief：",
            refined_design_brief,
            "",
            "Generation scope directive:",
            scope_directive,
        ]
        if geometry_summary:
            sections.extend(["", "几何与场地限制：", compact_text(geometry_summary, 1500)])
        if continuity_context:
            sections.extend(["", "连续性摘要：", compact_text(continuity_context, CONTINUITY_CONTEXT_MAX_CHARS)])
        if route_decision == "modify_existing" and previous_script_patch_context:
            sections.extend(
                [
                    "",
                    "旧脚本关键上下文：",
                    compact_text(previous_script_patch_context, PREVIOUS_SCRIPT_FULL_REWRITE_CONTEXT_MAX_CHARS),
                    "",
                    "本轮要求：",
                    "1. 这不是从零开始，请尽量延续旧脚本中合理的 helper、对象命名、集合结构和体量关系。",
                    "2. 只有在局部补丁已不适合时，才允许扩展到整份脚本重写。",
                    "3. 即使输出整份脚本，也应保留旧方案中仍然合理的设计逻辑，而不是无端推翻。",
                ]
            )
        else:
            sections.extend(
                [
                    "",
                    "本轮要求：",
                    "1. 这是首轮或全新生成，请直接输出一份结构清晰、便于后续 patch 的建筑脚本。",
                    "2. 可以自由组织 helper 函数与主函数，不要被限制为只有 generate_building() 一个函数。",
                ]
            )
        return "\n".join(sections).strip()

    def _run_full_script_codegen(
        self,
        *,
        route_decision: str,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
        continuity_context: str,
        previous_script_patch_context: str,
    ) -> tuple[str, str, dict[str, Any]]:
        prompt = self._build_full_script_prompt(
            route_decision=route_decision,
            current_user_input=current_user_input,
            refined_design_brief=refined_design_brief,
            generation_scope=generation_scope,
            geometry_summary=geometry_summary,
            continuity_context=continuity_context,
            previous_script_patch_context=previous_script_patch_context,
        )
        metric_group = (
            "node7 full rewrite prompt stats" if route_decision == "modify_existing" else "node7 full script prompt stats"
        )
        self._emit_text_metrics(metric_group, full_script_prompt=prompt)
        phase_name = "node7_script_generation.full_rewrite" if route_decision == "modify_existing" else "node7_script_generation.full_script"
        result_name = "node7_full_rewrite_response" if route_decision == "modify_existing" else "node7_full_script_response"

        with trace_phase(phase_name):
            script_text = self.openai_codegen.client.chat_text(
                system_prompt=FULL_SCRIPT_SYSTEM_PROMPT,
                user_content=prompt,
                temperature=0.1,
            )
        self._emit_tool_result_metrics(result_name, script_text)
        script_text = self._sanitize_full_script(script_text)
        compiles, compile_message = self._compile_script(script_text)
        if not compiles:
            raise RuntimeError(f"整份脚本生成后无法通过编译：{compile_message}")

        generation_mode = "modify_existing_full_rewrite" if route_decision == "modify_existing" else "full_script_single_pass"
        return (
            script_text,
            generation_mode,
            {
                "response_stats": text_stats(script_text),
                "used_previous_script_context": bool(previous_script_patch_context),
            },
        )

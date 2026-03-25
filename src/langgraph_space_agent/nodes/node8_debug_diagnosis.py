from __future__ import annotations

import ast
import json
import re
from typing import Any

from ..tracing import trace_phase
from ..utils import compact_text
from .node8_debug_prompts import RUNTIME_DIAGNOSIS_SYSTEM_PROMPT


class Node8RuntimeDiagnosisMixin:
    @staticmethod
    def _normalize_string_list(values: Any, *, max_items: int = 8) -> list[str]:
        if isinstance(values, str):
            candidates = re.split(r"[,;\n]+", values)
        elif isinstance(values, (list, tuple, set)):
            candidates = [str(item) for item in values]
        else:
            candidates = []

        normalized: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
            if len(normalized) >= max_items:
                break
        return normalized

    @classmethod
    def _extract_existing_top_level_function_names(cls, script_text: str) -> list[str]:
        try:
            tree = ast.parse(script_text)
            candidates = [
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        except SyntaxError:
            candidates = re.findall(r"(?m)^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", script_text or "")
        return cls._normalize_string_list(candidates, max_items=40)

    @classmethod
    def _coerce_relevant_objects(cls, values: Any, *, max_items: int = 8) -> list[str]:
        normalized = cls._normalize_string_list(values, max_items=max_items)
        if normalized:
            return normalized
        if not isinstance(values, str):
            return []
        candidates: list[str] = []
        for single_quoted in re.findall(r"'([^']+)'", values):
            if single_quoted.strip():
                candidates.append(single_quoted.strip())
        for double_quoted in re.findall(r'"([^"]+)"', values):
            if double_quoted.strip():
                candidates.append(double_quoted.strip())
        return cls._normalize_string_list(candidates, max_items=max_items)

    def _build_failure_signature(self, runtime_validation_result: dict[str, Any]) -> str:
        failure = self._summarize_runtime_failure(runtime_validation_result)
        signature_parts = [
            str(runtime_validation_result.get("stage") or "").strip(),
            str(runtime_validation_result.get("mode") or "").strip(),
            failure.get("exception_line") or failure.get("message") or "",
            "|".join(self._normalize_string_list(failure.get("traceback_functions") or [], max_items=6)),
        ]
        return " :: ".join(part for part in signature_parts if part)

    def _compare_runtime_failures(
        self,
        *,
        previous_result: dict[str, Any] | None,
        current_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        previous_result = previous_result or {}
        current_result = current_result or {}

        previous_status = str(previous_result.get("status") or "").strip()
        current_status = str(current_result.get("status") or "").strip()
        previous_signature = self._build_failure_signature(previous_result) if previous_result else ""
        current_signature = self._build_failure_signature(current_result) if current_result else ""

        previous_failure = self._summarize_runtime_failure(previous_result) if previous_result else {}
        current_failure = self._summarize_runtime_failure(current_result) if current_result else {}

        if previous_status in {"failed", "partial"} and current_status in {"passed", "partial"} and current_signature:
            summary = "The previous runtime failure appears resolved."
            changed = True
            same_root_cause = False
        elif not previous_signature and current_signature:
            summary = f"Captured a new runtime failure signature: {compact_text(current_signature, 220)}"
            changed = True
            same_root_cause = False
        elif previous_signature and not current_signature:
            summary = "The runtime failure signature cleared."
            changed = True
            same_root_cause = False
        elif previous_signature == current_signature:
            summary = "The runtime failure signature is unchanged."
            changed = False
            same_root_cause = True
        else:
            previous_exception = str(previous_failure.get("exception_line") or "").strip()
            current_exception = str(current_failure.get("exception_line") or "").strip()
            changed = True
            same_root_cause = (
                bool(previous_exception)
                and bool(current_exception)
                and previous_exception == current_exception
            )
            if same_root_cause:
                summary = "The failure moved, but the core exception line is unchanged."
            else:
                summary = "The failure signature changed after the last repair attempt."

        return {
            "previous_signature": previous_signature,
            "current_signature": current_signature,
            "changed": changed,
            "same_root_cause": same_root_cause,
            "summary": summary,
        }

    def _extract_traceback_frames(self, runtime_validation_result: dict[str, Any]) -> list[dict[str, Any]]:
        failure_text = "\n".join(
            part
            for part in [
                str(runtime_validation_result.get("runtime_error_excerpt") or "").strip(),
                str(runtime_validation_result.get("stderr_preview") or "").strip(),
                str(runtime_validation_result.get("message") or "").strip(),
            ]
            if part
        )
        frames: list[dict[str, Any]] = []
        seen: set[tuple[int, str]] = set()
        for match in re.finditer(
            r'^\s*File\s+"[^"]+",\s+line\s+(\d+),\s+in\s+([A-Za-z_<>][A-Za-z0-9_<>]*)\s*$',
            failure_text,
            re.M,
        ):
            line_number = int(match.group(1) or 0)
            function_name = str(match.group(2) or "").strip()
            if not line_number or not function_name:
                continue
            signature = (line_number, function_name)
            if signature in seen:
                continue
            seen.add(signature)
            frames.append(
                {
                    "line_number": line_number,
                    "function_name": function_name,
                }
            )
            if len(frames) >= 8:
                break
        return frames

    @staticmethod
    def _extract_line_window(script_text: str, *, line_number: int, radius: int = 2, max_chars: int = 900) -> str:
        if not script_text or line_number <= 0:
            return ""
        lines = script_text.splitlines()
        if line_number > len(lines):
            return ""
        start = max(1, line_number - radius)
        end = min(len(lines), line_number + radius)
        block = "\n".join(f"{index}: {lines[index - 1]}" for index in range(start, end + 1))
        return compact_text(block, max_chars)

    @classmethod
    def _extract_direct_top_level_callees(
        cls,
        script_text: str,
        *,
        function_names: list[str],
        max_items: int = 10,
    ) -> list[str]:
        function_names = cls._normalize_string_list(function_names, max_items=max_items)
        if not function_names:
            return []
        try:
            tree = ast.parse(script_text)
        except SyntaxError:
            return []

        top_level_functions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        collected: list[str] = []
        seen: set[str] = set()
        for function_name in function_names:
            target_node = next(
                (
                    node
                    for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
                ),
                None,
            )
            if target_node is None:
                continue
            for call_node in ast.walk(target_node):
                if not isinstance(call_node, ast.Call) or not isinstance(call_node.func, ast.Name):
                    continue
                callee_name = str(call_node.func.id or "").strip()
                if not callee_name or callee_name == function_name or callee_name not in top_level_functions:
                    continue
                if callee_name in seen:
                    continue
                seen.add(callee_name)
                collected.append(callee_name)
                if len(collected) >= max_items:
                    return collected
        return collected

    def _build_runtime_evidence_bundle(
        self,
        *,
        script_text: str,
        runtime_validation_result: dict[str, Any],
        target_functions: list[str] | None = None,
    ) -> dict[str, Any]:
        target_functions = self._normalize_string_list(target_functions or [], max_items=8)
        existing_functions = set(self._extract_existing_top_level_function_names(script_text))
        traceback_frames = self._extract_traceback_frames(runtime_validation_result)
        traceback_line_contexts: list[dict[str, Any]] = []
        for frame in traceback_frames:
            line_number = int(frame.get("line_number") or 0)
            context = self._extract_line_window(script_text, line_number=line_number, radius=2, max_chars=900)
            if not context:
                continue
            traceback_line_contexts.append(
                {
                    "function_name": str(frame.get("function_name") or "").strip(),
                    "line_number": line_number,
                    "context": context,
                }
            )

        supporting_functions = [
            name
            for name in self._extract_direct_top_level_callees(
                script_text,
                function_names=target_functions,
                max_items=8,
            )
            if name in existing_functions and name not in target_functions
        ]
        frame_summaries = [
            f"{frame['function_name']}@line{frame['line_number']}"
            for frame in traceback_frames
            if frame.get("function_name") and frame.get("line_number")
        ]

        scope_parts: list[str] = []
        if target_functions:
            scope_parts.append("Patch target functions: " + ", ".join(target_functions))
        if supporting_functions:
            scope_parts.append("Supporting helpers worth reading: " + ", ".join(supporting_functions))
        if frame_summaries:
            scope_parts.append("Exact traceback frames: " + ", ".join(frame_summaries[:6]))

        repair_checklist = [
            "Start from the exact traceback frames and nearby source lines, not from general guesswork.",
            "Patch target functions first; only touch supporting helpers when the target logic depends on them.",
            "Preserve helper boundaries, naming, collection structure, and design intent.",
            "Keep the patch minimal and avoid drifting into unrelated facade or detailing helpers.",
        ]
        return {
            "traceback_frames": traceback_frames,
            "traceback_line_contexts": traceback_line_contexts,
            "supporting_functions": supporting_functions,
            "repair_scope_summary": " | ".join(scope_parts),
            "repair_checklist": repair_checklist,
        }

    def _build_heuristic_runtime_diagnosis(
        self,
        *,
        script_text: str,
        runtime_validation_result: dict[str, Any],
    ) -> dict[str, Any]:
        failure = self._summarize_runtime_failure(runtime_validation_result)
        existing_functions = self._extract_existing_top_level_function_names(script_text)
        base_evidence = self._build_runtime_evidence_bundle(
            script_text=script_text,
            runtime_validation_result=runtime_validation_result,
        )
        traceback_functions = [
            name
            for name in self._normalize_string_list(
                [frame.get("function_name") for frame in base_evidence.get("traceback_frames") or []]
                or failure.get("traceback_functions")
                or [],
                max_items=8,
            )
            if name in existing_functions and name != "<module>"
        ]
        failure_text = "\n".join(
            part
            for part in [
                str(runtime_validation_result.get("message") or "").strip(),
                str(runtime_validation_result.get("runtime_error_excerpt") or "").strip(),
                str(runtime_validation_result.get("stderr_preview") or "").strip(),
            ]
            if part
        )
        relevant_objects = self._coerce_relevant_objects(failure_text, max_items=6)

        failure_kind = "unknown"
        confidence = "medium"
        fast_fix_kind = "none"
        root_cause_summary = failure.get("exception_line") or failure.get("message") or "Runtime validation failed."
        repair_strategy = "Patch only the traceback-implicated helper(s) and preserve the rest of the script."
        minimal_patch_scope = "Limit changes to the smallest helper or caller set directly implicated by the traceback."

        lowered = failure_text.lower()
        if "structrna of type object has been removed" in lowered:
            failure_kind = "boolean_cutter_lifecycle"
            confidence = "high"
            fast_fix_kind = "structrna_boolean_lifecycle"
            root_cause_summary = (
                "A Blender object reference is being reused after the object was invalidated, "
                "most likely during boolean cutter lifecycle handling."
            )
            repair_strategy = (
                "Repair boolean cutter lifecycle management so reused cutters remain valid across operations, "
                "or ensure the cutter is only hidden after its final use."
            )
            minimal_patch_scope = (
                "Patch add_boolean_difference and any directly implicated caller that reuses the same cutter. "
                "Do not rewrite unrelated facade or material helpers."
            )
        elif "support object" in lowered and "not grounded" in lowered:
            failure_kind = "support_grounding"
            confidence = "high"
            root_cause_summary = (
                "A support or plinth object is floating above ground, so the geometry semantics violate the grounding validator."
            )
            repair_strategy = (
                "Adjust the support object's Z placement or base geometry so the support touches ground, "
                "without removing the grounding validator."
            )
            minimal_patch_scope = (
                "Patch the implicated massing or support helper that creates the floating support object. "
                "Keep the validator intact."
            )
        elif "fill_mode" in lowered or "use_auto_smooth" in lowered:
            failure_kind = "api_compatibility"
            confidence = "high"
            root_cause_summary = "The script is using a Blender API property or enum that is incompatible with the current runtime."
            repair_strategy = "Guard or replace the incompatible API call in the implicated helper instead of bypassing the feature wholesale."
            minimal_patch_scope = "Patch only the incompatible property access or enum assignment in the implicated helper."
        elif runtime_validation_result.get("stage") == "static_validation":
            failure_kind = "static_validation"
            confidence = "high"
            root_cause_summary = "Static validation failed before Blender runtime execution could proceed."
            repair_strategy = "Fix the static validation issue first, then rerun runtime validation."
            minimal_patch_scope = "Patch only the syntax, invocation, or required-structure issue reported by static validation."
        elif str(failure.get("exception_line") or "").startswith("ValueError:"):
            failure_kind = "geometry_semantics"
            confidence = "medium"
            root_cause_summary = "A geometry invariant was violated during script execution."
            repair_strategy = "Repair the implicated geometry helper so it produces valid dimensions, transforms, or support relationships."
            minimal_patch_scope = "Patch only the implicated massing helper and preserve the global design structure."

        target_functions = list(traceback_functions)
        if "structrna" in lowered and "add_boolean_difference" in existing_functions and "add_boolean_difference" not in target_functions:
            target_functions.append("add_boolean_difference")
        if len(target_functions) > 1 and "generate_building" in target_functions:
            target_functions = [name for name in target_functions if name != "generate_building"]
        if not target_functions and "generate_building" in existing_functions:
            target_functions = ["generate_building"]

        evidence_bundle = self._build_runtime_evidence_bundle(
            script_text=script_text,
            runtime_validation_result=runtime_validation_result,
            target_functions=target_functions,
        )
        do_not_touch = [
            name
            for name in ("build_major_openings", "build_facade_articulation", "apply_materials")
            if name in existing_functions and name not in target_functions
        ]

        return {
            "root_cause_summary": root_cause_summary,
            "failure_kind": failure_kind,
            "confidence": confidence,
            "implicated_functions": traceback_functions,
            "target_functions": target_functions,
            "supporting_functions": evidence_bundle.get("supporting_functions") or [],
            "relevant_objects": relevant_objects,
            "repair_strategy": repair_strategy,
            "minimal_patch_scope": minimal_patch_scope,
            "repair_scope_summary": evidence_bundle.get("repair_scope_summary") or "",
            "repair_checklist": evidence_bundle.get("repair_checklist") or [],
            "traceback_frames": evidence_bundle.get("traceback_frames") or [],
            "traceback_line_contexts": evidence_bundle.get("traceback_line_contexts") or [],
            "do_not_touch": do_not_touch,
            "fast_fix_kind": fast_fix_kind,
            "expected_success_signal": "Runtime validation should pass or at least move to a different failure signature after the targeted repair.",
        }

    def _normalize_runtime_diagnosis_payload(
        self,
        *,
        raw_payload: dict[str, Any] | None,
        heuristic_payload: dict[str, Any],
        script_text: str,
        runtime_validation_result: dict[str, Any],
    ) -> dict[str, Any]:
        raw_payload = dict(raw_payload or {})
        failure = self._summarize_runtime_failure(runtime_validation_result)
        existing_functions = set(self._extract_existing_top_level_function_names(script_text))

        def normalize_functions(value: Any, *, fallback: list[str]) -> list[str]:
            normalized = [
                name
                for name in self._normalize_string_list(value, max_items=8)
                if not existing_functions or name in existing_functions
            ]
            return normalized or list(fallback)

        allowed_failure_kinds = {
            "boolean_cutter_lifecycle",
            "support_grounding",
            "api_compatibility",
            "geometry_semantics",
            "static_validation",
            "unknown",
        }
        allowed_confidence = {"high", "medium", "low"}
        allowed_fast_fix_kinds = {
            "none",
            "structrna_boolean_lifecycle",
            "support_grounding_adjustment",
            "api_property_guard",
        }

        implicated_functions = normalize_functions(
            raw_payload.get("implicated_functions"),
            fallback=list(heuristic_payload.get("implicated_functions") or []),
        )
        target_functions = normalize_functions(
            raw_payload.get("target_functions"),
            fallback=implicated_functions or list(heuristic_payload.get("target_functions") or []),
        )
        if len(target_functions) > 1 and "generate_building" in target_functions:
            target_functions = [name for name in target_functions if name != "generate_building"]
        if not target_functions and "generate_building" in existing_functions:
            target_functions = ["generate_building"]
        supporting_functions = [
            name
            for name in normalize_functions(
                raw_payload.get("supporting_functions"),
                fallback=list(heuristic_payload.get("supporting_functions") or []),
            )
            if name not in target_functions
        ]

        do_not_touch = [
            name
            for name in self._normalize_string_list(
                raw_payload.get("do_not_touch"),
                max_items=8,
            )
            if name in existing_functions and name not in target_functions
        ]
        if not do_not_touch:
            do_not_touch = list(heuristic_payload.get("do_not_touch") or [])

        failure_kind = str(raw_payload.get("failure_kind") or heuristic_payload.get("failure_kind") or "unknown").strip()
        if failure_kind not in allowed_failure_kinds:
            failure_kind = "unknown"

        confidence = str(raw_payload.get("confidence") or heuristic_payload.get("confidence") or "low").strip()
        if confidence not in allowed_confidence:
            confidence = "low"

        fast_fix_kind = str(raw_payload.get("fast_fix_kind") or heuristic_payload.get("fast_fix_kind") or "none").strip()
        if fast_fix_kind not in allowed_fast_fix_kinds:
            fast_fix_kind = "none"
        if fast_fix_kind != "structrna_boolean_lifecycle":
            fast_fix_kind = "none"

        return {
            "root_cause_summary": compact_text(
                str(raw_payload.get("root_cause_summary") or heuristic_payload.get("root_cause_summary") or failure.get("message") or "").strip(),
                500,
            ),
            "failure_kind": failure_kind,
            "confidence": confidence,
            "implicated_functions": implicated_functions,
            "target_functions": target_functions,
            "supporting_functions": supporting_functions,
            "relevant_objects": self._coerce_relevant_objects(
                raw_payload.get("relevant_objects") or heuristic_payload.get("relevant_objects") or failure.get("exception_line") or "",
                max_items=8,
            ),
            "repair_strategy": compact_text(
                str(raw_payload.get("repair_strategy") or heuristic_payload.get("repair_strategy") or "").strip(),
                800,
            ),
            "minimal_patch_scope": compact_text(
                str(raw_payload.get("minimal_patch_scope") or heuristic_payload.get("minimal_patch_scope") or "").strip(),
                800,
            ),
            "repair_scope_summary": compact_text(
                str(raw_payload.get("repair_scope_summary") or heuristic_payload.get("repair_scope_summary") or "").strip(),
                800,
            ),
            "repair_checklist": self._normalize_string_list(
                raw_payload.get("repair_checklist") or heuristic_payload.get("repair_checklist") or [],
                max_items=6,
            ),
            "traceback_frames": list(heuristic_payload.get("traceback_frames") or [])[:8],
            "traceback_line_contexts": list(heuristic_payload.get("traceback_line_contexts") or [])[:6],
            "do_not_touch": do_not_touch,
            "fast_fix_kind": fast_fix_kind,
            "expected_success_signal": compact_text(
                str(raw_payload.get("expected_success_signal") or heuristic_payload.get("expected_success_signal") or "").strip(),
                500,
            ),
        }

    def _build_runtime_diagnosis_prompt(
        self,
        *,
        current_user_input: str,
        refined_design_brief: str,
        current_script_path: str,
        script_text: str,
        runtime_validation_result: dict[str, Any],
        heuristic_payload: dict[str, Any],
        previous_diagnosis: dict[str, Any] | None = None,
        failure_delta: dict[str, Any] | None = None,
    ) -> str:
        failure = self._summarize_runtime_failure(runtime_validation_result)
        focus_targets = list(heuristic_payload.get("target_functions") or heuristic_payload.get("implicated_functions") or [])
        focus_context = self._build_runtime_repair_focus_context(
            current_script_path=current_script_path,
            runtime_validation_result=runtime_validation_result,
            target_function_names=focus_targets,
        )
        top_level_functions = self._extract_existing_top_level_function_names(script_text)

        sections = [
            "Current user request:",
            compact_text(current_user_input.strip(), 500) or "<empty>",
        ]
        if refined_design_brief:
            sections.extend(["", "Refined design brief:", compact_text(refined_design_brief, 1000)])
        if failure.get("message"):
            sections.extend(["", "Runtime validation summary:", failure["message"]])
        if failure.get("exception_line"):
            sections.extend(["", "Primary exception:", failure["exception_line"]])
        if failure.get("traceback_functions"):
            sections.extend(
                [
                    "",
                    "Traceback implicated functions:",
                    ", ".join(self._normalize_string_list(failure["traceback_functions"], max_items=8)),
                ]
            )
        if failure.get("traceback_excerpt"):
            sections.extend(["", "Traceback excerpt:", failure["traceback_excerpt"]])
        if heuristic_payload.get("repair_scope_summary"):
            sections.extend(
                ["", "Local repair scope summary:", compact_text(str(heuristic_payload["repair_scope_summary"]), 700)]
            )
        supporting_functions = self._normalize_string_list(heuristic_payload.get("supporting_functions") or [], max_items=8)
        if supporting_functions:
            sections.extend(["", "Supporting helpers near the target scope:", ", ".join(supporting_functions)])
        traceback_frames = heuristic_payload.get("traceback_frames") or []
        if traceback_frames:
            frame_lines = [
                f"- {frame.get('function_name')} line {frame.get('line_number')}"
                for frame in traceback_frames[:6]
                if frame.get("function_name") and frame.get("line_number")
            ]
            if frame_lines:
                sections.extend(["", "Exact traceback frames:"] + frame_lines)
        traceback_line_contexts = heuristic_payload.get("traceback_line_contexts") or []
        if traceback_line_contexts:
            line_blocks = []
            for item in traceback_line_contexts[:4]:
                function_name = str(item.get("function_name") or "").strip() or "<unknown>"
                line_number = item.get("line_number")
                context = compact_text(str(item.get("context") or ""), 700)
                if not context:
                    continue
                line_blocks.append(f"[{function_name} line {line_number}]\n{context}")
            if line_blocks:
                sections.extend(["", "Exact source windows around traceback lines:", "\n\n".join(line_blocks)])
        if failure_delta and failure_delta.get("summary"):
            sections.extend(["", "Failure delta from previous attempt:", compact_text(str(failure_delta["summary"]), 500)])
        if previous_diagnosis:
            sections.extend(
                [
                    "",
                    "Previous diagnosis JSON:",
                    compact_text(json.dumps(previous_diagnosis, ensure_ascii=False, indent=2), 1200),
                ]
            )
        sections.extend(
            [
                "",
                "Heuristic diagnosis JSON:",
                json.dumps(heuristic_payload, ensure_ascii=False, indent=2),
            ]
        )
        if top_level_functions:
            sections.extend(["", "Top-level functions in current script:", ", ".join(top_level_functions[:24])])
        if focus_context:
            sections.extend(["", "Focused code context:", focus_context])
        return "\n".join(sections).strip()

    def _diagnose_runtime_failure(
        self,
        *,
        current_user_input: str,
        refined_design_brief: str,
        current_script_path: str,
        script_text: str,
        runtime_validation_result: dict[str, Any],
        previous_diagnosis: dict[str, Any] | None = None,
        failure_delta: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str]:
        heuristic_payload = self._build_heuristic_runtime_diagnosis(
            script_text=script_text,
            runtime_validation_result=runtime_validation_result,
        )
        if not self.openai_codegen.is_available:
            return heuristic_payload, "heuristic_only"

        diagnosis_prompt = self._build_runtime_diagnosis_prompt(
            current_user_input=current_user_input,
            refined_design_brief=refined_design_brief,
            current_script_path=current_script_path,
            script_text=script_text,
            runtime_validation_result=runtime_validation_result,
            heuristic_payload=heuristic_payload,
            previous_diagnosis=previous_diagnosis,
            failure_delta=failure_delta,
        )
        self._emit_text_metrics("node8 runtime diagnosis prompt stats", diagnosis_prompt=diagnosis_prompt)

        try:
            with trace_phase("node8_runtime_debug.runtime_diagnosis"):
                raw_payload = self.openai_codegen.client.chat_json(
                    system_prompt=RUNTIME_DIAGNOSIS_SYSTEM_PROMPT,
                    user_content=diagnosis_prompt,
                    temperature=0.0,
                )
            self._emit_tool_result_metrics(
                "node8_runtime_diagnosis_response",
                json.dumps(raw_payload, ensure_ascii=False),
            )
            normalized = self._normalize_runtime_diagnosis_payload(
                raw_payload=raw_payload,
                heuristic_payload=heuristic_payload,
                script_text=script_text,
                runtime_validation_result=runtime_validation_result,
            )
            return normalized, "model_json"
        except Exception as exc:
            self._emit(f"node8 diagnosis failed, fallback to heuristic diagnosis: {exc}")
            return heuristic_payload, "heuristic_fallback"

from __future__ import annotations

import ast
import json
import re
import textwrap
from pathlib import Path
from typing import Any

from ..utils import compact_text, text_stats
from .codegen_shared import (
    CONTINUITY_CONTEXT_MAX_CHARS,
    LAST_RUN_STATUS_MAX_CHARS,
    PREVIOUS_SCRIPT_KEY_SNIPPETS_MAX_CHARS,
    PREVIOUS_SCRIPT_OVERVIEW_MAX_CHARS,
    PREVIOUS_SCRIPT_PATCH_CONTEXT_MAX_CHARS,
    PREVIOUS_SCRIPT_PATCH_HELPER_MAX_CHARS,
    PREVIOUS_SCRIPT_PATCH_HELPER_MAX_COUNT,
    PREVIOUS_SCRIPT_PATCH_IMPORT_MAX_LINES,
    PREVIOUS_SCRIPT_PATCH_MAIN_MAX_CHARS,
    RECENT_CONVERSATION_MAX_CHARS,
)


class Node7CodegenContextMixin:
    def _build_node7_last_run_status(self, memory: dict[str, Any]) -> str:
        if not memory:
            return "No session memory is available."

        node_results = memory.get("node_results") or {}
        node7_result = node_results.get("node7_script_generation") or {}
        node8_result = node_results.get("node8_runtime_debug") or {}
        final_validation_report = (
            memory.get("last_validation_report")
            or node8_result.get("validation_report")
            or node7_result.get("validation_report")
            or ""
        )
        runtime_validation_status = (
            memory.get("last_runtime_validation_status")
            or node8_result.get("runtime_validation_status")
            or node7_result.get("runtime_validation_status")
        )
        runtime_validation_mode = (
            memory.get("last_runtime_validation_mode")
            or node8_result.get("runtime_validation_mode")
            or node7_result.get("runtime_validation_mode")
        )
        status_payload = {
            "last_route_decision": memory.get("last_route_decision"),
            "last_generated_script_path": memory.get("last_generated_script_path"),
            "last_execution_result": compact_text(str(memory.get("last_execution_result") or ""), 180),
            "last_consolidated_prompt_source": memory.get("last_consolidated_prompt_source"),
            "last_geometry_summary": compact_text(str(memory.get("last_geometry_summary") or ""), 220),
            "last_consolidated_prompt_excerpt": compact_text(str(memory.get("last_consolidated_prompt") or ""), 280),
            "last_node7_status": node7_result.get("status"),
            "last_node7_generation_mode": node7_result.get("generation_mode"),
            "last_node8_status": node8_result.get("status"),
            "last_node7_validation_report": compact_text(str(node7_result.get("validation_report") or ""), 320),
            "last_final_validation_report": compact_text(str(final_validation_report or ""), 320),
            "last_runtime_validation_status": runtime_validation_status,
            "last_runtime_validation_mode": runtime_validation_mode,
        }
        return compact_text(json.dumps(status_payload, ensure_ascii=False, indent=2), LAST_RUN_STATUS_MAX_CHARS)

    def _build_node7_recent_conversation_summary(self, memory: dict[str, Any]) -> str:
        if not memory:
            return "No recent conversation summary is available."

        conversation_history = memory.get("conversation_history") or []
        if not conversation_history:
            return "No conversation history is available."

        recent_turns: list[dict[str, Any]] = []
        for item in conversation_history[-4:]:
            role = item.get("role") or "unknown"
            if role == "user":
                recent_turns.append(
                    {
                        "role": "user",
                        "content": compact_text(str(item.get("content") or ""), 180),
                    }
                )
                continue
            recent_turns.append(
                {
                    "role": role,
                    "route_decision": item.get("route_decision"),
                    "summary": compact_text(str(item.get("summary") or ""), 220),
                }
            )
        return compact_text(
            json.dumps({"recent_turns": recent_turns}, ensure_ascii=False, indent=2),
            RECENT_CONVERSATION_MAX_CHARS,
        )

    @staticmethod
    def _load_previous_script_text(previous_script_path: str | None) -> tuple[Path | None, str | None, str | None]:
        if not previous_script_path:
            return None, None, "No previous script path was found in session memory."
        path = Path(previous_script_path)
        if not path.exists():
            return None, None, f"Previous script path does not exist: {previous_script_path}"
        return path, path.read_text(encoding="utf-8", errors="ignore"), None

    def _build_previous_script_overview(self, previous_script_path: str | None) -> str:
        path, script_text, error = self._load_previous_script_text(previous_script_path)
        if error:
            return error
        assert path is not None and script_text is not None

        imports = re.findall(r"^(?:from\s+\S+\s+import\s+.+|import\s+.+)$", script_text, re.M)
        functions = re.findall(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", script_text, re.M)
        preview_lines = [line for line in script_text.splitlines() if line.strip()][:12]
        overview_payload = {
            "path": str(path),
            "stats": text_stats(script_text),
            "imports": imports[:6],
            "functions": functions[:12],
            "has_generate_building": "def generate_building" in script_text,
            "direct_generate_building_call": "generate_building()" in script_text,
            "preview": compact_text("\n".join(preview_lines), 500),
        }
        return compact_text(
            json.dumps(overview_payload, ensure_ascii=False, indent=2),
            PREVIOUS_SCRIPT_OVERVIEW_MAX_CHARS,
        )

    @staticmethod
    def _extract_named_windows(lines: list[str], *, keywords: tuple[str, ...], window_radius: int, max_windows: int) -> list[str]:
        windows: list[tuple[int, int]] = []
        lowered_keywords = tuple(keyword.lower() for keyword in keywords)
        for index, line in enumerate(lines):
            lowered_line = line.lower()
            if not any(keyword in lowered_line for keyword in lowered_keywords):
                continue
            start = max(0, index - window_radius)
            end = min(len(lines), index + window_radius + 1)
            if windows and start <= windows[-1][1]:
                windows[-1] = (windows[-1][0], max(windows[-1][1], end))
            else:
                windows.append((start, end))
            if len(windows) >= max_windows:
                break

        excerpts: list[str] = []
        for window_index, (start, end) in enumerate(windows, start=1):
            block = "\n".join(
                f"{line_no + 1}: {lines[line_no]}"
                for line_no in range(start, end)
                if lines[line_no].strip()
            )
            if block:
                excerpts.append(f"[snippet {window_index}]\n{block}")
        return excerpts

    def _build_previous_script_key_snippets(self, previous_script_path: str | None) -> str:
        path, script_text, error = self._load_previous_script_text(previous_script_path)
        if error:
            return error
        assert path is not None and script_text is not None

        function_match = re.search(
            r"def\s+generate_building\s*\([^)]*\)\s*:\s*\n(?P<body>(?:[ \t]+.*(?:\n|$))*)",
            script_text,
        )
        if function_match:
            body_text = textwrap.dedent(function_match.group("body"))
            body_lines = body_text.splitlines()
        else:
            body_lines = script_text.splitlines()

        opening_lines = [line for line in body_lines if line.strip()][:16]
        key_windows = self._extract_named_windows(
            body_lines,
            keywords=(
                "collection",
                "ensure_material",
                "assign_material",
                "primary_masses",
                "secondary_masses",
                "podium",
                "mainvolume",
                "roofvolume",
                "entry",
                "canopy",
                "terrace",
                "courtyard",
                "bridge",
                "ramp",
                "stair",
                "void",
                "glass",
                "accent",
                "add_box",
                "add_extruded_plan",
                "add_boolean_difference",
            ),
            window_radius=2,
            max_windows=8,
        )

        parts: list[str] = [f"Source: {path.name}"]
        if opening_lines:
            parts.extend(
                [
                    "",
                    "generate_building opening:",
                    "\n".join(f"{index + 1}: {line}" for index, line in enumerate(opening_lines)),
                ]
            )
        if key_windows:
            parts.extend(["", "Key massing snippets:", "\n\n".join(key_windows)])

        return compact_text("\n".join(parts).strip(), PREVIOUS_SCRIPT_KEY_SNIPPETS_MAX_CHARS)

    @staticmethod
    def _ast_node_offsets(source_text: str, node: ast.AST) -> tuple[int, int] | None:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        col_offset = getattr(node, "col_offset", 0)
        end_col_offset = getattr(node, "end_col_offset", 0)
        if lineno is None or end_lineno is None:
            return None
        lines = source_text.splitlines(keepends=True)
        if lineno - 1 >= len(lines) or end_lineno - 1 >= len(lines):
            return None
        start = sum(len(line) for line in lines[: lineno - 1]) + int(col_offset or 0)
        end = sum(len(line) for line in lines[: end_lineno - 1]) + int(end_col_offset or 0)
        return start, end

    @classmethod
    def _extract_top_level_function_source(cls, source_text: str, function_name: str) -> str:
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return ""

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                offsets = cls._ast_node_offsets(source_text, node)
                if not offsets:
                    return ""
                start, end = offsets
                return source_text[start:end].strip()
        return ""

    @classmethod
    def _find_top_level_function_span(cls, source_text: str, function_name: str) -> tuple[int, int] | None:
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            pattern = re.compile(rf"(?m)^def\s+{re.escape(function_name)}\s*\(")
            match = pattern.search(source_text)
            if not match:
                return None
            start = match.start()
            tail = source_text[start:]
            next_match = re.search(r"(?m)^def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(", tail[1:])
            if not next_match:
                return start, len(source_text)
            end = start + 1 + next_match.start()
            return start, end

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                return cls._ast_node_offsets(source_text, node)
        return None

    @staticmethod
    def _extract_import_lines(source_text: str, *, limit: int) -> list[str]:
        return re.findall(r"^(?:from\s+\S+\s+import\s+.+|import\s+.+)$", source_text, re.M)[:limit]

    @classmethod
    def _extract_called_top_level_function_names(
        cls,
        source_text: str,
        *,
        entry_function: str,
    ) -> list[str]:
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return []

        top_level_functions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        entry_node = next(
            (
                node
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry_function
            ),
            None,
        )
        if entry_node is None:
            return []

        ordered_names: list[str] = []
        seen: set[str] = set()
        for call_node in ast.walk(entry_node):
            if not isinstance(call_node, ast.Call):
                continue
            if not isinstance(call_node.func, ast.Name):
                continue
            function_name = call_node.func.id
            if function_name == entry_function or function_name not in top_level_functions or function_name in seen:
                continue
            seen.add(function_name)
            ordered_names.append(function_name)
        return ordered_names

    def _build_previous_script_patch_context(self, previous_script_path: str | None) -> str:
        path, script_text, error = self._load_previous_script_text(previous_script_path)
        if error:
            return error
        assert path is not None and script_text is not None

        normalized = script_text.strip()
        overview = self._build_previous_script_overview(previous_script_path)
        snippets = self._build_previous_script_key_snippets(previous_script_path)
        generate_building_source = self._extract_top_level_function_source(normalized, "generate_building")
        imports = self._extract_import_lines(normalized, limit=PREVIOUS_SCRIPT_PATCH_IMPORT_MAX_LINES)
        helper_names = self._extract_called_top_level_function_names(
            normalized,
            entry_function="generate_building",
        )

        helper_blocks: list[str] = []
        for helper_name in helper_names[:PREVIOUS_SCRIPT_PATCH_HELPER_MAX_COUNT]:
            helper_source = self._extract_top_level_function_source(normalized, helper_name)
            if not helper_source:
                continue
            helper_blocks.append(helper_source)

        parts = [
            f"Source: {path.name}",
            "",
            "Overview:",
            compact_text(overview, 900),
            "",
            "Imports:",
            "\n".join(imports) or "<none>",
        ]
        if generate_building_source:
            parts.extend(
                [
                    "",
                    "generate_building:",
                    compact_text(generate_building_source, PREVIOUS_SCRIPT_PATCH_MAIN_MAX_CHARS),
                ]
            )
        if helper_blocks:
            parts.extend(
                [
                    "",
                    "Helpers called by generate_building:",
                    compact_text(
                        "\n\n".join(helper_blocks),
                        PREVIOUS_SCRIPT_PATCH_HELPER_MAX_CHARS,
                    ),
                ]
            )
        elif snippets:
            parts.extend(
                [
                    "",
                    "Key snippets:",
                    compact_text(snippets, PREVIOUS_SCRIPT_PATCH_HELPER_MAX_CHARS),
                ]
            )
        return compact_text("\n".join(parts).strip(), PREVIOUS_SCRIPT_PATCH_CONTEXT_MAX_CHARS)

    def _build_continuity_context(
        self,
        *,
        route_decision: str,
        last_run_status: str,
        recent_conversation_summary: str,
        previous_script_overview: str,
        previous_script_key_snippets: str,
    ) -> str:
        if route_decision != "modify_existing":
            return ""
        parts: list[str] = []
        if last_run_status:
            parts.append("Last run status:\n" + compact_text(last_run_status, 180))
        if recent_conversation_summary:
            parts.append("Recent conversation summary:\n" + compact_text(recent_conversation_summary, 180))
        if previous_script_overview:
            parts.append("Previous script overview:\n" + compact_text(previous_script_overview, 180))
        if previous_script_key_snippets:
            parts.append("Previous script key snippets:\n" + compact_text(previous_script_key_snippets, 260))
        return compact_text("\n\n".join(parts).strip(), CONTINUITY_CONTEXT_MAX_CHARS)

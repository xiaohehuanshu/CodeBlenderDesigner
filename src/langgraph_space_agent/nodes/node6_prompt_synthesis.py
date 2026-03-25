from __future__ import annotations

import re
from typing import Any

from ..tracing import trace_phase
from ..utils import compact_text, merge_node_result
from .base import (
    ACTIVE_USER_INSTRUCTION_MAX_CHARS,
    ACTIVE_USER_INSTRUCTION_TOTAL_MAX_CHARS,
    DESIGN_BRIEF_FIELD_LIMITS,
    DESIGN_BRIEF_FIELD_SPECS,
    DESIGN_BRIEF_MAX_CHARS,
    MAX_ACTIVE_USER_INSTRUCTIONS,
    PROMPT_COLLECTION_MAX_CHARS,
)
from .codegen_shared import (
    GENERATION_SCOPE_CONCEPT,
    GENERATION_SCOPE_DETAIL,
    GENERATION_SCOPE_FACADE,
)
from .node6_prompts import NODE6_SYNTHESIS_SYSTEM_PROMPT



class Node6PromptSynthesisMixin:

    @staticmethod
    def _extract_design_brief_sections(design_brief: str) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        current_title: str | None = None
        current_lines: list[str] = []

        def flush_section() -> None:
            nonlocal current_title, current_lines
            if current_title is None:
                return
            content = "\n".join(current_lines).strip()
            if content:
                sections.setdefault(current_title, []).append(content)
            current_lines = []

        for raw_line in (design_brief or "").splitlines():
            line = raw_line.strip()
            matched = re.match(r"^【(.+?)】$", line)
            if matched:
                flush_section()
                current_title = matched.group(1).strip()
                continue
            if current_title is not None:
                current_lines.append(raw_line.rstrip())
        flush_section()
        return sections

    @staticmethod
    def _pick_design_brief_section(
        sections: dict[str, list[str]],
        title: str,
        *,
        prefer_latest: bool,
    ) -> str:
        values = [value.strip() for value in sections.get(title, []) if value and value.strip()]
        if not values:
            return ""
        return values[-1] if prefer_latest else values[0]

    @staticmethod
    def _merge_active_user_instructions(current_instruction: str, previous_instructions: list[Any]) -> list[str]:
        merged: list[str] = []
        for candidate in [current_instruction, *(previous_instructions or [])]:
            normalized = compact_text(str(candidate or "").strip(), ACTIVE_USER_INSTRUCTION_MAX_CHARS)
            if not normalized or normalized in merged:
                continue
            merged.append(normalized)

        trimmed: list[str] = []
        total_chars = 0
        for instruction in merged:
            if len(trimmed) >= MAX_ACTIVE_USER_INSTRUCTIONS:
                break
            if trimmed and total_chars + len(instruction) > ACTIVE_USER_INSTRUCTION_TOTAL_MAX_CHARS:
                break
            trimmed.append(instruction)
            total_chars += len(instruction)
        return trimmed

    @staticmethod
    def _format_active_instruction_lines(brief_context: dict[str, Any]) -> list[str]:
        current_user_instruction = brief_context.get("current_user_instruction") or ""
        active_user_instructions = list(brief_context.get("active_user_instructions") or [])
        previous_active_instructions = list(active_user_instructions)
        if current_user_instruction and previous_active_instructions and previous_active_instructions[0] == current_user_instruction:
            previous_active_instructions = previous_active_instructions[1:]

        lines: list[str] = []
        if current_user_instruction:
            lines.append(f"- 当前轮用户修改：{current_user_instruction}")
        if previous_active_instructions:
            lines.append(f"- 最近仍生效的修改：{'；'.join(previous_active_instructions)}")
        if not lines:
            lines.append("- 当前没有新的活跃修改指令，默认延续当前基线。")
        return lines

    @staticmethod
    def _format_field_update_lines(brief_context: dict[str, Any]) -> list[str]:
        effective_values = brief_context.get("effective_values") or {}
        updated_fields = brief_context.get("updated_fields") or []
        if not updated_fields:
            return ["- 本轮没有新的结构化摘要更新。"]

        lines: list[str] = []
        for field_key, label, _max_chars in DESIGN_BRIEF_FIELD_SPECS:
            if field_key == "prompt_collection" or field_key not in updated_fields:
                continue
            lines.append(f"- {label}：{effective_values.get(field_key) or '无'}")
        return lines or ["- 本轮没有新的结构化摘要更新。"]

    def _resolve_design_brief_context(
        self,
        *,
        route_decision: str,
        prompt_collection: str,
        research_summary: str,
        image_summary: str,
        markdown_summary: str,
        geometry_summary: str,
        memory: dict[str, Any],
        previous_design_brief: str,
    ) -> dict[str, Any]:
        parsed_sections = self._extract_design_brief_sections(previous_design_brief)
        current_values = {
            "prompt_collection": compact_text(prompt_collection, DESIGN_BRIEF_FIELD_LIMITS["prompt_collection"]),
            "research_summary": compact_text(research_summary, DESIGN_BRIEF_FIELD_LIMITS["research_summary"]),
            "image_summary": compact_text(image_summary, DESIGN_BRIEF_FIELD_LIMITS["image_summary"]),
            "markdown_summary": compact_text(markdown_summary, DESIGN_BRIEF_FIELD_LIMITS["markdown_summary"]),
            "geometry_summary": compact_text(geometry_summary, DESIGN_BRIEF_FIELD_LIMITS["geometry_summary"]),
        }
        legacy_previous_values = {
            "prompt_collection": compact_text(
                str(memory.get("last_prompt_collection") or ""), DESIGN_BRIEF_FIELD_LIMITS["prompt_collection"]
            )
            or compact_text(
                self._pick_design_brief_section(parsed_sections, "本轮最新修改意图", prefer_latest=False)
                or self._pick_design_brief_section(parsed_sections, "项目目标", prefer_latest=True),
                DESIGN_BRIEF_FIELD_LIMITS["prompt_collection"],
            ),
            "research_summary": compact_text(
                str(memory.get("last_research_summary") or ""), DESIGN_BRIEF_FIELD_LIMITS["research_summary"]
            )
            or compact_text(
                self._pick_design_brief_section(parsed_sections, "互联网研究总结", prefer_latest=True),
                DESIGN_BRIEF_FIELD_LIMITS["research_summary"],
            ),
            "image_summary": compact_text(
                str(memory.get("last_image_analysis_summary") or ""), DESIGN_BRIEF_FIELD_LIMITS["image_summary"]
            )
            or compact_text(
                self._pick_design_brief_section(parsed_sections, "图片风格总结", prefer_latest=True),
                DESIGN_BRIEF_FIELD_LIMITS["image_summary"],
            ),
            "markdown_summary": compact_text(
                str(memory.get("last_markdown_summary") or ""), DESIGN_BRIEF_FIELD_LIMITS["markdown_summary"]
            )
            or compact_text(
                self._pick_design_brief_section(parsed_sections, "Markdown 文本总结", prefer_latest=True),
                DESIGN_BRIEF_FIELD_LIMITS["markdown_summary"],
            ),
            "geometry_summary": compact_text(
                str(memory.get("last_geometry_summary") or ""), DESIGN_BRIEF_FIELD_LIMITS["geometry_summary"]
            )
            or compact_text(
                self._pick_design_brief_section(parsed_sections, "几何约束", prefer_latest=True),
                DESIGN_BRIEF_FIELD_LIMITS["geometry_summary"],
            ),
        }
        stored_base_values = memory.get("design_brief_base_values")
        base_values: dict[str, str] = {}
        for field_key, _label, max_chars in DESIGN_BRIEF_FIELD_SPECS:
            stored_value = ""
            if isinstance(stored_base_values, dict):
                stored_value = compact_text(str(stored_base_values.get(field_key) or ""), max_chars)
            base_values[field_key] = stored_value or legacy_previous_values[field_key]

        current_user_instruction = current_values["prompt_collection"]
        previous_active_user_instructions = memory.get("design_brief_active_user_instructions") or []
        active_user_instructions = (
            self._merge_active_user_instructions(current_user_instruction, previous_active_user_instructions)
            if route_decision == "modify_existing"
            else []
        )

        effective_values: dict[str, str] = dict(base_values)
        updated_fields: list[str] = []
        carried_fields: list[str] = []
        if route_decision == "modify_existing":
            if not effective_values["prompt_collection"]:
                effective_values["prompt_collection"] = current_user_instruction
            for field_key, _label, _max_chars in DESIGN_BRIEF_FIELD_SPECS:
                if field_key == "prompt_collection":
                    continue
                current_value = current_values[field_key]
                base_value = base_values[field_key]
                if current_value and current_value != base_value:
                    effective_values[field_key] = current_value
                    updated_fields.append(field_key)
                elif not current_value and base_value:
                    carried_fields.append(field_key)
        else:
            effective_values = {field_key: current_values[field_key] for field_key, _label, _max_chars in DESIGN_BRIEF_FIELD_SPECS}

        update_lines: list[str] = []
        if route_decision == "modify_existing":
            if current_user_instruction:
                update_lines.append("- 当前轮用户修改已记录为最高优先级活跃指令。")
            elif active_user_instructions:
                update_lines.append("- 当前轮无新的用户修改，继续沿用最近活跃指令。")
            for field_key, label, _max_chars in DESIGN_BRIEF_FIELD_SPECS:
                if field_key in updated_fields:
                    update_lines.append(f"- {label}：本轮已更新。")
            if carried_fields:
                carried_labels = [label for field_key, label, _max_chars in DESIGN_BRIEF_FIELD_SPECS if field_key in carried_fields]
                update_lines.append(f"- 未更新字段沿用当前基线：{'、'.join(carried_labels)}。")
            if not update_lines:
                if any(base_values.values()):
                    update_lines.append("- 本轮无新增更新，默认延续当前基线。")
                else:
                    update_lines.append("- 本轮无可复用的历史设计基线，按当前输入生成。")

        return {
            "current_values": current_values,
            "previous_values": base_values,
            "effective_values": effective_values,
            "updated_fields": updated_fields,
            "carried_fields": carried_fields,
            "update_lines": update_lines,
            "current_user_instruction": current_user_instruction,
            "active_user_instructions": active_user_instructions,
        }

    @staticmethod
    def _format_design_brief_sections(values: dict[str, str]) -> str:
        sections: list[str] = []
        for field_key, label, _max_chars in DESIGN_BRIEF_FIELD_SPECS:
            sections.extend([f"【{label}】", values.get(field_key) or "无", ""])
        return "\n".join(sections).strip()

    @staticmethod
    def _contains_positive_keyword(text: str, keywords: tuple[str, ...]) -> bool:
        if not text:
            return False
        negation_markers = (
            "不要",
            "先不要",
            "不用",
            "不做",
            "不需要",
            "先不",
            "暂不",
            "别",
            "without",
            "do not",
            "don't",
            "skip",
            "no ",
            "not ",
        )
        lowered = text.lower()
        for keyword in keywords:
            search_from = 0
            normalized_keyword = keyword.lower()
            while True:
                match_index = lowered.find(normalized_keyword, search_from)
                if match_index < 0:
                    break
                prefix = lowered[max(0, match_index - 12) : match_index]
                if not any(marker in prefix for marker in negation_markers):
                    return True
                search_from = match_index + len(normalized_keyword)
        return False

    @classmethod
    def _resolve_generation_scope(
        cls,
        *,
        route_decision: str,
        current_user_input: str,
        memory: dict[str, Any],
    ) -> tuple[str, str]:
        normalized_input = compact_text(current_user_input or "", 420).lower()
        detail_keywords = (
            "门窗",
            "窗洞",
            "窗格",
            "幕墙分格",
            "细节",
            "细部",
            "节点",
            "构造",
            "百叶",
            "栏杆",
            "格栅",
            "雨棚",
            "扶手",
            "window",
            "windows",
            "detail",
            "details",
            "louver",
            "louvers",
            "railing",
            "railings",
            "canopy",
        )
        facade_keywords = (
            "立面",
            "表皮",
            "幕墙",
            "开口",
            "大开口",
            "材质",
            "遮阳",
            "玻璃",
            "入口形象",
            "facade",
            "skin",
            "opening",
            "openings",
            "material",
            "materials",
            "shading",
            "curtain wall",
        )
        massing_keywords = (
            "体块",
            "体量",
            "形体",
            "轮廓",
            "流线",
            "退台",
            "屋顶",
            "屋面",
            "中庭",
            "比例",
            "massing",
            "volume",
            "volumes",
            "form",
            "roof",
            "silhouette",
        )

        if cls._contains_positive_keyword(normalized_input, detail_keywords):
            return GENERATION_SCOPE_DETAIL, "explicit_detail_request"
        if cls._contains_positive_keyword(normalized_input, facade_keywords):
            return GENERATION_SCOPE_FACADE, "explicit_facade_request"
        if cls._contains_positive_keyword(normalized_input, massing_keywords):
            return GENERATION_SCOPE_CONCEPT, "explicit_massing_request"

        previous_scope = str((memory or {}).get("last_generation_scope") or "").strip()
        if route_decision == "modify_existing" and previous_scope in {
            GENERATION_SCOPE_CONCEPT,
            GENERATION_SCOPE_FACADE,
            GENERATION_SCOPE_DETAIL,
        }:
            return previous_scope, "inherit_previous_scope"

        if route_decision == "new_generation":
            return GENERATION_SCOPE_CONCEPT, "new_generation_default"
        return GENERATION_SCOPE_CONCEPT, "modify_existing_default"

    @staticmethod
    def _build_generation_scope_section(*, generation_scope: str, route_decision: str) -> str:
        round_policy = (
            "This is a new_generation round. Default to concept-level massing unless the user clearly asks for facade articulation or detail."
            if route_decision == "new_generation"
            else "This is a modify_existing round. Inherit the current scheme maturity by default; do not automatically regress to pure massing or expand to full detail."
        )
        scope_policy_map = {
            GENERATION_SCOPE_CONCEPT: (
                "Current scope = concept_massing. Focus on primary and secondary volumes, entry emphasis, roof silhouette, major voids, and only the necessary large openings. Avoid repeated windows, dense curtain-wall grids, louvers, railings, and similar high-frequency details unless explicitly requested."
            ),
            GENERATION_SCOPE_FACADE: (
                "Current scope = facade_articulation. Preserve the current massing and refine major openings, facade zoning, solid-vs-glass balance, canopies, shading, and material relationships. Do not automatically expand into dense repeated detail."
            ),
            GENERATION_SCOPE_DETAIL: (
                "Current scope = detail_enhancement. Preserve the current massing and facade logic. Refine only the locally required detail-level elements such as windows, curtain-wall grids, louvers, railings, canopies, and material accents. Use the smallest necessary change scope."
            ),
        }
        return "\n".join([round_policy, scope_policy_map.get(generation_scope, scope_policy_map[GENERATION_SCOPE_CONCEPT])])

    def _build_local_design_brief(
        self,
        *,
        route_decision: str,
        brief_context: dict[str, Any],
    ) -> tuple[str, str]:
        effective_values = brief_context["effective_values"]
        update_lines = brief_context["update_lines"]
        has_previous_context = any(bool(value) for value in brief_context["previous_values"].values())

        sections: list[str] = []
        if route_decision == "modify_existing":
            sections.extend(
                [
                    "【当前任务】",
                    "延续既有方案，并按本轮要求做最小必要修改，默认继承当前方案的成熟度与细化层级。",
                    "",
                    "【当前活跃指令（包含高优先级几何约束）】",
                    *self._format_active_instruction_lines(brief_context),
                ]
            )
            if brief_context["effective_values"].get("geometry_summary"):
                sections.extend(
                    [
                        "",
                        "【高优先级几何约束】",
                        brief_context["effective_values"]["geometry_summary"],
                    ]
                )
            sections.extend(
                [
                    "",
                    "【本轮更新摘要】",
                    *update_lines,
                    "",
                    "【本轮新摘要更新】",
                    *self._format_field_update_lines(brief_context),
                    "",
                    "【当前基线简报】",
                ]
            )
        else:
            if brief_context["effective_values"].get("geometry_summary"):
                sections.extend(
                    [
                        "【高优先级几何约束】",
                        brief_context["effective_values"]["geometry_summary"],
                        "",
                    ]
                )
        sections.extend(
            [
                self._format_design_brief_sections(effective_values),
                "",
                "【默认类型策略】",
                "如果用户没有明确要求住宅、别墅或其他居住类项目，请保持为通用建筑方案，不要默认推断为住宅/别墅。",
                "",
                "【生成要求】",
                "请基于以上信息生成建筑空间体量，优先保证功能合理、空间组织清晰、体量与环境协调，并将信息转译成 Blender 可执行的几何建模逻辑。",
            ]
        )
        if route_decision == "modify_existing":
            sections.extend(
                [
                    "",
                    "【本轮生成范围】",
                    "默认继承当前方案的成熟度，并以最小必要修改满足本轮要求。仅在用户明确要求或任务确有必要时，扩展到立面、开口、材质或细部。",
                ]
            )
        source = "modify_existing_base_plus_active" if route_decision == "modify_existing" and has_previous_context else "local_template"
        return compact_text("\n".join(sections).strip(), DESIGN_BRIEF_MAX_CHARS), source

    def node6_prompt_synthesis(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node6_prompt_synthesis started")
        switches = self._switches(state)
        prompt_collection = compact_text(state.get("prompt_collection", ""), PROMPT_COLLECTION_MAX_CHARS)
        research_summary = compact_text(state.get("research_summary", ""), 450)
        image_summary = compact_text(state.get("image_analysis_summary", ""), 350)
        markdown_summary = compact_text(state.get("markdown_summary", ""), 350)
        geometry_summary = compact_text(state.get("geometry_summary", ""), 1500)
        route_decision = state.get("route_decision", "new_generation")
        current_user_input = str(state.get("user_input") or "").strip()
        memory = state.get("session_memory", {})
        generation_scope, generation_scope_reason = self._resolve_generation_scope(
            route_decision=route_decision,
            current_user_input=current_user_input,
            memory=memory,
        )
        generation_scope_section = self._build_generation_scope_section(
            generation_scope=generation_scope,
            route_decision=route_decision,
        )
        previous_design_brief = compact_text(str(memory.get("last_consolidated_prompt") or ""), DESIGN_BRIEF_MAX_CHARS)
        brief_context = self._resolve_design_brief_context(
            route_decision=route_decision,
            prompt_collection=prompt_collection,
            research_summary=research_summary,
            image_summary=image_summary,
            markdown_summary=markdown_summary,
            geometry_summary=geometry_summary,
            memory=memory,
            previous_design_brief=previous_design_brief,
        )
        used_previous_design_brief = route_decision == "modify_existing" and any(
            bool(value) for value in brief_context["previous_values"].values()
        )
        should_short_circuit_synthesis = (
            used_previous_design_brief
            and not research_summary
            and not image_summary
            and not markdown_summary
            and not geometry_summary
            and len(prompt_collection.strip()) <= 220
        )

        fallback_prompt, fallback_source = self._build_local_design_brief(route_decision=route_decision, brief_context=brief_context)
        fallback_prompt = compact_text(
            "\n\n".join([fallback_prompt, "[Generation Scope Strategy]", generation_scope_section]).strip(),
            DESIGN_BRIEF_MAX_CHARS,
        )

        if not switches.enabled("node6_prompt_synthesis"):
            refined_design_brief = fallback_prompt
            refined_design_brief_source = fallback_source
            self._emit_substep(
                "node6",
                "generation_scope",
                "resolved",
                f"scope={generation_scope}, reason={generation_scope_reason}",
            )
            self._emit_substep("node6", "design_brief", "resolved", f"source={fallback_source}")
            self._emit_substep("node6", "brief_refinement", "skipped", "reason=node_disabled")
            self._emit_text_block(
                "node6 design_brief content",
                fallback_prompt,
                event_name="node6.design_brief",
                route_decision=route_decision,
                source=fallback_source,
                used_previous_design_brief=used_previous_design_brief,
            )
            self._emit_text_block(
                "node6 refined design_brief",
                refined_design_brief,
                event_name="node6.refined_design_brief",
                route_decision=route_decision,
                source=refined_design_brief_source,
                upstream_source=fallback_source,
            )
            self._emit(f"node6_prompt_synthesis completed: status=skipped, source={refined_design_brief_source}")
            return {
                "consolidated_prompt": fallback_prompt,
                "consolidated_prompt_source": fallback_source,
                "refined_design_brief": refined_design_brief,
                "refined_design_brief_source": refined_design_brief_source,
                "generation_scope": generation_scope,
                "generation_scope_reason": generation_scope_reason,
                "design_brief_base_values": brief_context["effective_values"],
                "design_brief_active_user_instructions": brief_context["active_user_instructions"],
                "node_results": merge_node_result(
                    state.get("node_results"),
                    "node6_prompt_synthesis",
                    {
                        "status": "skipped",
                        "summary": refined_design_brief,
                        "message": "节点关闭，使用本地模板整合。",
                        "source": refined_design_brief_source,
                        "consolidated_prompt_source": fallback_source,
                        "brief_refinement_source": refined_design_brief_source,
                        "generation_scope": generation_scope,
                        "generation_scope_reason": generation_scope_reason,
                        "updated_fields": brief_context["updated_fields"],
                        "carried_fields": brief_context["carried_fields"],
                        "active_user_instruction_count": len(brief_context["active_user_instructions"]),
                    },
                ),
                "execution_log": ["node6_prompt_synthesis: 节点关闭，已使用本地模板整合 Prompt。"],
            }

        if should_short_circuit_synthesis:
            consolidated_prompt = fallback_prompt
            consolidated_prompt_source = fallback_source
            status = "completed"
            note = "modify_existing 且无新增上下文，已沿用当前基线并仅保留活跃修改指令。"
        elif self.qwen.is_available:
            synthesis_seed_values = (
                brief_context["previous_values"] if route_decision == "modify_existing" else brief_context["effective_values"]
            )
            synth_sections = [
                "请将以下多源信息整合为一套用于 Blender 建筑生成脚本的高质量 design_brief。",
                "输出时请显式区分“当前活跃指令（包含几何约束）”和“当前基线简报”，并保持单层结构。",
                "",
                "当前模式：",
                route_decision,
                "",
                "当前活跃指令（最高优先级）：",
                "\n".join(self._format_active_instruction_lines(brief_context)),
            ]
            if geometry_summary:
                synth_sections.extend(
                    [
                        "",
                        "高优先级几何约束（必须包含在活跃指令或最醒目位置）：",
                        geometry_summary,
                    ]
                )
            synth_sections.extend(
                [
                    "",
                    "本轮更新摘要：",
                    "\n".join(brief_context["update_lines"]) or "无",
                    "",
                    "本轮新摘要更新：",
                    "\n".join(self._format_field_update_lines(brief_context)),
                    "",
                    "Generation scope strategy:",
                    generation_scope_section,
                ]
            )
            synth_sections.extend(
                [
                    "",
                    "当前结构化字段：",
                    self._format_design_brief_sections(synthesis_seed_values),
                    "",
                    "互联网研究：",
                    research_summary or "无",
                    "",
                    "图片风格分析：",
                    image_summary or "无",
                    "",
                    "Markdown 文本总结：",
                    markdown_summary or "无",
                ]
            )
            synth_prompt = "\n".join(synth_sections).strip()
            try:
                with trace_phase("node6_prompt_synthesis.generate_prompt"):
                    consolidated_prompt = self.qwen.chat_text(
                        system_prompt=(
                            NODE6_SYNTHESIS_SYSTEM_PROMPT
                            + f"\n\n额外要求：输出内容需精炼且可直接服务后续 Blender 生成，只设上限，控制在 {DESIGN_BRIEF_MAX_CHARS} 字以内。"
                            + " 如果当前模式是 modify_existing，请优先输出“当前活跃指令”，再输出“当前基线简报”。"
                            + " 基线简报可沿用上一轮基线字段，但不要重复嵌套历史全文。"
                            + " 如果节点 1-5 没有新增信息，请直接沿用当前基线对应字段，不要为了改写而改写。"
                            + " 对 new_generation，默认先生成概念级体块与主要空间组织；仅当用户明确要求时再展开立面或细部。"
                            + " 对 modify_existing，默认继承当前方案成熟度，不要自动退回纯体块，也不要自动扩展到满量细节。"
                            + " 如果当前轮用户没有明确要求住宅、别墅或其他居住类项目，请不要默认推断为住宅/别墅，保持为通用建筑层级。"
                        ),
                        user_content=synth_prompt,
                        with_search=False,
                    )
                consolidated_prompt = compact_text(consolidated_prompt, DESIGN_BRIEF_MAX_CHARS)
                if consolidated_prompt:
                    consolidated_prompt_source = "qwen_synthesis"
                    status = "completed"
                    note = "已完成多源 Prompt 统一整理。"
                else:
                    consolidated_prompt = fallback_prompt
                    consolidated_prompt_source = fallback_source
                    status = "fallback"
                    note = "Qwen 返回空 design_brief，已回退本地模板。"
            except Exception as exc:
                consolidated_prompt = fallback_prompt
                consolidated_prompt_source = fallback_source
                status = "fallback"
                note = f"Qwen 整理失败，已回退本地模板: {compact_text(str(exc), 200)}"
        else:
            consolidated_prompt = fallback_prompt
            consolidated_prompt_source = fallback_source
            status = "fallback"
            note = "未配置 DASHSCOPE_API_KEY，使用本地模板整合 Prompt。"
        consolidated_prompt = compact_text(
            "\n\n".join([consolidated_prompt, "[Generation Scope Strategy]", generation_scope_section]).strip(),
            DESIGN_BRIEF_MAX_CHARS,
        )
        self._emit_substep(
            "node6",
            "generation_scope",
            "resolved",
            f"scope={generation_scope}, reason={generation_scope_reason}",
        )
        self._emit_substep("node6", "design_brief", "resolved", f"source={consolidated_prompt_source}")
        self._emit_text_block(
            "node6 design_brief content",
            consolidated_prompt,
            event_name="node6.design_brief",
            route_decision=route_decision,
            source=consolidated_prompt_source,
            used_previous_design_brief=used_previous_design_brief,
        )
        self._emit_substep("node6", "brief_refinement", "started")
        refined_design_brief, refined_design_brief_source = self._refine_design_brief_for_node6(
            route_decision=route_decision,
            current_user_input=current_user_input,
            raw_design_brief=consolidated_prompt,
            geometry_summary=geometry_summary,
        )
        self._emit_substep("node6", "brief_refinement", "completed", f"source={refined_design_brief_source}")
        self._emit_text_block(
            "node6 refined design_brief",
            refined_design_brief,
            event_name="node6.refined_design_brief",
            route_decision=route_decision,
            source=refined_design_brief_source,
            upstream_source=consolidated_prompt_source,
        )
        self._emit(f"node6_prompt_synthesis completed: status={status}, source={refined_design_brief_source}")

        return {
            "consolidated_prompt": consolidated_prompt,
            "consolidated_prompt_source": consolidated_prompt_source,
            "refined_design_brief": refined_design_brief,
            "refined_design_brief_source": refined_design_brief_source,
            "generation_scope": generation_scope,
            "generation_scope_reason": generation_scope_reason,
            "design_brief_base_values": brief_context["effective_values"],
            "design_brief_active_user_instructions": brief_context["active_user_instructions"],
            "node_results": merge_node_result(
                state.get("node_results"),
                "node6_prompt_synthesis",
                {
                    "status": status,
                    "summary": refined_design_brief,
                    "note": note,
                    "source": refined_design_brief_source,
                    "consolidated_prompt_source": consolidated_prompt_source,
                    "brief_refinement_source": refined_design_brief_source,
                    "generation_scope": generation_scope,
                    "generation_scope_reason": generation_scope_reason,
                    "used_previous_design_brief": used_previous_design_brief,
                    "updated_fields": brief_context["updated_fields"],
                    "carried_fields": brief_context["carried_fields"],
                    "active_user_instruction_count": len(brief_context["active_user_instructions"]),
                },
            ),
            "execution_log": [f"node6_prompt_synthesis: {note}"],
        }

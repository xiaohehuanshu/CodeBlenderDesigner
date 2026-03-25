from __future__ import annotations

import re

from ..tracing import trace_phase
from ..utils import clean_code_fence, compact_text
from .base import DESIGN_BRIEF_MAX_CHARS, PROMPT_COLLECTION_MAX_CHARS
from .node6_prompts import BRIEF_REFINER_SYSTEM_PROMPT


CODEGEN_BRIEF_MAX_CHARS = 1000


class Node6BriefRefinementMixin:
    @staticmethod
    def _should_refine_design_brief_for_node6(raw_design_brief: str) -> bool:
        return bool((raw_design_brief or "").strip())

    @staticmethod
    def _normalize_node6_refined_brief(text: str) -> str:
        text = clean_code_fence(text or "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return compact_text(text.strip(), CODEGEN_BRIEF_MAX_CHARS)

    @staticmethod
    def _is_usable_node6_refined_brief(raw_text: str, refined_text: str) -> bool:
        if not refined_text.strip():
            return False
        if len(refined_text) < 80:
            return False
        if raw_text and len(refined_text) > max(len(raw_text) + 220, int(len(raw_text) * 1.35)):
            return False
        return True

    def _refine_design_brief_for_node6(
        self,
        *,
        route_decision: str,
        current_user_input: str,
        raw_design_brief: str,
        geometry_summary: str,
    ) -> tuple[str, str]:
        raw_design_brief = compact_text(raw_design_brief, DESIGN_BRIEF_MAX_CHARS)
        if not raw_design_brief:
            return "", "empty"
        if not self._should_refine_design_brief_for_node6(raw_design_brief):
            return raw_design_brief, "raw"
        if not self.qwen.is_available:
            return raw_design_brief, "raw_no_qwen"

        sections = [
            f"Current mode: {route_decision}",
            "",
            "Current user input:",
            compact_text(current_user_input.strip(), PROMPT_COLLECTION_MAX_CHARS) or "<empty>",
            "",
            "Raw unified design_brief:",
            raw_design_brief,
        ]
        if geometry_summary:
            sections.extend(["", "Geometry and site constraints:", compact_text(geometry_summary, 1500)])

        try:
            with trace_phase("node6_prompt_synthesis.refine_design_brief"):
                refined = self.qwen.chat_text(
                    system_prompt=BRIEF_REFINER_SYSTEM_PROMPT,
                    user_content="\n".join(sections).strip(),
                    with_search=False,
                )
            refined = self._normalize_node6_refined_brief(refined)
            if self._is_usable_node6_refined_brief(raw_design_brief, refined):
                return refined, "qwen_refined"
        except Exception as exc:
            self._emit(f"node6 design_brief refinement failed, fallback to raw brief: {exc}")

        return raw_design_brief, "raw_fallback"

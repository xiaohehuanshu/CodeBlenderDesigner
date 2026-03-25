from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..tracing import trace_phase
from ..utils import compact_text, merge_node_result
from .base import ACTIVE_USER_INSTRUCTION_MAX_CHARS, PROMPT_COLLECTION_MAX_CHARS
from .node1_prompts import NODE1_INTENT_SYSTEM_PROMPT


NODE1_MEMORY_RECENT_TURNS = 5
NODE1_RECENT_USER_CONTENT_MAX_CHARS = 180
NODE1_RECENT_ASSISTANT_SUMMARY_MAX_CHARS = 220
NODE1_BASELINE_GOAL_MAX_CHARS = 320
NODE1_LAST_EXECUTION_RESULT_MAX_CHARS = 180
NODE1_MEMORY_SUMMARY_MAX_CHARS = 1500


class Node1CollectRequirementsMixin:

    def _build_node1_memory_summary(self, memory: dict[str, Any]) -> str:
        if not memory:
            return "No session memory is available."

        conversation_history = memory.get("conversation_history") or []
        recent_turns: list[dict[str, Any]] = []
        for item in conversation_history[-NODE1_MEMORY_RECENT_TURNS:]:
            role = item.get("role") or "unknown"
            if role == "user":
                recent_turns.append(
                    {
                        "role": "user",
                        "content": compact_text(str(item.get("content") or ""), NODE1_RECENT_USER_CONTENT_MAX_CHARS),
                    }
                )
                continue
            recent_turns.append(
                {
                    "role": role,
                    "route_decision": item.get("route_decision"),
                    "summary": compact_text(str(item.get("summary") or ""), NODE1_RECENT_ASSISTANT_SUMMARY_MAX_CHARS),
                }
            )

        base_values = memory.get("design_brief_base_values")
        baseline_goal = ""
        if isinstance(base_values, dict):
            baseline_goal = compact_text(
                str(base_values.get("prompt_collection") or ""),
                min(PROMPT_COLLECTION_MAX_CHARS, NODE1_BASELINE_GOAL_MAX_CHARS),
            )

        active_user_instructions: list[str] = []
        for instruction in list(memory.get("design_brief_active_user_instructions") or [])[:3]:
            normalized = compact_text(str(instruction or ""), ACTIVE_USER_INSTRUCTION_MAX_CHARS)
            if normalized:
                active_user_instructions.append(normalized)

        previous_script_path = memory.get("last_generated_script_path")
        summary_payload = {
            "last_route_decision": memory.get("last_route_decision"),
            "has_previous_script": bool(previous_script_path),
            "last_generated_script_name": Path(str(previous_script_path)).name if previous_script_path else None,
            "last_execution_result": compact_text(
                str(memory.get("last_execution_result") or ""),
                NODE1_LAST_EXECUTION_RESULT_MAX_CHARS,
            ),
            "last_consolidated_prompt_source": memory.get("last_consolidated_prompt_source"),
            "baseline_goal": baseline_goal,
            "active_user_instructions": active_user_instructions,
            "recent_turns": recent_turns,
        }
        return compact_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2),
            NODE1_MEMORY_SUMMARY_MAX_CHARS,
        )

    def node1_collect_requirements(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node1_collect_requirements started")
        switches = self._switches(state)
        user_input = str(state.get("user_input") or "")
        memory = state.get("session_memory", {}) or {}
        turn_index_in_run = max(1, int(state.get("turn_index_in_run") or 1))

        if not switches.enabled("node1_collect_requirements"):
            route_decision, should_end = self._heuristic_route(
                user_input,
                memory,
                turn_index_in_run=turn_index_in_run,
            )
            return {
                "route_decision": route_decision,
                "should_end": should_end,
                "prompt_collection": user_input,
                "node_results": merge_node_result(
                    state.get("node_results"),
                    "node1_collect_requirements",
                    {
                        "status": "skipped",
                        "route_decision": route_decision,
                        "reason": "节点关闭，使用启发式规则。",
                    },
                ),
                "execution_log": ["node1_collect_requirements: 节点关闭，已使用启发式规则判断流程。"],
            }

        if self.qwen.is_available:
            memory_summary = self._build_node1_memory_summary(memory)
            prompt = (
                f"用户输入：\n{user_input}\n\n"
                f"当前运行轮次：\n{turn_index_in_run}\n\n"
                f"历史记忆：\n{memory_summary or '无'}"
            ).strip()
            try:
                with trace_phase("node1_collect_requirements.intent"):
                    response = self.qwen.chat_json(system_prompt=NODE1_INTENT_SYSTEM_PROMPT, user_content=prompt)
                route_decision = response.get("route_decision") or "new_generation"
                should_end = bool(response.get("should_end", route_decision == "end"))
                requirement_summary = response.get("requirement_summary") or user_input
                reason = response.get("reason") or "Qwen 未返回明确原因。"
                route_decision, should_end, correction_note = self._stabilize_route_decision(
                    user_input=user_input,
                    memory=memory,
                    turn_index_in_run=turn_index_in_run,
                    route_decision=route_decision,
                    should_end=should_end,
                )
                if correction_note:
                    reason = f"{reason} {correction_note}".strip()
            except Exception as exc:
                route_decision, should_end = self._heuristic_route(
                    user_input,
                    memory,
                    turn_index_in_run=turn_index_in_run,
                )
                requirement_summary = user_input
                reason = f"Qwen 判断失败，回退启发式逻辑: {compact_text(str(exc), 200)}"
        else:
            route_decision, should_end = self._heuristic_route(
                user_input,
                memory,
                turn_index_in_run=turn_index_in_run,
            )
            requirement_summary = user_input
            reason = "未配置 DASHSCOPE_API_KEY，使用启发式逻辑。"

        self._emit(f"node1_collect_requirements completed: route_decision={route_decision}, should_end={should_end}")
        return {
            "route_decision": route_decision,
            "should_end": should_end,
            "prompt_collection": requirement_summary,
            "node_results": merge_node_result(
                state.get("node_results"),
                "node1_collect_requirements",
                {
                    "status": "completed",
                    "route_decision": route_decision,
                    "should_end": should_end,
                    "summary": requirement_summary,
                    "reason": reason,
                },
            ),
            "execution_log": [f"node1_collect_requirements: 已判断流程为 {route_decision}。"],
        }

    @staticmethod
    def _has_explicit_new_generation_intent(user_input: str) -> bool:
        text = (user_input or "").strip().lower()
        new_generation_keywords = (
            "重新生成",
            "全新",
            "新方案",
            "从头",
            "重来",
            "另一个",
            "换一个",
            "restart",
            "from scratch",
        )
        for keyword in new_generation_keywords:
            if keyword in text:
                return True
        return False

    @staticmethod
    def _has_explicit_modify_intent(user_input: str) -> bool:
        raw_text = (user_input or "").strip()
        text = raw_text.lower()
        modify_keywords = (
            "修改",
            "优化",
            "调整",
            "微调",
            "细化",
            "增强",
            "弱化",
            "延续",
            "沿用",
            "继续",
            "保留",
            "基于上次",
            "基于上一版",
            "上一轮",
            "现有方案",
            "当前方案",
            "改成",
            "改为",
            "换成",
        )
        modify_patterns = (
            r"(基于|按照|沿用|延续|保留).{0,12}(上次|上一版|上一轮|现有|当前)",
            r"(把|将).{0,24}(改成|改为|换成)",
            r"(入口|顶部|基座|体块|立面|轮廓|材质|比例|高度|脚本).{0,12}(调整|优化|加强|弱化|简化|保留|改)",
        )
        for keyword in modify_keywords:
            if keyword in text:
                return True
        for pattern in modify_patterns:
            if re.search(pattern, raw_text, re.I):
                return True
        return False

    @classmethod
    def _stabilize_route_decision(
        cls,
        *,
        user_input: str,
        memory: dict[str, Any],
        turn_index_in_run: int,
        route_decision: str,
        should_end: bool,
    ) -> tuple[str, bool, str]:
        if route_decision == "end":
            return "end", True, ""

        has_history = bool(memory.get("last_generated_script_path") or memory.get("conversation_history"))
        if (
            turn_index_in_run <= 1
            and has_history
            and route_decision == "modify_existing"
            and not cls._has_explicit_modify_intent(user_input)
        ):
            return "new_generation", False, "首轮未明确表达基于旧方案修改，已稳定为 new_generation。"

        return route_decision, should_end, ""

    @classmethod
    def _heuristic_route(
        cls,
        user_input: str,
        memory: dict[str, Any],
        *,
        turn_index_in_run: int = 1,
    ) -> tuple[str, bool]:
        raw_text = (user_input or "").strip()
        text = raw_text.lower()
        end_keywords = ("结束", "退出", "停止", "done", "finish", "end", "exit", "quit", "结束吧")

        for keyword in end_keywords:
            if keyword in text:
                return "end", True

        if cls._has_explicit_new_generation_intent(raw_text):
            return "new_generation", False

        has_history = bool(memory.get("last_generated_script_path") or memory.get("conversation_history"))
        if not has_history:
            return "new_generation", False

        if cls._has_explicit_modify_intent(raw_text):
            return "modify_existing", False

        if turn_index_in_run <= 1:
            return "new_generation", False

        return "modify_existing", False

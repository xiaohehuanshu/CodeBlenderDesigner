from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    request: dict[str, Any]
    user_input: str
    turn_index_in_run: int
    node_switches: dict[str, bool]
    session_memory: dict[str, Any]
    route_decision: str
    should_end: bool
    prompt_collection: str
    research_summary: str
    image_analysis_summary: str
    markdown_summary: str
    consolidated_prompt: str
    consolidated_prompt_source: str
    refined_design_brief: str
    refined_design_brief_source: str
    generation_scope: str
    generation_scope_reason: str
    design_brief_base_values: dict[str, str]
    design_brief_active_user_instructions: list[str]
    geometry_context: dict[str, Any]
    geometry_summary: str
    generated_script: str
    generated_script_path: str
    validation_report: str
    runtime_validation_status: str
    runtime_validation_mode: str
    runtime_diagnosis_history: list[dict[str, Any]]
    runtime_failure_deltas: list[dict[str, Any]]
    execution_result: str
    node_results: dict[str, Any]
    execution_log: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]

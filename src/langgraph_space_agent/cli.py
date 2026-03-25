from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .blender_bridge import resolve_blender_executable
from .config import AgentSettings, RunRequest
from .graph import build_design_agent_graph
from .tracing import finish_trace, start_trace, trace_event
from .utils import ensure_directory, load_env_file, load_json_file, write_json_file


END_COMMANDS = {"end", "结束"}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LangGraph architectural design agent")
    parser.add_argument("--prompt", dest="user_input", help="Explicit first-turn design prompt.")
    parser.add_argument("--prompt-file", help="JSON file used as the first-turn prompt source.")
    parser.add_argument("--request-file", help="JSON request/config file path.")
    parser.add_argument("--interactive", action="store_true", help="Enable multi-turn interactive mode.")
    parser.add_argument("--single-turn", action="store_true", help="Force single-turn mode.")
    parser.add_argument(
        "--use-prompt-file-first-turn",
        action="store_true",
        help="Use prompt_file as the first-turn prompt source.",
    )
    parser.add_argument(
        "--stdin-first-turn",
        action="store_true",
        help="Ignore prompt_file for the first turn and ask for input in the terminal.",
    )
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--thread-id", default=None)
    parser.add_argument("--image-dir", default=None)
    parser.add_argument("--markdown-path", default=None)
    parser.add_argument("--geometry-context-path", default=None)
    parser.add_argument("--blender-executable", default=None)
    parser.add_argument("--blend-file", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--output-script-path", default=None)
    parser.add_argument("--skip-script-validation", action="store_true")
    parser.add_argument("--script-validation-timeout", type=int, default=None)
    parser.add_argument("--auto-execute-generated-script", action="store_true")
    parser.add_argument("--disable-all-nodes", action="store_true")
    parser.add_argument("--disable-node1", action="store_true")
    parser.add_argument("--disable-node2", action="store_true")
    parser.add_argument("--disable-node3", action="store_true")
    parser.add_argument("--disable-node4", action="store_true")
    parser.add_argument("--disable-node5", action="store_true")
    parser.add_argument("--disable-node6", action="store_true")
    parser.add_argument("--disable-node7", action="store_true")
    parser.add_argument("--disable-node8", action="store_true")
    return parser


def load_prompt_from_file(path_like: str | None) -> dict[str, Any]:
    if not path_like:
        return {}
    payload = json.loads(Path(path_like).read_text(encoding="utf-8"))
    if isinstance(payload, str):
        return {"user_input": payload}
    if not isinstance(payload, dict):
        raise ValueError("prompt-file must contain either a JSON object or a JSON string.")
    return payload


def load_request_from_args(args: argparse.Namespace) -> RunRequest:
    request_data: dict[str, Any] = {}
    if args.request_file:
        request_data = json.loads(Path(args.request_file).read_text(encoding="utf-8"))

    request_data.pop("user_input", None)

    scalar_fields = [
        "session_id",
        "thread_id",
        "image_dir",
        "markdown_path",
        "geometry_context_path",
        "blender_executable",
        "blend_file",
        "output_dir",
        "output_script_path",
    ]
    for field in scalar_fields:
        value = getattr(args, field)
        if value is not None:
            request_data[field] = value

    if args.user_input is not None:
        request_data["user_input"] = args.user_input
    else:
        request_data["user_input"] = ""

    prompt_file = request_data.get("prompt_file")
    if args.prompt_file is not None:
        prompt_file = args.prompt_file
    if prompt_file is not None:
        request_data["prompt_file"] = prompt_file

    if args.use_prompt_file_first_turn:
        request_data["use_prompt_file_for_first_turn"] = True
    if args.stdin_first_turn:
        request_data["use_prompt_file_for_first_turn"] = False
    if args.prompt_file is not None and not args.stdin_first_turn:
        request_data["use_prompt_file_for_first_turn"] = True

    if args.single_turn:
        request_data["interactive"] = False
    elif args.interactive:
        request_data["interactive"] = True

    node_switches = dict(request_data.get("node_switches", {}))
    if args.disable_all_nodes:
        node_switches["global_enabled"] = False
    if args.disable_node1:
        node_switches["node1_collect_requirements"] = False
    if args.disable_node2:
        node_switches["node2_internet_research"] = False
    if args.disable_node3:
        node_switches["node3_image_analysis"] = False
    if args.disable_node4:
        node_switches["node4_markdown_analysis"] = False
    if args.disable_node5:
        node_switches["node5_geometry_constraints"] = False
    if args.disable_node6:
        node_switches["node6_prompt_synthesis"] = False
    if args.disable_node7:
        node_switches["node7_script_generation"] = False
    if args.disable_node8:
        node_switches["node8_runtime_debug"] = False
    if node_switches:
        request_data["node_switches"] = node_switches

    if args.skip_script_validation:
        request_data["validate_generated_script"] = False
    if args.script_validation_timeout is not None:
        request_data["script_validation_timeout_seconds"] = args.script_validation_timeout

    if args.auto_execute_generated_script:
        request_data["auto_execute_generated_script"] = True

    return RunRequest.model_validate(request_data)


def build_initial_state(request: RunRequest, session_memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "request": request.model_dump(mode="json"),
        "user_input": request.user_input,
        "turn_index_in_run": 1,
        "node_switches": request.node_switches.model_dump(),
        "session_memory": session_memory,
        "node_results": {},
        "execution_log": [],
        "errors": [],
    }


def summarize_turn(result: dict[str, Any]) -> str:
    route_decision = result.get("route_decision") or "unknown"
    generated_script_path = result.get("generated_script_path") or "N/A"
    execution_result = result.get("execution_result") or "No execution result."
    validation_report = (
        result.get("validation_report")
        or ((result.get("node_results") or {}).get("node8_runtime_debug") or {}).get("validation_report")
        or ((result.get("node_results") or {}).get("node7_script_generation") or {}).get("validation_report")
        or "No validation report."
    )
    return (
        f"route_decision={route_decision}\n"
        f"generated_script_path={generated_script_path}\n"
        f"execution_result={execution_result}\n"
        f"validation_report={validation_report}"
    )


def build_memory_payload(
    result: dict[str, Any],
    *,
    previous_memory: dict[str, Any],
    user_input: str,
) -> dict[str, Any]:
    def carry_forward_text(current_key: str, previous_key: str | None = None) -> Any:
        value = result.get(current_key)
        if value not in (None, ""):
            return value
        return previous_memory.get(previous_key or current_key)

    def carry_forward_value(current_key: str, previous_key: str | None = None) -> Any:
        value = result.get(current_key)
        if value is not None:
            return value
        return previous_memory.get(previous_key or current_key)

    conversation_history = list(previous_memory.get("conversation_history", []))
    if user_input:
        conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append(
        {
            "role": "assistant",
            "route_decision": result.get("route_decision"),
            "summary": summarize_turn(result),
            "generated_script_path": result.get("generated_script_path"),
        }
    )
    return {
        "last_route_decision": result.get("route_decision"),
        "last_prompt_collection": carry_forward_text("prompt_collection", "last_prompt_collection"),
        "last_research_summary": carry_forward_text("research_summary", "last_research_summary"),
        "last_image_analysis_summary": carry_forward_text("image_analysis_summary", "last_image_analysis_summary"),
        "last_markdown_summary": carry_forward_text("markdown_summary", "last_markdown_summary"),
        "last_consolidated_prompt": carry_forward_text("consolidated_prompt", "last_consolidated_prompt"),
        "last_consolidated_prompt_source": carry_forward_text("consolidated_prompt_source", "last_consolidated_prompt_source"),
        "last_refined_design_brief": carry_forward_text("refined_design_brief", "last_refined_design_brief"),
        "last_refined_design_brief_source": carry_forward_text(
            "refined_design_brief_source",
            "last_refined_design_brief_source",
        ),
        "last_generation_scope": carry_forward_text("generation_scope", "last_generation_scope"),
        "last_generation_scope_reason": carry_forward_text("generation_scope_reason", "last_generation_scope_reason"),
        "last_geometry_summary": carry_forward_text("geometry_summary", "last_geometry_summary"),
        "design_brief_base_values": carry_forward_value("design_brief_base_values", "design_brief_base_values"),
        "design_brief_active_user_instructions": carry_forward_value(
            "design_brief_active_user_instructions",
            "design_brief_active_user_instructions",
        ),
        "last_generated_script_path": carry_forward_text("generated_script_path", "last_generated_script_path"),
        "last_validation_report": carry_forward_text("validation_report", "last_validation_report"),
        "last_runtime_validation_status": carry_forward_text(
            "runtime_validation_status",
            "last_runtime_validation_status",
        ),
        "last_runtime_validation_mode": carry_forward_text(
            "runtime_validation_mode",
            "last_runtime_validation_mode",
        ),
        "last_execution_result": carry_forward_text("execution_result", "last_execution_result"),
        "last_trace_path": carry_forward_text("trace_path", "last_trace_path"),
        "conversation_history": conversation_history[-20:],
        "node_results": result.get("node_results", {}),
    }


def run_single_turn(
    *,
    graph: Any,
    request: RunRequest,
    settings: AgentSettings,
    turn_index_in_run: int = 1,
) -> dict[str, Any]:
    output_dir = ensure_directory(request.output_dir or settings.default_output_dir)
    trace_path = start_trace(
        output_dir=output_dir,
        session_id=request.session_id,
        thread_id=request.thread_id,
        user_input=request.user_input,
    )
    memory_dir = ensure_directory(output_dir / "memory")
    memory_path = memory_dir / f"{request.session_id}.json"
    session_memory = load_json_file(memory_path, default={})
    graph_thread_id = _build_graph_turn_thread_id(request)

    try:
        initial_state = build_initial_state(request, session_memory)
        initial_state["turn_index_in_run"] = max(1, int(turn_index_in_run))
        trace_event("run.graph_invoke", graph_thread_id=graph_thread_id)
        result = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": graph_thread_id}},
        )
        result["trace_path"] = trace_path
        trace_event(
            "run.graph_completed",
            route_decision=result.get("route_decision"),
            should_end=result.get("should_end"),
            generated_script_path=result.get("generated_script_path"),
        )
        write_json_file(
            memory_path,
            build_memory_payload(result, previous_memory=session_memory, user_input=request.user_input),
        )
        finish_trace(
            "completed",
            route_decision=result.get("route_decision"),
            should_end=result.get("should_end"),
            generated_script_path=result.get("generated_script_path"),
        )
        return result
    except Exception as exc:
        finish_trace("error", error=str(exc))
        raise


def print_result(result: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "route_decision": result.get("route_decision"),
                "should_end": result.get("should_end"),
                "generated_script_path": result.get("generated_script_path"),
                "trace_path": result.get("trace_path"),
                "execution_result": result.get("execution_result"),
                "errors": result.get("errors", []),
                "execution_log": result.get("execution_log", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def print_turn_summary(result: dict[str, Any]) -> None:
    print("Assistant summary:")
    print(summarize_turn(result))


def _should_print_final_result_summary() -> bool:
    return os.getenv("PRINT_CLI_FINAL_RESULT_SUMMARY", "false").strip().lower() == "true"


def maybe_print_final_result_summary(result: dict[str, Any]) -> None:
    if not _should_print_final_result_summary():
        return
    print_result(result)
    print_turn_summary(result)


def is_end_command(value: str) -> bool:
    return value.strip().lower() in END_COMMANDS


def _detect_first_turn_source(request: RunRequest) -> str:
    if request.user_input.strip():
        return "command_line"
    if request.use_prompt_file_for_first_turn:
        return "prompt_file"
    return "stdin"


def _build_graph_turn_thread_id(request: RunRequest) -> str:
    base_thread_id = (request.thread_id or request.session_id or "default").strip() or "default"
    turn_suffix = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{base_thread_id}__turn_{turn_suffix}"


def _should_print_startup_diagnostics() -> bool:
    return os.getenv("PRINT_CLI_DIAGNOSTICS", "false").strip().lower() == "true"


def print_startup_diagnostics(request: RunRequest) -> None:
    if not _should_print_startup_diagnostics():
        return
    resolved_blender = resolve_blender_executable(request.blender_executable)
    source = _detect_first_turn_source(request)
    stdin_is_tty = getattr(sys.stdin, "isatty", lambda: False)()
    print("[CLI] Startup configuration:")
    print(f"[CLI]   module_path={Path(__file__).resolve()}")
    print(f"[CLI]   interactive={request.interactive}")
    print(f"[CLI]   first_turn_source={source}")
    print(f"[CLI]   use_prompt_file_for_first_turn={request.use_prompt_file_for_first_turn}")
    print(f"[CLI]   prompt_file={request.prompt_file or '<none>'}")
    print(f"[CLI]   user_input_present={bool(request.user_input.strip())}")
    print(f"[CLI]   stdin_isatty={stdin_is_tty}")
    print(f"[CLI]   blender_executable_request={request.blender_executable or '<none>'}")
    print(f"[CLI]   blender_executable_resolved={resolved_blender.get('path') or '<none>'}")
    print(f"[CLI]   blender_executable_source={resolved_blender.get('source') or '<unknown>'}")


def _read_user_input(prompt_text: str = "You> ") -> str | None:
    try:
        return input(prompt_text).strip()
    except EOFError:
        print("Interactive input closed or unavailable on stdin. Session ended.")
        return None


def read_required_input(*, intro_message: str) -> str | None:
    print(intro_message)
    while True:
        value = _read_user_input()
        if value is None:
            return None
        if not value:
            continue
        if is_end_command(value):
            print("Session ended by user.")
            return None
        return value


def resolve_first_turn_input(request: RunRequest) -> str | None:
    explicit_input = request.user_input.strip()
    if explicit_input:
        print("Using first-turn prompt from command line.")
        return explicit_input

    if request.use_prompt_file_for_first_turn:
        prompt_payload = load_prompt_from_file(request.prompt_file)
        prompt_value = str(prompt_payload.get("user_input", "")).strip()
        if not prompt_value:
            raise ValueError("prompt_file is enabled for the first turn, but no user_input was found in that file.")
        source = request.prompt_file or "<unknown>"
        print(f"Using first-turn prompt from file: {source}")
        return prompt_value

    return read_required_input(
        intro_message="Enter the first-turn design requirements. Type 'end' to exit.",
    )


def run_interactive_session(
    *,
    graph: Any,
    base_request: RunRequest,
    settings: AgentSettings,
    intro_message: str = "Interactive modification session started. Enter revision notes, or type 'end' to finish.",
) -> None:
    print(intro_message)
    turn_index = 1

    while True:
        current_input = _read_user_input()
        if current_input is None:
            break
        if not current_input:
            continue
        if is_end_command(current_input):
            print("Session ended by user.")
            break

        request = base_request.model_copy(update={"user_input": current_input})
        turn_index += 1
        result = run_single_turn(graph=graph, request=request, settings=settings, turn_index_in_run=turn_index)
        maybe_print_final_result_summary(result)

        if result.get("should_end"):
            print("Session ended by node1 decision.")
            break


def main() -> None:
    load_env_file(Path(__file__).resolve().parents[2] / ".env")
    parser = build_arg_parser()
    args = parser.parse_args()
    request = load_request_from_args(args)
    settings = AgentSettings()
    graph = build_design_agent_graph(settings)

    print_startup_diagnostics(request)
    first_turn_input = resolve_first_turn_input(request)
    if first_turn_input is None:
        return

    first_turn_request = request.model_copy(update={"user_input": first_turn_input})
    result = run_single_turn(graph=graph, request=first_turn_request, settings=settings, turn_index_in_run=1)
    maybe_print_final_result_summary(result)

    if first_turn_request.interactive and not result.get("should_end"):
        followup_request = first_turn_request.model_copy(update={"user_input": ""})
        run_interactive_session(graph=graph, base_request=followup_request, settings=settings)

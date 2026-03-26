from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm_clients import build_stub_script
from ..tracing import trace_event
from ..utils import compact_text, ensure_directory, merge_node_result, now_stamp
from .base import DESIGN_BRIEF_MAX_CHARS
from .node7_codegen_context import Node7CodegenContextMixin
from .node7_codegen_patch import Node7CodegenPatchMixin
from .node7_codegen_staged import Node7CodegenStagedMixin
from .node7_codegen_validation import Node7CodegenValidationMixin


class Node7ScriptGenerationMixin(
    Node7CodegenPatchMixin,
    Node7CodegenStagedMixin,
    Node7CodegenContextMixin,
    Node7CodegenValidationMixin,
):
    @staticmethod
    def _build_generation_note(*, generation_mode: str, stage_metrics: dict[str, Any], used_stub: bool) -> str:
        if used_stub:
            failure_reason = stage_metrics.get("fallback_reason") or "unknown_error"
            return f"Code generation fell back to a stub script. reason={failure_reason}"

        if generation_mode == "modify_existing_local_patch":
            return (
                "Updated the existing script with local patch codegen. "
                f"updated_functions={stage_metrics.get('patch_function_count', 0)}"
            )

        if generation_mode == "modify_existing_full_rewrite":
            fallback_error = stage_metrics.get("local_patch_fallback_error")
            note = "Rewrote the full script because local patching was not suitable."
            if fallback_error:
                note += f" local_patch_error={fallback_error}"
            return note

        if generation_mode == "new_generation_scaffold_patch":
            note = (
                "Completed scaffold-first generation with incremental patches. "
                f"completed_steps={stage_metrics.get('completed_step_count', 0)}"
            )
            if stage_metrics.get("full_script_fallback_error"):
                note += f" quick_path_error={stage_metrics['full_script_fallback_error']}"
            return note

        if generation_mode.startswith("new_generation_scaffold_patch_partial"):
            note = (
                "Scaffold patch generation stopped early and kept the last compilable result. "
                f"completed_steps={stage_metrics.get('completed_step_count', 0)}"
            )
            if stage_metrics.get("failed_step_name"):
                note += f" failed_step={stage_metrics['failed_step_name']}"
            if stage_metrics.get("generation_error"):
                note += f" generation_error={stage_metrics['generation_error']}"
            if stage_metrics.get("compile_error"):
                note += f" compile_error={stage_metrics['compile_error']}"
            return note

        if generation_mode == "full_script_single_pass":
            note = "Completed single-pass full script generation."
            if stage_metrics.get("quick_path_used"):
                note += " source=quick_path"
            return note

        batch_count = ((stage_metrics.get("plan") or {}).get("batch_count")) or 0
        note = f"Completed staged code generation. planned_batches={batch_count}"
        if stage_metrics.get("full_script_fallback_error"):
            note += f" full_script_error={stage_metrics['full_script_fallback_error']}"
        if stage_metrics.get("scaffold_patch_fallback_error"):
            note += f" scaffold_patch_error={stage_metrics['scaffold_patch_fallback_error']}"
        return note

    def node7_script_generation(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node7_script_generation started")
        switches = self._switches(state)
        request = self._request(state)
        if not switches.enabled("node7_script_generation"):
            return self._node_skipped(
                state,
                "node7_script_generation",
                "node is disabled; skipping script generation.",
                {"summary": ""},
            )

        memory = state.get("session_memory", {}) or {}
        route_decision = str(state.get("route_decision") or "new_generation")
        design_prompt = compact_text(str(state.get("consolidated_prompt") or ""), DESIGN_BRIEF_MAX_CHARS)
        design_prompt_source = state.get("consolidated_prompt_source") or "state.consolidated_prompt"
        refined_design_brief = compact_text(str(state.get("refined_design_brief") or ""), DESIGN_BRIEF_MAX_CHARS)
        refined_brief_source = state.get("refined_design_brief_source") or ""
        generation_scope = str(state.get("generation_scope") or "").strip() or "concept_massing"
        generation_scope_reason = str(state.get("generation_scope_reason") or "").strip() or "state_default"
        geometry_summary = compact_text(str(state.get("geometry_summary") or ""), 1500)
        current_user_input = str(state.get("user_input") or "").strip()

        if not design_prompt:
            brief_context = self._resolve_design_brief_context(
                route_decision=route_decision,
                prompt_collection=state.get("prompt_collection", ""),
                research_summary=state.get("research_summary", ""),
                image_summary=state.get("image_analysis_summary", ""),
                markdown_summary=state.get("markdown_summary", ""),
                geometry_summary=geometry_summary,
                memory=memory,
                previous_design_brief=str(memory.get("last_consolidated_prompt") or ""),
            )
            design_prompt, design_prompt_source = self._build_local_design_brief(
                route_decision=route_decision,
                brief_context=brief_context,
            )

        if not refined_design_brief:
            refined_design_brief = design_prompt
            refined_brief_source = design_prompt_source
        else:
            refined_brief_source = refined_brief_source or design_prompt_source

        previous_script_path = memory.get("last_generated_script_path")
        last_run_status = self._build_node7_last_run_status(memory)
        recent_conversation_summary = self._build_node7_recent_conversation_summary(memory)
        previous_script_overview = ""
        previous_script_key_snippets = ""
        previous_script_patch_context = ""
        if route_decision == "modify_existing":
            previous_script_overview = self._build_previous_script_overview(previous_script_path)
            previous_script_key_snippets = self._build_previous_script_key_snippets(previous_script_path)
            if previous_script_path:
                previous_script_patch_context = self._build_previous_script_patch_context(previous_script_path)

        continuity_context = self._build_continuity_context(
            route_decision=route_decision,
            last_run_status=last_run_status,
            recent_conversation_summary=recent_conversation_summary,
            previous_script_overview=previous_script_overview,
            previous_script_key_snippets=previous_script_key_snippets,
        )
        self._emit_substep(
            "node7",
            "generation_scope",
            "resolved",
            f"scope={generation_scope}, reason={generation_scope_reason}",
        )
        prompt_metrics = self._emit_text_metrics(
            "node7 prompt stats",
            raw_design_brief=design_prompt,
            refined_design_brief=refined_design_brief,
            geometry_summary=geometry_summary,
            continuity_context=continuity_context,
            previous_script_key_snippets=previous_script_key_snippets,
            previous_script_patch_context=previous_script_patch_context,
        )
        self._emit_text_block(
            "node7 codegen design_brief",
            refined_design_brief,
            event_name="node7.codegen_design_brief",
            route_decision=route_decision,
            source=refined_brief_source,
            upstream_source=design_prompt_source,
        )

        validation_report = "SKIPPED: local validation was not run."
        generated_script = ""
        generation_mode = "stub"
        stage_metrics: dict[str, Any] = {}
        used_stub = False

        if self.openai_codegen.is_available:
            try:
                if route_decision == "modify_existing":
                    local_patch_error = ""
                    try:
                        self._emit_substep("node7", "local_patch", "started")
                        generated_script, generation_mode, stage_metrics = self._run_local_patch_codegen(
                            current_user_input=current_user_input,
                            refined_design_brief=refined_design_brief or design_prompt,
                            generation_scope=generation_scope,
                            geometry_summary=geometry_summary,
                            continuity_context=continuity_context,
                            previous_script_path=previous_script_path,
                        )
                        self._emit_substep(
                            "node7",
                            "local_patch",
                            "completed",
                            f"updated_functions={stage_metrics.get('patch_function_count', 0)}",
                        )
                    except Exception as exc:
                        local_patch_error = str(exc)
                        self._emit_substep("node7", "local_patch", "failed", local_patch_error)
                        self._emit(f"node7 local patch path failed, fallback to full rewrite: {exc}")
                        self._emit_substep("node7", "full_rewrite", "started", "reason=local_patch_fallback")
                        generated_script, generation_mode, stage_metrics = self._run_full_script_codegen(
                            route_decision=route_decision,
                            current_user_input=current_user_input,
                            refined_design_brief=refined_design_brief or design_prompt,
                            generation_scope=generation_scope,
                            geometry_summary=geometry_summary,
                            continuity_context=continuity_context,
                            previous_script_patch_context=previous_script_patch_context,
                        )
                        stage_metrics = {**stage_metrics, "local_patch_fallback_error": local_patch_error}
                        self._emit_substep("node7", "full_rewrite", "completed")
                else:
                    full_script_error = ""
                    scaffold_patch_error = ""
                    use_quick_path = self._should_use_new_generation_full_script_quick_path(
                        request=request,
                        current_user_input=current_user_input,
                        refined_design_brief=refined_design_brief or design_prompt,
                        generation_scope=generation_scope,
                        geometry_summary=geometry_summary,
                    )
                    self._emit_substep(
                        "node7",
                        "generation_strategy",
                        "resolved",
                        "full_script_quick_path" if use_quick_path else "scaffold_patch_first",
                    )

                    if use_quick_path:
                        try:
                            self._emit_substep("node7", "full_script", "started")
                            generated_script, generation_mode, stage_metrics = self._run_full_script_codegen(
                                route_decision=route_decision,
                                current_user_input=current_user_input,
                                refined_design_brief=refined_design_brief or design_prompt,
                                generation_scope=generation_scope,
                                geometry_summary=geometry_summary,
                                continuity_context=continuity_context,
                                previous_script_patch_context="",
                            )
                            stage_metrics = {**stage_metrics, "quick_path_used": True}
                            self._emit_substep("node7", "full_script", "completed")
                        except Exception as exc:
                            full_script_error = str(exc)
                            self._emit_substep("node7", "full_script", "failed", full_script_error)
                            self._emit(f"node7 full script quick path failed, fallback to scaffold patch: {exc}")

                    quick_path_succeeded = use_quick_path and not full_script_error and generation_mode == "full_script_single_pass"
                    if not quick_path_succeeded:
                        try:
                            self._emit_substep(
                                "node7",
                                "scaffold_patch",
                                "started",
                                "reason=default_path" if not full_script_error else "reason=full_script_fallback",
                            )
                            generated_script, generation_mode, stage_metrics = self._run_scaffold_patch_codegen(
                                current_user_input=current_user_input,
                                refined_design_brief=refined_design_brief or design_prompt,
                                generation_scope=generation_scope,
                                geometry_summary=geometry_summary,
                            )
                            if full_script_error:
                                stage_metrics = {**stage_metrics, "full_script_fallback_error": full_script_error}
                            self._emit_substep(
                                "node7",
                                "scaffold_patch",
                                "completed",
                                f"mode={generation_mode}, completed_steps={stage_metrics.get('completed_step_count', 0)}",
                            )
                        except Exception as exc:
                            scaffold_patch_error = str(exc)
                            self._emit_substep("node7", "scaffold_patch", "failed", scaffold_patch_error)
                            self._emit(f"node7 scaffold patch path failed, fallback to staged generation: {exc}")
                            self._emit_substep("node7", "staged_codegen", "started", "reason=scaffold_patch_fallback")
                            generated_script, generation_mode, stage_metrics = self._run_staged_codegen(
                                route_decision=route_decision,
                                current_user_input=current_user_input,
                                refined_design_brief=refined_design_brief or design_prompt,
                                generation_scope=generation_scope,
                                geometry_summary=geometry_summary,
                            )
                            if full_script_error:
                                stage_metrics = {**stage_metrics, "full_script_fallback_error": full_script_error}
                            stage_metrics = {**stage_metrics, "scaffold_patch_fallback_error": scaffold_patch_error}
                            self._emit_substep(
                                "node7",
                                "staged_codegen",
                                "completed",
                                f"mode={generation_mode}, completed_batches={stage_metrics.get('completed_batch_count', 0)}",
                            )

                validation_report = self._validate_generated_script(
                    script=generated_script,
                    route_decision=route_decision,
                )
                self._emit_substep(
                    "node7",
                    "static_validation",
                    "completed",
                    "passed" if "FAIL:" not in validation_report else "issues_detected",
                )
                self._emit("node7 static validation completed")
            except Exception as exc:
                used_stub = True
                generation_mode = "stub"
                self._emit_substep("node7", "codegen", "failed", str(exc))
                generated_script = build_stub_script(
                    refined_design_brief or design_prompt,
                    geometry_summary or "No geometry summary.",
                    failure_reason=f"Code generation failed: {exc}",
                )
                validation_report = "SKIPPED: fallback stub script."
                stage_metrics = {"fallback_reason": str(exc)}
                self._emit(f"node7 code generation failed, using stub: {exc}")
        else:
            used_stub = True
            self._emit_substep("node7", "codegen", "failed", "openai_codegen_unavailable")
            generated_script = build_stub_script(
                refined_design_brief or design_prompt,
                geometry_summary or "No geometry summary.",
                failure_reason="OpenAI codegen client is unavailable or OPENAI_API_KEY is missing.",
            )
            validation_report = "SKIPPED: fallback stub script."
            stage_metrics = {"fallback_reason": "openai_codegen_unavailable"}
            self._emit("node7 OpenAI codegen client unavailable, using stub script")

        output_dir = ensure_directory(request.get("output_dir") or self.settings.default_output_dir)
        script_dir = ensure_directory(output_dir / "generated_scripts")
        target_path = Path(request["output_script_path"]) if request.get("output_script_path") else script_dir / (
            f"{request.get('session_id', 'default')}_{now_stamp()}.py"
        )
        ensure_directory(target_path.parent)
        target_path.write_text(generated_script, encoding="utf-8")
        self._emit_substep("node7", "write_script", "completed", str(target_path))
        self._emit(f"node7 script written to {target_path}")

        stage_metrics = {**stage_metrics, "used_stub": used_stub}
        note = self._build_generation_note(
            generation_mode=generation_mode,
            stage_metrics=stage_metrics,
            used_stub=used_stub,
        )
        execution_message = "Script generated, not executed."

        trace_event(
            "node7.codegen_result",
            route_decision=route_decision,
            generation_mode=generation_mode,
            refined_brief_source=refined_brief_source,
            generation_scope=generation_scope,
            used_stub=used_stub,
            stage_metrics=stage_metrics,
        )
        self._emit_substep(
            "node7",
            "result",
            "completed" if not used_stub else "fallback",
            f"mode={generation_mode}",
        )
        self._emit(
            f"node7_script_generation completed: status={'fallback' if used_stub else 'completed'}, mode={generation_mode}"
        )

        node_status = "fallback" if used_stub else "completed"
        return {
            "generated_script": generated_script,
            "generated_script_path": str(target_path),
            "validation_report": validation_report,
            "runtime_validation_status": "skipped",
            "runtime_validation_mode": "none",
            "execution_result": execution_message,
            "node_results": merge_node_result(
                state.get("node_results"),
                "node7_script_generation",
                {
                    "status": node_status,
                    "generation_mode": generation_mode,
                    "summary": note,
                    "prompt_metrics": prompt_metrics,
                    "brief_refinement_source": refined_brief_source,
                    "generation_scope": generation_scope,
                    "generation_scope_reason": generation_scope_reason,
                    "stage_metrics": stage_metrics,
                    "validation_report": validation_report,
                    "runtime_validation_status": "skipped",
                    "runtime_validation_mode": "none",
                    "generated_script_path": str(target_path),
                    "execution_result": execution_message,
                    "used_stub": used_stub,
                },
            ),
            "execution_log": [f"node7_script_generation: {note}"],
        }

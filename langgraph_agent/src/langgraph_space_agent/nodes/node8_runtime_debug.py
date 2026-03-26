from __future__ import annotations

from pathlib import Path
from typing import Any

from ..blender_bridge import execute_blender_script
from ..utils import compact_text, merge_node_result
from .base import DESIGN_BRIEF_MAX_CHARS


RUNTIME_REPAIR_MAX_ATTEMPTS = 2


class Node8RuntimeDebugMixin:
    @staticmethod
    def _build_runtime_result(
        *,
        status: str,
        stage: str,
        mode: str,
        message: str,
        stdout_preview: str = "",
        stderr_preview: str = "",
    ) -> dict[str, Any]:
        return {
            "status": status,
            "stage": stage,
            "mode": mode,
            "message": message,
            "stdout_preview": stdout_preview,
            "stderr_preview": stderr_preview,
        }

    @classmethod
    def _build_static_validation_failure_result(
        cls,
        *,
        validation_report: str,
        message: str,
    ) -> dict[str, Any]:
        return cls._build_runtime_result(
            status="failed",
            stage="static_validation",
            mode="static_validation",
            message=message,
            stderr_preview=compact_text(validation_report, 900),
        )

    def node8_runtime_debug(self, state: dict[str, Any]) -> dict[str, Any]:
        self._emit("node8_runtime_debug started")
        switches = self._switches(state)
        request = self._request(state)
        if not switches.enabled("node8_runtime_debug"):
            return self._node_skipped(
                state,
                "node8_runtime_debug",
                "node is disabled; skipping runtime validation and repair.",
                {"summary": ""},
            )

        node_results = state.get("node_results") or {}
        node7_result = node_results.get("node7_script_generation") or {}
        generated_script_path = str(state.get("generated_script_path") or node7_result.get("generated_script_path") or "")
        if not generated_script_path:
            return self._node_skipped(
                state,
                "node8_runtime_debug",
                "no generated script path found; nothing to validate.",
                {"summary": ""},
            )

        target_path = Path(generated_script_path)
        generated_script = str(state.get("generated_script") or "")
        if not generated_script and target_path.exists():
            generated_script = target_path.read_text(encoding="utf-8", errors="ignore")
        if not generated_script:
            return self._node_skipped(
                state,
                "node8_runtime_debug",
                "generated script content is empty; nothing to validate.",
                {"summary": ""},
            )

        memory = state.get("session_memory", {}) or {}
        route_decision = str(state.get("route_decision") or "new_generation")
        current_user_input = str(state.get("user_input") or "").strip()
        refined_design_brief = compact_text(
            str(state.get("refined_design_brief") or state.get("consolidated_prompt") or ""),
            DESIGN_BRIEF_MAX_CHARS,
        )
        generation_scope = str(state.get("generation_scope") or "").strip() or "concept_massing"
        geometry_summary = compact_text(str(state.get("geometry_summary") or ""), 1500)
        previous_script_path = memory.get("last_generated_script_path")
        last_run_status = self._build_node7_last_run_status(memory)
        recent_conversation_summary = self._build_node7_recent_conversation_summary(memory)
        previous_script_overview = ""
        previous_script_key_snippets = ""
        if route_decision == "modify_existing":
            previous_script_overview = self._build_previous_script_overview(previous_script_path)
            previous_script_key_snippets = self._build_previous_script_key_snippets(previous_script_path)
        continuity_context = self._build_continuity_context(
            route_decision=route_decision,
            last_run_status=last_run_status,
            recent_conversation_summary=recent_conversation_summary,
            previous_script_overview=previous_script_overview,
            previous_script_key_snippets=previous_script_key_snippets,
        )

        static_validation_report = str(
            state.get("validation_report")
            or node7_result.get("validation_report")
            or "SKIPPED: static validation was not run."
        ).strip()
        validation_sections = [static_validation_report] if static_validation_report else []
        runtime_validation_result = self._build_runtime_result(
            status="skipped",
            stage="none",
            mode="none",
            message="SKIPPED: Blender runtime validation was not run.",
        )
        runtime_repair_attempts: list[dict[str, Any]] = []
        runtime_diagnosis_history: list[dict[str, Any]] = []
        failure_deltas: list[dict[str, Any]] = []
        used_stub = bool(node7_result.get("used_stub"))

        should_validate_script = request.get("validate_generated_script")
        if should_validate_script is None:
            should_validate_script = self.settings.validate_generated_script
        should_execute_script = request.get("auto_execute_generated_script")
        if should_execute_script is None:
            should_execute_script = self.settings.auto_execute_generated_script

        repair_failure_result: dict[str, Any] | None = None

        if should_validate_script:
            if used_stub:
                runtime_validation_result = self._build_runtime_result(
                    status="skipped",
                    stage="none",
                    mode="stub_script",
                    message="SKIPPED: Blender runtime validation skipped because node7 produced a stub script.",
                )
                validation_sections.append(runtime_validation_result["message"])
                self._emit_substep("node8", "runtime_validation", "skipped", "reason=stub_script")
            elif "FAIL:" in static_validation_report:
                runtime_validation_result = self._build_static_validation_failure_result(
                    validation_report=static_validation_report,
                    message="FAIL: Static validation failed before Blender runtime validation.",
                )
                validation_sections.append(runtime_validation_result["message"])
                repair_failure_result = runtime_validation_result
                self._emit_substep("node8", "runtime_validation", "skipped", "reason=static_validation_failed")
            else:
                self._emit_substep("node8", "runtime_validation", "started")
                runtime_validation_result = self._validate_generated_script_runtime(
                    script_path=str(target_path),
                    blender_executable=request.get("blender_executable") or self.settings.blender_executable,
                    blend_file=request.get("blend_file"),
                    route_decision=route_decision,
                    timeout_seconds=request.get("script_validation_timeout_seconds")
                    or self.settings.script_validation_timeout_seconds,
                )
                validation_sections.append(self._format_runtime_validation_report(runtime_validation_result))
                self._emit_substep(
                    "node8",
                    "runtime_validation",
                    "completed",
                    f"status={runtime_validation_result.get('status')}, mode={runtime_validation_result.get('mode')}",
                )
                if runtime_validation_result.get("status") == "failed":
                    repair_failure_result = runtime_validation_result
        else:
            validation_sections.append("SKIPPED: Blender runtime validation disabled by configuration.")
            self._emit_substep("node8", "runtime_validation", "skipped", "reason=disabled")

        if repair_failure_result:
            failure_signature = self._build_failure_signature(repair_failure_result)
            self._emit_substep(
                "node8",
                "capture_failure",
                "completed",
                compact_text(failure_signature or str(repair_failure_result.get("message") or ""), 220),
            )
            self._emit_substep("node8", "diagnose_failure", "started")
            current_diagnosis, diagnosis_source = self._diagnose_runtime_failure(
                current_user_input=current_user_input,
                refined_design_brief=refined_design_brief,
                current_script_path=str(target_path),
                script_text=generated_script,
                runtime_validation_result=repair_failure_result,
            )
            runtime_diagnosis_history.append(
                {
                    "diagnosis_index": len(runtime_diagnosis_history) + 1,
                    "source": diagnosis_source,
                    "failure_signature": failure_signature,
                    "payload": current_diagnosis,
                }
            )
            self._emit_substep(
                "node8",
                "diagnose_failure",
                "completed",
                f"kind={current_diagnosis.get('failure_kind')}, confidence={current_diagnosis.get('confidence')}, source={diagnosis_source}",
            )
            repair_targets = ", ".join(current_diagnosis.get("target_functions") or []) or "<none>"
            self._emit_substep("node8", "repair_scope", "completed", f"targets={compact_text(repair_targets, 180)}")

            self._emit_substep("node8", "fast_fix", "started")
            repaired_script, fast_fix_kind, fast_fix_metrics = self._try_high_confidence_fast_fix(
                script_text=generated_script,
                runtime_validation_result=repair_failure_result,
                diagnosis_payload=current_diagnosis,
            )
            latest_failure_delta: dict[str, Any] = {}
            if fast_fix_metrics:
                generated_script = repaired_script
                self._emit_substep("node8", "revalidate", "started", f"source=fast_fix:{fast_fix_kind}")
                (
                    static_validation_report,
                    runtime_validation_result,
                    revalidation_sections,
                    static_validation_passed,
                ) = self._revalidate_runtime_debug_candidate(
                    script_text=generated_script,
                    target_path=target_path,
                    route_decision=route_decision,
                    request=request,
                    label=(
                        f"diagnosis-driven fast fix {fast_fix_kind} applied "
                        f"{len(fast_fix_metrics)} edit(s)."
                    ),
                )
                validation_sections.extend(revalidation_sections)
                latest_failure_delta = self._compare_runtime_failures(
                    previous_result=repair_failure_result,
                    current_result=runtime_validation_result,
                )
                failure_deltas.append({"stage": "fast_fix", **latest_failure_delta})
                self._emit_substep(
                    "node8",
                    "failure_delta",
                    "completed",
                    compact_text(str(latest_failure_delta.get("summary") or ""), 220),
                )
                deterministic_passed = (
                    static_validation_passed
                    and runtime_validation_result.get("status") in {"passed", "partial"}
                )
                runtime_repair_attempts.append(
                    {
                        "attempt_index": 0,
                        "repair_mode": fast_fix_kind,
                        "repair_metrics": fast_fix_metrics,
                        "diagnosis_source": diagnosis_source,
                        "diagnosis_failure_kind": current_diagnosis.get("failure_kind"),
                        "diagnosis_target_functions": current_diagnosis.get("target_functions"),
                        "static_validation_passed": static_validation_passed,
                        "runtime_validation_status": runtime_validation_result.get("status"),
                        "runtime_validation_mode": runtime_validation_result.get("mode"),
                        "failure_delta_summary": latest_failure_delta.get("summary"),
                    }
                )
                self._emit_substep(
                    "node8",
                    "revalidate",
                    "completed",
                    f"status={runtime_validation_result.get('status')}, mode={runtime_validation_result.get('mode')}",
                )
                self._emit_substep(
                    "node8",
                    "fast_fix",
                    "completed" if deterministic_passed else "failed",
                    f"kind={fast_fix_kind}, edits={len(fast_fix_metrics)}, status={runtime_validation_result.get('status')}",
                )
                if deterministic_passed:
                    repair_failure_result = None
                else:
                    repair_failure_result = runtime_validation_result
                    self._emit_substep("node8", "diagnose_failure", "started", "reason=post_fast_fix_failure")
                    previous_diagnosis = current_diagnosis
                    current_diagnosis, diagnosis_source = self._diagnose_runtime_failure(
                        current_user_input=current_user_input,
                        refined_design_brief=refined_design_brief,
                        current_script_path=str(target_path),
                        script_text=generated_script,
                        runtime_validation_result=repair_failure_result,
                        previous_diagnosis=previous_diagnosis,
                        failure_delta=latest_failure_delta,
                    )
                    runtime_diagnosis_history.append(
                        {
                            "diagnosis_index": len(runtime_diagnosis_history) + 1,
                            "source": diagnosis_source,
                            "failure_signature": self._build_failure_signature(repair_failure_result),
                            "payload": current_diagnosis,
                        }
                    )
                    self._emit_substep(
                        "node8",
                        "diagnose_failure",
                        "completed",
                        f"kind={current_diagnosis.get('failure_kind')}, confidence={current_diagnosis.get('confidence')}, source={diagnosis_source}",
                    )
                    repair_targets = ", ".join(current_diagnosis.get("target_functions") or []) or "<none>"
                    self._emit_substep("node8", "repair_scope", "completed", f"targets={compact_text(repair_targets, 180)}")
            else:
                fast_fix_reason = "reason=no_applicable_fix"
                if str(current_diagnosis.get("fast_fix_kind") or "").strip() == "structrna_boolean_lifecycle":
                    fast_fix_reason = "reason=matched_but_no_edit"
                self._emit_substep("node8", "fast_fix", "skipped", fast_fix_reason)

        if repair_failure_result:
            if not self.openai_codegen.is_available:
                validation_sections.append(
                    "SKIPPED: Automatic runtime repair is unavailable because the OpenAI codegen client is not configured."
                )
                self._emit_substep("node8", "runtime_repair", "skipped", "reason=openai_codegen_unavailable")
            else:
                self._emit_substep("node8", "runtime_repair", "started")
                latest_static_validation = static_validation_report
                latest_runtime_result = repair_failure_result
                repair_succeeded = False
                latest_diagnosis = current_diagnosis if repair_failure_result else {}
                latest_diagnosis_source = diagnosis_source if repair_failure_result else ""
                latest_failure_delta = failure_deltas[-1] if failure_deltas else {}

                for attempt_index in range(1, RUNTIME_REPAIR_MAX_ATTEMPTS + 1):
                    attempt_name = f"repair_attempt{attempt_index}"
                    try:
                        if attempt_index > 1:
                            self._emit_substep("node8", "diagnose_failure", "started", f"reason=before_{attempt_name}")
                            previous_diagnosis = latest_diagnosis
                            latest_diagnosis, latest_diagnosis_source = self._diagnose_runtime_failure(
                                current_user_input=current_user_input,
                                refined_design_brief=refined_design_brief,
                                current_script_path=str(target_path),
                                script_text=generated_script,
                                runtime_validation_result=latest_runtime_result,
                                previous_diagnosis=previous_diagnosis,
                                failure_delta=latest_failure_delta,
                            )
                            runtime_diagnosis_history.append(
                                {
                                    "diagnosis_index": len(runtime_diagnosis_history) + 1,
                                    "source": latest_diagnosis_source,
                                    "failure_signature": self._build_failure_signature(latest_runtime_result),
                                    "payload": latest_diagnosis,
                                }
                            )
                            self._emit_substep(
                                "node8",
                                "diagnose_failure",
                                "completed",
                                f"kind={latest_diagnosis.get('failure_kind')}, confidence={latest_diagnosis.get('confidence')}, source={latest_diagnosis_source}",
                            )
                        repair_targets = ", ".join(latest_diagnosis.get("target_functions") or []) or "<none>"
                        self._emit_substep("node8", "repair_scope", "completed", f"targets={compact_text(repair_targets, 180)}")
                        self._emit_substep("node8", attempt_name, "started")
                        attempt_input_failure = dict(latest_runtime_result)
                        generated_script, _repair_mode, repair_metrics = self._run_runtime_repair_codegen(
                            current_user_input=current_user_input,
                            refined_design_brief=refined_design_brief,
                            generation_scope=generation_scope,
                            geometry_summary=geometry_summary,
                            continuity_context=continuity_context,
                            current_script_path=str(target_path),
                            runtime_validation_result=latest_runtime_result,
                            attempt_index=attempt_index,
                            diagnosis_payload=latest_diagnosis,
                            failure_delta=latest_failure_delta,
                        )
                        repair_review = self._audit_runtime_patch_scope(
                            applied_functions=repair_metrics.get("applied_functions") or [],
                            diagnosis_payload=latest_diagnosis,
                        )
                        repair_metrics["repair_review"] = repair_review
                        self._emit_substep(
                            "node8",
                            "repair_review",
                            "completed",
                            compact_text(str(repair_review.get("summary") or ""), 220),
                        )
                        self._emit_substep("node8", "revalidate", "started", f"source={attempt_name}")
                        (
                            latest_static_validation,
                            latest_runtime_result,
                            revalidation_sections,
                            static_validation_passed,
                        ) = self._revalidate_runtime_debug_candidate(
                            script_text=generated_script,
                            target_path=target_path,
                            route_decision=route_decision,
                            request=request,
                            label=(
                                f"automatic runtime repair attempt {attempt_index} applied "
                                f"{repair_metrics.get('patch_function_count', 0)} function patch(es)."
                            ),
                        )
                        validation_sections.extend(revalidation_sections)

                        attempt_passed = (
                            static_validation_passed
                            and latest_runtime_result.get("status") in {"passed", "partial"}
                        )
                        latest_failure_delta = self._compare_runtime_failures(
                            previous_result=attempt_input_failure,
                            current_result=latest_runtime_result,
                        )
                        if repair_review.get("status") in {"expanded", "off_target", "unclear"}:
                            review_summary = compact_text(str(repair_review.get("summary") or ""), 180)
                            if review_summary:
                                latest_failure_delta["repair_review_summary"] = review_summary
                                latest_failure_delta["summary"] = compact_text(
                                    f"{latest_failure_delta.get('summary') or ''} Patch review: {review_summary}".strip(),
                                    500,
                                )
                        failure_deltas.append({"attempt_index": attempt_index, **latest_failure_delta})
                        self._emit_substep(
                            "node8",
                            "failure_delta",
                            "completed",
                            compact_text(str(latest_failure_delta.get("summary") or ""), 220),
                        )
                        repair_metrics = {
                            **repair_metrics,
                            "diagnosis_source": latest_diagnosis_source,
                            "failure_delta_summary": latest_failure_delta.get("summary"),
                            "static_validation_passed": static_validation_passed,
                            "runtime_validation_status": latest_runtime_result.get("status"),
                            "runtime_validation_mode": latest_runtime_result.get("mode"),
                        }
                        runtime_repair_attempts.append(repair_metrics)
                        self._emit_substep(
                            "node8",
                            "revalidate",
                            "completed",
                            f"status={latest_runtime_result.get('status')}, mode={latest_runtime_result.get('mode')}",
                        )
                        self._emit_substep(
                            "node8",
                            attempt_name,
                            "completed" if attempt_passed else "failed",
                            f"status={latest_runtime_result.get('status')}, mode={latest_runtime_result.get('mode')}",
                        )

                        if attempt_passed:
                            repair_succeeded = True
                            static_validation_report = latest_static_validation
                            runtime_validation_result = latest_runtime_result
                            break

                        runtime_validation_result = latest_runtime_result
                    except Exception as exc:
                        runtime_repair_attempts.append({"attempt_index": attempt_index, "repair_error": str(exc)})
                        validation_sections.append(
                            f"INFO: automatic runtime repair attempt {attempt_index} failed before validation: {exc}"
                        )
                        latest_failure_delta = {
                            "changed": False,
                            "same_root_cause": True,
                            "summary": f"Repair attempt {attempt_index} failed before revalidation: {exc}",
                        }
                        failure_deltas.append({"attempt_index": attempt_index, **latest_failure_delta})
                        self._emit_substep("node8", attempt_name, "failed", str(exc))
                        break

                if not repair_succeeded:
                    static_validation_report = latest_static_validation
                    self._emit_substep(
                        "node8",
                        "runtime_repair",
                        "failed",
                        f"attempts={len(runtime_repair_attempts)}",
                    )
                else:
                    self._emit_substep(
                        "node8",
                        "runtime_repair",
                        "completed",
                        f"attempts={len(runtime_repair_attempts)}",
                    )

        final_validation_report = "\n".join(part for part in validation_sections if part).strip()

        execution_message = str(state.get("execution_result") or "Script generated, not executed.")
        validation_passed = "FAIL:" not in static_validation_report and (
            not should_validate_script or used_stub or runtime_validation_result.get("status") in {"passed", "partial"}
        )
        if should_execute_script and used_stub:
            execution_message = "Stub script generated, so auto-execution was skipped."
            self._emit_substep("node8", "execute_script", "skipped", "reason=stub_script")
        elif should_execute_script:
            if not validation_passed:
                execution_message = "Script validation did not pass, so auto-execution was skipped."
                self._emit_substep("node8", "execute_script", "skipped", "reason=validation_failed")
            else:
                try:
                    self._emit_substep("node8", "execute_script", "started")
                    execution_message = execute_blender_script(
                        script_path=str(target_path),
                        blender_executable=request.get("blender_executable") or self.settings.blender_executable,
                        blend_file=request.get("blend_file"),
                    )
                    self._emit_substep("node8", "execute_script", "completed")
                except Exception as exc:
                    execution_message = f"Script execution failed: {exc}"
                    self._emit_substep("node8", "execute_script", "failed", str(exc))

        summary_parts = []
        if should_validate_script:
            summary_parts.append(
                f"runtime_validation={runtime_validation_result.get('status')}({runtime_validation_result.get('mode')})"
            )
        else:
            summary_parts.append("runtime_validation=disabled")
        if runtime_diagnosis_history:
            summary_parts.append(f"runtime_diagnoses={len(runtime_diagnosis_history)}")
        if runtime_repair_attempts:
            summary_parts.append(f"runtime_repair_attempts={len(runtime_repair_attempts)}")
        if should_execute_script:
            if "failed" in execution_message.lower() or "skipped" in execution_message.lower():
                summary_parts.append("auto_execute=skipped_or_failed")
            else:
                summary_parts.append("auto_execute=done")
        note = ", ".join(summary_parts) or "runtime validation skipped"

        self._emit_substep(
            "node8",
            "result",
            "completed",
            f"status={runtime_validation_result.get('status')}, mode={runtime_validation_result.get('mode')}",
        )
        self._emit(
            "node8_runtime_debug completed: "
            f"status={runtime_validation_result.get('status')}, mode={runtime_validation_result.get('mode')}"
        )

        return {
            "generated_script": generated_script,
            "generated_script_path": str(target_path),
            "validation_report": final_validation_report,
            "runtime_validation_status": str(runtime_validation_result.get("status") or "skipped"),
            "runtime_validation_mode": str(runtime_validation_result.get("mode") or "none"),
            "runtime_diagnosis_history": runtime_diagnosis_history,
            "runtime_failure_deltas": failure_deltas,
            "execution_result": execution_message,
            "node_results": merge_node_result(
                state.get("node_results"),
                "node8_runtime_debug",
                {
                    "status": "completed",
                    "summary": note,
                    "validation_report": final_validation_report,
                    "runtime_validation_status": str(runtime_validation_result.get("status") or "skipped"),
                    "runtime_validation_mode": str(runtime_validation_result.get("mode") or "none"),
                    "runtime_diagnosis_history": runtime_diagnosis_history,
                    "runtime_failure_deltas": failure_deltas,
                    "runtime_repair_attempts": runtime_repair_attempts,
                    "generated_script_path": str(target_path),
                    "execution_result": execution_message,
                },
            ),
            "execution_log": [f"node8_runtime_debug: {note}"],
        }

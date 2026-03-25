from __future__ import annotations

from typing import Any

from ..blender_bridge import validate_blender_script


class Node7CodegenValidationMixin:
    def _validate_generated_script_runtime(
        self,
        *,
        script_path: str,
        blender_executable: str | None,
        blend_file: str | None,
        route_decision: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        return validate_blender_script(
            script_path=script_path,
            blender_executable=blender_executable,
            blend_file=blend_file,
            route_decision=route_decision,
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def _format_runtime_validation_report(result: dict[str, Any]) -> str:
        lines = [str(result.get("message") or "SKIPPED: Blender runtime validation was not run.")]
        stdout_preview = str(result.get("stdout_preview") or "").strip()
        stderr_preview = str(result.get("stderr_preview") or "").strip()
        if stdout_preview:
            lines.append(f"INFO: Blender stdout preview: {stdout_preview}")
        if stderr_preview:
            lines.append(f"INFO: Blender stderr preview: {stderr_preview}")
        return "\n".join(lines)

    @staticmethod
    def _validate_generated_script(*, script: str, route_decision: str) -> str:
        checks: list[str] = []
        normalized = script or ""

        if "import bpy" in normalized:
            checks.append("PASS: script imports bpy.")
        else:
            checks.append("FAIL: script does not import bpy.")

        if "def generate_building" in normalized:
            checks.append("PASS: generate_building() is defined.")
        else:
            checks.append("FAIL: generate_building() is missing.")

        if "__name__ == \"__main__\"" in normalized or "__name__ == '__main__'" in normalized:
            checks.append("FAIL: script contains a __main__ guard, which is forbidden.")
        else:
            checks.append("PASS: no __main__ guard found.")

        if "generate_building()" in normalized:
            checks.append("PASS: generate_building() is directly invoked.")
        else:
            checks.append("FAIL: script does not directly call generate_building().")

        facade_keywords = ("Facade", "Window", "Canopy", "Parapet", "Screen", "Frame", "Louver", "Fin")
        if any(keyword in normalized for keyword in facade_keywords):
            checks.append("PASS: facade or detail-related object naming is present.")
        else:
            checks.append("WARN: facade/detail object naming is not obvious.")

        destructive_scene_wipe = (
            "bpy.ops.object.select_all(action=\"SELECT\")" in normalized and "bpy.ops.object.delete" in normalized
        )
        if route_decision == "modify_existing" and destructive_scene_wipe:
            checks.append("FAIL: modify_existing mode should avoid wiping the whole scene.")
        elif destructive_scene_wipe:
            checks.append("WARN: script clears the whole scene before generating.")

        if "for " in normalized:
            checks.append("PASS: script appears to use iterative or procedural logic.")
        else:
            checks.append("WARN: script may not be using reusable procedural loops.")

        if ".fill_mode = 'FULL'" in normalized or '.fill_mode = "FULL"' in normalized:
            checks.append("FAIL: curve fill_mode uses 'FULL', which is not a valid Blender enum here.")

        if "bpy.mathutils.Vector(" in normalized:
            checks.append("FAIL: script uses bpy.mathutils.Vector(...); use Vector from mathutils instead.")

        if ".use_auto_smooth" in normalized:
            checks.append("WARN: script uses use_auto_smooth, which may be unsupported in newer Blender versions.")

        if "bpy.ops.mesh.remove_doubles" in normalized:
            checks.append("WARN: script uses remove_doubles; prefer merge_by_distance for better version compatibility.")

        has_half_scaled_cube_helper = (
            "bmesh.ops.create_cube(bm, size=1.0)" in normalized
            and "size[0] * 0.5" in normalized
            and "size[1] * 0.5" in normalized
            and "size[2] * 0.5" in normalized
        )
        if has_half_scaled_cube_helper:
            checks.append(
                "FAIL: script appears to double-apply half extents in a bmesh cube helper; box volumes may be undersized and float above ground."
            )

        return "\n".join(checks)

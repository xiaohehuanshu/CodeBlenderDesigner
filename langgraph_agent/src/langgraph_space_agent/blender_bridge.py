from __future__ import annotations

import os
import py_compile
import re
import runpy
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .utils import compact_text, load_json_file

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None


COMMON_WINDOWS_BLENDER_PATHS = (
    r"C:\Program Files\Blender Foundation\Blender\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
    r"C:\Program Files (x86)\Blender Foundation\Blender\blender.exe",
)


def _normalize_blender_candidate(path_like: str | None) -> str:
    text = str(path_like or "").strip().strip("\"")
    if not text:
        return ""
    exe_match = re.match(r"^(.*?\.exe)(?:,\d+)?$", text, flags=re.IGNORECASE)
    if exe_match:
        text = exe_match.group(1)
    candidate = Path(text).expanduser()
    if candidate.is_dir():
        candidate = candidate / "blender.exe"
    return str(candidate)


def _iter_windows_registry_blender_candidates() -> list[tuple[str, str]]:
    if os.name != "nt" or winreg is None:
        return []

    registry_roots = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    )

    candidates: list[tuple[str, str]] = []
    for hive, root in registry_roots:
        try:
            with winreg.OpenKey(hive, root) as uninstall_key:
                subkey_count = winreg.QueryInfoKey(uninstall_key)[0]
                for index in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(uninstall_key, index)
                        with winreg.OpenKey(uninstall_key, subkey_name) as app_key:
                            display_name = str(winreg.QueryValueEx(app_key, "DisplayName")[0] or "")
                            if "blender" not in display_name.lower():
                                continue
                            try:
                                install_location = str(winreg.QueryValueEx(app_key, "InstallLocation")[0] or "")
                            except OSError:
                                install_location = ""
                            try:
                                display_icon = str(winreg.QueryValueEx(app_key, "DisplayIcon")[0] or "")
                            except OSError:
                                display_icon = ""
                            if display_icon:
                                candidates.append((display_icon, "windows_registry_display_icon"))
                            if install_location:
                                candidates.append((install_location, "windows_registry_install_location"))
                    except OSError:
                        continue
        except OSError:
            continue
    return candidates


def resolve_blender_executable(blender_executable: str | None = None) -> dict[str, str]:
    seen: set[str] = set()
    candidates: list[tuple[str, str]] = []

    def add_candidate(path_like: str | None, source: str) -> None:
        normalized = _normalize_blender_candidate(path_like)
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        candidates.append((normalized, source))

    add_candidate(blender_executable, "request_or_config")
    add_candidate(os.getenv("BLENDER_EXECUTABLE"), "env_BLENDER_EXECUTABLE")
    add_candidate(shutil.which("blender"), "system_PATH")
    add_candidate(shutil.which("blender.exe"), "system_PATH")
    for common_path in COMMON_WINDOWS_BLENDER_PATHS:
        add_candidate(common_path, "common_windows_path")
    for candidate_path, source in _iter_windows_registry_blender_candidates():
        add_candidate(candidate_path, source)

    for candidate_path, source in candidates:
        candidate = Path(candidate_path)
        if candidate.exists() and candidate.is_file():
            return {"path": str(candidate), "source": source}

    return {"path": "", "source": "not_found"}


def export_geometry_context(
    *,
    blender_executable: str | None,
    blend_file: str,
    exporter_script: str,
    output_json_path: str,
) -> tuple[dict[str, Any], str]:
    resolved = resolve_blender_executable(blender_executable)
    resolved_path = resolved.get("path") or ""
    if not resolved_path:
        raise RuntimeError("No Blender executable was configured or auto-detected for geometry export.")
    command = [
        resolved_path,
        blend_file,
        "--background",
        "--python",
        exporter_script,
        "--",
        output_json_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Blender geometry export failed.")
    payload = load_json_file(output_json_path, default={})
    return payload, result.stdout.strip()


def execute_blender_script(
    *,
    script_path: str,
    blender_executable: str | None = None,
    blend_file: str | None = None,
) -> str:
    resolved = resolve_blender_executable(blender_executable)
    resolved_path = resolved.get("path") or ""
    if resolved_path:
        command = [resolved_path]
        if blend_file:
            command.append(blend_file)
        command.extend(["--background", "--python", script_path])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        runtime_error = _extract_blender_python_runtime_error(result.stdout, result.stderr)
        if result.returncode != 0 or runtime_error:
            raise RuntimeError(
                runtime_error
                or result.stderr.strip()
                or result.stdout.strip()
                or "Generated Blender script execution failed."
            )
        return result.stdout.strip()

    try:
        import bpy  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "No Blender executable was configured or auto-detected, and bpy is not available in current Python."
        ) from exc

    runpy.run_path(script_path, run_name="__main__")
    return f"Executed in-process: {script_path}"


def validate_blender_script(
    *,
    script_path: str,
    blender_executable: str | None = None,
    blend_file: str | None = None,
    route_decision: str = "new_generation",
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    script_file = Path(script_path)
    resolved = resolve_blender_executable(blender_executable)
    resolved_path = resolved.get("path") or ""
    resolved_source = resolved.get("source") or "unknown"
    report: dict[str, Any] = {
        "status": "skipped",
        "stage": "none",
        "mode": "none",
        "message": "SKIPPED: Blender runtime validation was not run.",
        "stdout_preview": "",
        "stderr_preview": "",
        "resolved_blender_executable": resolved_path,
        "resolved_blender_source": resolved_source,
    }

    try:
        py_compile.compile(str(script_file), doraise=True)
    except py_compile.PyCompileError as exc:
        report.update(
            {
                "status": "failed",
                "stage": "python_compile",
                "mode": "py_compile",
                "message": f"FAIL: Python compile check failed: {exc}",
            }
        )
        return report

    report.update(
        {
            "status": "partial",
            "stage": "python_compile",
            "mode": "py_compile",
            "message": "PASS: Python compile check passed.",
        }
    )

    if not resolved_path:
        report.update(
            {
                "status": "partial",
                "stage": "python_compile",
                "mode": "py_compile_only",
                "message": "PASS: Python compile check passed. WARN: Blender runtime validation skipped because no Blender executable was configured or auto-detected.",
            }
        )
        return report

    try:
        runtime_result = _run_blender_validation_subprocess(
            script_path=str(script_file),
            blender_executable=resolved_path,
            blend_file=blend_file,
            route_decision=route_decision,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        report.update(
            {
                "status": "failed",
                "stage": "blender_runtime",
                "mode": "timeout",
                "message": f"FAIL: Blender runtime validation timed out after {timeout_seconds} seconds.",
                "stdout_preview": compact_text((exc.stdout or "").strip(), 600),
                "stderr_preview": compact_text((exc.stderr or "").strip(), 600),
            }
        )
        return report
    except Exception as exc:
        report.update(
            {
                "status": "failed",
                "stage": "blender_runtime",
                "mode": "subprocess_error",
                "message": f"FAIL: Blender runtime validation failed to start: {exc}",
            }
        )
        return report

    report.update(runtime_result)
    report["resolved_blender_executable"] = resolved_path
    report["resolved_blender_source"] = resolved_source
    if resolved_path:
        report["message"] += f" INFO: Blender executable resolved via {resolved_source}: {resolved_path}"
    return report


def _extract_blender_python_runtime_error(stdout_text: str, stderr_text: str) -> str:
    combined = "\n".join(part.strip() for part in (stderr_text or "", stdout_text or "") if part and part.strip())
    markers = (
        "Traceback (most recent call last):",
        "Error: Python:",
        "Python: Traceback",
    )
    if not any(marker in combined for marker in markers):
        return ""
    return compact_text(combined, 1200)


def _run_blender_validation_subprocess(
    *,
    script_path: str,
    blender_executable: str,
    blend_file: str | None,
    route_decision: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    blend_path = Path(blend_file) if blend_file else None
    if blend_path and route_decision == "modify_existing" and blend_path.exists():
        with tempfile.TemporaryDirectory(prefix="langgraph_blender_validation_") as temp_dir:
            temp_blend_path = Path(temp_dir) / blend_path.name
            shutil.copy2(blend_path, temp_blend_path)
            result = subprocess.run(
                [
                    blender_executable,
                    str(temp_blend_path),
                    "--background",
                    "--python",
                    script_path,
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        mode = "temp_blend_copy"
    else:
        command = [blender_executable]
        if blend_path and blend_path.exists():
            command.append(str(blend_path))
            mode = "blend_file"
        else:
            command.append("--factory-startup")
            mode = "factory_startup_missing_blend" if blend_path and route_decision == "modify_existing" else "factory_startup"
        command.extend(["--background", "--python", script_path])
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )

    runtime_error = _extract_blender_python_runtime_error(result.stdout, result.stderr)
    stdout_preview = compact_text((result.stdout or "").strip(), 600)
    stderr_preview = compact_text((runtime_error or result.stderr or "").strip(), 1600)
    if result.returncode != 0:
        return {
            "status": "failed",
            "stage": "blender_runtime",
            "mode": mode,
            "message": f"FAIL: Blender runtime validation failed with exit code {result.returncode}.",
            "stdout_preview": stdout_preview,
            "stderr_preview": stderr_preview,
            "runtime_error_excerpt": compact_text(runtime_error, 1600) if runtime_error else "",
        }
    if runtime_error:
        return {
            "status": "failed",
            "stage": "blender_runtime",
            "mode": mode,
            "message": f"FAIL: Blender runtime validation detected a Python traceback in {mode} mode.",
            "stdout_preview": stdout_preview,
            "stderr_preview": stderr_preview,
            "runtime_error_excerpt": compact_text(runtime_error, 1600),
        }
    return {
        "status": "passed",
        "stage": "blender_runtime",
        "mode": mode,
        "message": f"PASS: Blender runtime validation succeeded in {mode} mode.",
        "stdout_preview": stdout_preview,
        "stderr_preview": stderr_preview,
    }

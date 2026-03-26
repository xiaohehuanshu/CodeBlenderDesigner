from __future__ import annotations

import json
import mimetypes
import os
import re
from base64 import b64encode
from datetime import datetime
from pathlib import Path
from typing import Any


TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def ensure_path_list(path_like: str | Path | list[str] | list[Path] | None) -> list[Path]:
    if path_like is None:
        return []
    if isinstance(path_like, (str, Path)):
        return [Path(path_like)]
    return [Path(item) for item in path_like]


def ensure_directory(path_like: str | Path) -> Path:
    path = Path(path_like)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_env_file(path_like: str | Path = ".env") -> None:
    path = Path(path_like)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_text_file(path_like: str | Path) -> str:
    path = Path(path_like)
    for encoding in TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def load_json_file(path_like: str | Path, default: Any | None = None) -> Any:
    path = Path(path_like)
    if not path.exists():
        return {} if default is None else default
    return json.loads(read_text_file(path))


def write_json_file(path_like: str | Path, payload: Any) -> Path:
    path = Path(path_like)
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def safe_json_loads(text: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    default = default or {}
    content = text.strip()
    if not content:
        return default

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.S)
    if fence_match:
        content = fence_match.group(1)

    if "{" in content and "}" in content:
        start = content.find("{")
        end = content.rfind("}") + 1
        content = content[start:end]

    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return default
    return default


def compact_text(text: str | None, max_chars: int = 4000) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    suffix = "...(truncated)"
    if max_chars <= len(suffix):
        return text[:max_chars]
    return f"{text[: max_chars - len(suffix)]}{suffix}"


def text_stats(text: str | None) -> dict[str, int]:
    normalized = text or ""
    if not isinstance(normalized, str):
        normalized = str(normalized)
    return {
        "chars": len(normalized),
        "bytes": len(normalized.encode("utf-8")),
        "lines": 0 if not normalized else normalized.count("\n") + 1,
    }


def clean_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_+-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def list_image_files(path_like: str | Path | list[str] | list[Path] | None, limit: int = 8) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for path in ensure_path_list(path_like):
        if not path.exists():
            continue
        candidates: list[Path] = []
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            candidates = [path]
        elif path.is_dir():
            candidates = [item for item in sorted(path.iterdir()) if item.suffix.lower() in IMAGE_SUFFIXES]
        for item in candidates:
            resolved = item.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(item)
            if len(files) >= limit:
                return files
    return files


def file_to_data_url(path_like: str | Path) -> str:
    path = Path(path_like)
    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"
    data = b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{data}"


def load_markdown_bundle(
    path_like: str | Path | list[str] | list[Path] | None,
    max_chars: int = 24000,
) -> tuple[str, list[str]]:
    files: list[Path] = []
    seen: set[Path] = set()
    for path in ensure_path_list(path_like):
        if not path.exists():
            continue
        candidates: list[Path]
        if path.is_file() and path.suffix.lower() == ".md":
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(path.rglob("*.md"))
        else:
            candidates = []
        for item in candidates:
            resolved = item.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(item)

    if not files:
        return "", []

    chunks: list[str] = []
    used_files: list[str] = []
    current_len = 0
    for file_path in files:
        content = read_text_file(file_path)
        header = f"\n# File: {file_path.name}\n"
        chunk = header + content.strip() + "\n"
        if current_len + len(chunk) > max_chars:
            remaining = max_chars - current_len
            if remaining > 0:
                chunks.append(chunk[:remaining])
                used_files.append(str(file_path))
            break
        chunks.append(chunk)
        used_files.append(str(file_path))
        current_len += len(chunk)

    return "\n".join(chunks).strip(), used_files


def merge_node_result(state_results: dict[str, Any] | None, node_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(state_results or {})
    merged[node_name] = payload
    return merged


def summarize_geometry_context(geometry_context: dict[str, Any]) -> str:
    if not geometry_context:
        return "未获得几何约束。"

    selected_faces = geometry_context.get("selected_face_regions", [])
    selected_objects = geometry_context.get("selected_object_regions", [])
    environment_objects = geometry_context.get("environment_objects", [])
    lines: list[str] = []

    if selected_faces:
        lines.append(f"设计范围包含 {len(selected_faces)} 个选中面区域。")
        for item in selected_faces[:2]:
            lines.append(
                "对象 {name}：{count} 个面，总面积 {area:.3f}，重心 {centroid}，平均法向 {normal}。".format(
                    name=item.get("object_name", "Unknown"),
                    count=item.get("face_count", 0),
                    area=float(item.get("total_area", 0.0)),
                    centroid=item.get("centroid", []),
                    normal=item.get("average_normal", []),
                )
            )
    elif selected_objects:
        lines.append(f"未检测到选中面，退化为 {len(selected_objects)} 个选中对象区域。")
        for item in selected_objects[:2]:
            lines.append(
                "对象 {name}：包围盒 {bbox_min} -> {bbox_max}，重心 {centroid}。".format(
                    name=item.get("object_name", "Unknown"),
                    bbox_min=item.get("bbox_min", []),
                    bbox_max=item.get("bbox_max", []),
                    centroid=item.get("centroid", []),
                )
            )
    else:
        lines.append("当前场景中没有检测到有效的选中设计区域。")

    if environment_objects:
        lines.append(f"环境中共识别到 {len(environment_objects)} 个未选中对象，以下为最近的若干对象：")
        for item in sorted(environment_objects, key=lambda x: x.get("distance_to_design_region", 1e9))[:3]:
            lines.append(
                "环境对象 {name}：距离设计区域中心约 {distance:.3f}。".format(
                    name=item.get("object_name", "Unknown"),
                    distance=float(item.get("distance_to_design_region", 0.0)),
                )
            )

    notes = geometry_context.get("notes", [])
    if notes:
        lines.append("附加说明：" + "；".join(str(item) for item in notes[:3]))

    return compact_text("\n".join(lines), 600)

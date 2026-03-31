from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .cli import run_single_turn
from .config import AgentSettings, RunRequest
from .graph import build_design_agent_graph
from .utils import compact_text, load_env_file, load_json_file


ArtifactKind = Literal["glb", "script", "trace"]


class GenerateApiRequest(RunRequest):
    export_stl: bool | None = None


class GenerateApiResponse(BaseModel):
    session_id: str
    thread_id: str
    route_decision: str | None = None
    should_end: bool = False
    generated_script_path: str | None = None
    glb_path: str | None = None
    execution_log: list[str] = []
    errors: list[str] = []
    trace_path: str | None = None
    consolidated_prompt: str | None = None
    refined_design_brief: str | None = None
    design_brief_base_values: dict[str, Any] | None = None
    runtime_validation_status: str | None = None
    runtime_validation_mode: str | None = None


class HealthResponse(BaseModel):
    status: str
    openai_configured: bool
    qwen_configured: bool
    blender_configured: bool


class SessionEventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
        async with self._lock:
            self._queues.setdefault(session_id, set()).add(queue)
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            subscribers = self._queues.get(session_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._queues.pop(session_id, None)

    async def publish(self, session_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._queues.get(session_id, set()))
        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    continue


@dataclass
class SessionArtifacts:
    session_id: str
    output_dir: Path
    generated_script_path: str | None = None
    glb_path: str | None = None
    trace_path: str | None = None


class ApiRuntime:
    def __init__(self) -> None:
        load_env_file(Path(__file__).resolve().parents[2] / ".env")
        self.settings = AgentSettings()
        self.graph = build_design_agent_graph(self.settings)
        self.events = SessionEventBroker()
        self.generation_lock = asyncio.Lock()
        self.sessions: dict[str, SessionArtifacts] = {}

    @staticmethod
    def normalize_identifier(value: str | None, *, fallback_prefix: str) -> str:
        raw = (value or "").strip()
        if not raw:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{fallback_prefix}_{stamp}"
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
        return normalized or f"{fallback_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def default_output_dir(self) -> Path:
        return Path(self.settings.default_output_dir).resolve()

    def build_request(self, payload: GenerateApiRequest) -> RunRequest:
        request_data = payload.model_dump(mode="json", exclude_none=True)
        session_id = self.normalize_identifier(request_data.get("session_id"), fallback_prefix="session")
        thread_id = self.normalize_identifier(request_data.get("thread_id"), fallback_prefix=session_id)
        request_data["session_id"] = session_id
        request_data["thread_id"] = thread_id
        request_data["user_input"] = str(request_data.get("user_input") or "").strip()
        return RunRequest.model_validate(request_data)

    def infer_turn_index(self, request: RunRequest) -> int:
        output_dir = Path(request.output_dir or self.settings.default_output_dir)
        memory_path = output_dir / "memory" / f"{request.session_id}.json"
        memory_payload = load_json_file(memory_path, default={})
        conversation_history = memory_payload.get("conversation_history") or []
        user_turns = sum(1 for item in conversation_history if (item.get("role") or "") == "user")
        return max(1, user_turns + 1)

    def remember_result(self, request: RunRequest, result: dict[str, Any]) -> None:
        output_dir = Path(request.output_dir or self.settings.default_output_dir).resolve()
        self.sessions[request.session_id] = SessionArtifacts(
            session_id=request.session_id,
            output_dir=output_dir,
            generated_script_path=str(result.get("generated_script_path") or "") or None,
            glb_path=str(result.get("glb_path") or "") or None,
            trace_path=str(result.get("trace_path") or "") or None,
        )

    def _memory_artifact_paths(self, output_dir: Path, session_id: str) -> dict[ArtifactKind, str | None]:
        memory_path = output_dir / "memory" / f"{session_id}.json"
        memory_payload = load_json_file(memory_path, default={})
        node8_result = ((memory_payload.get("node_results") or {}).get("node8_runtime_debug") or {})
        return {
            "glb": str(node8_result.get("glb_path") or "") or None,
            "script": str(memory_payload.get("last_generated_script_path") or "") or None,
            "trace": str(memory_payload.get("last_trace_path") or "") or None,
        }

    @staticmethod
    def _latest_matching_file(directory: Path, pattern: str) -> Path | None:
        if not directory.exists():
            return None
        matches = sorted(directory.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
        return matches[0] if matches else None

    def _artifact_candidates(self, output_dir: Path, session_id: str, kind: ArtifactKind) -> list[Path]:
        memory_paths = self._memory_artifact_paths(output_dir, session_id)
        candidates: list[Path] = []

        memory_path = memory_paths.get(kind)
        if memory_path:
            candidates.append(Path(memory_path))

        if kind == "glb":
            candidates.append(output_dir / "generated_glb" / f"{session_id}.glb")
        elif kind == "script":
            latest_script = self._latest_matching_file(output_dir / "generated_scripts", f"{session_id}_*.py")
            if latest_script:
                candidates.append(latest_script)
        elif kind == "trace":
            latest_trace = self._latest_matching_file(output_dir / "traces" / session_id, "*.jsonl")
            if latest_trace:
                candidates.append(latest_trace)

        return candidates

    def resolve_artifact(self, session_id: str, kind: ArtifactKind) -> Path | None:
        normalized_session = self.normalize_identifier(session_id, fallback_prefix="session")
        records: list[Path] = []
        session_record = self.sessions.get(normalized_session)
        if session_record:
            direct_value = {
                "glb": session_record.glb_path,
                "script": session_record.generated_script_path,
                "trace": session_record.trace_path,
            }.get(kind)
            if direct_value:
                records.append(Path(direct_value))
            records.extend(self._artifact_candidates(session_record.output_dir, normalized_session, kind))

        records.extend(self._artifact_candidates(self.default_output_dir(), normalized_session, kind))

        seen: set[Path] = set()
        for candidate in records:
            resolved = candidate.expanduser().resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists() and resolved.is_file():
                return resolved
        return None


runtime = ApiRuntime()


def build_generate_response(request: RunRequest, result: dict[str, Any]) -> GenerateApiResponse:
    return GenerateApiResponse(
        session_id=request.session_id,
        thread_id=request.thread_id,
        route_decision=result.get("route_decision"),
        should_end=bool(result.get("should_end")),
        generated_script_path=str(result.get("generated_script_path") or "") or None,
        glb_path=str(result.get("glb_path") or "") or None,
        execution_log=[str(item) for item in (result.get("execution_log") or []) if str(item).strip()],
        errors=[str(item) for item in (result.get("errors") or []) if str(item).strip()],
        trace_path=str(result.get("trace_path") or "") or None,
        consolidated_prompt=str(result.get("consolidated_prompt") or "") or None,
        refined_design_brief=str(result.get("refined_design_brief") or "") or None,
        design_brief_base_values=result.get("design_brief_base_values") or None,
        runtime_validation_status=str(result.get("runtime_validation_status") or "") or None,
        runtime_validation_mode=str(result.get("runtime_validation_mode") or "") or None,
    )


def create_app(api_runtime: ApiRuntime) -> FastAPI:
    app = FastAPI(title="PalX Blender API", version="0.1.0")

    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "PALX_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            openai_configured=bool(api_runtime.settings.openai_api_key),
            qwen_configured=bool(api_runtime.settings.dashscope_api_key),
            blender_configured=bool(api_runtime.settings.blender_executable),
        )

    @app.post("/generate", response_model=GenerateApiResponse)
    async def generate(payload: GenerateApiRequest) -> GenerateApiResponse:
        request = api_runtime.build_request(payload)
        if not request.user_input.strip():
            raise HTTPException(status_code=400, detail="user_input 不能为空。")

        await api_runtime.events.publish(
            request.session_id,
            {"event": "generation.start", "session_id": request.session_id},
        )

        try:
            async with api_runtime.generation_lock:
                turn_index = api_runtime.infer_turn_index(request)
                result = await asyncio.to_thread(
                    run_single_turn,
                    graph=api_runtime.graph,
                    request=request,
                    settings=api_runtime.settings,
                    turn_index_in_run=turn_index,
                )
        except Exception as exc:
            message = compact_text(str(exc), 800)
            await api_runtime.events.publish(
                request.session_id,
                {"event": "generation.error", "session_id": request.session_id, "error": message},
            )
            raise HTTPException(status_code=500, detail=message) from exc

        api_runtime.remember_result(request, result)
        response = build_generate_response(request, result)
        await api_runtime.events.publish(
            request.session_id,
            {
                "event": "generation.complete",
                "session_id": request.session_id,
                "route_decision": response.route_decision,
                "glb_path": response.glb_path,
            },
        )
        return response

    @app.websocket("/ws/{session_id}")
    async def session_socket(websocket: WebSocket, session_id: str) -> None:
        normalized_session = api_runtime.normalize_identifier(session_id, fallback_prefix="session")
        await websocket.accept()
        queue = await api_runtime.events.subscribe(normalized_session)
        await websocket.send_json({"event": "connected", "session_id": normalized_session})
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
        except Exception:
            return
        finally:
            await api_runtime.events.unsubscribe(normalized_session, queue)

    def serve_artifact(session_id: str, kind: ArtifactKind) -> FileResponse:
        path = api_runtime.resolve_artifact(session_id, kind)
        if path is None:
            raise HTTPException(status_code=404, detail=f"{kind} artifact not found for session {session_id}.")

        media_type = {
            "glb": "model/gltf-binary",
            "script": "text/x-python",
            "trace": "application/x-ndjson",
        }[kind]
        return FileResponse(path=path, media_type=media_type, filename=path.name)

    @app.get("/glb/{session_id}")
    async def get_glb(session_id: str) -> FileResponse:
        return serve_artifact(session_id, "glb")

    @app.get("/script/{session_id}")
    async def get_script(session_id: str) -> FileResponse:
        return serve_artifact(session_id, "script")

    @app.get("/trace/{session_id}")
    async def get_trace(session_id: str) -> FileResponse:
        return serve_artifact(session_id, "trace")

    return app


app = create_app(runtime)


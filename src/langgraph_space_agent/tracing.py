from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

from .utils import compact_text, ensure_directory, text_stats


_TRACE_PATH: Path | None = None
_TRACE_CONTEXT: dict[str, Any] = {}
_TRACE_SEQUENCE = 0
_TRACE_STARTED_AT: float | None = None
_TRACE_PHASE_STACK: list[str] = []


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "default"


def _trace_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def start_trace(
    *,
    output_dir: str | Path,
    session_id: str,
    thread_id: str,
    user_input: str,
) -> str:
    global _TRACE_CONTEXT
    global _TRACE_PATH
    global _TRACE_SEQUENCE
    global _TRACE_STARTED_AT
    global _TRACE_PHASE_STACK

    trace_dir = ensure_directory(Path(output_dir) / "traces" / _safe_name(session_id))
    trace_path = trace_dir / f"{_trace_stamp()}_{_safe_name(thread_id)}.jsonl"
    _TRACE_PATH = trace_path
    _TRACE_CONTEXT = {
        "session_id": session_id,
        "thread_id": thread_id,
        "trace_path": str(trace_path),
    }
    _TRACE_SEQUENCE = 0
    _TRACE_STARTED_AT = perf_counter()
    _TRACE_PHASE_STACK = []
    trace_event(
        "run.start",
        user_input_preview=compact_text(user_input, 240),
        user_input_stats=text_stats(user_input),
    )
    return str(trace_path)


def finish_trace(status: str, **payload: Any) -> None:
    global _TRACE_CONTEXT
    global _TRACE_PATH
    global _TRACE_SEQUENCE
    global _TRACE_STARTED_AT
    global _TRACE_PHASE_STACK

    trace_event("run.finish", status=status, **payload)
    _TRACE_PHASE_STACK = []
    _TRACE_STARTED_AT = None
    _TRACE_SEQUENCE = 0
    _TRACE_CONTEXT = {}
    _TRACE_PATH = None


def trace_event(event: str, **payload: Any) -> None:
    global _TRACE_SEQUENCE

    if _TRACE_PATH is None:
        return

    _TRACE_SEQUENCE += 1
    elapsed_ms = None if _TRACE_STARTED_AT is None else round((perf_counter() - _TRACE_STARTED_AT) * 1000, 3)
    record = {
        "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "seq": _TRACE_SEQUENCE,
        "elapsed_ms": elapsed_ms,
        **_TRACE_CONTEXT,
        "phase": _TRACE_PHASE_STACK[-1] if _TRACE_PHASE_STACK else None,
        "event": event,
        **payload,
    }

    try:
        ensure_directory(_TRACE_PATH.parent)
        with _TRACE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        return


@contextmanager
def trace_phase(phase_name: str, **payload: Any) -> Iterator[None]:
    _TRACE_PHASE_STACK.append(phase_name)
    trace_event("phase.start", phase_name=phase_name, **payload)
    try:
        yield
    except Exception as exc:
        trace_event("phase.end", phase_name=phase_name, status="error", error=str(exc))
        raise
    else:
        trace_event("phase.end", phase_name=phase_name, status="completed")
    finally:
        if _TRACE_PHASE_STACK:
            _TRACE_PHASE_STACK.pop()

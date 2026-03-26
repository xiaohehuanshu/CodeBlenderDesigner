from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_utf8_console() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCP(65001)
            kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass


def main() -> None:
    _configure_utf8_console()
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    argv = sys.argv[1:]
    has_input_args = any(
        arg == "--request-file"
        or arg.startswith("--request-file=")
        or arg == "--prompt"
        or arg.startswith("--prompt=")
        or arg == "--prompt-file"
        or arg.startswith("--prompt-file=")
        for arg in argv
    )
    if not has_input_args:
        default_request_file = project_root / "request_case_001.json"
        if default_request_file.exists():
            sys.argv.extend(["--request-file", str(default_request_file)])
        else:
            print(
                "No input arguments were provided, and the default request file was not found:\n"
                f"  {default_request_file}\n\n"
                "Please pass one of:\n"
                "  --request-file <path>\n"
                "  --prompt <text>\n"
                "  --prompt-file <path>\n",
                file=sys.stderr,
            )
            raise SystemExit(1)

    try:
        from langgraph_space_agent.cli import main as agent_main
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "unknown"
        expected_missing = {"pydantic", "langgraph", "langchain_core"}
        if missing_module in expected_missing:
            python_exe = sys.executable
            print(
                "Missing dependency detected while starting langgraph_agent.\n"
                f"Missing module: {missing_module}\n\n"
                "Please install the project dependencies into the current virtual environment:\n"
                f'  "{python_exe}" -m pip install -e "{project_root}"\n',
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise

    agent_main()


if __name__ == "__main__":
    main()

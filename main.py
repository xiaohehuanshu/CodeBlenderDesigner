from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    agent_root = project_root / "langgraph_agent"
    src_path = project_root / "langgraph_agent" / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        if exc.name == "uvicorn":
            python_exe = sys.executable
            print(
                "Missing dependency detected while starting the PalX web API.\n"
                "Please install the langgraph_agent dependencies into the current virtual environment:\n"
                f'  "{python_exe}" -m pip install -e "{agent_root}"\n',
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise

    try:
        import langgraph_space_agent.web_api  # noqa: F401
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "unknown"
        expected_missing = {
            "fastapi",
            "langgraph",
            "langchain_core",
            "pydantic",
        }
        if missing_module in expected_missing:
            python_exe = sys.executable
            print(
                "Missing dependency detected while loading the PalX web API.\n"
                f"Missing module: {missing_module}\n\n"
                "Please install the langgraph_agent dependencies into the current virtual environment:\n"
                f'  "{python_exe}" -m pip install -e "{agent_root}"\n',
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise

    uvicorn.run(
        "langgraph_space_agent.web_api:app",
        host=os.getenv("PALX_API_HOST", "0.0.0.0"),
        port=int(os.getenv("PALX_API_PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()

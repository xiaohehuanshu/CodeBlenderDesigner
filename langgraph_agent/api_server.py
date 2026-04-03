"""
FastAPI server for Pal 3D Agent
Provides HTTP API for the langgraph agent
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from langgraph_space_agent.cli import (
    build_initial_state,
    build_memory_payload,
    load_request_from_args as build_request,
)
from langgraph_space_agent.config import AgentSettings, RunRequest
from langgraph_space_agent.graph import build_design_agent_graph
from langgraph_space_agent.utils import ensure_directory, load_json_file, write_json_file

# Initialize FastAPI
app = FastAPI(title="Pal 3D Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
settings = AgentSettings()
graph = None


def get_graph():
    """Lazy load the graph"""
    global graph
    if graph is None:
        graph = build_design_agent_graph(settings)
    return graph


# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str | None = None
    thread_id: str | None = None


@app.on_event("startup")
async def startup_event():
    """Initialize graph on startup"""
    get_graph()
    print("Pal 3D Agent API started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def format_agent_response(result: dict[str, Any]) -> str:
    """Format agent result into readable response"""
    parts = []

    # Get node results
    node_results = result.get("node_results", {})

    # 1. Requirement collection
    if "node1_collect_requirements" in node_results:
        node1 = node_results["node1_collect_requirements"]
        if "prompt_collection" in node1:
            parts.append("## 📋 需求解析\n" + node1["prompt_collection"])

    # 2. Research summary
    if "node2_internet_research" in node_results:
        node2 = node_results["node2_internet_research"]
        if "research_summary" in node2:
            parts.append("## 🔍 互联网调研\n" + node2["research_summary"])

    # 3. Image analysis
    if "node3_image_analysis" in node_results:
        node3 = node_results["node3_image_analysis"]
        if "image_analysis_summary" in node3:
            parts.append("## 🖼️ 图像分析\n" + node3["image_analysis_summary"])

    # 4. Markdown analysis
    if "node4_markdown_analysis" in node_results:
        node4 = node_results["node4_markdown_analysis"]
        if "markdown_summary" in node4:
            parts.append("## 📄 规则文档分析\n" + node4["markdown_summary"])

    # 5. Geometry context
    if "node5_geometry_constraints" in node_results:
        node5 = node_results["node5_geometry_constraints"]
        if "geometry_summary" in node5:
            parts.append("## 🏗️ 几何约束\n" + node5["geometry_summary"])

    # 6. Consolidated prompt
    if "node6_prompt_synthesis" in node_results:
        node6 = node_results["node6_prompt_synthesis"]
        if "consolidated_prompt" in node6:
            parts.append("## 📝 综合设计简报\n" + node6["consolidated_prompt"])
        elif "refined_design_brief" in node6:
            parts.append("## 📝 设计简报\n" + node6["refined_design_brief"])

    # 7. Script generation
    if "node7_script_generation" in node_results:
        node7 = node_results["node7_script_generation"]
        if "generation_scope" in node7:
            parts.append("## 🔧 生成范围\n" + node7["generation_scope"])

    # Route decision and script path
    route_decision = result.get("route_decision", "unknown")
    generated_script_path = result.get("generated_script_path", "")

    if route_decision == "to_validation_end":
        parts.append(f"\n## ✅ 处理完成\n\n脚本已生成: `{generated_script_path}`")
    elif route_decision == "to_refinement":
        parts.append(f"\n## ⚠️ 需要修正\n\n{result.get('error_message', '未知错误')}")

    return "\n\n---\n\n".join(parts) if parts else "处理完成，但没有返回详细内容。"


async def stream_agent_process(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Stream agent processing steps with real output
    """
    try:
        # Get user input
        user_message = request.messages[-1]
        user_input = user_message.content

        # Send initial acknowledgment
        yield f"data: {json.dumps({'type': 'start', 'content': '开始处理...'}, ensure_ascii=False)}\n\n"

        # Build request
        request_data = {
            "user_input": user_input,
            "session_id": request.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "thread_id": request.thread_id or f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "interactive": False,
            "single_turn": True,
        }

        run_request = RunRequest.model_validate(request_data)

        # Send node progress updates
        yield f"data: {json.dumps({'type': 'progress', 'node': 'node1', 'content': '🔍 正在解析需求...'}, ensure_ascii=False)}\n\n"

        # Load session memory
        output_dir = ensure_directory(run_request.output_dir or settings.default_output_dir)
        memory_dir = ensure_directory(output_dir / "memory")
        memory_path = memory_dir / f"{run_request.session_id}.json"
        session_memory = load_json_file(memory_path, default={})

        # Build initial state and run
        initial_state = build_initial_state(run_request, session_memory)
        graph_instance = get_graph()
        graph_thread_id = f"{run_request.thread_id}__turn_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Run the graph
        result = graph_instance.invoke(
            initial_state,
            config={"configurable": {"thread_id": graph_thread_id}},
        )

        # Save memory
        write_json_file(
            memory_path,
            build_memory_payload(result, previous_memory=session_memory, user_input=user_input),
        )

        # Stream node results
        node_results = result.get("node_results", {})

        for node_name, node_id in [
            ("node1_collect_requirements", "node1"),
            ("node2_internet_research", "node2"),
            ("node3_image_analysis", "node3"),
            ("node4_markdown_analysis", "node4"),
            ("node5_geometry_constraints", "node5"),
            ("node6_prompt_synthesis", "node6"),
            ("node7_script_generation", "node7"),
            ("node8_runtime_debug", "node8"),
        ]:
            if node_name in node_results:
                titles = {
                    "node1": "📋 需求解析完成",
                    "node2": "🔍 互联网调研完成",
                    "node3": "🖼️ 图像分析完成",
                    "node4": "📄 规则文档分析完成",
                    "node5": "🏗️ 几何约束提取完成",
                    "node6": "📝 提示词综合完成",
                    "node7": "🔧 脚本生成完成",
                    "node8": "✅ 运行调试完成",
                }
                yield f"data: {json.dumps({'type': 'progress', 'node': node_id, 'content': titles[node_id]}, ensure_ascii=False)}\n\n"

        # Format and send final response
        content = format_agent_response(result)
        yield f"data: {json.dumps({'type': 'complete', 'content': content}, ensure_ascii=False)}\n\n"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        yield f"data: {json.dumps({'type': 'error', 'content': f'处理出错: {str(e)}'}, ensure_ascii=False)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events
    """
    return StreamingResponse(
        stream_agent_process(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session memory"""
    try:
        output_dir = settings.default_output_dir
        memory_path = output_dir / "memory" / f"{session_id}.json"

        if not memory_path.exists():
            raise HTTPException(status_code=404, detail="Session not found")

        session_data = load_json_file(memory_path)
        return session_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete session memory"""
    try:
        output_dir = settings.default_output_dir
        memory_path = output_dir / "memory" / f"{session_id}.json"

        if memory_path.exists():
            memory_path.unlink()
            return {"message": "Session deleted"}

        raise HTTPException(status_code=404, detail="Session not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=args.port)

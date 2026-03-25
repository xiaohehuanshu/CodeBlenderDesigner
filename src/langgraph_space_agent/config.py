from __future__ import annotations

import os
from pydantic import BaseModel, Field, model_validator


class NodeSwitches(BaseModel):
    global_enabled: bool = True
    node1_collect_requirements: bool = True
    node2_internet_research: bool = False
    node3_image_analysis: bool = True
    node4_markdown_analysis: bool = True
    node5_geometry_constraints: bool = True
    node6_prompt_synthesis: bool = True
    node7_script_generation: bool = True
    node8_runtime_debug: bool = True

    @model_validator(mode="before")
    @classmethod
    def _map_legacy_node_switch_keys(cls, data):
        if not isinstance(data, dict):
            return data

        mapped = dict(data)
        if "node5_geometry_constraints" not in mapped and "node6_geometry_constraints" in mapped:
            mapped["node5_geometry_constraints"] = mapped["node6_geometry_constraints"]
        if "node6_prompt_synthesis" not in mapped and "node5_prompt_synthesis" in mapped:
            mapped["node6_prompt_synthesis"] = mapped["node5_prompt_synthesis"]
        return mapped

    def enabled(self, key: str) -> bool:
        return self.global_enabled and bool(getattr(self, key, False))


class RunRequest(BaseModel):
    user_input: str = ""
    session_id: str = "default"
    thread_id: str = "default"
    interactive: bool = False
    prompt_file: str | None = None
    use_prompt_file_for_first_turn: bool = False
    image_dir: str | list[str] | None = None
    markdown_path: str | list[str] | None = None
    geometry_context_path: str | None = None
    blender_executable: str | None = None
    blend_file: str | None = None
    output_dir: str | None = None
    output_script_path: str | None = None
    validate_generated_script: bool = True
    script_validation_timeout_seconds: int | None = None
    auto_execute_generated_script: bool = False
    enable_new_generation_full_script_quick_path: bool | None = None
    node_switches: NodeSwitches = Field(default_factory=NodeSwitches)


class AgentSettings(BaseModel):
    dashscope_api_key: str | None = Field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY"))
    qwen_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    )
    qwen_text_model: str = Field(default_factory=lambda: os.getenv("QWEN_TEXT_MODEL", "qwen-plus"))
    qwen_vision_model: str = Field(default_factory=lambda: os.getenv("QWEN_VISION_MODEL", "qwen-vl-plus"))
    enable_qwen_web_search: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_QWEN_WEB_SEARCH", "true").strip().lower() == "true"
    )
    openai_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_base_url: str = Field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://haoshunxin.cloud/v1"))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5.4"))
    blender_executable: str | None = Field(default_factory=lambda: os.getenv("BLENDER_EXECUTABLE"))
    default_output_dir: str = Field(default_factory=lambda: os.getenv("DEFAULT_OUTPUT_DIR", "outputs"))
    validate_generated_script: bool = Field(
        default_factory=lambda: os.getenv("VALIDATE_GENERATED_SCRIPT", "true").strip().lower() == "true"
    )
    script_validation_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("SCRIPT_VALIDATION_TIMEOUT_SECONDS", "120"))
    )
    auto_execute_generated_script: bool = Field(
        default_factory=lambda: os.getenv("AUTO_EXECUTE_GENERATED_SCRIPT", "false").strip().lower() == "true"
    )
    enable_new_generation_full_script_quick_path: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_NEW_GENERATION_FULL_SCRIPT_QUICK_PATH", "false").strip().lower()
        == "true"
    )

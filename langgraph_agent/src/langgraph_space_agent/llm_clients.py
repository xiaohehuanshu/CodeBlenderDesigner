from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Callable
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

from .tracing import trace_event
from .utils import clean_code_fence, compact_text, file_to_data_url, safe_json_loads, text_stats


class ChatClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        default_model: str,
        *,
        max_retries: int = 2,
        retry_backoff_seconds: float = 3.0,
        request_timeout_seconds: float = 180.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.request_timeout_seconds = max(1.0, request_timeout_seconds)

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _payload_content_stats(content: Any) -> dict[str, int]:
        if isinstance(content, str):
            return {
                **text_stats(content),
                "parts": 1 if content else 0,
                "non_text_parts": 0,
            }
        if isinstance(content, list):
            text_fragments: list[str] = []
            non_text_parts = 0
            for item in content:
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        text_fragments.append(str(text))
                else:
                    non_text_parts += 1
            return {
                **text_stats("\n".join(text_fragments)),
                "parts": len(content),
                "non_text_parts": non_text_parts,
            }
        if content is None:
            return {"chars": 0, "bytes": 0, "lines": 0, "parts": 0, "non_text_parts": 0}
        return {
            **text_stats(str(content)),
            "parts": 1,
            "non_text_parts": 0,
        }

    @staticmethod
    def _debug_format_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            blocks: list[str] = []
            for index, item in enumerate(content, start=1):
                if not isinstance(item, dict):
                    blocks.append(f"[part {index}] {item}")
                    continue
                item_type = item.get("type") or "unknown"
                if item_type in {"text", "output_text"}:
                    text = item.get("text") or item.get("content") or ""
                    blocks.append(f"[part {index} text]\n{text}")
                    continue
                if item_type == "image_url":
                    image_url = ((item.get("image_url") or {}).get("url")) if isinstance(item.get("image_url"), dict) else item.get("image_url")
                    image_url_text = str(image_url or "")
                    blocks.append(
                        f"[part {index} image_url omitted length={len(image_url_text)}]"
                    )
                    continue
                blocks.append(f"[part {index} {item_type}] {json.dumps(item, ensure_ascii=False, default=str)}")
            return "\n".join(blocks)
        if content is None:
            return ""
        return str(content)

    @classmethod
    def _debug_format_tool_calls(cls, tool_calls: Any) -> str:
        if not isinstance(tool_calls, list) or not tool_calls:
            return ""
        blocks: list[str] = []
        for index, tool_call in enumerate(tool_calls, start=1):
            if not isinstance(tool_call, dict):
                blocks.append(f"[tool_call {index}] {tool_call}")
                continue
            function_payload = tool_call.get("function") or {}
            arguments = function_payload.get("arguments") or ""
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=False, default=str)
            blocks.append(
                "\n".join(
                    [
                        f"[tool_call {index}] id={tool_call.get('id')} name={function_payload.get('name')}",
                        "[arguments]",
                        arguments,
                    ]
                )
            )
        return "\n\n".join(blocks)

    @classmethod
    def _debug_collect_message_payloads(cls, payload: dict[str, Any]) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        for index, message in enumerate(payload.get("messages") or []):
            if not isinstance(message, dict):
                collected.append(
                    {
                        "index": index,
                        "role": "unknown",
                        "content": str(message),
                        "tool_calls": "",
                    }
                )
                continue
            collected.append(
                {
                    "index": index,
                    "role": message.get("role", "unknown"),
                    "name": message.get("name"),
                    "tool_call_id": message.get("tool_call_id"),
                    "content": cls._debug_format_content(message.get("content")),
                    "tool_calls": cls._debug_format_tool_calls(message.get("tool_calls")),
                }
            )
        return collected

    @classmethod
    def _collect_compact_message_previews(cls, payload: dict[str, Any]) -> list[dict[str, Any]]:
        previews: list[dict[str, Any]] = []
        for item in cls._debug_collect_message_payloads(payload):
            previews.append(
                {
                    "index": item.get("index"),
                    "role": item.get("role"),
                    "name": item.get("name"),
                    "tool_call_id": item.get("tool_call_id"),
                    "content_preview": compact_text(str(item.get("content") or ""), 240),
                    "tool_calls_preview": compact_text(str(item.get("tool_calls") or ""), 240),
                }
            )
        return previews

    @classmethod
    def _print_payload_messages(cls, *, model_name: str, request_id: str, payload: dict[str, Any]) -> None:
        print(f"[GPT-5.4 PROMPT] begin request_id={request_id}", flush=True)
        for item in cls._debug_collect_message_payloads(payload):
            header = f"[LLM] message[{item['index']}] role={item['role']}"
            if item.get("name"):
                header += f" name={item['name']}"
            if item.get("tool_call_id"):
                header += f" tool_call_id={item['tool_call_id']}"
            print(header, flush=True)
            content = str(item.get("content") or "").strip()
            if content:
                print(content, flush=True)
            tool_calls = str(item.get("tool_calls") or "").strip()
            if tool_calls:
                print(tool_calls, flush=True)
        print(f"[GPT-5.4 PROMPT] end request_id={request_id}", flush=True)

    @staticmethod
    def _should_print_payload_messages(model_name: str) -> bool:
        if not model_name.strip().lower().startswith("gpt-5.4"):
            return False
        # Real-user mode keeps full prompt dumping off unless explicitly enabled for debugging.
        return os.getenv("PRINT_LLM_PROMPTS", "false").strip().lower() == "true"

    @classmethod
    def _collect_payload_message_metrics(cls, payload: dict[str, Any]) -> list[dict[str, Any]]:
        metrics: list[dict[str, Any]] = []
        for index, message in enumerate(payload.get("messages") or []):
            if not isinstance(message, dict):
                metrics.append({"index": index, "role": "unknown"})
                continue
            content_metrics = cls._payload_content_stats(message.get("content"))
            tool_calls = message.get("tool_calls") or []
            tool_call_bytes = len(json.dumps(tool_calls, ensure_ascii=False).encode("utf-8")) if tool_calls else 0
            metrics.append(
                {
                    "index": index,
                    "role": message.get("role", "unknown"),
                    "chars": content_metrics["chars"],
                    "bytes": content_metrics["bytes"],
                    "lines": content_metrics["lines"],
                    "parts": content_metrics["parts"],
                    "non_text_parts": content_metrics["non_text_parts"],
                    "tool_calls": len(tool_calls),
                    "tool_call_bytes": tool_call_bytes,
                }
            )
        return metrics

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise ChatClientError("Client is not configured because the API key is missing.")

        payload_json = json.dumps(payload, ensure_ascii=False)
        payload_bytes = len(payload_json.encode("utf-8"))
        model_name = str(payload.get("model") or self.default_model)
        message_count = len(payload.get("messages") or [])
        request_id = uuid4().hex[:12]
        message_metrics = self._collect_payload_message_metrics(payload)
        if self._should_print_payload_messages(model_name):
            self._print_payload_messages(model_name=model_name, request_id=request_id, payload=payload)
        trace_event(
            "llm.request",
            request_id=request_id,
            model=model_name,
            base_url=self.base_url,
            payload_bytes=payload_bytes,
            message_count=message_count,
            timeout_s=self.request_timeout_seconds,
            message_metrics=message_metrics,
            message_previews=self._collect_compact_message_previews(payload),
        )

        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=payload_json.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        for attempt in range(self.max_retries + 1):
            attempt_started_at = time.perf_counter()
            try:
                with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                elapsed = time.perf_counter() - attempt_started_at
                trace_event(
                    "llm.request_success",
                    request_id=request_id,
                    model=model_name,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                    elapsed_s=round(elapsed, 3),
                    response_bytes=len(raw.encode("utf-8")),
                )
                break
            except urllib.error.HTTPError as exc:
                elapsed = time.perf_counter() - attempt_started_at
                body = exc.read().decode("utf-8", errors="ignore")
                trace_event(
                    "llm.http_error",
                    request_id=request_id,
                    model=model_name,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                    elapsed_s=round(elapsed, 3),
                    status_code=exc.code,
                    body_bytes=len(body.encode("utf-8")),
                    will_retry=self._should_retry_http_status(exc.code) and attempt < self.max_retries,
                )
                if self._should_retry_http_status(exc.code) and attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                attempts = attempt + 1
                raise ChatClientError(f"HTTP {exc.code} after {attempts} attempt(s): {body}") from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                elapsed = time.perf_counter() - attempt_started_at
                reason = getattr(exc, "reason", exc)
                trace_event(
                    "llm.network_error",
                    request_id=request_id,
                    model=model_name,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                    elapsed_s=round(elapsed, 3),
                    reason=str(reason),
                    will_retry=self._should_retry_network_error(reason) and attempt < self.max_retries,
                )
                if self._should_retry_network_error(reason) and attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                attempts = attempt + 1
                raise ChatClientError(f"Network error after {attempts} attempt(s): {reason}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ChatClientError(f"Invalid JSON response: {raw[:1000]}") from exc
        usage = parsed.get("usage") or {}
        choices = parsed.get("choices") or []
        first_choice = choices[0] if choices else {}
        trace_event(
            "llm.response",
            request_id=request_id,
            model=model_name,
            usage=usage or None,
            finish_reason=first_choice.get("finish_reason"),
        )
        return parsed

    @staticmethod
    def _should_retry_http_status(status_code: int) -> bool:
        return status_code in {408, 409, 429, 500, 502, 503, 504}

    @staticmethod
    def _should_retry_network_error(reason: Any) -> bool:
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return True

        text = str(reason).strip().lower()
        retry_markers = (
            "timed out",
            "timeout",
            "temporarily unavailable",
            "temporary failure",
            "connection reset",
            "connection aborted",
            "server disconnected",
            "gateway time-out",
            "gateway timeout",
        )
        return any(marker in text for marker in retry_markers)

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        choices = response.get("choices") or []
        if not choices:
            raise ChatClientError(f"Invalid response payload: {response}")
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") in {"text", "output_text"}:
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        parts.append(str(text))
            return "\n".join(parts)
        return str(content)

    def chat_text(
        self,
        *,
        system_prompt: str,
        user_content: str | list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
        }
        if extra_body:
            payload.update(extra_body)
        return self._extract_text(self._post_json(payload))

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_content: str,
        model: str | None = None,
        temperature: float = 0.0,
        extra_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if extra_body:
            payload.update(extra_body)

        try:
            return safe_json_loads(self._extract_text(self._post_json(payload)), default={})
        except Exception:
            fallback_payload = {
                "model": model or self.default_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_content}\n\n请严格返回单个 JSON 对象，不要使用 Markdown 代码块。"},
                ],
                "temperature": temperature,
            }
            if extra_body:
                fallback_payload.update(extra_body)
            return safe_json_loads(self._extract_text(self._post_json(fallback_payload)), default={})


class QwenClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        text_model: str,
        vision_model: str,
        enable_web_search: bool,
    ):
        self.text_client = OpenAICompatibleClient(api_key=api_key, base_url=base_url, default_model=text_model)
        self.vision_client = OpenAICompatibleClient(api_key=api_key, base_url=base_url, default_model=vision_model)
        self.enable_web_search = enable_web_search

    @property
    def is_available(self) -> bool:
        return self.text_client.is_available

    def chat_text(self, *, system_prompt: str, user_content: str, with_search: bool = False) -> str:
        extra_body = {"enable_search": True} if with_search and self.enable_web_search else None
        try:
            return self.text_client.chat_text(
                system_prompt=system_prompt,
                user_content=user_content,
                extra_body=extra_body,
            )
        except Exception:
            return self.text_client.chat_text(system_prompt=system_prompt, user_content=user_content)

    def chat_json(self, *, system_prompt: str, user_content: str) -> dict[str, Any]:
        return self.text_client.chat_json(system_prompt=system_prompt, user_content=user_content)

    def analyze_images(self, *, system_prompt: str, user_prompt: str, image_paths: list[str]) -> str:
        if not self.vision_client.is_available:
            raise ChatClientError("Qwen vision client is not configured.")

        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for path in image_paths:
            content.append({"type": "image_url", "image_url": {"url": file_to_data_url(path)}})

        return self.vision_client.chat_text(
            system_prompt=system_prompt,
            user_content=content,
            temperature=0.1,
        )


class OpenAICodegenClient:
    def __init__(self, *, api_key: str | None, base_url: str, model: str):
        self.client = OpenAICompatibleClient(api_key=api_key, base_url=base_url, default_model=model)

    @property
    def is_available(self) -> bool:
        return self.client.is_available

    def generate_blender_script(self, *, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat_text(
            system_prompt=system_prompt,
            user_content=user_prompt,
            temperature=0.1,
        )
        return clean_code_fence(response)


class OpenAICompatibleChatModel(BaseChatModel):
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4.1"
    temperature: float = 0.1
    extra_body: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def _llm_type(self) -> str:
        return "openai_compatible_chat_model"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model_name": self.model_name, "base_url": self.base_url}

    def bind_tools(
        self,
        tools: list[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable:
        openai_tools = [convert_to_openai_tool(tool) for tool in tools]
        bind_kwargs: dict[str, Any] = {"tools": openai_tools}
        if tool_choice:
            bind_kwargs["tool_choice"] = tool_choice
        bind_kwargs.update(kwargs)
        return self.bind(**bind_kwargs)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        client = OpenAICompatibleClient(
            api_key=self.api_key,
            base_url=self.base_url,
            default_model=self.model_name,
        )
        payload: dict[str, Any] = {
            "model": kwargs.pop("model", self.model_name),
            "messages": [self._message_to_openai_payload(message) for message in messages],
            "temperature": kwargs.pop("temperature", self.temperature),
        }
        if stop:
            payload["stop"] = stop
        if self.extra_body:
            payload.update(self.extra_body)
        payload.update(kwargs)

        response = client._post_json(payload)
        choices = response.get("choices") or []
        if not choices:
            raise ChatClientError(f"Invalid response payload: {response}")
        choice = choices[0]
        ai_message = self._choice_to_ai_message(choice)
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    @staticmethod
    def _message_to_openai_payload(message: BaseMessage) -> dict[str, Any]:
        content = OpenAICompatibleChatModel._normalize_message_content(message.content)
        if isinstance(message, SystemMessage):
            return {"role": "system", "content": content}
        if isinstance(message, HumanMessage):
            payload = {"role": "user", "content": content}
            if message.name:
                payload["name"] = message.name
            return payload
        if isinstance(message, ToolMessage):
            payload = {
                "role": "tool",
                "content": content,
                "tool_call_id": message.tool_call_id,
            }
            if message.name:
                payload["name"] = message.name
            return payload
        if isinstance(message, AIMessage):
            payload = {"role": "assistant", "content": content}
            if message.tool_calls:
                payload["tool_calls"] = [
                    {
                        "id": tool_call.get("id"),
                        "type": "function",
                        "function": {
                            "name": tool_call.get("name"),
                            "arguments": json.dumps(tool_call.get("args", {}), ensure_ascii=False),
                        },
                    }
                    for tool_call in message.tool_calls
                ]
            return payload
        return {"role": "user", "content": content}

    @staticmethod
    def _choice_to_ai_message(choice: dict[str, Any]) -> AIMessage:
        message = choice.get("message") or {}
        content = OpenAICompatibleChatModel._normalize_message_content(message.get("content", ""))
        tool_calls = []
        for raw_tool_call in message.get("tool_calls", []) or []:
            function_data = raw_tool_call.get("function") or {}
            raw_arguments = function_data.get("arguments") or "{}"
            if isinstance(raw_arguments, str):
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    arguments = {"raw_arguments": raw_arguments}
            elif isinstance(raw_arguments, dict):
                arguments = raw_arguments
            else:
                arguments = {"raw_arguments": str(raw_arguments)}
            tool_calls.append(
                {
                    "id": raw_tool_call.get("id") or function_data.get("name") or "tool_call",
                    "name": function_data.get("name") or "tool",
                    "args": arguments,
                    "type": "tool_call",
                }
            )
        return AIMessage(
            content=content,
            tool_calls=tool_calls,
            response_metadata={"finish_reason": choice.get("finish_reason")},
        )

    @staticmethod
    def _normalize_message_content(content: Any) -> str | list[dict[str, Any]]:
        if content is None:
            return ""
        if isinstance(content, (str, list)):
            return content
        return str(content)


def build_stub_script(design_prompt: str, geometry_summary: str, *, failure_reason: str | None = None) -> str:
    def as_triple_quoted_literal(text: str) -> str:
        normalized = text.replace("\r\n", "\n")
        return '"""' + normalized.replace('"""', '\\"""') + '"""'

    prompt_literal = as_triple_quoted_literal(compact_text(design_prompt, 2400))
    geometry_literal = as_triple_quoted_literal(compact_text(geometry_summary, 1800))
    reason_literal = as_triple_quoted_literal(compact_text(failure_reason or "No failure reason was captured.", 1400))
    return f'''import bpy


DESIGN_PROMPT = {prompt_literal}
GEOMETRY_SUMMARY = {geometry_literal}
FALLBACK_REASON = {reason_literal}


def generate_building():
    print("LLM generation did not succeed. This is a placeholder script.")
    print("Fallback reason:")
    print(FALLBACK_REASON)
    print("Design prompt:")
    print(DESIGN_PROMPT)
    print("Geometry summary:")
    print(GEOMETRY_SUMMARY)


generate_building()
'''

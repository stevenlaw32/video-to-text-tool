"""OpenAI Chat Completions / Responses API 兼容层。

这里仅处理端点之间稳定的协议差异，不根据模型名称猜测能力。模型参数保持
显式配置；``auto`` 优先尝试 Responses，只有端点明确不可用时才回退 Chat。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


API_MODES = {"auto", "chat", "responses"}
REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
CACHE_TTLS = {"auto", "off", "30m", "12h"}


def resolve_api_mode(api_mode: Optional[str] = "auto") -> str:
    """Resolve the preferred endpoint without inspecting the model identifier."""
    mode = (api_mode or "auto").strip().lower()
    if mode not in API_MODES:
        raise ValueError(f"不支持的 API 模式: {api_mode}")
    return "responses" if mode == "auto" else mode


def resolve_reasoning_effort(value: Optional[str]) -> Optional[str]:
    """Return an explicitly configured effort; ``auto`` delegates to the model."""
    effort = (value or "auto").strip().lower()
    if effort == "auto":
        return None
    if effort not in REASONING_EFFORTS:
        raise ValueError(f"不支持的推理强度: {value}")
    return effort


def resolve_cache_ttl(api_mode: str, value: Optional[str]) -> Optional[str]:
    """Only send a cache TTL when it was explicitly selected for Responses."""
    ttl = (value or "auto").strip().lower()
    if ttl not in CACHE_TTLS:
        raise ValueError(f"不支持的提示词缓存 TTL: {value}")
    if api_mode != "responses" or ttl in {"auto", "off"}:
        return None
    return ttl


def normalize_service_tier(value: Optional[str]) -> Optional[str]:
    tier = (value or "auto").strip().lower()
    if tier in {"", "auto"}:
        return None
    return tier


def _responses_input(
    user_message: str,
    developer_prompt: Optional[str],
    messages_history: Optional[Iterable[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Keep reusable instructions as the first developer item and append history."""
    items: List[Dict[str, Any]] = []
    if developer_prompt:
        items.append({"role": "developer", "content": developer_prompt})

    for message in messages_history or []:
        copied = dict(message)
        if copied.get("role") == "system":
            copied["role"] = "developer"
        items.append(copied)

    items.append({"role": "user", "content": user_message})
    return items


def _chat_messages(
    user_message: str,
    system_prompt: Optional[str],
    messages_history: Optional[Iterable[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(dict(message) for message in (messages_history or []))
    messages.append({"role": "user", "content": user_message})
    return messages


def build_request(
    *,
    model: str,
    user_message: str,
    developer_prompt: Optional[str] = None,
    messages_history: Optional[Iterable[Dict[str, Any]]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    reasoning_effort: Optional[str] = None,
    api_mode: Optional[str] = "auto",
    prompt_cache_ttl: Optional[str] = "auto",
    service_tier: Optional[str] = "auto",
    tools: Any = None,
    stream: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Build a sanitized request and return ``(endpoint, parameters)``."""
    mode = resolve_api_mode(api_mode)
    effort = resolve_reasoning_effort(reasoning_effort)
    ttl = resolve_cache_ttl(mode, prompt_cache_ttl)
    tier = normalize_service_tier(service_tier)

    if mode == "responses":
        params: Dict[str, Any] = {
            "model": model,
            "input": _responses_input(user_message, developer_prompt, messages_history),
        }
        if max_tokens is not None:
            params["max_output_tokens"] = max_tokens
        if effort:
            params["reasoning"] = {"effort": effort}
        if ttl:
            params["prompt_cache_options"] = {"ttl": ttl}
        if tools:
            params["tools"] = tools
        if temperature is not None:
            params["temperature"] = temperature
    else:
        params = {
            "model": model,
            "messages": _chat_messages(user_message, developer_prompt, messages_history),
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if effort:
            params["reasoning_effort"] = effort
        if tools:
            params["tools"] = tools
        if temperature is not None:
            params["temperature"] = temperature

    if tier:
        params["service_tier"] = tier
    if stream:
        params["stream"] = True
    return mode, params


def _get_value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def extract_response_text(response: Any) -> str:
    """Extract text from either endpoint without depending on SDK response classes."""
    direct = _get_value(response, "output_text")
    if direct:
        return str(direct)

    choices = _get_value(response, "choices", []) or []
    if choices:
        message = _get_value(choices[0], "message")
        content = _get_value(message, "content")
        if content is not None:
            return str(content)

    fragments: List[str] = []
    for output in _get_value(response, "output", []) or []:
        for content in _get_value(output, "content", []) or []:
            if _get_value(content, "type") == "output_text":
                text = _get_value(content, "text")
                if text:
                    fragments.append(str(text))
    return "".join(fragments)


def _is_auto_mode(kwargs: Dict[str, Any]) -> bool:
    return (kwargs.get("api_mode") or "auto").strip().lower() == "auto"


def _endpoint_unavailable(error: Exception) -> bool:
    """Recognize errors that safely indicate the Responses endpoint is absent."""
    status_code = getattr(error, "status_code", None)
    if status_code in {404, 405, 501}:
        return True
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "unknown endpoint",
            "unsupported endpoint",
            "responses endpoint is not supported",
            "responses api is not supported",
        )
    )


def _request_modes(kwargs: Dict[str, Any]) -> Tuple[str, ...]:
    if _is_auto_mode(kwargs):
        return ("responses", "chat")
    return (resolve_api_mode(kwargs.get("api_mode")),)


def complete_text(client: Any, **kwargs: Any) -> str:
    """Create one text response through the selected endpoint."""
    modes = _request_modes(kwargs)
    for index, mode in enumerate(modes):
        request_kwargs = dict(kwargs, api_mode=mode)
        _, params = build_request(**request_kwargs)
        try:
            if mode == "responses":
                responses = getattr(client, "responses", None)
                if responses is None:
                    if len(modes) > 1:
                        continue
                    raise RuntimeError("当前 openai SDK 不支持 Responses API，请升级到 openai 3.x")
                response = responses.create(**params)
            else:
                response = client.chat.completions.create(**params)
            return extract_response_text(response)
        except Exception as error:
            can_fallback = (
                index + 1 < len(modes)
                and not kwargs.get("tools")
                and _endpoint_unavailable(error)
            )
            if not can_fallback:
                raise
    raise RuntimeError("没有可用的模型调用端点")


def stream_text(client: Any, **kwargs: Any) -> Iterator[str]:
    """Yield text deltas from Chat Completions or Responses streaming events."""
    modes = _request_modes(kwargs)
    for index, mode in enumerate(modes):
        request_kwargs = dict(kwargs, api_mode=mode)
        _, params = build_request(stream=True, **request_kwargs)
        emitted = False
        try:
            if mode == "responses":
                responses = getattr(client, "responses", None)
                if responses is None:
                    if len(modes) > 1:
                        continue
                    raise RuntimeError("当前 openai SDK 不支持 Responses API，请升级到 openai 3.x")
                for event in responses.create(**params):
                    if _get_value(event, "type") == "response.output_text.delta":
                        delta = _get_value(event, "delta")
                        if delta:
                            emitted = True
                            yield str(delta)
                return

            for chunk in client.chat.completions.create(**params):
                choices = _get_value(chunk, "choices", []) or []
                if not choices:
                    continue
                delta = _get_value(choices[0], "delta")
                content = _get_value(delta, "content")
                if content:
                    emitted = True
                    yield str(content)
            return
        except Exception as error:
            can_fallback = (
                not emitted
                and index + 1 < len(modes)
                and not kwargs.get("tools")
                and _endpoint_unavailable(error)
            )
            if not can_fallback:
                raise
    raise RuntimeError("没有可用的模型调用端点")

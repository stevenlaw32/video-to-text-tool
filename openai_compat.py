"""OpenAI Chat Completions / Responses API 兼容层。

项目同时支持 OpenAI 官方接口和 OpenAI-compatible 供应商。这里集中处理
GPT-6.2 Astra / Sol 的迁移规则，避免每条业务路由各自拼请求参数。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


GPT62_RESPONSES_PREFIXES = ("gpt-6.2-astra", "gpt-6.2-sol")
API_MODES = {"auto", "chat", "responses"}
REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
CACHE_TTLS = {"auto", "off", "30m", "12h"}


def is_gpt62_astra_or_sol(model: str) -> bool:
    """Return whether the model belongs to the GPT-6.2 Astra/Sol API family."""
    normalized = (model or "").strip().lower().rsplit("/", 1)[-1]
    return normalized.startswith(GPT62_RESPONSES_PREFIXES)


def resolve_api_mode(model: str, api_mode: Optional[str] = "auto", tools: Any = None) -> str:
    """Resolve the endpoint while enforcing the GPT-6.2 tool-calling rule."""
    mode = (api_mode or "auto").strip().lower()
    if mode not in API_MODES:
        raise ValueError(f"不支持的 API 模式: {api_mode}")

    if mode == "auto":
        mode = "responses" if is_gpt62_astra_or_sol(model) else "chat"

    if tools and is_gpt62_astra_or_sol(model) and mode != "responses":
        raise ValueError("GPT-6.2 Astra/Sol 的工具调用必须使用 Responses API")
    return mode


def resolve_reasoning_effort(model: str, value: Optional[str]) -> Optional[str]:
    """Map legacy efforts to supported GPT-6.2 values and select new defaults."""
    effort = (value or "auto").strip().lower()
    if effort == "auto":
        return "medium" if is_gpt62_astra_or_sol(model) else None
    if effort not in REASONING_EFFORTS:
        raise ValueError(f"不支持的推理强度: {value}")
    if is_gpt62_astra_or_sol(model) and effort in {"none", "minimal"}:
        return "low"
    return effort


def resolve_cache_ttl(model: str, api_mode: str, value: Optional[str]) -> Optional[str]:
    """Resolve the current prompt-cache TTL parameter for Responses requests."""
    ttl = (value or "auto").strip().lower()
    if ttl not in CACHE_TTLS:
        raise ValueError(f"不支持的提示词缓存 TTL: {value}")
    if api_mode != "responses" or ttl == "off":
        return None
    if ttl == "auto":
        return "30m" if is_gpt62_astra_or_sol(model) else None
    return ttl


def validate_service_tier(model: str, value: Optional[str]) -> Optional[str]:
    tier = (value or "auto").strip().lower()
    if tier in {"", "auto"}:
        return None
    if is_gpt62_astra_or_sol(model) and tier == "flex":
        raise ValueError("GPT-6.2 Astra/Sol 不支持 service_tier=flex")
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
    mode = resolve_api_mode(model, api_mode, tools)
    effort = resolve_reasoning_effort(model, reasoning_effort)
    ttl = resolve_cache_ttl(model, mode, prompt_cache_ttl)
    tier = validate_service_tier(model, service_tier)

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
        if not is_gpt62_astra_or_sol(model) and temperature is not None:
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
        if not is_gpt62_astra_or_sol(model) and temperature is not None:
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


def complete_text(client: Any, **kwargs: Any) -> str:
    """Create one text response through the selected endpoint."""
    mode, params = build_request(**kwargs)
    if mode == "responses":
        responses = getattr(client, "responses", None)
        if responses is None:
            raise RuntimeError("当前 openai SDK 不支持 Responses API，请升级到 openai 3.x")
        response = responses.create(**params)
    else:
        response = client.chat.completions.create(**params)
    return extract_response_text(response)


def stream_text(client: Any, **kwargs: Any) -> Iterator[str]:
    """Yield text deltas from Chat Completions or Responses streaming events."""
    mode, params = build_request(stream=True, **kwargs)
    if mode == "responses":
        responses = getattr(client, "responses", None)
        if responses is None:
            raise RuntimeError("当前 openai SDK 不支持 Responses API，请升级到 openai 3.x")
        events = responses.create(**params)
        for event in events:
            if _get_value(event, "type") == "response.output_text.delta":
                delta = _get_value(event, "delta")
                if delta:
                    yield str(delta)
        return

    chunks = client.chat.completions.create(**params)
    for chunk in chunks:
        choices = _get_value(chunk, "choices", []) or []
        if not choices:
            continue
        delta = _get_value(choices[0], "delta")
        content = _get_value(delta, "content")
        if content:
            yield str(content)

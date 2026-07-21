from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, status

from graduate_entrance.core.config import Settings, get_settings


class ToolsUnsupportedError(Exception):
    """Raised when the provider rejects a request that includes tool definitions."""


@dataclass(frozen=True)
class AssistantTurn:
    content: str
    reasoning: str
    tool_calls: list[dict[str, Any]]


def is_ai_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(
        settings.ai_base_url
        and settings.ai_api_key.get_secret_value()
        and settings.ai_model
    )


async def complete_chat(
    messages: list[dict[str, Any]],
    settings: Settings | None = None,
    reasoning_effort: str | None = None,
    response_format: dict[str, Any] | None = None,
) -> str:
    """Call the configured OpenAI-compatible chat completions endpoint."""
    settings = settings or get_settings()
    if not is_ai_configured(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI extraction is not configured",
        )
    url = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {"model": settings.ai_model, "messages": messages}
    effort = reasoning_effort or settings.ai_reasoning_effort
    if effort:
        payload["reasoning_effort"] = effort
    if response_format is not None:
        payload["response_format"] = response_format
    headers = {"Authorization": f"Bearer {settings.ai_api_key.get_secret_value()}"}
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            if (
                response_format is not None
                and response.status_code in (400, 404, 422, 501)
            ):
                # provider 不支持 response_format 时退回普通请求
                payload.pop("response_format")
                response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider request failed",
        ) from exc
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an unexpected response",
        ) from exc
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an empty response",
        )
    return content


async def complete_chat_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    settings: Settings | None = None,
    reasoning_effort: str | None = None,
) -> AssistantTurn:
    """Call the chat endpoint with tool definitions and return the assistant turn.

    Raises ``ToolsUnsupportedError`` when the provider rejects tool usage so the
    caller can gracefully fall back to a plain completion.
    """
    settings = settings or get_settings()
    if not is_ai_configured(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI extraction is not configured",
        )
    url = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": settings.ai_model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    effort = reasoning_effort or settings.ai_reasoning_effort
    if effort:
        payload["reasoning_effort"] = effort
    headers = {"Authorization": f"Bearer {settings.ai_api_key.get_secret_value()}"}
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (400, 404, 422, 501):
                raise ToolsUnsupportedError(response.text)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider request failed",
        ) from exc
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an unexpected response",
        ) from exc
    content = message.get("content")
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    raw_tool_calls = message.get("tool_calls") or []
    tool_calls = [call for call in raw_tool_calls if isinstance(call, dict)]
    return AssistantTurn(
        content=content if isinstance(content, str) else "",
        reasoning=reasoning if isinstance(reasoning, str) else "",
        tool_calls=tool_calls,
    )

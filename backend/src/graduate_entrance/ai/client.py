from typing import Any

import httpx
from fastapi import HTTPException, status

from graduate_entrance.core.config import Settings, get_settings


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
    headers = {"Authorization": f"Bearer {settings.ai_api_key.get_secret_value()}"}
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
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

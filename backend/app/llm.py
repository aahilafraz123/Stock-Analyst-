"""Thin wrapper around the Anthropic SDK: structured JSON outputs and cited answers."""

import copy
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel

from app.config import settings
from app.errors import ConfigError, LLMError, UpstreamError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
Progress = Callable[[dict], Awaitable[None]]
SOURCE = "Anthropic"

_client: anthropic.AsyncAnthropic | None = None


def client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        # With no explicit key the SDK falls back to ANTHROPIC_AUTH_TOKEN / an `ant` profile.
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None, timeout=300, max_retries=2)
    return _client


def strict_schema(model: type[BaseModel]) -> dict:
    """Pydantic JSON schema -> the strict subset structured outputs accepts.

    Inlines $refs, requires every property and forbids extra keys on every object.
    """
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node: Any, is_properties: bool = False) -> Any:
        if isinstance(node, dict):
            if is_properties:  # keys here are field names, not schema keywords
                return {name: walk(sub) for name, sub in node.items()}
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            node = {
                k: walk(v, is_properties=(k == "properties")) for k, v in node.items() if k not in ("title", "default")
            }
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            return node
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def _request_options() -> dict:
    if not settings.anthropic_fallbacks:
        return {}
    # Server-side refusal fallbacks: a declined request is retried on a fallback model
    # inside the same call. Sent as raw header/body so it works across SDK versions.
    return {
        "extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"},
        "extra_body": {"fallbacks": settings.anthropic_fallbacks},
    }


def _usage(response, started: float) -> dict:
    usage = getattr(response, "usage", None)
    return {
        "model": getattr(response, "model", settings.anthropic_model),
        "inputTokens": getattr(usage, "input_tokens", None),
        "outputTokens": getattr(usage, "output_tokens", None),
        "cacheReadTokens": getattr(usage, "cache_read_input_tokens", None),
        "stopReason": getattr(response, "stop_reason", None),
        "latencyMs": int((time.perf_counter() - started) * 1000),
    }


def _translate(exc: Exception) -> Exception:
    """Map SDK exceptions (most specific first) to the app's typed errors."""
    if isinstance(exc, anthropic.AuthenticationError):
        return ConfigError("Anthropic rejected the API key (check ANTHROPIC_API_KEY)", source=SOURCE)
    if isinstance(exc, anthropic.PermissionDeniedError):
        return ConfigError(f"Anthropic API key lacks access: {exc.message}", source=SOURCE)
    if isinstance(exc, anthropic.RateLimitError):
        return LLMError("Anthropic rate limit hit; retry shortly", source=SOURCE)
    if isinstance(exc, anthropic.BadRequestError):
        return LLMError(f"Anthropic rejected the request: {exc.message}", source=SOURCE)
    if isinstance(exc, anthropic.APIStatusError):
        return LLMError(f"Anthropic API error {exc.status_code}: {exc.message}", source=SOURCE)
    if isinstance(exc, anthropic.APIConnectionError):
        return UpstreamError(f"Could not reach the Anthropic API: {exc}", source=SOURCE)
    if isinstance(exc, TypeError) and any(w in str(exc).lower() for w in ("authentication", "api_key")):
        return ConfigError("ANTHROPIC_API_KEY is not set", source=SOURCE)  # no credentials resolved
    return exc


def _params(**params) -> dict:
    return {"model": settings.anthropic_model, **params, **_request_options()}


async def _create(**params):
    try:
        return await client().messages.create(**_params(**params))
    except Exception as exc:
        translated = _translate(exc)
        if translated is exc:
            raise
        raise translated from exc


def _check_stop(response) -> None:
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        raise LLMError(
            f"Claude declined the request ({getattr(details, 'category', None) or 'refusal'})", source=SOURCE
        )
    if response.stop_reason == "max_tokens":
        raise LLMError("Claude's response was cut off at max_tokens", source=SOURCE)


def _text_blocks(response) -> list:
    return [b for b in response.content if getattr(b, "type", None) == "text"]


async def structured(
    system: str,
    content: str | list,
    output: type[T],
    max_tokens: int = 32000,
    on_progress: Progress | None = None,
) -> tuple[T, dict]:
    """Schema-constrained JSON output, streamed so long inputs don't hit HTTP timeouts
    and so callers can show live progress (`thinking`, then `writing` with a char count)."""
    started = time.perf_counter()
    params = _params(
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_config={
            "format": {"type": "json_schema", "schema": strict_schema(output)},
            "effort": settings.anthropic_effort,
        },
    )
    try:
        async with client().messages.stream(**params) as stream:
            phase, chars, last_emit = None, 0, 0.0
            async for event in stream:
                if on_progress is None:
                    continue
                if event.type == "thinking" and phase is None:
                    phase = "thinking"
                    await on_progress({"phase": phase})
                elif event.type == "text":
                    chars += len(event.text)
                    now = time.perf_counter()
                    if phase != "writing" or now - last_emit > 0.75:
                        phase, last_emit = "writing", now
                        await on_progress({"phase": phase, "chars": chars})
            response = await stream.get_final_message()
    except Exception as exc:
        translated = _translate(exc)
        if translated is exc:
            raise
        raise translated from exc
    _check_stop(response)
    blocks = _text_blocks(response)
    if not blocks:
        raise LLMError("Claude returned no text output", source=SOURCE)
    try:
        parsed = output.model_validate_json(blocks[-1].text)
    except ValueError as exc:
        raise LLMError(f"Claude's output did not match the report schema: {exc}", source=SOURCE) from exc
    return parsed, _usage(response, started)


async def cited_answer(system: str, documents: list[dict], question: str, max_tokens: int = 8000) -> tuple[list, dict]:
    """Ask a question over documents with the Citations API; returns raw text blocks + usage."""
    started = time.perf_counter()
    response = await _create(
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": [*documents, {"type": "text", "text": question}]}],
        output_config={"effort": settings.anthropic_effort},
    )
    _check_stop(response)
    return _text_blocks(response), _usage(response, started)

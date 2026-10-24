"""OpenAI-compatible DeepSeek transport with JSON validation and model fallback."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import openai
from openai import AsyncOpenAI

from app.config import Settings

T = TypeVar("T")
Validator = Callable[[dict[str, Any]], T | None]


class DeepSeekError(Exception):
    """A non-retryable DeepSeek failure."""


class DeepSeekUnavailableError(DeepSeekError):
    """No API key or client available."""


class ModelUnavailableError(DeepSeekError):
    """The requested model does not exist; retry with the fast model."""


@dataclass(frozen=True, slots=True)
class CompletionResult:
    content: str | None


CompletionCallable = Callable[..., Awaitable[CompletionResult]]


class DeepSeekChat:
    """Small adapter around the chat-completions endpoint.

    Tries the reasoning model, retries empty/invalid JSON once, then falls back
    to the fast model on ``model_not_found``. Never raises to the caller.
    """

    def __init__(
        self, settings: Settings, *, completion: CompletionCallable | None = None
    ) -> None:
        self._settings = settings
        self._completion = completion
        self._client: AsyncOpenAI | None = None

    async def request_json(
        self,
        *,
        system: str,
        user: str,
        validator: Validator[T],
        budget_sec: float | None = None,
    ) -> T | None:
        timeout = budget_sec if budget_sec is not None else self._settings.deepseek_timeout_sec
        if timeout <= 0:
            return None
        try:
            return await asyncio.wait_for(
                self._try_models(system, user, validator), timeout=timeout
            )
        except Exception:
            return None

    async def _try_models(
        self, system: str, user: str, validator: Validator[T]
    ) -> T | None:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        models = (self._settings.deepseek_reasoning_model, self._settings.deepseek_fast_model)
        for model in dict.fromkeys(models):
            for _attempt in range(2):
                try:
                    parsed = await self._call_json(model, messages, validator)
                except ModelUnavailableError:
                    break
                except Exception:
                    return None
                if parsed is not None:
                    return parsed
        return None

    async def _call_json(
        self, model: str, messages: list[dict[str, str]], validator: Validator[T]
    ) -> T | None:
        result = await self._complete(**self._request_kwargs(model, messages))
        if not result.content:
            return None
        payload = _loads_json(result.content)
        return validator(payload) if payload is not None else None

    def _request_kwargs(self, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        if model == self._settings.deepseek_reasoning_model:
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            kwargs["reasoning_effort"] = "max"
        else:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        return kwargs

    async def _complete(self, **kwargs: Any) -> CompletionResult:
        if self._completion is not None:
            return await self._completion(**kwargs)
        api_key = self._settings.deepseek_api_key
        if not api_key:
            raise DeepSeekUnavailableError("DEEPSEEK_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self._settings.deepseek_base_url,
                timeout=self._settings.deepseek_timeout_sec,
            )
        try:
            response = await self._client.chat.completions.create(**kwargs)
        except (openai.NotFoundError, openai.BadRequestError) as exc:
            if _is_model_missing(exc):
                raise ModelUnavailableError(str(exc)) from exc
            raise DeepSeekError(str(exc)) from exc
        except openai.OpenAIError as exc:
            raise DeepSeekError(str(exc)) from exc
        if not response.choices:
            return CompletionResult(content=None)
        return CompletionResult(content=response.choices[0].message.content)


def _loads_json(content: str) -> dict[str, Any] | None:
    candidates = [content.strip()]
    fence = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if fence is not None:
        candidates.append(fence.group(1).strip())
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        candidates.append(content[start : end + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _is_model_missing(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in ("model_not_found", "model not found", "does not exist", "invalid model")
    )

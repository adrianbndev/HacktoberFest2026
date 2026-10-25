"""DeepSeek-only product relevance for the deep market analysis.

`/analyze` has no deterministic product prefilter: every sanitised listing is
classified by `deepseek-flash` in small JSON batches. Only listings labelled
`exact` feed the price triplet. A missing key, transport error, timeout or
invalid payload fails the analysis with a typed error (never a silent subset
and never the full sample as a fallback).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from time import monotonic
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.config import Settings
from app.mcp.deepseek_client import DeepSeekChat
from app.mcp.llm_relevance_prompt import SYSTEM_PROMPT, build_user_prompt
from app.models.market_analysis import MarketAnalysisRequest
from app.models.sdd import MarketListingSample

logger = logging.getLogger(__name__)

EXACT = "exact"
LABELS = frozenset(
    {
        "exact",
        "different_model",
        "accessory",
        "single_item",
        "broken",
        "unrelated",
        "bundle",
    }
)
UNKNOWN_LABEL = "unrelated"

LLM_RELEVANCE_UNAVAILABLE = "llm_relevance_unavailable"
LLM_RELEVANCE_TIMEOUT = "llm_relevance_timeout"
LLM_RELEVANCE_DISABLED = "llm_relevance_disabled"
LLM_RELEVANCE_EMPTY = "llm_relevance_empty"

# A batch is one LLM round; keep the fan-out bounded so `batch_size=1` with a
# large sample cannot open one request per listing at once.
MAX_BATCH_CONCURRENCY = 4

class LlmRelevanceUnavailableError(Exception):
    """The LLM could not decide relevance; the caller must return a 503."""

    def __init__(self, code: str = LLM_RELEVANCE_UNAVAILABLE) -> None:
        super().__init__(code)
        self.code = code


class RelevanceClassifierProtocol(Protocol):
    async def classify(
        self,
        request: MarketAnalysisRequest,
        listings: Sequence[MarketListingSample],
        deadline: float,
    ) -> list[MarketListingSample]: ...


class _LabeledListing(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    label: str

    @field_validator("id", mode="before")
    @classmethod
    def _reject_bool_id(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("listing id must be an integer")
        return value

    @field_validator("label")
    @classmethod
    def _require_known_label(cls, value: str) -> str:
        normalised = value.strip().lower()
        if normalised not in LABELS:
            raise ValueError(f"unknown relevance label: {value!r}")
        return normalised


class _RelevanceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    listings: list[_LabeledListing] = Field(..., min_length=1)


def _validate_response(payload: dict[str, object]) -> _RelevanceResponse | None:
    try:
        return _RelevanceResponse.model_validate(payload)
    except ValidationError:
        return None


class LlmRelevanceFilter:
    """Batch classifier over the shared DeepSeek JSON transport."""

    def __init__(self, settings: Settings, *, chat: DeepSeekChat | None = None) -> None:
        self._settings = settings
        self._chat = chat or DeepSeekChat(settings)

    async def classify(
        self,
        request: MarketAnalysisRequest,
        listings: Sequence[MarketListingSample],
        deadline: float,
    ) -> list[MarketListingSample]:
        if not self._settings.market_llm_relevance_enabled:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_DISABLED)
        indexed = list(enumerate(listings))
        if not indexed:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_EMPTY)

        remaining = min(
            self._settings.market_llm_relevance_budget_sec, deadline - monotonic()
        )
        if remaining <= 0:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_TIMEOUT)
        local_deadline = monotonic() + remaining
        batch_size = self._settings.market_llm_relevance_batch_size
        batches = [
            indexed[start : start + batch_size]
            for start in range(0, len(indexed), batch_size)
        ]
        semaphore = asyncio.Semaphore(min(MAX_BATCH_CONCURRENCY, len(batches)))

        async def run_batch(
            batch: Sequence[tuple[int, MarketListingSample]],
        ) -> set[str]:
            async with semaphore:
                return await self._classify_batch(
                    request, batch, remaining, local_deadline
                )

        try:
            outcomes = await asyncio.wait_for(
                asyncio.gather(
                    *(run_batch(batch) for batch in batches),
                    return_exceptions=True,
                ),
                timeout=remaining,
            )
        except TimeoutError as exc:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_TIMEOUT) from exc

        accepted_ids: set[str] = set()
        for outcome in outcomes:
            if isinstance(outcome, LlmRelevanceUnavailableError):
                raise outcome
            if isinstance(outcome, BaseException):
                logger.warning("LLM relevance batch crashed")
                raise LlmRelevanceUnavailableError(
                    LLM_RELEVANCE_UNAVAILABLE
                ) from outcome
            accepted_ids |= outcome

        return [
            listing for index, listing in indexed if str(index) in accepted_ids
        ]

    async def _classify_batch(
        self,
        request: MarketAnalysisRequest,
        batch: Sequence[tuple[int, MarketListingSample]],
        budget_sec: float,
        local_deadline: float,
    ) -> set[str]:
        response = await self._chat.request_json(
            system=SYSTEM_PROMPT,
            user=build_user_prompt(request, batch),
            validator=_validate_response,
            budget_sec=budget_sec,
            model=self._settings.llm_relevance_model,
        )
        if response is None:
            code = (
                LLM_RELEVANCE_TIMEOUT
                if monotonic() >= local_deadline
                else LLM_RELEVANCE_UNAVAILABLE
            )
            raise LlmRelevanceUnavailableError(code)
        batch_ids = {str(index) for index, _ in batch}
        returned_ids = {str(entry.id) for entry in response.listings}
        if returned_ids != batch_ids:
            logger.warning(
                "LLM relevance batch coverage mismatch: expected %d ids, got %d",
                len(batch_ids),
                len(returned_ids),
            )
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_UNAVAILABLE)
        return {
            str(entry.id) for entry in response.listings if entry.label == EXACT
        }

"""SQLite TTL cache for real deep-analysis results (brief §5.3)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.mcp import cache as cache_module
from app.mcp.cache import MarketAnalysisCache, build_cache_key

ANALYZED_AT = "2026-10-24T15:00:00Z"


def test_cache_miss_returns_none(tmp_path: Path) -> None:
    cache = MarketAnalysisCache(path=tmp_path / "cache.sqlite", ttl_sec=900)

    result = asyncio.run(cache.get("missing"))

    assert result is None


def test_cache_hit_returns_the_stored_payload(tmp_path: Path) -> None:
    cache = MarketAnalysisCache(path=tmp_path / "nested" / "cache.sqlite", ttl_sec=900)

    asyncio.run(cache.set("key", '{"priceAvg": 38}', analyzed_at=ANALYZED_AT))
    record = asyncio.run(cache.get("key"))

    assert record is not None
    assert record.payload == '{"priceAvg": 38}'
    assert record.analyzed_at == ANALYZED_AT
    assert Path(cache.path).exists()


def test_expired_entries_are_a_miss_and_are_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache_module.time, "time", lambda: 1_000.0)
    cache = MarketAnalysisCache(path=tmp_path / "cache.sqlite", ttl_sec=10)
    asyncio.run(cache.set("key", "payload", analyzed_at=ANALYZED_AT))

    monkeypatch.setattr(cache_module.time, "time", lambda: 1_011.0)
    assert asyncio.run(cache.get("key")) is None

    monkeypatch.setattr(cache_module.time, "time", lambda: 1_000.0)
    assert asyncio.run(cache.get("key")) is None


def test_ttl_zero_disables_the_hit(tmp_path: Path) -> None:
    cache = MarketAnalysisCache(path=tmp_path / "cache.sqlite", ttl_sec=0)
    asyncio.run(cache.set("key", "payload", analyzed_at=ANALYZED_AT))

    assert asyncio.run(cache.get("key")) is None


def test_key_is_isolated_by_query_score_and_sorted_sources() -> None:
    base = build_cache_key("Silla madera", 85, ["ebay", "wallapop"])

    assert base == build_cache_key("  silla   MADERA ", 85, ["wallapop", "ebay"])
    assert base != build_cache_key("Silla madera", 86, ["ebay", "wallapop"])
    assert base != build_cache_key("Silla metalica", 85, ["ebay", "wallapop"])
    assert base != build_cache_key("Silla madera", 85, ["ebay"])
    assert base != build_cache_key("Silla madera", 85, ["ebay", "milanuncios"])


def test_key_never_includes_a_description_or_user_identity() -> None:
    key = build_cache_key("Silla madera", 85, ["ebay"])

    assert "silla" not in key
    assert "descripcion" not in key
    assert len(key) == 64


def test_concurrent_reads_and_writes_do_not_corrupt_the_cache(tmp_path: Path) -> None:
    cache = MarketAnalysisCache(path=tmp_path / "cache.sqlite", ttl_sec=900)

    async def scenario() -> list[str | None]:
        await asyncio.gather(
            *(cache.set(f"key-{index}", f"payload-{index}", analyzed_at=ANALYZED_AT) for index in range(20))
        )
        records = await asyncio.gather(*(cache.get(f"key-{index}") for index in range(20)))
        return [record.payload if record else None for record in records]

    payloads = asyncio.run(scenario())

    assert payloads == [f"payload-{index}" for index in range(20)]


def test_clear_removes_every_entry(tmp_path: Path) -> None:
    cache = MarketAnalysisCache(path=tmp_path / "cache.sqlite", ttl_sec=900)
    asyncio.run(cache.set("key", "payload", analyzed_at=ANALYZED_AT))

    asyncio.run(cache.clear())

    assert asyncio.run(cache.get("key")) is None

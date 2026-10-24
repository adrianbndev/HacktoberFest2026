"""SQLite TTL cache for real deep-analysis results (brief §5.3).

The cache is deliberately generic: it stores opaque JSON payloads and an ISO
timestamp, so it depends only on the standard library. Serialization of the
Pydantic result happens in the deep-analysis engine, which keeps the dependency
direction `mcp/cache.py -> stdlib (+ settings)` intact.
"""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS market_analysis_cache (
    cache_key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    analyzed_at TEXT NOT NULL,
    expires_at REAL NOT NULL
)
"""


@dataclass(frozen=True, slots=True)
class CacheRecord:
    """A cached real analysis, as stored on disk."""

    payload: str
    analyzed_at: str


def build_cache_key(
    normalized_query: str, condition_score: int, sources: list[str] | tuple[str, ...]
) -> str:
    """Key = normalized query + condition score + sorted sources (no description)."""
    query = " ".join(normalized_query.split()).casefold()
    source_part = ",".join(sorted({source.casefold() for source in sources}))
    material = f"{query}|{int(condition_score)}|{source_part}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class MarketAnalysisCache:
    """15-minute (configurable) TTL cache with one connection per operation."""

    def __init__(self, *, path: str | Path, ttl_sec: int = 900) -> None:
        if ttl_sec < 0:
            raise ValueError("ttl_sec must be non-negative")
        self._path = str(path)
        self._ttl_sec = ttl_sec

    @property
    def path(self) -> str:
        return self._path

    @property
    def ttl_sec(self) -> int:
        return self._ttl_sec

    async def get(self, key: str) -> CacheRecord | None:
        return await asyncio.to_thread(self._get_sync, key)

    async def set(self, key: str, payload: str, *, analyzed_at: str) -> None:
        await asyncio.to_thread(self._set_sync, key, payload, analyzed_at)

    async def clear(self) -> None:
        await asyncio.to_thread(self._clear_sync)

    def _get_sync(self, key: str) -> CacheRecord | None:
        now = time.time()
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload, analyzed_at, expires_at FROM market_analysis_cache "
                "WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            payload, analyzed_at, expires_at = row
            if float(expires_at) <= now:
                connection.execute(
                    "DELETE FROM market_analysis_cache WHERE cache_key = ?", (key,)
                )
                return None
            return CacheRecord(payload=str(payload), analyzed_at=str(analyzed_at))

    def _set_sync(self, key: str, payload: str, analyzed_at: str) -> None:
        expires_at = time.time() + self._ttl_sec
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO market_analysis_cache "
                "(cache_key, payload, analyzed_at, expires_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(cache_key) DO UPDATE SET "
                "payload = excluded.payload, analyzed_at = excluded.analyzed_at, "
                "expires_at = excluded.expires_at",
                (key, payload, analyzed_at, expires_at),
            )

    def _clear_sync(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM market_analysis_cache")

    def _connect(self) -> sqlite3.Connection:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute(SCHEMA)
        return connection

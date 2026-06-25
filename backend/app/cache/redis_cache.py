"""Async Redis cache façade with JSON (de)serialization.

A thin wrapper so services depend on a stable interface rather than the redis
client directly. Eases testing (`FakeRedis` in tests).
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis_async

from app.core.config import Settings


class RedisCache:
    def __init__(self, client: redis_async.Redis, *, default_ttl: int) -> None:
        self._client = client
        self._default_ttl = default_ttl

    async def get_json(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    async def set_json(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        await self._client.set(
            key,
            json.dumps(value, default=str, separators=(",", ":")),
            ex=ttl if ttl is not None else self._default_ttl,
        )

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return int(await self._client.delete(*keys))

    async def delete_prefix(self, prefix: str) -> int:
        """Best-effort prefix delete — uses SCAN to avoid blocking Redis."""
        deleted = 0
        async for key in self._client.scan_iter(match=f"{prefix}*", count=200):
            await self._client.delete(key)
            deleted += 1
        return deleted

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


# Module-level cache keyed by URL — Settings is unhashable so we cannot use
# functools.lru_cache directly on the factory.
_CACHES: dict[str, RedisCache] = {}


def get_redis_cache(settings: Settings) -> RedisCache:
    key = settings.redis_url
    cache = _CACHES.get(key)
    if cache is None:
        client = redis_async.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        cache = RedisCache(client, default_ttl=settings.redis_cache_ttl_seconds)
        _CACHES[key] = cache
    return cache


async def dispose_redis_cache(settings: Settings) -> None:
    """Close the cached client for ``settings`` (used in lifespan teardown)."""
    cache = _CACHES.pop(settings.redis_url, None)
    if cache is not None:
        await cache.close()

"""Redis-backed token-bucket rate limiting (P2-106).

Applied per-route via FastAPI `dependencies=[...]`, not as global middleware
— the three endpoints this guards (`/session/start`, `/session/*/answer`,
`/coding/run`) have very different legitimate call rates, so each gets its
own bucket, not one shared limit.

Two dimensions, checked independently — either one being empty rejects the
request:
  - per-IP:  catches unauthenticated/pre-token abuse and any single source
             hammering the API regardless of account.
  - per-UID: catches a single authenticated account abusing its own quota,
             regardless of which IP it's coming from.

`/coding/run` has no auth dependency (P2-101 left it disabled by default;
adding auth there is out of this story's scope), so it only gets the
per-IP dimension.

Falls back to an in-process bucket when REDIS_URL is unset — same pattern
already used for session persistence in services/session_engine.py. That
fallback is single-replica-only by nature (each pod would enforce its own
limit); acceptable for local dev, not for a multi-replica deployment.
"""

from __future__ import annotations

import math
import os
import threading
import time
from typing import Dict, Tuple

from fastapi import Depends, HTTPException, Request

from deps import get_current_user
from models.auth_user import AuthUser

try:
    from redis import Redis
except ImportError:
    Redis = None


REDIS_URL = os.getenv("REDIS_URL", "").strip()
_REDIS_CLIENT = Redis.from_url(REDIS_URL, decode_responses=True) if Redis and REDIS_URL else None


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ── Defaults — deliberately generous relative to real usage patterns (a
# candidate answers roughly every 30-90s per the capacity model), tunable
# via env without a code change or new image build. ──────────────────────
SESSION_START_CAPACITY = _get_int_env("RATE_LIMIT_SESSION_START_CAPACITY", 5)
SESSION_START_REFILL_PER_MIN = _get_int_env("RATE_LIMIT_SESSION_START_REFILL_PER_MIN", 5)

SESSION_ANSWER_CAPACITY = _get_int_env("RATE_LIMIT_SESSION_ANSWER_CAPACITY", 30)
SESSION_ANSWER_REFILL_PER_MIN = _get_int_env("RATE_LIMIT_SESSION_ANSWER_REFILL_PER_MIN", 30)

CODING_RUN_CAPACITY = _get_int_env("RATE_LIMIT_CODING_RUN_CAPACITY", 20)
CODING_RUN_REFILL_PER_MIN = _get_int_env("RATE_LIMIT_CODING_RUN_REFILL_PER_MIN", 20)


# ── Redis-backed bucket: atomic check-and-consume via a Lua script ───────
#
# KEYS[1] = bucket key
# ARGV[1] = capacity
# ARGV[2] = refill tokens per second
# ARGV[3] = now (unix timestamp, float)
# ARGV[4] = tokens requested by this call
#
# Returns {allowed (0/1), tokens_remaining}. Runs as a single atomic Redis
# operation, so concurrent requests hitting the same key can't race past
# each other between reading and writing the bucket state.
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_per_second = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local ts = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    ts = now
end

local elapsed = now - ts
if elapsed < 0 then elapsed = 0 end
tokens = math.min(capacity, tokens + elapsed * refill_per_second)

local allowed = 0
if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
-- let idle buckets expire instead of accumulating forever
redis.call('EXPIRE', key, math.ceil(capacity / refill_per_second) + 60)

return {allowed, tostring(tokens)}
"""


def _consume_redis(key: str, capacity: int, refill_per_second: float, now: float, requested: float) -> Tuple[bool, float]:
    result = _REDIS_CLIENT.eval(_TOKEN_BUCKET_LUA, 1, key, capacity, refill_per_second, now, requested)
    return bool(int(result[0])), float(result[1])


# ── In-memory fallback — mirrors the Lua logic exactly, just not
# distributed across processes. Guarded by a lock because sync FastAPI
# route dependencies run in Starlette's threadpool, so concurrent requests
# can genuinely race on this dict without one. ────────────────────────────
_local_lock = threading.Lock()
_local_buckets: Dict[str, Tuple[float, float]] = {}  # key -> (tokens, last_ts)


def _consume_local(key: str, capacity: int, refill_per_second: float, now: float, requested: float) -> Tuple[bool, float]:
    with _local_lock:
        tokens, ts = _local_buckets.get(key, (float(capacity), now))
        elapsed = max(0.0, now - ts)
        tokens = min(capacity, tokens + elapsed * refill_per_second)
        allowed = tokens >= requested
        if allowed:
            tokens -= requested
        _local_buckets[key] = (tokens, now)
        return allowed, tokens


def reset_local_buckets() -> None:
    """Test helper — clears in-process bucket state between test cases."""
    with _local_lock:
        _local_buckets.clear()


def _client_ip(request: Request) -> str:
    # request.client.host is correct for direct connections. Once an
    # ingress/proxy sits in front (Epic 3), this needs to read a trusted
    # X-Forwarded-For instead — not done here, since blindly trusting that
    # header today (with no proxy actually validating it) would let a
    # client spoof their way around the per-IP limit entirely.
    if request.client is None:
        return "unknown"
    return request.client.host


def _consume(key: str, capacity: int, refill_per_minute: int, *, requested: float = 1.0) -> None:
    """Raises HTTPException(429, Retry-After=...) if `key`'s bucket is empty."""
    refill_per_second = refill_per_minute / 60.0
    now = time.time()

    if _REDIS_CLIENT is not None:
        allowed, tokens_left = _consume_redis(f"ratelimit:{key}", capacity, refill_per_second, now, requested)
    else:
        allowed, tokens_left = _consume_local(key, capacity, refill_per_second, now, requested)

    if not allowed:
        deficit = requested - tokens_left
        wait_seconds = max(1, math.ceil(deficit / refill_per_second))
        raise HTTPException(
            status_code=429,
            detail="Too many requests — please slow down and try again shortly.",
            headers={"Retry-After": str(wait_seconds)},
        )


def rate_limit_by_ip_and_uid(scope: str, capacity: int, refill_per_minute: int):
    """Dependency factory for routes that already require auth. Depends on
    the same get_current_user used by the route itself — FastAPI caches
    dependency results per request, so this doesn't re-verify the token."""

    async def _dependency(request: Request, current_user: AuthUser = Depends(get_current_user)) -> None:
        _consume(f"{scope}:ip:{_client_ip(request)}", capacity, refill_per_minute)
        _consume(f"{scope}:uid:{current_user.uid}", capacity, refill_per_minute)

    return _dependency


def rate_limit_by_ip(scope: str, capacity: int, refill_per_minute: int):
    """Dependency factory for routes with no auth dependency (/coding/run)."""

    async def _dependency(request: Request) -> None:
        _consume(f"{scope}:ip:{_client_ip(request)}", capacity, refill_per_minute)

    return _dependency

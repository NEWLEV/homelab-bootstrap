import math
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any

from starlette.responses import JSONResponse


CONTROLLED_PATHS = frozenset({
    "/ask",
    "/ask/stream",
    "/index",
    "/search",
})


def non_negative_int_from_environment(
    name: str,
    default: int,
) -> int:
    raw_value = os.environ.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be zero or greater.")
    return value


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class TokenBucketRateLimiter:
    def __init__(
        self,
        requests_per_minute: int,
        burst: int,
        *,
        max_clients: int = 1024,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if requests_per_minute < 0:
            raise ValueError("requests_per_minute must not be negative")
        if burst < 1:
            raise ValueError("burst must be at least one")
        if max_clients < 1:
            raise ValueError("max_clients must be at least one")

        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.max_clients = max_clients
        self._clock = clock
        self._lock = Lock()
        self._buckets: dict[str, _Bucket] = {}

    @property
    def enabled(self) -> bool:
        return self.requests_per_minute > 0

    def allow(self, client_key: str) -> RateLimitDecision:
        if not self.enabled:
            return RateLimitDecision(allowed=True)

        now = self._clock()
        refill_per_second = self.requests_per_minute / 60.0

        with self._lock:
            bucket = self._buckets.get(client_key)
            if bucket is None:
                self._make_room(now)
                bucket = _Bucket(
                    tokens=float(self.burst),
                    updated_at=now,
                )
                self._buckets[client_key] = bucket
            else:
                elapsed = max(0.0, now - bucket.updated_at)
                bucket.tokens = min(
                    float(self.burst),
                    bucket.tokens + elapsed * refill_per_second,
                )
                bucket.updated_at = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return RateLimitDecision(allowed=True)

            retry_after = max(
                1,
                math.ceil((1.0 - bucket.tokens) / refill_per_second),
            )
            return RateLimitDecision(
                allowed=False,
                retry_after=retry_after,
            )

    def _make_room(self, now: float) -> None:
        if len(self._buckets) < self.max_clients:
            return

        stale_after = max(
            60.0,
            (self.burst * 60.0 / self.requests_per_minute) * 2,
        )
        stale_clients = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.updated_at >= stale_after
        ]
        for key in stale_clients:
            self._buckets.pop(key, None)

        if len(self._buckets) >= self.max_clients:
            oldest = min(
                self._buckets,
                key=lambda key: self._buckets[key].updated_at,
            )
            self._buckets.pop(oldest, None)


class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int) -> None:
        if max_concurrent < 0:
            raise ValueError("max_concurrent must not be negative")
        self.max_concurrent = max_concurrent
        self._active = 0
        self._lock = Lock()

    @property
    def enabled(self) -> bool:
        return self.max_concurrent > 0

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    def try_acquire(self) -> bool:
        if not self.enabled:
            return True
        with self._lock:
            if self._active >= self.max_concurrent:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._active < 1:
                raise RuntimeError("resource slot released without acquire")
            self._active -= 1


class RequestBodyTooLarge(Exception):
    pass


class ResourceControlMiddleware:
    def __init__(
        self,
        app: Callable[..., Awaitable[None]],
        *,
        rate_limiter: TokenBucketRateLimiter,
        concurrency_limiter: ConcurrencyLimiter,
        max_request_body_bytes: int,
        controlled_paths: frozenset[str] = CONTROLLED_PATHS,
        record_rejection: Callable[[str], None] | None = None,
    ) -> None:
        if max_request_body_bytes < 0:
            raise ValueError("max_request_body_bytes must not be negative")
        self.app = app
        self.rate_limiter = rate_limiter
        self.concurrency_limiter = concurrency_limiter
        self.max_request_body_bytes = max_request_body_bytes
        self.controlled_paths = controlled_paths
        self.record_rejection = record_rejection or (lambda name: None)

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("path") not in self.controlled_paths
        ):
            await self.app(scope, receive, send)
            return

        if self._declared_body_too_large(scope):
            self.record_rejection("oversized_requests")
            await self._reject(
                scope,
                receive,
                send,
                413,
                "Request body exceeds configured limit.",
            )
            return

        decision = self.rate_limiter.allow(self._client_key(scope))
        if not decision.allowed:
            self.record_rejection("rate_limited_requests")
            await self._reject(
                scope,
                receive,
                send,
                429,
                "Rate limit exceeded.",
                {"Retry-After": str(decision.retry_after)},
            )
            return

        acquired = self.concurrency_limiter.try_acquire()
        if not acquired:
            self.record_rejection("capacity_rejected_requests")
            await self._reject(
                scope,
                receive,
                send,
                503,
                "Local RAG request capacity is exhausted.",
                {"Retry-After": "1"},
            )
            return

        response_started = False
        received_bytes = 0

        async def limited_receive() -> dict[str, Any]:
            nonlocal received_bytes
            message = await receive()
            if (
                self.max_request_body_bytes > 0
                and message.get("type") == "http.request"
            ):
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_request_body_bytes:
                    raise RequestBodyTooLarge
            return message

        async def tracked_send(message: dict[str, Any]) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except RequestBodyTooLarge:
            self.record_rejection("oversized_requests")
            if response_started:
                raise
            await self._reject(
                scope,
                receive,
                send,
                413,
                "Request body exceeds configured limit.",
            )
        finally:
            self.concurrency_limiter.release()

    def _declared_body_too_large(self, scope: dict[str, Any]) -> bool:
        if self.max_request_body_bytes == 0:
            return False
        for name, value in scope.get("headers", []):
            if name.lower() != b"content-length":
                continue
            try:
                return int(value) > self.max_request_body_bytes
            except ValueError:
                return False
        return False

    @staticmethod
    def _client_key(scope: dict[str, Any]) -> str:
        client = scope.get("client")
        if not client:
            return "unknown"
        return str(client[0])

    @staticmethod
    async def _reject(
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
        status_code: int,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        response = JSONResponse(
            status_code=status_code,
            content={"detail": detail},
            headers=headers,
        )
        await response(scope, receive, send)

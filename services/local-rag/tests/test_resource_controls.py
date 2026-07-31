from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import app.main as main
from app.resource_controls import (
    ConcurrencyLimiter,
    ResourceControlMiddleware,
    TokenBucketRateLimiter,
    non_negative_int_from_environment,
)


def build_app(
    *,
    requests_per_minute: int = 0,
    burst: int = 2,
    max_concurrent: int = 0,
    max_body_bytes: int = 0,
    rejections: list[str] | None = None,
) -> tuple[FastAPI, ConcurrencyLimiter]:
    app = FastAPI()
    concurrency_limiter = ConcurrencyLimiter(max_concurrent)
    app.add_middleware(
        ResourceControlMiddleware,
        rate_limiter=TokenBucketRateLimiter(
            requests_per_minute,
            burst,
        ),
        concurrency_limiter=concurrency_limiter,
        max_request_body_bytes=max_body_bytes,
        record_rejection=(
            rejections.append if rejections is not None else None
        ),
    )

    @app.post("/search")
    async def search(request: Request) -> dict[str, bool]:
        await request.body()
        return {"ok": True}

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    return app, concurrency_limiter


def test_token_bucket_refills_deterministically() -> None:
    now = [100.0]
    limiter = TokenBucketRateLimiter(
        requests_per_minute=60,
        burst=2,
        clock=lambda: now[0],
    )

    assert limiter.allow("client").allowed is True
    assert limiter.allow("client").allowed is True
    denied = limiter.allow("client")
    assert denied.allowed is False
    assert denied.retry_after == 1

    now[0] += 1
    assert limiter.allow("client").allowed is True


def test_token_buckets_are_isolated_by_client() -> None:
    limiter = TokenBucketRateLimiter(
        requests_per_minute=1,
        burst=1,
    )

    assert limiter.allow("first").allowed is True
    assert limiter.allow("first").allowed is False
    assert limiter.allow("second").allowed is True


def test_disabled_rate_limiter_always_allows() -> None:
    limiter = TokenBucketRateLimiter(
        requests_per_minute=0,
        burst=1,
    )

    for _ in range(10):
        assert limiter.allow("client").allowed is True


def test_concurrency_limiter_bounds_and_releases_slots() -> None:
    limiter = ConcurrencyLimiter(max_concurrent=2)

    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    assert limiter.active == 2
    assert limiter.try_acquire() is False

    limiter.release()
    assert limiter.active == 1
    assert limiter.try_acquire() is True


def test_middleware_returns_rate_limit_headers() -> None:
    rejections: list[str] = []
    app, _ = build_app(
        requests_per_minute=1,
        burst=1,
        rejections=rejections,
    )
    client = TestClient(app)

    assert client.post("/search").status_code == 200
    response = client.post("/search")

    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded."}
    assert int(response.headers["retry-after"]) >= 1
    assert rejections == ["rate_limited_requests"]
    assert client.get("/health").status_code == 200


def test_middleware_rejects_when_capacity_is_full() -> None:
    rejections: list[str] = []
    app, limiter = build_app(
        max_concurrent=1,
        rejections=rejections,
    )
    client = TestClient(app)
    assert limiter.try_acquire() is True

    try:
        response = client.post("/search")
    finally:
        limiter.release()

    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"
    assert rejections == ["capacity_rejected_requests"]


def test_middleware_rejects_declared_oversized_body() -> None:
    rejections: list[str] = []
    app, _ = build_app(
        max_body_bytes=8,
        rejections=rejections,
    )
    client = TestClient(app)

    response = client.post(
        "/search",
        content=b"123456789",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Request body exceeds configured limit."
    }
    assert rejections == ["oversized_requests"]


def test_middleware_counts_streamed_body_bytes() -> None:
    rejections: list[str] = []
    app, _ = build_app(
        max_body_bytes=8,
        rejections=rejections,
    )
    client = TestClient(app)

    def body_chunks():
        yield b"12345"
        yield b"6789"

    response = client.post(
        "/search",
        content=body_chunks(),
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert rejections == ["oversized_requests"]


def test_environment_integer_validation(monkeypatch) -> None:
    monkeypatch.setenv("CONTROL_VALUE", "12")
    assert non_negative_int_from_environment("CONTROL_VALUE", 0) == 12

    monkeypatch.setenv("CONTROL_VALUE", "-1")
    try:
        non_negative_int_from_environment("CONTROL_VALUE", 0)
    except RuntimeError as exc:
        assert "zero or greater" in str(exc)
    else:
        raise AssertionError("negative values must fail")

    monkeypatch.setenv("CONTROL_VALUE", "invalid")
    try:
        non_negative_int_from_environment("CONTROL_VALUE", 0)
    except RuntimeError as exc:
        assert "integer" in str(exc)
    else:
        raise AssertionError("non-integer values must fail")


def test_public_request_models_bound_user_controlled_text() -> None:
    client = TestClient(main.app)

    assert client.post(
        "/search",
        json={"query": "q" * 2001},
    ).status_code == 422
    assert client.post(
        "/ask",
        json={"question": "q" * 2001},
    ).status_code == 422
    assert client.post(
        "/search",
        json={
            "query": "valid",
            "path": "p" * 1025,
        },
    ).status_code == 422

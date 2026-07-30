import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as main
import app.streaming as streaming
from app.streaming import (
    parse_ollama_line,
    sse_event,
    stream_ollama_answer,
)


client = TestClient(main.app)


def parse_events(body: str) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        event = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((event, data))
    return events


def confident_match() -> dict[str, Any]:
    return {
        "path": "docs.md",
        "line_start": 10,
        "line_end": 20,
        "distance": 0.1,
        "snippet": "Backups run nightly.",
        "vector_score": 0.9,
        "lexical_score": 0.9,
        "combined_score": 0.9,
        "matching_tokens": ["backups", "run"],
        "rank": 1,
        "reranker_used": False,
    }


def test_stream_returns_tokens_and_final_grounded_result(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [confident_match()],
    )

    async def fake_stream(**kwargs):
        yield "Backups run "
        yield "nightly. [docs.md:10-20]"

    monkeypatch.setattr(main, "stream_ollama_answer", fake_stream)

    response = client.post(
        "/ask/stream",
        json={"question": "When do backups run?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/event-stream"
    )
    assert response.headers["cache-control"] == "no-cache"
    events = parse_events(response.text)
    assert events[:2] == [
        ("token", {"text": "Backups run "}),
        ("token", {"text": "nightly. [docs.md:10-20]"}),
    ]
    event, result = events[-1]
    assert event == "result"
    assert result["grounded"] is True
    assert result["confidence"] == 0.92
    assert result["citation_completeness"] == 1.0
    assert result["citations"][0]["path"] == "docs.md"


def test_stream_preserves_ask_filters(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_retrieve(query, limit, **kwargs):
        calls.append(kwargs)
        return [confident_match()]

    async def fake_stream(**kwargs):
        yield "Backups run nightly. [docs.md:10-20]"

    monkeypatch.setattr(main, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(main, "stream_ollama_answer", fake_stream)

    response = client.post(
        "/ask/stream",
        json={
            "question": "When do backups run?",
            "path": "docs.md",
            "path_prefix": "docs",
            "directory": ".",
            "extension": ".md",
        },
    )

    assert response.status_code == 200
    assert calls == [
        {
            "debug": True,
            "path": "docs.md",
            "path_prefix": "docs",
            "directory": ".",
            "extension": ".md",
        }
    ]
    assert parse_events(response.text)[-1][1]["grounded"] is True


def test_stream_low_confidence_skips_generation(monkeypatch) -> None:
    match = confident_match()
    match.update(combined_score=0.05, matching_tokens=[])
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [match],
    )

    async def fail_stream(**kwargs):
        raise AssertionError("generation must be skipped")
        yield

    monkeypatch.setattr(main, "stream_ollama_answer", fail_stream)

    response = client.post(
        "/ask/stream",
        json={
            "question": "What color is the moon base cafeteria?",
            "debug": True,
        },
    )

    events = parse_events(response.text)
    assert len(events) == 1
    event, result = events[0]
    assert event == "result"
    assert result["grounded"] is False
    assert result["confidence"] < 0.45
    assert "below_confidence_threshold" in result[
        "confidence_reasons"
    ]


def test_stream_invalid_citation_finishes_refused(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [confident_match()],
    )

    async def fake_stream(**kwargs):
        yield "Backups run nightly without a citation."

    monkeypatch.setattr(main, "stream_ollama_answer", fake_stream)

    response = client.post(
        "/ask/stream",
        json={
            "question": "When do backups run?",
            "debug": True,
        },
    )

    events = parse_events(response.text)
    assert events[0][0] == "token"
    event, result = events[-1]
    assert event == "result"
    assert result["grounded"] is False
    assert result["citation_completeness"] == 0.0
    assert "missing_citations" in result["confidence_reasons"]


def test_stream_generation_error_emits_error_event(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [confident_match()],
    )

    async def fail_stream(**kwargs):
        raise RuntimeError("generation unavailable")
        yield

    monkeypatch.setattr(main, "stream_ollama_answer", fail_stream)

    response = client.post(
        "/ask/stream",
        json={"question": "When do backups run?"},
    )

    assert parse_events(response.text) == [
        ("error", {"detail": "generation unavailable"})
    ]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ('{"response":"hello","done":false}', ("hello", False)),
        ('{"response":"","done":true}', ("", True)),
    ],
)
def test_parse_ollama_line(line: str, expected) -> None:
    assert parse_ollama_line(line) == expected


def test_parse_ollama_error() -> None:
    with pytest.raises(RuntimeError, match="model not found"):
        parse_ollama_line('{"error":"model not found"}')


def test_sse_event_json_encodes_newlines() -> None:
    encoded = sse_event("token", {"text": "one\ntwo"})

    assert encoded == 'event: token\ndata: {"text":"one\\ntwo"}\n\n'


def test_disconnected_client_skips_ollama_stream() -> None:
    async def disconnected() -> bool:
        return True

    async def collect() -> list[str]:
        return [
            token
            async for token in stream_ollama_answer(
                ollama_url="http://unused",
                model="unused",
                prompt="unused",
                is_disconnected=disconnected,
            )
        ]

    assert asyncio.run(collect()) == []


def test_truncated_ollama_stream_is_rejected(monkeypatch) -> None:
    class FakeResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def raise_for_status(self) -> None:
            return None

        async def aiter_lines(self):
            yield '{"response":"partial","done":false}'

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(
        streaming.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(),
    )

    async def connected() -> bool:
        return False

    async def collect() -> list[str]:
        return [
            token
            async for token in stream_ollama_answer(
                ollama_url="http://ollama",
                model="model",
                prompt="prompt",
                is_disconnected=connected,
            )
        ]

    with pytest.raises(RuntimeError, match="before completion"):
        asyncio.run(collect())


def test_stream_openapi_marks_tokens_as_provisional() -> None:
    description = main.app.openapi()["paths"]["/ask/stream"]["post"][
        "description"
    ]

    assert "provisional tokens" in description
    assert "final result" in description


def test_stream_limit_and_blank_question_validation() -> None:
    assert client.post(
        "/ask/stream",
        json={"question": "test", "limit": 11},
    ).status_code == 422
    assert client.post(
        "/ask/stream",
        json={"question": "   "},
    ).status_code == 422

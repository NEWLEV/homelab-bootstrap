import json
import urllib.request
from typing import Any

from evaluation.run import post_search


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "results": [
                    {"path": "compose/ai/local-rag.yml"},
                ]
            }
        ).encode("utf-8")


def test_post_search_sends_authorization_header(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(
        request: urllib.request.Request,
        timeout: int,
    ) -> FakeResponse:
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    paths = post_search(
        "http://api:8080",
        "OLLAMA_URL",
        5,
        "Bearer token",
    )

    assert paths == ["compose/ai/local-rag.yml"]
    assert captured == {
        "authorization": "Bearer token",
        "timeout": 180,
    }


def test_post_search_omits_authorization_when_disabled(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(
        request: urllib.request.Request,
        timeout: int,
    ) -> FakeResponse:
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    post_search("http://api:8080", "OLLAMA_URL", 5)

    assert captured["authorization"] is None

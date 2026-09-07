from fastapi.testclient import TestClient

from app.main import app, build_grounded_prompt

client = TestClient(app)


def test_ask_returns_insufficient_context(monkeypatch):
    monkeypatch.setattr(
        "app.main.retrieve_chunks",
        lambda query, limit, **kwargs: [
            {
                "path": "foo.txt",
                "line_start": 1,
                "line_end": 10,
                "distance": 0.2,
                "snippet": "backup service",
            }
        ],
    )

    monkeypatch.setattr(
        "app.main.generate_answer",
        lambda prompt, *, model: (
            "The encrypted backups are not explicitly configured "
            "and might be handled elsewhere."
        ),
    )

    response = client.post(
        "/ask",
        json={
            "question": "How are encrypted backups configured?"
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["grounded"] is False
    assert body["citations"] == []
    assert (
        body["answer"]
        == "The indexed repository does not contain enough information to answer this question."
    )


def test_ask_returns_grounded_answer(monkeypatch):
    monkeypatch.setattr(
        "app.main.retrieve_chunks",
        lambda query, limit, **kwargs: [
            {
                "path": "docs.md",
                "line_start": 10,
                "line_end": 20,
                "distance": 0.1,
                "snippet": "Backups run nightly.",
                "combined_score": 0.9,
                "matching_tokens": ["backups", "run"],
                "reranker_used": False,
            }
        ],
    )

    monkeypatch.setattr(
        "app.main.generate_answer",
        lambda prompt, *, model: (
            "Backups run nightly. "
            "[docs.md:10-20]"
        ),
    )

    response = client.post(
        "/ask",
        json={
            "question": "When do backups run?"
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["grounded"] is True
    assert len(body["citations"]) == 1
    assert body["citations"][0]["path"] == "docs.md"
    assert body["confidence"] == 0.92
    assert body["citation_completeness"] == 1.0


def test_grounded_prompt_requires_complete_verbatim_citations() -> None:
    prompt = build_grounded_prompt(
        "When do backups run?",
        [
            {
                "path": "docs.md",
                "line_start": 10,
                "line_end": 20,
                "snippet": "Backups run nightly.",
            }
        ],
    )

    assert "SOURCE [docs.md:10-20]" in prompt
    assert "copy each citation verbatim" in prompt
    assert "complete path and full line range" in prompt
    assert (
        "never shorten [path:line_start-line_end]"
        in prompt
    )
    assert "each citation in its own brackets" in prompt
    assert "never combine sources in one bracket" in prompt

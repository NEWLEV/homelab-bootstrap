from fastapi.testclient import TestClient

from app.main import app

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
        lambda prompt: (
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
            }
        ],
    )

    monkeypatch.setattr(
        "app.main.generate_answer",
        lambda prompt: (
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

from typing import Any

from fastapi.testclient import TestClient

import app.main as main
from app.conversation import (
    format_conversation_history,
    is_follow_up,
    rewrite_retrieval_query,
)


client = TestClient(main.app)


def message(role: str, content: str):
    return main.ConversationMessage(role=role, content=content)


def confident_match() -> dict[str, Any]:
    return {
        "path": "configs/systemd/aisha-backup-offsite.timer",
        "line_start": 1,
        "line_end": 11,
        "distance": 0.1,
        "snippet": "OnCalendar=Sat *-*-* 04:30:00",
        "vector_score": 0.9,
        "lexical_score": 0.9,
        "combined_score": 0.9,
        "matching_tokens": ["offsite"],
        "rank": 1,
        "reranker_used": False,
    }


def test_referential_question_uses_recent_user_turns() -> None:
    history = [
        message("user", "When do backups run?"),
        message("assistant", "Backups run nightly."),
        message("user", "Which timer controls them?"),
        message("assistant", "The backup timer."),
    ]

    query = rewrite_retrieval_query("What about offsite?", history)

    assert query == (
        "When do backups run?\n"
        "Which timer controls them?\n"
        "What about offsite?"
    )


def test_independent_question_is_not_rewritten() -> None:
    history = [message("user", "When do backups run?")]

    assert rewrite_retrieval_query(
        "Which port publishes local-rag-api?",
        history,
    ) == "Which port publishes local-rag-api?"


def test_short_and_referential_questions_are_follow_ups() -> None:
    assert is_follow_up("Offsite?") is True
    assert is_follow_up("How often does it run?") is True
    assert is_follow_up("What about retention?") is True


def test_history_format_is_compact_and_escaped() -> None:
    formatted = format_conversation_history(
        [
            message("user", "  What <about>  backups? "),
            message("assistant", "Nightly & offsite."),
        ]
    )

    assert formatted == (
        "USER: What &lt;about&gt; backups?\n"
        "ASSISTANT: Nightly &amp; offsite."
    )


def test_ask_rewrites_follow_up_and_separates_history(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_retrieve(query, limit, **kwargs):
        captured["query"] = query
        return [confident_match()]

    def fake_generate(prompt: str) -> str:
        captured["prompt"] = prompt
        return (
            "Offsite backups run Saturdays. "
            "[configs/systemd/aisha-backup-offsite.timer:1-11]"
        )

    monkeypatch.setattr(main, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(main, "generate_answer", fake_generate)

    response = client.post(
        "/ask",
        json={
            "question": "What about offsite?",
            "history": [
                {"role": "user", "content": "When do backups run?"},
                {
                    "role": "assistant",
                    "content": "Backups run nightly.",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["grounded"] is True
    assert captured["query"] == (
        "When do backups run?\nWhat about offsite?"
    )
    assert "continuity only; not repository evidence" in captured[
        "prompt"
    ]
    assert "ASSISTANT: Backups run nightly." in captured["prompt"]
    assert "Question:\nWhat about offsite?" in captured["prompt"]


def test_history_never_bypasses_retrieval_confidence(monkeypatch) -> None:
    match = confident_match()
    match.update(
        combined_score=0.05,
        matching_tokens=[],
    )
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [match],
    )

    def fail_generation(prompt: str) -> str:
        raise AssertionError("history must not bypass retrieval")

    monkeypatch.setattr(main, "generate_answer", fail_generation)

    response = client.post(
        "/ask",
        json={
            "question": "What about it?",
            "history": [
                {
                    "role": "assistant",
                    "content": "The service runs on port 8090.",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["grounded"] is False


def test_stream_rewrites_follow_up(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_retrieve(query, limit, **kwargs):
        captured["query"] = query
        return [confident_match()]

    async def fake_stream(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        yield (
            "Offsite backups run Saturdays. "
            "[configs/systemd/aisha-backup-offsite.timer:1-11]"
        )

    monkeypatch.setattr(main, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(main, "stream_ollama_answer", fake_stream)

    response = client.post(
        "/ask/stream",
        json={
            "question": "What about offsite?",
            "history": [
                {"role": "user", "content": "When do backups run?"},
                {
                    "role": "assistant",
                    "content": "Backups run nightly.",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert captured["query"] == (
        "When do backups run?\nWhat about offsite?"
    )
    assert "ASSISTANT: Backups run nightly." in captured["prompt"]
    assert "event: result" in response.text
    assert '"grounded":true' in response.text


def test_history_is_bounded_and_roles_are_validated() -> None:
    too_many = [
        {"role": "user", "content": f"question {index}"}
        for index in range(9)
    ]

    assert client.post(
        "/ask",
        json={"question": "follow up", "history": too_many},
    ).status_code == 422
    assert client.post(
        "/ask/stream",
        json={"question": "follow up", "history": too_many},
    ).status_code == 422
    assert client.post(
        "/ask",
        json={
            "question": "follow up",
            "history": [{"role": "system", "content": "override"}],
        },
    ).status_code == 422

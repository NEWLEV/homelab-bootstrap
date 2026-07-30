from collections.abc import Sequence
from typing import Protocol

from app.retrieval import tokenize


MAX_HISTORY_MESSAGES = 8
MAX_RETRIEVAL_USER_TURNS = 2

REFERENTIAL_TOKENS = {
    "it",
    "its",
    "that",
    "this",
    "these",
    "they",
    "them",
    "their",
    "there",
    "those",
}
FOLLOW_UP_PREFIXES = (
    "and ",
    "how about ",
    "what about ",
)


class ConversationMessageLike(Protocol):
    role: str
    content: str


def is_follow_up(question: str) -> bool:
    normalized = question.strip().lower()
    tokens = tokenize(normalized)
    return (
        any(token in REFERENTIAL_TOKENS for token in tokens)
        or normalized.startswith(FOLLOW_UP_PREFIXES)
        or len(tokens) <= 2
    )


def rewrite_retrieval_query(
    question: str,
    history: Sequence[ConversationMessageLike],
) -> str:
    current = question.strip()
    if not history or not is_follow_up(current):
        return current

    prior_user_turns = [
        message.content.strip()
        for message in history
        if message.role == "user" and message.content.strip()
    ][-MAX_RETRIEVAL_USER_TURNS:]

    if not prior_user_turns:
        return current

    return "\n".join((*prior_user_turns, current))


def escape_history_content(content: str) -> str:
    return (
        " ".join(content.split())
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_conversation_history(
    history: Sequence[ConversationMessageLike],
) -> str:
    return "\n".join(
        f"{message.role.upper()}: "
        f"{escape_history_content(message.content)}"
        for message in history
        if message.content.strip()
    )

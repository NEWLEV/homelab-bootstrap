from pathlib import Path

import pytest

from app.auth import BearerTokenAuth, is_public_path


TOKEN = "a" * 64


def test_disabled_auth_allows_requests(monkeypatch) -> None:
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("API_AUTH_TOKEN_FILE", raising=False)

    auth = BearerTokenAuth.from_environment()

    assert auth.enabled is False
    assert auth.authorize(None) is True
    assert auth.authorization_header is None


def test_direct_token_accepts_only_matching_bearer(monkeypatch) -> None:
    monkeypatch.setenv("API_AUTH_TOKEN", TOKEN)
    monkeypatch.delenv("API_AUTH_TOKEN_FILE", raising=False)

    auth = BearerTokenAuth.from_environment()

    assert auth.enabled is True
    assert auth.authorize(f"Bearer {TOKEN}") is True
    assert auth.authorization_header == f"Bearer {TOKEN}"
    assert TOKEN not in repr(auth)
    assert auth.authorize(f"bearer {TOKEN}") is True
    assert auth.authorize(None) is False
    assert auth.authorize("Basic credentials") is False
    assert auth.authorize("Bearer wrong") is False
    assert auth.authorize(f"Bearer {TOKEN} ") is False


def test_token_file_is_loaded(monkeypatch, tmp_path: Path) -> None:
    token_file = tmp_path / "api-token"
    token_file.write_text(f"{TOKEN}\n", encoding="utf-8")
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("API_AUTH_TOKEN_FILE", str(token_file))

    auth = BearerTokenAuth.from_environment()

    assert auth.authorize(f"Bearer {TOKEN}") is True


def test_missing_token_file_fails_closed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing-token"
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("API_AUTH_TOKEN_FILE", str(missing))

    with pytest.raises(RuntimeError, match="Unable to read"):
        BearerTokenAuth.from_environment()


@pytest.mark.parametrize(
    "token",
    [
        "",
        "short-token",
        "a" * 31,
        f"{'a' * 32} contains-space",
    ],
)
def test_invalid_token_is_rejected(monkeypatch, token: str) -> None:
    monkeypatch.setenv("API_AUTH_TOKEN", token)
    monkeypatch.delenv("API_AUTH_TOKEN_FILE", raising=False)

    with pytest.raises(RuntimeError):
        BearerTokenAuth.from_environment()


def test_conflicting_token_sources_are_rejected(
    monkeypatch,
    tmp_path: Path,
) -> None:
    token_file = tmp_path / "api-token"
    token_file.write_text(TOKEN, encoding="utf-8")
    monkeypatch.setenv("API_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("API_AUTH_TOKEN_FILE", str(token_file))

    with pytest.raises(RuntimeError, match="only one"):
        BearerTokenAuth.from_environment()


def test_only_health_is_public() -> None:
    assert is_public_path("/health") is True
    assert is_public_path("/metrics") is False
    assert is_public_path("/docs") is False
    assert is_public_path("/openapi.json") is False
    assert is_public_path("/search") is False

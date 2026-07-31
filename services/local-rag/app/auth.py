import os
from dataclasses import dataclass, field
from hmac import compare_digest
from pathlib import Path


PUBLIC_PATHS = frozenset({"/health"})


@dataclass(frozen=True)
class BearerTokenAuth:
    token: str | None = field(default=None, repr=False)

    @property
    def enabled(self) -> bool:
        return self.token is not None

    @property
    def authorization_header(self) -> str | None:
        if not self.enabled:
            return None
        return f"Bearer {self.token}"

    def authorize(self, authorization: str | None) -> bool:
        if not self.enabled:
            return True
        if not authorization:
            return False

        scheme, separator, credentials = authorization.partition(" ")
        if separator != " " or scheme.lower() != "bearer":
            return False
        if not credentials or credentials != credentials.strip():
            return False

        return compare_digest(credentials, self.token or "")

    @classmethod
    def from_environment(cls) -> "BearerTokenAuth":
        direct_token = os.environ.get("API_AUTH_TOKEN")
        token_file = os.environ.get("API_AUTH_TOKEN_FILE")

        if direct_token is not None and token_file:
            raise RuntimeError(
                "Configure only one of API_AUTH_TOKEN or "
                "API_AUTH_TOKEN_FILE."
            )

        if direct_token is not None:
            return cls(_validate_token(direct_token, "API_AUTH_TOKEN"))

        if token_file:
            path = Path(token_file)
            try:
                value = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(
                    f"Unable to read API authentication token file: {path}"
                ) from exc
            return cls(_validate_token(value, "API_AUTH_TOKEN_FILE"))

        return cls()


def _validate_token(value: str, source: str) -> str:
    token = value.strip()
    if not token:
        raise RuntimeError(f"{source} must not be empty.")
    if any(character.isspace() for character in token):
        raise RuntimeError(f"{source} must not contain whitespace.")
    if len(token) < 32:
        raise RuntimeError(
            f"{source} must contain at least 32 characters."
        )
    return token


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS

from __future__ import annotations

import os

import app.__main__ as app_launcher


def test_build_parser_defaults_to_dashboard_bindings() -> None:
    original_host = os.environ.pop("AISHA_HOST", None)
    original_port = os.environ.pop("AISHA_PORT", None)
    try:
        parser = app_launcher.build_parser()
        args = parser.parse_args([])

        assert args.host == "127.0.0.1"
        assert args.port == 8000
        assert args.reload is False
    finally:
        if original_host is not None:
            os.environ["AISHA_HOST"] = original_host
        if original_port is not None:
            os.environ["AISHA_PORT"] = original_port


def test_build_parser_honors_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("AISHA_HOST", "0.0.0.0")
    monkeypatch.setenv("AISHA_PORT", "8088")

    parser = app_launcher.build_parser()
    args = parser.parse_args([])

    assert args.host == "0.0.0.0"
    assert args.port == 8088

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx


DisconnectCheck = Callable[[], Awaitable[bool]]


def sse_event(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event}\ndata: {data}\n\n"


def parse_ollama_line(line: str) -> tuple[str, bool]:
    payload = json.loads(line)
    error = payload.get("error")
    if error:
        raise RuntimeError(f"Ollama generation failed: {error}")
    return str(payload.get("response", "")), bool(
        payload.get("done", False)
    )


async def stream_ollama_answer(
    *,
    ollama_url: str,
    model: str,
    prompt: str,
    is_disconnected: DisconnectCheck,
    timeout: float = 300.0,
) -> AsyncIterator[str]:
    if await is_disconnected():
        return

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0,
                },
            },
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if await is_disconnected():
                    return
                if not line:
                    continue

                token, done = parse_ollama_line(line)
                if token:
                    yield token
                if done:
                    return

            raise RuntimeError(
                "Ollama stream ended before completion."
            )

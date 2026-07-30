import copy
import json
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IndexJobAlreadyRunning(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "last_run_status": None,
        "started_at": None,
        "finished_at": None,
        "last_success_at": None,
        "last_error": None,
        "last_result": None,
    }


class IndexJobManager:
    def __init__(
        self,
        status_path: Path,
        *,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.status_path = status_path
        self.clock = clock
        self._lock = threading.Lock()
        self._state = self._load()

        if self._state["status"] == "running":
            self._state.update(
                status="failed",
                last_run_status="interrupted",
                finished_at=self.clock(),
                last_error=(
                    "Index job was interrupted by a service restart."
                ),
            )
            self._persist()

    def _load(self) -> dict[str, Any]:
        if not self.status_path.exists():
            return default_state()

        try:
            loaded = json.loads(
                self.status_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            state = default_state()
            state.update(
                status="failed",
                last_run_status="status_read_failed",
                finished_at=self.clock(),
                last_error=(
                    "Index status could not be loaded: "
                    f"{type(exc).__name__}"
                ),
            )
            return state

        if not isinstance(loaded, dict):
            state = default_state()
            state.update(
                status="failed",
                last_run_status="status_read_failed",
                finished_at=self.clock(),
                last_error="Index status file is not a JSON object.",
            )
            return state

        return {**default_state(), **loaded}

    def _persist(self) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.status_path.with_name(
            f".{self.status_path.name}.tmp"
        )
        temporary_path.write_text(
            json.dumps(self._state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.status_path)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def begin(self) -> dict[str, Any]:
        with self._lock:
            if self._state["status"] == "running":
                raise IndexJobAlreadyRunning(
                    "A repository indexing job is already running."
                )

            self._state.update(
                status="running",
                started_at=self.clock(),
                finished_at=None,
                last_error=None,
            )
            self._persist()
            return copy.deepcopy(self._state)

    def succeed(self, result: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._state["status"] != "running":
                raise RuntimeError("No indexing job is running.")

            finished_at = self.clock()
            self._state.update(
                status="idle",
                last_run_status="succeeded",
                finished_at=finished_at,
                last_success_at=finished_at,
                last_error=None,
                last_result=copy.deepcopy(result),
            )
            self._persist()
            return copy.deepcopy(self._state)

    def fail(self, error: BaseException) -> dict[str, Any]:
        with self._lock:
            if self._state["status"] != "running":
                raise RuntimeError("No indexing job is running.")

            self._state.update(
                status="failed",
                last_run_status="failed",
                finished_at=self.clock(),
                last_error=f"{type(error).__name__}: {error}",
            )
            self._persist()
            return copy.deepcopy(self._state)

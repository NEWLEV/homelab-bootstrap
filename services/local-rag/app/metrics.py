from collections import defaultdict
from contextlib import contextmanager
from threading import Lock
from time import monotonic, perf_counter
from typing import Iterator


COUNTER_NAMES = (
    "search_requests",
    "ask_requests",
    "stream_requests",
    "index_requests",
    "grounded_answers",
    "refused_answers",
    "dependency_failures",
    "rate_limited_requests",
    "capacity_rejected_requests",
    "oversized_requests",
)
LATENCY_NAMES = (
    "embedding",
    "retrieval",
    "generation",
    "indexing",
)
DEPENDENCY_NAMES = (
    "embedding",
    "generation",
    "streaming_generation",
    "indexing",
)


class MetricRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = monotonic()
        self._counters: dict[str, int] = defaultdict(int)
        self._dependency_failures: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, dict[str, float | int]] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def dependency_failure(self, component: str) -> None:
        with self._lock:
            self._counters["dependency_failures"] += 1
            self._dependency_failures[component] += 1

    def observe(self, name: str, seconds: float) -> None:
        milliseconds = max(0.0, seconds * 1000)
        with self._lock:
            timing = self._latencies.setdefault(
                name,
                {
                    "count": 0,
                    "total_ms": 0.0,
                    "last_ms": 0.0,
                    "max_ms": 0.0,
                },
            )
            timing["count"] = int(timing["count"]) + 1
            timing["total_ms"] = float(timing["total_ms"]) + milliseconds
            timing["last_ms"] = milliseconds
            timing["max_ms"] = max(
                float(timing["max_ms"]),
                milliseconds,
            )

    @contextmanager
    def time(self, name: str) -> Iterator[None]:
        started = perf_counter()
        try:
            yield
        finally:
            self.observe(name, perf_counter() - started)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            counters = {
                name: self._counters[name]
                for name in COUNTER_NAMES
            }
            failures = {
                name: self._dependency_failures[name]
                for name in DEPENDENCY_NAMES
            }
            latencies: dict[str, dict[str, float | int]] = {}
            for name in LATENCY_NAMES:
                timing = self._latencies.get(name)
                if timing is None:
                    latencies[name] = {
                        "count": 0,
                        "total_ms": 0.0,
                        "average_ms": 0.0,
                        "last_ms": 0.0,
                        "max_ms": 0.0,
                    }
                    continue
                count = int(timing["count"])
                total = float(timing["total_ms"])
                latencies[name] = {
                    "count": count,
                    "total_ms": round(total, 3),
                    "average_ms": round(total / count, 3),
                    "last_ms": round(float(timing["last_ms"]), 3),
                    "max_ms": round(float(timing["max_ms"]), 3),
                }

            return {
                "uptime_seconds": round(monotonic() - self._started_at, 3),
                "counters": counters,
                "dependency_failures": failures,
                "latencies_ms": latencies,
            }

    def reset(self) -> None:
        with self._lock:
            self._started_at = monotonic()
            self._counters.clear()
            self._dependency_failures.clear()
            self._latencies.clear()


metrics = MetricRegistry()

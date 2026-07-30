import threading
from typing import Any


DIAGNOSTIC_FIELDS = {
    "vector_score",
    "lexical_score",
    "combined_score",
    "matching_tokens",
    "rank",
    "hybrid_rank",
    "reranker_score",
    "reranker_used",
    "reranker_error",
}


class LocalReranker:
    def __init__(
        self,
        *,
        enabled: bool,
        model_name: str,
        cache_dir: str,
        threads: int,
    ) -> None:
        self.enabled = enabled
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.threads = threads
        self._encoder: Any = None
        self._lock = threading.Lock()

    def _get_encoder(self) -> Any:
        if self._encoder is not None:
            return self._encoder

        with self._lock:
            if self._encoder is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                self._encoder = TextCrossEncoder(
                    model_name=self.model_name,
                    cache_dir=self.cache_dir,
                    threads=self.threads,
                    providers=["CPUExecutionProvider"],
                )

        return self._encoder

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        limit: int,
        *,
        debug: bool,
    ) -> list[dict[str, Any]]:
        if not candidates:
            return []

        if not self.enabled:
            return finalize_results(
                fallback_results(candidates, limit, error=None),
                debug,
            )

        try:
            documents = [
                f"{candidate.get('path', '')}\n{candidate.get('snippet', '')}"
                for candidate in candidates
            ]
            scores = list(
                self._get_encoder().rerank(
                    query,
                    documents,
                    batch_size=min(16, len(documents)),
                )
            )
            ranked = apply_scores(candidates, scores, limit)
        except Exception as exc:
            ranked = fallback_results(
                candidates,
                limit,
                error=f"{type(exc).__name__}: {exc}",
            )

        return finalize_results(ranked, debug)


def apply_scores(
    candidates: list[dict[str, Any]],
    scores: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    if len(scores) != len(candidates):
        raise ValueError("Reranker returned an unexpected number of scores.")

    ranked = [
        {
            **candidate,
            "hybrid_rank": candidate.get("rank", index + 1),
            "reranker_score": float(score),
            "reranker_used": True,
            "reranker_error": None,
            "_original_order": index,
        }
        for index, (candidate, score) in enumerate(
            zip(candidates, scores, strict=True)
        )
    ]
    ranked.sort(
        key=lambda candidate: (
            -candidate["reranker_score"],
            candidate["_original_order"],
        )
    )

    results: list[dict[str, Any]] = []
    for rank, candidate in enumerate(ranked[:limit], start=1):
        result = {
            key: value
            for key, value in candidate.items()
            if key != "_original_order"
        }
        result["rank"] = rank
        results.append(result)

    return results


def fallback_results(
    candidates: list[dict[str, Any]],
    limit: int,
    *,
    error: str | None,
) -> list[dict[str, Any]]:
    return [
        {
            **candidate,
            "hybrid_rank": candidate.get("rank", rank),
            "rank": rank,
            "reranker_score": None,
            "reranker_used": False,
            "reranker_error": error,
        }
        for rank, candidate in enumerate(candidates[:limit], start=1)
    ]


def finalize_results(
    candidates: list[dict[str, Any]],
    debug: bool,
) -> list[dict[str, Any]]:
    if debug:
        return candidates

    return [
        {
            key: value
            for key, value in candidate.items()
            if key not in DIAGNOSTIC_FIELDS
        }
        for candidate in candidates
    ]

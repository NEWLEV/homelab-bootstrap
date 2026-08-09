from __future__ import annotations

import re
from collections import Counter
from typing import Any

PATH_SCORE_BONUSES: tuple[tuple[str, float], ...] = (
    ('docs/', 0.45),
    ('configs/', 0.4),
    ('homelab-bootstrap/services/', 0.25),
    ('services/', 0.15),
)

PATH_SCORE_PENALTIES: tuple[tuple[str, float], ...] = (
    ('tests/', -0.35),
    ('bootstrap/', -0.2),
    ('/.venv/', -1.0),
    ('/site-packages/', -1.0),
)

PATH_NAME_PENALTIES: tuple[tuple[str, float], ...] = (
    ('request.json', -0.9),
    ('diagnose-', -0.75),
    ('.prep-', -0.5),
    ('bundle-test', -0.4),
)


def candidate_pool_size(limit: int, collection_size: int) -> int:
    if limit <= 0 or collection_size <= 0:
        return 0
    return min(collection_size, max(limit, limit * 4))



def path_score_adjustment(path: str) -> float:
    normalized = f"/{str(path).replace('\\', '/').lower().strip('/')}"
    score = 0.0
    for prefix, bonus in PATH_SCORE_BONUSES:
        if normalized.startswith(f"/{prefix}"):
            score += bonus
    for fragment, penalty in PATH_SCORE_PENALTIES:
        if fragment in normalized:
            score += penalty
    for fragment, penalty in PATH_NAME_PENALTIES:
        if fragment in normalized:
            score += penalty
    return score



def rerank_candidates(query: str, matches: list[dict[str, Any]], limit: int, debug: bool = False) -> list[dict[str, Any]]:
    query_tokens = set(re.findall(r"[A-Za-z0-9]+", query.lower()))
    ranked: list[dict[str, Any]] = []
    for rank, match in enumerate(matches, start=1):
        snippet_tokens = re.findall(r"[A-Za-z0-9]+", f"{match.get('path', '')} {match.get('snippet', '')}".lower())
        token_counts = Counter(snippet_tokens)
        matching = sorted(query_tokens & set(snippet_tokens))
        coverage = len(matching) / max(1, len(query_tokens))
        frequency = sum(token_counts[token] for token in matching) / max(1, len(query_tokens))
        lexical_score = float(coverage + frequency)
        vector_score = max(0.0, 1.0 - float(match.get('distance', 0.0)))
        path_bias = path_score_adjustment(str(match.get('path', '')))
        combined_score = (vector_score * 0.75) + (lexical_score * 1.25) + path_bias
        item = dict(match)
        item.update({
            'vector_score': vector_score,
            'lexical_score': lexical_score,
            'combined_score': combined_score,
            'path_bias': path_bias,
            'matching_tokens': matching,
            'rank': rank,
            'hybrid_rank': rank,
            'reranker_used': False,
            'reranker_score': None,
            'reranker_error': None,
        })
        ranked.append(item)
    ranked.sort(key=lambda item: (item['combined_score'], item['vector_score']), reverse=True)
    return ranked[:limit]
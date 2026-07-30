import os
import re
from pathlib import Path
from typing import Any

import chromadb
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.reranker import LocalReranker
from app.retrieval import candidate_pool_size, rerank_candidates


APP_VERSION = "0.7.0"


app = FastAPI(
    title="Aisha Local RAG",
    version=APP_VERSION,
)


CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", "/data/chroma"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "nomic-embed-text",
)
GENERATION_MODEL = os.environ.get(
    "GENERATION_MODEL",
    "llama3.2:3b",
)

RERANKER_ENABLED = os.environ.get(
    "RERANKER_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes"}
RERANKER_MODEL = os.environ.get(
    "RERANKER_MODEL",
    "Xenova/ms-marco-MiniLM-L-6-v2",
)
RERANKER_CACHE_DIR = os.environ.get(
    "RERANKER_CACHE_DIR",
    "/models/fastembed",
)
RERANKER_THREADS = max(1, int(os.environ.get("RERANKER_THREADS", "2")))
reranker = LocalReranker(
    enabled=RERANKER_ENABLED,
    model_name=RERANKER_MODEL,
    cache_dir=RERANKER_CACHE_DIR,
    threads=RERANKER_THREADS,
)


INSUFFICIENT_CONTEXT_MESSAGE = (
    "The indexed repository does not contain enough information "
    "to answer this question."
)


CHROMA_PATH.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_PATH),
)

collection = chroma_client.get_or_create_collection(
    name="homelab_bootstrap",
    metadata={
        "description": "Aisha homelab repository",
    },
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    debug: bool = False
    path: str | None = None
    path_prefix: str | None = None
    directory: str | None = None
    extension: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)
    path: str | None = None
    debug: bool = False
    path_prefix: str | None = None
    directory: str | None = None
    extension: str | None = None


class Citation(BaseModel):
    path: str
    line_start: int
    line_end: int
    distance: float


class RetrievalDiagnostic(BaseModel):
    path: str
    line_start: int
    line_end: int
    distance: float
    vector_score: float
    lexical_score: float
    combined_score: float
    matching_tokens: list[str]
    rank: int
    hybrid_rank: int | None = None
    reranker_score: float | None = None
    reranker_used: bool = False
    reranker_error: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    grounded: bool
    citations: list[Citation]
    retrieval_debug: list[RetrievalDiagnostic] | None = None


def embed_text(text: str) -> list[float]:
    response = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": EMBEDDING_MODEL,
            "input": text,
        },
        timeout=120,
    )

    response.raise_for_status()

    embeddings = response.json().get("embeddings", [])

    if not embeddings:
        raise RuntimeError(
            "Ollama returned no embedding.",
        )

    return embeddings[0]


def build_metadata_filter(
    *,
    path: str | None = None,
    path_prefix: str | None = None,
    directory: str | None = None,
    extension: str | None = None,
) -> dict[str, Any] | None:
    conditions: list[dict[str, Any]] = []

    if path:
        conditions.append(
            {
                "path": {
                    "$eq": path,
                },
            }
        )


    if directory:
        conditions.append(
            {
                "directory": {
                    "$eq": directory,
                },
            }
        )

    if extension:
        conditions.append(
            {
                "extension": {
                    "$eq": extension,
                },
            }
        )

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {
        "$and": conditions,
    }


def retrieve_chunks(
    query: str,
    limit: int,
    debug: bool = False,
    path: str | None = None,
    path_prefix: str | None = None,
    directory: str | None = None,
    extension: str | None = None,
) -> list[dict[str, Any]]:
    pool_size = candidate_pool_size(
        limit,
        collection.count(),
    )

    if pool_size == 0:
        return []

    query_embedding = embed_text(query)

    where = build_metadata_filter(
        path=path,
        path_prefix=path_prefix,
        directory=directory,
        extension=extension,
    )

    query_arguments: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": pool_size,
        "include": [
            "documents",
            "metadatas",
            "distances",
        ],
    }

    if where is not None:
        query_arguments["where"] = where

    results = collection.query(
        **query_arguments,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    matches: list[dict[str, Any]] = []
    ids = results.get("ids", [[]])[0]

    for record_id, document, metadata, distance in zip(
        ids,
        documents,
        metadatas,
        distances,
        strict=False,
    ):
        metadata = metadata or {}

        matches.append(
            {
                "id": record_id,
                "path": str(
                    metadata.get("path", "unknown")
                ),
                "directory": str(
                    metadata.get("directory", "")
                ),
                "filename": str(
                    metadata.get("filename", "")
                ),
                "extension": str(
                    metadata.get("extension", "")
                ),
                "line_start": int(
                    metadata.get("line_start", 0)
                ),
                "line_end": int(
                    metadata.get("line_end", 0)
                ),
                "distance": float(distance),
                "snippet": document or "",
            }
        )

    if path_prefix:
        matches = [
            match
            for match in matches
            if match["path"].startswith(path_prefix)
        ]

    hybrid_candidates = rerank_candidates(
        query,
        matches,
        len(matches),
        debug=True,
    )
    return reranker.rerank(
        query, hybrid_candidates, limit, debug=debug
    )


def build_grounded_prompt(
    question: str,
    matches: list[dict[str, Any]],
) -> str:
    context_sections: list[str] = []

    for match in matches:
        source_label = (
            f"{match['path']}:"
            f"{match['line_start']}-"
            f"{match['line_end']}"
        )

        context_sections.append(
            f"SOURCE [{source_label}]\n"
            f"{match['snippet']}"
        )

    context = "\n\n---\n\n".join(
        context_sections
    )

    return f"""You are Aisha, a local homelab knowledge assistant.

Use only the supplied repository context.

A supported answer must be directly stated in the context.
Do not infer configuration from file names, service names, paths, or conventions.
Do not speculate about files or settings that are not present.
Do not say that something "might", "may", "could", "suggests", or "probably" exists.

If the context does not directly answer the question, reply with exactly:
INSUFFICIENT_CONTEXT

For a supported answer:
- answer the question directly
- cite every factual claim inline
- use citations exactly like [path:line_start-line_end]

Repository context:

{context}

Question:
{question}

Answer:
"""


def generate_answer(prompt: str) -> str:
    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": GENERATION_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
            },
        },
        timeout=300,
    )

    response.raise_for_status()

    answer = (
        response.json()
        .get("response", "")
        .strip()
    )

    if not answer:
        raise RuntimeError(
            "Ollama returned an empty generated response.",
        )

    return answer


def is_insufficient_answer(answer: str) -> bool:
    normalized = answer.strip().lower()

    if normalized == "insufficient_context":
        return True

    unsupported_phrases = (
        "not explicitly configured",
        "not explicitly stated",
        "not shown in",
        "not provided in",
        "not included in",
        "might be",
        "may be",
        "could be",
        "suggests",
        "probably",
        "cannot determine",
        "unable to determine",
        "not enough information",
        "does not contain enough information",
    )

    return any(
        phrase in normalized
        for phrase in unsupported_phrases
    )


def extract_used_citations(
    answer: str,
    matches: list[dict[str, Any]],
) -> list[Citation]:
    citation_pattern = re.compile(
        r"\[([^:\]\n]+):(\d+)-(\d+)\]"
    )

    used_citations = {
        (
            path,
            int(line_start),
            int(line_end),
        )
        for path, line_start, line_end
        in citation_pattern.findall(answer)
    }

    citations: list[Citation] = []

    for match in matches:
        citation_key = (
            match["path"],
            match["line_start"],
            match["line_end"],
        )

        if citation_key not in used_citations:
            continue

        citations.append(
            Citation(
                path=match["path"],
                line_start=match["line_start"],
                line_end=match["line_end"],
                distance=match["distance"],
            )
        )

    return citations


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "vector_store": "chromadb",
        "version": APP_VERSION,
        "collection": collection.name,
        "chunks": collection.count(),
        "embedding_model": EMBEDDING_MODEL,
        "generation_model": GENERATION_MODEL,
        "reranker_enabled": reranker.enabled,
        "reranker_model": reranker.model_name,
        "reranker_threads": reranker.threads,
    }


@app.post("/search")
def search(
    request: SearchRequest,
) -> dict[str, Any]:
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Query must not be empty.",
        )

    try:
        matches = retrieve_chunks(
            query=query,
            limit=request.limit,
            debug=request.debug,
            path=request.path,
            path_prefix=request.path_prefix,
            directory=request.directory,
            extension=request.extension,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama embedding request failed: "
                f"{exc}"
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "query": query,
        "count": len(matches),
        "results": matches,
    }


@app.post(
    "/ask",
    response_model=AskResponse,
    response_model_exclude_none=True,
)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question must not be empty.",
        )

    try:
        matches = retrieve_chunks(
            query=question,
            limit=request.limit,
            debug=request.debug,
            path=request.path,
            path_prefix=request.path_prefix,
            directory=request.directory,
            extension=request.extension,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama embedding request failed: "
                f"{exc}"
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    retrieval_debug = (
        [
            RetrievalDiagnostic(
                path=match["path"],
                line_start=match["line_start"],
                line_end=match["line_end"],
                distance=match["distance"],
                vector_score=match["vector_score"],
                lexical_score=match["lexical_score"],
                combined_score=match["combined_score"],
                matching_tokens=match["matching_tokens"],
                rank=match["rank"],
                hybrid_rank=match.get("hybrid_rank"),
                reranker_score=match.get("reranker_score"),
                reranker_used=match.get("reranker_used", False),
                reranker_error=match.get("reranker_error"),
            )
            for match in matches
        ]
        if request.debug
        else None
    )
    if not matches:
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            retrieval_debug=retrieval_debug,
        )

    prompt = build_grounded_prompt(
        question,
        matches,
    )

    try:
        answer = generate_answer(prompt)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama generation request failed: "
                f"{exc}"
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    if is_insufficient_answer(answer):
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            retrieval_debug=retrieval_debug,
        )

    citations = extract_used_citations(
        answer,
        matches,
    )

    if not citations:
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            retrieval_debug=retrieval_debug,
        )

    return AskResponse(
        question=question,
        answer=answer,
        grounded=True,
        citations=citations,
        retrieval_debug=retrieval_debug,
    )


@app.post("/index")
def index_documents() -> dict[str, Any]:
    from app.indexer import index_repository

    result = index_repository()

    return {
        "status": "indexed",
        **result,
    }


@app.get("/stats")
def stats() -> dict[str, Any]:
    sample = collection.peek(limit=5)

    return {
        "collection": collection.name,
        "chunks": collection.count(),
        "sample_ids": sample.get("ids", []),
        "sample_paths": [
            metadata.get("path")
            for metadata in sample.get(
                "metadatas",
                [],
            )
            if metadata
        ],
    }

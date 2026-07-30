import asyncio
import os
import re
from pathlib import Path
from typing import Any, Literal

import chromadb
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from app.confidence import (
    assess_citation_completeness,
    assess_retrieval_confidence,
)
from app.conversation import (
    MAX_HISTORY_MESSAGES,
    format_conversation_history,
    rewrite_retrieval_query,
)
from app.index_jobs import (
    IndexJobAlreadyRunning,
    IndexJobManager,
)

from app.reranker import LocalReranker
from app.retrieval import candidate_pool_size, rerank_candidates
from app.streaming import sse_event, stream_ollama_answer


APP_VERSION = "0.9.1"


app = FastAPI(
    title="Aisha Local RAG",
    version=APP_VERSION,
)


CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", "/data/chroma"))
INDEX_STATUS_PATH = Path(
    os.environ.get(
        "INDEX_STATUS_PATH",
        str(CHROMA_PATH / "index-status.json"),
    )
)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "nomic-embed-text",
)
GENERATION_MODEL = os.environ.get(
    "GENERATION_MODEL",
    "llama3.2:3b",
)
CONFIDENCE_MIN_SCORE = float(
    os.environ.get("CONFIDENCE_MIN_SCORE", "0.45")
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
index_job_manager = IndexJobManager(INDEX_STATUS_PATH)

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


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=MAX_HISTORY_MESSAGES,
    )
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
    confidence: float
    citation_completeness: float | None = None
    confidence_reasons: list[str] | None = None
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
    history: list[ConversationMessage] | None = None,
) -> str:
    context_sections: list[str] = []
    formatted_history = format_conversation_history(history or [])
    conversation_section = (
        "Conversation history (continuity only; not repository evidence):\n"
        f"<conversation_history>\n{formatted_history}\n"
        "</conversation_history>\n\n"
        if formatted_history
        else ""
    )

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
Conversation history can resolve references but is never factual evidence.
Never repeat a factual claim from history unless repository context supports it.
Do not infer configuration from file names, service names, paths, or conventions.
Do not speculate about files or settings that are not present.
Do not say that something "might", "may", "could", "suggests", or "probably" exists.

If the context does not directly answer the question, reply with exactly:
INSUFFICIENT_CONTEXT

For a supported answer:
- return only a concise answer to the question
- do not reproduce source text or put a citation on its own line
- end every sentence with one or more citations
- copy each citation verbatim from a SOURCE bracket above
- include the complete path and full line range in every citation
- never shorten [path:line_start-line_end] to [path:line_start]
- put each citation in its own brackets: [first] [second]
- never combine sources in one bracket: [first, second]

{conversation_section}
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
    index_job = index_job_manager.snapshot()

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
        "confidence_min_score": CONFIDENCE_MIN_SCORE,
        "index_status": index_job["status"],
        "last_index_success_at": index_job["last_success_at"],
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

    retrieval_query = rewrite_retrieval_query(question, request.history)
    try:
        matches = retrieve_chunks(
            query=retrieval_query,
            limit=request.limit,
            debug=True,
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
    confidence = assess_retrieval_confidence(
        question,
        matches,
        minimum=CONFIDENCE_MIN_SCORE,
    )

    def debug_reasons(*extra: str) -> list[str] | None:
        if not request.debug:
            return None
        return list(
            dict.fromkeys((*confidence.reasons, *extra))
        )

    if not confidence.sufficient:
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            confidence=confidence.score,
            confidence_reasons=debug_reasons(),
            retrieval_debug=retrieval_debug,
        )

    prompt = build_grounded_prompt(
        question,
        matches,
        request.history,
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
            confidence=confidence.score,
            confidence_reasons=debug_reasons("model_refusal"),
            retrieval_debug=retrieval_debug,
        )

    citations = extract_used_citations(
        answer,
        matches,
    )

    citation_assessment = assess_citation_completeness(
        answer,
        matches,
    )
    final_confidence = round(
        confidence.score * citation_assessment.completeness,
        6,
    )

    if not citation_assessment.complete or not citations:
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            confidence=final_confidence,
            citation_completeness=citation_assessment.completeness,
            confidence_reasons=debug_reasons(
                *citation_assessment.reasons
            ),
            retrieval_debug=retrieval_debug,
        )

    return AskResponse(
        question=question,
        answer=answer,
        grounded=True,
        citations=citations,
        confidence=final_confidence,
        citation_completeness=citation_assessment.completeness,
        confidence_reasons=debug_reasons(),
        retrieval_debug=retrieval_debug,
    )


@app.post("/ask/stream")
async def ask_stream(
    request: Request,
    body: AskRequest,
) -> StreamingResponse:
    """Stream provisional tokens followed by an authoritative result.

    Consumers must not treat token events as grounded until the final result.
    """
    question = body.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question must not be empty.",
        )

    retrieval_query = rewrite_retrieval_query(question, body.history)
    try:
        matches = await run_in_threadpool(
            retrieve_chunks,
            retrieval_query,
            body.limit,
            debug=True,
            path=body.path,
            path_prefix=body.path_prefix,
            directory=body.directory,
            extension=body.extension,
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
        if body.debug
        else None
    )
    confidence = assess_retrieval_confidence(
        question,
        matches,
        minimum=CONFIDENCE_MIN_SCORE,
    )

    def debug_reasons(*extra: str) -> list[str] | None:
        if not body.debug:
            return None
        return list(
            dict.fromkeys((*confidence.reasons, *extra))
        )

    def result_event(response: AskResponse) -> str:
        return sse_event(
            "result",
            response.model_dump(exclude_none=True),
        )

    async def events():
        if not confidence.sufficient:
            yield result_event(
                AskResponse(
                    question=question,
                    answer=INSUFFICIENT_CONTEXT_MESSAGE,
                    grounded=False,
                    citations=[],
                    confidence=confidence.score,
                    confidence_reasons=debug_reasons(),
                    retrieval_debug=retrieval_debug,
                )
            )
            return

        prompt = build_grounded_prompt(
            question,
            matches,
            body.history,
        )
        answer_parts: list[str] = []

        try:
            async for token in stream_ollama_answer(
                ollama_url=OLLAMA_URL,
                model=GENERATION_MODEL,
                prompt=prompt,
                is_disconnected=request.is_disconnected,
            ):
                answer_parts.append(token)
                yield sse_event("token", {"text": token})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield sse_event("error", {"detail": str(exc)})
            return

        if await request.is_disconnected():
            return

        answer = "".join(answer_parts).strip()
        if not answer:
            yield sse_event(
                "error",
                {"detail": "Ollama returned an empty generated response."},
            )
            return

        if is_insufficient_answer(answer):
            yield result_event(
                AskResponse(
                    question=question,
                    answer=INSUFFICIENT_CONTEXT_MESSAGE,
                    grounded=False,
                    citations=[],
                    confidence=confidence.score,
                    confidence_reasons=debug_reasons("model_refusal"),
                    retrieval_debug=retrieval_debug,
                )
            )
            return

        citations = extract_used_citations(answer, matches)
        citation_assessment = assess_citation_completeness(
            answer,
            matches,
        )
        final_confidence = round(
            confidence.score * citation_assessment.completeness,
            6,
        )

        if not citation_assessment.complete or not citations:
            yield result_event(
                AskResponse(
                    question=question,
                    answer=INSUFFICIENT_CONTEXT_MESSAGE,
                    grounded=False,
                    citations=[],
                    confidence=final_confidence,
                    citation_completeness=(
                        citation_assessment.completeness
                    ),
                    confidence_reasons=debug_reasons(
                        *citation_assessment.reasons
                    ),
                    retrieval_debug=retrieval_debug,
                )
            )
            return

        yield result_event(
            AskResponse(
                question=question,
                answer=answer,
                grounded=True,
                citations=citations,
                confidence=final_confidence,
                citation_completeness=(
                    citation_assessment.completeness
                ),
                confidence_reasons=debug_reasons(),
                retrieval_debug=retrieval_debug,
            )
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/index/status")
def index_status() -> dict[str, Any]:
    return index_job_manager.snapshot()


@app.post("/index")
def index_documents() -> dict[str, Any]:
    from app.indexer import index_repository

    try:
        index_job_manager.begin()
    except IndexJobAlreadyRunning as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    try:
        result = index_repository()
    except Exception as exc:
        index_job_manager.fail(exc)
        raise HTTPException(
            status_code=500,
            detail="Repository indexing failed.",
        ) from exc

    job = index_job_manager.succeed(result)

    return {
        "status": "indexed",
        **result,
        "job": job,
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

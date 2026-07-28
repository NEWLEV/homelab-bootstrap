import os
from pathlib import Path
from typing import Any

import chromadb
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Aisha Local RAG",
    version="0.2.0",
)

CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", "/data/chroma"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

CHROMA_PATH.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = chroma_client.get_or_create_collection(
    name="homelab_bootstrap",
    metadata={"description": "Aisha homelab repository"},
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    path_prefix: str | None = None


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
        raise RuntimeError("Ollama returned no embedding.")

    return embeddings[0]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "vector_store": "chromadb",
        "collection": collection.name,
        "chunks": collection.count(),
    }


@app.post("/search")
def search(request: SearchRequest) -> dict[str, Any]:
    try:
        query_embedding = embed_text(request.query)

        where = None
        if request.path_prefix:
            where = {
                "path": {
                    "$contains": request.path_prefix,
                }
            }

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    matches = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
        strict=False,
    ):
        matches.append(
            {
                "path": metadata.get("path"),
                "line_start": metadata.get("line_start"),
                "line_end": metadata.get("line_end"),
                "distance": distance,
                "snippet": document,
            }
        )

    return {
        "query": request.query,
        "count": len(matches),
        "results": matches,
    }


@app.post("/index")
def index_documents() -> dict[str, Any]:
    from app.indexer import index_repository

    result = index_repository()
    return {
        "status": "indexed",
        **result,
    }

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="Aisha Local RAG",
    version="0.1.0",
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    workspace: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search")
def search(request: SearchRequest) -> dict:
    return {
        "query": request.query,
        "workspace": request.workspace,
        "results": [],
    }

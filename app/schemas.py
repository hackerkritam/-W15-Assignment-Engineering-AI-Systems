from typing import Any, Literal
from pydantic import BaseModel, Field


class Source(BaseModel):
    document_id: str
    title: str
    content: str
    score: float


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = None
    use_rag: bool = True


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    tool_calls: list[str] = []
    provider: str
    cached: bool = False
    latency_ms: float
    steps: int = 1
    total_tokens: int = 0
    completion_status: str = "completed"


class IngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100000)
    document_id: str | None = None


class IngestResponse(BaseModel):
    document_id: str
    chunks_created: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    provider: str
    documents: int
    cache_entries: int
    requests_total: int
    errors_total: int
    uptime_seconds: float
    version: str = "1.0.0"

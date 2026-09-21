import asyncio
import hashlib
import json
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent import AgentRunner
from app.config import get_settings
from app.provider import LLMProvider
from app.rag import store
from app.schemas import ChatRequest, ChatResponse, HealthResponse, IngestRequest, IngestResponse
from app.tools import TOOLS

settings = get_settings()
provider = LLMProvider(settings)
agent_runner = AgentRunner(provider.decide, store.search, TOOLS, settings.agent_max_steps)
cache: dict[str, tuple[float, ChatResponse]] = {}
request_windows: dict[str, deque[float]] = defaultdict(deque)
metrics = {"requests": 0, "errors": 0}
started = time.monotonic()


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.add_document("Welcome", "ContextPilot is an AI assistant with retrieval augmented generation, structured JSON output, tool calling, retries, rate limiting, and a local vLLM deployment path.", "welcome")
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path == "/chat":
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = request_windows[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        window.append(now)
    return await call_next(request)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse("web/index.html")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", provider=provider.provider_name, documents=len(store.chunks), cache_entries=len(cache), requests_total=metrics["requests"], errors_total=metrics["errors"], uptime_seconds=round(time.monotonic() - started, 2))


@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    document_id, chunks = store.add_document(request.title, request.content, request.document_id)
    return IngestResponse(document_id=document_id, chunks_created=chunks)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    metrics["requests"] += 1
    started_request = time.perf_counter()
    key = hashlib.sha256(json.dumps(request.model_dump(), sort_keys=True).encode()).hexdigest()
    cached = cache.get(key)
    if cached and time.time() - cached[0] < settings.cache_ttl_seconds:
        result = cached[1].model_copy(update={"cached": True, "latency_ms": round((time.perf_counter() - started_request) * 1000, 2)})
        return result
    try:
        result = await asyncio.wait_for(agent_runner.run(request.message, request.use_rag), timeout=20)
    except Exception as error:
        metrics["errors"] += 1
        raise HTTPException(status_code=503, detail=f"Assistant unavailable: {error}") from error
    if request.use_rag and not result.sources:
        result.sources = store.search(request.message)
    response = ChatResponse(answer=result.answer, sources=result.sources, tool_calls=result.tool_calls, provider=provider.provider_name, steps=result.steps, total_tokens=result.total_tokens, completion_status=result.status, latency_ms=round((time.perf_counter() - started_request) * 1000, 2))
    cache[key] = (time.time(), response)
    return response

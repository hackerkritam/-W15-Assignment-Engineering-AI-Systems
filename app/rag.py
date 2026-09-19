import hashlib
import math
import re
import uuid
from dataclasses import dataclass

from app.config import Settings
from app.schemas import Source


@dataclass
class Chunk:
    document_id: str
    title: str
    content: str
    vector: list[float]


class InMemoryVectorStore:
    """Small dependency-free vector store; swap with pgvector/Qdrant in production."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions
        self.chunks: list[Chunk] = []

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def add_document(self, title: str, content: str, document_id: str | None = None) -> tuple[str, int]:
        document_id = document_id or str(uuid.uuid4())
        words = content.split()
        chunks = [" ".join(words[index:index + 180]) for index in range(0, len(words), 150)] or [content]
        self.chunks = [chunk for chunk in self.chunks if chunk.document_id != document_id]
        for chunk_text in chunks:
            self.chunks.append(Chunk(document_id, title, chunk_text, self._embed(chunk_text)))
        return document_id, len(chunks)

    def search(self, query: str, limit: int = 4) -> list[Source]:
        query_vector = self._embed(query)
        scored = []
        for chunk in self.chunks:
            score = sum(left * right for left, right in zip(query_vector, chunk.vector))
            scored.append(Source(document_id=chunk.document_id, title=chunk.title, content=chunk.content, score=round(score, 4)))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]


store = InMemoryVectorStore()

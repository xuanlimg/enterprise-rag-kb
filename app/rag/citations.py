from dataclasses import dataclass
from uuid import UUID

from app.services.retrieval.base import RetrievedChunk


@dataclass(slots=True)
class Citation:
    """回答引用的文档块。"""

    index: int
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float


def build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """把检索结果转换为引用列表。"""
    return [
        Citation(
            index=index,
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            content=chunk.content,
            score=chunk.score,
        )
        for index, chunk in enumerate(chunks, start=1)
    ]

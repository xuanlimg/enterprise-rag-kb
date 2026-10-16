from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.services.retrieval.base import RetrievedChunk


class VectorRetriever:
    """基于 pgvector 的向量检索。"""

    def search(
        self,
        db: Session,
        tenant_id: UUID,
        query_embedding: list[float],
        top_k: int = 30,
    ) -> list[RetrievedChunk]:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
        stmt = (
            select(DocumentChunk, distance)
            .where(
                DocumentChunk.tenant_id == tenant_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(top_k)
        )
        rows = db.execute(stmt).all()
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                score=max(0.0, 1.0 - float(distance_value)),
                page_no=chunk.page_no,
                heading_path=chunk.heading_path,
                metadata=chunk.chunk_metadata,
            )
            for chunk, distance_value in rows
        ]

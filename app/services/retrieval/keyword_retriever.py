from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.services.retrieval.base import RetrievedChunk
from app.services.retrieval.terms import build_query_terms


class KeywordRetriever:
    """关键词检索，当前阶段使用 ILIKE，后续可替换为全文检索。"""

    def search(
        self,
        db: Session,
        tenant_id: UUID,
        query: str,
        top_k: int = 30,
    ) -> list[RetrievedChunk]:
        terms = build_query_terms(query) or [query.strip()]
        conditions = [DocumentChunk.content.ilike(f"%{term}%") for term in terms]

        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.tenant_id == tenant_id, or_(*conditions))
            .limit(top_k)
        )
        chunks = db.execute(stmt).scalars().all()

        results: list[RetrievedChunk] = []
        for chunk in chunks:
            content = chunk.content.lower()
            matched = sum(1 for term in terms if term.lower() in content)
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=matched / max(1, len(terms)),
                    page_no=chunk.page_no,
                    heading_path=chunk.heading_path,
                    metadata=chunk.chunk_metadata,
                )
            )
        return results

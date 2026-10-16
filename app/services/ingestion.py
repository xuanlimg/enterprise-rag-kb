from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import delete

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.chunking.text_chunker import TextChunker
from app.services.embedding.factory import get_embedding_provider
from app.services.parsing.factory import get_parser

logger = structlog.get_logger(__name__)


def ingest_document(document_id: UUID, tenant_id: UUID) -> None:
    """后台摄取文档：解析、切块、向量化并写入数据库。"""
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None or document.tenant_id != tenant_id:
            logger.warning("document_not_found", document_id=str(document_id))
            return

        try:
            document.status = DocumentStatus.parsing.value
            document.error_message = None
            db.commit()

            parser = get_parser(document.filename)
            parsed = parser.parse(Path(document.storage_path))

            document.status = DocumentStatus.chunking.value
            db.commit()
            chunker = TextChunker(
                max_tokens=settings.chunk_max_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
            )
            drafts = chunker.chunk(parsed)

            document.status = DocumentStatus.embedding.value
            db.commit()
            provider = get_embedding_provider()
            vectors = provider.embed_documents([draft.content for draft in drafts])

            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            for draft, vector in zip(drafts, vectors, strict=True):
                db.add(
                    DocumentChunk(
                        tenant_id=tenant_id,
                        document_id=document.id,
                        chunk_index=draft.chunk_index,
                        content=draft.content,
                        token_count=draft.token_count,
                        heading_path=draft.heading_path,
                        page_no=draft.page_no,
                        chunk_metadata=draft.metadata,
                        embedding=vector,
                    )
                )

            document.status = DocumentStatus.ready.value
            db.commit()
            logger.info(
                "document_ingested",
                document_id=str(document_id),
                chunk_count=len(drafts),
            )
        except Exception as exc:
            db.rollback()
            failed_document = db.get(Document, document_id)
            if failed_document is not None:
                failed_document.status = DocumentStatus.failed.value
                failed_document.error_message = str(exc)[:2000]
                db.commit()
            logger.exception(
                "document_ingest_failed",
                document_id=str(document_id),
                error=str(exc),
            )

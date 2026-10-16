from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentBulkDeleteRequest, DocumentPage, DocumentRead
from app.services.ingestion import ingest_document
from app.services.storage import save_upload_file

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    overwrite: bool = Form(default=False),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> Document:
    """上传文档；同名文件默认提示，确认覆盖后替换旧文档。"""
    filename = (file.filename or "unnamed").strip()
    existing = db.execute(
        select(Document).where(
            Document.tenant_id == tenant_id,
            Document.filename == filename,
        )
    ).scalar_one_or_none()

    if existing is not None:
        if not overwrite:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="同名文件已存在，是否覆盖原文件？",
            )
        old_path = Path(existing.storage_path)
        if old_path.exists():
            old_path.unlink()
        db.delete(existing)
        db.commit()

    storage_path = save_upload_file(file.file, filename, tenant_id)
    document = Document(
        tenant_id=tenant_id,
        filename=filename,
        content_type=file.content_type,
        storage_path=str(storage_path),
        status=DocumentStatus.pending.value,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(ingest_document, document.id, tenant_id)
    return document


@router.get("", response_model=DocumentPage)
def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> DocumentPage:
    """分页查询文档，支持按文件名搜索。"""
    filters = [Document.tenant_id == tenant_id]
    if q:
        filters.append(Document.filename.ilike(f"%{q.strip()}%"))

    total = db.execute(
        select(func.count()).select_from(Document).where(*filters)
    ).scalar_one()
    stmt = (
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.execute(stmt).scalars().all())
    return DocumentPage(items=items, total=total, limit=limit, offset=offset)


@router.post("/reingest-all")
def reingest_all_documents(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> dict[str, int | str]:
    """重新摄取当前租户的所有文档。"""
    stmt = select(Document).where(Document.tenant_id == tenant_id)
    documents = list(db.execute(stmt).scalars().all())
    for document in documents:
        document.status = DocumentStatus.pending.value
        document.error_message = None
    db.commit()

    for document in documents:
        background_tasks.add_task(ingest_document, document.id, tenant_id)

    return {"message": "已触发全部重新摄取", "count": len(documents)}


@router.post("/bulk-delete")
def bulk_delete_documents(
    payload: DocumentBulkDeleteRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> dict[str, int | str]:
    """批量删除文档和对应文件。"""
    stmt = select(Document).where(
        Document.tenant_id == tenant_id,
        Document.id.in_(payload.document_ids),
    )
    documents = list(db.execute(stmt).scalars().all())
    for document in documents:
        file_path = Path(document.storage_path)
        if file_path.exists():
            file_path.unlink()
        db.delete(document)
    db.commit()
    return {"message": "文档已批量删除", "count": len(documents)}


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> Document:
    """获取单个文档详情。"""
    document = db.get(Document, document_id)
    if document is None or document.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    return document


@router.post("/{document_id}/ingest", response_model=DocumentRead)
def reingest_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> Document:
    """重新解析并向量化文档。"""
    document = db.get(Document, document_id)
    if document is None or document.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    document.status = DocumentStatus.pending.value
    document.error_message = None
    db.commit()
    db.refresh(document)
    background_tasks.add_task(ingest_document, document.id, tenant_id)
    return document


@router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> dict[str, str]:
    """删除文档和对应文件。"""
    document = db.get(Document, document_id)
    if document is None or document.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    file_path = Path(document.storage_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(document)
    db.commit()
    return {"message": "文档已删除"}

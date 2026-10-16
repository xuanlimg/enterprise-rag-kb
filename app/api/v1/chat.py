import json
from collections.abc import Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_tenant_id
from app.db.session import SessionLocal, get_db
from app.models.conversation import Conversation, Message, MessageCitation
from app.rag.pipeline import RagPipeline
from app.schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    CitationRead,
    ConversationDetail,
    ConversationBulkDeleteRequest,
    ConversationPage,
    ConversationRead,
    ConversationUpdate,
    MessageRead,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    """把事件序列化为 Server-Sent Events 格式。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_or_create_conversation(
    db: Session,
    tenant_id: UUID,
    conversation_id: UUID | None,
    query: str,
) -> Conversation:
    """获取当前租户的会话，不存在时新建。"""
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None and conversation.tenant_id == tenant_id:
            return conversation

    conversation = Conversation(tenant_id=tenant_id, title=query[:80])
    db.add(conversation)
    db.flush()
    return conversation


@router.get("/conversations", response_model=ConversationPage)
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> ConversationPage:
    """分页查询当前租户的会话，支持按标题搜索。"""
    filters = [Conversation.tenant_id == tenant_id]
    if q:
        filters.append(Conversation.title.ilike(f"%{q.strip()}%"))

    total = db.execute(
        select(func.count()).select_from(Conversation).where(*filters)
    ).scalar_one()
    stmt = (
        select(Conversation)
        .where(*filters)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.execute(stmt).scalars().all())
    return ConversationPage(items=items, total=total, limit=limit, offset=offset)


@router.post("/conversations/bulk-delete")
def bulk_delete_conversations(
    payload: ConversationBulkDeleteRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> dict[str, int | str]:
    """批量删除会话及其消息。"""
    stmt = select(Conversation).where(
        Conversation.tenant_id == tenant_id,
        Conversation.id.in_(payload.conversation_ids),
    )
    conversations = list(db.execute(stmt).scalars().all())
    for conversation in conversations:
        db.delete(conversation)
    db.commit()
    return {"message": "会话已批量删除", "count": len(conversations)}


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> ConversationDetail:
    """获取会话详情和引用来源。"""
    stmt = (
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
        .options(
            selectinload(Conversation.messages)
            .selectinload(Message.citations)
            .selectinload(MessageCitation.chunk)
        )
    )
    conversation = db.execute(stmt).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )

    messages: list[MessageRead] = []
    for message in sorted(conversation.messages, key=lambda item: item.created_at):
        citations: list[CitationRead] = []
        for index, citation in enumerate(message.citations, start=1):
            chunk = citation.chunk
            if chunk is None:
                continue
            citations.append(
                CitationRead(
                    index=index,
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=citation.score,
                )
            )
        messages.append(
            MessageRead(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                citations=citations,
            )
        )

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=messages,
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationRead)
def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> Conversation:
    """重命名会话。"""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    conversation.title = payload.title
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> dict[str, str]:
    """删除会话及其消息。"""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    db.delete(conversation)
    db.commit()
    return {"message": "会话已删除"}


@router.post("/query", response_model=ChatQueryResponse)
def query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> ChatQueryResponse:
    """执行非流式 RAG 问答并保存会话记录。"""
    pipeline = RagPipeline(db=db, tenant_id=tenant_id)
    result = pipeline.answer(request.query, top_k=request.top_k)

    conversation = _get_or_create_conversation(
        db=db,
        tenant_id=tenant_id,
        conversation_id=request.conversation_id,
        query=request.query,
    )
    db.add(Message(conversation_id=conversation.id, role="user", content=request.query))
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
    )
    db.add(assistant_message)
    db.flush()

    for citation in result.citations:
        db.add(
            MessageCitation(
                message_id=assistant_message.id,
                chunk_id=citation.chunk_id,
                score=citation.score,
            )
        )
    db.commit()

    return ChatQueryResponse(
        conversation_id=conversation.id,
        answer=result.answer,
        citations=[
            CitationRead(
                index=citation.index,
                chunk_id=citation.chunk_id,
                document_id=citation.document_id,
                content=citation.content,
                score=citation.score,
            )
            for citation in result.citations
        ],
        latency_ms=result.latency_ms,
    )


@router.post("/stream")
def stream_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> StreamingResponse:
    """执行 SSE 流式 RAG 问答。"""
    conversation = _get_or_create_conversation(
        db=db,
        tenant_id=tenant_id,
        conversation_id=request.conversation_id,
        query=request.query,
    )
    db.add(Message(conversation_id=conversation.id, role="user", content=request.query))
    db.commit()
    conversation_id = conversation.id

    def event_generator() -> Iterator[str]:
        answer_parts: list[str] = []
        citations_payload: list[dict] = []
        try:
            # 流式生成期间使用独立会话，避免请求会话生命周期影响。
            with SessionLocal() as session:
                pipeline = RagPipeline(db=session, tenant_id=tenant_id)
                for event in pipeline.stream_answer(request.query, request.top_k):
                    if event.event == "citations":
                        citations_payload = event.data.get("citations", [])
                    elif event.event == "token":
                        answer_parts.append(event.data.get("text", ""))
                    elif event.event == "done":
                        event.data["conversation_id"] = str(conversation_id)
                    yield _sse(event.event, event.data)
        except Exception as exc:
            # 模型或检索失败时，把错误作为 SSE 事件发给前端，避免只显示引用没有回答。
            yield _sse("error", {"message": str(exc)})
        finally:
            if answer_parts:
                with SessionLocal() as session:
                    assistant = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content="".join(answer_parts),
                    )
                    session.add(assistant)
                    session.flush()
                    for item in citations_payload:
                        session.add(
                            MessageCitation(
                                message_id=assistant.id,
                                chunk_id=UUID(item["chunk_id"]),
                                score=float(item.get("score", 0.0)),
                            )
                        )
                    session.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatQueryRequest(BaseModel):
    """RAG 问答请求。"""

    query: str = Field(min_length=1, description="用户问题")
    conversation_id: UUID | None = Field(default=None, description="可选会话 ID")
    top_k: int = Field(default=5, ge=1, le=20, description="最终送入模型的引用数量")


class CitationRead(BaseModel):
    """引用来源。"""

    index: int
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float


class ChatQueryResponse(BaseModel):
    """RAG 问答响应。"""

    conversation_id: UUID
    answer: str
    citations: list[CitationRead]
    latency_ms: float


class ConversationRead(BaseModel):
    """会话列表项。"""

    id: UUID
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationPage(BaseModel):
    """会话分页响应。"""

    items: list[ConversationRead]
    total: int
    limit: int
    offset: int


class ConversationBulkDeleteRequest(BaseModel):
    """批量删除会话请求。"""

    conversation_ids: list[UUID]


class ConversationUpdate(BaseModel):
    """会话更新请求。"""

    title: str = Field(min_length=1, max_length=255)


class MessageRead(BaseModel):
    """会话消息。"""

    id: UUID
    role: str
    content: str
    created_at: datetime
    citations: list[CitationRead] = Field(default_factory=list)


class ConversationDetail(BaseModel):
    """会话详情。"""

    id: UUID
    title: str
    created_at: datetime
    messages: list[MessageRead]

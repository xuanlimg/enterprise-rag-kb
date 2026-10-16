from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """文档响应模型。"""

    id: UUID
    filename: str
    content_type: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentPage(BaseModel):
    """文档分页响应。"""

    items: list[DocumentRead]
    total: int
    limit: int
    offset: int


class DocumentBulkDeleteRequest(BaseModel):
    """批量删除文档请求。"""

    document_ids: list[UUID]

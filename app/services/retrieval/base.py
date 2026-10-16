from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class RetrievedChunk:
    """检索结果。"""

    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    page_no: int | None = None
    heading_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

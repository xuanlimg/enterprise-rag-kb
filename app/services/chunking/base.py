from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChunkDraft:
    """切块草稿，尚未写入数据库。"""

    content: str
    chunk_index: int
    token_count: int
    heading_path: str | None = None
    page_no: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

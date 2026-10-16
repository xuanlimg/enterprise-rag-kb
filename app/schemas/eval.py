from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvalRunRequest(BaseModel):
    """评测请求。"""

    dataset_name: str = "rag_benchmark"
    top_k: int = 5


class EvalRunResponse(BaseModel):
    """评测响应。"""

    status: str
    message: str
    metrics: dict[str, float] = Field(default_factory=dict)
    results: list[dict] = Field(default_factory=list)


class EvalRunRead(BaseModel):
    """历史评测记录。"""

    id: UUID
    dataset_name: str
    hit_rate: float
    mrr: float
    metrics: dict = Field(default_factory=dict)
    created_at: datetime

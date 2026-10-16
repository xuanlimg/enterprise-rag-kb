from dataclasses import replace
from uuid import UUID

from app.services.retrieval.base import RetrievedChunk


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]],
    k: int = 60,
) -> list[RetrievedChunk]:
    """使用 RRF 融合多路召回结果。"""
    scores: dict[UUID, float] = {}
    chunk_map: dict[UUID, RetrievedChunk] = {}

    for results in result_lists:
        for rank, chunk in enumerate(results, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
            chunk_map.setdefault(chunk.chunk_id, chunk)

    fused = [replace(chunk, score=scores[chunk_id]) for chunk_id, chunk in chunk_map.items()]
    fused.sort(key=lambda item: item.score, reverse=True)
    return fused

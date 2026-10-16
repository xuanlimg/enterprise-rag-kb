from app.services.retrieval.base import RetrievedChunk
from app.services.retrieval.terms import build_query_terms


class HeuristicReranker:
    """轻量重排器，先按关键词重合度做启发式排序。

    后续可以替换成 Cross-Encoder 或云服务 Rerank。
    """

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        terms = set(build_query_terms(query))
        if not terms:
            return chunks[:top_k]

        def score(chunk: RetrievedChunk) -> float:
            content = chunk.content.lower()
            overlap = sum(1 for term in terms if term.lower() in content)
            return chunk.score + overlap * 0.05

        return sorted(chunks, key=score, reverse=True)[:top_k]

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.citations import Citation, build_citations
from app.rag.prompts import SYSTEM_PROMPT, build_rag_user_prompt
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.factory import get_embedding_provider
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.retrieval.base import RetrievedChunk
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.keyword_retriever import KeywordRetriever
from app.services.retrieval.reranker import HeuristicReranker
from app.services.retrieval.vector_retriever import VectorRetriever


@dataclass(slots=True)
class RagAnswer:
    """RAG 回答结果。"""

    answer: str
    citations: list[Citation]
    latency_ms: float


@dataclass(slots=True)
class RagStreamEvent:
    """SSE 流式事件。"""

    event: str
    data: dict[str, Any]


class RagPipeline:
    """RAG 主流程：向量检索、关键词检索、融合、重排、生成。"""

    def __init__(
        self,
        db: Session,
        tenant_id: UUID,
        embedding_provider: BaseEmbeddingProvider | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.llm_provider = llm_provider or get_llm_provider()

    def answer(self, query: str, top_k: int | None = None) -> RagAnswer:
        """执行一次完整问答。"""
        top_k = top_k or settings.retrieval_rerank_top_k
        return self.answer_from_chunks(query, self.retrieve(query, top_k))

    def answer_from_chunks(self, query: str, chunks: list[RetrievedChunk]) -> RagAnswer:
        """基于已经检索好的片段生成回答，评测时可以复用检索结果。"""
        started_at = time.perf_counter()
        if not chunks:
            return RagAnswer(
                answer="知识库中没有检索到相关内容。",
                citations=[],
                latency_ms=(time.perf_counter() - started_at) * 1000,
            )

        user_prompt = build_rag_user_prompt(query, chunks)
        answer = self.llm_provider.generate(SYSTEM_PROMPT, user_prompt)
        return RagAnswer(
            answer=answer,
            citations=build_citations(chunks),
            latency_ms=(time.perf_counter() - started_at) * 1000,
        )

    def stream_answer(self, query: str, top_k: int | None = None) -> Iterator[RagStreamEvent]:
        """流式执行问答，依次产生 citations、token、done 事件。"""
        started_at = time.perf_counter()
        top_k = top_k or settings.retrieval_rerank_top_k
        reranked = self.retrieve(query, top_k)
        citations = build_citations(reranked)

        yield RagStreamEvent(
            event="citations",
            data={"citations": [self._citation_to_dict(item) for item in citations]},
        )

        if not reranked:
            text = "知识库中没有检索到相关内容。"
            yield RagStreamEvent(event="token", data={"text": text})
            yield RagStreamEvent(
                event="done",
                data={
                    "latency_ms": (time.perf_counter() - started_at) * 1000,
                    "answer": text,
                },
            )
            return

        user_prompt = build_rag_user_prompt(query, reranked)
        answer_parts: list[str] = []
        for piece in self.llm_provider.stream(SYSTEM_PROMPT, user_prompt):
            answer_parts.append(piece)
            yield RagStreamEvent(event="token", data={"text": piece})

        yield RagStreamEvent(
            event="done",
            data={
                "latency_ms": (time.perf_counter() - started_at) * 1000,
                "answer": "".join(answer_parts),
            },
        )

    def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        """执行混合检索和重排。"""
        query_embedding = self.embedding_provider.embed_query(query)
        vector_results = VectorRetriever().search(
            self.db,
            tenant_id=self.tenant_id,
            query_embedding=query_embedding,
            top_k=settings.retrieval_vector_top_k,
        )
        keyword_results = KeywordRetriever().search(
            self.db,
            tenant_id=self.tenant_id,
            query=query,
            top_k=settings.retrieval_keyword_top_k,
        )
        fused = reciprocal_rank_fusion([vector_results, keyword_results])
        return HeuristicReranker().rerank(query, fused, top_k)

    @staticmethod
    def _citation_to_dict(citation: Citation) -> dict[str, Any]:
        """把引用对象转换为可 JSON 序列化的结构。"""
        return {
            "index": citation.index,
            "chunk_id": str(citation.chunk_id),
            "document_id": str(citation.document_id),
            "content": citation.content,
            "score": citation.score,
        }

from collections.abc import Callable
from dataclasses import asdict, dataclass

from app.eval.loader import EvalCase
from app.eval.metrics import keyword_coverage
from app.services.retrieval.base import RetrievedChunk


@dataclass(slots=True)
class EvalCaseResult:
    """单条评测结果。"""

    question: str
    retrieved_chunk_ids: list[str]
    relevant_ranks: list[int]
    hit: bool
    reciprocal_rank: float
    answer: str
    answer_keyword_coverage: float


def evaluate_cases(
    cases: list[EvalCase],
    retrieve_fn: Callable[[str, int], list[RetrievedChunk]],
    answer_fn: Callable[[str, list[RetrievedChunk]], str],
    top_k: int = 5,
) -> dict:
    """运行检索和生成评测。"""
    results: list[EvalCaseResult] = []
    hits: list[float] = []
    reciprocal_ranks: list[float] = []
    coverages: list[float] = []

    for case in cases:
        chunks = retrieve_fn(case.question, top_k)
        relevant_ranks = [
            rank
            for rank, chunk in enumerate(chunks, start=1)
            if any(
                keyword.lower() in chunk.content.lower()
                for keyword in case.relevant_keywords
            )
        ]
        hit = bool(relevant_ranks)
        reciprocal_rank = 1.0 / min(relevant_ranks) if relevant_ranks else 0.0
        answer = answer_fn(case.question, chunks)
        coverage = keyword_coverage(answer, case.relevant_keywords)

        results.append(
            EvalCaseResult(
                question=case.question,
                retrieved_chunk_ids=[str(chunk.chunk_id) for chunk in chunks],
                relevant_ranks=relevant_ranks,
                hit=hit,
                reciprocal_rank=reciprocal_rank,
                answer=answer,
                answer_keyword_coverage=coverage,
            )
        )
        hits.append(1.0 if hit else 0.0)
        reciprocal_ranks.append(reciprocal_rank)
        coverages.append(coverage)

    case_count = len(cases)
    return {
        "cases": case_count,
        "top_k": top_k,
        "hit_rate": sum(hits) / case_count if case_count else 0.0,
        "mrr": sum(reciprocal_ranks) / case_count if case_count else 0.0,
        "avg_answer_keyword_coverage": sum(coverages) / case_count if case_count else 0.0,
        "results": [asdict(result) for result in results],
    }

def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """计算 Recall@K。"""
    if not relevant_ids:
        return 0.0
    top_ids = set(retrieved_ids[:k])
    return len(top_ids & relevant_ids) / len(relevant_ids)


def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """计算 MRR，即第一个相关结果排名的倒数。"""
    if not relevant_ids:
        return 0.0
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def keyword_coverage(text: str, keywords: list[str]) -> float:
    """计算答案覆盖了多少评测关键词。"""
    if not keywords:
        return 0.0
    lowered = text.lower()
    hits = sum(1 for keyword in keywords if keyword.lower() in lowered)
    return hits / len(keywords)

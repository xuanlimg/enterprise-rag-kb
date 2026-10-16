from app.services.retrieval.terms import build_query_terms


def test_build_query_terms_for_chinese() -> None:
    """中文长词应拆成双字滑窗。"""
    terms = build_query_terms("差旅报销标准")
    assert "差旅" in terms
    assert "报销" in terms
    assert len(terms) <= 8


def test_build_query_terms_for_english() -> None:
    """英文关键词应保持原样。"""
    terms = build_query_terms("RAG retrieval")
    assert terms == ["RAG", "retrieval"]

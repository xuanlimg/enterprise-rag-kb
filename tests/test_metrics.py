from app.eval.metrics import mrr, recall_at_k


def test_recall_at_k() -> None:
    """召回率按命中相关文档比例计算。"""
    assert recall_at_k(["a", "b", "c"], {"b", "d"}, 3) == 0.5
    assert recall_at_k(["a", "b"], {"b"}, 1) == 0.0


def test_mrr() -> None:
    """MRR 取第一个相关结果的倒数排名。"""
    assert mrr(["a", "b", "c"], {"b"}) == 0.5
    assert mrr(["a", "b"], {"c"}) == 0.0

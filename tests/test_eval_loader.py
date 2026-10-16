from app.eval.loader import list_datasets, load_dataset


def test_list_datasets() -> None:
    """应能发现内置评测集。"""
    assert "rag_benchmark" in list_datasets()


def test_load_benchmark() -> None:
    """内置评测集应包含有效用例。"""
    cases = load_dataset("rag_benchmark")
    assert len(cases) >= 10
    assert all(case.question for case in cases)
    assert all(case.relevant_keywords for case in cases)

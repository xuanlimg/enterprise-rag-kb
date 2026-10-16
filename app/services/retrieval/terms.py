import re


def build_query_terms(query: str, max_terms: int = 8) -> list[str]:
    """把查询拆成关键词，中文长词补充双字滑窗。

    这样即使没有中文分词器，也能提升 ILIKE 关键词检索的命中率。
    """
    raw_terms = [
        term
        for term in re.split(r"[\s,，。;；、]+", query.strip())
        if term
    ]
    if not raw_terms:
        return []

    terms: list[str] = []
    for term in raw_terms:
        # 英文、数字和短词直接使用。
        if term.isascii() or len(term) <= 4:
            terms.append(term)
            continue
        # 中文长词拆成双字滑窗，例如“差旅报销” -> 差旅、旅报、报销。
        terms.extend(term[index : index + 2] for index in range(len(term) - 1))

    unique_terms = list(dict.fromkeys(term for term in terms if term.strip()))
    return unique_terms[:max_terms]

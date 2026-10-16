from app.services.retrieval.base import RetrievedChunk

SYSTEM_PROMPT = """你是一个企业知识库助手。
你只能根据提供的资料回答问题，不要编造资料中不存在的信息。
如果资料不足以回答，请明确说明“知识库中没有足够信息”。
回答时使用 [1]、[2] 这样的编号标注引用来源，并在结尾列出引用来源。"""


def build_rag_user_prompt(query: str, chunks: list[RetrievedChunk]) -> str:
    """把检索结果拼接成带编号的上下文。"""
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        source = f"来源 {index}"
        if chunk.page_no is not None:
            source += f"，第 {chunk.page_no} 页"
        context_blocks.append(f"[{index}] {source}\n{chunk.content}")

    context = "\n\n".join(context_blocks)
    return f"""请根据下面的资料回答问题。

问题：
{query}

资料：
{context}
"""

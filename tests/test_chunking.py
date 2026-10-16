from app.services.chunking.text_chunker import TextChunker
from app.services.parsing.base import ParsedDocument, ParsedPage


def test_chunk_short_text() -> None:
    """短文本应保持为一个块。"""
    parsed = ParsedDocument(
        text="这是一段短文本。",
        pages=[ParsedPage(page_no=1, text="这是一段短文本。")],
    )
    chunker = TextChunker(max_tokens=50, overlap_tokens=5)
    chunks = chunker.chunk(parsed)
    assert len(chunks) == 1
    assert chunks[0].content == "这是一段短文本。"
    assert chunks[0].page_no == 1


def test_chunk_long_text_with_overlap() -> None:
    """长文本应切分为多个块，并保留页码。"""
    text = "知识库" * 200
    parsed = ParsedDocument(
        text=text,
        pages=[ParsedPage(page_no=2, text=text)],
    )
    chunker = TextChunker(max_tokens=50, overlap_tokens=10, chars_per_token=1)
    chunks = chunker.chunk(parsed)
    assert len(chunks) > 1
    assert all(chunk.page_no == 2 for chunk in chunks)

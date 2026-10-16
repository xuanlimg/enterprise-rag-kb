from app.services.chunking.base import ChunkDraft
from app.services.parsing.base import ParsedDocument, ParsedPage


class TextChunker:
    """按近似 Token 长度切块，保留页码和基础元数据。

    当前实现用字符数近似 Token，目的是先跑通流程。
    后续可以替换为 tiktoken 或模型自带 tokenizer。
    """

    def __init__(
        self,
        max_tokens: int = 500,
        overlap_tokens: int = 80,
        chars_per_token: int = 2,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens 必须大于 0")
        if overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens 必须大于等于 0 且小于 max_tokens")
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.chars_per_token = chars_per_token

    def chunk(self, parsed: ParsedDocument) -> list[ChunkDraft]:
        """把解析结果切成可向量化的文本块。"""
        drafts: list[ChunkDraft] = []
        pages = parsed.pages or [ParsedPage(page_no=None, text=parsed.text)]
        chunk_index = 0

        for page in pages:
            text = page.text.strip()
            if not text:
                continue
            for piece in self._split_text(text):
                drafts.append(
                    ChunkDraft(
                        content=piece,
                        chunk_index=chunk_index,
                        token_count=max(1, len(piece) // self.chars_per_token),
                        page_no=page.page_no,
                        metadata={"chars": len(piece)},
                    )
                )
                chunk_index += 1

        return drafts

    def _split_text(self, text: str) -> list[str]:
        """按字符窗口滑动切分，避免把一段话完全切断。"""
        max_chars = self.max_tokens * self.chars_per_token
        overlap_chars = self.overlap_tokens * self.chars_per_token

        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(text):
                break
            start = max(end - overlap_chars, start + 1)

        return chunks

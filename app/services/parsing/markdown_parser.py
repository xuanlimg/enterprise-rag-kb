from pathlib import Path

from app.services.parsing.base import BaseParser, ParsedDocument, ParsedPage


class MarkdownParser(BaseParser):
    """Markdown 解析器，当前阶段直接读取纯文本。"""

    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        return ParsedDocument(
            text=text,
            pages=[ParsedPage(page_no=None, text=text)],
            metadata={"parser": "markdown"},
        )

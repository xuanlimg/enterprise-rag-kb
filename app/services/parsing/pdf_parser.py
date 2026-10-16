from pathlib import Path

from pypdf import PdfReader

from app.services.parsing.base import BaseParser, ParsedDocument, ParsedPage


class PdfParser(BaseParser):
    """PDF 解析器，逐页提取文本。"""

    def parse(self, path: Path) -> ParsedDocument:
        reader = PdfReader(str(path))
        pages: list[ParsedPage] = []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(ParsedPage(page_no=index, text=text))
        full_text = "\n\n".join(page.text for page in pages)
        return ParsedDocument(
            text=full_text,
            pages=pages,
            metadata={"parser": "pdf", "page_count": len(reader.pages)},
        )

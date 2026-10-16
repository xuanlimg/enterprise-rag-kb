from pathlib import Path

import docx

from app.services.parsing.base import BaseParser, ParsedDocument, ParsedPage


class DocxParser(BaseParser):
    """Word 解析器，读取段落和表格文本。"""

    def parse(self, path: Path) -> ParsedDocument:
        document = docx.Document(str(path))
        lines: list[str] = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                lines.append(text)

        # 表格按行拍平，方便后续检索。
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))

        text = "\n".join(lines)
        return ParsedDocument(
            text=text,
            pages=[ParsedPage(page_no=None, text=text)],
            metadata={"parser": "docx", "paragraph_count": len(lines)},
        )

from pathlib import Path
from typing import Type

from app.services.parsing.base import BaseParser
from app.services.parsing.docx_parser import DocxParser
from app.services.parsing.excel_parser import ExcelParser
from app.services.parsing.markdown_parser import MarkdownParser
from app.services.parsing.pdf_parser import PdfParser
from app.services.parsing.text_parser import TextParser

PARSER_MAP: dict[str, Type[BaseParser]] = {
    ".pdf": PdfParser,
    ".docx": DocxParser,
    ".xlsx": ExcelParser,
    ".xlsm": ExcelParser,
    ".md": MarkdownParser,
    ".markdown": MarkdownParser,
    ".txt": TextParser,
}


def get_parser(filename: str) -> BaseParser:
    """根据文件后缀返回解析器。"""
    suffix = Path(filename).suffix.lower()
    parser_class = PARSER_MAP.get(suffix)
    if parser_class is None:
        raise ValueError(f"暂不支持该文件类型: {suffix or 'unknown'}")
    return parser_class()

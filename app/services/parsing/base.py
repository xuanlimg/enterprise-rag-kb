from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class ParsedPage:
    """解析后的单页文本。"""

    page_no: int | None
    text: str


@dataclass(slots=True)
class ParsedDocument:
    """解析后的文档，保留全文和分页信息。"""

    text: str
    pages: list[ParsedPage]
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseParser(Protocol):
    """文档解析器协议。"""

    def parse(self, path: Path) -> ParsedDocument:
        """解析文件并返回结构化文本。"""

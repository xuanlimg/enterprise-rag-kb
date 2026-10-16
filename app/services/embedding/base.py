from typing import Protocol


class BaseEmbeddingProvider(Protocol):
    """向量化提供方协议。"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文档。"""

    def embed_query(self, text: str) -> list[float]:
        """向量化查询语句。"""

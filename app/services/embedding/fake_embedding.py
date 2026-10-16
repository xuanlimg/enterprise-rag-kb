import hashlib
import math


class FakeEmbeddingProvider:
    """本地开发用假向量，保证不配置 API Key 也能跑通流程。"""

    def __init__(self, dim: int = 1536) -> None:
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        """使用哈希生成稳定向量，仅用于开发调试，不具备语义能力。"""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [
            ((digest[index % len(digest)] / 255.0) * 2.0) - 1.0
            for index in range(self.dim)
        ]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

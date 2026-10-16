from fastembed import TextEmbedding


class FastEmbedEmbeddingProvider:
    """本地 BGE 向量模型，使用 fastembed + onnxruntime。"""

    def __init__(
        self,
        model_name: str,
        query_prefix: str = "",
        cache_dir: str | None = None,
    ) -> None:
        if cache_dir:
            self.model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        else:
            self.model = TextEmbedding(model_name=model_name)
        self.query_prefix = query_prefix

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.embed(texts)
        return [list(map(float, vector)) for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        query = self.query_prefix + text if self.query_prefix else text
        return self.embed_documents([query])[0]

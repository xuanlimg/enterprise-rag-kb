from functools import lru_cache

import structlog

from app.core.config import settings
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.fake_embedding import FakeEmbeddingProvider
from app.services.embedding.fastembed_embedding import FastEmbedEmbeddingProvider
from app.services.embedding.openai_embedding import OpenAIEmbeddingProvider

logger = structlog.get_logger(__name__)


@lru_cache
def get_embedding_provider() -> BaseEmbeddingProvider:
    """根据配置返回向量化提供方。"""
    provider = settings.embedding_provider.lower()
    api_key = settings.embedding_api_key or settings.openai_api_key
    base_url = settings.embedding_base_url or settings.openai_base_url

    if provider in {"fastembed", "local"}:
        return FastEmbedEmbeddingProvider(
            model_name=settings.embedding_model,
            query_prefix=settings.embedding_query_prefix,
            cache_dir=settings.embedding_cache_dir,
        )

    if provider == "openai":
        if not api_key:
            logger.warning("embedding_api_key_missing_fallback_to_fake")
            return FakeEmbeddingProvider(dim=settings.embedding_dim)
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.embedding_model,
        )

    return FakeEmbeddingProvider(dim=settings.embedding_dim)

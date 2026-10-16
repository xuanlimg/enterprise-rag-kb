from functools import lru_cache

import structlog

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.echo_llm import EchoLLMProvider
from app.services.llm.openai_llm import OpenAILLMProvider

logger = structlog.get_logger(__name__)


@lru_cache
def get_llm_provider() -> BaseLLMProvider:
    """根据配置返回大模型提供方。"""
    provider = settings.llm_provider.lower()
    api_key = settings.llm_api_key or settings.openai_api_key
    base_url = settings.llm_base_url or settings.openai_base_url

    if provider == "openai":
        if not api_key:
            logger.warning("llm_api_key_missing_fallback_to_echo")
            return EchoLLMProvider()
        return OpenAILLMProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.llm_model,
        )
    return EchoLLMProvider()

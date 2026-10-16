from functools import lru_cache
from pathlib import Path
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，统一从环境变量和 .env 文件读取。"""

    app_name: str = "Enterprise RAG KB"
    environment: str = "dev"
    debug: bool = True

    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"
    default_tenant_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    auto_create_tables: bool = True
    storage_dir: Path = Path("./data/uploads")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # 登录鉴权配置
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 1440
    auth_required: bool = False

    # 向量化配置
    embedding_provider: str = "fake"
    embedding_dim: int = 1536
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_query_prefix: str = ""
    embedding_cache_dir: str | None = None

    # 大模型配置
    llm_provider: str = "echo"
    llm_model: str = "deepseek-v4-pro"
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    # 兼容旧变量名
    openai_api_key: str | None = None
    openai_base_url: str | None = None

    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 80
    retrieval_vector_top_k: int = 30
    retrieval_keyword_top_k: int = 30
    retrieval_rerank_top_k: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免重复读取环境变量。"""
    return Settings()


settings = get_settings()

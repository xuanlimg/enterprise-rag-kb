from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str | bool]:
    """健康检查接口，同时返回当前生效的模型提供方。"""
    embedding_key = settings.embedding_api_key or settings.openai_api_key
    llm_key = settings.llm_api_key or settings.openai_api_key

    configured_embedding = settings.embedding_provider.lower()
    configured_llm = settings.llm_provider.lower()

    embedding_ready = configured_embedding != "openai" or bool(embedding_key)
    llm_ready = configured_llm != "openai" or bool(llm_key)

    embedding_provider = (
        settings.embedding_provider if embedding_ready else "fake"
    )
    llm_provider = settings.llm_provider if llm_ready else "echo"

    return {
        "status": "ok",
        "embedding_provider": embedding_provider,
        "llm_provider": llm_provider,
        "embedding_configured": embedding_ready,
        "llm_configured": llm_ready,
        "openai_configured": embedding_ready and llm_ready,
    }


@router.get("/health/db")
def health_db() -> dict[str, str]:
    """检查数据库连接，数据库不可用时返回 503。"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unavailable: {exc}",
        ) from exc
    return {"status": "ok", "database": "connected"}

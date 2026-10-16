from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# PostgreSQL 连接增加超时，数据库没启动时也能让服务快速监听。
connect_args = {}
if settings.database_url.startswith("postgresql"):
    connect_args["connect_timeout"] = 3

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 数据库依赖，每个请求使用独立会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

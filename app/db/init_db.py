from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine

# 导入模型，确保 Base.metadata 能感知所有表。
import app.models  # noqa: F401
from app.models.tenant import Tenant


def init_db() -> None:
    """初始化数据库：启用 pgvector、建表并写入默认租户。"""
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)
    seed_default_tenant()


def seed_default_tenant() -> None:
    """确保默认租户存在，便于本地开发不登录也能调用接口。"""
    with SessionLocal() as db:
        tenant = db.get(Tenant, settings.default_tenant_id)
        if tenant is None:
            db.add(Tenant(id=settings.default_tenant_id, name="默认空间"))
            db.commit()

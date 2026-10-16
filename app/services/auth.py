from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User


class AuthError(Exception):
    """鉴权相关错误。"""


def register_user(
    db: Session,
    email: str,
    password: str,
    tenant_name: str | None = None,
) -> User:
    """注册用户，可选创建新的租户空间。"""
    normalized_email = email.strip().lower()
    existing = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()
    if existing is not None:
        raise AuthError("该邮箱已注册")

    if tenant_name:
        tenant = db.execute(
            select(Tenant).where(Tenant.name == tenant_name.strip())
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name=tenant_name.strip())
            db.add(tenant)
            db.flush()
    else:
        tenant = db.get(Tenant, settings.default_tenant_id)
        if tenant is None:
            tenant = Tenant(id=settings.default_tenant_id, name="默认空间")
            db.add(tenant)
            db.flush()

    user = User(
        tenant_id=tenant.id,
        email=normalized_email,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """校验邮箱和密码。"""
    normalized_email = email.strip().lower()
    user = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthError("邮箱或密码错误")
    if not user.is_active:
        raise AuthError("用户已被禁用")
    return user

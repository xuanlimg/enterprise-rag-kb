from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tokens import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """解析 Bearer Token，返回当前用户；未登录时返回 None。"""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )
    return user


def get_current_tenant_id(
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-Id"),
    current_user: User | None = Depends(get_current_user),
) -> UUID:
    """优先使用登录用户所属租户，未登录时按配置回退。"""
    if current_user is not None:
        return current_user.tenant_id
    if settings.auth_required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    return x_tenant_id or settings.default_tenant_id

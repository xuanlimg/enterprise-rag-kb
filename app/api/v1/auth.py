from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.tokens import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRead, UserRegister
from app.services.auth import AuthError, authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    """注册新用户，可以顺便创建租户空间。"""
    try:
        return register_user(
            db=db,
            email=payload.email,
            password=payload.password,
            tenant_name=payload.tenant_name,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """登录并返回访问令牌。"""
    try:
        user = authenticate_user(db, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    token = create_access_token(subject=str(user.id), tenant_id=user.tenant_id)
    return TokenResponse(
        access_token=token,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(current_user: User | None = Depends(get_current_user)) -> User:
    """返回当前登录用户。"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    return current_user

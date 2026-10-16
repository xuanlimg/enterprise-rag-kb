from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    """注册请求。"""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    tenant_name: str | None = Field(default=None, max_length=128)


class UserLogin(BaseModel):
    """登录请求。"""

    email: str
    password: str


class UserRead(BaseModel):
    """用户信息响应。"""

    id: UUID
    tenant_id: UUID
    email: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """登录成功后的令牌响应。"""

    access_token: str
    token_type: str = "bearer"
    user: UserRead

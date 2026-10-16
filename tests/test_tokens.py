from uuid import uuid4

from app.core.tokens import create_access_token, decode_access_token


def test_create_and_decode_token() -> None:
    """令牌应能正确保存用户和租户信息。"""
    tenant_id = uuid4()
    token = create_access_token(subject="user-1", tenant_id=tenant_id)
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == str(tenant_id)

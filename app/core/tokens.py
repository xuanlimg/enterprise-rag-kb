import base64
import hashlib
import hmac
import json
import time
from uuid import UUID

from app.core.config import settings


def _b64url_encode(data: bytes) -> str:
    """URL 安全的 Base64 编码，去掉补位等号。"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    """URL 安全 Base64 解码，自动补齐等号。"""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    subject: str,
    tenant_id: UUID,
    expires_minutes: int | None = None,
) -> str:
    """生成 HS256 签名的访问令牌。

    这里手写最小 JWT，避免额外引入第三方依赖。
    """
    now = int(time.time())
    expires_in = expires_minutes or settings.access_token_expire_minutes
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + expires_in * 60,
    }

    header_b64 = _b64url_encode(
        json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict:
    """校验并解析访问令牌，失败时抛出 ValueError。"""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("token 格式错误") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    actual_signature = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("token 签名无效")

    payload = json.loads(_b64url_decode(payload_b64))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("token 已过期")
    return payload

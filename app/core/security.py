import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 120_000
ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """使用 PBKDF2 生成密码哈希，避免额外引入 bcrypt 依赖。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{ALGORITHM}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """校验密码哈希。"""
    try:
        algorithm, iterations_text, salt, expected = hashed_password.split("$", 3)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations_text),
    )
    return hmac.compare_digest(digest.hex(), expected)

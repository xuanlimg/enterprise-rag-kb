import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from app.core.config import settings


def save_upload_file(file_obj: BinaryIO, filename: str, tenant_id: UUID) -> Path:
    """把上传文件保存到租户隔离目录，返回绝对路径。"""
    target_dir = settings.storage_dir / str(tenant_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix.lower()
    target = target_dir / f"{uuid4().hex}{suffix}"
    with target.open("wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)
    return target.resolve()

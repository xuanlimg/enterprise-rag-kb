"""启用 pgvector 扩展

Revision ID: 0001_enable_pgvector
Revises:
Create Date: 2026-10-11
"""
from alembic import op

revision = "0001_enable_pgvector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 pgvector 扩展，表结构后续用 autogenerate 生成。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """删除 pgvector 扩展。"""
    op.execute("DROP EXTENSION IF EXISTS vector")

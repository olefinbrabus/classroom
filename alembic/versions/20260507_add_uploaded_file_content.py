"""Add uploaded file content

Revision ID: 20260507_file_content
Revises: 20260501_remove_class
Create Date: 2026-05-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260507_file_content"
down_revision: Union[str, None] = "20260501_remove_class"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("uploaded_file", sa.Column("content", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("uploaded_file", "content")

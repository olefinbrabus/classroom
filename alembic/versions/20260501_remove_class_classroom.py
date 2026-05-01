"""Remove class and classroom models

Revision ID: 20260501_remove_class
Revises: 20260501_lms_core
Create Date: 2026-05-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260501_remove_class"
down_revision: Union[str, None] = "20260501_lms_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("material") as batch_op:
        batch_op.drop_index("ix_material_classroom")
        batch_op.drop_column("classroom")

    op.drop_table("class_users")
    op.drop_table("class_classroom")
    op.drop_index(op.f("ix_class_name"), table_name="class")
    op.drop_table("class")
    op.drop_index(op.f("ix_classroom_name"), table_name="classroom")
    op.drop_table("classroom")


def downgrade() -> None:
    op.create_table(
        "class",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_class_name"), "class", ["name"], unique=False)

    op.create_table(
        "classroom",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_classroom_name"), "classroom", ["name"], unique=False)

    op.create_table(
        "class_classroom",
        sa.Column("class_id", sa.Integer(), nullable=True),
        sa.Column("classroom_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["class_id"], ["class.id"]),
        sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"]),
    )
    op.create_table(
        "class_users",
        sa.Column("class_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["class_id"], ["class.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["classroom_user.id"]),
    )

    with op.batch_alter_table("material") as batch_op:
        batch_op.add_column(sa.Column("classroom", sa.Integer(), nullable=True))
        batch_op.create_index("ix_material_classroom", ["classroom"], unique=False)
        batch_op.create_foreign_key(
            "fk_material_classroom_classroom",
            "classroom",
            ["classroom"],
            ["id"],
        )

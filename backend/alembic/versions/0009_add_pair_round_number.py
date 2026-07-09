"""add round_number to test_session_pairs

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-09

round_number: 같은 라운드 내 페어는 병렬 실행, 다음 라운드는 이전 라운드 완료 후 시작.
기존 행은 전부 round_number=1 로 기본값 처리한다.
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.add_column(
        "test_session_pairs",
        sa.Column("round_number", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_session_round",
        "test_session_pairs",
        ["session_id", "round_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_round", table_name="test_session_pairs")
    if _is_sqlite():
        with op.batch_alter_table("test_session_pairs") as batch_op:
            batch_op.drop_column("round_number")
    else:
        op.drop_column("test_session_pairs", "round_number")


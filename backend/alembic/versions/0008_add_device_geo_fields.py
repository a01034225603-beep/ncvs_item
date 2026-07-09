"""add_device_geo_fields

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.add_column("bacs_devices", sa.Column("sido",    sa.String(32),  nullable=True))
    op.add_column("bacs_devices", sa.Column("sigungu", sa.String(64),  nullable=True))
    op.add_column("bacs_devices", sa.Column("geo_x",   sa.Float(),     nullable=True))
    op.add_column("bacs_devices", sa.Column("geo_y",   sa.Float(),     nullable=True))


def downgrade() -> None:
    # SQLite: batch_alter_table 사용 (DROP COLUMN 직접 미지원)
    if _is_sqlite():
        with op.batch_alter_table("bacs_devices") as batch_op:
            batch_op.drop_column("geo_y")
            batch_op.drop_column("geo_x")
            batch_op.drop_column("sigungu")
            batch_op.drop_column("sido")
    else:
        op.drop_column("bacs_devices", "geo_y")
        op.drop_column("bacs_devices", "geo_x")
        op.drop_column("bacs_devices", "sigungu")
        op.drop_column("bacs_devices", "sido")

"""bacs_devices: 포트별 전화번호 4개 컬럼 추가 (port0~3_phone)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 포트별 전화번호 컬럼 추가 (0·1=발신TX, 2·3=착신RX), NULL 허용
    op.add_column("bacs_devices", sa.Column("port0_phone", sa.String(32), nullable=True))
    op.add_column("bacs_devices", sa.Column("port1_phone", sa.String(32), nullable=True))
    op.add_column("bacs_devices", sa.Column("port2_phone", sa.String(32), nullable=True))
    op.add_column("bacs_devices", sa.Column("port3_phone", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("bacs_devices", "port3_phone")
    op.drop_column("bacs_devices", "port2_phone")
    op.drop_column("bacs_devices", "port1_phone")
    op.drop_column("bacs_devices", "port0_phone")

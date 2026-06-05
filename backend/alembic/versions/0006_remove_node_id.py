"""remove node_id column (항상 1로 고정)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-27

node_id는 BACS 프로토콜 명세상 항상 1로 고정 사용하므로
DB 컬럼을 제거하고 코드에서 상수로 관리한다.
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 혹시 컬럼이 남아 있을 경우를 위해 먼저 1로 일괄 업데이트 후 컬럼 제거
    op.execute("UPDATE bacs_devices SET node_id = 1")
    op.drop_column('bacs_devices', 'node_id')


def downgrade() -> None:
    # 롤백 시 node_id 컬럼 복원 (전부 1로)
    op.add_column(
        'bacs_devices',
        sa.Column('node_id', sa.SmallInteger(), nullable=False, server_default='1'),
    )

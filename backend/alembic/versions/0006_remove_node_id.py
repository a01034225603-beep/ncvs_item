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


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    # SQLite: batch_alter_table 사용 (DROP COLUMN 직접 미지원)
    # MySQL: 기존 방식 유지 (UPDATE 후 drop_column)
    if _is_sqlite():
        with op.batch_alter_table('bacs_devices') as batch_op:
            try:
                batch_op.drop_column('node_id')
            except Exception:  # noqa: BLE001
                pass  # 컬럼이 이미 없으면 무시
    else:
        op.execute("UPDATE bacs_devices SET node_id = 1")
        op.drop_column('bacs_devices', 'node_id')


def downgrade() -> None:
    # 롤백 시 node_id 컬럼 복원 (전부 1로)
    op.add_column(
        'bacs_devices',
        sa.Column('node_id', sa.SmallInteger(), nullable=False, server_default='1'),
    )

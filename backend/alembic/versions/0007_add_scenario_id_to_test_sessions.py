"""add scenario_id to test_sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-04

"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.add_column(
        'test_sessions',
        sa.Column('scenario_id', sa.BigInteger(), nullable=True),
    )
    # SQLite는 FK constraint ALTER 미지원 → skip (FK 강제 불필요)
    if not _is_sqlite():
        op.create_foreign_key(
            'fk_test_sessions_scenario_id',
            'test_sessions', 'scenarios',
            ['scenario_id'], ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    if not _is_sqlite():
        op.drop_constraint('fk_test_sessions_scenario_id', 'test_sessions', type_='foreignkey')
    if _is_sqlite():
        with op.batch_alter_table('test_sessions') as batch_op:
            batch_op.drop_column('scenario_id')
    else:
        op.drop_column('test_sessions', 'scenario_id')


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


def upgrade() -> None:
    # test_sessions 테이블에 scenario_id 컬럼 추가
    # NULL 허용 — 기존 세션(마이그레이션 이전 데이터) 호환 유지
    op.add_column(
        'test_sessions',
        sa.Column('scenario_id', sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        'fk_test_sessions_scenario_id',
        'test_sessions', 'scenarios',
        ['scenario_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_test_sessions_scenario_id', 'test_sessions', type_='foreignkey')
    op.drop_column('test_sessions', 'scenario_id')

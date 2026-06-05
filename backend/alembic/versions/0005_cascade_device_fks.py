"""add ON DELETE CASCADE to bacs_devices foreign keys

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-26

장비 삭제 시 FK 제약으로 삭제가 막히는 문제 해결.
device_locks / pair_latest_result / test_session_pairs 테이블의
bacs_devices 참조 FK에 ON DELETE CASCADE 추가.
"""
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── device_locks ──────────────────────────────────────────────
    op.drop_constraint('device_locks_ibfk_1', 'device_locks', type_='foreignkey')
    op.create_foreign_key(
        'device_locks_ibfk_1', 'device_locks',
        'bacs_devices', ['bacs_id'], ['id'],
        ondelete='CASCADE',
    )

    # ── pair_latest_result ────────────────────────────────────────
    op.drop_constraint('pair_latest_result_ibfk_1', 'pair_latest_result', type_='foreignkey')
    op.create_foreign_key(
        'pair_latest_result_ibfk_1', 'pair_latest_result',
        'bacs_devices', ['dst_bacs_id'], ['id'],
        ondelete='CASCADE',
    )
    op.drop_constraint('pair_latest_result_ibfk_3', 'pair_latest_result', type_='foreignkey')
    op.create_foreign_key(
        'pair_latest_result_ibfk_3', 'pair_latest_result',
        'bacs_devices', ['src_bacs_id'], ['id'],
        ondelete='CASCADE',
    )

    # ── test_session_pairs ────────────────────────────────────────
    op.drop_constraint('test_session_pairs_ibfk_1', 'test_session_pairs', type_='foreignkey')
    op.create_foreign_key(
        'test_session_pairs_ibfk_1', 'test_session_pairs',
        'bacs_devices', ['dst_bacs_id'], ['id'],
        ondelete='CASCADE',
    )
    op.drop_constraint('test_session_pairs_ibfk_3', 'test_session_pairs', type_='foreignkey')
    op.create_foreign_key(
        'test_session_pairs_ibfk_3', 'test_session_pairs',
        'bacs_devices', ['src_bacs_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    # ── test_session_pairs ────────────────────────────────────────
    op.drop_constraint('test_session_pairs_ibfk_3', 'test_session_pairs', type_='foreignkey')
    op.create_foreign_key(
        'test_session_pairs_ibfk_3', 'test_session_pairs',
        'bacs_devices', ['src_bacs_id'], ['id'],
    )
    op.drop_constraint('test_session_pairs_ibfk_1', 'test_session_pairs', type_='foreignkey')
    op.create_foreign_key(
        'test_session_pairs_ibfk_1', 'test_session_pairs',
        'bacs_devices', ['dst_bacs_id'], ['id'],
    )

    # ── pair_latest_result ────────────────────────────────────────
    op.drop_constraint('pair_latest_result_ibfk_3', 'pair_latest_result', type_='foreignkey')
    op.create_foreign_key(
        'pair_latest_result_ibfk_3', 'pair_latest_result',
        'bacs_devices', ['src_bacs_id'], ['id'],
    )
    op.drop_constraint('pair_latest_result_ibfk_1', 'pair_latest_result', type_='foreignkey')
    op.create_foreign_key(
        'pair_latest_result_ibfk_1', 'pair_latest_result',
        'bacs_devices', ['dst_bacs_id'], ['id'],
    )

    # ── device_locks ──────────────────────────────────────────────
    op.drop_constraint('device_locks_ibfk_1', 'device_locks', type_='foreignkey')
    op.create_foreign_key(
        'device_locks_ibfk_1', 'device_locks',
        'bacs_devices', ['bacs_id'], ['id'],
    )

"""health status enum: ok→online, fail→offline

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-20
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    """현재 마이그레이션 실행 중인 DB가 SQLite인지 확인한다."""
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    # SQLite는 ENUM 타입을 문자열로 저장하므로 MODIFY COLUMN 불필요
    # MySQL에서만 ENUM 컬럼 타입 확장 후 데이터 이전
    if not _is_sqlite():
        op.execute(
            "ALTER TABLE device_health MODIFY COLUMN status "
            "ENUM('ok','fail','unknown','online','offline') NOT NULL DEFAULT 'unknown'"
        )
    # 데이터 값 마이그레이션 (공통)
    op.execute("UPDATE device_health SET status='online' WHERE status='ok'")
    op.execute("UPDATE device_health SET status='offline' WHERE status='fail'")
    if not _is_sqlite():
        op.execute(
            "ALTER TABLE device_health MODIFY COLUMN status "
            "ENUM('online','offline','unknown') NOT NULL DEFAULT 'unknown'"
        )


def downgrade() -> None:
    if not _is_sqlite():
        op.execute(
            "ALTER TABLE device_health MODIFY COLUMN status "
            "ENUM('online','offline','unknown','ok','fail') NOT NULL DEFAULT 'unknown'"
        )
    op.execute("UPDATE device_health SET status='ok' WHERE status='online'")
    op.execute("UPDATE device_health SET status='fail' WHERE status='offline'")
    if not _is_sqlite():
        op.execute(
            "ALTER TABLE device_health MODIFY COLUMN status "
            "ENUM('ok','fail','unknown') NOT NULL DEFAULT 'unknown'"
        )

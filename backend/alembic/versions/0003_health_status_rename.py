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


def upgrade() -> None:
    # 1. MySQL ENUM 타입 변경: 'ok'→'online', 'fail'→'offline' 추가
    op.execute(
        "ALTER TABLE device_health MODIFY COLUMN status "
        "ENUM('ok','fail','unknown','online','offline') NOT NULL DEFAULT 'unknown'"
    )
    # 2. 기존 데이터 값 마이그레이션
    op.execute("UPDATE device_health SET status='online' WHERE status='ok'")
    op.execute("UPDATE device_health SET status='offline' WHERE status='fail'")
    # 3. 구 값 제거하여 최종 ENUM 정리
    op.execute(
        "ALTER TABLE device_health MODIFY COLUMN status "
        "ENUM('online','offline','unknown') NOT NULL DEFAULT 'unknown'"
    )


def downgrade() -> None:
    # 1. 구 값 다시 추가
    op.execute(
        "ALTER TABLE device_health MODIFY COLUMN status "
        "ENUM('online','offline','unknown','ok','fail') NOT NULL DEFAULT 'unknown'"
    )
    # 2. 데이터 롤백
    op.execute("UPDATE device_health SET status='ok' WHERE status='online'")
    op.execute("UPDATE device_health SET status='fail' WHERE status='offline'")
    # 3. 최종 ENUM 정리
    op.execute(
        "ALTER TABLE device_health MODIFY COLUMN status "
        "ENUM('ok','fail','unknown') NOT NULL DEFAULT 'unknown'"
    )

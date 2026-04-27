"""init: create all tables from models

Revision ID: 20260427_0001
Revises:
Create Date: 2026-04-27 12:00:00
"""

from __future__ import annotations

from alembic import op

from core.db.models import Base

revision = "20260427_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Bootstrap the schema from SQLAlchemy metadata.

    Subsequent migrations will be generated via `alembic revision --autogenerate`.
    """
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

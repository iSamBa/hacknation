"""add transport_mode to user_profiles

Revision ID: c3be89450f71
Revises: a2ad78349f60
Create Date: 2026-02-08 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3be89450f71'
down_revision: str | Sequence[str] | None = 'a2ad78349f60'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('transport_mode', sa.String(20), server_default='driving', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('user_profiles', 'transport_mode')

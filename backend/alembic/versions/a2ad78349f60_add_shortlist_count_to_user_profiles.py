"""add shortlist_count to user_profiles

Revision ID: a2ad78349f60
Revises: b394345ca7cf
Create Date: 2026-02-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a2ad78349f60'
down_revision: Union[str, Sequence[str], None] = 'b394345ca7cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('shortlist_count', sa.Integer(), server_default='15', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('user_profiles', 'shortlist_count')

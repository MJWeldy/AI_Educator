"""enrollments

Revision ID: c3e6a9b47d51
Revises: b2d5f8a13c42
Create Date: 2026-07-09 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db  # custom column types (TZDateTime) referenced by autogenerate


# revision identifiers, used by Alembic.
revision: str = 'c3e6a9b47d51'
down_revision: Union[str, Sequence[str], None] = 'b2d5f8a13c42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'enrollments',
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('created_at', app.db.TZDateTime(), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id']),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('profile_id', 'course_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('enrollments')

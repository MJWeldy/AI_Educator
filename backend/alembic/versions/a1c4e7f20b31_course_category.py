"""course category

Revision ID: a1c4e7f20b31
Revises: 275215b989f5
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db  # custom column types (TZDateTime) referenced by autogenerate


# revision identifiers, used by Alembic.
revision: str = 'a1c4e7f20b31'
down_revision: Union[str, Sequence[str], None] = '275215b989f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.String(), nullable=False, server_default=''))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('category')

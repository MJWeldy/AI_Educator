"""auth accounts and sessions

Revision ID: d4f7b1c8e2a3
Revises: c3e6a9b47d51
Create Date: 2026-07-09 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db  # custom column types (TZDateTime) referenced by autogenerate


# revision identifiers, used by Alembic.
revision: str = 'd4f7b1c8e2a3'
down_revision: Union[str, Sequence[str], None] = 'c3e6a9b47d51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('password_hash', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_profiles_username'), ['username'], unique=True)

    op.create_table(
        'auth_sessions',
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('created_at', app.db.TZDateTime(), nullable=False),
        sa.Column('expires_at', app.db.TZDateTime(), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('token'),
    )
    op.create_index(op.f('ix_auth_sessions_profile_id'), 'auth_sessions', ['profile_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_auth_sessions_profile_id'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_profiles_username'))
        batch_op.drop_column('password_hash')
        batch_op.drop_column('username')

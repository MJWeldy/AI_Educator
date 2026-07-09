"""document files (folder/multi-file uploads)

Revision ID: b2d5f8a13c42
Revises: a1c4e7f20b31
Create Date: 2026-07-09 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db  # custom column types (TZDateTime) referenced by autogenerate


# revision identifiers, used by Alembic.
revision: str = 'b2d5f8a13c42'
down_revision: Union[str, Sequence[str], None] = 'a1c4e7f20b31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'document_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('stored_path', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('kind', sa.String(), nullable=False, server_default='pdf'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_files_document_id'), 'document_files', ['document_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_document_files_document_id'), table_name='document_files')
    op.drop_table('document_files')

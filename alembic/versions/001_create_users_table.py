"""Create users table

Revision ID: 001
Revises: 
Create Date: 2025-11-07 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True, schema='public')
    op.create_index('ix_users_id', 'users', ['id'], unique=False, schema='public')
    op.create_index('ix_users_is_active', 'users', ['is_active'], unique=False, schema='public')


def downgrade() -> None:
    op.drop_index('ix_users_is_active', table_name='users', schema='public')
    op.drop_index('ix_users_id', table_name='users', schema='public')
    op.drop_index('ix_users_telegram_id', table_name='users', schema='public')
    op.drop_table('users', schema='public')


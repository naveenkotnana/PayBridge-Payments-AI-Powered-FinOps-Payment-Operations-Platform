"""add shared login throttling

Revision ID: 3be1b69e44f1
Revises: 363a5299afcb
Create Date: 2026-11-08 10:28:54.725228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3be1b69e44f1'
down_revision: Union[str, Sequence[str], None] = '363a5299afcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Some local/deployed databases already created this table through the
    # previous ORM create_all startup path before Alembic was introduced.
    if not sa.inspect(op.get_bind()).has_table('login_rate_limits'):
        op.create_table('login_rate_limits',
        sa.Column('identity_digest', sa.String(length=64), nullable=False),
        sa.Column('window_started_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('blocked_until', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('identity_digest')
        )
        op.create_index(op.f('ix_login_rate_limits_blocked_until'), 'login_rate_limits', ['blocked_until'], unique=False)
        op.create_index(op.f('ix_login_rate_limits_window_started_at'), 'login_rate_limits', ['window_started_at'], unique=False)


def downgrade() -> None:
    """Protect accumulated security-throttle evidence from destructive rollback."""
    raise RuntimeError("Destructive schema downgrade is disabled; use a reviewed forward migration.")

"""store checkout key reference

Revision ID: 8e6f27fd41bb
Revises: 1a5dbd9f3a39
Create Date: 2026-11-08 10:48:10.713983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e6f27fd41bb'
down_revision: Union[str, Sequence[str], None] = '1a5dbd9f3a39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Some databases created these columns through an earlier ORM startup
    # before Alembic tracked the corresponding revision. Adopt that schema
    # without failing or rewriting existing checkout reservations.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("checkout_requests"):
        columns = {column["name"] for column in inspector.get_columns("checkout_requests")}
        if "provider_key_id" not in columns:
            op.add_column(
                "checkout_requests",
                sa.Column("provider_key_id", sa.String(length=40), nullable=True),
            )


def downgrade() -> None:
    """Keep checkout idempotency evidence available for recovery."""
    raise RuntimeError("Destructive schema downgrade is disabled; use a reviewed forward migration.")

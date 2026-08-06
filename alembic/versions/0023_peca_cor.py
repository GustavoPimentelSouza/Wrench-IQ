"""adicionar cor em pecas

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-04

"""
import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pecas", sa.Column("cor", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("pecas", "cor")

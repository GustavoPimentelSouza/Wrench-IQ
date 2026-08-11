"""adicionar acao_finalizadora em mensagens

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-06

"""
import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mensagens", sa.Column("acao_finalizadora", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("mensagens", "acao_finalizadora")

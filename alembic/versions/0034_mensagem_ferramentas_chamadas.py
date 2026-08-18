"""adicionar ferramentas_chamadas em mensagens

Revision ID: 0034
Revises: 0033
Create Date: 2026-08-11

"""
import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mensagens", sa.Column("ferramentas_chamadas", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("mensagens", "ferramentas_chamadas")

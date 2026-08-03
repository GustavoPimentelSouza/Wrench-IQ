"""adicionar valor_orcamento e motivo_cancelamento em protocolos

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-30

"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "protocolos", sa.Column("valor_orcamento", sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        "protocolos", sa.Column("motivo_cancelamento", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("protocolos", "motivo_cancelamento")
    op.drop_column("protocolos", "valor_orcamento")

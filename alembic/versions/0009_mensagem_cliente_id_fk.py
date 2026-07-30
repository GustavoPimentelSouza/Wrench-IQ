"""transformar mensagens.cliente_id em FK para clientes

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Mesma situação da migração 0007: cliente_id existentes eram strings de
    # teste sem cliente real correspondente.
    op.execute("DELETE FROM mensagens")
    op.drop_column("mensagens", "cliente_id")
    op.add_column(
        "mensagens",
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("mensagens", "cliente_id")
    op.add_column("mensagens", sa.Column("cliente_id", sa.String(), nullable=False))

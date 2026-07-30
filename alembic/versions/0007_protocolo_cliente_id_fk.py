"""transformar protocolos.cliente_id em FK para clientes

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Os cliente_id existentes eram strings arbitrárias de teste (ex:
    # "cliente-1"), sem cliente real correspondente — não dá pra migrar
    # esses dados, então limpamos antes de trocar o tipo da coluna.
    op.execute("DELETE FROM protocolos")
    op.drop_column("protocolos", "cliente_id")
    op.add_column(
        "protocolos",
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("protocolos", "cliente_id")
    op.add_column("protocolos", sa.Column("cliente_id", sa.String(), nullable=False))

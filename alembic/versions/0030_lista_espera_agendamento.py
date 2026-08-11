"""criar tabela lista_espera_agendamento

Revision ID: 0030
Revises: 0029
Create Date: 2026-08-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lista_espera_agendamento",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("especialidade", sa.String(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atendido", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_table("lista_espera_agendamento")

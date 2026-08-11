"""criar tabela notificacoes

Revision ID: 0029
Revises: 0028
Create Date: 2026-08-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notificacoes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("mensagem", sa.String(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enviada", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("enviada_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("notificacoes")

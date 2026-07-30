"""criar tabela pedidos

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pedidos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.Integer(), sa.Identity(), nullable=False, unique=True),
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "peca_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pecas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("tipo_entrega", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("endereco_entrega", sa.String(), nullable=True),
        sa.Column("link_pagamento", sa.String(), nullable=True),
        sa.Column("entregue_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("pedidos")

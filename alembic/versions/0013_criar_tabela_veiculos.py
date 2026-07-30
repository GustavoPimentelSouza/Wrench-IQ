"""criar tabela veiculos

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "veiculos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("marca", sa.String(), nullable=False),
        sa.Column("modelo", sa.String(), nullable=False),
        sa.Column("ano", sa.String(), nullable=False),
        sa.Column("placa", sa.String(), nullable=False, unique=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("veiculos")

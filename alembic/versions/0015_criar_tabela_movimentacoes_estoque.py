"""criar tabela movimentacoes_estoque

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movimentacoes_estoque",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "peca_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pecas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("movimentacoes_estoque")

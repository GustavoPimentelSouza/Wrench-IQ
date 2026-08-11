"""criar tabela itens_adicionais_protocolo

Revision ID: 0028
Revises: 0027
Create Date: 2026-08-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "itens_adicionais_protocolo",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "protocolo_id",
            UUID(as_uuid=True),
            sa.ForeignKey("protocolos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("descricao", sa.String(), nullable=False),
        sa.Column(
            "peca_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pecas.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("itens_adicionais_protocolo")

"""criar tabela avaliacoes_teste (temporária, ferramenta de dev)

Revision ID: 0040
Revises: 0039
Create Date: 2026-09-29

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "avaliacoes_teste",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("resultado", sa.String(), nullable=False),
        sa.Column("comentario", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("avaliacoes_teste")

"""criar tabela reclassificacoes_especialidade

Revision ID: 0031
Revises: 0030
Create Date: 2026-08-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reclassificacoes_especialidade",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "protocolo_id",
            UUID(as_uuid=True),
            sa.ForeignKey("protocolos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("especialidades_originais", sa.String(), nullable=False),
        sa.Column("especialidades_finais", sa.String(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reclassificacoes_especialidade")

"""remover tabela itens_adicionais_protocolo (módulo fora do escopo do MVP)

Revision ID: 0036
Revises: 0035
Create Date: 2026-08-19

Item adicional de protocolo confirmado como isolado do core (mapeamento
de dependência feito antes da remoção): nenhum arquivo core importa esse
módulo, só o inverso. A migração 0028 que criou a tabela permanece
intacta — histórico de schema nunca é editado, só estendido.
"""
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("itens_adicionais_protocolo")


def downgrade() -> None:
    # Recria a mesma estrutura da migração 0028, caso precise reverter.
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID

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

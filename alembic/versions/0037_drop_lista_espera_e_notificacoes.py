"""remover tabelas lista_espera_agendamento e notificacoes (módulos fora do escopo do MVP)

Revision ID: 0037
Revises: 0036
Create Date: 2026-08-19

Lista de espera e notificação de agendamento confirmadas como isoladas do
core (mapeamento de dependência feito antes da remoção): a lógica core de
disponibilidade ("sempre devolver a próxima data com vaga") não depende de
nenhuma das duas. As migrações 0029/0030 que criaram as tabelas permanecem
intactas — histórico de schema nunca é editado, só estendido.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("lista_espera_agendamento")
    op.drop_table("notificacoes")


def downgrade() -> None:
    # Recria a mesma estrutura das migrações 0029/0030, caso precise reverter.
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

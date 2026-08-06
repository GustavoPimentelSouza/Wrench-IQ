"""adicionar motivo_atendimento em mensagens

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-04

"""
import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mensagens", sa.Column("motivo_atendimento", sa.String(), nullable=True))
    # Dado histórico: toda mensagem já marcada como precisa_atendimento
    # antes desse campo existir era reclamação sensível (o único motivo que
    # existia até agora) — sem isso, ficaria motivo=None pra registros
    # antigos, quebrando a distinção visual na tela de Atendimento.
    op.execute(
        "UPDATE mensagens SET motivo_atendimento = 'reclamacao_sensivel' "
        "WHERE precisa_atendimento_humano = true AND categoria = 'reclamacao_sensivel'"
    )
    op.execute(
        "UPDATE mensagens SET motivo_atendimento = 'falha_tecnica' "
        "WHERE precisa_atendimento_humano = true AND motivo_atendimento IS NULL"
    )


def downgrade() -> None:
    op.drop_column("mensagens", "motivo_atendimento")

"""ajustar limite_trocas_sem_resolucao padrão de 3 pra 8

Revision ID: 0035
Revises: 0034
Create Date: 2026-08-12

Padrão de produção: 3 se mostrou agressivo demais em teste ao vivo — uma
venda legítima de várias etapas (peça, cor, quantidade, entrega) já
consumia o limite antes de fechar. 8 dá espaço real sem deixar a conversa
girar pra sempre (ver domain/configuracao_oficina.py).
"""
import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "configuracao_oficina",
        "limite_trocas_sem_resolucao",
        server_default="8",
    )
    op.execute(
        "UPDATE configuracao_oficina SET limite_trocas_sem_resolucao = 8 "
        "WHERE limite_trocas_sem_resolucao = 3"
    )


def downgrade() -> None:
    op.alter_column(
        "configuracao_oficina",
        "limite_trocas_sem_resolucao",
        server_default="3",
    )
    op.execute(
        "UPDATE configuracao_oficina SET limite_trocas_sem_resolucao = 3 "
        "WHERE limite_trocas_sem_resolucao = 8"
    )

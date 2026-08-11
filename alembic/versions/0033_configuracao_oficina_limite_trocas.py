"""adicionar limite_trocas_sem_resolucao em configuracao_oficina

Revision ID: 0033
Revises: 0032
Create Date: 2026-08-11

"""
import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuracao_oficina",
        sa.Column(
            "limite_trocas_sem_resolucao", sa.Integer(), nullable=False, server_default="3"
        ),
    )


def downgrade() -> None:
    op.drop_column("configuracao_oficina", "limite_trocas_sem_resolucao")

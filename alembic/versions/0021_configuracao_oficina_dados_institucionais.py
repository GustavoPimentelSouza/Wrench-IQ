"""adicionar nome_empresa, endereco e mensagem_encerramento em configuracao_oficina

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-04

"""
import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuracao_oficina",
        sa.Column("nome_empresa", sa.String(), nullable=False, server_default="Oficina"),
    )
    op.add_column("configuracao_oficina", sa.Column("endereco", sa.String(), nullable=True))
    op.add_column(
        "configuracao_oficina", sa.Column("mensagem_encerramento", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("configuracao_oficina", "mensagem_encerramento")
    op.drop_column("configuracao_oficina", "endereco")
    op.drop_column("configuracao_oficina", "nome_empresa")

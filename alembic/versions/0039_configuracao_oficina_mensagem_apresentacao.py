"""adicionar mensagem_apresentacao em configuracao_oficina

Revision ID: 0039
Revises: 0038
Create Date: 2026-09-15

"""
import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuracao_oficina", sa.Column("mensagem_apresentacao", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("configuracao_oficina", "mensagem_apresentacao")

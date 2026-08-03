"""adicionar precisa_atendimento_humano e atendimento_resolvido em mensagens

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-03

"""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mensagens",
        sa.Column(
            "precisa_atendimento_humano",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "mensagens",
        sa.Column(
            "atendimento_resolvido",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("mensagens", "atendimento_resolvido")
    op.drop_column("mensagens", "precisa_atendimento_humano")

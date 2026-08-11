"""adicionar tolerancia_no_show_minutos em configuracao_oficina

Revision ID: 0032
Revises: 0031
Create Date: 2026-08-10

"""
import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuracao_oficina",
        sa.Column(
            "tolerancia_no_show_minutos", sa.Integer(), nullable=False, server_default="20"
        ),
    )


def downgrade() -> None:
    op.drop_column("configuracao_oficina", "tolerancia_no_show_minutos")

"""adicionar imagem_url em mensagens

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-06

"""
import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mensagens", sa.Column("imagem_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("mensagens", "imagem_url")

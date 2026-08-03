"""adicionar resposta_ia em mensagens

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-31

"""
import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mensagens", sa.Column("resposta_ia", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("mensagens", "resposta_ia")

"""adicionar embedding vetorial em pecas (busca semantica)

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-31

"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("pecas", sa.Column("embedding", Vector(768), nullable=True))


def downgrade() -> None:
    op.drop_column("pecas", "embedding")

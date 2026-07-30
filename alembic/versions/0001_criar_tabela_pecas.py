"""criar tabela pecas

Revision ID: 0001
Revises:
Create Date: 2026-07-22

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pecas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("marca_modelo_compativel", sa.String(), nullable=False),
        sa.Column("ano_compativel", sa.String(), nullable=False),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantidade_estoque", sa.Integer(), nullable=False),
        sa.Column("imagem_url", sa.String(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("pecas")

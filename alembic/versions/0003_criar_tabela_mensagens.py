"""criar tabela mensagens

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mensagens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cliente_id", sa.String(), nullable=False),
        sa.Column("texto", sa.String(), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("mensagens")

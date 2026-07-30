"""criar tabela protocolos

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protocolos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.Integer(), sa.Identity(), nullable=False, unique=True),
        sa.Column("cliente_id", sa.String(), nullable=False),
        sa.Column("veiculo", sa.String(), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("descricao", sa.String(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("protocolos")

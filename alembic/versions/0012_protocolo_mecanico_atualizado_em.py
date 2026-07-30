"""adicionar mecanico_id e atualizado_em em protocolos

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "protocolos",
        sa.Column(
            "mecanico_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "protocolos",
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("protocolos", "atualizado_em")
    op.drop_column("protocolos", "mecanico_id")

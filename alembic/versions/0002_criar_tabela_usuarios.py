"""criar tabela usuarios

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-22

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_PAPEL_USUARIO_TIPO = ENUM(
    "admin", "atendente", "mecanico", name="papel_usuario", create_type=False
)


def upgrade() -> None:
    # DO $$ ... EXCEPTION torna a criação do tipo idempotente de verdade (via
    # SQL puro), sem depender do comportamento de create_type/checkfirst do
    # SQLAlchemy, que não suprimiu a tentativa automática de recriação do
    # tipo ao usar o Enum como coluna em create_table().
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE papel_usuario AS ENUM ('admin', 'atendente', 'mecanico');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.create_table(
        "usuarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("senha_hash", sa.String(), nullable=False),
        sa.Column("papel", _PAPEL_USUARIO_TIPO, nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
    op.execute("DROP TYPE IF EXISTS papel_usuario")
